"""Regression coverage for inbox promotion using disposable filesystem fixtures."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import load_script


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
PROMOTE = load_script("35_promote_inbox_batch_to_project.py", "promote_inbox_batch_to_project")


class PromoteInboxBatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.workspace = Path(self.temp_dir.name)
        self.project = self.workspace / "01_Project_Workspace" / "demo"
        self.project.mkdir(parents=True)

    def make_batch(self, *files: str) -> Path:
        batch = self.workspace / "00_Inbox_Mac_Intake" / "2026-09-02_demo"
        batch.mkdir(parents=True)
        for name in files:
            (batch / name).write_bytes(f"fixture-{name}".encode())
        return batch

    def resolved_project(self):
        return patch.object(
            PROMOTE,
            "resolve_project_dir",
            return_value=(self.project, {"project_id": "demo"}),
        )

    def test_promotes_only_temp_fixture_and_keeps_a_recovery_record(self) -> None:
        batch = self.make_batch("clip.mp4")
        (batch / "00_批次说明.md").write_text("fixture", encoding="utf-8")
        (batch / "_ai_analysis").mkdir()
        (batch / "_ai_analysis" / "analysis.json").write_text("{}", encoding="utf-8")
        (batch / "90_Draft_Project").mkdir()
        (batch / "90_Draft_Project" / "draft.txt").write_text("fixture", encoding="utf-8")
        (batch / ".DS_Store").write_bytes(b"ignored")

        with self.resolved_project():
            result = PROMOTE.promote_batch(batch, self.workspace)

        self.assertTrue(result["source_batch_removed"])
        self.assertFalse(batch.exists())
        self.assertEqual(
            (self.project / "00_Inbox_待分类" / "clip.mp4").read_bytes(),
            b"fixture-clip.mp4",
        )
        self.assertTrue((self.project / "00_Inbox_待分类" / "00_批次说明.md").is_file())
        archived_scaffold = Path(result["archived_generated_scaffold"][0])
        self.assertEqual(archived_scaffold.name, "90_Draft_Project")
        self.assertEqual((archived_scaffold / "draft.txt").read_text(encoding="utf-8"), "fixture")
        record = Path(result["promotion_record"])
        self.assertTrue(record.is_file())
        self.assertIn("source_batch_path", record.read_text(encoding="utf-8"))
        self.assertIn("Inbox 批次迁移", (self.project / "素材整理记录.md").read_text(encoding="utf-8"))
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])

    def test_refuses_a_batch_outside_the_inbox_root(self) -> None:
        outside = self.workspace / "outside"
        outside.mkdir()
        with self.assertRaises(PROMOTE.PromoteError):
            PROMOTE.promote_batch(outside, self.workspace)

    def test_preflight_collision_rejects_before_any_source_move(self) -> None:
        batch = self.make_batch("clip.mp4", "other.mp4")
        collision = self.project / "00_Inbox_待分类" / "clip.mp4"
        collision.parent.mkdir(parents=True)
        collision.write_bytes(b"existing-target")

        with self.resolved_project(), self.assertRaisesRegex(PROMOTE.PromoteError, "preflight collision"):
            PROMOTE.promote_batch(batch, self.workspace)

        self.assertEqual((batch / "clip.mp4").read_bytes(), b"fixture-clip.mp4")
        self.assertEqual((batch / "other.mp4").read_bytes(), b"fixture-other.mp4")
        self.assertEqual(collision.read_bytes(), b"existing-target")
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_RECORD_SUFFIX}")), [])
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])

    def test_second_move_failure_rolls_back_and_retry_succeeds(self) -> None:
        batch = self.make_batch("a.mp4", "b.mp4")
        real_move = PROMOTE.move_path
        move_calls = 0

        def fail_second_move(source: Path, target: Path) -> Path:
            nonlocal move_calls
            move_calls += 1
            if move_calls == 2:
                raise OSError("injected second move failure")
            return real_move(source, target)

        with self.resolved_project(), patch.object(PROMOTE, "move_path", side_effect=fail_second_move):
            with self.assertRaisesRegex(PROMOTE.PromoteError, "rolled back"):
                PROMOTE.promote_batch(batch, self.workspace)

        self.assertEqual((batch / "a.mp4").read_bytes(), b"fixture-a.mp4")
        self.assertEqual((batch / "b.mp4").read_bytes(), b"fixture-b.mp4")
        self.assertFalse((self.project / "00_Inbox_待分类" / "a.mp4").exists())
        self.assertFalse((self.project / "00_Inbox_待分类" / "b.mp4").exists())
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_RECORD_SUFFIX}")), [])
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])

        with self.resolved_project():
            result = PROMOTE.promote_batch(batch, self.workspace)
        self.assertTrue(result["source_batch_removed"])
        self.assertEqual(result["moved_count"], 2)

    def test_record_write_failure_removes_record_and_restores_sources(self) -> None:
        batch = self.make_batch("clip.mp4")
        real_write_record = PROMOTE.write_promotion_record

        def write_then_fail(*args, **kwargs):
            real_write_record(*args, **kwargs)
            raise OSError("injected record completion failure")

        with self.resolved_project(), patch.object(
            PROMOTE,
            "write_promotion_record",
            side_effect=write_then_fail,
        ):
            with self.assertRaisesRegex(PROMOTE.PromoteError, "rolled back"):
                PROMOTE.promote_batch(batch, self.workspace)

        self.assertEqual((batch / "clip.mp4").read_bytes(), b"fixture-clip.mp4")
        self.assertFalse((self.project / "00_Inbox_待分类" / "clip.mp4").exists())
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_RECORD_SUFFIX}")), [])
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])
        self.assertFalse((self.project / "素材整理记录.md").exists())

    def test_log_write_failure_removes_record_and_restores_prior_log(self) -> None:
        batch = self.make_batch("clip.mp4")
        log_path = self.project / "素材整理记录.md"
        original_log = "# 素材整理记录\n\n原有记录\n"
        log_path.write_text(original_log, encoding="utf-8")
        real_append_log = PROMOTE.append_project_log

        def append_then_fail(*args, **kwargs):
            real_append_log(*args, **kwargs)
            raise OSError("injected log completion failure")

        with self.resolved_project(), patch.object(
            PROMOTE,
            "append_project_log",
            side_effect=append_then_fail,
        ):
            with self.assertRaisesRegex(PROMOTE.PromoteError, "rolled back"):
                PROMOTE.promote_batch(batch, self.workspace)

        self.assertEqual((batch / "clip.mp4").read_bytes(), b"fixture-clip.mp4")
        self.assertEqual(log_path.read_text(encoding="utf-8"), original_log)
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_RECORD_SUFFIX}")), [])
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])

    def test_retry_recovers_an_interrupted_journal_before_promoting(self) -> None:
        batch = self.make_batch("a.mp4", "b.mp4")
        real_move = PROMOTE.move_path
        move_calls = 0

        def interrupt_second_move(source: Path, target: Path) -> Path:
            nonlocal move_calls
            move_calls += 1
            if move_calls == 2:
                raise KeyboardInterrupt("injected interruption")
            return real_move(source, target)

        with self.resolved_project(), patch.object(PROMOTE, "move_path", side_effect=interrupt_second_move):
            with self.assertRaises(KeyboardInterrupt):
                PROMOTE.promote_batch(batch, self.workspace)

        journals = list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}"))
        self.assertEqual(len(journals), 1)
        self.assertFalse((batch / "a.mp4").exists())
        self.assertTrue((batch / "b.mp4").exists())

        with self.resolved_project():
            result = PROMOTE.promote_batch(batch, self.workspace)

        self.assertTrue(result["source_batch_removed"])
        self.assertEqual(result["moved_count"], 2)
        self.assertEqual(list(self.project.rglob(f"*{PROMOTE.PROMOTION_JOURNAL_SUFFIX}")), [])

    def test_retry_after_success_returns_existing_result_without_duplication(self) -> None:
        batch = self.make_batch("clip.mp4")
        with self.resolved_project():
            first = PROMOTE.promote_batch(batch, self.workspace)

        with patch.object(
            PROMOTE,
            "resolve_project_dir",
            side_effect=AssertionError("completed retry must not bootstrap or move again"),
        ):
            second = PROMOTE.promote_batch(batch, self.workspace)

        self.assertEqual(second, first)
        records = list(self.project.rglob(f"*{PROMOTE.PROMOTION_RECORD_SUFFIX}"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].resolve(), Path(first["promotion_record"]).resolve())
        log_text = (self.project / "素材整理记录.md").read_text(encoding="utf-8")
        self.assertEqual(log_text.count("Inbox 批次迁移"), 1)


if __name__ == "__main__":
    unittest.main()
