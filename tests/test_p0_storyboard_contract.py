from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _support import load_script

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

module = load_script("18_generate_storyboard_edl.py", "storyboard_under_test")


class StoryboardContractTests(unittest.TestCase):
    def valid(self):
        return {
            "storyboard_markdown": "---\ndoc_type: storyboard\nwriter_agent: mac_openclaw\ngeneration_model: gpt-test\ngeneration_reasoning: high\n---\n\n# 分镜\n",
            "edl_json": {
                "doc_type": "edit_decision_list",
                "source_script_used": True,
                "generation_model": "gpt-test",
                "generation_reasoning": "high",
                "clips": [{
                    "slot": 1,
                    "time_range": {"timeline_in": 0, "timeline_out": 2},
                    "source_start_sec": 0,
                    "purpose": "开场",
                    "visual_need": "环境",
                    "caption": "你好",
                    "candidate_files": ["01_Media/a.mp4"],
                    "edit_note": "切入",
                }],
            },
        }

    def test_model_output_is_canonicalised_before_write(self):
        storyboard, edl = module.validate_outputs(self.valid(), model="gpt-test", reasoning="high")
        self.assertIn("# 分镜", storyboard)
        self.assertEqual(edl["clips"][0]["time_range"], "0.000-2.000")
        self.assertEqual(edl["schema_version"], "edit_decision_list_v1")

    def test_storyboard_model_identity_is_required(self):
        value = self.valid()
        value["storyboard_markdown"] = value["storyboard_markdown"].replace("gpt-test", "other")
        with self.assertRaisesRegex(RuntimeError, "generation_model"):
            module.validate_outputs(value, model="gpt-test", reasoning="high")


if __name__ == "__main__":
    unittest.main()
