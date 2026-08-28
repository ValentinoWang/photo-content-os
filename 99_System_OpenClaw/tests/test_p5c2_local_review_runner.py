"""Regression tests for the P5C2 local output-review capability contract."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mac_openclaw_runner as runner  # noqa: E402


def load_output_review():
    spec = importlib.util.spec_from_file_location("p5c2_output_review", SCRIPTS / "19_review_output_video.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


output_review = load_output_review()


class P5C2LocalReviewRunnerTests(unittest.TestCase):
    def test_runner_passes_declared_review_capabilities_and_available_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            video = root / "candidate.mp4"
            video.write_bytes(b"fixture")
            bgm_dir = root / "bgm-review"
            bgm_dir.mkdir()
            vault = root / "vault"
            package = vault / "08_内容项目" / "project"
            package.mkdir(parents=True)
            config = runner.RunnerConfig(vault_root=vault, workspace_root=root / "workspace")
            task = {
                "task_id": "p5c2-review",
                "project_id": "project",
                "idea_id": "idea",
                "inputs": {
                    "local_project_path": str(project),
                    "output_video_path": str(video),
                    "bgm_review_dir": str(bgm_dir),
                },
                "expected_outputs": ["reports/project_output_review.md"],
            }

            with patch.object(runner, "run_command") as run_command, patch.object(runner, "output_review_result"):
                runner.run_output_review(config, task, root / "result.yaml", execute=True)

            args = run_command.call_args.args[0]
            self.assertIn("--project-root", args)
            self.assertEqual(args[args.index("--project-root") + 1], str(project))
            self.assertIn("--bgm-review-dir", args)
            self.assertEqual(args[args.index("--bgm-review-dir") + 1], str(bgm_dir.resolve()))
            self.assertIn("--rhythm-sync", args)
            self.assertIn("--run-vlm-review", args)
            self.assertIn("--require-production-capabilities", args)

    def test_missing_bgm_context_withholds_partial_strategy_score(self) -> None:
        context = output_review.ProjectContext(
            project_root=Path("/project"),
            target_platforms=["抖音"],
            project_goal="短视频",
            notes=[],
        )

        review = output_review.creative_review_for_version(
            version_name="candidate",
            probe={"width": 1080, "height": 1920},
            video_metrics={"short_side": 1080, "letterbox_or_pillarbox_risk": "low", "compression_risk": "low"},
            bgm_review=None,
            context=context,
        )

        self.assertEqual(review["status"], "partial")
        self.assertIsNone(review["score"])
        self.assertEqual(review["available_weight_ratio"], 0.42)
        self.assertIn("策略分未出具", review["coverage_note"])

    def test_unavailable_vlm_withholds_strategy_score_and_marks_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "candidate.mp4"
            video.write_bytes(b"fixture")
            version = {
                "version_name": "candidate",
                "technical_status": "pass",
                "risk_flags": [],
                "probe": {},
                "video_metrics": {},
                "audio_metrics": {},
                "artifacts": {"contact_sheet": "", "scene_change_sheet": ""},
                "creative_review": {
                    "score": 76.0,
                    "confidence": "medium",
                    "status": "complete",
                    "dimensions": {"rhythm": {"score": 80}},
                },
            }
            with (
                patch.object(output_review, "check_dependencies", return_value={"errors": [], "warnings": []}),
                patch.object(output_review, "review_one", return_value=version),
                patch.object(
                    output_review,
                    "run_vlm_semantic_review",
                    return_value={"schema_version": output_review.VLM_SCHEMA_VERSION, "status": "failed", "reason": "本机 AI 不可用"},
                ),
                patch.object(output_review, "write_metrics_json"),
                patch.object(output_review, "write_result_yaml"),
                patch.object(output_review, "write_markdown_report"),
            ):
                result = output_review.review_output_video(
                    task_id="p5c2-review",
                    project_id="project",
                    idea_id="idea",
                    videos=[output_review.ReviewInput("candidate", video)],
                    output_root=root / "output",
                    report_output=root / "report.md",
                    metrics_output=root / "metrics.json",
                    result_output=root / "result.yaml",
                    brief=None,
                    script=None,
                    publish_pack=None,
                    run_vlm_review=True,
                    require_production_capabilities=True,
                )

        self.assertEqual(result["task_status"], "partial")
        self.assertFalse(result["publish_as_final"])
        self.assertIsNone(result["strategy_preferred_score"])
        self.assertEqual(result["review_capability_status"]["vlm_semantic_review"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
