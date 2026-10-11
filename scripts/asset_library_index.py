#!/usr/bin/env python3
"""Validated, deterministic persistence for the reusable asset index."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

from media_common import media_id, write_json_atomic


SCHEMA_VERSION = "asset_library_index_v1"
INDEX_NAME = "index.json"
ASSET_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
INDEX_FIELDS = (
    "schema_version",
    "revision",
    "asset_count",
    "categories",
    "tags",
    "uses",
    "assets",
)
ASSET_FIELDS = (
    "asset_id",
    "title",
    "category",
    "card_path",
    "source_project",
    "source_relative_path",
    "source_sha256",
    "source_size",
    "public_status",
    "tags",
    "uses",
    "cuts",
    "icloud_copy",
    "notes",
)


class AssetIndexError(ValueError):
    """Raised when an asset index would be unsafe or internally inconsistent."""


def _require_exact_fields(value: dict[str, Any], expected: tuple[str, ...], label: str) -> None:
    missing = set(expected) - set(value)
    extra = set(value) - set(expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unexpected {', '.join(sorted(extra))}")
        raise AssetIndexError(f"{label} fields invalid: {'; '.join(details)}")


def _require_text(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise AssetIndexError(f"{label} must be a string")
    if value != value.strip():
        raise AssetIndexError(f"{label} must not have leading or trailing whitespace")
    if not allow_empty and not value:
        raise AssetIndexError(f"{label} must not be empty")
    return value


def validate_relative_path(value: object, label: str) -> str:
    text = _require_text(value, label)
    if "\\" in text or PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute():
        raise AssetIndexError(f"{label} must be a relative POSIX path")
    path = PurePosixPath(text)
    if path.as_posix() != text or any(part in {"", ".", "..", "~"} for part in path.parts):
        raise AssetIndexError(f"{label} must be a normalized path without traversal")
    return text


def _normalized_values(values: object, label: str) -> list[str]:
    if not isinstance(values, list):
        raise AssetIndexError(f"{label} must be a list")
    normalized = [_require_text(value, f"{label} item") for value in values]
    expected = sorted(set(normalized), key=lambda value: (value.casefold(), value))
    if normalized != expected:
        raise AssetIndexError(f"{label} must be unique and deterministically sorted")
    return normalized


def normalize_values(values: Iterable[str]) -> list[str]:
    normalized = [_require_text(value, "asset metadata item") for value in values]
    return sorted(set(normalized), key=lambda value: (value.casefold(), value))


def stable_asset_id(source_project: str, source_relative_path: str) -> str:
    project = _require_text(source_project, "source_project")
    if "/" in project or "\\" in project:
        raise AssetIndexError("source_project must be a single project identity")
    relative_path = validate_relative_path(source_relative_path, "source_relative_path")
    return media_id(f"{project}/{relative_path}")


def empty_index() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "asset_count": 0,
        "categories": [],
        "tags": [],
        "uses": [],
        "assets": [],
    }


def _validate_asset(asset: object, index: int | None = None) -> dict[str, Any]:
    label = f"assets[{index}]" if index is not None else "asset"
    if not isinstance(asset, dict):
        raise AssetIndexError(f"{label} must be an object")
    _require_exact_fields(asset, ASSET_FIELDS, label)

    asset_id = _require_text(asset["asset_id"], f"{label}.asset_id")
    if not ASSET_ID_PATTERN.fullmatch(asset_id):
        raise AssetIndexError(f"{label}.asset_id must be 12 lowercase hex characters")
    _require_text(asset["title"], f"{label}.title")
    _require_text(asset["category"], f"{label}.category")
    card_path = validate_relative_path(asset["card_path"], f"{label}.card_path")
    if not card_path.endswith(".asset.md"):
        raise AssetIndexError(f"{label}.card_path must end in .asset.md")
    source_project = _require_text(asset["source_project"], f"{label}.source_project")
    if "/" in source_project or "\\" in source_project:
        raise AssetIndexError(f"{label}.source_project must be a single project identity")
    source_relative_path = validate_relative_path(
        asset["source_relative_path"], f"{label}.source_relative_path"
    )
    if asset_id != stable_asset_id(source_project, source_relative_path):
        raise AssetIndexError(f"{label}.asset_id does not match its source identity")
    source_sha256 = _require_text(asset["source_sha256"], f"{label}.source_sha256")
    if not SHA256_PATTERN.fullmatch(source_sha256):
        raise AssetIndexError(f"{label}.source_sha256 must be 64 lowercase hex characters")
    if type(asset["source_size"]) is not int or asset["source_size"] < 0:
        raise AssetIndexError(f"{label}.source_size must be a non-negative integer")
    _require_text(asset["public_status"], f"{label}.public_status")
    _normalized_values(asset["tags"], f"{label}.tags")
    _normalized_values(asset["uses"], f"{label}.uses")
    _normalized_values(asset["cuts"], f"{label}.cuts")
    if asset["icloud_copy"] is not None:
        validate_relative_path(asset["icloud_copy"], f"{label}.icloud_copy")
    _require_text(asset["notes"], f"{label}.notes", allow_empty=True)
    return asset


def _facet_counts(assets: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for asset in assets:
        values = [asset[field]] if field == "category" else asset[field]
        for value in values:
            counts[value] = counts.get(value, 0) + 1
    return [
        {"name": name, "asset_count": counts[name]}
        for name in sorted(counts, key=lambda value: (value.casefold(), value))
    ]


def validate_index(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise AssetIndexError("asset index root must be an object")
    _require_exact_fields(data, INDEX_FIELDS, "asset index")
    if data["schema_version"] != SCHEMA_VERSION:
        raise AssetIndexError(f"unsupported asset index schema_version: {data['schema_version']!r}")
    if type(data["revision"]) is not int or data["revision"] < 0:
        raise AssetIndexError("asset index revision must be a non-negative integer")
    if type(data["asset_count"]) is not int or data["asset_count"] < 0:
        raise AssetIndexError("asset_count must be a non-negative integer")
    if not isinstance(data["assets"], list):
        raise AssetIndexError("assets must be a list")

    assets = [_validate_asset(asset, index) for index, asset in enumerate(data["assets"])]
    asset_ids = [asset["asset_id"] for asset in assets]
    if asset_ids != sorted(asset_ids):
        raise AssetIndexError("assets must be sorted by asset_id")
    if len(set(asset_ids)) != len(asset_ids):
        raise AssetIndexError("asset index contains duplicate asset_id values")
    card_paths = [asset["card_path"] for asset in assets]
    if len(set(card_paths)) != len(card_paths):
        raise AssetIndexError("asset index contains duplicate card_path values")
    source_keys = [(asset["source_project"], asset["source_relative_path"]) for asset in assets]
    if len(set(source_keys)) != len(source_keys):
        raise AssetIndexError("asset index contains duplicate source identities")
    if data["asset_count"] != len(assets):
        raise AssetIndexError("asset_count does not match assets")

    expected_facets = {
        "categories": _facet_counts(assets, "category"),
        "tags": _facet_counts(assets, "tags"),
        "uses": _facet_counts(assets, "uses"),
    }
    for name, expected in expected_facets.items():
        if data[name] != expected:
            raise AssetIndexError(f"{name} counts do not match assets")
    return data


def load_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_index()
    if not path.is_file():
        raise AssetIndexError(f"asset index path is not a file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AssetIndexError(f"asset index is not valid UTF-8 JSON: {path}") from exc
    return validate_index(data)


def _canonical_asset(asset: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(asset[field]) for field in ASSET_FIELDS}


def _build_index(revision: int, assets: list[dict[str, Any]]) -> dict[str, Any]:
    canonical_assets = sorted((_canonical_asset(asset) for asset in assets), key=lambda asset: asset["asset_id"])
    result = {
        "schema_version": SCHEMA_VERSION,
        "revision": revision,
        "asset_count": len(canonical_assets),
        "categories": _facet_counts(canonical_assets, "category"),
        "tags": _facet_counts(canonical_assets, "tags"),
        "uses": _facet_counts(canonical_assets, "uses"),
        "assets": canonical_assets,
    }
    return validate_index(result)


def upsert_asset(index: dict[str, Any], asset: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    validate_index(index)
    candidate = _canonical_asset(_validate_asset(asset))
    existing = next((item for item in index["assets"] if item["asset_id"] == candidate["asset_id"]), None)
    for item in index["assets"]:
        if item["asset_id"] != candidate["asset_id"] and item["card_path"] == candidate["card_path"]:
            raise AssetIndexError(f"card_path already belongs to another asset: {candidate['card_path']}")
    if existing == candidate:
        return deepcopy(index), False

    assets = [item for item in index["assets"] if item["asset_id"] != candidate["asset_id"]]
    assets.append(candidate)
    return _build_index(index["revision"] + 1, assets), True


def save_index(path: Path, index: dict[str, Any]) -> None:
    validate_index(index)
    write_json_atomic(path, index, hidden_temp=True)


def query_assets(
    index: dict[str, Any], *, category: str | None = None, tags: Iterable[str] | None = None
) -> list[dict[str, Any]]:
    validate_index(index)
    category_filter = _require_text(category, "category filter") if category is not None else None
    tag_filter = set(normalize_values(tags or []))
    return [
        deepcopy(asset)
        for asset in index["assets"]
        if (category_filter is None or asset["category"] == category_filter)
        and tag_filter.issubset(asset["tags"])
    ]


def get_asset(index: dict[str, Any], asset_id: str) -> dict[str, Any] | None:
    validate_index(index)
    identity = _require_text(asset_id, "asset_id")
    return next((deepcopy(asset) for asset in index["assets"] if asset["asset_id"] == identity), None)
