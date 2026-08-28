#!/usr/bin/env python3
"""Contract tests for the editor-independent handoff pack backend."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "scripts" / "edit_backends" / "handoff_pack.py"


def run_backend(*args: str, expected_returncode: int = 0) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, str(BACKEND), *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != expected_returncode:
        raise AssertionError(
            f"backend returned {result.returncode}, expected {expected_returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return json.loads(result.stdout)


def make_inputs(base: Path, *, raw_second_source: bool = False, gap: bool = False) -> tuple[Path, Path, Path, Path]:
    project = base / "project"
    media = project / "media"
    media.mkdir(parents=True)
    first = media / "intro.mp4"
    first.write_bytes(b"fixture-media-intro")
    if raw_second_source:
        second = project / "00_RawVault_不可直用" / "360原始组" / "camera.LRF"
        second.parent.mkdir(parents=True)
    else:
        second = media / "middle.mp4"
    second.write_bytes(b"fixture-media-middle")

    second_start = 2.5 if gap else 2.0
    edl = {
        "spec_version": "content_os_v0.2",
        "doc_type": "edit_decision_list",
        "project_id": "project_handoff_test",
        "local_project_path": str(project),
        "clips": [
            {
                "slot": 10,
                "time_range": "0.000-2.000",
                "purpose": "开场",
                "visual_need": "正面镜头",
                "edit_note": "保持人物出场",
                "caption": "第一句字幕",
                "candidate_files": ["media/intro.mp4"],
            },
            {
                "slot": 20,
                "time_range": f"{second_start:.3f}-4.000",
                "purpose": "转折",
                "visual_need": "细节镜头",
                "edit_note": "保留停顿",
                "caption": "第二句字幕",
                "candidate_files": [str(second.relative_to(project))],
            },
        ],
    }
    edl_path = base / "06_edit_decision_list.json"
    edl_path.write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
    storyboard = base / "05_storyboard.md"
    storyboard.write_text("# Storyboard\n\n镜头按 EDL 顺序执行。\n", encoding="utf-8")
    materials = base / "materials.json"
    materials.write_text(
        json.dumps({"local_project_path": str(project), "files": [str(first), str(second)]}, ensure_ascii=False),
        encoding="utf-8",
    )
    output_root = project / "90_Draft_Project" / "edit_handoff"
    return edl_path, storyboard, materials, output_root


class EditHandoffPackTest(unittest.TestCase):
    def test_generate_and_validate_immutable_handoff_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            edl, storyboard, materials, output_root = make_inputs(base)
            result_path = base / "generate_result.json"
            generated = run_backend(
                "generate",
                "--project-id",
                "project_handoff_test",
                "--project-revision",
                "3",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
                "--result-output",
                str(result_path),
            )
            self.assertEqual(generated["status"], "done")
            self.assertEqual(generated["editor_backend"], "handoff_pack")
            package = (output_root / "3").resolve()
            self.assertEqual(generated["project_revision"], 3)
            self.assertEqual(Path(str(generated["pack_dir"])), package)
            for name in ("manifest.json", "clips.csv", "captions.srt", "剪辑交接说明.md", "预览说明.md"):
                self.assertTrue((package / name).is_file(), name)
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8"))["manifest"], generated["manifest"])

            with (package / "clips.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["timeline_order"] for row in rows], ["1", "2"])
            self.assertEqual([row["timeline_start_sec"] for row in rows], ["0.0", "2.0"])
            self.assertEqual([row["timeline_end_sec"] for row in rows], ["2.0", "4.0"])
            srt = (package / "captions.srt").read_text(encoding="utf-8")
            self.assertIn("00:00:00,000 --> 00:00:02,000", srt)
            self.assertIn("00:00:02,000 --> 00:00:04,000", srt)
            self.assertIn("没有把原始材料重新渲染成预览视频", (package / "预览说明.md").read_text(encoding="utf-8"))

            validation = run_backend("validate", "--manifest", str(package / "manifest.json"))
            self.assertEqual(validation["status"], "passed")
            self.assertEqual(validation["clip_count"], 2)
            self.assertEqual(validation["caption_count"], 2)
            self.assertEqual(validation["preview_kind"], "explanation")

            repeated = run_backend(
                "generate",
                "--project-revision",
                "3",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
                expected_returncode=2,
            )
            self.assertEqual(repeated["status"], "blocked")
            self.assertEqual(repeated["error_code"], "revision_exists")

    def test_blocks_direct_raw360_source_with_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            edl, storyboard, materials, output_root = make_inputs(base, raw_second_source=True)
            result_path = base / "blocked_result.json"
            blocked = run_backend(
                "generate",
                "--project-revision",
                "4",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
                "--result-output",
                str(result_path),
                expected_returncode=2,
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["error_code"], "raw360_reframe_required")
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8"))["error_code"], "raw360_reframe_required")
            self.assertFalse((output_root / "4").exists())

    def test_revision_basis_is_hash_bound_to_the_handoff_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            edl, storyboard, materials, output_root = make_inputs(base)
            basis = base / "confirmed_revision.json"
            basis.write_text(
                json.dumps(
                    {
                        "spec_version": "content_os_v0.2",
                        "doc_type": "confirmed_revision_basis",
                        "project_id": "project_handoff_test",
                        "project_revision": 7,
                        "change_request_id": "change_20260828_001",
                        "editor_backend": "handoff_pack",
                        "change_summary": {
                            "requested_location": "第二段",
                            "requested_change": "保留停顿",
                            "reason": "人工确认",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            generated = run_backend(
                "generate", "--project-revision", "7", "--edl", str(edl), "--storyboard", str(storyboard),
                "--materials", str(materials), "--output-root", str(output_root), "--revision-basis", str(basis),
            )
            manifest_path = Path(str(generated["manifest"]))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            descriptor = next(item for item in manifest["inputs"] if item["role"] == "confirmed_revision_basis")
            self.assertEqual(descriptor["change_request_id"], "change_20260828_001")
            validation = run_backend("validate", "--manifest", str(manifest_path))
            self.assertEqual(validation["revision_basis"], descriptor)

            basis.write_text(basis.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            blocked = run_backend("validate", "--manifest", str(manifest_path), expected_returncode=2)
            self.assertEqual(blocked["error_code"], "revision_basis_checksum")

    def test_rejects_gapped_timeline_and_tampered_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            edl, storyboard, materials, output_root = make_inputs(base, gap=True)
            blocked = run_backend(
                "generate",
                "--project-revision",
                "5",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
                expected_returncode=2,
            )
            self.assertEqual(blocked["error_code"], "timeline_gap_or_overlap")

            ordered_edl = json.loads(edl.read_text(encoding="utf-8"))
            ordered_edl["clips"] = list(reversed(ordered_edl["clips"]))
            edl.write_text(json.dumps(ordered_edl, ensure_ascii=False), encoding="utf-8")
            blocked = run_backend(
                "generate",
                "--project-revision",
                "5",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
                expected_returncode=2,
            )
            self.assertEqual(blocked["error_code"], "edl_order_mismatch")

            edl, storyboard, materials, output_root = make_inputs(base / "valid")
            generated = run_backend(
                "generate",
                "--project-revision",
                "6",
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--materials",
                str(materials),
                "--output-root",
                str(output_root),
            )
            package = Path(str(generated["pack_dir"]))
            with (package / "clips.csv").open("a", encoding="utf-8") as handle:
                handle.write("\n")
            blocked = run_backend("validate", "--manifest", str(package / "manifest.json"), expected_returncode=2)
            self.assertEqual(blocked["error_code"], "artifact_checksum_mismatch")


if __name__ == "__main__":
    unittest.main()
