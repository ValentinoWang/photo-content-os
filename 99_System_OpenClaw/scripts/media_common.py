#!/usr/bin/env python3
"""Shared helpers for reusable media-analysis scripts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".insv", ".osv", ".lrf"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".webp"}
METADATA_EXTS = {".xmp"}
MEDIA_EXTS = VIDEO_EXTS | IMAGE_EXTS | METADATA_EXTS

ANALYSIS_DIR = "_ai_analysis"
MANIFEST_NAME = "media_manifest.json"

DERIVED_DIR_NAMES = {
    "80_To_iCloudPhotos_精选入库": "selected_copy",
    "90_Draft_Project": "draft_project",
    "91_Output": "output",
    "92_Aliyun_SyncReady": "sync_ready",
    "93_GroupPhoto_Distribution_合照发放": "group_photo_distribution",
    "App_WorkCache": "work_cache",
}


def project_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"project path does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"project path is not a directory: {path}")
    return path


def project_additions_dir(project: Path) -> Path:
    return project / "待增加"


def ensure_project_additions_dir(additions: Path, project: Path) -> Path:
    additions = additions.expanduser().resolve()
    expected = project_additions_dir(project).resolve()
    if additions != expected:
        raise RuntimeError(f"待增加目录必须位于正式项目内：{expected}\n当前目录：{additions}")
    return additions


def manifest_path(project: Path) -> Path:
    return project / ANALYSIS_DIR / MANIFEST_NAME


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_text(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def ffprobe_json(path: Path) -> dict[str, Any]:
    output = run_text(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:format_tags:stream=index,codec_type,codec_name,width,height,avg_frame_rate,channels",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ]
    )
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid JSON for {path}") from exc


def parse_iso6709(value: str | None) -> tuple[float | None, float | None, float | None]:
    if not value:
        return None, None, None
    match = re.match(r"^([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)?/?$", value)
    if not match:
        return None, None, None
    latitude = float(match.group(1))
    longitude = float(match.group(2))
    altitude = float(match.group(3)) if match.group(3) else None
    return latitude, longitude, altitude


def safe_slug(text: str, max_len: int = 96) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text, flags=re.UNICODE).strip("._")
    return (cleaned or "media")[:max_len]


def media_id(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]


def relative_posix(path: Path, project: Path) -> str:
    return path.relative_to(project).as_posix()


def is_hidden_or_analysis(path: Path, project: Path) -> bool:
    rel_parts = path.relative_to(project).parts
    if any(part.startswith(".") for part in rel_parts):
        return True
    return ANALYSIS_DIR in rel_parts


def lifecycle_for(path: Path, project: Path) -> str:
    for part in path.relative_to(project).parts:
        if part in DERIVED_DIR_NAMES:
            return DERIVED_DIR_NAMES[part]
    if "Raw_待处理" in path.parts or "00_RawVault_不可直用" in path.parts:
        return "raw_or_pending"
    return "primary"


def source_type(filename: str, relative_path: str, live_status: str | None = None) -> str:
    text = f"{filename} {relative_path}".lower()
    if live_status:
        return "Live Photo"
    if filename.lower().endswith((".osv", ".lrf")):
        return "360相机原始组"
    if "dji" in text or "osmo" in text:
        return "DJI"
    if "insta" in text or filename.lower().endswith(".insv"):
        return "Insta360"
    if "wink" in text:
        return "Wink输出"
    if "screen" in text or "录屏" in text:
        return "录屏"
    return "普通素材"


# Raw 360/panoramic-camera source material cannot be used as an executable
# edit clip until it has been reframed/reconstructed (see
# 99_System_OpenClaw/docs/03_项目目录与素材处理.md and
# 11_rename_media_file.py:RAW_ASSOCIATED_EXTS). ".insv" is included alongside
# ".osv"/".lrf" because 11_rename_media_file.py already groups it with them
# as one raw-associated set, and the project docs consistently describe
# OSV/LRF/INSV as one "must not be split, must be reconstructed before use"
# group.
RAW360_SUFFIXES = {".osv", ".lrf", ".insv"}

# Path substrings that name the RawVault/raw-360 convention used across the
# vault structure. Matched as whole, specific tokens (never split into looser
# fragments like a bare "rawvault" or "不可直用") to avoid false positives
# from unrelated paths that happen to contain part of the phrase.
RAW360_PATH_TOKENS = (
    "00_rawvault_不可直用",
    "360原始组",
    "raw360",
)

RAW360_SOURCE_TYPES = {"360相机原始组"}


def is_raw360_path(path_or_text: Path | str) -> bool:
    """Return True when a path/string denotes raw 360-camera material.

    Matches by exact suffix -- never by treating an extension as a substring
    that could appear anywhere in a path (a directory whose name happens to
    contain ".osv" must not be misjudged as raw 360 media) -- plus a
    case-folded substring match against a small, specific set of path
    tokens naming the RawVault/raw-360 convention.
    """
    text = path_or_text.as_posix() if isinstance(path_or_text, Path) else str(path_or_text)
    suffix = Path(text).suffix.lower()
    if suffix in RAW360_SUFFIXES:
        return True
    folded = text.casefold()
    return any(token in folded for token in RAW360_PATH_TOKENS)


def is_raw360_item(item: dict[str, Any]) -> bool:
    """Return True when a media-manifest item denotes raw 360 material.

    Any of the following is sufficient:
    - an already-computed `is_raw360` field (an upstream stage may have
      decided this once already; trust it rather than recomputing);
    - `source_type` is the 360-camera raw source type;
    - `raw_decision_tokens` explicitly contains "reframe_needed". This is
      read only from that structured field, never matched as a free
      substring against a path/filename -- a clip whose name happens to
      contain the words "reframe needed" is not proof the material is raw
      360, and matching it as a path substring would misjudge such files;
    - the item's relative_path matches `is_raw360_path`.
    """
    if item.get("is_raw360"):
        return True
    if str(item.get("source_type") or "") in RAW360_SOURCE_TYPES:
        return True
    raw_tokens = item.get("raw_decision_tokens") or []
    if "reframe_needed" in raw_tokens:
        return True
    relative_path = str(item.get("relative_path") or "")
    return bool(relative_path) and is_raw360_path(relative_path)


def load_manifest(project: Path) -> dict[str, Any]:
    path = manifest_path(project)
    if not path.exists():
        raise FileNotFoundError(f"manifest not found, run 01_scan_media_manifest.py first: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return {"project_dir": str(project), "generated_at": None, "items": data}
    if not isinstance(data, dict) or "items" not in data:
        raise ValueError(f"invalid manifest format: {path}")
    return data


def save_manifest(project: Path, data: dict[str, Any]) -> None:
    path = manifest_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def eligible_item(item: dict[str, Any], include_derived: bool = False) -> bool:
    if include_derived:
        return item.get("media_type") in {"video", "image"}
    return bool(item.get("analysis_eligible")) and item.get("media_type") in {"video", "image"}
