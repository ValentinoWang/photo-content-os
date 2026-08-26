from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
sys.path.insert(0, str(SCRIPTS))

from edl_contract import EDLContractError, normalise_edl  # noqa: E402


class EDLContractTests(unittest.TestCase):
    def base(self):
        return {
            "doc_type": "edit_decision_list",
            "source_script_used": True,
            "generation_model": "gpt-test",
            "generation_reasoning": "high",
            "clips": [
                {
                    "slot": 1,
                    "time_range": {"timeline_in": 0, "timeline_out": 4},
                    "source_start_sec": 1.25,
                    "purpose": "开场",
                    "visual_need": "人物进入画面",
                    "caption": "开始",
                    "candidate_files": ["01_Media/clip.mp4"],
                    "edit_note": "硬切",
                }
            ],
        }

    def test_repairs_reported_legacy_timing_shape(self):
        result = normalise_edl(self.base())
        self.assertEqual(result["schema_version"], "edit_decision_list_v1")
        self.assertEqual(result["clips"][0]["time_range"], "0.000-4.000")
        self.assertEqual(result["clips"][0]["source_start_sec"], 1.25)
        schema = json.loads((SCHEMAS / "edit_decision_list.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "edit_decision_list_v1")
        self.assertTrue(set(schema["required"]).issubset(result))

    def test_rejects_string_slot(self):
        value = self.base()
        value["clips"][0]["slot"] = "A001"
        with self.assertRaisesRegex(EDLContractError, "edl_slot_invalid"):
            normalise_edl(value)

    def test_rejects_executable_clip_without_source(self):
        value = self.base()
        value["clips"][0]["candidate_files"] = []
        with self.assertRaisesRegex(EDLContractError, "source_missing"):
            normalise_edl(value)

    def test_rejects_overlap(self):
        value = self.base()
        second = dict(value["clips"][0])
        second.update({"slot": 2, "time_range": "3.500-5.000"})
        value["clips"].append(second)
        with self.assertRaisesRegex(EDLContractError, "timeline_overlap"):
            normalise_edl(value)

    def test_requires_millisecond_precision(self):
        value = self.base()
        value["clips"][0]["source_start_sec"] = 1.2345
        with self.assertRaisesRegex(EDLContractError, "timing_precision"):
            normalise_edl(value)


if __name__ == "__main__":
    unittest.main()
