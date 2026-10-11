from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
SCRIPTS = SYSTEM / "scripts"
sys.path.insert(0, str(SCRIPTS))

from edl_contract import normalise_edl  # noqa: E402

from _support import load_script  # noqa: E402


def create_video(path: Path, duration: float = 1.2) -> None:
    completed = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=white:s=160x90:d={duration}",
            "-pix_fmt", "yuv420p", str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace"))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg is required")
class MediaIntegrationTests(unittest.TestCase):
    def test_tier_plan_drives_real_keyframe_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            video = project / "clip.mp4"
            create_video(video, 2.0)
            analysis = project / "_ai_analysis"
            analysis.mkdir()
            manifest = {
                "items": [{
                    "media_id": "m1", "relative_path": "clip.mp4", "media_type": "video",
                    "analysis_eligible": True, "duration_sec": 2.0,
                }]
            }
            (analysis / "media_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            plan = {
                "schema_version": "analysis_tiering_v1",
                "plans": [{"media_id": "m1", "tier": "preview", "image_budget": 3, "cache_key": "sha256:test"}],
            }
            plan_path = analysis / "analysis_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "02_extract_keyframes.py"), str(project), "--analysis-plan", str(plan_path)],
                text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                env={**dict(__import__("os").environ), "PYTHONPATH": str(SCRIPTS)},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            updated = json.loads((analysis / "media_manifest.json").read_text(encoding="utf-8"))
            item = updated["items"][0]
            self.assertEqual(item["keyframe_status"], "ok")
            self.assertEqual(len(item["keyframes"]), 3)
            for ref in item["keyframes"]:
                self.assertTrue((project / ref).is_file())

    def test_preview_execute_creates_local_mp4(self):
        module = load_script("20_render_preview.py", "preview_execution_under_test", register=True)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            media = project / "01_Media"
            media.mkdir()
            source = media / "clip.mp4"
            create_video(source, 1.2)
            edl = normalise_edl({
                "source_script_used": True,
                "generation_model": "test",
                "generation_reasoning": "high",
                "clips": [{
                    "slot": 1, "time_range": "0.000-1.000", "source_start_sec": 0,
                    "purpose": "预览", "visual_need": "白色视频", "caption": "无字幕",
                    "candidate_files": ["01_Media/clip.mp4"], "edit_note": "本地测试",
                }],
            })
            output = project / "preview.mp4"
            plan = module.build_plan(edl, project=project, output=output, width=180, height=320, fps=12)
            module.execute_plan(plan)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
