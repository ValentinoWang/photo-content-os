#!/usr/bin/env python3
"""Wave-6 regression tests for explicit local prompt creator context."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


storyboard = load_script("18_generate_storyboard_edl.py", "wave6_storyboard")
edit_log = load_script("29_generate_ai_edit_log.py", "wave6_edit_log")


class LocalPromptCreatorContextTests(unittest.TestCase):
    def test_storyboard_prompt_uses_explicit_creator_context_without_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "_ai_analysis").mkdir()
            (project / "_ai_analysis" / "media_manifest.json").write_text(
                json.dumps({"items": []}, ensure_ascii=False), encoding="utf-8"
            )
            brief = project / "02_brief.md"
            brief.write_text(
                "---\nproject_id: p1\nidea_id: i1\n---\n\n"
                "- 发布平台：小红书\n- 账号人设：城市通勤观察者\n- 口吻：克制直接\n",
                encoding="utf-8",
            )
            script = project / "04_script.md"
            report = project / "03_material_match_report.md"
            script.write_text("# 脚本\n", encoding="utf-8")
            report.write_text("# 素材适配\n", encoding="utf-8")

            prompt = storyboard.build_user_prompt(
                project=project,
                brief_path=brief,
                script_path=script,
                report_path=report,
                storyboard_path=project / "05_storyboard.md",
                edl_path=project / "06_edit_decision_list.json",
                model="gpt-test",
                reasoning="xhigh",
            )

            self.assertIn("城市通勤观察者", prompt)
            self.assertIn("小红书", prompt)
            self.assertIn("没有提供的字段必须标记人工确认，不得猜测", prompt)
            self.assertIn('"creator_context"', prompt)

    def test_edit_log_context_carries_only_declared_creator_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "00_项目总览.md").write_text(
                "---\nproject_id: p1\nidea_id: i1\n---\n\n"
                "- 账号：夜班编辑\n- 发布平台：视频号\n- 题材边界：只写亲历观察\n",
                encoding="utf-8",
            )
            (project / "04_script.md").write_text("# 脚本\n", encoding="utf-8")
            (project / "06_edit_decision_list.json").write_text("{}\n", encoding="utf-8")

            context = edit_log.collect_context(
                project_package=project,
                output=project / "07_edit_log.md",
                human_notes=None,
                video=None,
                model="gpt-test",
                reasoning="xhigh",
            )

            creator_context = context["creator_context"]
            self.assertEqual(creator_context["account"], "夜班编辑")
            self.assertEqual(creator_context["platforms"], "视频号")
            self.assertEqual(creator_context["topic_boundaries"], "只写亲历观察")
            self.assertEqual(creator_context["persona"], "")
            self.assertEqual(creator_context["status"], "provided")


if __name__ == "__main__":
    unittest.main()
