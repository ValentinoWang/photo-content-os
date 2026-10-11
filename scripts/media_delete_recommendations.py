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
from pathlib import PurePosixPath
from typing import Any


CANDIDATE_STATE = "suggested"
CONFIRMED_STATE = "confirmed"
MIN_USABLE_VIDEO_DURATION_SECONDS = 1.0
REASON_DURATION_TOO_SHORT = "duration_too_short"
REASON_FILE_DAMAGED = "file_damaged"
REASON_HASH_DUPLICATE = "sha256_duplicate"
REASON_CAMERA_LOW_RES_PROXY = "camera_low_resolution_proxy"
REASON_LABELS = {
    REASON_DURATION_TOO_SHORT: "时长过短",
    REASON_FILE_DAMAGED: "文件损坏",
    REASON_HASH_DUPLICATE: "哈希完全重复",
    REASON_CAMERA_LOW_RES_PROXY: "相机低清代理",
}
GENERATION_REASON = REASON_DURATION_TOO_SHORT
_IMAGE_HEALTH_STATES = {"healthy", "malformed", "unreadable", "probe_unavailable", "not_applicable"}
_HIGH_RES_CAMERA_EXTENSIONS = {".mp4", ".mov", ".m4v"}

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
    image_health = item.get("image_health")
    if image_health not in _IMAGE_HEALTH_STATES:
        _reject("invalid_image_health", "image_health is invalid")

    if "image_readable" not in item:
        _reject("missing_image_readable", "image_readable is required")
    image_readable = item.get("image_readable")
    if image_readable is not None and not isinstance(image_readable, bool):
        _reject("invalid_image_readable", "image_readable must be boolean or null")

    return {
        "media_id": media_id,
        "relative_path": relative_path,
        "sha256": sha256,
        "image_health": image_health,
        "image_readable": image_readable,
    }


def _validate_reason(value: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    reason = value.get("reason")
    if reason not in REASON_LABELS:
        _reject("invalid_reason", "candidate reason is not one of the four supported machine reasons")
    evidence = value.get("reason_evidence")
    if not isinstance(evidence, Mapping) or not evidence:
        _reject("invalid_reason_evidence", "reason_evidence must be a non-empty object")
    normalized = dict(evidence)
    if reason == REASON_DURATION_TOO_SHORT:
        duration = normalized.get("duration_sec")
        threshold = normalized.get("threshold_sec")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration < 0:
            _reject("invalid_reason_evidence", "duration reason requires a non-negative duration_sec")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or threshold <= 0 or duration >= threshold:
            _reject("invalid_reason_evidence", "duration reason must prove duration_sec is below threshold_sec")
    elif reason == REASON_FILE_DAMAGED:
        if normalized.get("image_health") not in {"malformed", "unreadable"}:
            _reject("invalid_reason_evidence", "damaged-file reason requires malformed or unreadable image health")
    elif reason == REASON_HASH_DUPLICATE:
        duplicate_of = normalized.get("duplicate_of_media_id")
        duplicate_sha = normalized.get("sha256")
        if not isinstance(duplicate_of, str) or not _MEDIA_ID_RE.fullmatch(duplicate_of):
            _reject("invalid_reason_evidence", "duplicate reason requires a valid duplicate_of_media_id")
        if not isinstance(duplicate_sha, str) or not _SHA256_RE.fullmatch(duplicate_sha):
            _reject("invalid_reason_evidence", "duplicate reason requires the shared sha256")
    else:
        original_id = normalized.get("original_media_id")
        original_path = normalized.get("original_relative_path")
        if not isinstance(original_id, str) or not _MEDIA_ID_RE.fullmatch(original_id):
            _reject("invalid_reason_evidence", "proxy reason requires a valid original_media_id")
        _validate_relative_path(original_path)
    try:
        json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        _reject("invalid_reason_evidence", "reason_evidence must be JSON serializable")
        raise AssertionError("unreachable") from exc
    return str(reason), normalized


def candidate_number_for_evidence(evidence: Mapping[str, Any]) -> str:
    """Return the stable candidate number for the complete immutable evidence."""

    normalized = _validate_evidence(evidence)
    if "reason" in evidence or "reason_evidence" in evidence:
        reason, reason_evidence = _validate_reason(evidence)
        normalized["reason"] = reason
        normalized["reason_evidence"] = reason_evidence
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
    """Generate deterministic review candidates for four machine-verifiable reasons."""

    items = list(_manifest_items(manifest))
    hashed_items: list[tuple[Mapping[str, Any], dict[str, Any]]] = []
    for item in items:
        if item.get("sha256") is None:
            continue
        hashed_items.append((item, _validate_evidence(item)))

    first_by_hash: dict[str, dict[str, Any]] = {}
    original_by_stem: dict[tuple[str, str], dict[str, Any]] = {}
    for item, evidence in hashed_items:
        first_by_hash.setdefault(evidence["sha256"], evidence)
        path = PurePosixPath(evidence["relative_path"])
        extension = str(item.get("extension") or path.suffix).lower()
        stem = str(item.get("stem") or path.stem)
        if extension in _HIGH_RES_CAMERA_EXTENSIONS:
            original_by_stem.setdefault((path.parent.as_posix(), stem), evidence)

    recommendations: list[dict[str, Any]] = []
    seen_numbers: set[str] = set()
    for item, evidence in hashed_items:
        path = PurePosixPath(evidence["relative_path"])
        extension = str(item.get("extension") or path.suffix).lower()
        stem = str(item.get("stem") or path.stem)
        reason: str | None = None
        reason_evidence: dict[str, Any] = {}

        if evidence["image_health"] in {"malformed", "unreadable"}:
            reason = REASON_FILE_DAMAGED
            reason_evidence = {
                "image_health": evidence["image_health"],
                "image_health_reason": item.get("image_health_reason"),
            }
        elif extension == ".lrf" and (path.parent.as_posix(), stem) in original_by_stem:
            original = original_by_stem[(path.parent.as_posix(), stem)]
            reason = REASON_CAMERA_LOW_RES_PROXY
            reason_evidence = {
                "original_media_id": original["media_id"],
                "original_relative_path": original["relative_path"],
            }
        elif first_by_hash[evidence["sha256"]]["media_id"] != evidence["media_id"]:
            original = first_by_hash[evidence["sha256"]]
            reason = REASON_HASH_DUPLICATE
            reason_evidence = {
                "duplicate_of_media_id": original["media_id"],
                "sha256": evidence["sha256"],
            }
        else:
            duration = item.get("duration_sec")
            if (
                item.get("media_type") == "video"
                and isinstance(duration, (int, float))
                and not isinstance(duration, bool)
                and 0 <= duration < MIN_USABLE_VIDEO_DURATION_SECONDS
            ):
                reason = REASON_DURATION_TOO_SHORT
                reason_evidence = {
                    "duration_sec": duration,
                    "threshold_sec": MIN_USABLE_VIDEO_DURATION_SECONDS,
                }

        if reason is None:
            continue
        candidate_evidence = {**evidence, "reason": reason, "reason_evidence": reason_evidence}
        candidate_number = candidate_number_for_evidence(candidate_evidence)
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
                "reason": reason,
                "reason_label": REASON_LABELS[reason],
                "reason_evidence": reason_evidence,
                "generation_reason": reason,
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
    reason, reason_evidence = _validate_reason(candidate)
    number = _candidate_number(candidate)
    expected_number = candidate_number_for_evidence({**evidence, "reason": reason, "reason_evidence": reason_evidence})
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
            "reason": candidate["reason"],
            "reason_label": candidate.get("reason_label", REASON_LABELS[str(candidate["reason"])]),
            "reason_evidence": dict(candidate["reason_evidence"]),
            "generation_reason": candidate["reason"],
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
    "GENERATION_REASON",
    "MIN_USABLE_VIDEO_DURATION_SECONDS",
    "REASON_CAMERA_LOW_RES_PROXY",
    "REASON_DURATION_TOO_SHORT",
    "REASON_FILE_DAMAGED",
    "REASON_HASH_DUPLICATE",
    "REASON_LABELS",
    "DeleteRecommendationError",
    "candidate_number_for_evidence",
    "confirm_delete_selection",
    "confirm_selection",
    "generate_delete_recommendations",
    "generate_recommendations",
]
