from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from _support import load_script

contract = load_script("openclaw_product_contract", "mx_video_contract", register=True)
adapter = load_script("openclaw_video_execution", "mx_video_execution", register=True)


class VideoExecutionContractTests(unittest.TestCase):
    def handoff(self):
        identity = {"job_id": "job_mx_fixture", "tenant_id": "11111111-1111-4111-8111-111111111111", "work_id": "work_mx_fixture", "work_revision": 3, "project_id": "project-mx-fixture", "project_revision": 2, "catalog_digest": contract.load_snapshot()["catalog_digest"], "confirmation_ref": "confirm_mx_fixture"}
        payload = {"identity": identity, "script": "确认稿件", "storyboard": [{"shot": "01", "visual": "画面", "dialogue": "台词", "subtitle": "字幕", "camera": "全屏", "audio": "配音"}], "animations": [], "tts_ref": "audio/tts.wav"}
        return {**payload, "handoff_digest": contract.video_digest(payload)}

    def test_valid_handoff_is_a_copy_bound_to_confirmed_content(self):
        payload = self.handoff()
        result = contract.validate_video_handoff(payload, payload["identity"], expected_handoff_digest=payload["handoff_digest"])
        result["identity"]["work_id"] = "other"
        self.assertEqual(payload["identity"]["work_id"], "work_mx_fixture")

    def test_recomputed_digest_does_not_replace_confirmed_content(self):
        payload = self.handoff(); expected = payload["handoff_digest"]
        payload["script"] = "被替换的稿件"
        payload["handoff_digest"] = contract.video_digest({k: v for k, v in payload.items() if k != "handoff_digest"})
        with self.assertRaises(contract.ProductContractError):
            contract.validate_video_handoff(payload, payload["identity"], expected_handoff_digest=expected)

    def test_changed_identity_and_unknown_columns_are_rejected(self):
        payload = self.handoff()
        for key, value in (("work_revision", 2), ("project_revision", True), ("tenant_id", "22222222-2222-4222-8222-222222222222"), ("catalog_digest", "sha256:" + "0" * 64), ("confirmation_ref", "other")):
            current = copy.deepcopy(payload["identity"]); current[key] = value
            with self.subTest(key=key), self.assertRaises(contract.ProductContractError):
                contract.validate_video_handoff(payload, current, expected_handoff_digest=payload["handoff_digest"])
        payload["storyboard"][0]["path"] = "/Users/operator/raw.mp4"
        payload["handoff_digest"] = contract.video_digest({k: v for k, v in payload.items() if k != "handoff_digest"})
        with self.assertRaises(contract.ProductContractError):
            contract.validate_video_handoff(payload, payload["identity"], expected_handoff_digest=payload["handoff_digest"])

    def test_refs_reject_aliases_escape_and_symlinks(self):
        for ref in (".", "a//b", "a/./b", "a/../b", "C:media", "a\\b", "/raw.mp4"):
            with self.subTest(ref=ref), self.assertRaises(contract.ProductContractError):
                contract.safe_workspace_ref(ref)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "workspace").mkdir(); (root / "outside").write_text("raw")
            (root / "workspace/link").symlink_to(root / "outside")
            with self.assertRaises(adapter.ProductContractError):
                adapter.local_path(root / "workspace", "link")

    def test_catalog_stamp_cannot_hide_changed_definitions(self):
        pipelines = [{"pipeline_id": "media.fixture.v1", "version": "1.0.0"}]
        digest = "sha256:" + hashlib.sha256(json.dumps(pipelines, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        snapshot = contract.load_snapshot(); snapshot["catalog_digest"] = digest
        catalog = {"catalog_digest": digest, "pipelines": pipelines}
        with patch.object(contract, "load_snapshot", return_value=snapshot), patch.object(contract, "_installed_catalog", return_value=("0.2.0", catalog)):
            self.assertTrue(contract.compatibility().compatible)
            pipelines[0]["version"] = "2.0.0"
            self.assertEqual(contract.compatibility().reason, "catalog_definitions_mismatch")

    def test_whitelist_executes_real_local_function_and_rejects_unknowns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / "video_render").mkdir()
            (root / "video_render/compose.py").write_text("import sys\ndef fixture(project_root):\n    (project_root / 'ran').write_text('yes')\n    (project_root / 'python').write_text(sys.executable)\n")
            registry = adapter.PhotoNodeRegistry(SimpleNamespace(), root / "binding.json")
            with patch.object(adapter, "SCRIPTS", root):
                registry._invoke({"action": "compose", "function": "fixture", "kwargs": {"project_root": "$project_root"}}, root=root, handoff={}, output_root=root)
                self.assertEqual((root / "ran").read_text(), "yes")
                self.assertEqual(Path((root / "python").read_text()).resolve(), adapter.PHOTO_PYTHON.resolve())
                for step in ({"action": "shell", "function": "fixture", "kwargs": {}}, {"action": "compose", "function": "missing", "kwargs": {}}, {"action": "transcribe", "function": "main", "kwargs": {}}):
                    with self.subTest(step=step), self.assertRaises(adapter.ProductContractError):
                        registry._invoke(step, root=root, handoff={}, output_root=root)


if __name__ == "__main__":
    unittest.main()
