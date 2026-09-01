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
        self.assertIn("默认行为和新增提供方尚未形成可验收决定", content)
        self.assertNotIn("转写：阿里云在线为默认，FunASR 本地兜底", content)

    def test_prototype_keeps_chatcut_optional_and_non_primary(self) -> None:
        content = PROTOTYPE.read_text(encoding="utf-8")
        self.assertIn('data-chatcut-optional hidden', content)
        self.assertIn("ChatCut Desktop 可选连接", content)
        self.assertIn("探测成功并主动连接后显示", content)
        self.assertNotIn("送入 ChatCut", content)
        self.assertNotIn('<span class="flow-name">时间线</span><span class="flow-by">ChatCut</span>', content)

    def test_studio_keeps_policy_settings_and_user_confirmed_delete_entrypoints(self) -> None:
        index = STUDIO_INDEX.read_text(encoding="utf-8")
        app = STUDIO_APP.read_text(encoding="utf-8")

        self.assertIn('<button data-tab="settings">设置</button>', index)
        self.assertIn("if(state.tab==='settings')return settings()", app)
        self.assertIn('<h2>设置</h2>', app)
        self.assertIn("删除候选", app)
        self.assertIn("secondConfirmation", app)
        self.assertIn("确认移入系统回收站", app)
        self.assertIn("恢复回执", app)
        self.assertIn("/media-delete/recommendations", app)
        self.assertIn("/media-delete/confirm", app)
        self.assertIn("/media-delete/restore", app)
        self.assertIn("if(state.tab==='settings')return settings();if(!state.project)", app)
        self.assertIn("projectPolicyPanels=p?", app)
        self.assertIn("if(!p)return;$('#delete-recommendation-form')", app)


if __name__ == "__main__":
    unittest.main()
