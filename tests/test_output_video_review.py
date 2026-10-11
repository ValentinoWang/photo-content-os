#!/usr/bin/env python3
"""Tests for output-video review metrics and result mapping."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _support import load_script

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

output_review = load_script("19_review_output_video.py", "output_review", register=True)


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(args)}")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class OutputVideoReviewIntegrationTest(unittest.TestCase):
    def test_low_resolution_video_generates_warning_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "lowres.mp4"
            run_ffmpeg(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=480x854:rate=25",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=44100",
                    "-t",
                    "1.2",
                    "-pix_fmt",
                    "yuv420p",
                    "-shortest",
                    str(video),
                ]
            )

            result = output_review.review_output_video(
                task_id="task_test_lowres",
                project_id="project_test",
                idea_id="idea_test",
                videos=[output_review.ReviewInput("current", video)],
                output_root=root / "review",
                report_output=root / "project_output_review.md",
                metrics_output=root / "review/metrics.json",
                result_output=root / "review/result.yaml",
                brief=None,
                script=None,
                publish_pack=None,
                artifact_base=root,
            )

            metrics = json.loads((root / "review/metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(result["task_status"], "success")
            self.assertIn("resolution_below_1080_short_side", result["risk_flags"])
            self.assertIn("strategy_preferred_version", result)
            self.assertEqual(metrics["schema_version"], "output_review.v1")
            self.assertIn("creative_review", metrics)
            self.assertIn("creative_review", metrics["versions"][0])
            self.assertTrue((root / "project_output_review.md").exists())
            self.assertTrue((root / "review/current/contact_sheet.jpg").exists())

    def test_black_video_generates_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "black.mp4"
            run_ffmpeg(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=480x854:r=25",
                    "-t",
                    "1.2",
                    "-pix_fmt",
                    "yuv420p",
                    str(video),
                ]
            )

            result = output_review.review_output_video(
                task_id="task_test_black",
                project_id="project_test",
                idea_id="idea_test",
                videos=[output_review.ReviewInput("current", video)],
                output_root=root / "review",
                report_output=root / "project_output_review.md",
                metrics_output=root / "review/metrics.json",
                result_output=root / "review/result.yaml",
                brief=None,
                script=None,
                publish_pack=None,
                artifact_base=root,
            )

            self.assertEqual(result["technical_status"], "fail")
            self.assertIn("mostly_black_frames", result["risk_flags"])

    def test_rhythm_sync_generates_contract_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "rhythm.mp4"
            run_ffmpeg(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=720x1280:rate=25",
                    "-f",
                    "lavfi",
                    "-i",
                    "aevalsrc=if(lt(mod(t\\,0.5)\\,0.08)\\,0.8*sin(2*PI*880*t)\\,0):s=44100",
                    "-t",
                    "2.4",
                    "-pix_fmt",
                    "yuv420p",
                    "-shortest",
                    str(video),
                ]
            )

            result = output_review.review_output_video(
                task_id="task_test_rhythm",
                project_id="project_test",
                idea_id="idea_test",
                videos=[output_review.ReviewInput("rhythm_a", video)],
                output_root=root / "review",
                report_output=root / "project_output_review.md",
                metrics_output=root / "review/metrics.json",
                result_output=root / "review/result.yaml",
                brief=None,
                script=None,
                publish_pack=None,
                artifact_base=root,
                rhythm_sync=True,
                rhythm_profile="general_bgm_edit",
            )

            metrics = json.loads((root / "review/metrics.json").read_text(encoding="utf-8"))
            rhythm_metrics = root / "review/rhythm_sync/rhythm_sync_metrics.json"
            rhythm_result = root / "review/rhythm_sync/rhythm_sync_result.yaml"
            rhythm_report = root / "review/rhythm_sync/rhythm_sync_report.md"

            self.assertTrue(result["rhythm_sync_enabled"])
            self.assertEqual(result["rhythm_profile"], "general_bgm_edit")
            self.assertTrue(rhythm_metrics.exists())
            self.assertTrue(rhythm_result.exists())
            self.assertTrue(rhythm_report.exists())
            self.assertEqual(metrics["rhythm_sync"]["schema_version"], "rhythm_sync_review.v1")
            self.assertEqual(metrics["rhythm_sync"]["preferred_version"], "rhythm_a")
            version = metrics["rhythm_sync"]["versions"][0]
            self.assertTrue((root / version["artifacts"]["audio_events"]).exists())
            self.assertTrue((root / version["artifacts"]["visual_events"]).exists())
            self.assertTrue((root / version["artifacts"]["matches"]).exists())
            self.assertIn("final_score", version["scores"])
            self.assertIn("edit_suggestions", version)
            self.assertGreaterEqual(len(version["edit_suggestions"]), 1)
            self.assertIn("edit_path", version)
            self.assertIsInstance(version["edit_path"], list)


class OutputVideoReviewUnitTest(unittest.TestCase):
    def test_map_recommendation_keeps_unknown_brief_human_required(self) -> None:
        result = output_review.map_recommendation(
            task_status="success",
            technical_status="pass",
            current_brief_fit="unknown",
            human_decision_required=True,
        )

        self.assertEqual(result["recommendation"], "small_fix")
        self.assertFalse(result["publish_as_final"])
        self.assertTrue(result["human_decision_required"])

    def test_missing_dependencies_are_blocked_not_technical_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(output_review.shutil, "which", return_value=None):
                result = output_review.review_output_video(
                    task_id="task_test_deps",
                    project_id="project_test",
                    idea_id="idea_test",
                    videos=[output_review.ReviewInput("current", root / "missing.mp4")],
                    output_root=root / "review",
                    report_output=root / "project_output_review.md",
                    metrics_output=root / "review/metrics.json",
                    result_output=root / "review/result.yaml",
                    brief=None,
                    script=None,
                    publish_pack=None,
                    artifact_base=root,
                )

            self.assertEqual(result["task_status"], "blocked")
            self.assertEqual(result["technical_status"], "unknown")
            self.assertFalse(result["publish_as_final"])

    def test_creative_review_uses_bgm_step_alignment(self) -> None:
        context = output_review.ProjectContext(
            project_root=None,
            target_platforms=["抖音", "小红书"],
            project_goal="第一视角体验清华毕业典礼",
            notes=[],
        )
        review = output_review.creative_review_for_version(
            version_name="蓝袍黄领翻拍_单人会场舞台加长版_V1b",
            probe={"width": 1920, "height": 1080},
            video_metrics={
                "short_side": 1080,
                "letterbox_or_pillarbox_risk": "low",
                "compression_risk": "low",
            },
            bgm_review={
                "step_alignment": {"matched_ratio": 0.586, "matched_step_count": 17, "step_peak_count": 29},
                "alignment": {"matched_ratio": None},
                "rhythm": {"estimated_bpm": 109.1},
                "visual": {"intro_effect_proxy": {"candidate_intentional_blur_or_overexposure": True}},
                "timeline_events": [{"timestamp_sec": 0.5, "type": "step_motion_peak_proxy"}],
            },
            context=context,
        )

        self.assertEqual(review["dimensions"]["rhythm"]["score"], 59)
        self.assertEqual(review["dimensions"]["platform_format"]["format"], "horizontal")
        self.assertTrue(review["human_review_required"])
        self.assertEqual(review["algorithm_version"], "video_scoring_judgement.v3")
        self.assertEqual(review["weights_version"], "creative_strategy_weights.v3")
        self.assertEqual(review["weights"]["platform_format"], 0.10)
        self.assertEqual(review["weights"]["opening_hook"], 0.23)
        self.assertEqual(review["weights"]["composition"], 0.20)

    def test_creative_strategy_weights_v3_sum_to_one(self) -> None:
        self.assertEqual(output_review.CREATIVE_STRATEGY_ALGORITHM_VERSION, "video_scoring_judgement.v3")
        self.assertAlmostEqual(sum(weight for _, weight in output_review.CREATIVE_STRATEGY_WEIGHTS), 1.0)
        self.assertEqual(dict(output_review.CREATIVE_STRATEGY_WEIGHTS)["platform_format"], 0.10)
        self.assertEqual(dict(output_review.CREATIVE_STRATEGY_WEIGHTS)["opening_hook"], 0.23)
        self.assertEqual(dict(output_review.CREATIVE_STRATEGY_WEIGHTS)["composition"], 0.20)

    def test_apply_vlm_semantic_review_updates_strategy_score(self) -> None:
        versions = [
            {
                "version_name": "单人会场舞台加长版",
                "creative_review": {
                    "score": 67.3,
                    "confidence": "low",
                    "dimensions": {"person_state": {"status": "needs_visual_semantic_review"}},
                },
            }
        ]
        output_review.apply_vlm_semantic_review(
            versions,
            {
                "schema_version": "local_output_vlm_semantic_review.v1",
                "status": "success",
                "confidence": "medium",
                "versions": [
                    {
                        "version_name": "单人会场舞台加长版",
                        "overall_score": 82,
                        "person_state_score": 78,
                        "composition_aesthetic_score": 80,
                        "manual_review_focus": ["确认第一帧虚焦是否为设计效果"],
                    }
                ],
            },
        )

        creative = versions[0]["creative_review"]
        self.assertEqual(creative["score_before_vlm"], 67.3)
        self.assertEqual(creative["score"], 73.9)
        self.assertEqual(creative["confidence"], "medium")
        self.assertEqual(creative["dimensions"]["person_state"]["status"], "automated_vlm_review")

    def test_rhythm_matching_is_one_to_one_and_signed(self) -> None:
        audio_events = [
            {"id": "a1", "time": 1.0, "type": "beat_grid", "strength": 0.8, "confidence": 0.7},
            {"id": "a2", "time": 2.0, "type": "accent_peak", "strength": 0.9, "confidence": 0.8},
        ]
        visual_events = [
            {"id": "v1", "time": 1.03, "type": "step_motion_peak_proxy", "strength": 0.8, "confidence": 0.6},
            {"id": "v2", "time": 1.05, "type": "step_motion_peak_proxy", "strength": 0.7, "confidence": 0.6},
            {"id": "v3", "time": 1.96, "type": "scene_cut", "strength": 0.9, "confidence": 0.7},
        ]

        matches = output_review.align_audio_visual_events(audio_events, visual_events)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["visual_event_id"], "v1")
        self.assertEqual(matches[0]["audio_event_id"], "a1")
        self.assertGreater(matches[0]["delta_sec"], 0)
        self.assertEqual(matches[1]["visual_event_id"], "v3")
        self.assertEqual(matches[1]["audio_event_id"], "a2")
        self.assertLess(matches[1]["delta_sec"], 0)

    def test_rhythm_score_uses_profile_weights(self) -> None:
        audio_events = [
            {"id": "a1", "time": 1.0, "type": "beat_grid", "strength": 0.8, "confidence": 0.7},
            {"id": "a2", "time": 2.0, "type": "accent_peak", "strength": 0.9, "confidence": 0.8},
        ]
        visual_events = [
            {"id": "v1", "time": 1.03, "type": "step_motion_peak_proxy", "strength": 0.8, "confidence": 0.6},
            {"id": "v2", "time": 2.04, "type": "scene_cut", "strength": 0.9, "confidence": 0.7},
        ]
        matches = output_review.align_audio_visual_events(audio_events, visual_events)

        single_scores, single_diag, _, single_suggestions = output_review.score_rhythm_sync(
            profile="single_person_stage_walk",
            audio_events=audio_events,
            visual_events=visual_events,
            matches=matches,
            probe={"width": 1080, "height": 1920},
            risk_flags=[],
            audio_meta={"estimated_bpm": 120.0},
        )
        split_scores, split_diag, _, split_suggestions = output_review.score_rhythm_sync(
            profile="split_screen_comparison",
            audio_events=audio_events,
            visual_events=visual_events,
            matches=matches,
            probe={"width": 1080, "height": 1920},
            risk_flags=[],
            audio_meta={"estimated_bpm": 120.0},
        )

        self.assertEqual(single_diag["profile_used"], "single_person_stage_walk")
        self.assertEqual(split_diag["profile_used"], "split_screen_comparison")
        self.assertNotEqual(single_scores["final_score"], split_scores["final_score"])
        self.assertGreater(single_scores["step_sync"], 0)
        self.assertIsInstance(single_suggestions, list)
        self.assertIsInstance(split_suggestions, list)

    def test_timing_edit_path_orders_candidates(self) -> None:
        audio_events = [
            {"id": "a1", "time": 0.5, "type": "beat_grid", "strength": 0.8, "confidence": 0.7},
            {"id": "a2", "time": 1.0, "type": "accent_peak", "strength": 0.9, "confidence": 0.8},
            {"id": "a3", "time": 1.5, "type": "beat_grid", "strength": 0.8, "confidence": 0.7},
        ]
        visual_events = [
            {"id": "v1", "time": 0.51, "type": "step_motion_peak_proxy", "strength": 0.8, "confidence": 0.6},
            {"id": "v2", "time": 1.01, "type": "scene_cut", "strength": 0.9, "confidence": 0.7},
            {"id": "v3", "time": 1.49, "type": "global_motion_peak", "strength": 0.7, "confidence": 0.6},
        ]
        matches = output_review.align_audio_visual_events(audio_events, visual_events)

        path = output_review.build_timing_edit_path(visual_events, audio_events, matches)

        self.assertGreaterEqual(len(path), 2)
        self.assertEqual([node["order"] for node in path], list(range(1, len(path) + 1)))
        self.assertLess(path[0]["visual_time"], path[-1]["visual_time"])


if __name__ == "__main__":
    unittest.main()
