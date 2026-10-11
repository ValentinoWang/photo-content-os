"""Wave 6 regression gates for the Photo Content OS bridge boundary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import load_script


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mac_openclaw_runner as runner  # noqa: E402
import openclaw_product_contract as contract  # noqa: E402
import validate_content_os_task as validator  # noqa: E402
from llm_common import REQUIRED_CREATIVE_MODEL, REQUIRED_CREATIVE_REASONING  # noqa: E402


refresh = load_script("refresh_openclaw_media_contract_snapshot.py", "wave6_snapshot_refresh", register=True)


class Wave6BridgeContractTests(unittest.TestCase):
    def test_runner_uses_shared_creative_contract_constants(self) -> None:
        self.assertEqual(runner.REQUIRED_CREATIVE_MODEL, REQUIRED_CREATIVE_MODEL)
        self.assertEqual(runner.REQUIRED_CREATIVE_REASONING, REQUIRED_CREATIVE_REASONING)
        payload = {"task_id": "task_20260829_003", "project_revision": 4}
        self.assertEqual(runner.request_fingerprint(payload), validator.request_fingerprint(payload))

    def test_local_material_match_uses_one_declared_model_for_analysis_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            vault = root / "vault"
            package = vault / "08_内容项目" / "project"
            package.mkdir(parents=True)
            for filename in ("02_project_brief.md", "04_script.md"):
                (package / filename).write_text("content", encoding="utf-8")
            for filename in (
                "03_material_match_report.md",
                "05_storyboard.md",
                "06_edit_decision_list.json",
                "08_local_assets.md",
            ):
                (package / filename).write_text("{}" if filename.endswith(".json") else "content", encoding="utf-8")
            task = {
                "task_id": "task_20260829_001",
                "project_id": "project",
                "inputs": {"local_project_path": str(project)},
                "expected_outputs": [str((package / filename).relative_to(vault)) for filename in (
                    "03_material_match_report.md",
                    "05_storyboard.md",
                    "06_edit_decision_list.json",
                    "08_local_assets.md",
                )],
            }
            config = runner.RunnerConfig(vault_root=vault, workspace_root=root)

            with patch.object(runner, "validate_content_os_link", return_value=None), patch.object(
                runner, "local_material_match_result"
            ), patch.object(runner, "run_command") as run_command, patch.object(
                runner, "write_local_assets"
            ):
                runner.run_local_material_match(config, task, root / "result.yaml", execute=True, skip_analyze=False)

            analysis_args = run_command.call_args_list[0].args[0]
            self.assertEqual(analysis_args[0], "bash")
            self.assertEqual(analysis_args[analysis_args.index("--model") + 1], runner.REQUIRED_CREATIVE_MODEL)
            self.assertEqual(analysis_args[analysis_args.index("--reasoning") + 1], runner.REQUIRED_CREATIVE_REASONING)

    def test_blocked_result_keeps_bridge_identity_and_retry_can_replace_it(self) -> None:
        task = {
            "task_id": "task_20260829_002",
            "task_type": "local_material_match",
            "project_id": "project",
            "idea_id": "idea_20260829_002",
            "project_revision": 4,
            "editor_backend": "handoff_pack",
            "idempotency_key": "retry-key",
        }
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.yaml"
            validator.write_blocked_result(result_path, task, "invalid task")
            blocked = runner.load_yaml(result_path)

        self.assertEqual(blocked["doc_type"], "mac_result")
        self.assertEqual(blocked["task_id"], task["task_id"])
        self.assertEqual(blocked["idea_id"], task["idea_id"])
        self.assertEqual(blocked["idempotency_key"], "retry-key")
        self.assertTrue(blocked["request_fingerprint"].startswith("sha256:"))

        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.yaml"
            runner.write_execution_blocked_result(result_path, task, "runtime unavailable")
            with patch.object(runner, "resolve_task_ref", return_value=Path(directory) / "task.yaml"), patch.object(
                runner, "validate_or_block", return_value=(task, result_path, [])
            ), patch.object(runner, "run_local_material_match") as run_local_material_match:
                runner.run_task(
                    runner.RunnerConfig(vault_root=Path(directory), workspace_root=Path(directory)),
                    "task_20260829_002",
                    execute=False,
                    allow_replace_result=False,
                    allow_replace_generated=False,
                    skip_runtime_check=False,
                    skip_analyze=False,
                )

            self.assertTrue(run_local_material_match.called)
            self.assertFalse(result_path.exists())

    def test_snapshot_refresh_rebuilds_candidate_without_mutating_pin_until_approved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = root / "upstream"
            catalog_path = upstream / refresh.CATALOG_RELATIVE_PATH
            catalog_path.parent.mkdir(parents=True)
            pipelines = [
                {"pipeline_id": pipeline_id, "version": "1.0.0"}
                for pipeline_id in refresh.PIPELINE_ALIASES.values()
            ]
            digest = refresh.catalog_digest(pipelines)
            for pipeline in pipelines:
                pipeline["catalog_digest"] = digest
            catalog_path.write_text(
                json.dumps(
                    {
                        "contract_id": "openclaw_media_product_v1",
                        "contract_version": 1,
                        "catalog_digest": digest,
                        "pipeline_count": len(pipelines),
                        "pipelines": pipelines,
                    }
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "init", str(upstream)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "-C", str(upstream), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "-C", str(upstream), "-c", "user.name=Wave6", "-c", "user.email=wave6@example.test", "commit", "-m", "catalog"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            snapshot_path = root / "snapshot.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "schema_version": "photo_content_os_openclaw_bridge_v1",
                        "upstream_repository": "ValentinoWang/openclaw-media",
                        "upstream_commit": "0" * 40,
                        "upstream_contract_id": "openclaw_media_product_v1",
                        "upstream_contract_version": 1,
                        "catalog_digest": "sha256:" + "0" * 64,
                        "api_base": "/openclaw/media/api",
                        "supported_device_platforms": ["macos"],
                        "job_states": ["queued", "blocked"],
                        "pipelines": dict(refresh.PIPELINE_ALIASES),
                        "privacy": {"absolute_paths": "remove", "credentials": "remove", "raw_media_bytes": "local_only", "artifact_modes": ["content"]},
                    }
                ),
                encoding="utf-8",
            )
            before = snapshot_path.read_text(encoding="utf-8")

            candidate = refresh.regenerate_snapshot(upstream, snapshot_path=snapshot_path)

            self.assertEqual(snapshot_path.read_text(encoding="utf-8"), before)
            self.assertEqual(candidate["catalog_digest"], digest)
            self.assertEqual(candidate["upstream_commit"], subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip())
            contract.validate_snapshot(candidate)

            refresh.write_snapshot(snapshot_path, candidate)
            self.assertEqual(json.loads(snapshot_path.read_text(encoding="utf-8")), candidate)

            catalog_path.write_text(catalog_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(refresh.SnapshotRefreshError, "uncommitted changes"):
                refresh.regenerate_snapshot(upstream, snapshot_path=snapshot_path)


if __name__ == "__main__":
    unittest.main()
