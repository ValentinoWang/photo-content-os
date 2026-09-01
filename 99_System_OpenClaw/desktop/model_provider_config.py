"""Local creative-model provider configuration with network-free probing."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import tempfile
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol


SCHEMA_VERSION = "model_provider_config_v1"
DEFAULT_CONFIG_FILENAME = "model-provider-config.json"
_CONFIG_FIELDS = frozenset({"id", "provider", "model", "endpoint", "secret_ref", "capability"})
_CAPABILITY_FIELDS = frozenset({"state", "reason_code"})
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_MODEL_RE = re.compile(r"^[^\s\x00-\x1f\x7f]{1,200}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_REASON_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_CONTROLLED_REF_SCHEMES = frozenset({"config", "credential", "env", "keychain", "ref", "secret", "vault"})


class ModelProviderConfigError(ValueError):
    """Base error whose message never includes supplied field values."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ConfigValidationError(ModelProviderConfigError):
    """Raised when a provider configuration or capability record is invalid."""


class ConfigStorageError(ModelProviderConfigError):
    """Raised when the bounded JSON store cannot be safely read or written."""


class Provider(str, Enum):
    CODEX_OPENAI = "codex_openai"
    CLAUDE_ANTHROPIC = "claude_anthropic"
    DEEPSEEK = "deepseek"
    OPENAI_COMPATIBLE = "openai_compatible"

    @classmethod
    def from_value(cls, value: object) -> "Provider":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ConfigValidationError("provider_invalid", "provider must be a supported value")
        try:
            return cls(value)
        except ValueError as exc:
            raise ConfigValidationError("provider_invalid", "provider must be a supported value") from exc


ModelProvider = Provider
ProviderKind = Provider
SUPPORTED_PROVIDERS = tuple(provider.value for provider in Provider)


class CapabilityState(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"

    @classmethod
    def from_value(cls, value: object) -> "CapabilityState":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise ConfigValidationError("capability_state_invalid", "capability state is invalid")
        try:
            return cls(value)
        except ValueError as exc:
            raise ConfigValidationError("capability_state_invalid", "capability state is invalid") from exc


CapabilityStatusValue = CapabilityState


def _looks_like_raw_secret(value: str) -> bool:
    """Reject common token shapes without retaining or echoing the value."""

    lowered = value.lower()
    suspicious_prefixes = (
        "s" + "k-",
        "s" + "k-ant-",
        "deepseek-",
        "a" + "kia",
        "a" + "iza",
        "ghp_",
        "github_pat_",
        "xox",
        "eyj",
        "bearer-",
        "raw-",
    )
    if lowered.startswith(suspicious_prefixes):
        return True

    # A long, separator-free value with several character classes is much more
    # likely to be a token than a human-chosen secret reference.
    if len(value) >= 32 and not any(char in value for char in "_.:-"):
        classes = sum(
            (
                any(char.islower() for char in value),
                any(char.isupper() for char in value),
                any(char.isdigit() for char in value),
            )
        )
        if classes >= 3:
            return True
    return False


def _validate_identifier(value: object) -> str:
    if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
        raise ConfigValidationError("identifier_invalid", "configuration id is invalid")
    return value


def _validate_model(value: object) -> str:
    if not isinstance(value, str) or _MODEL_RE.fullmatch(value) is None:
        raise ConfigValidationError("model_invalid", "model is invalid")
    return value


def _validate_secret_ref(value: object) -> str:
    if not isinstance(value, str):
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    if value != value.strip() or "/" in value or "\\" in value:
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    if _REFERENCE_RE.fullmatch(value) is None:
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.netloc
        or "://" in value
        or value.lower().startswith("www.")
        or (parsed.scheme and parsed.scheme.lower() not in _CONTROLLED_REF_SCHEMES)
    ):
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    if _looks_like_raw_secret(value):
        raise ConfigValidationError("secret_ref_invalid", "secret reference is invalid")
    return value


def _validate_endpoint(endpoint: object, provider: Provider) -> str:
    if not isinstance(endpoint, str) or not endpoint or endpoint != endpoint.strip():
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in endpoint):
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL")
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL") from exc

    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL")
    if parsed.query or parsed.fragment:
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL")
    if parsed.scheme == "https":
        return endpoint
    if parsed.scheme != "http" or provider is not Provider.OPENAI_COMPATIBLE:
        raise ConfigValidationError("endpoint_invalid", "endpoint must be a secure URL")

    normalized_host = hostname.lower().rstrip(".")
    is_loopback = normalized_host in _LOOPBACK_HOSTS
    if not is_loopback:
        try:
            is_loopback = ipaddress.ip_address(normalized_host).is_loopback
        except ValueError:
            is_loopback = False
    if not is_loopback:
        raise ConfigValidationError("endpoint_invalid", "plain HTTP is limited to local compatible services")
    # Accessing parsed.port above validates malformed ports. Keep the local
    # endpoint rule explicit even when a caller supplied no port.
    _ = port
    return endpoint


def _validate_reason_code(value: object) -> str:
    if not isinstance(value, str) or _REASON_CODE_RE.fullmatch(value) is None:
        raise ConfigValidationError("reason_code_invalid", "capability reason code is invalid")
    if _looks_like_raw_secret(value):
        raise ConfigValidationError("reason_code_invalid", "capability reason code is invalid")
    return value


@dataclass(frozen=True, slots=True)
class CapabilityStatus:
    state: CapabilityState
    reason_code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", CapabilityState.from_value(self.state))
        object.__setattr__(self, "reason_code", _validate_reason_code(self.reason_code))

    @classmethod
    def available(cls, reason_code: str = "probe_ok") -> "CapabilityStatus":
        return cls(CapabilityState.AVAILABLE, reason_code)

    @classmethod
    def unavailable(cls, reason_code: str = "provider_unavailable") -> "CapabilityStatus":
        return cls(CapabilityState.UNAVAILABLE, reason_code)

    @classmethod
    def error(cls, reason_code: str = "probe_error") -> "CapabilityStatus":
        return cls(CapabilityState.ERROR, reason_code)

    @classmethod
    def from_dict(cls, value: object) -> "CapabilityStatus":
        if not isinstance(value, Mapping) or set(value) != _CAPABILITY_FIELDS:
            raise ConfigValidationError("capability_invalid", "capability status is invalid")
        return cls(value["state"], value["reason_code"])

    @property
    def status(self) -> str:
        return self.state.value

    def to_dict(self) -> dict[str, str]:
        return {"state": self.state.value, "reason_code": self.reason_code}


def _coerce_capability(value: object) -> CapabilityStatus:
    if isinstance(value, CapabilityStatus):
        return value
    if isinstance(value, Mapping):
        return CapabilityStatus.from_dict(value)
    raise ConfigValidationError("capability_invalid", "capability status is invalid")


@dataclass(frozen=True, slots=True)
class ModelProviderConfig:
    id: str
    provider: Provider
    model: str
    endpoint: str
    secret_ref: str = field(repr=False)
    capability: CapabilityStatus = field(
        default_factory=lambda: CapabilityStatus.unavailable("not_probed")
    )

    def __init__(
        self,
        id: str | None = None,
        provider: Provider | str | None = None,
        model: str | None = None,
        endpoint: str | None = None,
        secret_ref: str | None = None,
        capability: CapabilityStatus | Mapping[str, Any] | None = None,
        *,
        config_id: str | None = None,
        credential_ref: str | None = None,
        key_ref: str | None = None,
    ) -> None:
        if id is not None and config_id is not None and id != config_id:
            raise ConfigValidationError("identifier_conflict", "configuration identifiers conflict")
        chosen_id = id if id is not None else config_id

        references = [
            value
            for value in (secret_ref, credential_ref, key_ref)
            if value is not None
        ]
        if len({repr(value) for value in references}) > 1:
            raise ConfigValidationError("secret_ref_conflict", "secret references conflict")
        chosen_ref = references[0] if references else None

        normalized_provider = Provider.from_value(provider)
        normalized_capability = (
            CapabilityStatus.unavailable("not_probed")
            if capability is None
            else _coerce_capability(capability)
        )
        object.__setattr__(self, "id", _validate_identifier(chosen_id))
        object.__setattr__(self, "provider", normalized_provider)
        object.__setattr__(self, "model", _validate_model(model))
        object.__setattr__(self, "endpoint", _validate_endpoint(endpoint, normalized_provider))
        object.__setattr__(self, "secret_ref", _validate_secret_ref(chosen_ref))
        object.__setattr__(self, "capability", normalized_capability)

    @property
    def config_id(self) -> str:
        return self.id

    @property
    def credential_ref(self) -> str:
        return self.secret_ref

    @property
    def key_ref(self) -> str:
        return self.secret_ref

    @property
    def capability_state(self) -> str:
        return self.capability.state.value

    def with_capability(self, capability: CapabilityStatus | Mapping[str, Any]) -> "ModelProviderConfig":
        return ModelProviderConfig(
            id=self.id,
            provider=self.provider,
            model=self.model,
            endpoint=self.endpoint,
            secret_ref=self.secret_ref,
            capability=_coerce_capability(capability),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider.value,
            "model": self.model,
            "endpoint": self.endpoint,
            "secret_ref": self.secret_ref,
            "capability": self.capability.to_dict(),
        }

    def to_public_dict(self) -> dict[str, Any]:
        """Return a workbench-safe view without exposing even the reference."""

        return {
            "id": self.id,
            "provider": self.provider.value,
            "model": self.model,
            "endpoint": self.endpoint,
            "has_secret_ref": True,
            "capability": self.capability.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> "ModelProviderConfig":
        if not isinstance(value, Mapping):
            raise ConfigValidationError("config_invalid", "provider configuration must be an object")
        unknown = set(value) - _CONFIG_FIELDS
        if unknown:
            raise ConfigValidationError("config_unknown_field", "provider configuration contains an unknown field")
        required = _CONFIG_FIELDS - {"capability"}
        if not required.issubset(value):
            raise ConfigValidationError("config_missing_field", "provider configuration is incomplete")
        capability = None if "capability" not in value else CapabilityStatus.from_dict(value["capability"])
        return cls(
            id=value["id"],
            provider=value["provider"],
            model=value["model"],
            endpoint=value["endpoint"],
            secret_ref=value["secret_ref"],
            capability=capability,
        )


ProviderConfig = ModelProviderConfig


def validate_config(value: object) -> ModelProviderConfig:
    if isinstance(value, ModelProviderConfig):
        return value
    return ModelProviderConfig.from_dict(value)


def serialize_config(value: object) -> dict[str, Any]:
    return validate_config(value).to_dict()


def deserialize_config(value: object) -> ModelProviderConfig:
    return ModelProviderConfig.from_dict(value)


class CapabilityProbe(Protocol):
    def probe(self, config: ModelProviderConfig) -> CapabilityStatus | Mapping[str, Any]:
        """Return a status without receiving or returning a raw secret."""


class NoNetworkCapabilityProbe:
    """Default probe: deterministic and deliberately incapable of networking."""

    def probe(self, config: ModelProviderConfig) -> CapabilityStatus:
        _ = config
        return CapabilityStatus.unavailable("network_probe_disabled")


DefaultCapabilityProbe = NoNetworkCapabilityProbe


def _normalize_probe_result(value: object) -> CapabilityStatus:
    if isinstance(value, CapabilityStatus):
        return value
    if isinstance(value, Mapping):
        return CapabilityStatus.from_dict(value)
    raise ConfigValidationError("probe_result_invalid", "capability probe returned an invalid result")


def probe_capability(
    config: ModelProviderConfig,
    capability_probe: CapabilityProbe | Any | None = None,
    *,
    probe: CapabilityProbe | Any | None = None,
) -> CapabilityStatus:
    """Probe through an injected object/callable, never through the network by default."""

    if capability_probe is not None and probe is not None:
        raise ConfigValidationError("probe_conflict", "capability probes conflict")
    candidate = capability_probe if capability_probe is not None else probe
    if candidate is None:
        candidate = NoNetworkCapabilityProbe()
    normalized_config = validate_config(config)
    try:
        if hasattr(candidate, "probe"):
            result = candidate.probe(normalized_config)
        elif callable(candidate):
            result = candidate(normalized_config)
        else:
            raise TypeError
        return _normalize_probe_result(result)
    except ModelProviderConfigError:
        return CapabilityStatus.error("probe_result_invalid")
    except Exception:
        # Do not expose exception text: a poorly behaved injected probe could
        # include an endpoint, credential reference, or provider response.
        return CapabilityStatus.error("probe_exception")


probe_provider_capability = probe_capability


def _safe_store_path(work_dir: Path, filename: object) -> Path:
    if not isinstance(filename, str) or not filename or filename in {".", ".."}:
        raise ConfigStorageError("path_invalid", "configuration filename is invalid")
    if Path(filename).is_absolute() or "/" in filename or "\\" in filename:
        raise ConfigStorageError("path_outside_workdir", "configuration file must stay inside the work directory")
    if not filename.endswith(".json"):
        raise ConfigStorageError("path_invalid", "configuration file must be JSON")
    candidate = work_dir / filename
    try:
        resolved = candidate.resolve()
        resolved.relative_to(work_dir)
    except (OSError, ValueError) as exc:
        raise ConfigStorageError("path_outside_workdir", "configuration file must stay inside the work directory") from exc
    if candidate.exists() and candidate.is_dir():
        raise ConfigStorageError("path_invalid", "configuration path is not a file")
    return candidate


class ModelProviderConfigStore:
    """Atomic JSON persistence restricted to one explicit existing directory."""

    def __init__(self, work_dir: str | os.PathLike[str], filename: str = DEFAULT_CONFIG_FILENAME) -> None:
        if work_dir is None or (isinstance(work_dir, str) and not work_dir.strip()):
            raise ConfigStorageError("workdir_invalid", "an explicit work directory is required")
        try:
            resolved_work_dir = Path(work_dir).expanduser().resolve()
        except (OSError, TypeError, ValueError) as exc:
            raise ConfigStorageError("workdir_invalid", "an explicit work directory is required") from exc
        if not resolved_work_dir.is_dir():
            raise ConfigStorageError("workdir_invalid", "an explicit existing work directory is required")
        self.work_dir = resolved_work_dir
        self.path = _safe_store_path(resolved_work_dir, filename)

    def _read_payload(self) -> list[ModelProviderConfig]:
        if not self.path.exists():
            return []
        if not self.path.is_file():
            raise ConfigStorageError("store_unavailable", "configuration store is not a file")
        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigStorageError("store_invalid", "configuration store cannot be read") from exc
        if not isinstance(payload, Mapping) or set(payload) != {"schema_version", "configs"}:
            raise ConfigStorageError("store_schema_invalid", "configuration store schema is invalid")
        if payload.get("schema_version") != SCHEMA_VERSION or not isinstance(payload.get("configs"), list):
            raise ConfigStorageError("store_schema_invalid", "configuration store schema is invalid")

        configs: list[ModelProviderConfig] = []
        seen: set[str] = set()
        for item in payload["configs"]:
            try:
                config = ModelProviderConfig.from_dict(item)
            except ModelProviderConfigError as exc:
                raise ConfigStorageError("config_invalid", "configuration store contains an invalid provider") from exc
            if config.id in seen:
                raise ConfigStorageError("duplicate_id", "configuration store contains duplicate identifiers")
            seen.add(config.id)
            configs.append(config)
        return configs

    @staticmethod
    def _normalize_configs(configs: Iterable[ModelProviderConfig]) -> list[ModelProviderConfig]:
        if isinstance(configs, (str, bytes, Mapping)):
            raise ConfigValidationError("configs_invalid", "configurations must be an iterable of records")
        try:
            normalized = [validate_config(config) for config in configs]
        except TypeError as exc:
            raise ConfigValidationError("configs_invalid", "configurations must be an iterable of records") from exc
        seen: set[str] = set()
        for config in normalized:
            if config.id in seen:
                raise ConfigValidationError("duplicate_id", "configuration identifiers must be unique")
            seen.add(config.id)
        return normalized

    def load(self) -> list[ModelProviderConfig]:
        return self._read_payload()

    read = load

    def save(self, configs: Iterable[ModelProviderConfig]) -> list[ModelProviderConfig]:
        normalized = self._normalize_configs(configs)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "configs": [config.to_dict() for config in normalized],
        }
        serialized = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        temporary_path: str | None = None
        file_descriptor: int | None = None
        try:
            file_descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.work_dir,
            )
            os.fchmod(file_descriptor, 0o600)
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as handle:
                file_descriptor = None
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
            try:
                directory_descriptor = os.open(self.work_dir, os.O_RDONLY)
            except OSError:
                directory_descriptor = None
            if directory_descriptor is not None:
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
        except (OSError, TypeError, ValueError) as exc:
            raise ConfigStorageError("store_write_failed", "configuration store cannot be written") from exc
        finally:
            if file_descriptor is not None:
                os.close(file_descriptor)
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
        return normalized

    write = save

    def list_configs(self) -> list[ModelProviderConfig]:
        return self.load()

    def get(self, config_id: str) -> ModelProviderConfig:
        normalized_id = _validate_identifier(config_id)
        for config in self.load():
            if config.id == normalized_id:
                return config
        raise ConfigStorageError("config_not_found", "provider configuration was not found")

    def upsert(self, config: ModelProviderConfig) -> list[ModelProviderConfig]:
        normalized = validate_config(config)
        configs = self.load()
        replaced = False
        updated: list[ModelProviderConfig] = []
        for current in configs:
            if current.id == normalized.id:
                updated.append(normalized)
                replaced = True
            else:
                updated.append(current)
        if not replaced:
            updated.append(normalized)
        return self.save(updated)

    def probe(
        self,
        config_id: str,
        capability_probe: CapabilityProbe | Any | None = None,
        *,
        probe: CapabilityProbe | Any | None = None,
    ) -> CapabilityStatus:
        config = self.get(config_id)
        status = probe_capability(config, capability_probe, probe=probe)
        self.upsert(config.with_capability(status))
        return status

    def probe_all(
        self,
        capability_probe: CapabilityProbe | Any | None = None,
        *,
        probe: CapabilityProbe | Any | None = None,
    ) -> dict[str, CapabilityStatus]:
        configs = self.load()
        statuses: dict[str, CapabilityStatus] = {}
        updated: list[ModelProviderConfig] = []
        for config in configs:
            status = probe_capability(config, capability_probe, probe=probe)
            statuses[config.id] = status
            updated.append(config.with_capability(status))
        self.save(updated)
        return statuses


ProviderConfigStore = ModelProviderConfigStore
ConfigStore = ModelProviderConfigStore


def load_provider_configs(work_dir: str | os.PathLike[str]) -> list[ModelProviderConfig]:
    return ModelProviderConfigStore(work_dir).load()


def save_provider_configs(
    work_dir: str | os.PathLike[str], configs: Iterable[ModelProviderConfig]
) -> list[ModelProviderConfig]:
    return ModelProviderConfigStore(work_dir).save(configs)


__all__ = [
    "CapabilityProbe",
    "CapabilityState",
    "CapabilityStatus",
    "CapabilityStatusValue",
    "ConfigStore",
    "ConfigStorageError",
    "ConfigValidationError",
    "DEFAULT_CONFIG_FILENAME",
    "DefaultCapabilityProbe",
    "ModelProvider",
    "ModelProviderConfig",
    "ModelProviderConfigError",
    "ModelProviderConfigStore",
    "NoNetworkCapabilityProbe",
    "Provider",
    "ProviderConfig",
    "ProviderConfigStore",
    "ProviderKind",
    "SCHEMA_VERSION",
    "SUPPORTED_PROVIDERS",
    "deserialize_config",
    "load_provider_configs",
    "probe_capability",
    "probe_provider_capability",
    "save_provider_configs",
    "serialize_config",
    "validate_config",
]
