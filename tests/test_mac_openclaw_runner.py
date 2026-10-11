#!/usr/bin/env python3
"""Tests for the strict Mac OpenClaw runner helpers."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mac_openclaw_runner as runner  # noqa: E402


class MacOpenClawRunnerTest(unittest.TestCase):
    def test_result_path_keeps_task_filename_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            config = runner.RunnerConfig(vault_root=vault, workspace_root=ROOT)
            task_path = vault / "98_Agent任务队列/01_cloud_to_mac_ready/task_20260520_001_material_match.yaml"
            task = {"task_id": "task_20260520_001", "task_type": "local_material_match"}

            result = runner.result_path_for(config, task_path, task)

            self.assertEqual(result.name, "result_20260520_001_material_match.yaml")
            self.assertEqual(result.parent, vault / "98_Agent任务队列/02_mac_to_cloud_results")

    def test_expected_output_resolves_vault_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            config = runner.RunnerConfig(vault_root=vault, workspace_root=ROOT)
            task = {
                "expected_outputs": [
                    "08_内容项目/project/03_material_match_report.md",
                    "08_内容项目/project/06_edit_decision_list.json",
                ]
            }

            output = runner.expected_output(config, task, "06_edit_decision_list.json")

            self.assertEqual(output, vault / "08_内容项目/project/06_edit_decision_list.json")

    def test_required_action_guard_blocks_partial_task(self) -> None:
        task = {"task_type": "local_material_match"}

        with self.assertRaises(runner.RunnerError):
            runner.validate_required_actions(task, ["analyze_project"])

    def test_generate_ai_edit_log_requires_canonical_action(self) -> None:
        task = {"task_type": "generate_ai_edit_log"}

        runner.validate_required_actions(task, ["generate_ai_edit_log"])
        with self.assertRaises(runner.RunnerError):
            runner.validate_required_actions(task, ["generate_import_readme"])

    def test_local_output_review_requires_review_action(self) -> None:
        task = {"task_type": "local_output_review"}

        runner.validate_required_actions(task, ["review_output_video"])
        with self.assertRaises(runner.RunnerError):
            runner.validate_required_actions(task, ["generate_ai_edit_log"])

    def test_local_project_path_resolves_hint_under_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            project = workspace / "01_Project_Workspace/theme/20260520_400米比赛_第一视角"
            project.mkdir(parents=True)
            config = runner.RunnerConfig(vault_root=Path(tmp) / "vault", workspace_root=workspace)
            task = {
                "project_id": "20260520_400米比赛_第一视角",
                "inputs": {"local_project_hint": "20260520_400米比赛_第一视角"},
            }

            self.assertEqual(runner.local_project_path(config, task), project.resolve())

    def test_content_os_link_validates_batch_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            vault = root / "vault"
            project = workspace / "01_Project_Workspace/theme/20260626_测试项目"
            project.mkdir(parents=True)
            link = root / "batch/_ai_analysis/content_os_link.yaml"
            link.parent.mkdir(parents=True)
            link.write_text(
                yaml.safe_dump(
                    {
                        "doc_type": "content_os_link",
                        "status": "brief_ready",
                        "obsidian": {"project_id": "20260626_测试项目"},
                        "validation": {"missing_required_files": []},
                        "batch": {"target_project_resolved": str(project)},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            config = runner.RunnerConfig(vault_root=vault, workspace_root=workspace)
            task = {
                "project_id": "20260626_测试项目",
                "inputs": {"content_os_link_path": str(link)},
            }

            self.assertEqual(runner.validate_content_os_link(config, task, project), link.resolve())

    def test_content_os_link_rejects_project_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            vault = root / "vault"
            project = workspace / "01_Project_Workspace/theme/20260626_测试项目"
            project.mkdir(parents=True)
            link = root / "batch/_ai_analysis/content_os_link.yaml"
            link.parent.mkdir(parents=True)
            link.write_text(
                yaml.safe_dump(
                    {
                        "doc_type": "content_os_link",
                        "status": "brief_ready",
                        "obsidian": {"project_id": "other_project"},
                        "validation": {"missing_required_files": []},
                        "batch": {"target_project_resolved": str(project)},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            config = runner.RunnerConfig(vault_root=vault, workspace_root=workspace)
            task = {
                "project_id": "20260626_测试项目",
                "inputs": {"content_os_link_path": str(link)},
            }

            with self.assertRaises(runner.RunnerError):
                runner.validate_content_os_link(config, task, project)


if __name__ == "__main__":
    unittest.main()
