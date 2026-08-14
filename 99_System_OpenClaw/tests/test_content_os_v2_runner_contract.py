#!/usr/bin/env python3
"""Regression tests for Content OS v0.2 Mac task identity and dispatch guards."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mac_openclaw_runner as runner  # noqa: E402
import validate_content_os_task as task_validator  # noqa: E402


PROJECT_ID = "project_v2_test"
CHANGE_ID = "change_20260710_001"


def capabilities() -> dict:
    return {
        "editor_backends": {
            "supported": {
                "handoff_pack": {"implemented": True},
                "otio_kdenlive": {"implemented": True},
            }
        },
        "supported_actions": {
            "apply_confirmed_revision": {"implemented": True},
            "generate_edit_handoff_pack": {"implemented": True},
            "validate_edit_handoff_pack": {"implemented": True},
            "generate_otio_timeline": {"implemented": True},
            "create_kdenlive_timeline": {"implemented": True},
            "validate_kdenlive_timeline": {"implemented": True},
            "analyze_project": {"implemented": True},
            "match_materials_to_brief": {"implemented": True},
            "generate_storyboard_edl": {"implemented": True},
            "write_local_assets": {"implemented": True},
            "review_output_video": {"implemented": True},
            "generate_ai_edit_log": {"implemented": True},
        },
    }


class ContentOsV2RunnerContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.vault = self.root / "vault"
        self.project_dir = self.vault / "08_内容项目" / PROJECT_ID
        self.project_dir.mkdir(parents=True)
        (self.project_dir / "output").mkdir()
        (self.project_dir / "00_项目总览.md").write_text(
            "---\n"
            "spec_version: content_os_v0.2\n"
            f"project_id: {PROJECT_ID}\n"
            "status: editing\n"
            "project_revision: 3\n"
            "editor_backend: handoff_pack\n"
            "---\n\n# 项目\n",
            encoding="utf-8",
        )
        self.change_dir = self.vault / "98_Agent任务队列" / "00_change_requests"
        self.change_dir.mkdir(parents=True)
        self.write_change_request()
        self.capabilities = capabilities()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_change_request(self, **overrides: object) -> None:
        data: dict[str, object] = {
            "spec_version": "content_os_v0.2",
            "doc_type": "content_revision_request",
            "change_id": CHANGE_ID,
            "project_id": PROJECT_ID,
            "base_revision": 2,
            "target_revision": 3,
            "request_status": "executing",
            "execution_intent": "execute_now",
            "assigned_owner": "mac_openclaw",
            "execution_confirmed_at": "2026-07-10T12:00:00+08:00",
        }
        data.update(overrides)
        (self.change_dir / f"{CHANGE_ID}.yaml").write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )

    def task(self, **overrides: object) -> dict:
        data: dict[str, object] = {
            "spec_version": "content_os_v0.2",
            "task_id": "task_20260710_001",
            "task_type": "revise_local_edit_artifacts",
            "project_id": PROJECT_ID,
            "project_revision": 3,
            "change_request_id": CHANGE_ID,
            "editor_backend": "handoff_pack",
            "human_confirmed_impact": True,
            "idea_id": "idea_001",
            "owner": "mac_openclaw",
            "status": "ready",
            "inputs": {},
            "expected_outputs": [f"08_内容项目/{PROJECT_ID}/output/result.md"],
            "allowed_actions": ["apply_confirmed_revision"],
        }
        data.update(overrides)
        return data

    def test_accepts_confirmed_current_revision_with_matching_backend(self) -> None:
        summary = task_validator.validate_task(self.task(), self.capabilities, self.vault)

        self.assertEqual(summary["project_revision"], 3)
        self.assertEqual(summary["change_request_id"], CHANGE_ID)
        self.assertEqual(summary["editor_backend"], "handoff_pack")

    def test_blocks_stale_revision_before_mac_can_write(self) -> None:
        with self.assertRaisesRegex(task_validator.ValidationError, "stale project_revision"):
            task_validator.validate_task(self.task(project_revision=2), self.capabilities, self.vault)

    def test_blocks_change_request_owned_by_cloud(self) -> None:
        self.write_change_request(assigned_owner="cloud_openclaw")

        with self.assertRaisesRegex(task_validator.ValidationError, "not assigned to mac_openclaw"):
            task_validator.validate_task(self.task(), self.capabilities, self.vault)

    def test_blocks_unknown_backend_even_if_overview_matches_it(self) -> None:
        overview = self.project_dir / "00_项目总览.md"
        overview.write_text(
            overview.read_text(encoding="utf-8").replace("handoff_pack", "unknown_backend"), encoding="utf-8"
        )

        with self.assertRaisesRegex(task_validator.ValidationError, "unknown editor_backend"):
            task_validator.validate_task(self.task(editor_backend="unknown_backend"), self.capabilities, self.vault)

    def test_blocks_unknown_action_and_backend_fallback(self) -> None:
        with self.assertRaisesRegex(task_validator.ValidationError, "unsupported action"):
            task_validator.validate_task(self.task(allowed_actions=["invent_a_shell_command"]), self.capabilities, self.vault)
        with self.assertRaisesRegex(task_validator.ValidationError, "fallback fields are forbidden"):
            task_validator.validate_task(self.task(fallback_editor_backend="otio_kdenlive"), self.capabilities, self.vault)

    def test_result_identity_and_revision_invalidation_are_not_optional(self) -> None:
        task = self.task(inputs={"invalidated_artifacts": ["06_edit_decision_list.json"]})

        self.assertEqual(
            runner.task_identity(task),
            {
                "spec_version": "content_os_v0.2",
                "task_id": "task_20260710_001",
                "task_type": "revise_local_edit_artifacts",
                "completed_by": "mac_openclaw",
                "project_id": PROJECT_ID,
                "project_revision": 3,
                "change_request_id": CHANGE_ID,
                "editor_backend": "handoff_pack",
            },
        )
        self.assertEqual(
            runner.revision_invalidation(task),
            {
                "superseded_revision": 2,
                "superseded_artifacts": ["06_edit_decision_list.json"],
                "preserved_for_comparison": True,
            },
        )

    def test_backend_result_identity_mismatch_is_blocked(self) -> None:
        result = self.root / "backend-result.json"
        result.write_text(
            json.dumps(
                {
                    "spec_version": "content_os_v0.2",
                    "doc_type": "edit_handoff_manifest",
                    "project_id": PROJECT_ID,
                    "project_revision": 2,
                    "editor_backend": "handoff_pack",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(runner.RunnerError, "project_revision"):
            runner.require_json_identity(result, self.task(), "edit_handoff_manifest")

    def test_runner_has_no_legacy_native_draft_dispatch_or_fallback(self) -> None:
        self.assertNotIn("create_jianying_native_import_pack", runner.REQUIRED_ACTIONS)
        config = runner.RunnerConfig(vault_root=self.vault, workspace_root=self.root)
        invalid_backend_task = self.task(editor_backend="unexpected")
        with self.assertRaisesRegex(runner.RunnerError, "no fallback"):
            runner.run_revision_task(config, invalid_backend_task, self.root / "result.yaml", execute=False)

    def test_runner_executes_only_selected_handoff_backend_and_writes_identity(self) -> None:
        local_project = self.root / "local-project"
        local_project.mkdir()
        media = local_project / "clip.mp4"
        media.write_bytes(b"fixture-media")
        edl = self.project_dir / "06_edit_decision_list.json"
        edl.write_text(
            json.dumps(
                {
                    "doc_type": "edit_decision_list",
                    "project_id": PROJECT_ID,
                    "clips": [
                        {
                            "slot": 1,
                            "time_range": "0s-1s",
                            "candidate_files": [str(media)],
                            "caption": "测试字幕",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        storyboard = self.project_dir / "05_storyboard.md"
        storyboard.write_text("# Storyboard\n", encoding="utf-8")
        handoff_task = self.task(
            task_type="generate_edit_handoff_pack",
            change_request_id="",
            inputs={
                "edl_path": f"08_内容项目/{PROJECT_ID}/06_edit_decision_list.json",
                "storyboard_path": f"08_内容项目/{PROJECT_ID}/05_storyboard.md",
                "local_project_path": str(local_project),
            },
            expected_outputs=["90_Draft_Project/edit_handoff/3/manifest.json"],
            allowed_actions=["generate_edit_handoff_pack", "validate_edit_handoff_pack"],
        )
        inbox = self.vault / "98_Agent任务队列" / "01_cloud_to_mac_ready"
        inbox.mkdir(parents=True)
        task_path = inbox / "task_20260710_001_handoff.yaml"
        task_path.write_text(yaml.safe_dump(handoff_task, allow_unicode=True, sort_keys=False), encoding="utf-8")
        capabilities_path = self.vault / "00_入口与总览" / "mac_runner_capabilities.yaml"
        capabilities_path.parent.mkdir(parents=True)
        capabilities_path.write_text(yaml.safe_dump(self.capabilities, allow_unicode=True, sort_keys=False), encoding="utf-8")
        config = runner.RunnerConfig(vault_root=self.vault, workspace_root=self.root)

        result_path = runner.run_task(
            config,
            str(task_path),
            execute=True,
            allow_replace_result=False,
            allow_replace_generated=False,
            skip_runtime_check=True,
            skip_analyze=True,
        )

        result = yaml.safe_load(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["project_revision"], 3)
        self.assertEqual(result["editor_backend"], "handoff_pack")
        self.assertFalse(result["fallback_used"])
        self.assertTrue(Path(result["outputs"]["handoff_manifest"]).is_file())

    def test_otio_runner_uses_fixed_venv_from_regular_python(self) -> None:
        local_project = self.root / "local-project-otio"
        local_project.mkdir()
        edl = self.project_dir / "06_edit_decision_list.json"
        edl.write_text(
            json.dumps(
                {
                    "doc_type": "edit_decision_list",
                    "project_id": PROJECT_ID,
                    "clips": [
                        {
                            "slot": 1,
                            "time_range": "0-1s",
                            "candidate_files": ["缺失素材.mp4"],
                            "caption": "时间线字幕",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        storyboard = self.project_dir / "05_storyboard.md"
        storyboard.write_text("# Storyboard\n", encoding="utf-8")
        overview = self.project_dir / "00_项目总览.md"
        overview.write_text(
            overview.read_text(encoding="utf-8").replace("handoff_pack", "otio_kdenlive"), encoding="utf-8"
        )
        otio_task = self.task(
            task_type="generate_otio_kdenlive_timeline",
            change_request_id="",
            editor_backend="otio_kdenlive",
            inputs={
                "edl_path": f"08_内容项目/{PROJECT_ID}/06_edit_decision_list.json",
                "storyboard_path": f"08_内容项目/{PROJECT_ID}/05_storyboard.md",
                "local_project_path": str(local_project),
            },
            expected_outputs=["90_Draft_Project/edit_handoff/3/timeline.otio"],
            allowed_actions=["generate_otio_timeline", "create_kdenlive_timeline", "validate_kdenlive_timeline"],
        )
        inbox = self.vault / "98_Agent任务队列" / "01_cloud_to_mac_ready"
        inbox.mkdir(parents=True)
        task_path = inbox / "task_20260710_002_otio.yaml"
        task_path.write_text(yaml.safe_dump(otio_task, allow_unicode=True, sort_keys=False), encoding="utf-8")
        capabilities_path = self.vault / "00_入口与总览" / "mac_runner_capabilities.yaml"
        capabilities_path.parent.mkdir(parents=True)
        capabilities_path.write_text(yaml.safe_dump(self.capabilities, allow_unicode=True, sort_keys=False), encoding="utf-8")
        regular_python = Path("/opt/homebrew/bin/python3")
        self.assertTrue(regular_python.is_file())
        self.assertTrue(runner.OTIO_KDENLIVE_PYTHON.is_file())
        self.assertNotEqual(regular_python, runner.OTIO_KDENLIVE_PYTHON)
        regular_probe = subprocess.run(
            [str(regular_python), "-c", "import opentimelineio"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertNotEqual(regular_probe.returncode, 0)

        completed = subprocess.run(
            [
                str(regular_python),
                str(ROOT / "scripts" / "mac_openclaw_runner.py"),
                "--vault-root",
                str(self.vault),
                "--workspace-root",
                str(self.root),
                "run-task",
                str(task_path),
                "--skip-runtime-check",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result_path = self.vault / "98_Agent任务队列" / "02_mac_to_cloud_results" / "result_20260710_002_otio.yaml"
        result = yaml.safe_load(result_path.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["editor_backend"], "otio_kdenlive")
        self.assertTrue(Path(result["outputs"]["otio_timeline"]).is_file())

    def test_missing_fixed_otio_runtime_blocks_without_interpreter_fallback(self) -> None:
        original = runner.OTIO_KDENLIVE_PYTHON
        runner.OTIO_KDENLIVE_PYTHON = self.root / "missing-otio-runtime"
        try:
            with self.assertRaisesRegex(runner.RunnerError, "no fallback backend"):
                runner.otio_kdenlive_python()
        finally:
            runner.OTIO_KDENLIVE_PYTHON = original


if __name__ == "__main__":
    unittest.main()
