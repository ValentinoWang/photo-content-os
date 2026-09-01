"""Static contract for the audited checklist and prototype artifacts."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / "agents-results" / "2026-09-01" / "openclaw-media-ui-prototype-and-checklist"
CHECKLIST = ARTIFACT_DIR / "openclaw-dev-checklist.html"
PROTOTYPE = ARTIFACT_DIR / "openclaw-media-ui-prototype.html"


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


if __name__ == "__main__":
    unittest.main()
