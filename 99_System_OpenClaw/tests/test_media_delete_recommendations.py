from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


SYSTEM = Path(__file__).resolve().parents[1]
SCRIPTS = SYSTEM / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_recommendations():
    source = SCRIPTS / "media_delete_recommendations.py"
    spec = importlib.util.spec_from_file_location("media_delete_recommendations_contract", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load recommendations module: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


recommendations = load_recommendations()


VALID_HASH = "a" * 64
VALID_MEDIA_ID = "0123456789ab"


def manifest_item(**updates: object) -> dict[str, object]:
    item: dict[str, object] = {
        "media_id": VALID_MEDIA_ID,
        "relative_path": "selected/portrait.jpg",
        "sha256": VALID_HASH,
        "image_health": "healthy",
        "image_readable": True,
    }
    item.update(updates)
    return item


class MediaDeleteRecommendationTests(unittest.TestCase):
    def test_healthy_manifest_item_produces_reviewable_suggestion(self) -> None:
        candidates = recommendations.generate_delete_recommendations({"items": [manifest_item()]})

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertTrue(candidate["candidate_number"].startswith("DEL-"))
        self.assertEqual(candidate["candidate_id"], candidate["candidate_number"])
        self.assertEqual(candidate["media_id"], VALID_MEDIA_ID)
        self.assertEqual(candidate["relative_path"], "selected/portrait.jpg")
        self.assertEqual(candidate["sha256"], VALID_HASH)
        self.assertEqual(candidate["image_health"], "healthy")
        self.assertTrue(candidate["image_readable"])
        self.assertTrue(candidate["reason"])
        self.assertEqual(candidate["state"], "suggested")
        repeated = recommendations.generate_delete_recommendations({"items": [manifest_item()]})[0]
        self.assertEqual(candidate["candidate_number"], repeated["candidate_number"])

    def test_missing_hash_is_rejected_with_stable_code(self) -> None:
        with self.assertRaises(recommendations.DeleteRecommendationError) as raised:
            recommendations.generate_delete_recommendations({"items": [manifest_item(sha256=None)]})

        self.assertEqual(raised.exception.code, "missing_sha256")

    def test_unhealthy_item_is_rejected_with_stable_code(self) -> None:
        with self.assertRaises(recommendations.DeleteRecommendationError) as raised:
            recommendations.generate_delete_recommendations(
                {"items": [manifest_item(image_health="malformed", image_readable=False)]}
            )

        self.assertEqual(raised.exception.code, "image_not_healthy")

    def test_content_change_changes_candidate_number(self) -> None:
        first = recommendations.generate_delete_recommendations({"items": [manifest_item()]})[0]
        changed = recommendations.generate_delete_recommendations(
            {"items": [manifest_item(sha256="b" * 64)]}
        )[0]

        self.assertEqual(first["media_id"], changed["media_id"])
        self.assertNotEqual(first["candidate_number"], changed["candidate_number"])

    def test_unknown_duplicate_and_blank_selection_numbers_are_rejected(self) -> None:
        candidate = recommendations.generate_delete_recommendations({"items": [manifest_item()]})[0]

        with self.assertRaisesRegex(recommendations.DeleteRecommendationError, "unknown_candidate_number"):
            recommendations.confirm_delete_selection([candidate], ["DEL-unknown"], operation_time="2026-09-02T00:00:00Z")
        with self.assertRaisesRegex(recommendations.DeleteRecommendationError, "duplicate_candidate_number"):
            recommendations.confirm_delete_selection(
                [candidate],
                [candidate["candidate_number"], candidate["candidate_number"]],
                operation_time="2026-09-02T00:00:00Z",
            )
        with self.assertRaisesRegex(recommendations.DeleteRecommendationError, "blank_candidate_number"):
            recommendations.confirm_delete_selection([candidate], ["   "], operation_time="2026-09-02T00:00:00Z")

    def test_stale_candidate_number_is_rejected(self) -> None:
        candidate = recommendations.generate_delete_recommendations({"items": [manifest_item()]})[0]
        tampered = dict(candidate)
        tampered["sha256"] = "b" * 64

        with self.assertRaisesRegex(recommendations.DeleteRecommendationError, "stale_candidate_number"):
            recommendations.confirm_delete_selection([tampered], [candidate["candidate_number"]])

    def test_confirmation_preserves_evidence_and_has_no_side_effect(self) -> None:
        candidate = recommendations.generate_delete_recommendations({"items": [manifest_item()]})[0]
        before = copy.deepcopy(candidate)

        confirmation = recommendations.confirm_delete_selection(
            [candidate], [candidate["candidate_number"]], operation_time="2026-09-02T01:02:03Z"
        )

        self.assertEqual(candidate, before)
        self.assertEqual(confirmation["state"], "confirmed")
        self.assertEqual(confirmation["operation_time"], "2026-09-02T01:02:03Z")
        self.assertEqual(confirmation["selected_candidates"][0]["media_id"], VALID_MEDIA_ID)
        self.assertEqual(confirmation["selected_candidates"][0]["relative_path"], "selected/portrait.jpg")
        self.assertEqual(confirmation["selected_candidates"][0]["sha256"], VALID_HASH)
        self.assertIsNot(confirmation["selected_candidates"][0], candidate)


if __name__ == "__main__":
    unittest.main()
