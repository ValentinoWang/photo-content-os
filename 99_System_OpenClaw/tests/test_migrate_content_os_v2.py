from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "37_migrate_content_os_v2.py"


def write_project(vault: Path, name: str, status: str) -> Path:
    path = vault / "08_内容项目" / name
    path.mkdir(parents=True)
    overview = path / "00_项目总览.md"
    overview.write_text(
        f"---\nspec_version: content_os_v0.1\nproject_id: {name}\nstatus: {status}\nowner_agent: human\nnext_owner: human\n---\n\n# 项目\n",
        encoding="utf-8",
    )
    return overview


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text[4 : text.find("\n---", 4)])


class MigrateContentOsV2Tests(unittest.TestCase):
    def run_script(self, vault: Path, *, apply: bool, expected: int = 0) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--vault-root", str(vault), "--today", "2026-07-10"]
        if apply:
            command.append("--apply")
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return completed

    def test_dry_run_does_not_write_and_apply_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            old = write_project(vault, "old_project", "native_import_pack_ready")
            current = write_project(vault, "current_project", "editing")
            original = old.read_text(encoding="utf-8")
            self.run_script(vault, apply=False)
            self.assertEqual(old.read_text(encoding="utf-8"), original)
            self.run_script(vault, apply=True)
            old_data = frontmatter(old)
            current_data = frontmatter(current)
            self.assertEqual(old_data["status"], "planned")
            self.assertEqual(current_data["status"], "editing")
            self.assertEqual(old_data["doc_type"], "project_overview")
            self.assertEqual(old_data["project_revision"], 1)
            self.assertEqual(old_data["editor_backend"], "handoff_pack")
            self.assertEqual(old_data["migration_source_status"], "native_import_pack_ready")
            self.assertIn("旧剪映相关文件和旧任务仅作为历史证据保留", old.read_text(encoding="utf-8"))
            registry = (vault / "90_索引与注册表" / "project_registry.md").read_text(encoding="utf-8")
            self.assertIn("write_policy: generated_only", registry)
            self.assertIn("old_project", registry)
            self.run_script(vault, apply=True)
            self.assertEqual(frontmatter(old)["migration_source_status"], "native_import_pack_ready")

    def test_unknown_legacy_state_blocks_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            overview = write_project(vault, "bad_project", "surprise_state")
            original = overview.read_text(encoding="utf-8")
            completed = self.run_script(vault, apply=True, expected=1)
            self.assertIn("没有为旧项目阶段提供迁移映射", completed.stderr)
            self.assertEqual(overview.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
