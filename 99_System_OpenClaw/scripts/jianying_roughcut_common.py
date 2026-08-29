#!/usr/bin/env python3
"""Shared helpers for the Jianying roughcut draft pipeline."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from edl_contract import EDLContractError
from edl_contract import parse_time_range as _canonical_parse_time_range

RAW360_EXTS = {".osv", ".lrf"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"} | RAW360_EXTS
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
MEDIA_EXTS = VIDEO_EXTS | IMAGE_EXTS


class ContractError(Exception):
    """Raised when a roughcut pipeline input violates the strict contract."""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractError(f"JSON file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContractError(f"YAML file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ContractError(f"YAML root must be an object: {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def parse_time_range(value: str) -> tuple[float, float]:
    """Parse the canonical "start-end" seconds string.

    Delegates to edl_contract.parse_time_range so the Jianying roughcut route
    shares the exact same validation (including millisecond-precision
    enforcement) as the rest of the EDL pipeline. This is a deliberate
    tightening versus the previous unrounded, precision-unchecked parsing:
    every EDL this route consumes is produced by edl_contract.write_edl
    (via 18_generate_storyboard_edl.py normalise_edl -> canonical_time_range)
    before it ever reaches this script, so it is already millisecond-precise
    and this closes a validation gap instead of risking a regression on
    historical draft plans.
    """
    try:
        return _canonical_parse_time_range(value, path="time_range")
    except EDLContractError as exc:
        raise ContractError(f"invalid time_range, expected start-end seconds: {value}: {exc}") from exc


def markdown_first_code_block(text: str, title: str) -> str | None:
    marker = f"# {title}"
    index = text.find(marker)
    if index == -1:
        return None
    fence = text.find("```", index)
    if fence == -1:
        return None
    body_start = text.find("\n", fence)
    if body_start == -1:
        return None
    body_end = text.find("```", body_start + 1)
    if body_end == -1:
        return None
    return text[body_start + 1 : body_end].strip()


def local_project_path_from_assets(local_assets_path: Path) -> Path:
    text = local_assets_path.read_text(encoding="utf-8")
    value = markdown_first_code_block(text, "本地项目路径")
    if not value:
        raise ContractError(f"local project path not found in {local_assets_path}")
    path = Path(value).expanduser()
    if not path.exists() or not path.is_dir():
        raise ContractError(f"local project path does not exist: {path}")
    return path


def ffprobe_duration_sec(path: Path) -> float:
    if path.suffix.lower() in IMAGE_EXTS:
        return 3600.0
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise ContractError(f"ffprobe returned invalid duration for {path}: {result.stdout!r}") from exc
    if duration <= 0:
        raise ContractError(f"media duration must be positive: {path}")
    return duration


def is_raw360_media(path: Path) -> bool:
    text = path.as_posix()
    return path.suffix.lower() in RAW360_EXTS or "360原始组" in text or "00_RawVault_不可直用" in text


def raw360_proxy_path(path: Path) -> Path:
    """Prefer the lightweight LRF proxy for native roughcut rendering."""
    if path.suffix.lower() != ".osv":
        return path
    candidates = [
        path.with_suffix(".LRF"),
        path.with_suffix(".lrf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def resolve_media_candidate(
    local_project_path: Path,
    candidates: list[Any],
    required_duration: float,
    *,
    allow_raw360_proxy: bool = False,
) -> dict[str, Any]:
    checked: list[dict[str, Any]] = []
    skipped_raw360: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            candidate_path = local_project_path / candidate_path
        candidate_path = candidate_path.expanduser().resolve()
        if is_raw360_media(candidate_path):
            if not allow_raw360_proxy:
                skipped_raw360.append(str(candidate_path))
                continue
            candidate_path = raw360_proxy_path(candidate_path)
        suffix = candidate_path.suffix.lower()
        if suffix not in MEDIA_EXTS or not candidate_path.exists():
            continue
        duration = ffprobe_duration_sec(candidate_path)
        checked.append({"path": candidate_path, "duration": duration})
        if duration >= required_duration:
            return {
                "path": str(candidate_path),
                "duration": duration,
                "source_duration_sec": required_duration,
                "media_duration_sec": duration,
                "is_raw360": is_raw360_media(candidate_path),
            }

    if not checked and skipped_raw360:
        examples = "\n".join(f"- {path}" for path in skipped_raw360[:5])
        raise ContractError(
            "native import pack cannot use RawVault/OSV/LRF 360 source directly. "
            "Export a reframed editable MP4 first and put that MP4 into the EDL candidate_files.\n"
            f"Skipped raw 360 candidates:\n{examples}"
        )
    if not checked:
        raise ContractError(f"no usable media candidate found for duration {required_duration}s")

    longest = max(checked, key=lambda item: float(item["duration"]))
    source_duration = float(longest["duration"])
    if source_duration <= 0:
        raise ContractError(f"selected media has invalid duration: {longest['path']}")
    return {
        "path": str(longest["path"]),
        "duration": source_duration,
        "source_duration_sec": source_duration,
        "speed": round(source_duration / required_duration, 6),
        "is_raw360": is_raw360_media(Path(str(longest["path"]))),
    }


def now_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
