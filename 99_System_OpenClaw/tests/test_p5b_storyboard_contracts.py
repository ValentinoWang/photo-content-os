from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


storyboard = load_script("18_generate_storyboard_edl.py", "p5b_storyboard")
jianying = load_script("23_generate_jianying_draft_plan.py", "p5b_jianying")
import jianying_roughcut_common as roughcut_common  # noqa: E402


def valid_edl() -> dict[str, object]:
    return {
        "source_script_used": True,
        "clips": [
            {
                "slot": 1,
                "time_range": "0.000-2.000",
                "source_start_sec": 0,
                "purpose": "开场",
                "visual_need": "人物进入画面",
                "caption": "开始",
                "candidate_files": ["clip.mp4"],
                "edit_note": "硬切",
            }
        ],
    }


class StoryboardContractTests(unittest.TestCase):
    def test_quoted_frontmatter_is_accepted_and_invocation_metadata_is_canonical(self) -> None:
        raw = {
            "storyboard_markdown": (
                '---\n'
                'doc_type: "storyboard"\n'
                'writer_agent: "mac_openclaw"\n'
                'generation_model: "gpt-test"\n'
                'generation_reasoning: "xhigh"\n'
                '---\n\n'
                "# 分镜\n\n镜头一"
            ),
            "edl_json": valid_edl(),
        }
        markdown, _ = storyboard.validate_outputs(raw, model="gpt-test", reasoning="xhigh")
        metadata = storyboard.parse_frontmatter(markdown)
        self.assertEqual(metadata["doc_type"], "storyboard")
        self.assertEqual(metadata["writer_agent"], "mac_openclaw")
        self.assertEqual(metadata["generation_model"], "gpt-test")
        self.assertEqual(metadata["generation_reasoning"], "xhigh")
        self.assertEqual(metadata["spec_version"], "content_os_v0.1")

    def test_invalid_or_unclosed_frontmatter_is_rejected(self) -> None:
        raw = {"storyboard_markdown": "---\ndoc_type: storyboard\n", "edl_json": valid_edl()}
        with self.assertRaisesRegex(RuntimeError, "frontmatter invalid"):
            storyboard.validate_outputs(raw, model="gpt-test", reasoning="xhigh")

    def test_conflicting_invocation_metadata_is_rejected(self) -> None:
        raw = {
            "storyboard_markdown": "---\ndoc_type: storyboard\nwriter_agent: mac_openclaw\ngeneration_model: other\n---\n\n# 分镜",
            "edl_json": valid_edl(),
        }
        with self.assertRaisesRegex(RuntimeError, "generation_model"):
            storyboard.validate_outputs(raw, model="gpt-test", reasoning="xhigh")

    def test_missing_invocation_metadata_is_stamped_by_script(self) -> None:
        raw = {
            "storyboard_markdown": "---\ndoc_type: storyboard\nwriter_agent: mac_openclaw\n---\n\n# 分镜",
            "edl_json": valid_edl(),
        }
        markdown, _ = storyboard.validate_outputs(raw, model="gpt-test", reasoning="xhigh")
        metadata = storyboard.parse_frontmatter(markdown)
        self.assertEqual(metadata["generation_model"], "gpt-test")
        self.assertEqual(metadata["generation_reasoning"], "xhigh")

    def test_json_response_accepts_one_outer_json_fence(self) -> None:
        parsed = storyboard.parse_llm_json('```json\n{"storyboard_markdown": "ok", "edl_json": {}}\n```')
        self.assertEqual(parsed["storyboard_markdown"], "ok")

    def test_json_response_rejects_wrong_or_unclosed_fence(self) -> None:
        for response in ("```yaml\n{}\n```", "```json\n{}"):
            with self.assertRaisesRegex(RuntimeError, "valid JSON"):
                storyboard.parse_llm_json(response)

    def test_long_summary_has_shared_limit_and_explicit_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            summaries = project / "_ai_analysis" / "summaries"
            summaries.mkdir(parents=True)
            evidence_boundary = "证据边界：超出提示预算后必须人工复核。"
            (summaries / "m1_clip.summary.md").write_text("画面事实\n" + "视觉证据" * 1000 + evidence_boundary, encoding="utf-8")
            value = storyboard.summary_text(project, {"media_id": "m1", "relative_path": "clip.mp4"})
            self.assertLessEqual(len(value), storyboard.MAX_SUMMARY_CHARS)
            self.assertEqual(storyboard.MAX_SUMMARY_CHARS, 2500)
            self.assertIn("[已截断]", value)

    def test_short_summary_is_preserved_without_truncation_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            summaries = project / "_ai_analysis" / "summaries"
            summaries.mkdir(parents=True)
            expected = "画面事实：人物进入画面。\n证据边界：仅支持这一结论。"
            (summaries / "m1_clip.summary.md").write_text(expected, encoding="utf-8")
            value = storyboard.summary_text(project, {"media_id": "m1", "relative_path": "clip.mp4"})
            self.assertEqual(value, expected)
            self.assertNotIn("[已截断]", value)

    def test_storyboard_script_has_no_historical_slot_mapping(self) -> None:
        source = (SCRIPTS / "23_generate_jianying_draft_plan.py").read_text(encoding="utf-8")
        self.assertNotIn("slot_map", source)
        self.assertNotIn("赛前候场", source)


class JianyingContractTests(unittest.TestCase):
    def test_raw360_source_start_uses_explicit_edl_value(self) -> None:
        selected = {"path": "/tmp/new-project/camera.LRF", "is_raw360": True, "source_duration_sec": 120.0}
        self.assertEqual(jianying.source_start_from_edl(selected, {"source_start_sec": 37.5}, 4.0), 37.5)

    def test_raw360_source_start_without_project_mapping_is_rejected(self) -> None:
        selected = {"path": "/tmp/new-project/camera.LRF", "is_raw360": True, "source_duration_sec": 120.0}
        with self.assertRaisesRegex(jianying.ContractError, "explicit EDL source_start_sec"):
            jianying.source_start_from_edl(selected, {}, 4.0)

    def test_invalid_edl_project_path_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            edl_path = base / "edl.json"
            edl_path.write_text(json.dumps({"local_project_path": str(base / "missing"), "clips": []}), encoding="utf-8")
            with self.assertRaisesRegex(jianying.ContractError, "local_project_path"):
                jianying.generate_plan(edl_path, base / "local-assets.md", base / "plan.json", "test")

    def test_candidate_source_duration_keeps_actual_media_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            candidate = project / "clip.mp4"
            candidate.write_bytes(b"fixture")
            with patch.object(roughcut_common, "ffprobe_duration_sec", return_value=12.0):
                selected = roughcut_common.resolve_media_candidate(project, ["clip.mp4"], 4.0)
            self.assertEqual(selected["source_duration_sec"], 4.0)
            self.assertEqual(selected["media_duration_sec"], 12.0)


if __name__ == "__main__":
    unittest.main()
