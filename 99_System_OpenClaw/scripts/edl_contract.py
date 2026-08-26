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
DOC_TYPE = "edit_decision_list"
TIMING_TOLERANCE = 0.000_001
REQUIRED_CLIP_TEXT_FIELDS = ("purpose", "visual_need", "caption", "edit_note")


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
    for optional in ("transition", "audio_note", "evidence_refs"):
        value = raw.get(optional)
        if value not in (None, "", []):
            normalised[optional] = value
    return normalised


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

    previous_end = -1.0
    for index, clip in enumerate(clips):
        start, end = parse_time_range(clip["time_range"], path=f"clips[{index}].time_range")
        if start + TIMING_TOLERANCE < previous_end:
            _fail("timeline_overlap", "片段时间线重叠或未按时间排序", f"clips[{index}].time_range")
        previous_end = end

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

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "doc_type": DOC_TYPE,
        "source_script_used": True,
        "generation_model": model,
        "generation_reasoning": reasoning,
        "clips": clips,
        "missing_materials": missing,
    }
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
