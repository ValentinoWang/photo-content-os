#!/usr/bin/env python3
"""Build and confirm read-only deletion recommendations from a media manifest.

This module deliberately operates on manifest mappings only. It never resolves,
opens, moves, renames, or deletes a media path.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


CANDIDATE_STATE = "suggested"
CONFIRMED_STATE = "confirmed"
GENERATION_REASON = "manifest_item_is_healthy_and_readable_with_verified_sha256"

_MEDIA_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


class DeleteRecommendationError(ValueError):
    """A fail-closed validation error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.error_code = code
        super().__init__(f"{code}: {message}")


def _reject(code: str, message: str) -> None:
    raise DeleteRecommendationError(code, message)


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        _reject("missing_relative_path", "relative_path is required")
    if not value.strip():
        _reject("blank_relative_path", "relative_path must not be blank")
    if "\x00" in value:
        _reject("invalid_relative_path", "relative_path contains a NUL byte")
    if value.startswith(("/", "\\")) or _WINDOWS_ABSOLUTE_RE.match(value):
        _reject("invalid_relative_path", "relative_path must be relative")
    if any(part == ".." for part in re.split(r"[/\\]", value)):
        _reject("invalid_relative_path", "relative_path must not escape its root")
    return value


def _validate_evidence(item: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(item, Mapping):
        _reject("invalid_evidence", "evidence must be an object")
    media_id = item.get("media_id")
    if not isinstance(media_id, str) or not media_id:
        _reject("missing_media_id", "media_id is required")
    if not _MEDIA_ID_RE.fullmatch(media_id):
        _reject("invalid_media_id", "media_id must be 12 lowercase hexadecimal characters")

    relative_path = _validate_relative_path(item.get("relative_path"))

    if "sha256" not in item or item.get("sha256") is None:
        _reject("missing_sha256", "sha256 is required")
    sha256 = item.get("sha256")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        _reject("invalid_sha256", "sha256 must be 64 lowercase hexadecimal characters")

    if "image_health" not in item or item.get("image_health") is None:
        _reject("missing_image_health", "image_health is required")
    if item.get("image_health") != "healthy":
        _reject("image_not_healthy", "only healthy images can be suggested")

    if "image_readable" not in item or item.get("image_readable") is None:
        _reject("missing_image_readable", "image_readable is required")
    if item.get("image_readable") is not True:
        _reject("image_not_readable", "image_readable must be true")

    return {
        "media_id": media_id,
        "relative_path": relative_path,
        "sha256": sha256,
        "image_health": "healthy",
        "image_readable": True,
    }


def candidate_number_for_evidence(evidence: Mapping[str, Any]) -> str:
    """Return the stable candidate number for the complete immutable evidence."""

    normalized = _validate_evidence(evidence)
    payload = json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return f"DEL-{digest[:20]}"


def _manifest_items(manifest: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    if not isinstance(manifest, Mapping):
        _reject("invalid_manifest", "manifest must be an object")
    if "items" not in manifest:
        _reject("missing_manifest_items", "manifest.items is required")
    items = manifest.get("items")
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
        _reject("invalid_manifest_items", "manifest.items must be a sequence")
    for item in items:
        if not isinstance(item, Mapping):
            _reject("invalid_manifest_item", "each manifest item must be an object")
    return items


def generate_delete_recommendations(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Generate deterministic, review-only candidates from a B1 manifest object."""

    recommendations: list[dict[str, Any]] = []
    seen_numbers: set[str] = set()
    for item in _manifest_items(manifest):
        evidence = _validate_evidence(item)
        candidate_number = candidate_number_for_evidence(evidence)
        if candidate_number in seen_numbers:
            _reject("duplicate_candidate_number", "manifest produced a duplicate candidate number")
        seen_numbers.add(candidate_number)
        recommendations.append(
            {
                "candidate_number": candidate_number,
                "candidate_id": candidate_number,
                "media_id": evidence["media_id"],
                "relative_path": evidence["relative_path"],
                "sha256": evidence["sha256"],
                "image_health": evidence["image_health"],
                "image_readable": evidence["image_readable"],
                "reason": GENERATION_REASON,
                "generation_reason": GENERATION_REASON,
                "state": CANDIDATE_STATE,
            }
        )
    return recommendations


def _candidate_number(candidate: Mapping[str, Any]) -> str:
    number = candidate.get("candidate_number")
    candidate_id = candidate.get("candidate_id")
    if number is None:
        number = candidate_id
    if not isinstance(number, str) or not number:
        _reject("missing_candidate_number", "candidate number is required")
    if candidate_id is not None and candidate_id != number:
        _reject("candidate_number_mismatch", "candidate number aliases do not match")
    return number


def _validate_candidate(candidate: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(candidate, Mapping):
        _reject("invalid_candidate", "each candidate must be an object")
    evidence = _validate_evidence(candidate)
    number = _candidate_number(candidate)
    expected_number = candidate_number_for_evidence(evidence)
    if number != expected_number:
        _reject("stale_candidate_number", "candidate number does not match its evidence")
    if candidate.get("state") != CANDIDATE_STATE:
        _reject("candidate_not_suggested", "only suggested candidates can be confirmed")
    return number, evidence


def _selection_numbers(selected: Iterable[str]) -> list[str]:
    if isinstance(selected, (str, bytes)) or not isinstance(selected, Iterable):
        _reject("invalid_selection", "selected candidate numbers must be an iterable")
    numbers = list(selected)
    for number in numbers:
        if not isinstance(number, str):
            _reject("invalid_candidate_number", "candidate numbers must be strings")
        if not number.strip():
            _reject("blank_candidate_number", "candidate numbers must not be blank")
    if len(numbers) != len(set(numbers)):
        _reject("duplicate_candidate_number", "a candidate number may be selected only once")
    return numbers


def _operation_timestamp(operation_time: str | datetime | None) -> str:
    if operation_time is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(operation_time, datetime):
        return operation_time.isoformat().replace("+00:00", "Z")
    if not isinstance(operation_time, str) or not operation_time.strip():
        _reject("invalid_operation_time", "operation time must be a non-blank string")
    return operation_time


def confirm_delete_selection(
    candidates: Sequence[Mapping[str, Any]],
    selected_candidate_numbers: Iterable[str],
    *,
    operation_time: str | datetime | None = None,
) -> dict[str, Any]:
    """Confirm an explicit subset while retaining its manifest evidence.

    The returned snapshot is data-only. No candidate path is opened or acted on.
    """

    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        _reject("invalid_candidates", "candidates must be a sequence")
    by_number: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        number, evidence = _validate_candidate(candidate)
        if number in by_number:
            _reject("duplicate_candidate_number", "candidate numbers must be unique")
        by_number[number] = {
            "candidate_number": number,
            "candidate_id": number,
            **evidence,
            "reason": candidate.get("reason", GENERATION_REASON),
            "generation_reason": candidate.get("generation_reason", candidate.get("reason", GENERATION_REASON)),
            "state": CANDIDATE_STATE,
        }

    selected_numbers = _selection_numbers(selected_candidate_numbers)
    selected: list[dict[str, Any]] = []
    for number in selected_numbers:
        if number not in by_number:
            _reject("unknown_candidate_number", "selected candidate number is not in the supplied candidates")
        selected.append(dict(by_number[number]))

    timestamp = _operation_timestamp(operation_time)
    return {
        "state": CONFIRMED_STATE,
        "status": CONFIRMED_STATE,
        "operation_time": timestamp,
        "confirmed_at": timestamp,
        "selected_candidate_numbers": selected_numbers,
        "selected_candidates": selected,
    }


# Short aliases keep the data-only API convenient without creating a second
# implementation or changing the candidate contract.
generate_recommendations = generate_delete_recommendations
confirm_selection = confirm_delete_selection


__all__ = [
    "CANDIDATE_STATE",
    "CONFIRMED_STATE",
    "DeleteRecommendationError",
    "candidate_number_for_evidence",
    "confirm_delete_selection",
    "confirm_selection",
    "generate_delete_recommendations",
    "generate_recommendations",
]
