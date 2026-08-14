#!/usr/bin/env python3
"""Tests for the review capability SSOT registry."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "36_validate_review_capability_registry.py"
REGISTRY_PATH = ROOT / "review_capabilities.registry.json"
SPEC = importlib.util.spec_from_file_location("review_capability_validator", SCRIPT_PATH)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules["review_capability_validator"] = validator
SPEC.loader.exec_module(validator)


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


class ReviewCapabilityRegistryTest(unittest.TestCase):
    def test_current_registry_is_valid(self) -> None:
        errors = validator.validate_registry(load_registry(), ROOT.parent)

        self.assertEqual(errors, [])

    def test_duplicate_runner_task_type_is_rejected(self) -> None:
        registry = load_registry()
        duplicate = copy.deepcopy(registry["capabilities"][0])
        duplicate["capability_id"] = "duplicate_output_review"
        duplicate["display_name"] = "Duplicate output review"
        registry["capabilities"].append(duplicate)

        errors = validator.validate_registry(registry, ROOT.parent)

        self.assertTrue(any("local_output_review" in error for error in errors))

    def test_missing_implementation_file_is_rejected(self) -> None:
        registry = load_registry()
        registry["capabilities"][0]["implementation_files"] = ["99_System_OpenClaw/scripts/missing_review.py"]

        errors = validator.validate_registry(registry, ROOT.parent)

        self.assertTrue(any("missing_review.py" in error for error in errors))

    def test_unknown_dedupe_capability_is_rejected(self) -> None:
        registry = load_registry()
        registry["dedupe_rules"][0]["canonical_capability_id"] = "unknown_capability"

        errors = validator.validate_registry(registry, ROOT.parent)

        self.assertTrue(any("unknown_capability" in error for error in errors))

    def test_cloud_orchestration_cannot_claim_video_scoring_core_role(self) -> None:
        registry = load_registry()
        remote = next(item for item in registry["capabilities"] if item["capability_id"] == "remote_review_orchestration")
        remote["algorithm_contract"]["algorithm_role"] = "scoring_core"
        remote["algorithm_contract"]["scoring_dimensions"] = ["remote_score"]

        errors = validator.validate_registry(registry, ROOT.parent)

        self.assertTrue(any("must not be video scoring core" in error for error in errors))

    def test_remote_work_acceptance_keeps_strategy_evaluation_role(self) -> None:
        registry = load_registry()
        remote = next(item for item in registry["capabilities"] if item["capability_id"] == "remote_work_acceptance_review")

        self.assertEqual(remote["algorithm_contract"]["algorithm_role"], "remote_strategy_evaluation")
        self.assertIn("work_acceptance.py", " ".join(remote["external_implementation_refs"]))

    def test_strategy_weights_must_sum_to_one(self) -> None:
        registry = load_registry()
        local = next(item for item in registry["capabilities"] if item["capability_id"] == "local_output_review")
        local["algorithm_contract"]["strategy_weights"]["platform_format"] = 0.2

        errors = validator.validate_registry(registry, ROOT.parent)

        self.assertTrue(any("strategy_weights must sum to 1.0" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
