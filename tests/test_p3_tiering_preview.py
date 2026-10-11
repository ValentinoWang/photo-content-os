from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import analysis_tiering  # noqa: E402
from analysis_tiering import (  # noqa: E402
    POLICY_VERSION,
    SCHEMA_PATH,
    TierBudget,
    TieringValidationError,
    analysis_cache_key,
    analysis_tiering_document,
    cache_hit,
    evenly_spaced_indexes,
    plan_manifest,
    validate_analysis_tiering_document,
    write_cache,
)
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

    def test_schema_and_runtime_validation_cover_budgeted_output(self):
        budget = TierBudget(
            preview_images_per_asset=2,
            deep_images_per_asset=7,
            max_preview_assets=2,
            max_deep_assets=1,
            max_audio_minutes=1.0,
        )
        manifest = {
            "items": [
                {
                    "media_id": "selected",
                    "relative_path": "selected.mp4",
                    "analysis_eligible": True,
                    "project_selected": True,
                    "duration_sec": 40,
                    "has_audio": True,
                    "sha256": "a" * 64,
                },
                {
                    "media_id": "preview",
                    "relative_path": "preview.mp4",
                    "analysis_eligible": True,
                    "duration_sec": 40,
                    "has_audio": True,
                    "sha256": "b" * 64,
                },
            ]
        }
        plans = plan_manifest(manifest, model="gpt", prompt_version="v1", budget=budget)
        document = analysis_tiering_document(plans, budget)

        self.assertEqual(validate_analysis_tiering_document(document), document)
        self.assertEqual(document["schema_version"], POLICY_VERSION)
        self.assertEqual(document["budget"], budget.to_dict())
        self.assertEqual(sum(row["audio_seconds_budget"] for row in document["plans"]), 60)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], POLICY_VERSION)
        self.assertEqual(set(schema["required"]), set(document))

        default_key = analysis_cache_key(
            content_sha256="a" * 64,
            model="gpt",
            prompt_version="v1",
            tier="deep",
        )
        configured_key = analysis_cache_key(
            content_sha256="a" * 64,
            model="gpt",
            prompt_version="v1",
            tier="deep",
            budget=budget,
        )
        self.assertNotEqual(default_key, configured_key)

    def test_budget_validation_rejects_invalid_or_partial_config(self):
        for field, value in (
            ("preview_images_per_asset", True),
            ("deep_images_per_asset", -1),
            ("max_preview_assets", 1.5),
            ("max_deep_assets", -1),
            ("max_audio_minutes", float("inf")),
            ("max_audio_minutes", float("nan")),
            ("max_audio_minutes", 10**10000),
        ):
            with self.subTest(field=field):
                values = TierBudget().to_dict()
                values[field] = value
                with self.assertRaises(TieringValidationError):
                    TierBudget.from_dict(values)

        partial = TierBudget().to_dict()
        partial.pop("max_audio_minutes")
        with self.assertRaisesRegex(TieringValidationError, "budget_shape_invalid"):
            TierBudget.from_dict(partial)
        with self.assertRaisesRegex(TieringValidationError, "budget_shape_invalid"):
            TierBudget.from_dict(TierBudget().to_dict() | {"unexpected": 1})

    def test_schema_drift_fails_closed(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        schema["required"].remove("budget")
        with tempfile.TemporaryDirectory() as directory:
            drifted_path = Path(directory) / "analysis_tiering.schema.json"
            drifted_path.write_text(json.dumps(schema), encoding="utf-8")
            with mock.patch.object(analysis_tiering, "SCHEMA_PATH", drifted_path):
                with self.assertRaisesRegex(TieringValidationError, "schema_drift"):
                    analysis_tiering.load_analysis_tiering_schema()

    def test_runtime_validation_rejects_plan_contract_drift(self):
        budget = TierBudget(max_deep_assets=1, max_audio_minutes=0)
        plans = plan_manifest(
            {
                "items": [
                    {
                        "media_id": "a",
                        "relative_path": "a.jpg",
                        "analysis_eligible": True,
                        "sha256": "a" * 64,
                    }
                ]
            },
            model="gpt",
            prompt_version="v1",
            budget=budget,
        )
        valid = analysis_tiering_document(plans, budget)

        mutations = []
        extra_field = copy.deepcopy(valid)
        extra_field["plans"][0]["unexpected"] = True
        mutations.append(extra_field)
        mismatched_budget = copy.deepcopy(valid)
        mismatched_budget["plans"][0]["image_budget"] += 1
        mutations.append(mismatched_budget)
        bad_cache_key = copy.deepcopy(valid)
        bad_cache_key["plans"][0]["cache_key"] = "sha256:not-a-digest"
        mutations.append(bad_cache_key)
        invalid_tier = copy.deepcopy(valid)
        invalid_tier["plans"][0]["tier"] = []
        mutations.append(invalid_tier)
        duplicate = copy.deepcopy(valid)
        duplicate["plans"].append(copy.deepcopy(duplicate["plans"][0]))
        mutations.append(duplicate)
        deep_budget_exceeded = copy.deepcopy(valid)
        extra_deep = copy.deepcopy(deep_budget_exceeded["plans"][0])
        extra_deep["media_id"] = "b"
        extra_deep["relative_path"] = "b.jpg"
        deep_budget_exceeded["plans"].append(extra_deep)

        preview_budget = TierBudget(max_preview_assets=1, max_deep_assets=0, max_audio_minutes=0)
        preview_valid = analysis_tiering_document(
            plan_manifest(
                {
                    "items": [
                        {
                            "media_id": "preview-a",
                            "relative_path": "preview-a.jpg",
                            "analysis_eligible": True,
                            "sha256": "b" * 64,
                        }
                    ]
                },
                model="gpt",
                prompt_version="v1",
                budget=preview_budget,
            ),
            preview_budget,
        )
        preview_budget_exceeded = copy.deepcopy(preview_valid)
        extra_preview = copy.deepcopy(preview_budget_exceeded["plans"][0])
        extra_preview["media_id"] = "preview-b"
        extra_preview["relative_path"] = "preview-b.jpg"
        preview_budget_exceeded["plans"].append(extra_preview)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(TieringValidationError):
                    validate_analysis_tiering_document(mutation)
        with self.assertRaisesRegex(TieringValidationError, "deep_budget_exceeded"):
            validate_analysis_tiering_document(deep_budget_exceeded)
        with self.assertRaisesRegex(TieringValidationError, "preview_budget_exceeded"):
            validate_analysis_tiering_document(preview_budget_exceeded)

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
