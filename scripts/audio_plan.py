"""Compile canonical EDL audio into a derived, editor-independent mixing plan.

All envelope times are film times. Gain is the product of linear factors,
which preserves simultaneous fades and duck ramps without approximating their
product as a straight line. Renderers must preflight sources before execution.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path
import json
import subprocess
from typing import Any

from edl_contract import AUDIO_CLIP_FIELDS, EDLContractError, normalise_duck_regions, parse_time_range

CUT_FADE_SEC = .030
UNVERIFIED_AUDIO = "这项声音处理尚未核实"


def audio_operations(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Inventory explicit audio requests before an adapter can discard fields."""
    operations = []
    for index, clip in enumerate(document.get("clips", [])):
        if isinstance(clip, dict):
            for key in AUDIO_CLIP_FIELDS:
                if key in clip:
                    operations.append({"path": f"clips[{index}].{key}", "value": clip[key], "message": UNVERIFIED_AUDIO})
    for section in ("audio_beds", "music"):
        if section in document and (section == "audio_beds" or document[section] not in (None, [])):
            operations.append({"path": section, "value": document[section], "message": UNVERIFIED_AUDIO})
    return operations


def reject_audio_request(document: dict[str, Any], *, backend: str) -> None:
    from edit_backends.interface import BackendError
    operations = audio_operations(document)
    if operations:
        paths = ", ".join(item["path"] for item in operations)
        raise BackendError(f"audio_request_unsupported:{backend}:{paths}; 请改用标准剪辑交接或移除音频请求")


def probe_audio_source(path: Path) -> dict[str, Any]:
    """Read bounded probe facts; unreadable media is never reported as silent."""
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                                capture_output=True, text=True, check=True, timeout=30)
        probe = json.loads(result.stdout)
        audio = next((s for s in probe["streams"] if s.get("codec_type") == "audio"), None)
        duration = float((audio or {}).get("duration") or probe.get("format", {}).get("duration", 0))
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("invalid duration")
        return {"has_audio": audio is not None, "duration_sec": duration}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise EDLContractError("audio_probe_failed", "声音素材探测失败；请确认素材可读后重新生成", str(path)) from exc


def _source_facts(source_info: dict[str, dict[str, Any]], source: str) -> dict[str, Any]:
    info = source_info.get(source)
    if not isinstance(info, dict) or not isinstance(info.get("duration_sec"), (int, float)) or isinstance(info["duration_sec"], bool) or not math.isfinite(info["duration_sec"]) or info["duration_sec"] <= 0:
        _fail("audio_source_info_required", "缺少可信素材时长；请重新探测素材", source)
    if not isinstance(info.get("has_audio"), bool):
        _fail("audio_source_info_required", "音轨状态未核实；请重新探测素材", source)
    return info


def _fail(code: str, message: str, path: str) -> None:
    raise EDLContractError(code, message, path)


def _factor_value(points: list[list[float]], time: float) -> float:
    if time < points[0][0]:
        return points[0][1]
    for (a, x), (b, y) in zip(points, points[1:]):
        if time < b:
            return y if b == a else x + (y - x) * (time - a) / (b - a)
    return points[-1][1]


def gain_at(segment: dict[str, Any], time: float) -> float:
    if time < segment["timeline_start_sec"] or time > segment["timeline_end_sec"]:
        return 0.0
    return math.prod(_factor_value(factor["points"], time) for factor in segment["gain_envelope"]["factors"])


def _segment(*, identity, kind, source, start, end, source_start, volume, fade_in, fade_out, ducks, slot=None):
    duration = end - start
    if duration <= 0 or start < 0:
        _fail("audio_range_invalid", "声音区间必须为有限正时长并位于影片内", identity)
    for fade in (fade_in, fade_out):
        if fade > duration / 2 + 1e-6:
            _fail("audio_fade_invalid", "淡变不能超过声音区间的一半", identity)
    # Even an authored zero retains the minimum de-click fade at a true cut.
    fade_in = max(min(CUT_FADE_SEC, duration / 2), fade_in)
    fade_out = max(min(CUT_FADE_SEC, duration / 2), fade_out)
    factors = [{"kind": "base_and_fade", "points": [[start, 0], [start + fade_in, volume], [end - fade_out, volume], [end, 0]]}]
    for region in ducks:
        a, b, ramp, gain = (region[k] for k in ("start_sec", "end_sec", "ramp_sec", "gain"))
        if a - ramp < start - 1e-6 or b + ramp > end + 1e-6:
            _fail("audio_duck_invalid", "压低区间及过渡必须位于这首歌内", identity)
        factors.append({"kind": "duck", "points": [[a - ramp, 1], [a, gain], [b, gain], [b + ramp, 1]]})
    segment = {"id": identity, "kind": kind, "source": source,
               "timeline_start_sec": start, "timeline_end_sec": end,
               "source_start_sec": source_start, "source_end_sec": source_start + duration,
               "volume": volume, "fade_in_sec": fade_in, "fade_out_sec": fade_out,
               "duck_regions": copy.deepcopy(ducks),
               "gain_envelope": {"interpolation": "product_of_linear_factors", "factors": factors}}
    if slot is not None:
        segment["slot"] = slot
    return segment


def compile_audio_plan(edl: dict[str, Any], *, source_info: dict[str, dict[str, Any]] | None = None,
                       speech_regions: list[dict[str, float]] | None = None) -> dict[str, Any]:
    """Compile normalized EDL; optional trusted probe facts enable source preflight.

    source_info maps the chosen source to duration_sec and has_audio. A plan
    marked pending is useful for inspection, but is not ready for rendering.
    Legacy duck_to is an absolute level and needs explicit trusted speech spans;
    new duck gains are relative to the song's base volume and take precedence.
    """
    clips = edl["clips"]
    duration = max(parse_time_range(c["time_range"])[1] for c in clips)
    if audio_operations(edl) and any(c.get("speed", 1) != 1 for c in clips):
        _fail("audio_speed_unsupported", "新音频处理只支持 speed=1", "clips")
    segments = []
    muted = []
    for clip in clips:
        slot = clip["slot"]
        if clip.get("audio_mute"):
            muted.append(slot)
            continue
        source = clip.get("source_file") or clip["candidate_files"][0]
        if source_info is not None and _source_facts(source_info, source)["has_audio"] is False:
            if any(k in clip for k in AUDIO_CLIP_FIELDS):
                _fail("audio_stream_missing", "请求处理的原片没有音轨；请更换素材或静音", f"clip:{slot}")
            continue
        start, end = parse_time_range(clip["time_range"])
        speed = clip.get("speed", 1)
        if speed != 1:
            _fail("audio_speed_unsupported", "声音计划只支持 speed=1", f"clip:{slot}")
        lead, tail = clip.get("audio_lead_sec", 0), clip.get("audio_tail_sec", 0)
        segments.append(_segment(identity=f"clip:{slot}", kind="clip", slot=slot, source=source,
                                 start=start - lead, end=end + tail, source_start=clip["source_start_sec"] - lead,
                                 volume=clip.get("volume", 1), fade_in=clip.get("audio_fade_in_sec", 0),
                                 fade_out=clip.get("audio_fade_out_sec", 0), ducks=[]))
    for section, kind in (("audio_beds", "bed"), ("music", "music")):
        for index, track in enumerate(edl.get(section, [])):
            identity = f"{kind}:{index}"
            start, end = track["timeline_start_sec"], track.get("timeline_end_sec", duration)
            if end > duration + 1e-6:
                _fail("audio_range_invalid", "声音终点超出影片；请修正时间码", identity)
            volume = track.get("volume", 1)
            ducks = copy.deepcopy(track.get("duck_regions", []))
            if "duck_regions" not in track and "duck_to" in track:
                if speech_regions is None:
                    _fail("audio_speech_regions_required", "旧 duck_to 缺可信说话区间；请提供区间或改写 duck_regions", identity)
                ducks = normalise_duck_regions([dict(r, gain=1) for r in speech_regions], path="speech_regions")
                for region in ducks:
                    # Preserve the legacy absolute level, including zero base gain.
                    region["gain"] = min(1, track["duck_to"] / volume) if volume else 0
            segment = _segment(identity=identity, kind=kind, source=track["source"], start=start, end=end,
                               source_start=track.get("source_start_sec", 0), volume=volume,
                               fade_in=track.get("fade_in_sec", 0), fade_out=track.get("fade_out_sec", 0), ducks=ducks)
            if track.get("loop"):
                if source_info is None or track["source"] not in source_info:
                    _fail("audio_source_info_required", "循环配乐需要可信的素材时长；请先探测素材", identity)
                native = _source_facts(source_info, track["source"])["duration_sec"]
                available = native - segment["source_start_sec"]
                if available <= 0:
                    _fail("audio_source_range", "配乐入点超出素材；请修正入点", identity)
                cursor = start
                repeat = 0
                while cursor < end - 1e-9:
                    part = copy.deepcopy(segment)
                    part_end = min(end, cursor + available)
                    part.update(id=f"{identity}:loop:{repeat}", timeline_start_sec=cursor, timeline_end_sec=part_end,
                                source_end_sec=segment["source_start_sec"] + part_end - cursor)
                    # Song fades and duck timing remain on the whole song;
                    # source jumps are real sound cuts and need de-click fades.
                    cut_factors = []
                    edge = min(CUT_FADE_SEC, (part_end - cursor) / 2)
                    if cursor > start:
                        cut_factors.append({"kind": "loop_cut_in", "points": [[cursor, 0], [cursor + edge, 1]]})
                    if part_end < end:
                        cut_factors.append({"kind": "loop_cut_out", "points": [[part_end - edge, 1], [part_end, 0]]})
                    part["gain_envelope"]["factors"].extend(cut_factors)
                    segments.append(part)
                    cursor, repeat = part_end, repeat + 1
            else:
                segments.append(segment)
    if source_info is not None:
        for segment in segments:
            source = segment["source"]
            info = _source_facts(source_info, source)
            if info.get("has_audio") is not True:
                _fail("audio_stream_missing", "请求使用的素材没有音轨；请更换素材", source)
            if segment["source_start_sec"] < -1e-6 or segment["source_end_sec"] > info["duration_sec"] + 1e-6:
                _fail("audio_source_range", "原片的声音余量不足；请缩短声音或更换素材", segment["id"])
    # Allocate the first free physical audio lane, including all crossfades and
    # J/L overlaps. Touching intervals can safely reuse a lane.
    occupied_until = []
    for segment in sorted(segments, key=lambda s: (s["timeline_start_sec"], s["id"])):
        lane = next((i for i, end in enumerate(occupied_until) if end <= segment["timeline_start_sec"] + 1e-9), len(occupied_until))
        if lane == len(occupied_until):
            occupied_until.append(0)
        occupied_until[lane] = segment["timeline_end_sec"]
        segment["physical_track"] = lane
    return {"schema_version": "audio_plan_v1", "authority": "derived_from_edl", "duration_sec": duration,
            "source_validation": "passed" if source_info is not None else "pending",
            "muted_slots": muted, "segments": segments, "physical_track_count": len(occupied_until)}
