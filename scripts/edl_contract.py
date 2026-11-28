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

if __package__:
    from .constants import (
        EDL_CONTRACT_SCHEMA_VERSION as SCHEMA_VERSION,
        SCHEMA_VERSION_V2,
        DOC_TYPE,
        TIMING_TOLERANCE,
        REQUIRED_CLIP_TEXT_FIELDS,
        CLIP_ROLES,
        CLIP_LAYERS,
        DEFAULT_CLIP_LAYER,
        EXCLUSIVE_LAYERS,
        CROP_KEYS,
        AUDIO_CLIP_FIELDS,
        V2_CLIP_FIELDS,
        V2_DOCUMENT_FIELDS,
    )
else:
    from constants import (
        EDL_CONTRACT_SCHEMA_VERSION as SCHEMA_VERSION,
        SCHEMA_VERSION_V2,
        DOC_TYPE,
        TIMING_TOLERANCE,
        REQUIRED_CLIP_TEXT_FIELDS,
        CLIP_ROLES,
        CLIP_LAYERS,
        DEFAULT_CLIP_LAYER,
        EXCLUSIVE_LAYERS,
        CROP_KEYS,
        AUDIO_CLIP_FIELDS,
        V2_CLIP_FIELDS,
        V2_DOCUMENT_FIELDS,
    )

# v2 vocabulary.  `role` is the narrative job a clip performs; `layer` is where
# it sits in the composition stack.  The two are deliberately orthogonal: a
# full-screen B-roll cutaway is role="b_roll" on layer="primary", while the same
# footage as a picture-in-picture insert is role="b_roll" on layer="overlay".

# Only the primary layer carries the "one thing on screen at a time" rule.
# Overlay and background clips are expected to sit on top of, or behind, it.



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


def _required_text(clip: dict[str, Any], field: str, *, path: str, allow_empty: bool = False) -> str:
    value = clip.get(field)
    if field == "caption" and not value:
        value = clip.get("subtitle")
    text = str(value or "").strip()
    if not text and not allow_empty:
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
    if "duck_regions" in raw:
        track["duck_regions"] = normalise_duck_regions(raw["duck_regions"], path=f"{path}.duck_regions")
    return track


def normalise_duck_regions(raw: Any, *, path: str) -> list[dict[str, float]]:
    if not isinstance(raw, list):
        _fail("audio_duck_invalid", "压低区间必须是数组", path)
    regions = []
    previous_end = -1.0
    for index, item in enumerate(raw):
        location = f"{path}[{index}]"
        if not isinstance(item, dict):
            _fail("audio_duck_invalid", "压低区间必须是对象", location)
        region = {key: parse_seconds(item.get(key), path=f"{location}.{key}")
                  for key in ("start_sec", "end_sec", "ramp_sec")}
        gain = _optional_number(item, "gain", path=location, minimum=0, maximum=1)
        if gain is None:
            _fail("audio_duck_invalid", "压低区间必须提供 gain", location)
        region["gain"] = gain
        start, end, ramp = (region[k] for k in ("start_sec", "end_sec", "ramp_sec"))
        if end <= start or start - ramp < previous_end - TIMING_TOLERANCE:
            _fail("audio_duck_invalid", "压低区间须顺序排列，含过渡的区间不能重叠；请合并后重试", location)
        previous_end = end + ramp
        regions.append(region)
    return regions


def _normalise_audio_bed(raw: Any, *, index: int) -> dict[str, Any]:
    path = f"audio_beds[{index}]"
    if not isinstance(raw, dict) or not isinstance(raw.get("source"), str) or not raw["source"].strip():
        _fail("audio_bed_invalid", "铺底声必须指定 source", path)
    bed: dict[str, Any] = {"source": raw["source"].strip()}
    for key in ("source_start_sec", "timeline_start_sec", "timeline_end_sec"):
        bed[key] = parse_seconds(raw.get(key), path=f"{path}.{key}")
    for key in ("fade_in_sec", "fade_out_sec"):
        if key in raw:
            bed[key] = parse_seconds(raw[key], path=f"{path}.{key}")
    if "volume" in raw:
        value = _optional_number(raw, "volume", path=path, minimum=0, maximum=2)
        if value is None:
            _fail("audio_bed_invalid", "volume 不能是 null", path)
        bed["volume"] = value
    note = _optional_text(raw, "note", path=path)
    if note is not None:
        bed["note"] = note
    return bed


def validate_audio_layout(clips: list[dict[str, Any]], extras: dict[str, Any], *, new_audio: bool) -> None:
    """Check authored timing without reading local media; source tails need preflight."""
    duration = max(parse_time_range(c["time_range"])[1] for c in clips)
    primary = [c for c in clips if clip_layer(c) == "primary"]
    for clip in clips:
        path = f"clip:{clip['slot']}"
        if new_audio and clip.get("speed", 1) != 1:
            _fail("audio_speed_unsupported", "新音频处理只支持 speed=1；请移除变速或音频请求", path)
        if not any(k in clip for k in AUDIO_CLIP_FIELDS):
            continue
        start, end = parse_time_range(clip["time_range"])
        lead, tail = clip.get("audio_lead_sec", 0), clip.get("audio_tail_sec", 0)
        if lead or tail:
            if clip_layer(clip) != "primary":
                _fail("audio_handle_invalid", "声音早进晚出只支持主轴相邻镜头", path)
            index = primary.index(clip)
            for amount, neighbor_index, boundary in ((lead, index - 1, start), (tail, index + 1, end)):
                if not amount:
                    continue
                if neighbor_index < 0 or neighbor_index >= len(primary):
                    _fail("audio_handle_invalid", "声音延伸需要相邻镜头", path)
                ns, ne = parse_time_range(primary[neighbor_index]["time_range"])
                expected = ne if neighbor_index < index else ns
                if abs(expected - boundary) > TIMING_TOLERANCE or amount > ne - ns + TIMING_TOLERANCE:
                    _fail("audio_handle_invalid", "声音延伸不能超过连续相邻镜头的时长", path)
        if clip["source_start_sec"] < lead - TIMING_TOLERANCE:
            _fail("audio_handle_invalid", "原片向前的声音余量不足", path)
        for key in ("audio_fade_in_sec", "audio_fade_out_sec"):
            if clip.get(key, 0) > (end - start + lead + tail) / 2 + TIMING_TOLERANCE:
                _fail("audio_fade_invalid", "淡变不能超过声音区间的一半", f"{path}.{key}")
    for section in ("audio_beds", "music"):
        for index, track in enumerate(extras.get(section, [])):
            path = f"{section}[{index}]"
            start, end = track["timeline_start_sec"], track.get("timeline_end_sec", duration)
            # Legacy music normalization is deliberately unchanged. Execution
            # validates its bounds too, without rounding old high precision.
            if section == "audio_beds" or "duck_regions" in track:
                if end <= start or end > duration + TIMING_TOLERANCE:
                    _fail("audio_range_invalid", "声音区间须位于影片内且终点晚于起点", path)
                for key in ("fade_in_sec", "fade_out_sec"):
                    if track.get(key, 0) > (end - start) / 2 + TIMING_TOLERANCE:
                        _fail("audio_fade_invalid", "淡变不能超过声音区间的一半", path)
            for region in track.get("duck_regions", []):
                if region["start_sec"] - region["ramp_sec"] < start - TIMING_TOLERANCE or region["end_sec"] + region["ramp_sec"] > end + TIMING_TOLERANCE:
                    _fail("audio_duck_invalid", "压低区间及过渡必须位于这首歌内", path)


def normalise_clip(raw: Any, *, index: int, allow_empty_caption: bool = False) -> dict[str, Any]:
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
        "caption": _required_text(raw, "caption", path=path, allow_empty=allow_empty_caption),
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

    for field in AUDIO_CLIP_FIELDS:
        if field not in raw:
            continue
        if field == "audio_mute":
            if not isinstance(raw[field], bool):
                _fail("audio_mute_invalid", "audio_mute 必须是布尔值", f"{path}.{field}")
            normalised[field] = raw[field]
        else:
            normalised[field] = parse_seconds(raw[field], path=f"{path}.{field}")

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


def layers_used(edl: dict[str, Any]) -> list[str]:
    """Distinct composition layers present in an EDL, in stack order.

    A v1 document always returns ["primary"].
    """
    present = {clip_layer(clip) for clip in edl.get("clips") or [] if isinstance(clip, dict)}
    return [layer for layer in CLIP_LAYERS if layer in present]


def require_flat_timeline(edl: dict[str, Any], *, backend: str) -> None:
    """Guard for backends that can only render one video track.

    Flattening a layered cut onto a single track silently produces the wrong
    video -- an overlay would be concatenated inline instead of composited on
    top -- so single-track backends must refuse the document instead.
    """
    extra = [layer for layer in layers_used(edl) if layer != DEFAULT_CLIP_LAYER]
    if extra:
        _fail(
            "layered_timeline_unsupported",
            f"{backend} 只支持单轨时间线，无法渲染 {'、'.join(extra)} 层；"
            f"请改用支持多轨的后端（otio_kdenlive），或先把叠加层压成主轴素材",
            "clips",
        )




def _normalise_provenance(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw["provenance"]
    required = ("kind", "planner", "planner_version", "preset_id", "input_digest")
    allowed = (*required, "preset_name")
    if not isinstance(value, dict) or set(value) - set(allowed):
        _fail("provenance_invalid", "provenance 必须是来源声明对象，且不能包含未知字段", "provenance")
    for field in required:
        if not isinstance(value.get(field), str) or not value[field].strip():
            _fail("provenance_invalid", f"{field} 必须是非空文本", f"provenance.{field}")
    if value["kind"] != "media_first_planner":
        _fail("provenance_invalid", "kind 只支持 media_first_planner", "provenance.kind")
    if re.fullmatch(r"[0-9a-fA-F]{64}", value["input_digest"]) is None:
        _fail("provenance_invalid", "input_digest 必须是 64 位十六进制", "provenance.input_digest")
    if "preset_name" in value and (not isinstance(value["preset_name"], str) or not value["preset_name"].strip()):
        _fail("provenance_invalid", "preset_name 必须是非空文本", "provenance.preset_name")
    if raw.get("source_script_used") is not False:
        _fail("provenance_script_conflict", "媒体优先编排必须明确声明 source_script_used=false", "source_script_used")
    return {field: value[field] for field in allowed if field in value}


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

    provenance = _normalise_provenance(raw) if "provenance" in raw else None
    clips = [normalise_clip(clip, index=index, allow_empty_caption=provenance is not None)
             for index, clip in enumerate(clips_raw)]
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
    if provenance is not None:
        origin: dict[str, Any] = {"source_script_used": False, "provenance": provenance}
        for field, override in (("generation_model", generation_model), ("generation_reasoning", generation_reasoning)):
            if field in raw or override is not None:
                value = override if override is not None else raw[field]
                if not isinstance(value, str) or not value.strip():
                    _fail(f"{field}_invalid", f"{field} 若提供就必须是非空文本", field)
                origin[field] = value.strip()
    else:
        if not model:
            _fail("generation_model_missing", "generation_model 不能为空", "generation_model")
        if not reasoning:
            _fail("generation_reasoning_missing", "generation_reasoning 不能为空", "generation_reasoning")
        if raw.get("source_script_used") is not True:
            _fail("source_script_required", "source_script_used 必须为 true", "source_script_used")
        origin = {"source_script_used": True, "generation_model": model, "generation_reasoning": reasoning}

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
        if section == "audio" and "tracks" in value:
            _fail("audio_tracks_invalid", "audio 只放全片设置，轨道请写 audio_beds 或 music", section)
        extras[section] = value
    music_raw = raw.get("music")
    if music_raw not in (None, []):
        if not isinstance(music_raw, list):
            _fail("music_invalid", "music 必须是数组", "music")
        extras["music"] = [
            _normalise_music_track(track, index=index)
            for index, track in enumerate(music_raw)
        ]
    if "audio_beds" in raw:
        if not isinstance(raw["audio_beds"], list):
            _fail("audio_bed_invalid", "audio_beds 必须是数组", "audio_beds")
        extras["audio_beds"] = [_normalise_audio_bed(bed, index=i) for i, bed in enumerate(raw["audio_beds"])]
    new_audio = "audio_beds" in raw or any(k in c for c in clips for k in AUDIO_CLIP_FIELDS) or any("duck_regions" in m for m in extras.get("music", []))
    validate_audio_layout(clips, extras, new_audio=new_audio)

    uses_v2 = bool(extras) or any(
        field in clip for clip in clips for field in V2_CLIP_FIELDS
    )

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION_V2 if uses_v2 else SCHEMA_VERSION,
        "doc_type": DOC_TYPE,
        **origin,
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
