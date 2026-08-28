from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "edit_backends" / "otio_kdenlive.py"
OTIO_KDENLIVE_PYTHON = ROOT / ".venv-content-os" / "bin" / "python"


def write_edl(path: Path, *, raw360: bool = False, overlap: bool = False) -> None:
    candidate_one = "素材/第一段.mp4"
    if raw360:
        candidate_one = "00_RawVault_不可直用/第一视角.OSV"
    data = {
        "doc_type": "edit_decision_list",
        "project_id": "demo_中文",
        "clips": [
            {
                "slot": "01",
                "time_range": "0.0-2.0s",
                "caption": "第一句",
                "candidate_files": [candidate_one],
                "edit_note": "开场",
            },
            {
                "slot": "02",
                "time_range": "1.5-4.0s" if overlap else "2.0-4.0s",
                "caption": "第二句",
                "candidate_files": ["素材/不存在但可重链.mp4"],
                "edit_note": "结尾",
            },
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class OtioKdenliveBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not OTIO_KDENLIVE_PYTHON.is_file() or not OTIO_KDENLIVE_PYTHON.stat().st_mode & 0o111:
            raise RuntimeError("missing fixed OTIO/Kdenlive test runtime")

    def run_script(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run([str(OTIO_KDENLIVE_PYTHON), str(SCRIPT), *args], text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, expected, completed.stderr)
        return completed

    def test_generates_reopens_unicode_and_missing_media_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            write_edl(edl)
            output = root / "edit_handoff"
            revision_dir = output / "3"
            otio_result = root / "otio_result.json"
            self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "3",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(output),
                "--result-output", str(otio_result),
            )
            self.assertTrue((revision_dir / "timeline.otio").is_file())
            manifest = json.loads((revision_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["project_revision"], 3)
            self.assertEqual(manifest["clips"][0]["candidate_file"], "素材/第一段.mp4")
            self.assertTrue(all(clip["needs_relink"] for clip in manifest["clips"]))
            self.run_script(
                "generate-kdenlive", "--project-id", "demo_中文", "--project-revision", "3",
                "--otio", str(revision_dir / "timeline.otio"), "--output-root", str(output),
                "--result-output", str(root / "kdenlive_result.json"),
            )
            validation = root / "validation.json"
            self.run_script(
                "validate", "--project-id", "demo_中文", "--project-revision", "3",
                "--otio", str(revision_dir / "timeline.otio"), "--kdenlive", str(revision_dir / "timeline.kdenlive"),
                "--result-output", str(validation),
            )
            result = json.loads(validation.read_text(encoding="utf-8"))
            self.assertTrue(result["otio_reopened"])
            self.assertTrue(result["kdenlive_project_reopened"])
            self.assertEqual(result["clip_count"], 2)

    def test_blocks_raw360_source_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            write_edl(edl, raw360=True)
            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            completed = self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "1",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(root / "out"),
                expected=2,
            )
            self.assertIn("raw 360", completed.stderr)

    def test_revision_basis_is_written_to_otio_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            storyboard = root / "storyboard.md"
            basis = root / "revision.json"
            write_edl(edl)
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            basis.write_text(json.dumps({
                "spec_version": "content_os_v0.2",
                "doc_type": "confirmed_revision_basis",
                "project_id": "demo_中文",
                "project_revision": 4,
                "change_request_id": "change_20260828_002",
                "editor_backend": "otio_kdenlive",
                "change_summary": {
                    "requested_location": "结尾",
                    "requested_change": "调整字幕",
                    "reason": "人工确认",
                },
            }, ensure_ascii=False), encoding="utf-8")
            output = root / "edit_handoff"
            revision_dir = output / "4"
            self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "4",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(output),
                "--revision-basis", str(basis),
            )
            self.run_script(
                "generate-kdenlive", "--project-id", "demo_中文", "--project-revision", "4",
                "--otio", str(revision_dir / "timeline.otio"), "--output-root", str(output),
            )
            self.run_script(
                "validate", "--project-id", "demo_中文", "--project-revision", "4",
                "--otio", str(revision_dir / "timeline.otio"), "--kdenlive", str(revision_dir / "timeline.kdenlive"),
            )
            manifest = json.loads((revision_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["revision_basis"]["change_request_id"], "change_20260828_002")

    def test_blocks_overlapping_edl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            write_edl(edl, overlap=True)
            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            completed = self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "1",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(root / "out"),
                expected=2,
            )
            self.assertIn("overlaps", completed.stderr)


if __name__ == "__main__":
    unittest.main()
