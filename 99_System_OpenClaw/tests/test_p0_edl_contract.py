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
        self.assertEqual(
            schema["properties"]["schema_version"]["enum"],
            ["edit_decision_list_v1", "edit_decision_list_v2"],
        )
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


class EDLContractV2Tests(unittest.TestCase):
    """role/layer vocabulary and the wider v2 coverage."""

    def base(self):
        return {
            "doc_type": "edit_decision_list",
            "source_script_used": True,
            "generation_model": "gpt-test",
            "generation_reasoning": "high",
            "clips": [
                {
                    "slot": 1,
                    "time_range": "0.000-4.000",
                    "source_start_sec": 0.0,
                    "purpose": "口播主轴",
                    "visual_need": "人物出镜",
                    "caption": "今天讲三件事",
                    "candidate_files": ["01_Media/aroll.mp4"],
                    "edit_note": "硬切",
                }
            ],
        }

    def overlay_clip(self, **overrides):
        clip = {
            "slot": 2,
            "time_range": "1.000-2.500",
            "source_start_sec": 0.0,
            "purpose": "盖跳切",
            "visual_need": "屏幕录制",
            "caption": "示意画面",
            "candidate_files": ["01_Media/broll.mp4"],
            "edit_note": "画中画",
            "role": "b_roll",
            "layer": "overlay",
        }
        clip.update(overrides)
        return clip

    def test_v1_document_keeps_v1_version(self):
        """No v2 vocabulary means no version drift for existing pipelines."""
        result = normalise_edl(self.base())
        self.assertEqual(result["schema_version"], "edit_decision_list_v1")
        self.assertNotIn("layer", result["clips"][0])
        self.assertNotIn("role", result["clips"][0])

    def test_role_and_layer_survive_normalisation(self):
        value = self.base()
        value["clips"][0]["role"] = "a_roll"
        value["clips"].append(self.overlay_clip())
        result = normalise_edl(value)
        self.assertEqual(result["schema_version"], "edit_decision_list_v2")
        self.assertEqual(result["clips"][0]["role"], "a_roll")
        self.assertEqual(result["clips"][1]["role"], "b_roll")
        self.assertEqual(result["clips"][1]["layer"], "overlay")

    def test_overlay_may_sit_on_top_of_primary(self):
        """A picture-in-picture insert overlaps the A-roll by definition."""
        value = self.base()
        value["clips"].append(self.overlay_clip())
        result = normalise_edl(value)
        self.assertEqual(len(result["clips"]), 2)

    def test_two_overlays_may_overlap_each_other(self):
        value = self.base()
        value["clips"].append(self.overlay_clip())
        value["clips"].append(self.overlay_clip(slot=3, time_range="2.000-3.000"))
        self.assertEqual(len(normalise_edl(value)["clips"]), 3)

    def test_primary_layer_still_rejects_overlap(self):
        value = self.base()
        value["clips"].append(
            self.overlay_clip(slot=2, time_range="3.500-5.000", layer="primary")
        )
        with self.assertRaisesRegex(EDLContractError, "timeline_overlap"):
            normalise_edl(value)

    def test_rejects_unknown_role_and_layer(self):
        for field, bad in (("role", "c_roll"), ("layer", "foreground")):
            value = self.base()
            value["clips"][0][field] = bad
            with self.assertRaisesRegex(EDLContractError, f"{field}_invalid"):
                normalise_edl(value)

    def test_speed_and_transform_round_trip(self):
        value = self.base()
        value["clips"][0].update(
            {
                "speed": 1.5,
                "volume": 0.8,
                "transform": {
                    "scale": 1.2,
                    "animation": "ken-burns-slow-zoom",
                    "crop": {"x": 0.1, "y": 0.0, "width": 0.8, "height": 1.0},
                },
            }
        )
        clip = normalise_edl(value)["clips"][0]
        self.assertEqual(clip["speed"], 1.5)
        self.assertEqual(clip["volume"], 0.8)
        self.assertEqual(clip["transform"]["animation"], "ken-burns-slow-zoom")
        self.assertEqual(clip["transform"]["crop"]["width"], 0.8)

    def test_rejects_non_positive_speed(self):
        value = self.base()
        value["clips"][0]["speed"] = 0
        with self.assertRaisesRegex(EDLContractError, "speed_invalid"):
            normalise_edl(value)

    def test_rejects_crop_outside_the_frame(self):
        value = self.base()
        value["clips"][0]["transform"] = {
            "crop": {"x": 0.5, "y": 0.0, "width": 0.8, "height": 1.0}
        }
        with self.assertRaisesRegex(EDLContractError, "crop_invalid"):
            normalise_edl(value)

    def test_transition_duration_needs_a_transition(self):
        value = self.base()
        value["clips"][0]["transition_duration"] = 0.5
        with self.assertRaisesRegex(EDLContractError, "transition_duration_invalid"):
            normalise_edl(value)

    def test_transition_pair_round_trips(self):
        value = self.base()
        value["clips"][0].update(
            {"transition_in": "fade", "transition_duration": 0.5}
        )
        clip = normalise_edl(value)["clips"][0]
        self.assertEqual(clip["transition_in"], "fade")
        self.assertEqual(clip["transition_duration"], 0.5)

    def test_music_bed_is_normalised(self):
        value = self.base()
        value["music"] = [
            {
                "source": "SharedAssets/Music/bed.mp3",
                "timeline_start_sec": 0,
                "timeline_end_sec": 4,
                "volume": 0.3,
                "duck_to": 0.1,
                "loop": True,
            }
        ]
        result = normalise_edl(value)
        self.assertEqual(result["schema_version"], "edit_decision_list_v2")
        self.assertEqual(result["music"][0]["source"], "SharedAssets/Music/bed.mp3")
        self.assertEqual(result["music"][0]["duck_to"], 0.1)
        self.assertTrue(result["music"][0]["loop"])

    def test_music_bed_requires_a_source(self):
        value = self.base()
        value["music"] = [{"timeline_start_sec": 0}]
        with self.assertRaisesRegex(EDLContractError, "music_invalid"):
            normalise_edl(value)

    def test_document_sections_promote_to_v2(self):
        value = self.base()
        value["subtitles"] = {"burn_in": False, "style": "bottom-center"}
        result = normalise_edl(value)
        self.assertEqual(result["schema_version"], "edit_decision_list_v2")
        self.assertEqual(result["subtitles"]["style"], "bottom-center")


if __name__ == "__main__":
    unittest.main()
