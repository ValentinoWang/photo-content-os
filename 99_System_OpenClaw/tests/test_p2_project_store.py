from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

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

        with self.assertRaisesRegex(ProjectStoreError, "selection_invalid"):
            self.store.patch_document(
                locked["id"], "brief", {"brief-goal": "重复选区"},
                selected_block_ids=["brief-goal", "brief-goal"], expected_revision=locked["revision"],
            )
        with self.assertRaisesRegex(ProjectStoreError, "patch_contract_invalid"):
            self.store.patch_document(
                locked["id"], "brief", {"brief-goal": "允许", "brief-angle": "越界"},
                selected_block_ids=["brief-goal"], expected_revision=locked["revision"],
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
        with self.assertRaisesRegex(ProjectStoreError, "revision_invalid"):
            self.store.update_project(rolled["id"], {"title": "bool 不是 revision"}, expected_revision=True)

    def test_concurrent_project_writes_use_one_cas_winner(self):
        second_store = ProjectStore(self.root / "state")
        barrier = Barrier(2)

        def update(store, title):
            barrier.wait()
            try:
                return "ok", store.update_project(
                    self.project["id"], {"title": title}, expected_revision=self.project["revision"],
                )
            except ProjectStoreError as exc:
                return exc.code, None

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda args: update(*args), ((self.store, "并发 A"), (second_store, "并发 B"))))

        self.assertEqual(sorted(code for code, _ in outcomes), ["ok", "revision_conflict"])
        final = self.store.get_project(self.project["id"])
        self.assertEqual(final["revision"], self.project["revision"] + 1)
        self.assertIn(final["title"], {"并发 A", "并发 B"})
        persisted = json.loads(self.store.path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["revision"], 3)
        self.assertEqual(list(self.store.path.parent.glob("creative-projects.json.*.tmp")), [])

    def test_stale_requires_exact_upstream_version_and_consumer_digest(self):
        brief_changed = self.store.patch_document(
            self.project["id"], "brief", {"brief-goal": "有证据的目标"},
            selected_block_ids=["brief-goal"], expected_revision=self.project["revision"],
        )
        script = brief_changed["documents"]["script"]
        source = script["stale_sources"][0]
        self.assertEqual(source["document"], "brief")
        self.assertEqual(source["document_version"], 2)
        self.assertEqual(
            source["consumer_surface_digest"],
            brief_changed["documents"]["brief"]["history"][-1]["consumer_surface_digest"],
        )

        wrong = {"brief": {"document_version": 2, "consumer_surface_digest": "sha256:" + "0" * 64}}
        with self.assertRaisesRegex(ProjectStoreError, "stale_provenance_mismatch"):
            self.store.patch_document(
                brief_changed["id"], "script", {"script-hook": "错误确认"},
                selected_block_ids=["script-hook"], consumed_upstream=wrong,
                expected_revision=brief_changed["revision"],
            )

        still_stale = self.store.patch_document(
            brief_changed["id"], "script", {"script-hook": "仅编辑，未确认上游"},
            selected_block_ids=["script-hook"], expected_revision=brief_changed["revision"],
        )
        self.assertTrue(still_stale["documents"]["script"]["stale"])
        consumed = {"brief": {"document_version": source["document_version"], "consumer_surface_digest": source["consumer_surface_digest"]}}
        reconciled = self.store.patch_document(
            still_stale["id"], "script", {"script-hook": "已消费 Brief v2"},
            selected_block_ids=["script-hook"], consumed_upstream=consumed,
            expected_revision=still_stale["revision"],
        )
        self.assertFalse(reconciled["documents"]["script"]["stale"])
        self.assertEqual(reconciled["documents"]["script"]["stale_sources"], [])
        self.assertEqual(reconciled["documents"]["script"]["consumed_inputs"]["brief"]["document_version"], 2)
        storyboard_sources = {item["document"] for item in reconciled["documents"]["storyboard"]["stale_sources"]}
        self.assertEqual(storyboard_sources, {"brief", "script"})

    def test_reference_ids_are_rejected_from_editing_candidates(self):
        project = self.store.add_reference(
            self.project["id"], title="公开样本", url="https://example.com/reference", platform="小红书",
            note="只用于研究", expected_revision=self.project["revision"],
        )
        reference = project["references"][0]
        self.assertEqual(reference["asset_role"], "reference")
        self.assertFalse(reference["editing_eligible"])
        with self.assertRaisesRegex(ProjectStoreError, "reference_asset_forbidden"):
            self.store.reject_known_reference_ids(project["id"], ["owned-asset-1", reference["id"]])
        self.assertEqual(self.store.reject_known_reference_ids(project["id"], ["owned-asset-1"]), ["owned-asset-1"])

    def test_brief_and_script_bridge_metadata_is_cas_bound(self):
        brief_bridge = self.project["documents"]["brief"]["authority_bridge"]
        script_bridge = self.project["documents"]["script"]["authority_bridge"]
        self.assertEqual(brief_bridge["target_relative_path"], "02_project_brief.md")
        self.assertEqual(script_bridge["target_relative_path"], "04_script.md")
        self.assertEqual(brief_bridge["export_state"], "pending_export")

        exported = self.store.record_document_bridge_export(
            self.project["id"], "brief",
            source_document_version=brief_bridge["source_document_version"],
            source_consumer_surface_digest=brief_bridge["source_consumer_surface_digest"],
            target_content_digest=brief_bridge["source_consumer_surface_digest"],
            expected_revision=self.project["revision"],
        )
        self.assertEqual(exported["documents"]["brief"]["authority_bridge"]["export_state"], "current")

        changed = self.store.patch_document(
            exported["id"], "brief", {"brief-goal": "新版 Brief"},
            selected_block_ids=["brief-goal"], expected_revision=exported["revision"],
        )
        changed_bridge = changed["documents"]["brief"]["authority_bridge"]
        self.assertEqual(changed_bridge["export_state"], "pending_export")
        self.assertEqual(changed_bridge["exported_source_document_version"], 1)
        with self.assertRaisesRegex(ProjectStoreError, "bridge_source_conflict"):
            self.store.record_document_bridge_export(
                changed["id"], "brief",
                source_document_version=brief_bridge["source_document_version"],
                source_consumer_surface_digest=brief_bridge["source_consumer_surface_digest"],
                target_content_digest=brief_bridge["source_consumer_surface_digest"],
                expected_revision=changed["revision"],
            )

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
        self.assertEqual(publishing["snapshot_version"], 1)
        self.assertEqual(len(recorded["publishing_history"]), 1)
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

        first_snapshot = copy.deepcopy(recorded["publishing_history"][0])
        second = self.store.record_publishing(
            recorded["id"],
            {"metrics": {"views": 1400}, "reviewConclusion": "第二次复盘"},
            expected_revision=recorded["revision"],
        )
        self.assertEqual(second["publishing"]["snapshot_version"], 2)
        self.assertEqual(len(second["publishing_history"]), 2)
        self.assertEqual(second["publishing_history"][0], first_snapshot)
        self.assertNotEqual(second["publishing_history"][0]["snapshot_digest"], second["publishing_history"][1]["snapshot_digest"])
        second["publishing_history"][0]["review_conclusion"] = "篡改返回值"
        self.assertEqual(self.store.get_project(second["id"])["publishing_history"][0], first_snapshot)

    def test_review_context_uses_snapshot_account_and_platform(self):
        same = self.store.create_project(title="同账号同平台", platform="小红书", account="账号 A")
        other_platform = self.store.create_project(title="同账号其他平台", platform="抖音", account="账号 A")
        target = self.store.create_project(title="当前项目", platform="小红书", account="账号 A")
        same = self.store.record_publishing(same["id"], {"reviewConclusion": "同平台结论"}, expected_revision=same["revision"])
        self.store.record_publishing(other_platform["id"], {"reviewConclusion": "其他平台结论"}, expected_revision=other_platform["revision"])

        context = self.store.account_review_context(target["id"])
        self.assertEqual([item["review_conclusion"] for item in context], ["同平台结论"])
        self.assertEqual(context[0]["snapshot_id"], same["publishing"]["snapshot_id"])
        self.assertEqual(context[0]["snapshot_digest"], same["publishing"]["snapshot_digest"])

    def test_legacy_store_is_normalized_without_schema_bump(self):
        persisted = json.loads(self.store.path.read_text(encoding="utf-8"))
        project = persisted["projects"][0]
        project.pop("publishing_history")
        project["delivery"].pop("stale_sources")
        project["delivery"].pop("consumed_inputs")
        for document in project["documents"].values():
            document.pop("stale_sources")
            document.pop("consumed_inputs")
            document.pop("authority_bridge", None)
            for history in document["history"]:
                history.pop("consumer_surface_digest")
        self.store.path.write_text(json.dumps(persisted, ensure_ascii=False), encoding="utf-8")

        compatible = ProjectStore(self.root / "state").get_project(self.project["id"])
        self.assertEqual(compatible["publishing_history"], [])
        self.assertEqual(compatible["documents"]["brief"]["stale_sources"], [])
        self.assertIn("consumer_surface_digest", compatible["documents"]["brief"]["history"][0])
        self.assertEqual(compatible["documents"]["brief"]["authority_bridge"]["export_state"], "pending_export")


if __name__ == "__main__":
    unittest.main()
