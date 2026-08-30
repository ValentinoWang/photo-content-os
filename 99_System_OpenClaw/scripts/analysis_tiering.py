#!/usr/bin/env python3
"""Deterministic analysis tiers, budgets and cache identities.

The planner decides *how much evidence to inspect*, never what the media means.
Semantic claims remain the responsibility of evidence-backed model runs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from media_common import file_sha256, stable_json_hash  # noqa: F401  (re-exported: L-13/r8)

POLICY_VERSION = "analysis_tiering_v1"


@dataclass(frozen=True)
class TierBudget:
    preview_images_per_asset: int = 3
    deep_images_per_asset: int = 12
    max_preview_assets: int = 100
    max_deep_assets: int = 24
    max_audio_minutes: float = 120.0


@dataclass(frozen=True)
class AssetPlan:
    media_id: str
    relative_path: str
    tier: str
    image_budget: int
    audio_seconds_budget: float
    reason_codes: tuple[str, ...]
    cache_key: str


def analysis_cache_key(
    *,
    content_sha256: str,
    model: str,
    prompt_version: str,
    policy_version: str = POLICY_VERSION,
    tier: str,
) -> str:
    return "sha256:" + stable_json_hash(
        {
            "content_sha256": content_sha256,
            "model": model,
            "prompt_version": prompt_version,
            "policy_version": policy_version,
            "tier": tier,
        }
    )


def evenly_spaced_indexes(total: int, count: int) -> list[int]:
    if total <= 0 or count <= 0:
        return []
    if count >= total:
        return list(range(total))
    if count == 1:
        return [total // 2]
    indexes = [round(index * (total - 1) / (count - 1)) for index in range(count)]
    return list(dict.fromkeys(indexes))


def _quality_score(item: dict[str, Any]) -> tuple[int, float, int, str]:
    eligible = int(bool(item.get("analysis_eligible")))
    duration = float(item.get("duration_sec") or 0)
    pixels = int(item.get("width") or 0) * int(item.get("height") or 0)
    return eligible, min(duration, 600), pixels, str(item.get("relative_path") or "")


def plan_manifest(
    manifest: dict[str, Any],
    *,
    model: str,
    prompt_version: str,
    requested_media_ids: Iterable[str] = (),
    budget: TierBudget = TierBudget(),
) -> list[AssetPlan]:
    requested = {str(value) for value in requested_media_ids}
    items = [item for item in manifest.get("items", []) if isinstance(item, dict)]
    ranked = sorted(items, key=_quality_score, reverse=True)
    preview_ids = {
        str(item.get("media_id") or item.get("id"))
        for item in ranked[: budget.max_preview_assets]
        if item.get("analysis_eligible")
    }
    deep_candidates = [
        item
        for item in ranked
        if str(item.get("media_id") or item.get("id")) in requested
        or item.get("project_selected") is True
        or item.get("edl_selected") is True
    ]
    if not deep_candidates:
        deep_candidates = [item for item in ranked if item.get("analysis_eligible")][: budget.max_deep_assets]
    deep_ids = {str(item.get("media_id") or item.get("id")) for item in deep_candidates[: budget.max_deep_assets]}

    audio_remaining = max(0.0, budget.max_audio_minutes * 60)
    plans: list[AssetPlan] = []
    for item in items:
        media_id = str(item.get("media_id") or item.get("id") or "")
        if not media_id:
            continue
        reasons: list[str] = []
        if media_id in deep_ids:
            tier = "deep"
            image_budget = budget.deep_images_per_asset
            reasons.append("selected_for_project_or_budget")
        elif media_id in preview_ids:
            tier = "preview"
            image_budget = budget.preview_images_per_asset
            reasons.append("eligible_preview")
        else:
            tier = "metadata"
            image_budget = 0
            reasons.append("outside_current_budget")
        duration = max(0.0, float(item.get("duration_sec") or 0)) if item.get("has_audio") else 0.0
        audio_budget = min(duration, audio_remaining) if tier in {"preview", "deep"} else 0.0
        audio_remaining -= audio_budget
        sha = str(item.get("sha256") or item.get("content_sha256") or stable_json_hash({"ref": item.get("relative_path"), "size": item.get("size_bytes")}))
        plans.append(
            AssetPlan(
                media_id=media_id,
                relative_path=str(item.get("relative_path") or ""),
                tier=tier,
                image_budget=image_budget,
                audio_seconds_budget=round(audio_budget, 3),
                reason_codes=tuple(reasons),
                cache_key=analysis_cache_key(
                    content_sha256=sha,
                    model=model,
                    prompt_version=prompt_version,
                    tier=tier,
                ),
            )
        )
    return plans


def cache_hit(cache_root: Path, cache_key: str) -> Path | None:
    digest = cache_key.removeprefix("sha256:")
    path = cache_root / digest[:2] / f"{digest}.json"
    return path if path.is_file() else None


def write_cache(cache_root: Path, cache_key: str, payload: dict[str, Any]) -> Path:
    digest = cache_key.removeprefix("sha256:")
    path = cache_root / digest[:2] / f"{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-version", required=True)
    parser.add_argument("--requested-media-id", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = {
        "schema_version": POLICY_VERSION,
        "plans": [asdict(plan) for plan in plan_manifest(
            manifest,
            model=args.model,
            prompt_version=args.prompt_version,
            requested_media_ids=args.requested_media_id,
        )],
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
