from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_state_transition.py"
VAULT_RULES = Path("/Users/vsiyo/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体/00_入口与总览/state_transition_rules.yaml")

# 本机 vault 缺失时（CI 容器、他人机器）合成与 vault 合同同构的最小规则，
# 只覆盖本文件断言的两条迁移；vault 存在时仍然直接校验真实规则文件。
FALLBACK_RULES_TEXT = """\
project_statuses:
  - planned
  - edit_ready
  - final_ready
  - published
transitions:
  planned_to_edit_ready:
    from: planned
    to: edit_ready
    allowed_actor: cloud_openclaw
    required_evidence:
      - result_identity_valid
      - selected_editor_backend_result_valid
  final_ready_to_published:
    from: final_ready
    to: published
    allowed_actor: human
    required_evidence:
      - human_published_confirmation
"""


class StateTransitionV2Tests(unittest.TestCase):
    def rules_path(self, root: Path) -> Path:
        if VAULT_RULES.exists():
            return VAULT_RULES
        path = root / "state_transition_rules.yaml"
        if not path.exists():
            path.write_text(FALLBACK_RULES_TEXT, encoding="utf-8")
        return path

    def run_validator(
        self,
        project: Path,
        *extra: str,
        expected: int = 0,
        from_status: str = "planned",
        to_status: str = "edit_ready",
        actor: str = "cloud_openclaw",
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable, str(SCRIPT), "--vault-root", str(project.parent),
            "--project-index", str(project / "00_项目总览.md"), "--rules", str(self.rules_path(project.parent)),
            "--from", from_status, "--to", to_status, "--actor", actor, *extra,
        ]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return completed

    def write_project(self, root: Path, *, revision: int = 3, backend: str = "handoff_pack") -> Path:
        project = root / "demo"
        project.mkdir()
        (project / "00_项目总览.md").write_text(
            "---\nproject_id: demo\nstatus: planned\nproject_revision: " + str(revision) + "\neditor_backend: " + backend + "\n---\n# 项目\n",
            encoding="utf-8",
        )
        (project / "05_storyboard.md").write_text("# 分镜\n", encoding="utf-8")
        (project / "06_edit_decision_list.json").write_text("{}\n", encoding="utf-8")
        return project

    def write_result(self, root: Path, *, revision: int = 3, backend: str = "handoff_pack") -> Path:
        result = root / "result.yaml"
        result.write_text(
            "status: done\nproject_id: demo\nproject_revision: " + str(revision) + "\neditor_backend: " + backend + "\n",
            encoding="utf-8",
        )
        return result

    def test_accepts_matching_result_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.write_project(root)
            result = self.write_result(root)
            completed = self.run_validator(project, "--evidence", str(result))
            self.assertIn("status: valid", completed.stdout)

    def test_blocks_stale_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.write_project(root)
            result = self.write_result(root, revision=2)
            completed = self.run_validator(project, "--evidence", str(result), expected=1)
            self.assertIn("current project id, revision", completed.stderr)

    def test_blocks_backend_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.write_project(root, backend="otio_kdenlive")
            result = self.write_result(root, backend="handoff_pack")
            completed = self.run_validator(project, "--evidence", str(result), expected=1)
            self.assertIn("selected editor backend", completed.stderr)

    def test_publish_accepts_recorded_human_confirmation_without_post_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.write_project(root)
            overview = project / "00_项目总览.md"
            overview.write_text(
                overview.read_text(encoding="utf-8")
                .replace("status: planned", "status: final_ready")
                .replace("editor_backend: handoff_pack", "editor_backend: handoff_pack\npublication_confirmed_at: 2026-07-11\npublication_confirmed_by: 负责人"),
                encoding="utf-8",
            )
            completed = self.run_validator(
                project,
                "--human-confirmed",
                from_status="final_ready",
                to_status="published",
                actor="human",
            )
            self.assertIn("status: valid", completed.stdout)

    def test_publish_requires_a_recorded_human_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = self.write_project(root)
            overview = project / "00_项目总览.md"
            overview.write_text(
                overview.read_text(encoding="utf-8").replace("status: planned", "status: final_ready"),
                encoding="utf-8",
            )
            completed = self.run_validator(
                project,
                "--human-confirmed",
                expected=1,
                from_status="final_ready",
                to_status="published",
                actor="human",
            )
            self.assertIn("publication_confirmed_at is empty", completed.stderr)


if __name__ == "__main__":
    unittest.main()
