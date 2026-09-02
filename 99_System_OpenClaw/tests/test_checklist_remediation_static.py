"""Static contract for the audited checklist and prototype artifacts."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "agents-results" / "2026-09-01" / "openclaw-media-ui-prototype-and-checklist"
CHECKLIST = ARTIFACT_DIR / "openclaw-dev-checklist.html"
PROTOTYPE = ARTIFACT_DIR / "openclaw-media-ui-prototype.html"
STUDIO_INDEX = ROOT / "99_System_OpenClaw" / "desktop" / "static" / "index.html"
STUDIO_APP = ROOT / "99_System_OpenClaw" / "desktop" / "static" / "app.js"


class ChecklistRemediationStaticTests(unittest.TestCase):
    def test_checklist_has_document_contract_and_ssot_pointer(self) -> None:
        content = CHECKLIST.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("<!doctype html>"))
        self.assertIn('<html lang="zh-CN">', content)
        self.assertIn('<meta charset="utf-8">', content)
        self.assertIn('name="viewport" content="width=device-width, initial-scale=1"', content)
        self.assertIn("待 SSOT 整改", content)
        self.assertIn("../openclaw-dev-checklist-review-remediation/ssot-development-paths.md", content)
        self.assertIn("默认以阿里云线上模型 API 为主", content)
        self.assertIn("FunASR 作为本机兜底方案保留", content)
        self.assertIn("<code>dashscope</code> 并设为默认", content)

    def test_prototype_keeps_chatcut_optional_and_non_primary(self) -> None:
        content = PROTOTYPE.read_text(encoding="utf-8")
        self.assertIn('data-chatcut-optional hidden', content)
        self.assertIn("ChatCut Desktop 可选连接", content)
        self.assertIn("探测成功并主动连接后显示", content)
        self.assertNotIn("送入 ChatCut", content)
        self.assertNotIn('<span class="flow-name">时间线</span><span class="flow-by">ChatCut</span>', content)

    def test_prototype_v2_resolves_declared_surface_gaps(self) -> None:
        content = PROTOTYPE.read_text(encoding="utf-8")
        self.assertIn("系统回收站；恢复时间和方式以当前操作系统", content)
        self.assertNotIn("30 天内可", content)
        self.assertIn('data-asset-add-project', content)
        self.assertIn('data-edl-view="text"', content)
        self.assertIn('data-copy-report', content)
        self.assertIn("这是产品策略，不是因为草稿加密", content)
        for item in range(1, 7):
            self.assertIn(f'data-preserved-k="k{item}"', content)

    def test_studio_keeps_policy_settings_and_user_confirmed_delete_entrypoints(self) -> None:
        index = STUDIO_INDEX.read_text(encoding="utf-8")
        app = STUDIO_APP.read_text(encoding="utf-8")

        for screen in ("home", "inbox", "library", "project", "settings"):
            self.assertIn(f'data-screen="{screen}"', index)
            self.assertIn(f'data-screen-panel="{screen}"', index)
        for surface in ("login", "setup", "cloud"):
            self.assertIn(f'data-surface-panel="{surface}"', index)
        self.assertIn("/inbox-plan", app)
        self.assertIn("state.inboxPlan?.batches", app)
        self.assertIn("/api/assets", app)
        self.assertIn("/api/assets/statistics", app)
        self.assertIn("state.selectedAsset", app)
        for recommendation in ("d1", "d2", "d3"):
            self.assertIn(f"'{recommendation}'", app)
        for pane in ("paths", "agent", "asr", "budget", "account", "doctor"):
            self.assertIn(f"settingsPane('{pane}'", app)
        self.assertIn("系统回收站", app)
        self.assertIn("二次确认", app)
        self.assertIn("本地功能保持完整", app)
        self.assertIn("ChatCut Desktop MCP", app)
        self.assertIn("结构化剪辑方案是唯一机器执行依据", app)


if __name__ == "__main__":
    unittest.main()
