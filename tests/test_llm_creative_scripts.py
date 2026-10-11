#!/usr/bin/env python3
"""Regression tests for Mac-local LLM creative scripts."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LLMCreativeScriptsTest(unittest.TestCase):
    def test_creative_scripts_do_not_contain_old_rule_matching(self) -> None:
        combined = "\n".join(
            (ROOT / "scripts" / name).read_text(encoding="utf-8")
            for name in ["17_match_materials_to_brief.py", "18_generate_storyboard_edl.py"]
        )
        forbidden = [
            "score_item",
            "top_candidates",
            "keywords",
            "多年后，我又回到了兰大",
            "从广州到兰州，像赴一场迟到很久的约",
            "枪响、奔跑、欢呼，青春感突然回来了",
            "不是回到校园，是回到那时的自己",
        ]
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, combined)

    def test_material_match_prompt_puts_execution_before_macro_rationale(self) -> None:
        text = (ROOT / "scripts" / "17_match_materials_to_brief.py").read_text(encoding="utf-8")
        order = "是否建议进入剪辑、推荐镜头组、缺失素材、风险、素材覆盖度、宏观创作判断"

        self.assertIn(order, text)
        self.assertIn("宏观论证只能放在后面", text)

    def test_production_analysis_prompt_has_no_sports_specific_prefill(self) -> None:
        text = (ROOT / "scripts" / "04_generate_ai_prompt.py").read_text(encoding="utf-8")
        for token in ("第一视角全景跑400米", "400米比赛记录", "运动员兼拍摄者"):
            with self.subTest(token=token):
                self.assertNotIn(token, text)


if __name__ == "__main__":
    unittest.main()
