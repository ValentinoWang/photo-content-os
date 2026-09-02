#!/usr/bin/env python3
"""Deterministic analysis tiers, budgets and cache identities.

The planner decides *how much evidence to inspect*, never what the media means.
Semantic claims remain the responsibility of evidence-backed model runs.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from media_common import file_sha256, stable_json_hash  # noqa: F401  (re-exported: L-13/r8)

POLICY_VERSION = "analysis_tiering_v1"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "analysis_tiering.schema.json"
_SCHEMA_CONTRACT_SHA256 = "79385a1d4f5a192af99c3a28200dda690b6dc5ad01c10252a45b0aab70dd3939"
_BUDGET_FIELDS = frozenset(
    {
        "preview_images_per_asset",
        "deep_images_per_asset",
        "max_preview_assets",
        "max_deep_assets",
        "max_audio_minutes",
    }
)
_PLAN_FIELDS = frozenset(
    {
        "media_id",
        "relative_path",
        "tier",
        "image_budget",
        "audio_seconds_budget",
        "reason_codes",
        "cache_key",
    }
)
_CACHE_KEY_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class TieringValidationError(ValueError):
    """Fail-closed analysis policy or output validation error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _non_negative_integer(value: object, *, code: str) -> int:
    if type(value) is not int or value < 0:
        raise TieringValidationError(code, "budget value must be a non-negative integer")
    return value


def _non_negative_number(value: object, *, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TieringValidationError(code, "budget value must be a non-negative finite number")
    try:
        normalized = float(value)
    except OverflowError as exc:
        raise TieringValidationError(code, "budget value must be a non-negative finite number") from exc
    if not math.isfinite(normalized) or normalized < 0:
        raise TieringValidationError(code, "budget value must be a non-negative finite number")
    return normalized


@dataclass(frozen=True)
class TierBudget:
    preview_images_per_asset: int = 3
    deep_images_per_asset: int = 12
    max_preview_assets: int = 100
    max_deep_assets: int = 24
    max_audio_minutes: float = 120.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "preview_images_per_asset",
            _non_negative_integer(self.preview_images_per_asset, code="preview_images_per_asset_invalid"),
        )
        object.__setattr__(
            self,
            "deep_images_per_asset",
            _non_negative_integer(self.deep_images_per_asset, code="deep_images_per_asset_invalid"),
        )
        object.__setattr__(
            self,
            "max_preview_assets",
            _non_negative_integer(self.max_preview_assets, code="max_preview_assets_invalid"),
        )
        object.__setattr__(
            self,
            "max_deep_assets",
            _non_negative_integer(self.max_deep_assets, code="max_deep_assets_invalid"),
        )
        object.__setattr__(
            self,
            "max_audio_minutes",
            _non_negative_number(self.max_audio_minutes, code="max_audio_minutes_invalid"),
        )

    @classmethod
    def from_dict(cls, value: object) -> "TierBudget":
        if not isinstance(value, Mapping) or set(value) != _BUDGET_FIELDS:
            raise TieringValidationError("budget_shape_invalid", "budget must contain exactly the declared fields")
        return cls(**{field: value[field] for field in _BUDGET_FIELDS})

    def to_dict(self) -> dict[str, int | float]:
        return {
            "preview_images_per_asset": self.preview_images_per_asset,
            "deep_images_per_asset": self.deep_images_per_asset,
            "max_preview_assets": self.max_preview_assets,
            "max_deep_assets": self.max_deep_assets,
            "max_audio_minutes": self.max_audio_minutes,
        }


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
    budget: TierBudget = TierBudget(),
) -> str:
    if not isinstance(budget, TierBudget):
        raise TieringValidationError("budget_invalid", "budget must be a TierBudget")
    return "sha256:" + stable_json_hash(
        {
            "content_sha256": content_sha256,
            "model": model,
            "prompt_version": prompt_version,
            "policy_version": policy_version,
            "tier": tier,
            "budget": budget.to_dict(),
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
    if not isinstance(budget, TierBudget):
        raise TieringValidationError("budget_invalid", "budget must be a TierBudget")
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
                    budget=budget,
                ),
            )
        )
    return plans


def load_analysis_tiering_schema() -> dict[str, Any]:
    """Load the checked-in schema and reject drift from the runtime contract."""

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TieringValidationError("schema_unavailable", "analysis tiering schema cannot be loaded") from exc
    try:
        schema_version = schema["properties"]["schema_version"]["const"]
        required = frozenset(schema["required"])
        plan_fields = frozenset(schema["$defs"]["asset_plan"]["required"])
        budget_fields = frozenset(schema["$defs"]["tier_budget"]["required"])
    except (KeyError, TypeError) as exc:
        raise TieringValidationError("schema_invalid", "analysis tiering schema is incomplete") from exc
    if (
        stable_json_hash(schema) != _SCHEMA_CONTRACT_SHA256
        or schema_version != POLICY_VERSION
        or required != {"schema_version", "budget", "plans"}
        or plan_fields != _PLAN_FIELDS
        or budget_fields != _BUDGET_FIELDS
    ):
        raise TieringValidationError("schema_drift", "analysis tiering schema and runtime contract differ")
    return schema


def _validate_plan(plan: object, budget: TierBudget, *, seen_media_ids: set[str]) -> float:
    if not isinstance(plan, Mapping) or set(plan) != _PLAN_FIELDS:
        raise TieringValidationError("plan_shape_invalid", "analysis plan contains unknown or missing fields")

    media_id = plan["media_id"]
    relative_path = plan["relative_path"]
    tier = plan["tier"]
    image_budget = plan["image_budget"]
    audio_budget = plan["audio_seconds_budget"]
    reason_codes = plan["reason_codes"]
    cache_key = plan["cache_key"]

    if not isinstance(media_id, str) or not media_id:
        raise TieringValidationError("media_id_invalid", "analysis plan media id must be non-empty")
    if media_id in seen_media_ids:
        raise TieringValidationError("media_id_duplicate", "analysis plan media ids must be unique")
    seen_media_ids.add(media_id)
    if not isinstance(relative_path, str) or not relative_path:
        raise TieringValidationError("relative_path_invalid", "analysis plan relative path must be non-empty")
    if not isinstance(tier, str) or tier not in {"metadata", "preview", "deep"}:
        raise TieringValidationError("tier_invalid", "analysis plan tier is invalid")
    if type(image_budget) is not int or image_budget < 0:
        raise TieringValidationError("image_budget_invalid", "analysis plan image budget is invalid")
    normalized_audio = _non_negative_number(audio_budget, code="audio_budget_invalid")
    if not isinstance(reason_codes, list) or not reason_codes:
        raise TieringValidationError("reason_codes_invalid", "analysis plan reason codes must be a non-empty list")
    if any(not isinstance(code, str) or not code for code in reason_codes) or len(set(reason_codes)) != len(reason_codes):
        raise TieringValidationError("reason_codes_invalid", "analysis plan reason codes must be unique strings")
    if not isinstance(cache_key, str) or _CACHE_KEY_RE.fullmatch(cache_key) is None:
        raise TieringValidationError("cache_key_invalid", "analysis plan cache key must be a SHA-256 identity")

    expected_image_budget = {
        "metadata": 0,
        "preview": budget.preview_images_per_asset,
        "deep": budget.deep_images_per_asset,
    }[tier]
    if image_budget != expected_image_budget:
        raise TieringValidationError("image_budget_mismatch", "analysis plan image budget differs from its tier budget")
    if tier == "metadata" and normalized_audio != 0:
        raise TieringValidationError("audio_budget_mismatch", "metadata plans cannot consume audio budget")
    return normalized_audio


def validate_analysis_tiering_document(value: object) -> dict[str, Any]:
    """Validate one serialized planner document against the checked-in contract."""

    load_analysis_tiering_schema()
    if not isinstance(value, Mapping) or set(value) != {"schema_version", "budget", "plans"}:
        raise TieringValidationError("document_shape_invalid", "analysis tiering document shape is invalid")
    if value["schema_version"] != POLICY_VERSION:
        raise TieringValidationError("schema_version_invalid", "analysis tiering schema version is unsupported")
    budget = TierBudget.from_dict(value["budget"])
    plans = value["plans"]
    if not isinstance(plans, list):
        raise TieringValidationError("plans_invalid", "analysis plans must be a list")
    seen_media_ids: set[str] = set()
    tier_counts = {"preview": 0, "deep": 0}
    audio_total = 0.0
    for plan in plans:
        audio_total += _validate_plan(plan, budget, seen_media_ids=seen_media_ids)
        tier = plan["tier"]
        if tier in tier_counts:
            tier_counts[tier] += 1
    if tier_counts["preview"] > budget.max_preview_assets:
        raise TieringValidationError("preview_budget_exceeded", "analysis plans exceed the preview asset budget")
    if tier_counts["deep"] > budget.max_deep_assets:
        raise TieringValidationError("deep_budget_exceeded", "analysis plans exceed the deep asset budget")
    if audio_total > budget.max_audio_minutes * 60 + 1e-9:
        raise TieringValidationError("audio_budget_exceeded", "analysis plans exceed the declared audio budget")
    return dict(value)


def analysis_tiering_document(plans: Sequence[AssetPlan], budget: TierBudget) -> dict[str, Any]:
    if not isinstance(budget, TierBudget):
        raise TieringValidationError("budget_invalid", "budget must be a TierBudget")
    document = {
        "schema_version": POLICY_VERSION,
        "budget": budget.to_dict(),
        "plans": [
            {
                **asdict(plan),
                "reason_codes": list(plan.reason_codes),
            }
            for plan in plans
        ],
    }
    return validate_analysis_tiering_document(document)


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
    parser.add_argument("--budget-config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    budget = TierBudget()
    if args.budget_config:
        try:
            budget = TierBudget.from_dict(json.loads(args.budget_config.read_text(encoding="utf-8")))
        except (OSError, UnicodeError, json.JSONDecodeError, TieringValidationError) as exc:
            parser.error(f"invalid budget config: {getattr(exc, 'code', 'invalid_json')}")
    result = analysis_tiering_document(
        plan_manifest(
            manifest,
            model=args.model,
            prompt_version=args.prompt_version,
            requested_media_ids=args.requested_media_id,
            budget=budget,
        ),
        budget,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
