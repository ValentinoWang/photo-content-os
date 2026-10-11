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


def short_video_item(**updates: object) -> dict[str, object]:
    item = manifest_item(
        relative_path="selected/short.mov",
        media_type="video",
        extension=".mov",
        stem="short",
        duration_sec=0.4,
        image_health="not_applicable",
        image_readable=None,
    )
    item.update(updates)
    return item


class MediaDeleteRecommendationTests(unittest.TestCase):
    def test_only_four_machine_verifiable_reason_classes_produce_candidates(self) -> None:
        items = [
            manifest_item(),
            short_video_item(media_id="111111111111", sha256="b" * 64),
            manifest_item(
                media_id="222222222222",
                relative_path="selected/damaged.jpg",
                sha256="c" * 64,
                image_health="malformed",
                image_readable=False,
                image_health_reason="malformed_image",
            ),
            manifest_item(media_id="333333333333", relative_path="selected/original.jpg", sha256="d" * 64),
            manifest_item(media_id="444444444444", relative_path="selected/copy.jpg", sha256="d" * 64),
            short_video_item(
                media_id="555555555555",
                relative_path="camera/VID_0032.MP4",
                extension=".mp4",
                stem="VID_0032",
                sha256="e" * 64,
                duration_sec=8,
            ),
            short_video_item(
                media_id="666666666666",
                relative_path="camera/VID_0032.LRF",
                extension=".lrf",
                stem="VID_0032",
                sha256="f" * 64,
                duration_sec=8,
            ),
        ]

        candidates = recommendations.generate_delete_recommendations({"items": items})

        self.assertEqual(
            {candidate["reason"] for candidate in candidates},
            {
                recommendations.REASON_DURATION_TOO_SHORT,
                recommendations.REASON_FILE_DAMAGED,
                recommendations.REASON_HASH_DUPLICATE,
                recommendations.REASON_CAMERA_LOW_RES_PROXY,
            },
        )
        self.assertEqual(len(candidates), 4)
        self.assertNotIn(VALID_MEDIA_ID, {candidate["media_id"] for candidate in candidates})
        for candidate in candidates:
            self.assertTrue(candidate["candidate_number"].startswith("DEL-"))
            self.assertEqual(candidate["candidate_id"], candidate["candidate_number"])
            self.assertTrue(candidate["reason_label"])
            self.assertTrue(candidate["reason_evidence"])
            self.assertEqual(candidate["state"], "suggested")

        repeated = recommendations.generate_delete_recommendations({"items": items})
        self.assertEqual(candidates, repeated)

    def test_missing_hash_is_not_actionable(self) -> None:
        self.assertEqual(
            recommendations.generate_delete_recommendations({"items": [short_video_item(sha256=None)]}),
            [],
        )

    def test_unknown_health_state_is_rejected_with_stable_code(self) -> None:
        with self.assertRaises(recommendations.DeleteRecommendationError) as raised:
            recommendations.generate_delete_recommendations(
                {"items": [manifest_item(image_health="mystery", image_readable=False)]}
            )

        self.assertEqual(raised.exception.code, "invalid_image_health")

    def test_content_change_changes_candidate_number(self) -> None:
        first = recommendations.generate_delete_recommendations({"items": [short_video_item()]})[0]
        changed = recommendations.generate_delete_recommendations(
            {"items": [short_video_item(sha256="b" * 64)]}
        )[0]

        self.assertEqual(first["media_id"], changed["media_id"])
        self.assertNotEqual(first["candidate_number"], changed["candidate_number"])

    def test_unknown_duplicate_and_blank_selection_numbers_are_rejected(self) -> None:
        candidate = recommendations.generate_delete_recommendations({"items": [short_video_item()]})[0]

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
        candidate = recommendations.generate_delete_recommendations({"items": [short_video_item()]})[0]
        tampered = dict(candidate)
        tampered["sha256"] = "b" * 64

        with self.assertRaisesRegex(recommendations.DeleteRecommendationError, "stale_candidate_number"):
            recommendations.confirm_delete_selection([tampered], [candidate["candidate_number"]])

    def test_confirmation_preserves_evidence_and_has_no_side_effect(self) -> None:
        candidate = recommendations.generate_delete_recommendations({"items": [short_video_item()]})[0]
        before = copy.deepcopy(candidate)

        confirmation = recommendations.confirm_delete_selection(
            [candidate], [candidate["candidate_number"]], operation_time="2026-09-02T01:02:03Z"
        )

        self.assertEqual(candidate, before)
        self.assertEqual(confirmation["state"], "confirmed")
        self.assertEqual(confirmation["operation_time"], "2026-09-02T01:02:03Z")
        self.assertEqual(confirmation["selected_candidates"][0]["media_id"], VALID_MEDIA_ID)
        self.assertEqual(confirmation["selected_candidates"][0]["relative_path"], "selected/short.mov")
        self.assertEqual(confirmation["selected_candidates"][0]["sha256"], VALID_HASH)
        self.assertEqual(confirmation["selected_candidates"][0]["reason"], recommendations.REASON_DURATION_TOO_SHORT)
        self.assertIsNot(confirmation["selected_candidates"][0], candidate)


if __name__ == "__main__":
    unittest.main()
