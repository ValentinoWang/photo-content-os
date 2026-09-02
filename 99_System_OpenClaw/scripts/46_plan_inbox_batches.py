#!/usr/bin/env python3
"""Create a read-only, deterministic event-batch plan from a media manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


PLAN_SCHEMA_VERSION = "inbox_batch_plan_v1"
DEFAULT_TIME_GAP_SECONDS = 30 * 60
DEFAULT_DISTANCE_METERS = 1000.0


class BatchPlanError(ValueError):
    """Raised when the manifest cannot be consumed safely."""


def parse_captured_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def item_captured_at(item: dict[str, Any]) -> datetime | None:
    return parse_captured_at(item.get("captured_at")) or parse_captured_at(item.get("created_at"))


def item_gps(item: dict[str, Any]) -> tuple[float, float] | None:
    latitude = item.get("gps_latitude")
    longitude = item.get("gps_longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return None
    if not math.isfinite(latitude) or not math.isfinite(longitude):
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return float(latitude), float(longitude)


def live_group_key(item: dict[str, Any]) -> str | None:
    if not isinstance(item.get("live_photo_status"), str):
        return None
    relative_path = item.get("relative_path")
    stem = item.get("stem")
    if not isinstance(relative_path, str) or not isinstance(stem, str) or not stem:
        return None
    return f"live:{Path(relative_path).parent.as_posix()}:{stem}"


def haversine_meters(left: tuple[float, float], right: tuple[float, float]) -> float:
    earth_radius_meters = 6_371_000.0
    left_latitude, left_longitude = map(math.radians, left)
    right_latitude, right_longitude = map(math.radians, right)
    latitude_delta = right_latitude - left_latitude
    longitude_delta = right_longitude - left_longitude
    value = math.sin(latitude_delta / 2) ** 2
    value += math.cos(left_latitude) * math.cos(right_latitude) * math.sin(longitude_delta / 2) ** 2
    return 2 * earth_radius_meters * math.asin(math.sqrt(value))


def source_composition(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in items:
        source = item.get("source_type")
        label = source if isinstance(source, str) and source else "unknown"
        counts[label] = counts.get(label, 0) + 1
    return [{"source_type": name, "count": counts[name]} for name in sorted(counts)]


def build_units(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        media_id = item.get("media_id")
        if not isinstance(media_id, str) or not media_id:
            raise BatchPlanError("each manifest item requires a non-empty media_id")
        key = live_group_key(item) or f"media:{media_id}"
        grouped.setdefault(key, []).append(item)

    units: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = sorted(grouped[key], key=lambda item: str(item["media_id"]))
        captured = [value for value in (item_captured_at(item) for item in members) if value is not None]
        gps = [value for value in (item_gps(item) for item in members) if value is not None]
        reasons: list[str] = []
        if not captured:
            reasons.append("missing_captured_at")
        if not gps:
            reasons.append("missing_gps")
        units.append(
            {
                "unit_id": key,
                "is_live_group": key.startswith("live:"),
                "items": members,
                # The earliest observed capture time is a stable group position.
                "captured_at": min(captured) if captured else None,
                # Preserve a paired Live Photo by using one observed location, never separate members.
                "gps": gps[0] if gps else None,
                "pending_reasons": reasons,
            }
        )
    return units


def plan_batches(
    manifest: dict[str, Any],
    *,
    manifest_sha256: str,
    time_gap_seconds: int = DEFAULT_TIME_GAP_SECONDS,
    distance_meters: float = DEFAULT_DISTANCE_METERS,
) -> dict[str, Any]:
    if not isinstance(manifest.get("items"), list):
        raise BatchPlanError("manifest items must be an array")
    if not isinstance(manifest.get("manifest_version"), int) or manifest["manifest_version"] < 1:
        raise BatchPlanError("manifest_version must be a positive integer")
    if time_gap_seconds <= 0 or distance_meters <= 0:
        raise BatchPlanError("time and distance thresholds must be positive")

    units = build_units(manifest["items"])
    pending_units = [unit for unit in units if unit["pending_reasons"]]
    eligible_units = sorted(
        (unit for unit in units if not unit["pending_reasons"]),
        key=lambda unit: (unit["captured_at"], unit["unit_id"]),
    )
    batches: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None

    for unit in eligible_units:
        boundary_reasons: list[str] = []
        if previous is not None:
            elapsed_seconds = (unit["captured_at"] - previous["captured_at"]).total_seconds()
            if elapsed_seconds > time_gap_seconds:
                boundary_reasons.append("time_gap_exceeded")
            if haversine_meters(previous["gps"], unit["gps"]) > distance_meters:
                boundary_reasons.append("distance_exceeded")
        if previous is not None and boundary_reasons:
            batches.append(make_batch(len(batches) + 1, current))
            current = []
        current.append(unit)
        previous = unit
    if current:
        batches.append(make_batch(len(batches) + 1, current))

    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "input_manifest": {
            "manifest_sha256": f"sha256:{manifest_sha256}",
            "manifest_version": manifest.get("manifest_version"),
            "item_count": len(manifest["items"]),
        },
        "thresholds": {
            "time_gap_seconds": time_gap_seconds,
            "distance_meters": distance_meters,
        },
        "confirmation_status": "pending",
        "migration_status": "not_requested",
        "batches": batches,
        "pending_items": [
            {
                "unit_id": unit["unit_id"],
                "is_live_group": unit["is_live_group"],
                "media_ids": [item["media_id"] for item in unit["items"]],
                "reasons": unit["pending_reasons"],
            }
            for unit in pending_units
        ],
    }


def make_batch(sequence: int, units: list[dict[str, Any]]) -> dict[str, Any]:
    items = [item for unit in units for item in unit["items"]]
    return {
        "batch_id": f"event-{sequence:03d}",
        "confirmation_status": "pending",
        "media_ids": [item["media_id"] for item in items],
        "live_group_unit_ids": [unit["unit_id"] for unit in units if unit["is_live_group"]],
        "captured_at_start": units[0]["captured_at"].isoformat(),
        "captured_at_end": units[-1]["captured_at"].isoformat(),
        "source_composition": source_composition(items),
    }


def read_manifest(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise BatchPlanError(f"cannot read manifest: {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BatchPlanError("manifest root must be an object")
    return manifest, hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to _ai_analysis/media_manifest.json")
    parser.add_argument("--output", type=Path, help="plan path; defaults beside the manifest")
    parser.add_argument("--time-gap-seconds", type=int, default=DEFAULT_TIME_GAP_SECONDS)
    parser.add_argument("--distance-meters", type=float, default=DEFAULT_DISTANCE_METERS)
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    output_path = (args.output or manifest_path.with_name("inbox_batch_plan.json")).expanduser().resolve()
    manifest, digest = read_manifest(manifest_path)
    plan = plan_batches(
        manifest,
        manifest_sha256=digest,
        time_gap_seconds=args.time_gap_seconds,
        distance_meters=args.distance_meters,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "planned", "plan_path": str(output_path), "batch_count": len(plan["batches"]), "pending_count": len(plan["pending_items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
