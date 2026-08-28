#!/usr/bin/env python3
"""Tests for the lightweight OpenClaw JSON queue processor."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("openclaw_queue", SCRIPT_DIR / "32_process_openclaw_queue.py")
openclaw_queue = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = openclaw_queue
SPEC.loader.exec_module(openclaw_queue)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_config(root: Path) -> object:
    return openclaw_queue.QueueConfig(workspace_root=root, queue_root=root / "_OpenClawQueue")


class OpenClawQueueTest(unittest.TestCase):
    def test_legacy_queue_warning_checks_a_nondefault_vault(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "nondefault-vault"
            config = make_config(vault)
            package = vault / "98_Agent任务队列/01_cloud_to_mac_ready/run_20260828_001"
            package.mkdir(parents=True)
            (package / "manifest.json").write_text("{}", encoding="utf-8")

            self.assertEqual(openclaw_queue.legacy_queue_packages(config), [package])

    def test_batch_shell_uses_domain_neutral_human_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            batch = Path(tmp) / "20260828_demo"
            text = openclaw_queue.batch_note_text({}, batch)

            self.assertIn("活动第一视角", text)
            self.assertNotIn("400米", text)
            self.assertNotIn("校运会", text)

    def test_bind_creation_run_to_local_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_清华毕业典礼"
            batch.mkdir(parents=True)
            (batch / "00_批次说明.md").write_text("# 20260627_清华毕业典礼\n", encoding="utf-8")
            (batch / "clip.mp4").write_bytes(b"not a real video")
            task_path = config.cloud_to_mac / "run_20260627_115051_382a.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_115051_382a",
                    "feishu_doc_link": "https://tcnwueberajc.feishu.cn/wiki/demo",
                    "batch_id": "20260627_清华毕业典礼",
                    "topic": "第一视角体验清华毕业典礼",
                    "platform": "抖音",
                    "content_type": "视频",
                    "local_batch_path": str(batch),
                    "requested_outputs": ["剪辑说明", "素材匹配", "Storyboard", "EDL"],
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["status"], "linked")
            self.assertFalse(task_path.exists())
            self.assertTrue((config.processed / task_path.name).exists())
            link = json.loads((batch / "_openclaw/link.json").read_text(encoding="utf-8"))
            status = json.loads((batch / "_openclaw/status.json").read_text(encoding="utf-8"))
            result = json.loads((config.mac_to_cloud / "run_20260627_115051_382a.result.json").read_text(encoding="utf-8"))
            self.assertEqual(link["creation_run_id"], "run_20260627_115051_382a")
            self.assertEqual(status["status"], "linked")
            self.assertEqual(result["media_file_count"], 1)
            self.assertNotIn("clip.mp4", json.dumps(result, ensure_ascii=False))

    def test_rejects_batch_outside_inbox(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            outside = root / "01_Project_Workspace/not_an_inbox_batch"
            outside.mkdir(parents=True)
            task_path = config.cloud_to_mac / "run_20260627_bad.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_bad",
                    "local_batch_path": str(outside),
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "blocked")
            self.assertIn("00_Inbox_Mac_Intake", results[0]["detail"])
            self.assertTrue((config.failed / task_path.name).exists())
            result = json.loads((config.mac_to_cloud / "run_20260627_bad.result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["blocked_reason"], "queue_contract_failed")

    def test_accepts_nested_local_batch_path_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_清华毕业典礼"
            batch.mkdir(parents=True)
            (batch / "00_批次说明.md").write_text("# 20260627_清华毕业典礼\n", encoding="utf-8")
            task_path = config.cloud_to_mac / "run_20260627_nested.json"
            write_json(
                task_path,
                {
                    "schema_version": "openclaw_mac_queue_task_v1",
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_nested",
                    "local_batch": {"path": str(batch), "required": True},
                    "requested_outputs": ["写入批次/_openclaw/link.json"],
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            link = json.loads((batch / "_openclaw/link.json").read_text(encoding="utf-8"))
            self.assertEqual(link["local_batch_path"], str(batch.resolve()))

    def test_missing_batch_dir_is_created_and_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_新云端批次"
            task_path = config.cloud_to_mac / "run_20260627_auto_create.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_auto_create",
                    "batch_id": "20260627_新云端批次",
                    "topic": "云端有内容时先建本地批次壳",
                    "local_batch_path": str(batch),
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            self.assertTrue(batch.is_dir())
            self.assertTrue((batch / "00_批次说明.md").is_file())
            self.assertTrue((batch / "_openclaw/link.json").is_file())
            self.assertIn("auto_created_local_batch_dir", results[0]["warnings"])
            self.assertIn("auto_created_batch_note", results[0]["warnings"])

    def test_batch_id_only_creates_default_inbox_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_只给批次ID"
            task_path = config.cloud_to_mac / "run_20260627_batch_id_only.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_batch_id_only",
                    "batch_id": "20260627_只给批次ID",
                    "topic": "云端不知道 Mac 完整路径",
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            self.assertTrue(batch.is_dir())
            self.assertTrue((batch / "00_批次说明.md").is_file())
            self.assertEqual(results[0]["local_batch_path"], str(batch.resolve()))
            self.assertIn("local_batch_path_derived_from_batch_id", results[0]["warnings"])
            note = (batch / "00_批次说明.md").read_text(encoding="utf-8")
            self.assertIn("batch_id：20260627_只给批次ID", note)

    def test_missing_batch_note_is_created_and_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_自动补说明"
            batch.mkdir(parents=True)
            task_path = config.cloud_to_mac / "run_20260627_missing_note.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_missing_note",
                    "local_batch_path": str(batch),
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            status = json.loads((batch / "_openclaw/status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "linked")
            self.assertTrue((batch / "00_批次说明.md").is_file())
            self.assertTrue((config.processed / task_path.name).exists())

    def test_existing_batch_note_gets_cloud_prefill_without_overwriting_manual_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_已有人工说明"
            batch.mkdir(parents=True)
            note = batch / "00_批次说明.md"
            note.write_text(
                "# 20260627_已有人工说明\n\n"
                "## 本地素材批次\n\n"
                "事件：我手动写的事件\n"
                "地点：我手动写的地点\n",
                encoding="utf-8",
            )
            task_path = config.cloud_to_mac / "run_20260627_prefill.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_prefill",
                    "batch_id": "20260627_已有人工说明",
                    "topic": "云端传来的主题",
                    "platform": "抖音",
                    "content_type": "视频",
                    "feishu_doc_link": "https://example.com/doc",
                    "local_batch_path": str(batch),
                    "requested_outputs": ["剪辑说明", "Storyboard"],
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            text = note.read_text(encoding="utf-8")
            self.assertIn("## 云端自动填充区", text)
            self.assertIn("creation_run_id：run_20260627_prefill", text)
            self.assertIn("topic：云端传来的主题", text)
            self.assertIn("事件：我手动写的事件", text)
            self.assertIn("地点：我手动写的地点", text)
            self.assertIn("inserted_cloud_prefill_into_batch_note", results[0]["warnings"])

    def test_renamed_batch_dir_is_found_from_existing_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            original = root / "00_Inbox_Mac_Intake/20260627_云端旧名"
            renamed = root / "00_Inbox_Mac_Intake/20260627_我改过的新名字"
            renamed.mkdir(parents=True)
            (renamed / "00_批次说明.md").write_text("# 20260627_我改过的新名字\n", encoding="utf-8")
            write_json(
                renamed / "_openclaw/link.json",
                {
                    "creation_run_id": "run_20260627_rename",
                    "batch_id": "20260627_云端旧名",
                    "local_batch_path": str(original),
                },
            )
            task_path = config.cloud_to_mac / "run_20260627_rename.json"
            write_json(
                task_path,
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_rename",
                    "batch_id": "20260627_云端旧名",
                    "local_batch_path": str(original),
                },
            )

            results = openclaw_queue.process_pending(config)

            self.assertEqual(results[0]["status"], "linked")
            self.assertFalse(original.exists())
            self.assertTrue(renamed.exists())
            self.assertEqual(results[0]["local_batch_path"], str(renamed.resolve()))
            self.assertIn("local_batch_path_resolved_from_existing_link", results[0]["warnings"])


if __name__ == "__main__":
    unittest.main()
