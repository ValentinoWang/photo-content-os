#!/usr/bin/env python3
"""Tests for linking an intake batch to a Content OS project package."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("batch_link", SCRIPT_DIR / "31_link_batch_to_content_project.py")
batch_link = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(batch_link)


def write_batch_note(batch: Path, project_id: str) -> None:
    batch.mkdir(parents=True)
    (batch / "00_批次说明.md").write_text(
        f"""# 20260626_测试事件_待整理

## 云端项目引用

Obsidian 项目ID：{project_id}

腾讯云初稿路径：
- 01_idea_card:
- 02_project_brief:
- 04_script:
- task:

## 本地素材批次

事件：测试事件
地点：测试地点
人物：测试人物
时间范围：2026-06-26
素材来源：AirDrop
本地素材批次：20260626_测试事件_待整理
目标项目：20260626_测试项目
这批素材可能服务的内容：
- 测试短视频
必须保留 / 特别注意：
- 保留合照
不确定的地方：
- 是否需要补拍
""",
        encoding="utf-8",
    )


class BatchContentLinkTest(unittest.TestCase):
    def test_project_id_links_to_required_obsidian_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            package = vault / "08_内容项目/20260626_测试项目"
            package.mkdir(parents=True)
            for name in ["01_idea_card.md", "02_project_brief.md", "04_script.md"]:
                (package / name).write_text(f"# {name}\n", encoding="utf-8")
            batch = root / "00_Inbox_Mac_Intake/20260626_测试事件_待整理"
            write_batch_note(batch, "20260626_测试项目")
            (batch / "clip.mp4").write_bytes(b"not a real video")

            link = batch_link.build_link(batch, vault, root)

            self.assertEqual(link["status"], "brief_ready")
            self.assertEqual(link["obsidian"]["project_id"], "20260626_测试项目")
            self.assertEqual(link["validation"]["missing_required_files"], [])
            self.assertEqual(link["batch"]["media_file_count"], 1)
            self.assertTrue(link["obsidian"]["files"]["project_brief"]["exists"])

    def test_missing_project_id_records_pending_cloud_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            vault.mkdir()
            batch = root / "00_Inbox_Mac_Intake/20260626_测试事件_待整理"
            write_batch_note(batch, "")

            link = batch_link.build_link(batch, vault, root)

            self.assertEqual(link["status"], "pending_cloud_brief")
            self.assertFalse(link["validation"]["project_id_present"])
            self.assertEqual(link["validation"]["missing_required_files"], ["idea_card", "project_brief", "script"])

    def test_write_link_creates_yaml_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "_ai_analysis/content_os_link.yaml"
            data = {"spec_version": "content_os_batch_link_v0.1", "status": "brief_ready"}

            batch_link.write_link(output, data)

            self.assertEqual(yaml.safe_load(output.read_text(encoding="utf-8"))["status"], "brief_ready")


if __name__ == "__main__":
    unittest.main()
