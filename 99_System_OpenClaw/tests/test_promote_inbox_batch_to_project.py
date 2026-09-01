"""Regression coverage for inbox promotion using disposable filesystem fixtures."""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from _support import load_script


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
PROMOTE = load_script("35_promote_inbox_batch_to_project.py", "promote_inbox_batch_to_project")


class PromoteInboxBatchTests(unittest.TestCase):
    def test_promotes_only_temp_fixture_and_keeps_a_recovery_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            batch = workspace / "00_Inbox_Mac_Intake" / "2026-09-02_demo"
            project = workspace / "01_Project_Workspace" / "demo"
            batch.mkdir(parents=True)
            project.mkdir(parents=True)
            (batch / "clip.mp4").write_bytes(b"fixture-media")
            (batch / "00_批次说明.md").write_text("fixture", encoding="utf-8")
            (batch / "_ai_analysis").mkdir()
            (batch / "_ai_analysis" / "analysis.json").write_text("{}", encoding="utf-8")

            with patch.object(PROMOTE, "resolve_project_dir", return_value=(project, {"project_id": "demo"})):
                result = PROMOTE.promote_batch(batch, workspace)

            self.assertTrue(result["source_batch_removed"])
            self.assertFalse(batch.exists())
            self.assertEqual((project / "00_Inbox_待分类" / "clip.mp4").read_bytes(), b"fixture-media")
            self.assertTrue((project / "00_Inbox_待分类" / "00_批次说明.md").is_file())
            record = Path(result["promotion_record"])
            self.assertTrue(record.is_file())
            self.assertIn("source_batch_path", record.read_text(encoding="utf-8"))
            self.assertIn("Inbox 批次迁移", (project / "素材整理记录.md").read_text(encoding="utf-8"))

    def test_refuses_a_batch_outside_the_inbox_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            outside = workspace / "outside"
            outside.mkdir()
            with self.assertRaises(PROMOTE.PromoteError):
                PROMOTE.promote_batch(outside, workspace)


if __name__ == "__main__":
    unittest.main()
