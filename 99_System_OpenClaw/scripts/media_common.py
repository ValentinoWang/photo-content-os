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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
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
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def eligible_item(item: dict[str, Any], include_derived: bool = False) -> bool:
    if include_derived:
        return item.get("media_type") in {"video", "image"}
    return bool(item.get("analysis_eligible")) and item.get("media_type") in {"video", "image"}
