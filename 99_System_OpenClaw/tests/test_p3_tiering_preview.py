from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analysis_tiering import TierBudget, analysis_cache_key, cache_hit, evenly_spaced_indexes, plan_manifest, write_cache  # noqa: E402
from edl_contract import normalise_edl  # noqa: E402
from _support import load_script  # noqa: E402

preview = load_script("20_render_preview.py", "preview_under_test", register=True)


class TieringPreviewTests(unittest.TestCase):
    def test_even_sampling_is_deterministic(self):
        self.assertEqual(evenly_spaced_indexes(10, 3), [0, 4, 9])
        self.assertEqual(evenly_spaced_indexes(2, 5), [0, 1])

    def test_tier_plan_and_cache(self):
        manifest = {"items": [
            {"media_id": "a", "relative_path": "a.mp4", "analysis_eligible": True, "duration_sec": 5, "width": 1080, "height": 1920, "has_audio": True, "sha256": "aaa", "project_selected": True},
            {"media_id": "b", "relative_path": "b.mp4", "analysis_eligible": False, "duration_sec": 2, "width": 720, "height": 1280, "has_audio": False, "sha256": "bbb"},
        ]}
        plans = plan_manifest(manifest, model="gpt", prompt_version="v1", budget=TierBudget(max_deep_assets=1))
        by_id = {plan.media_id: plan for plan in plans}
        self.assertEqual(by_id["a"].tier, "deep")
        self.assertEqual(by_id["b"].tier, "metadata")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = write_cache(root, by_id["a"].cache_key, {"ok": True})
            self.assertEqual(cache_hit(root, by_id["a"].cache_key), path)

    def test_preview_is_local_dry_run_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = project / "01_Media" / "a.mp4"
            source.parent.mkdir()
            source.write_bytes(b"placeholder")
            raw = {
                "source_script_used": True,
                "generation_model": "gpt",
                "generation_reasoning": "high",
                "clips": [{"slot": 1, "time_range": "0.000-2.000", "source_start_sec": 1, "purpose": "开场", "visual_need": "环境", "caption": "字幕", "candidate_files": ["01_Media/a.mp4"], "edit_note": "切入"}],
            }
            edl = normalise_edl(raw)
            plan = preview.build_plan(edl, project=project, output=project / "preview.mp4", require_sources=True)
            self.assertFalse(plan["privacy"]["raw_media_upload"])
            self.assertEqual(plan["mode"], "silent_roughcut")
            self.assertEqual(plan["command"][0], "ffmpeg")

    def test_preview_blocks_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            project.mkdir()
            outside = project.parent / "outside.mp4"
            outside.write_bytes(b"x")
            raw = {
                "source_script_used": True, "generation_model": "gpt", "generation_reasoning": "high",
                "clips": [{"slot": 1, "time_range": "0.000-1.000", "source_start_sec": 0, "purpose": "x", "visual_need": "x", "caption": "x", "candidate_files": [str(outside)], "edit_note": "x"}],
            }
            with self.assertRaises(preview.PreviewError):
                preview.build_plan(normalise_edl(raw), project=project, output=project / "out.mp4")


if __name__ == "__main__":
    unittest.main()
