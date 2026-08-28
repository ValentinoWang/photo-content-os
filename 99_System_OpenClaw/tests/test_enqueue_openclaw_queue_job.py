#!/usr/bin/env python3
"""Tests for bridging Content OS tasks into _OpenClawQueue."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from runtime_paths import obsidian_root


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("enqueue_queue", SCRIPT_DIR / "33_enqueue_openclaw_queue_job.py")
enqueue_queue = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = enqueue_queue
SPEC.loader.exec_module(enqueue_queue)


class EnqueueOpenClawQueueJobTest(unittest.TestCase):
    def test_default_vault_uses_shared_portable_resolver(self) -> None:
        self.assertEqual(enqueue_queue.DEFAULT_VAULT_ROOT, obsidian_root())

    def test_enqueue_from_content_os_task_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            workspace = root / "workspace"
            queue = workspace / "_OpenClawQueue"
            batch = workspace / "00_Inbox_Mac_Intake/20260627_清华毕业典礼"
            task_dir = vault / "98_Agent任务队列/01_cloud_to_mac_ready"
            link = root / "batch/_ai_analysis/content_os_link.yaml"
            task_dir.mkdir(parents=True)
            link.parent.mkdir(parents=True)
            batch.mkdir(parents=True)
            link.write_text(
                yaml.safe_dump(
                    {
                        "doc_type": "content_os_link",
                        "status": "brief_ready",
                        "batch": {"dir": str(batch)},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            task_path = task_dir / "task_20260627_material_match.yaml"
            task_path.write_text(
                yaml.safe_dump(
                    {
                        "task_id": "task_20260627_material_match",
                        "task_type": "local_material_match",
                        "project_id": "20260627_清华毕业典礼",
                        "idea_id": "idea_001",
                        "feishu_doc_link": "https://example.com/doc",
                        "inputs": {"content_os_link_path": str(link)},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            output = enqueue_queue.enqueue_task(
                "task_20260627_material_match",
                vault_root=vault,
                workspace_root=workspace,
                queue_root=queue,
                allow_replace=False,
                process=False,
            )

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["task_type"], "bind_creation_run_to_local_batch")
            self.assertEqual(data["creation_run_id"], "task_20260627_material_match")
            self.assertEqual(data["local_batch"]["path"], str(batch))
            self.assertTrue(data["constraints"]["old_queue_is_task_layer"])
            self.assertTrue(data["constraints"]["openclaw_queue_is_execution_layer"])

    def test_missing_local_batch_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            workspace = root / "workspace"
            queue = workspace / "_OpenClawQueue"
            task_dir = vault / "98_Agent任务队列/01_cloud_to_mac_ready"
            task_dir.mkdir(parents=True)
            task_path = task_dir / "task_no_batch.yaml"
            task_path.write_text(
                yaml.safe_dump({"task_id": "task_no_batch", "task_type": "local_material_match"}, allow_unicode=True),
                encoding="utf-8",
            )

            with self.assertRaises(enqueue_queue.EnqueueError):
                enqueue_queue.enqueue_task(
                    "task_no_batch",
                    vault_root=vault,
                    workspace_root=workspace,
                    queue_root=queue,
                    allow_replace=False,
                    process=False,
                )

    def test_batch_id_is_enough_to_enqueue_without_mac_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            workspace = root / "workspace"
            queue = workspace / "_OpenClawQueue"
            task_dir = vault / "98_Agent任务队列/01_cloud_to_mac_ready"
            task_dir.mkdir(parents=True)
            task_path = task_dir / "task_batch_id_only.yaml"
            task_path.write_text(
                yaml.safe_dump(
                    {
                        "task_id": "task_batch_id_only",
                        "task_type": "openclaw_queue_dispatch",
                        "creation_run_id": "run_batch_id_only",
                        "batch_id": "20260627_只给批次ID",
                        "topic": "云端不知道 Mac 完整路径",
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            output = enqueue_queue.enqueue_task(
                "task_batch_id_only",
                vault_root=vault,
                workspace_root=workspace,
                queue_root=queue,
                allow_replace=False,
                process=False,
            )

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["batch_id"], "20260627_只给批次ID")
            self.assertNotIn("local_batch", data)
            self.assertNotIn("local_batch_path", data)

    def test_enqueue_prefers_openclaw_queue_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            workspace = root / "workspace"
            queue = workspace / "_OpenClawQueue"
            task_dir = vault / "98_Agent任务队列/01_cloud_to_mac_ready"
            task_dir.mkdir(parents=True)
            task_path = task_dir / "task_payload.yaml"
            local_batch = str(workspace / "00_Inbox_Mac_Intake/20260627_清华毕业典礼")
            task_path.write_text(
                yaml.safe_dump(
                    {
                        "task_id": "task_payload",
                        "task_type": "openclaw_queue_dispatch",
                        "creation_run_id": "run_payload",
                        "inputs": {"local_batch_path": "/should/not/use"},
                        "openclaw_queue_payload": {
                            "schema_version": "openclaw_mac_queue_task_v1",
                            "task_type": "bind_creation_run_to_local_batch",
                            "creation_run_id": "run_payload",
                            "batch_id": "20260627_清华毕业典礼",
                            "local_batch_path": local_batch,
                            "requested_outputs": ["剪辑说明", "素材匹配"],
                        },
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            output = enqueue_queue.enqueue_task(
                "task_payload",
                vault_root=vault,
                workspace_root=workspace,
                queue_root=queue,
                allow_replace=False,
                process=False,
            )

            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["local_batch_path"], local_batch)
            self.assertEqual(data["requested_outputs"], ["剪辑说明", "素材匹配"])
            self.assertEqual(data["source_agent_task"]["task_type"], "openclaw_queue_dispatch")

    def test_process_ready_tasks_creates_missing_local_batch_shell(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            workspace = root / "workspace"
            queue = workspace / "_OpenClawQueue"
            task_dir = vault / "98_Agent任务队列/01_cloud_to_mac_ready"
            task_dir.mkdir(parents=True)
            batch = workspace / "00_Inbox_Mac_Intake/20260627_清华毕业典礼"
            task_path = task_dir / "task_20260627_dispatch.yaml"
            task_path.write_text(
                yaml.safe_dump(
                    {
                        "task_id": "task_20260627_dispatch",
                        "task_type": "openclaw_queue_dispatch",
                        "creation_run_id": "run_20260627_dispatch",
                        "feishu_doc_link": "https://example.com/doc",
                        "openclaw_queue_payload": {
                            "schema_version": "openclaw_mac_queue_task_v1",
                            "task_type": "bind_creation_run_to_local_batch",
                            "creation_run_id": "run_20260627_dispatch",
                            "batch_id": "20260627_清华毕业典礼",
                            "local_batch_path": str(batch),
                            "requested_outputs": ["剪辑说明", "素材匹配"],
                        },
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            outcomes = enqueue_queue.process_ready_tasks(
                vault_root=vault,
                workspace_root=workspace,
                queue_root=queue,
                allow_replace=False,
            )

            self.assertEqual(outcomes, [(task_path, "processed")])
            self.assertTrue((batch / "00_批次说明.md").is_file())
            self.assertTrue((batch / "_openclaw/link.json").is_file())
            result = yaml.safe_load(
                (vault / "98_Agent任务队列/02_mac_to_cloud_results/result_20260627_dispatch.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(result["status"], "done")


if __name__ == "__main__":
    unittest.main()
