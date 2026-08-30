from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "edit_backends" / "otio_kdenlive.py"
OTIO_KDENLIVE_PYTHON = ROOT / ".venv-content-os" / "bin" / "python"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from edl_contract import normalise_edl  # noqa: E402
from edl_contract import write_edl as write_canonical_edl  # noqa: E402


def write_edl(path: Path, *, raw360: bool = False, overlap: bool = False) -> None:
    # Uses the canonical "start-end" seconds format (no trailing "s") that the
    # real edl_contract producer (edl_contract.canonical_time_range) emits.
    candidate_one = "素材/第一段.mp4"
    if raw360:
        candidate_one = "00_RawVault_不可直用/第一视角.OSV"
    data = {
        "doc_type": "edit_decision_list",
        "project_id": "demo_中文",
        "clips": [
            {
                "slot": "01",
                "time_range": "0.000-2.000",
                "caption": "第一句",
                "candidate_files": [candidate_one],
                "edit_note": "开场",
            },
            {
                "slot": "02",
                "time_range": "1.500-4.000" if overlap else "2.000-4.000",
                "caption": "第二句",
                "candidate_files": ["素材/不存在但可重链.mp4"],
                "edit_note": "结尾",
            },
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_layered_edl(path: Path) -> None:
    """Two primary clips with a picture-in-picture overlay across the seam."""
    data = {
        "doc_type": "edit_decision_list",
        "project_id": "demo_中文",
        "clips": [
            {
                "slot": "01",
                "time_range": "0.000-2.000",
                "caption": "第一句",
                "candidate_files": ["素材/第一段.mp4"],
                "edit_note": "开场",
                "role": "a_roll",
                "layer": "primary",
            },
            {
                "slot": "02",
                "time_range": "2.000-4.000",
                "caption": "第二句",
                "candidate_files": ["素材/第二段.mp4"],
                "edit_note": "结尾",
                "role": "a_roll",
                "layer": "primary",
            },
            {
                "slot": "03",
                "time_range": "1.500-3.000",
                "caption": "小窗补充",
                "candidate_files": ["素材/小窗.mp4"],
                "edit_note": "画中画盖住跳切",
                "role": "b_roll",
                "layer": "overlay",
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

    def test_accepts_edl_produced_by_the_canonical_edl_contract_writer(self) -> None:
        """Regression test for the parse_time_range format mismatch (L-11).

        edl_contract.canonical_time_range/write_edl is the authoritative EDL
        producer used by the real pipeline (18_generate_storyboard_edl.py).
        It never appends a trailing "s" (e.g. "0.000-4.000"). The otio_kdenlive
        backend used to require that trailing "s" and would reject any EDL
        coming straight out of the canonical producer. This test feeds a real
        edl_contract.write_edl() output straight into the otio backend's
        generate-otio load path and asserts it is accepted without error.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_edl = {
                "doc_type": "edit_decision_list",
                "project_id": "demo_canonical",
                "source_script_used": True,
                "generation_model": "gpt-test",
                "generation_reasoning": "high",
                "clips": [
                    {
                        "slot": 1,
                        "time_range": {"timeline_in": 0, "timeline_out": 2},
                        "purpose": "开场",
                        "visual_need": "人物入镜",
                        "caption": "第一句",
                        "candidate_files": ["素材/第一段.mp4"],
                        "edit_note": "开场",
                    },
                    {
                        "slot": 2,
                        "time_range": {"timeline_in": 2, "timeline_out": 4},
                        "purpose": "结尾",
                        "visual_need": "细节镜头",
                        "caption": "第二句",
                        "candidate_files": ["素材/不存在但可重链.mp4"],
                        "edit_note": "结尾",
                    },
                ],
            }
            canonical_edl = normalise_edl(raw_edl)
            # normalise_edl always renders time_range without a trailing "s".
            self.assertEqual(canonical_edl["clips"][0]["time_range"], "0.000-2.000")
            edl = root / "edl.json"
            write_canonical_edl(edl, canonical_edl)

            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            output = root / "edit_handoff"
            self.run_script(
                "generate-otio", "--project-id", "demo_canonical", "--project-revision", "1",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(output),
            )
            self.assertTrue((output / "1" / "timeline.otio").is_file())

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

    def test_layered_edl_becomes_a_multi_track_timeline(self) -> None:
        """An overlay clip must composite on its own track, not flatten inline."""
        import xml.etree.ElementTree as ET

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            write_layered_edl(edl)
            output = root / "edit_handoff"
            revision_dir = output / "1"
            self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "1",
                "--edl", str(edl), "--storyboard", str(storyboard), "--output-root", str(output),
                "--result-output", str(root / "otio_result.json"),
            )
            manifest = json.loads((revision_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["layers"], ["primary", "overlay"])
            self.assertEqual(
                [clip["layer"] for clip in manifest["clips"]],
                ["primary", "primary", "overlay"],
            )

            timeline = json.loads((revision_dir / "timeline.otio").read_text(encoding="utf-8"))
            self.assertEqual(len(timeline["tracks"]["children"]), 2)
            self.assertEqual(
                [track["name"] for track in timeline["tracks"]["children"]],
                ["主画面", "叠加"],
            )

            self.run_script(
                "generate-kdenlive", "--project-id", "demo_中文", "--project-revision", "1",
                "--otio", str(revision_dir / "timeline.otio"), "--output-root", str(output),
                "--result-output", str(root / "kdenlive_result.json"),
            )
            mlt = ET.parse(revision_dir / "timeline.kdenlive").getroot()
            self.assertEqual(len(mlt.findall("./playlist")), 2)
            self.assertEqual(len(mlt.findall("./tractor/track")), 2)
            # Without a blend the top track would hide the cut underneath it.
            transitions = mlt.findall("./tractor/transition")
            self.assertEqual(len(transitions), 1)
            self.assertEqual(transitions[0].attrib["mlt_service"], "frei0r.cairoblend")
            self.assertEqual(transitions[0].attrib["b_track"], "1")

            validation = root / "validation.json"
            self.run_script(
                "validate", "--project-id", "demo_中文", "--project-revision", "1",
                "--otio", str(revision_dir / "timeline.otio"),
                "--kdenlive", str(revision_dir / "timeline.kdenlive"),
                "--result-output", str(validation),
            )
            result = json.loads(validation.read_text(encoding="utf-8"))
            self.assertEqual(result["clip_count"], 3)
            self.assertEqual(result["track_count"], 2)

    def test_rejects_unknown_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            edl = root / "edl.json"
            storyboard = root / "storyboard.md"
            storyboard.write_text("# 分镜\n", encoding="utf-8")
            write_layered_edl(edl)
            payload = json.loads(edl.read_text(encoding="utf-8"))
            payload["clips"][2]["layer"] = "foreground"
            edl.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            completed = self.run_script(
                "generate-otio", "--project-id", "demo_中文", "--project-revision", "1",
                "--edl", str(edl), "--storyboard", str(storyboard),
                "--output-root", str(root / "edit_handoff"),
                expected=2,
            )
            self.assertIn("unknown layer", completed.stderr)


if __name__ == "__main__":
    unittest.main()
