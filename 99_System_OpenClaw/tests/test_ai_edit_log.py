#!/usr/bin/env python3
"""Tests for the AI-assisted edit log contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util


SCRIPT_PATH = ROOT / "scripts" / "29_generate_ai_edit_log.py"
SPEC = importlib.util.spec_from_file_location("generate_ai_edit_log", SCRIPT_PATH)
assert SPEC and SPEC.loader
edit_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(edit_log)


class AIEditLogTest(unittest.TestCase):
    def test_validate_markdown_requires_evidence_sections(self) -> None:
        text = """---
spec_version: content_os_v0.1
doc_type: edit_log
project_id: project_test
idea_id: idea_test
status: edit_log_ai_draft
writer_agent: mac_openclaw
owner_agent: human
next_owner: human
generation_model: gpt-5.5
generation_reasoning: xhigh
evidence_level: content_plan_only
---

# AI 跟剪摘要

# 已确认人工修改

# AI 建议修改

# AI 推断修改

# 需要人确认

# 下一版建议

# 记录规则
"""
        edit_log.validate_markdown(text, project_id="project_test", model="gpt-5.5", reasoning="xhigh")

    def test_collect_context_requires_script_and_edl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project_test"
            project.mkdir()
            (project / "00_项目总览.md").write_text(
                "---\nproject_id: project_test\nidea_id: idea_test\n---\n", encoding="utf-8"
            )
            (project / "04_script.md").write_text("# 脚本\n", encoding="utf-8")
            (project / "06_edit_decision_list.json").write_text(
                json.dumps({"doc_type": "edit_decision_list", "clips": []}, ensure_ascii=False),
                encoding="utf-8",
            )

            context = edit_log.collect_context(
                project_package=project,
                output=project / "07_edit_log.md",
                human_notes=None,
                video=None,
                model="gpt-5.5",
                reasoning="xhigh",
            )

            self.assertEqual(context["project_id"], "project_test")
            self.assertIn("脚本", context["script_markdown"])
            self.assertIn("edit_decision_list", context["edit_decision_list_json"])


if __name__ == "__main__":
    unittest.main()
