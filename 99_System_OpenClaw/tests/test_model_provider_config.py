from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.model_provider_config import (  # noqa: E402
    CapabilityState,
    CapabilityStatus,
    ConfigStorageError,
    ConfigValidationError,
    DEFAULT_REASONING_EFFORT,
    ExecutionProtocol,
    LEGACY_SCHEMA_VERSION,
    ModelProviderConfig,
    ModelProviderConfigStore,
    NoNetworkCapabilityProbe,
    Provider,
    ReasoningEffort,
    SCHEMA_VERSION,
    SUPPORTED_REASONING_EFFORTS,
    probe_capability,
    resolve_execution_config,
)


class _FakeProbe:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.seen_ids: list[str] = []

    def probe(self, config: ModelProviderConfig) -> object:
        self.seen_ids.append(config.id)
        if self.error is not None:
            raise self.error
        return self.result


class ModelProviderConfigTests(unittest.TestCase):
    def make_config(
        self,
        config_id: str = "codex-main",
        provider: Provider | str = Provider.CODEX_OPENAI,
        model: str = "gpt-5",
        endpoint: str = "https://api.openai.com/v1",
        secret_ref: str = "keychain:codex-main",
        capability: CapabilityStatus | None = None,
        reasoning_effort: ReasoningEffort | str | None = None,
    ) -> ModelProviderConfig:
        return ModelProviderConfig(
            id=config_id,
            provider=provider,
            model=model,
            endpoint=endpoint,
            secret_ref=secret_ref,
            capability=capability,
            reasoning_effort=reasoning_effort,
        )

    def test_all_supported_providers_and_local_compatible_http(self) -> None:
        configs = [
            self.make_config(),
            self.make_config(
                "claude-main",
                Provider.CLAUDE_ANTHROPIC,
                "claude-3-7-sonnet",
                "https://api.anthropic.com/v1",
                "keychain:claude-main",
            ),
            self.make_config(
                "deepseek-main",
                Provider.DEEPSEEK,
                "deepseek-chat",
                "https://api.deepseek.com/v1",
                "keychain:deepseek-main",
            ),
            self.make_config(
                "local-compatible",
                Provider.OPENAI_COMPATIBLE,
                "local-model",
                "http://127.0.0.1:11434/v1",
                "keychain:local-compatible",
            ),
        ]
        self.assertEqual(
            {config.provider.value for config in configs},
            {"codex_openai", "claude_anthropic", "deepseek", "openai_compatible"},
        )
        self.assertTrue(all(config.id for config in configs))
        self.assertTrue(all(config.secret_ref for config in configs))
        self.assertTrue(all(config.reasoning_effort is ReasoningEffort.XHIGH for config in configs))

    def test_reasoning_effort_is_strict_public_and_persisted(self) -> None:
        self.assertEqual(
            set(SUPPORTED_REASONING_EFFORTS),
            {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"},
        )
        for effort in ReasoningEffort:
            with self.subTest(effort=effort.value):
                config = self.make_config(reasoning_effort=effort)
                self.assertEqual(config.reasoning_effort, effort)
                self.assertEqual(config.to_dict()["reasoning_effort"], effort.value)
                self.assertEqual(config.to_public_dict()["reasoning_effort"], effort.value)

        for invalid in ("", "HIGH", "custom", 1, True):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ConfigValidationError):
                    self.make_config(reasoning_effort=invalid)

        legacy_input = self.make_config().to_dict()
        legacy_input.pop("reasoning_effort")
        self.assertEqual(
            ModelProviderConfig.from_dict(legacy_input).reasoning_effort.value,
            DEFAULT_REASONING_EFFORT,
        )

    def test_execution_resolution_is_deterministic_and_secret_free(self) -> None:
        configs = [
            self.make_config(reasoning_effort="high"),
            self.make_config(
                "claude-main",
                Provider.CLAUDE_ANTHROPIC,
                "claude-3-7-sonnet",
                "https://api.anthropic.com/v1",
                "keychain:claude-main",
                reasoning_effort="medium",
            ),
            self.make_config(
                "deepseek-main",
                Provider.DEEPSEEK,
                "deepseek-chat",
                "https://api.deepseek.com/v1",
                "keychain:deepseek-main",
                reasoning_effort="low",
            ),
            self.make_config(
                "local-compatible",
                Provider.OPENAI_COMPATIBLE,
                "local-model",
                "http://127.0.0.1:11434/v1",
                "keychain:local-compatible",
                reasoning_effort="none",
            ),
        ]
        expected_protocols = {
            Provider.CODEX_OPENAI: ExecutionProtocol.OPENAI_RESPONSES,
            Provider.CLAUDE_ANTHROPIC: ExecutionProtocol.ANTHROPIC_MESSAGES,
            Provider.DEEPSEEK: ExecutionProtocol.OPENAI_CHAT_COMPLETIONS,
            Provider.OPENAI_COMPATIBLE: ExecutionProtocol.OPENAI_CHAT_COMPLETIONS,
        }

        for config in configs:
            with self.subTest(provider=config.provider.value):
                resolved = resolve_execution_config(config)
                self.assertEqual(resolved.protocol, expected_protocols[config.provider])
                self.assertEqual(resolved.credential_ref, config.secret_ref)
                self.assertEqual(resolved.reasoning_effort, config.reasoning_effort)
                serialized = json.dumps(resolved.to_dict(), sort_keys=True)
                self.assertNotIn(config.secret_ref, serialized)
                self.assertNotIn(config.secret_ref, repr(resolved))
                self.assertNotIn("secret_ref", resolved.to_dict())
                self.assertNotIn("credential_ref", resolved.to_dict())

    def test_secret_reference_rejects_urls_paths_and_token_shapes_without_leak(self) -> None:
        invalid_references = [
            "https://secret.example/key",
            "keychain/provider",
            "raw-secret-value",
            "aB39xY7q" * 6,
        ]
        for reference in invalid_references:
            with self.subTest(reference_type=reference[:8]):
                with self.assertRaises(ConfigValidationError) as context:
                    self.make_config(secret_ref=reference)
                self.assertNotIn(reference, str(context.exception))

        config = self.make_config()
        serialized = json.dumps(config.to_dict(), sort_keys=True)
        self.assertIn("keychain:codex-main", serialized)
        public_record = config.to_public_dict()
        self.assertNotIn("api_key", json.dumps(public_record, sort_keys=True))
        self.assertNotIn("secret_ref", public_record)

    def test_endpoint_policy_is_https_or_local_compatible_http(self) -> None:
        with self.assertRaises(ConfigValidationError):
            self.make_config(endpoint="http://api.openai.com/v1")
        with self.assertRaises(ConfigValidationError):
            self.make_config(
                provider=Provider.OPENAI_COMPATIBLE,
                endpoint="http://remote.example/v1",
            )
        with self.assertRaises(ConfigValidationError):
            self.make_config(
                provider=Provider.OPENAI_COMPATIBLE,
                endpoint="http://user:password@127.0.0.1:11434/v1",
            )
        with self.assertRaises(ConfigValidationError):
            self.make_config(endpoint="https://api.openai.com/v1?token=secret")
        self.assertEqual(
            self.make_config(
                config_id="localhost-compatible",
                provider=Provider.OPENAI_COMPATIBLE,
                endpoint="http://localhost/v1",
            ).endpoint,
            "http://localhost/v1",
        )

    def test_injected_probe_and_default_probe_have_distinct_states(self) -> None:
        config = self.make_config()
        for expected in (
            CapabilityStatus.available("capability_confirmed"),
            CapabilityStatus.unavailable("model_not_available"),
            CapabilityStatus.error("provider_error"),
        ):
            fake = _FakeProbe(expected)
            actual = probe_capability(config, fake)
            self.assertEqual(actual, expected)
            self.assertEqual(fake.seen_ids, [config.id])

        raised = probe_capability(config, _FakeProbe(error=RuntimeError("secret must not escape")))
        self.assertEqual(raised.state, CapabilityState.ERROR)
        self.assertEqual(raised.reason_code, "probe_exception")

        invalid = probe_capability(config, _FakeProbe({"state": "not-a-state", "reason_code": "bad"}))
        self.assertEqual(invalid, CapabilityStatus.error("probe_result_invalid"))

        default = probe_capability(config, NoNetworkCapabilityProbe())
        self.assertEqual(default.state, CapabilityState.UNAVAILABLE)
        self.assertEqual(default.reason_code, "network_probe_disabled")

    def test_store_round_trip_probe_persistence_and_atomic_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            store = ModelProviderConfigStore(root)
            configs = [
                self.make_config(),
                self.make_config(
                    "compatible-main",
                    Provider.OPENAI_COMPATIBLE,
                    "local-model",
                    "http://127.0.0.1:8000/v1",
                    "keychain:compatible-main",
                ),
            ]
            store.save(configs)
            self.assertEqual(store.load(), configs)
            self.assertEqual(store.path.parent, root.resolve())
            self.assertEqual(list(root.glob("*.tmp")), [])

            status = store.probe("codex-main", _FakeProbe(CapabilityStatus.available("probe_ok")))
            self.assertEqual(status.state, CapabilityState.AVAILABLE)
            self.assertEqual(store.get("codex-main").capability, status)

            payload = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
            self.assertEqual(len(payload["configs"]), 2)
            self.assertTrue(all(record["reasoning_effort"] == DEFAULT_REASONING_EFFORT for record in payload["configs"]))
            resolved = store.resolve_execution("codex-main")
            self.assertEqual(resolved.protocol, ExecutionProtocol.OPENAI_RESPONSES)
            self.assertNotIn("keychain:codex-main", json.dumps(resolved.to_dict(), sort_keys=True))

    def test_store_migrates_v1_and_rejects_incomplete_v2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            store = ModelProviderConfigStore(root)
            legacy_record = self.make_config().to_dict()
            legacy_record.pop("reasoning_effort")
            store.path.write_text(
                json.dumps({"schema_version": LEGACY_SCHEMA_VERSION, "configs": [legacy_record]}),
                encoding="utf-8",
            )

            loaded = store.load()
            self.assertEqual(loaded[0].reasoning_effort.value, DEFAULT_REASONING_EFFORT)
            store.save(loaded)
            migrated = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["schema_version"], SCHEMA_VERSION)
            self.assertEqual(migrated["configs"][0]["reasoning_effort"], DEFAULT_REASONING_EFFORT)

            migrated["configs"][0].pop("reasoning_effort")
            store.path.write_text(json.dumps(migrated), encoding="utf-8")
            with self.assertRaisesRegex(ConfigStorageError, "config_invalid"):
                store.load()

            legacy_record["reasoning_effort"] = "high"
            store.path.write_text(
                json.dumps({"schema_version": LEGACY_SCHEMA_VERSION, "configs": [legacy_record]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigStorageError, "store_schema_invalid"):
                store.load()

    def test_store_fails_closed_for_unknown_fields_duplicates_and_invalid_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            store = ModelProviderConfigStore(root)
            config = self.make_config()
            with self.assertRaises(ConfigValidationError):
                store.save([config, config])

            valid_record = config.to_dict()
            store.path.write_text(
                json.dumps(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "configs": [valid_record | {"unexpected": "field"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigStorageError):
                store.load()

            duplicate_record = config.to_dict()
            store.path.write_text(
                json.dumps(
                    {"schema_version": SCHEMA_VERSION, "configs": [duplicate_record, duplicate_record]}
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigStorageError):
                store.load()

            invalid_record = config.to_dict() | {"endpoint": "http://outside.example"}
            store.path.write_text(
                json.dumps({"schema_version": SCHEMA_VERSION, "configs": [invalid_record]}),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigStorageError) as context:
                store.load()
            self.assertNotIn("outside.example", str(context.exception))

    def test_store_rejects_paths_outside_explicit_work_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            outside = root.parent / "provider-config-outside.json"
            with self.assertRaises(ConfigStorageError):
                ModelProviderConfigStore(root, filename="../provider-config-outside.json")
            with self.assertRaises(ConfigStorageError):
                ModelProviderConfigStore(root, filename=str(outside))
            with self.assertRaises(ConfigStorageError):
                ModelProviderConfigStore(root, filename="provider-config.txt")
            with self.assertRaises(ConfigStorageError):
                ModelProviderConfigStore("")

            outside.write_text("{}", encoding="utf-8")
            link = root / "linked.json"
            try:
                os.symlink(outside, link)
            except (OSError, NotImplementedError):
                pass
            else:
                with self.assertRaises(ConfigStorageError):
                    ModelProviderConfigStore(root, filename="linked.json")
                link.unlink()
            outside.unlink()


if __name__ == "__main__":
    unittest.main()
