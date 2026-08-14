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


if __name__ == "__main__":
    unittest.main()
