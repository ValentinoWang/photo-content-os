#!/usr/bin/env python3
"""Tests for the Jianying roughcut draft pipeline."""

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


class JianyingDraftPipelineTest(unittest.TestCase):
    def test_edl_to_plan_to_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            project.mkdir()
            media = project / "media"
            media.mkdir()
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

            edl = {
                "spec_version": "content_os_v0.1",
                "doc_type": "edit_decision_list",
                "project_id": "test_project",
                "idea_id": "idea_test",
                "local_project_path": str(project),
                "clips": [
                    {
                        "slot": 1,
                        "time_range": "0.0-2.0",
                        "purpose": "开头",
                        "caption": "第一段",
                        "candidate_files": ["media/clip1.mp4"],
                    },
                    {
                        "slot": 2,
                        "time_range": "2.0-4.0",
                        "purpose": "第二段",
                        "caption": "第二段",
                        "candidate_files": ["media/clip2.mp4"],
                    },
                ],
            }
            edl_path = base / "06_edit_decision_list.json"
            edl_path.write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
            local_assets = base / "08_local_assets.md"
            local_assets.write_text(f"# 本地项目路径\n\n```text\n{project}\n```\n", encoding="utf-8")

            plan_path = base / "06b_jianying_draft_plan.json"
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "23_generate_jianying_draft_plan.py"),
                    "--edl",
                    str(edl_path),
                    "--local-assets",
                    str(local_assets),
                    "--output",
                    str(plan_path),
                    "--draft-name",
                    "unit_test_roughcut",
                ]
            )
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["doc_type"], "jianying_draft_plan")
            self.assertEqual(len(plan["tracks"][0]["clips"]), 2)
            self.assertEqual(len(plan["tracks"][1]["clips"]), 2)

            result_path = base / "06c_jianying_draft_result.yaml"
            draft_root = base / "drafts"
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "24_create_jianying_roughcut_draft.py"),
                    "--plan",
                    str(plan_path),
                    "--draft-root",
                    str(draft_root),
                    "--result-output",
                    str(result_path),
                ]
            )
            result = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "done")
            draft_dir = Path(result["draft_dir"])
            self.assertTrue((draft_dir / "draft_content.json").exists())
            self.assertTrue(result["media_bundled_into_draft"])
            self.assertEqual(result["bundled_media_count"], 2)
            self.assertTrue((draft_dir / "video" / "media_001.mp4").exists())
            content = json.loads((draft_dir / "draft_content.json").read_text(encoding="utf-8"))
            first_video_path = content["materials"]["videos"][0]["path"]
            self.assertTrue(first_video_path.startswith("##_draftpath_placeholder_"))
            self.assertIn("/video/media_001.mp4", first_video_path)
            self.assertEqual(content["tracks"][0]["type"], "video")
            self.assertEqual(content["tracks"][0]["name"], "")
            self.assertIs(content["tracks"][0]["is_default_name"], True)
            first_segment = content["tracks"][0]["segments"][0]
            self.assertIs(first_segment["visible"], True)
            self.assertEqual(first_segment["clip"]["alpha"], 1.0)
            self.assertIn("rotation", first_segment["clip"])
            self.assertIs(first_segment["uniform_scale"]["on"], True)
            self.assertEqual(first_segment["source_timerange"]["start"], 0)

            validation_path = base / "draft_validation.yaml"
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "25_validate_jianying_draft.py"),
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
            self.assertEqual(validation["plan_video_clips"], 2)
            self.assertEqual(validation["plan_text_clips"], 2)
            self.assertIs(validation["video_render_fields_exist"], True)

            (draft_dir / "draft_meta_info.json").write_text("opened-by-jianying", encoding="utf-8")
            run_cmd(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "25_validate_jianying_draft.py"),
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
            self.assertIs(validation["draft_meta_info_parseable"], False)

    def test_plan_generation_blocks_raw360_proxy_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            raw_dir = project / "00_RawVault_不可直用" / "400米第一视角_360原始组_待重构"
            raw_dir.mkdir(parents=True)
            raw = raw_dir / "全程记录_360原始组.LRF"
            raw.write_bytes(b"not-a-production-source")

            edl = {
                "spec_version": "content_os_v0.1",
                "doc_type": "edit_decision_list",
                "project_id": "test_project",
                "idea_id": "idea_test",
                "local_project_path": str(project),
                "clips": [
                    {
                        "slot": 1,
                        "time_range": "0.0-2.0",
                        "purpose": "第一视角",
                        "caption": "第一视角",
                        "candidate_files": [str(raw.relative_to(project))],
                    }
                ],
            }
            edl_path = base / "06_edit_decision_list.json"
            edl_path.write_text(json.dumps(edl, ensure_ascii=False), encoding="utf-8")
            local_assets = base / "08_local_assets.md"
            local_assets.write_text(f"# 本地项目路径\n\n```text\n{project}\n```\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "23_generate_jianying_draft_plan.py"),
                    "--edl",
                    str(edl_path),
                    "--local-assets",
                    str(local_assets),
                    "--output",
                    str(base / "06b_jianying_draft_plan.json"),
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot use RawVault/OSV/LRF 360 source directly", result.stderr)


if __name__ == "__main__":
    unittest.main()
