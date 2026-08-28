from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SYSTEM))

from desktop.project_store import ProjectStore, ProjectStoreError  # noqa: E402


class ProjectStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.workspace = self.root / "本地素材"
        self.workspace.mkdir()
        self.store = ProjectStore(self.root / "state")
        self.project = self.store.create_project(title="中文项目", platform="小红书", local_workspace=str(self.workspace))

    def tearDown(self):
        self.temp.cleanup()

    def test_chinese_title_still_produces_safe_id_and_redacted_projection(self):
        self.assertRegex(self.project["id"], r"^[a-z0-9][a-z0-9_-]+$")
        encoded = json.dumps(self.project, ensure_ascii=False)
        self.assertNotIn(str(self.workspace.resolve()), encoded)
        self.assertTrue(self.project["local_workspace"]["connected"])
        self.assertIn("sha256:", self.project["local_workspace"]["path_digest"])

    def test_patch_only_selected_unlocked_blocks(self):
        revision = self.project["revision"]
        updated = self.store.patch_document(
            self.project["id"], "brief", {"brief-goal": "新的目标"},
            selected_block_ids=["brief-goal"], expected_revision=revision,
        )
        brief = updated["documents"]["brief"]
        self.assertEqual(brief["version"], 2)
        self.assertEqual(brief["blocks"][0]["body"], "新的目标")
        self.assertTrue(updated["documents"]["script"]["stale"])
        self.assertTrue(updated["delivery"]["stale"])

        locked = self.store.set_block_lock(updated["id"], "brief", "brief-audience", True, expected_revision=updated["revision"])
        with self.assertRaisesRegex(ProjectStoreError, "block_locked"):
            self.store.patch_document(
                locked["id"], "brief", {"brief-audience": "越权修改"},
                selected_block_ids=["brief-audience"], expected_revision=locked["revision"],
            )

    def test_diff_rollback_and_optimistic_lock(self):
        updated = self.store.patch_document(
            self.project["id"], "script", {"script-hook": "第一版"},
            selected_block_ids=["script-hook"], expected_revision=self.project["revision"],
        )
        diff = self.store.document_diff(updated["id"], "script", 1, 2)
        self.assertIn("+第一版", diff)
        rolled = self.store.rollback_document(updated["id"], "script", 1, expected_revision=updated["revision"])
        self.assertEqual(rolled["documents"]["script"]["version"], 3)
        self.assertEqual(rolled["documents"]["script"]["history"][-1]["reason"], "rollback_from_v1")
        with self.assertRaisesRegex(ProjectStoreError, "revision_conflict"):
            self.store.update_project(rolled["id"], {"title": "冲突"}, expected_revision=1)

    def test_record_publishing_is_versioned_and_only_accepts_public_metadata(self):
        recorded = self.store.record_publishing(
            self.project["id"],
            {
                "publishedAt": "2026-08-28T09:30:00Z",
                "links": ["https://example.com/post/1"],
                "metrics": {"views": 1200, "likes": 80, "saves": 12},
                "reviewConclusion": "开头直接给结果，完播更稳定。",
                "nextConstraint": "下次前两句先给可验证的结论。",
            },
            expected_revision=self.project["revision"],
        )
        publishing = recorded["publishing"]
        self.assertEqual(publishing["state"], "published")
        self.assertEqual(publishing["metrics"], {"views": 1200, "likes": 80, "saves": 12})
        self.assertEqual(recorded["audit"][-1]["action"], "publishing_recorded")
        self.assertNotIn("review_conclusion", recorded["audit"][-1]["detail"])
        with self.assertRaisesRegex(ProjectStoreError, "revision_conflict"):
            self.store.record_publishing(
                self.project["id"],
                {"reviewConclusion": "过期写入"},
                expected_revision=self.project["revision"],
            )
        with self.assertRaisesRegex(ProjectStoreError, "publishing_field_invalid"):
            self.store.record_publishing(
                recorded["id"],
                {"metrics": {"views": 1}, "local_workspace": "/private/media"},
                expected_revision=recorded["revision"],
            )
        with self.assertRaisesRegex(ProjectStoreError, "publishing_review_private"):
            self.store.record_publishing(
                recorded["id"],
                {"reviewConclusion": "素材在 /Users/example/private.mp4"},
                expected_revision=recorded["revision"],
            )
        with self.assertRaisesRegex(ProjectStoreError, "publishing_link_invalid"):
            self.store.record_publishing(
                recorded["id"],
                {"links": ["https://"]},
                expected_revision=recorded["revision"],
            )


if __name__ == "__main__":
    unittest.main()
