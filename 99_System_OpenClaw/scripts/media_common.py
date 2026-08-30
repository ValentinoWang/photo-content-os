#!/usr/bin/env python3
"""Shared helpers for reusable media-analysis scripts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

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


# --- File/content hashing shared by analysis_tiering.py (L-13/r8: file_sha256
# --- was duplicated verbatim across 5+ scripts; stable_json_hash is its
# --- canonical-JSON counterpart used to derive cache/idempotency keys), and
# --- by edit_backends/handoff_pack.py, edit_backends/otio_kdenlive.py,
# --- 32_process_openclaw_queue.py and 45_archive_project.py, all of which
# --- previously carried their own byte-identical streaming sha256_file.


def file_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# --- Path-safety guards against directory escape (L-07: a project-relative
# --- path resolver; L-08: a plain containment check). These are two
# --- distinct shapes of the same "is this path actually inside that
# --- directory" question -- resolver returns the resolved Path (or None),
# --- containment returns a bool for a caller that already has two resolved
# --- (or resolve-worthy) Paths in hand -- so they are kept as two functions
# --- rather than one trying to serve both call shapes.


def path_inside(child: Path, parent: Path) -> bool:
    """True when `child` resolves to a location inside (or equal to) `parent`.

    Baseline: project_bootstrap_common.py's inside(), byte-identical across
    7 call sites before this consolidation. Deliberately NOT the right fit
    for edit_backends/handoff_pack.py's path_is_within(), which skips
    resolve() on purpose (see that function's docstring) -- that one stays
    separate.
    """
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_project_file(project: Path, raw: object, *, must_be_file: bool = True) -> Path | None:
    """Resolve `raw` (absolute or project-relative) to a Path inside `project`.

    Returns None for a non-string/blank `raw`, a path that resolves outside
    `project` (directory-escape guard), or -- when must_be_file=True, the
    default -- a resolved path that is not an existing file.

    Baseline: 05_write_content_summary.py's _safe_project_file (identical to
    03_transcribe_audio.py's _safe_audio_path). Callers needing a different
    failure mode than "return None" -- e.g. raising a domain-specific error,
    or explicitly tolerating a not-yet-existing output path -- should call
    this with must_be_file=False and apply their own existence/escape
    handling on top, rather than reimplementing the resolution logic.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = Path(raw).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve()
    try:
        resolved.relative_to(project.resolve())
    except ValueError:
        return None
    if must_be_file:
        return resolved if resolved.is_file() else None
    return resolved


# Directory-wide glob patterns shared by writers (04/05) and prune helpers.
PROMPT_GLOB = "*_prompt.md"
SUMMARY_GLOB = "*.summary.md"


def item_prompt_path(prompt_dir: Path, item: dict[str, Any]) -> Path:
    """Canonical per-item prompt file path, as written by 04_generate_ai_prompt.py."""
    return prompt_dir / f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}_prompt.md"


def item_summary_path(summary_dir: Path, item: dict[str, Any]) -> Path:
    """Canonical per-item summary file path, as written by 05_write_content_summary.py."""
    return summary_dir / f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}.summary.md"


def find_item_summary(summaries_dir: Path, item: dict[str, Any]) -> Path | None:
    """Locate an existing summary file for `item`, tolerating filename drift.

    Tries the media_id-prefixed glob first (the stable identity every writer
    uses); falls back to a slug-based glob on the relative_path stem. The
    fallback MUST use safe_slug(stem), matching what item_summary_path()
    above actually writes -- matching on the raw, un-slugged stem instead
    means a stem containing spaces, CJK punctuation, or other characters
    safe_slug() rewrites can never be found by this fallback.
    """
    media_id_value = str(item.get("media_id") or item.get("id") or "")
    stem = Path(str(item.get("relative_path", ""))).stem
    candidates = list(summaries_dir.glob(f"{media_id_value}_*.summary.md")) if media_id_value else []
    candidates.extend(summaries_dir.glob(f"*_{safe_slug(stem)}.summary.md"))
    for path in candidates:
        if path.exists():
            return path
    return None


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


# --- Media scan helpers shared by 01_scan_media_manifest.py and
# --- 08_plan_additions_merge.py.

# HEIC/JPEG (still) + MOV (motion) + XMP (metadata) sharing the same
# directory and stem are treated as one Live Photo group.
LIVE_GROUP_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".mov", ".xmp"}


def discover_live_groups(paths: list[Path], project: Path) -> dict[tuple[str, str], dict[str, bool]]:
    groups: dict[tuple[str, str], dict[str, bool]] = {}
    for path in paths:
        ext = path.suffix.lower()
        if ext not in LIVE_GROUP_EXTS:
            continue
        key = (relative_posix(path.parent, project), path.stem)
        group = groups.setdefault(key, {"still": False, "motion": False, "xmp": False})
        if ext in {".heic", ".heif", ".jpg", ".jpeg"}:
            group["still"] = True
        elif ext == ".mov":
            group["motion"] = True
        elif ext == ".xmp":
            group["xmp"] = True
    return groups


def live_status_for(
    path: Path,
    project: Path,
    groups: dict[tuple[str, str], dict[str, bool]],
) -> tuple[str | None, str | None, str | None]:
    """Return (status, role, group_id) for a Live Photo group member, or (None, None, None).

    group_id is 08_plan_additions_merge.py's addition (a stable id for the
    still/motion/xmp trio, used to name merged Live Photo output files
    consistently). 01_scan_media_manifest.py's caller ignores it -- writing
    live_group_id into the manifest is a separate behavior change the audit
    flagged as needing its own decision, not something to add as a side
    effect of this consolidation.
    """
    ext = path.suffix.lower()
    if ext not in LIVE_GROUP_EXTS:
        return None, None, None
    key = (relative_posix(path.parent, project), path.stem)
    group = groups.get(key)
    if not group or not (group["still"] and group["motion"]):
        return None, None, None
    status = "complete_heic_mov_xmp" if group["xmp"] else "heic_mov_missing_xmp"
    group_id = media_id("/".join(key))
    if ext in {".heic", ".heif", ".jpg", ".jpeg"}:
        return status, "still", group_id
    if ext == ".mov":
        return status, "motion", group_id
    return status, "metadata", group_id


def media_dimensions_for_image(path: Path) -> tuple[int | None, int | None]:
    if not shutil.which("sips"):
        return None, None
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None, None
    width = None
    height = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("pixelWidth:"):
            width = int(line.split(":", 1)[1].strip())
        elif line.startswith("pixelHeight:"):
            height = int(line.split(":", 1)[1].strip())
    return width, height


def video_info(path: Path) -> dict[str, object]:
    """ffprobe-derived video facts, including avg_frame_rate.

    01_scan_media_manifest.py originally carried this field; 08's own copy
    did not. Both now get it -- 08's addition-plan JSON gaining
    avg_frame_rate is a verified-safe additive field, not a behavior removal.
    """
    info = ffprobe_json(path)
    format_info = info.get("format", {})
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    tags = format_info.get("tags") or {}
    location_raw = tags.get("com.apple.quicktime.location.ISO6709")
    latitude, longitude, altitude = parse_iso6709(location_raw)
    duration_raw = format_info.get("duration")
    duration = round(float(duration_raw), 3) if duration_raw else None
    return {
        "duration_sec": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "avg_frame_rate": video_stream.get("avg_frame_rate"),
        "has_audio": has_audio,
        "created_at": tags.get("creation_time"),
        "location_raw": location_raw,
        "gps_latitude": latitude,
        "gps_longitude": longitude,
        "gps_altitude": altitude,
        "gps_horizontal_accuracy": tags.get("com.apple.quicktime.location.accuracy.horizontal"),
    }


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


# --- Config-file readers (L-20/SV-06): "check exists, parse, check root is a
# --- mapping/object" boilerplate that was previously written out 5 times for
# --- YAML and 3 more times for JSON, differing only in which domain
# --- exception type each caller raises (and, for one YAML and one JSON
# --- caller, the noun used in the message). `error` takes that exception
# --- type's constructor (or any Callable[[str], Exception]) so each caller
# --- keeps its own exception class; `label`/`root_label` reproduce the two
# --- callers whose message wording differs from the rest.
#
# edit_backends/handoff_pack.py's read_json_object is deliberately NOT
# folded in here: it raises HandoffError(code, message) with three distinct
# machine-readable codes (input_missing/invalid_json/invalid_json_root) per
# failure mode, which the single Callable[[str], Exception] `error` shape
# below cannot reproduce without collapsing those codes to one -- a real
# behavior loss, not a style difference. It keeps its own implementation.


def read_yaml_mapping(
    path: Path,
    *,
    error: Callable[[str], Exception],
    label: str = "YAML file",
    root_label: str = "mapping",
) -> dict[str, Any]:
    """Read `path` as YAML and require its root to be a mapping.

    Baseline: 33_enqueue_openclaw_queue_job.py's load_yaml -- the only one
    of 5 near-identical copies that also rejected a directory path (not
    just a missing one) before this consolidation. Catching yaml.YAMLError
    here (none of the 5 originals did) is a deliberate behavior improvement,
    not an equivalence-preserving refactor: malformed YAML now raises the
    caller's own domain exception instead of a raw pyyaml exception escaping
    past it.
    """
    if not path.exists() or not path.is_file():
        raise error(f"{label} does not exist: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        raise error(f"{label} is not valid YAML: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise error(f"{label} root must be a {root_label}: {path}")
    return data


def read_json_object(
    path: Path,
    *,
    error: Callable[[str], Exception],
    label: str = "JSON file",
) -> dict[str, Any]:
    """Read `path` as JSON and require its root to be an object.

    Catches both OSError and json.JSONDecodeError (edit_backends/
    otio_kdenlive.py's read_json was the only one of the 3 folded-in copies
    that caught OSError; jianying_roughcut_common.py's load_json and
    32_process_openclaw_queue.py's load_json did not, so a missing/
    unreadable file previously escaped as a raw OSError instead of the
    caller's own domain exception for those two -- the same deliberate
    improvement as read_yaml_mapping's YAMLError handling above).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise error(f"cannot read {label}: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise error(f"{label} root must be an object: {path}")
    return data


# --- Atomic on-disk writers.
#
# This is a first, deliberately narrow pass (L-12): only the two call sites
# named by the audit (validate_content_os_task.write_blocked_result,
# mac_openclaw_runner.write_yaml) are migrated to these helpers in this
# round. The cluster's other ~12 non-atomic write points (31's write_link,
# several in 19_review_output_video.py, jianying_roughcut_common.py,
# otio_kdenlive.py, run_analyze_project.py, etc.) are NOT touched here --
# each has its own behavior nuances that need individually checking before
# switching them over. sort_keys is deliberately a per-call parameter, not
# unified to one default: forcing every writer to the same sort_keys value
# would change the byte-for-byte diff of every produced artifact at once,
# which is explicitly out of scope for this pass.


def _atomic_temp_path(path: Path, *, hidden_temp: bool) -> Path:
    if hidden_temp:
        return path.with_name(f".{path.name}.tmp")
    return path.with_suffix(f"{path.suffix}.tmp")


def write_json_atomic(
    path: Path,
    data: Any,
    *,
    sort_keys: bool = False,
    hidden_temp: bool = False,
    trailing_newline: bool = True,
) -> None:
    """Write JSON atomically: mkdir + temp file + os.replace.

    Skeleton taken from edit_backends/handoff_pack.py's write_json(). That
    function always passes sort_keys=True; this shared version defaults to
    False (most JSON writers in this codebase do not sort keys) and leaves
    it to each caller to pass what its own current output already does.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _atomic_temp_path(path, hidden_temp=hidden_temp)
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=sort_keys)
        if trailing_newline:
            handle.write("\n")
    os.replace(temporary, path)


def write_yaml_atomic(
    path: Path,
    data: Any,
    *,
    sort_keys: bool = False,
    hidden_temp: bool = False,
) -> None:
    """Write YAML atomically, same mkdir + temp file + os.replace skeleton as write_json_atomic.

    Added alongside write_json_atomic because this round's two named
    migration targets are both YAML writers, not JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _atomic_temp_path(path, hidden_temp=hidden_temp)
    with temporary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=sort_keys)
    os.replace(temporary, path)


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


# --- Keyframe sampling / preview generation, shared by 08_plan_additions_merge.py,
# --- 11_rename_media_file.py and 19_review_output_video.py.
#
# 02_extract_keyframes.py's own sampling variant (_timestamp_candidates) is
# deliberately NOT folded in here: it is its own independent sampling
# strategy within that one module, not a duplicate of this one.


def timestamp_label(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    total_seconds, ms = divmod(millis, 1000)
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}-{minutes:02d}-{sec:02d}-{ms:03d}"
    return f"{minutes:02d}-{sec:02d}-{ms:03d}"


@dataclass(frozen=True)
class SamplingPreset:
    """Numeric knobs for sample_times(). Each caller's preset is independent --
    do not fold RENAME_PREVIEW_SAMPLING and OUTPUT_REVIEW_SAMPLING into one
    shared value; they intentionally disagree (frame budget, the duration<=0
    fallback timestamp, the seconds-per-sampled-frame step, and how close to
    the clip's edges the first/last sample may land)."""

    max_frames: int
    zero_duration_fallback: float
    step_seconds: float
    edge_margin_seconds: float
    edge_margin_ratio: float
    single_frame_floor: float | None


# 08_plan_additions_merge.py and 11_rename_media_file.py: sparse preview frames
# (up to 5, one per ~3s), used only to help a human/LLM recognize the clip.
RENAME_PREVIEW_SAMPLING = SamplingPreset(
    max_frames=5,
    zero_duration_fallback=0.5,
    step_seconds=3.0,
    edge_margin_seconds=0.5,
    edge_margin_ratio=0.15,
    single_frame_floor=0.2,
)

# 19_review_output_video.py: dense uniform frames (up to 48, one per 0.75s) for
# frame-level output review; duration<=0 falls back to 0.0, not 0.5.
OUTPUT_REVIEW_SAMPLING = SamplingPreset(
    max_frames=48,
    zero_duration_fallback=0.0,
    step_seconds=0.75,
    edge_margin_seconds=0.25,
    edge_margin_ratio=0.1,
    single_frame_floor=None,
)


def sample_times(duration: float, preset: SamplingPreset) -> list[float]:
    if duration <= 0:
        return [preset.zero_duration_fallback]
    count = min(preset.max_frames, max(1, math.ceil(duration / preset.step_seconds)))
    if count == 1:
        candidate = duration * 0.5
        if preset.single_frame_floor is not None:
            candidate = max(candidate, preset.single_frame_floor)
        return [min(candidate, max(duration - 0.1, 0.0))]
    start = min(preset.edge_margin_seconds, duration * preset.edge_margin_ratio)
    end = max(duration - min(preset.edge_margin_seconds, duration * preset.edge_margin_ratio), start)
    step = (end - start) / (count - 1)
    return [round(start + step * index, 3) for index in range(count)]


def extract_video_keyframes(
    source: Path,
    output_dir: Path,
    duration: float,
    preset: SamplingPreset,
    *,
    scale_width: int = 640,
) -> list[Path]:
    """ffmpeg-sample `source` at preset's timestamps into an already-prepared output_dir.

    The caller owns output_dir: creating it and clearing any stale frames from
    a prior run are the caller's responsibility (08 and 11 clear differently --
    11 also proactively clears a stale contact_sheet.jpg -- so that stays out
    of this shared function rather than being silently unified).
    """
    if not shutil.which("ffmpeg"):
        return []
    frames: list[Path] = []
    for index, seconds in enumerate(sample_times(duration, preset), start=1):
        output = output_dir / f"frame_{index:04d}_{timestamp_label(seconds)}.jpg"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seconds:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            f"scale='min({scale_width},iw)':-2",
            str(output),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            frames.append(output)
    return frames


def extract_still_frame_preview(source: Path, output_dir: Path) -> list[Path]:
    """sips (macOS) or Pillow fallback: a single still-image preview into output_dir."""
    output = output_dir / "frame_0001_image.jpg"
    if shutil.which("sips"):
        result = subprocess.run(
            ["sips", "-s", "format", "jpeg", str(source), "--out", str(output)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return [output]

    try:
        from PIL import Image
    except ImportError:
        return []
    try:
        image = Image.open(source).convert("RGB")
        image.thumbnail((960, 960))
        image.save(output, quality=90)
    except Exception:
        return []
    if output.exists() and output.stat().st_size > 0:
        return [output]
    return []


def build_frame_contact_sheet(frames: list[Path], output_path: Path) -> Path | None:
    """2-column, 320x180-thumbnail contact sheet (08/11's shared layout).

    Does not create output_path's parent directory -- both callers already
    guarantee it exists by the time frames were extracted into it.
    """
    if not frames:
        return None
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    images = []
    for frame in frames:
        image = Image.open(frame).convert("RGB")
        image.thumbnail((320, 180))
        canvas = Image.new("RGB", (320, 180), "white")
        canvas.paste(image, ((320 - image.width) // 2, (180 - image.height) // 2))
        images.append((frame.name, canvas))

    cols = 2
    rows = math.ceil(len(images) / cols)
    output = Image.new("RGB", (cols * 320, rows * 220), "white")
    draw = ImageDraw.Draw(output)
    for index, (name, image) in enumerate(images):
        x = (index % cols) * 320
        y = (index // cols) * 220
        draw.text((x + 8, y + 4), name, fill=(0, 0, 0))
        output.paste(image, (x, y + 20))

    output.save(output_path, quality=90)
    return output_path
