#!/usr/bin/env python3
"""Tests for the lightweight OpenClaw JSON queue processor."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from _support import load_script


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
openclaw_queue = load_script("32_process_openclaw_queue.py", "openclaw_queue", register=True)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_config(root: Path) -> object:
    return openclaw_queue.QueueConfig(workspace_root=root, queue_root=root / "_OpenClawQueue")


class OpenClawQueueTest(unittest.TestCase):
    def _queue_task(self, path: Path, batch: Path, *, topic: str = "第一视角体验") -> None:
        write_json(
            path,
            {
                "task_type": "bind_creation_run_to_local_batch",
                "creation_run_id": "run_20260627_idempotent",
                "idempotency_key": "task_20260627_001",
                "project_revision": 3,
                "editor_backend": "handoff_pack",
                "topic": topic,
                "local_batch_path": str(batch),
                "source_agent_task": {
                    "task_id": "task_20260627_001",
                    "task_type": "local_material_match",
                    "project_id": "project_demo",
                    "idea_id": "idea_demo",
                    "project_revision": 3,
                    "editor_backend": "handoff_pack",
                    "tenant_id": "tenant_demo",
                },
            },
        )

    def test_cloud_markdown_is_verified_and_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "package"
            package.mkdir()
            markdown = package / "draft.md"
            markdown.write_text("# 云端初稿\n", encoding="utf-8")
            task = {
                "markdown_file": "draft.md",
                "markdown_sha256": openclaw_queue.sha256_file(markdown),
                "source_cloud_markdown": "cloud://draft",
            }
            info = openclaw_queue.markdown_info(task, package)
            self.assertEqual(info["markdown_sha256"], task["markdown_sha256"])
            self.assertEqual(info["source_cloud_markdown"], "cloud://draft")

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

    def test_result_identity_and_same_payload_replay_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_idempotent"
            batch.mkdir(parents=True)
            (batch / "00_批次说明.md").write_text("# 批次\n", encoding="utf-8")
            first = config.cloud_to_mac / "first.json"
            self._queue_task(first, batch)

            first_result = openclaw_queue.process_pending(config)[0]
            result_path = config.mac_to_cloud / "run_20260627_idempotent.result.json"
            persisted = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(first_result["status"], "linked")
            self.assertEqual(persisted["doc_type"], "mac_result")
            self.assertEqual(persisted["content_os_spec_version"], "content_os_v0.2")
            self.assertEqual(persisted["task_id"], "task_20260627_001")
            self.assertEqual(persisted["project_revision"], 3)
            self.assertEqual(persisted["editor_backend"], "handoff_pack")
            self.assertTrue(persisted["request_fingerprint"].startswith("sha256:"))

            replay_task = config.cloud_to_mac / "retry.json"
            self._queue_task(replay_task, batch)
            replay = openclaw_queue.process_pending(config)[0]
            self.assertTrue(replay["idempotent_replay"])
            self.assertEqual(
                json.loads(result_path.read_text(encoding="utf-8"))["generated_at"],
                persisted["generated_at"],
            )

    def test_different_payload_same_run_is_blocked_without_overwriting_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_conflict"
            batch.mkdir(parents=True)
            (batch / "00_批次说明.md").write_text("# 批次\n", encoding="utf-8")
            self._queue_task(config.cloud_to_mac / "first.json", batch)
            openclaw_queue.process_pending(config)
            result_path = config.mac_to_cloud / "run_20260627_idempotent.result.json"
            original = json.loads(result_path.read_text(encoding="utf-8"))

            self._queue_task(config.cloud_to_mac / "changed.json", batch, topic="改过的主题")
            conflict = openclaw_queue.process_pending(config)[0]
            self.assertEqual(conflict["status"], "blocked")
            self.assertEqual(conflict["blocked_reason"], "idempotency_conflict")
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), original)

    def test_invalid_markdown_digest_writes_blocked_mac_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            package = config.cloud_to_mac / "package"
            package.mkdir(parents=True)
            (package / "draft.md").write_text("# draft\n", encoding="utf-8")
            write_json(
                package / "manifest.json",
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_sha",
                    "markdown_file": "draft.md",
                    "markdown_sha256": "0" * 64,
                },
            )

            result = openclaw_queue.process_pending(config)[0]
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["doc_type"], "mac_result")
            self.assertEqual(result["blocked_reason"], "queue_contract_failed")
            self.assertIn("markdown_sha256 mismatch", result["detail"])

    def test_markdown_package_is_processed_and_path_is_rebound_after_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = make_config(root)
            batch = root / "00_Inbox_Mac_Intake/20260627_markdown"
            batch.mkdir(parents=True)
            package = config.cloud_to_mac / "package"
            package.mkdir(parents=True)
            markdown = package / "draft.md"
            markdown.write_text("# 云端初稿\n", encoding="utf-8")
            write_json(
                package / "manifest.json",
                {
                    "task_type": "bind_creation_run_to_local_batch",
                    "creation_run_id": "run_20260627_markdown",
                    "local_batch_path": str(batch),
                    "markdown_file": "draft.md",
                    "markdown_sha256": openclaw_queue.sha256_file(markdown),
                },
            )

            result = openclaw_queue.process_pending(config)[0]
            moved = config.processed / "package"
            self.assertEqual(result["status"], "linked")
            self.assertEqual(result["cloud_markdown"]["local_markdown_path"], str(moved / "draft.md"))
            link = json.loads((batch / "_openclaw/link.json").read_text(encoding="utf-8"))
            self.assertEqual(link["cloud_markdown"]["markdown_sha256"], result["cloud_markdown"]["markdown_sha256"])

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
