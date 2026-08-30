#!/usr/bin/env python3
"""Canonical Edit Decision List contract shared by AI, preview and handoff backends.

The contract intentionally normalises legacy model output into the one shape
accepted by the handoff backend.  It performs deterministic format repair only;
it never invents a source file, caption or timing.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "edit_decision_list_v1"
SCHEMA_VERSION_V2 = "edit_decision_list_v2"
DOC_TYPE = "edit_decision_list"
TIMING_TOLERANCE = 0.000_001
REQUIRED_CLIP_TEXT_FIELDS = ("purpose", "visual_need", "caption", "edit_note")

# v2 vocabulary.  `role` is the narrative job a clip performs; `layer` is where
# it sits in the composition stack.  The two are deliberately orthogonal: a
# full-screen B-roll cutaway is role="b_roll" on layer="primary", while the same
# footage as a picture-in-picture insert is role="b_roll" on layer="overlay".
CLIP_ROLES = ("a_roll", "b_roll", "overlay", "title")
CLIP_LAYERS = ("primary", "overlay", "background")
DEFAULT_CLIP_LAYER = "primary"

# Only the primary layer carries the "one thing on screen at a time" rule.
# Overlay and background clips are expected to sit on top of, or behind, it.
EXCLUSIVE_LAYERS = frozenset({"primary"})

CROP_KEYS = ("x", "y", "width", "height")


@dataclass(frozen=True)
class EDLContractError(ValueError):
    code: str
    message: str
    path: str = ""

    def __str__(self) -> str:
        location = f" ({self.path})" if self.path else ""
        return f"{self.code}{location}: {self.message}"


def _fail(code: str, message: str, path: str = "") -> None:
    raise EDLContractError(code=code, message=message, path=path)


def parse_seconds(value: Any, *, path: str) -> float:
    if isinstance(value, bool):
        _fail("invalid_timing", "必须是非负秒数", path)
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        _fail("invalid_timing", f"必须是非负秒数，收到 {value!r}", path)
    if not math.isfinite(seconds) or seconds < 0:
        _fail("invalid_timing", f"必须是有限非负秒数，收到 {value!r}", path)
    rounded = round(seconds, 3)
    if abs(seconds - rounded) > TIMING_TOLERANCE:
        _fail("timing_precision", f"必须精确到毫秒，收到 {value!r}", path)
    return rounded


def parse_time_range(value: Any, *, path: str = "time_range") -> tuple[float, float]:
    """Read the canonical string or the legacy timeline_in/timeline_out object."""
    if isinstance(value, str):
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*s?\s*-\s*(\d+(?:\.\d+)?)\s*s?\s*",
            value,
            flags=re.IGNORECASE,
        )
        if not match:
            _fail("invalid_timing", "格式必须是“起点-终点”的秒数文本", path)
        start = parse_seconds(match.group(1), path=f"{path}.start")
        end = parse_seconds(match.group(2), path=f"{path}.end")
    elif isinstance(value, dict):
        # Backward-compatible deterministic repair for the format reported by
        # the ordinary-user test.  The repaired value is always written back as
        # a canonical string before any downstream backend sees it.
        if "timeline_in" not in value or "timeline_out" not in value:
            _fail("invalid_timing", "对象必须同时包含 timeline_in 和 timeline_out", path)
        start = parse_seconds(value["timeline_in"], path=f"{path}.timeline_in")
        end = parse_seconds(value["timeline_out"], path=f"{path}.timeline_out")
    else:
        _fail("invalid_timing", "必须是“起点-终点”文本", path)
    if end <= start:
        _fail("invalid_timing", "终点必须大于起点", path)
    return start, end


def canonical_time_range(start: float, end: float) -> str:
    return f"{start:.3f}-{end:.3f}"


def _required_text(clip: dict[str, Any], field: str, *, path: str) -> str:
    value = clip.get(field)
    if field == "caption" and not value:
        value = clip.get("subtitle")
    text = str(value or "").strip()
    if not text:
        _fail(f"{field}_missing", f"缺少必填字段 {field}", f"{path}.{field}")
    return text


def _optional_enum(
    raw: dict[str, Any], field: str, allowed: tuple[str, ...], *, path: str
) -> str | None:
    """Read an optional closed-vocabulary field.  Absent stays absent."""
    if field not in raw or raw[field] in (None, ""):
        return None
    value = raw[field]
    if not isinstance(value, str) or value.strip() not in allowed:
        _fail(
            f"{field}_invalid",
            f"{field} 必须是 {'、'.join(allowed)} 之一，收到 {value!r}",
            f"{path}.{field}",
        )
    return value.strip()


def _optional_number(
    raw: dict[str, Any],
    field: str,
    *,
    path: str,
    minimum: float | None = None,
    exclusive_minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    if field not in raw or raw[field] is None:
        return None
    value = raw[field]
    if isinstance(value, bool):
        _fail(f"{field}_invalid", f"{field} 必须是数字", f"{path}.{field}")
    try:
        number = float(value)
    except (TypeError, ValueError):
        _fail(f"{field}_invalid", f"{field} 必须是数字，收到 {value!r}", f"{path}.{field}")
    if not math.isfinite(number):
        _fail(f"{field}_invalid", f"{field} 必须是有限数字", f"{path}.{field}")
    if minimum is not None and number < minimum:
        _fail(f"{field}_invalid", f"{field} 不能小于 {minimum}", f"{path}.{field}")
    if exclusive_minimum is not None and number <= exclusive_minimum:
        _fail(f"{field}_invalid", f"{field} 必须大于 {exclusive_minimum}", f"{path}.{field}")
    if maximum is not None and number > maximum:
        _fail(f"{field}_invalid", f"{field} 不能大于 {maximum}", f"{path}.{field}")
    return number


def _optional_text(raw: dict[str, Any], field: str, *, path: str) -> str | None:
    if field not in raw or raw[field] in (None, ""):
        return None
    text = str(raw[field]).strip()
    if not text:
        _fail(f"{field}_invalid", f"{field} 不能是空字符串", f"{path}.{field}")
    return text


def _normalise_crop(raw: Any, *, path: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        _fail("crop_invalid", "crop 必须是对象", path)
    missing = [key for key in CROP_KEYS if key not in raw]
    if missing:
        _fail("crop_invalid", f"crop 缺少 {'、'.join(missing)}", path)
    crop: dict[str, float] = {}
    for key in CROP_KEYS:
        value = _optional_number(
            raw,
            key,
            path=path,
            minimum=0.0 if key in ("x", "y") else None,
            exclusive_minimum=0.0 if key in ("width", "height") else None,
            maximum=1.0,
        )
        if value is None:
            _fail("crop_invalid", f"crop.{key} 不能为空", f"{path}.{key}")
        crop[key] = value
    for axis, extent in (("x", "width"), ("y", "height")):
        if crop[axis] + crop[extent] > 1.0 + TIMING_TOLERANCE:
            _fail(
                "crop_invalid",
                f"crop.{axis} 与 crop.{extent} 之和不能超出画面",
                f"{path}.{extent}",
            )
    return crop


def _normalise_transform(raw: Any, *, path: str) -> dict[str, Any]:
    """Normalise the optional geometry/motion block (scale, position, crop, Ken Burns)."""
    if not isinstance(raw, dict):
        _fail("transform_invalid", "transform 必须是对象", path)
    transform: dict[str, Any] = {}
    scale = _optional_number(raw, "scale", path=path, exclusive_minimum=0.0)
    if scale is not None:
        transform["scale"] = scale
    for field in ("position", "animation"):
        text = _optional_text(raw, field, path=path)
        if text is not None:
            transform[field] = text
    if raw.get("crop") is not None:
        transform["crop"] = _normalise_crop(raw["crop"], path=f"{path}.crop")
    if not transform:
        _fail("transform_invalid", "transform 不能是空对象", path)
    return transform


def _normalise_music_track(raw: Any, *, index: int) -> dict[str, Any]:
    path = f"music[{index}]"
    if not isinstance(raw, dict):
        _fail("music_invalid", "音乐轨必须是对象", path)
    source = _optional_text(raw, "source", path=path)
    if source is None:
        _fail("music_invalid", "音乐轨必须有 source", f"{path}.source")
    track: dict[str, Any] = {"source": source}
    start = parse_seconds(raw.get("timeline_start_sec", 0), path=f"{path}.timeline_start_sec")
    track["timeline_start_sec"] = start
    for field, kwargs in (
        ("timeline_end_sec", {"minimum": 0.0}),
        ("source_start_sec", {"minimum": 0.0}),
        ("volume", {"minimum": 0.0, "maximum": 2.0}),
        ("fade_in_sec", {"minimum": 0.0}),
        ("fade_out_sec", {"minimum": 0.0}),
        ("duck_to", {"minimum": 0.0, "maximum": 2.0}),
    ):
        value = _optional_number(raw, field, path=path, **kwargs)
        if value is not None:
            track[field] = value
    if "timeline_end_sec" in track and track["timeline_end_sec"] <= start:
        _fail("music_invalid", "音乐轨终点必须大于起点", f"{path}.timeline_end_sec")
    loop = raw.get("loop")
    if loop is not None:
        if not isinstance(loop, bool):
            _fail("music_invalid", "loop 必须是布尔值", f"{path}.loop")
        track["loop"] = loop
    note = _optional_text(raw, "note", path=path)
    if note is not None:
        track["note"] = note
    return track


def normalise_clip(raw: Any, *, index: int) -> dict[str, Any]:
    path = f"clips[{index}]"
    if not isinstance(raw, dict):
        _fail("edl_clip_format", "片段必须是对象", path)

    slot_value = raw.get("slot", index + 1)
    if isinstance(slot_value, bool):
        _fail("edl_slot_invalid", "slot 必须是唯一正整数", f"{path}.slot")
    try:
        slot = int(slot_value)
    except (TypeError, ValueError):
        _fail("edl_slot_invalid", "slot 必须是唯一正整数", f"{path}.slot")
    if slot <= 0 or str(slot_value).strip() not in {str(slot), f"{slot}.0"}:
        _fail("edl_slot_invalid", "slot 必须是唯一正整数", f"{path}.slot")

    if "time_range" in raw:
        start, end = parse_time_range(raw["time_range"], path=f"{path}.time_range")
    else:
        start = parse_seconds(raw.get("timeline_start_sec"), path=f"{path}.timeline_start_sec")
        duration = parse_seconds(raw.get("duration_sec"), path=f"{path}.duration_sec")
        if duration <= 0:
            _fail("invalid_timing", "duration_sec 必须大于 0", f"{path}.duration_sec")
        end = round(start + duration, 3)
    duration = round(end - start, 3)

    source_file = str(raw.get("source_file") or "").strip()
    raw_candidates = raw.get("candidate_files")
    candidate_files: list[str] = []
    if isinstance(raw_candidates, list):
        for value in raw_candidates:
            text = str(value or "").strip()
            if text and text not in candidate_files:
                candidate_files.append(text)
    elif raw_candidates is not None:
        _fail("candidate_files_invalid", "candidate_files 必须是数组", f"{path}.candidate_files")
    if source_file and source_file not in candidate_files:
        candidate_files.insert(0, source_file)
    if not source_file and not candidate_files:
        _fail(
            "source_missing",
            "可执行片段必须包含 source_file 或非空 candidate_files；缺失素材应写入顶层 missing_materials",
            path,
        )

    normalised: dict[str, Any] = {
        "slot": slot,
        "time_range": canonical_time_range(start, end),
        "source_start_sec": parse_seconds(raw.get("source_start_sec", 0), path=f"{path}.source_start_sec"),
        "purpose": _required_text(raw, "purpose", path=path),
        "visual_need": _required_text(raw, "visual_need", path=path),
        "caption": _required_text(raw, "caption", path=path),
        "candidate_files": candidate_files,
        "edit_note": _required_text(raw, "edit_note", path=path),
    }
    if source_file:
        normalised["source_file"] = source_file

    # v2 vocabulary.  Every field below is optional and is emitted only when the
    # caller supplied it, so a v1 document normalises to byte-identical output.
    # Consumers read the documented defaults: layer="primary", speed=1.0.
    role = _optional_enum(raw, "role", CLIP_ROLES, path=path)
    if role is not None:
        normalised["role"] = role
    layer = _optional_enum(raw, "layer", CLIP_LAYERS, path=path)
    if layer is not None:
        normalised["layer"] = layer

    speed = _optional_number(raw, "speed", path=path, exclusive_minimum=0.0)
    if speed is not None:
        normalised["speed"] = speed
    volume = _optional_number(raw, "volume", path=path, minimum=0.0, maximum=2.0)
    if volume is not None:
        normalised["volume"] = volume

    if raw.get("transform") is not None:
        normalised["transform"] = _normalise_transform(
            raw["transform"], path=f"{path}.transform"
        )

    for field in ("transition_in", "transition_out"):
        text = _optional_text(raw, field, path=path)
        if text is not None:
            normalised[field] = text
    transition_duration = _optional_number(
        raw, "transition_duration", path=path, minimum=0.0
    )
    if transition_duration is not None:
        if "transition_in" not in normalised and "transition_out" not in normalised:
            _fail(
                "transition_duration_invalid",
                "transition_duration 必须搭配 transition_in 或 transition_out",
                f"{path}.transition_duration",
            )
        normalised["transition_duration"] = transition_duration

    for optional in ("transition", "audio_note", "evidence_refs"):
        value = raw.get(optional)
        if value not in (None, "", []):
            normalised[optional] = value
    return normalised


def clip_layer(clip: dict[str, Any]) -> str:
    """The composition layer a clip sits on.  Absent means the primary track."""
    return str(clip.get("layer") or DEFAULT_CLIP_LAYER)


V2_CLIP_FIELDS = (
    "role",
    "layer",
    "speed",
    "volume",
    "transform",
    "transition_in",
    "transition_out",
    "transition_duration",
)
V2_DOCUMENT_FIELDS = ("audio", "music", "subtitles")


def normalise_edl(
    raw: Any,
    *,
    generation_model: str | None = None,
    generation_reasoning: str | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _fail("invalid_json_root", "EDL 根节点必须是对象")
    clips_raw = raw.get("clips")
    if not isinstance(clips_raw, list) or not clips_raw:
        _fail("edl_clips_missing", "EDL 必须有非空 clips 列表", "clips")

    clips = [normalise_clip(clip, index=index) for index, clip in enumerate(clips_raw)]
    slots = [clip["slot"] for clip in clips]
    if len(set(slots)) != len(slots):
        _fail("edl_slot_invalid", "slot 必须唯一", "clips")

    # Ordering and non-overlap are enforced per composition layer.  Overlay and
    # background clips are meant to sit on top of, or behind, the primary track,
    # so only layers listed in EXCLUSIVE_LAYERS must stay sequential.  A v1
    # document has no `layer` on any clip, so every clip lands on "primary" and
    # this is exactly the pre-v2 whole-timeline check.
    previous_end_by_layer: dict[str, float] = {}
    for index, clip in enumerate(clips):
        layer = clip_layer(clip)
        if layer not in EXCLUSIVE_LAYERS:
            continue
        start, end = parse_time_range(clip["time_range"], path=f"clips[{index}].time_range")
        if start + TIMING_TOLERANCE < previous_end_by_layer.get(layer, -1.0):
            _fail(
                "timeline_overlap",
                f"{layer} 层的片段时间线重叠或未按时间排序",
                f"clips[{index}].time_range",
            )
        previous_end_by_layer[layer] = end

    model = str(generation_model or raw.get("generation_model") or "").strip()
    reasoning = str(generation_reasoning or raw.get("generation_reasoning") or "").strip()
    if not model:
        _fail("generation_model_missing", "generation_model 不能为空", "generation_model")
    if not reasoning:
        _fail("generation_reasoning_missing", "generation_reasoning 不能为空", "generation_reasoning")
    if raw.get("source_script_used") is not True:
        _fail("source_script_required", "source_script_used 必须为 true", "source_script_used")

    missing = raw.get("missing_materials") or []
    if not isinstance(missing, list):
        _fail("missing_materials_invalid", "missing_materials 必须是数组", "missing_materials")

    # Document-level v2 sections.  `subtitles` and `audio` carry render settings
    # that apply to the whole cut; per-clip captions stay on the clips.
    extras: dict[str, Any] = {}
    for section in ("audio", "subtitles"):
        value = raw.get(section)
        if value in (None, {}):
            continue
        if not isinstance(value, dict):
            _fail(f"{section}_invalid", f"{section} 必须是对象", section)
        extras[section] = value
    music_raw = raw.get("music")
    if music_raw not in (None, []):
        if not isinstance(music_raw, list):
            _fail("music_invalid", "music 必须是数组", "music")
        extras["music"] = [
            _normalise_music_track(track, index=index)
            for index, track in enumerate(music_raw)
        ]

    uses_v2 = bool(extras) or any(
        field in clip for clip in clips for field in V2_CLIP_FIELDS
    )

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_V2 if uses_v2 else SCHEMA_VERSION,
        "doc_type": DOC_TYPE,
        "source_script_used": True,
        "generation_model": model,
        "generation_reasoning": reasoning,
        "clips": clips,
        "missing_materials": missing,
    }
    result.update(extras)
    for optional in ("project_id", "project_revision", "local_project_path", "notes"):
        value = raw.get(optional)
        if value not in (None, ""):
            result[optional] = value
    return result


def load_and_normalise(
    path: Path,
    *,
    generation_model: str | None = None,
    generation_reasoning: str | None = None,
) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _fail("input_missing", f"文件不存在：{path}")
    except json.JSONDecodeError as exc:
        _fail("invalid_json", f"不是有效 JSON：{exc}")
    return normalise_edl(
        raw,
        generation_model=generation_model,
        generation_reasoning=generation_reasoning,
    )


def write_edl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
