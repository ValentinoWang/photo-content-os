#!/usr/bin/env python3
"""Tests for the Jianying native import package route."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


class JianyingNativeImportPackageTest(unittest.TestCase):
    def test_plan_to_native_import_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            media = project / "media"
            media.mkdir(parents=True)
            for index, color in [(1, "red"), (2, "blue")]:
                run_cmd(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c={color}:s=540x960:d=3:r=30",
                        str(media / f"clip{index}.mp4"),
                    ]
                )

            plan = {
                "spec_version": "content_os_v0.1",
                "doc_type": "jianying_draft_plan",
                "project_id": "test_project",
                "idea_id": "idea_test",
                "draft_name": "jy_roughcut_unit_native",
                "target": {"width": 1080, "height": 1920, "fps": 30, "duration_sec": 4, "platform": "douyin"},
                "source_edl": "06_edit_decision_list.json",
                "tracks": [
                    {
                        "track_id": "video_main",
                        "type": "video",
                        "clips": [
                            {
                                "slot": 1,
                                "timeline_start_sec": 0.0,
                                "duration_sec": 2.0,
                                "source_file": str(media / "clip1.mp4"),
                                "source_start_sec": 0.0,
                                "source_duration_sec": 2.0,
                                "purpose": "开头",
                                "caption": "第一段",
                            },
                            {
                                "slot": 2,
                                "timeline_start_sec": 2.0,
                                "duration_sec": 2.0,
                                "source_file": str(media / "clip2.mp4"),
                                "source_start_sec": 0.0,
                                "source_duration_sec": 2.0,
                                "purpose": "第二段",
                                "caption": "第二段",
                            },
                        ],
                    },
                    {
                        "track_id": "text_caption",
                        "type": "text",
                        "clips": [
                            {"timeline_start_sec": 0.0, "duration_sec": 2.0, "text": "第一段"},
                            {"timeline_start_sec": 2.0, "duration_sec": 2.0, "text": "第二段"},
                        ],
                    },
                    {"track_id": "audio_bgm", "type": "audio", "clips": []},
                ],
                "bgm": {"source_file": "", "timeline_start_sec": 0.0, "volume": 0.7},
                "constraints": {"strict_mode": True, "no_auto_export": True, "human_must_open_check": True},
            }
            plan_path = base / "06b_jianying_draft_plan.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            result_path = base / "06d_native_import_pack_result.yaml"
            output_root = base / "native_import_packs"
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "26_create_native_import_pack.py"),
                    "--plan",
                    str(plan_path),
                    "--output-root",
                    str(output_root),
                    "--result-output",
                    str(result_path),
                ]
            )
            result = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "done")
            self.assertEqual(result["doc_type"], "native_import_pack_result")
            package_dir = Path(result["pack_dir"])
            self.assertEqual(result["pack_name"], "jy_import_pack_unit_native")
            self.assertTrue((package_dir / "01_clips" / "001_000-002_开头.mp4").exists())
            self.assertTrue((package_dir / "01_clips" / "002_002-004_第二段.mp4").exists())
            self.assertTrue((package_dir / "02_captions" / "captions.srt").exists())
            self.assertTrue((package_dir / "02_captions" / "README_字幕导入.md").exists())
            self.assertTrue((package_dir / "04_preview" / "preview_roughcut.mp4").exists())
            self.assertTrue((package_dir / "edit_manifest.json").exists())
            self.assertTrue((package_dir / "README_导入剪映.md").exists())
            self.assertEqual(result["caption_count"], 2)
            self.assertIn("文本 -> 本地字幕", result["contents"]["caption_import_method"])

            validation_path = base / "native_validation.yaml"
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "27_validate_native_import_pack.py"),
                    "--plan",
                    str(plan_path),
                    "--result",
                    str(result_path),
                    "--validation-output",
                    str(validation_path),
                ]
            )
            validation = yaml.safe_load(validation_path.read_text(encoding="utf-8"))
            self.assertEqual(validation["status"], "passed")
            self.assertEqual(validation["doc_type"], "native_import_pack_validation")
            self.assertEqual(validation["clip_count"], 2)
            self.assertEqual(validation["caption_count"], 2)
            self.assertTrue(validation["no_direct_draft_json"])
            self.assertTrue(validation["raw360_direct_use_blocked"])
            self.assertEqual(validation["target_video_spec"]["codec_name"], "h264")

    def test_native_import_pack_rejects_raw360_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw = base / "00_RawVault_不可直用" / "400米第一视角_360原始组_待重构" / "全程记录_360原始组.LRF"
            raw.parent.mkdir(parents=True)
            raw.write_bytes(b"not-a-production-source")

            plan = {
                "spec_version": "content_os_v0.1",
                "doc_type": "jianying_draft_plan",
                "project_id": "test_project",
                "idea_id": "idea_test",
                "draft_name": "jy_roughcut_raw_blocked",
                "target": {"width": 1080, "height": 1920, "fps": 30, "duration_sec": 2, "platform": "douyin"},
                "source_edl": "06_edit_decision_list.json",
                "tracks": [
                    {
                        "track_id": "video_main",
                        "type": "video",
                        "clips": [
                            {
                                "slot": 1,
                                "timeline_start_sec": 0.0,
                                "duration_sec": 2.0,
                                "source_file": str(raw),
                                "source_start_sec": 0.0,
                                "source_duration_sec": 2.0,
                                "purpose": "第一视角",
                            }
                        ],
                    },
                    {"track_id": "text_caption", "type": "text", "clips": [{"timeline_start_sec": 0.0, "duration_sec": 2.0, "text": "第一视角"}]},
                    {"track_id": "audio_bgm", "type": "audio", "clips": []},
                ],
                "bgm": {"source_file": "", "timeline_start_sec": 0.0, "volume": 0.7},
                "constraints": {"strict_mode": True, "no_auto_export": True, "human_must_open_check": True},
            }
            plan_path = base / "06b_jianying_draft_plan.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "26_create_native_import_pack.py"),
                    "--plan",
                    str(plan_path),
                    "--output-root",
                    str(base / "native_import_packs"),
                    "--result-output",
                    str(base / "06d_native_import_pack_result.yaml"),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot render RawVault/OSV/LRF 360 source directly", result.stderr)


if __name__ == "__main__":
    unittest.main()
