#!/usr/bin/env python3
"""Create a Jianying roughcut draft directory from a strict draft plan."""

from __future__ import annotations

import argparse
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

import pyJianYingDraft as jy

from edl_contract import EDLContractError
from edl_contract import parse_seconds as canonical_parse_seconds
from jianying_roughcut_common import ContractError, ensure_dir, load_json, write_yaml

SEC = 1_000_000


def track_by_id(plan: dict[str, Any], track_id: str) -> dict[str, Any]:
    tracks = plan.get("tracks")
    if not isinstance(tracks, list):
        raise ContractError("plan.tracks must be a list")
    for track in tracks:
        if isinstance(track, dict) and track.get("track_id") == track_id:
            return track
    raise ContractError(f"track not found in plan: {track_id}")


def seconds(value: Any) -> int:
    """Validate a non-negative, finite seconds value and convert to microseconds.

    Reuses edl_contract.parse_seconds for the float/finite/non-negative
    validation shared with the rest of the EDL pipeline. Unlike a timeline
    position authored by a human or an AI (which edl_contract requires to be
    millisecond-precise), the values that pass through this helper include
    raw ffprobe-measured source media durations, which are never
    millisecond-aligned by construction. So a value that only fails the
    millisecond-precision check is rounded to milliseconds and revalidated
    instead of being rejected outright.
    """
    try:
        validated = canonical_parse_seconds(value, path="time_value")
    except EDLContractError as exc:
        if exc.code == "timing_precision":
            validated = canonical_parse_seconds(round(float(value), 3), path="time_value")
        else:
            raise ContractError(f"invalid time value: {value!r}: {exc}") from exc
    return int(round(validated * SEC))


def media_copy_name(index: int, source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".jpg", ".jpeg", ".png"}:
        raise ContractError(f"unsupported Jianying bundled media type: {source}")
    return f"media_{index:03d}{suffix}"


def rewrite_content_media_paths(content_path: Path, original_to_bundled: dict[str, str], placeholder: str) -> int:
    if not content_path.exists():
        return 0
    data = json.loads(content_path.read_text(encoding="utf-8"))
    materials = data.get("materials", {})
    videos = materials.get("videos", []) if isinstance(materials, dict) else []
    updated = 0
    for item in videos:
        if not isinstance(item, dict):
            continue
        original_path = str(item.get("media_path") or item.get("path") or "")
        bundled_path = original_to_bundled.get(original_path)
        if not bundled_path:
            continue
        item["media_path"] = original_path
        item["path"] = f"{placeholder}/{bundled_path}"
        item["source"] = 0
        item["source_platform"] = 0
        item["check_flag"] = 125892607
        updated += 1
    content_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    return updated


def normalize_video_render_fields(content_path: Path) -> int:
    """Add Mac Jianying render defaults required for visible video playback."""
    if not content_path.exists():
        return 0
    data = json.loads(content_path.read_text(encoding="utf-8"))
    tracks = data.get("tracks", [])
    if not isinstance(tracks, list):
        raise ContractError(f"draft_content.tracks must be a list: {content_path}")

    updated = 0
    for track_index, track in enumerate(tracks):
        if not isinstance(track, dict) or track.get("type") != "video":
            continue
        track["name"] = ""
        track.setdefault("attribute", 0)
        track.setdefault("flag", 0)
        track["is_default_name"] = True
        for segment in track.get("segments") or []:
            if not isinstance(segment, dict):
                continue
            segment.setdefault("common_keyframes", [])
            segment.setdefault("keyframe_refs", [])
            segment.setdefault("enable_adjust", True)
            segment.setdefault("enable_color_correct_adjust", False)
            segment.setdefault("enable_color_curves", True)
            segment.setdefault("enable_color_match_adjust", False)
            segment.setdefault("enable_color_wheels", True)
            segment.setdefault("enable_lut", True)
            segment.setdefault("enable_smart_color_adjust", False)
            segment.setdefault("enable_video_mask", True)
            segment.setdefault("last_nonzero_volume", 1.0)
            segment.setdefault("reverse", False)
            segment.setdefault("track_attribute", 0)
            segment.setdefault("track_render_index", 0)
            segment.setdefault("render_index", track_index)
            segment.setdefault("visible", True)
            segment.setdefault("speed", 1.0)
            segment.setdefault("volume", 1.0)
            segment.setdefault("state", 0)
            segment.setdefault("is_placeholder", False)
            segment.setdefault("is_loop", False)
            segment.setdefault("is_tone_modify", False)
            segment.setdefault("raw_segment_id", "")
            segment.setdefault("group_id", "")
            segment.setdefault("template_id", "")
            segment.setdefault("template_scene", "default")
            segment.setdefault("caption_info", None)
            segment.setdefault("cartoon", False)
            segment.setdefault("lyric_keyframes", None)
            segment.setdefault("digital_human_template_group_id", "")
            render_timerange = segment.setdefault("render_timerange", {})
            if isinstance(render_timerange, dict):
                render_timerange.setdefault("start", 0)
                render_timerange.setdefault("duration", 0)
            for key in ("source_timerange", "target_timerange"):
                timerange = segment.setdefault(key, {})
                if isinstance(timerange, dict):
                    timerange.setdefault("start", 0)
                    timerange.setdefault("duration", 0)
            clip = segment.setdefault("clip", {})
            if isinstance(clip, dict):
                clip.setdefault("alpha", 1.0)
                clip.setdefault("rotation", 0.0)
                flip = clip.setdefault("flip", {})
                if isinstance(flip, dict):
                    flip.setdefault("horizontal", False)
                    flip.setdefault("vertical", False)
                scale = clip.setdefault("scale", {})
                if isinstance(scale, dict):
                    scale.setdefault("x", 1.0)
                    scale.setdefault("y", 1.0)
                transform = clip.setdefault("transform", {})
                if isinstance(transform, dict):
                    transform.setdefault("x", 0.0)
                    transform.setdefault("y", 0.0)
            uniform_scale = segment.setdefault("uniform_scale", {})
            if isinstance(uniform_scale, dict):
                uniform_scale.setdefault("on", True)
                uniform_scale.setdefault("value", 1.0)
            hdr_settings = segment.setdefault("hdr_settings", {})
            if isinstance(hdr_settings, dict):
                hdr_settings.setdefault("intensity", 1.0)
                hdr_settings.setdefault("mode", 1)
                hdr_settings.setdefault("nits", 1000)
            responsive_layout = segment.setdefault("responsive_layout", {})
            if isinstance(responsive_layout, dict):
                responsive_layout.setdefault("enable", False)
                responsive_layout.setdefault("horizontal_pos_layout", 0)
                responsive_layout.setdefault("size_layout", 0)
                responsive_layout.setdefault("target_follow", "")
                responsive_layout.setdefault("vertical_pos_layout", 0)
            updated += 1

    content_path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    return updated


def update_meta_materials(draft_dir: Path, content_path: Path, original_to_bundled: dict[str, str]) -> None:
    meta_path = draft_dir / "draft_meta_info.json"
    if not meta_path.exists():
        return
    content = json.loads(content_path.read_text(encoding="utf-8"))
    videos = content.get("materials", {}).get("videos", [])
    now = int(time.time())
    values: list[dict[str, Any]] = []
    for item in videos:
        if not isinstance(item, dict):
            continue
        original_path = str(item.get("media_path") or "")
        bundled_path = original_to_bundled.get(original_path)
        if not bundled_path:
            continue
        values.append(
            {
                "create_time": 0,
                "duration": int(item.get("duration") or 0),
                "extra_info": "",
                "file_Path": f"./{bundled_path}",
                "height": int(item.get("height") or 0),
                "id": str(item.get("id") or item.get("material_id") or uuid.uuid4()).upper(),
                "import_time": now,
                "import_time_ms": -1,
                "item_source": 1,
                "md5": "",
                "metetype": "photo" if item.get("type") == "photo" else "video",
                "roughcut_time_range": {"duration": -1, "start": -1},
                "sub_time_range": {"duration": -1, "start": -1},
                "type": 0,
                "width": int(item.get("width") or 0),
            }
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    draft_materials = meta.get("draft_materials")
    if isinstance(draft_materials, list):
        target = next((entry for entry in draft_materials if isinstance(entry, dict) and entry.get("type") == 0), None)
        if target is None:
            target = {"type": 0, "value": []}
            draft_materials.insert(0, target)
        target["value"] = values
    meta["draft_materials_copied_info"] = []
    meta["draft_timeline_materials_size_"] = content_path.stat().st_size
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=4), encoding="utf-8")


def bundle_video_media(draft_dir: Path, plan: dict[str, Any]) -> dict[str, Any]:
    video_dir = draft_dir / "video"
    video_dir.mkdir(parents=True, exist_ok=True)
    placeholder = f"##_draftpath_placeholder_{str(uuid.uuid4()).upper()}_##"
    original_to_bundled: dict[str, str] = {}

    for index, clip in enumerate(track_by_id(plan, "video_main").get("clips", []), start=1):
        if not isinstance(clip, dict):
            raise ContractError("video clip entries must be objects")
        source = Path(str(clip.get("source_file", ""))).expanduser().resolve()
        if not source.exists():
            raise ContractError(f"source media does not exist: {source}")
        if str(source) in original_to_bundled:
            continue
        copy_name = media_copy_name(index, source)
        target = video_dir / copy_name
        shutil.copy2(source, target)
        original_to_bundled[str(source)] = f"video/{copy_name}"

    root_content = draft_dir / "draft_content.json"
    rewritten_files = 0
    rewritten_materials = 0
    normalized_video_segments = 0
    for content_path in draft_dir.rglob("draft_content.json"):
        rewritten = rewrite_content_media_paths(content_path, original_to_bundled, placeholder)
        normalized_video_segments += normalize_video_render_fields(content_path)
        if rewritten:
            rewritten_files += 1
            rewritten_materials += rewritten
    update_meta_materials(draft_dir, root_content, original_to_bundled)
    return {
        "media_bundled_into_draft": True,
        "bundled_media_count": len(original_to_bundled),
        "rewritten_draft_content_files": rewritten_files,
        "rewritten_media_references": rewritten_materials,
        "normalized_video_segments": normalized_video_segments,
    }


def create_draft(plan_path: Path, draft_root: Path, result_output: Path | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    if plan.get("doc_type") != "jianying_draft_plan":
        raise ContractError("plan.doc_type must be jianying_draft_plan")
    if not plan.get("constraints", {}).get("strict_mode"):
        raise ContractError("plan.constraints.strict_mode must be true")

    target = plan.get("target")
    if not isinstance(target, dict):
        raise ContractError("plan.target must be an object")

    draft_name = str(plan.get("draft_name") or "").strip()
    if not draft_name:
        raise ContractError("plan.draft_name is required")

    draft_root = ensure_dir(draft_root)
    folder = jy.DraftFolder(str(draft_root))
    script = folder.create_draft(
        draft_name,
        int(target["width"]),
        int(target["height"]),
        fps=int(target["fps"]),
        allow_replace=False,
    )
    script.add_track(jy.TrackType.video)
    script.add_track(jy.TrackType.text, "text_caption")

    material_cache: dict[str, Any] = {}
    for clip in track_by_id(plan, "video_main").get("clips", []):
        if not isinstance(clip, dict):
            raise ContractError("video clip entries must be objects")
        source = Path(str(clip.get("source_file", ""))).expanduser().resolve()
        if not source.exists():
            raise ContractError(f"source media does not exist: {source}")
        source_key = str(source)
        if source_key not in material_cache:
            material_cache[source_key] = jy.VideoMaterial(source_key)
            script.add_material(material_cache[source_key])
        target_range = jy.Timerange(seconds(clip["timeline_start_sec"]), seconds(clip["duration_sec"]))
        source_range = jy.Timerange(seconds(clip.get("source_start_sec", 0.0)), seconds(clip.get("source_duration_sec", clip["duration_sec"])))
        segment_kwargs: dict[str, Any] = {"source_timerange": source_range}
        if "speed" in clip:
            segment_kwargs["speed"] = float(clip["speed"])
        segment = jy.VideoSegment(material_cache[source_key], target_range, **segment_kwargs)
        script.add_segment(segment)

    text_style = jy.TextStyle(size=8.0, bold=True, color=(1.0, 1.0, 1.0), align=1, auto_wrapping=True)
    text_border = jy.TextBorder(width=35.0)
    text_settings = jy.ClipSettings(transform_y=-0.76)
    for clip in track_by_id(plan, "text_caption").get("clips", []):
        if not isinstance(clip, dict):
            raise ContractError("text clip entries must be objects")
        text = str(clip.get("text", "")).strip()
        if not text:
            continue
        segment = jy.TextSegment(
            text,
            jy.Timerange(seconds(clip["timeline_start_sec"]), seconds(clip["duration_sec"])),
            style=text_style,
            border=text_border,
            clip_settings=text_settings,
        )
        script.add_segment(segment, "text_caption")

    audio_track = track_by_id(plan, "audio_bgm")
    audio_clips = audio_track.get("clips") or []
    if audio_clips:
        script.add_track(jy.TrackType.audio, "audio_bgm")
        for clip in audio_clips:
            if not isinstance(clip, dict):
                raise ContractError("audio clip entries must be objects")
            source = Path(str(clip.get("source_file", ""))).expanduser().resolve()
            if not source.exists():
                raise ContractError(f"audio source does not exist: {source}")
            material = jy.AudioMaterial(str(source))
            script.add_material(material)
            source_range = jy.Timerange(seconds(clip.get("source_start_sec", 0.0)), seconds(clip.get("source_duration_sec", clip["duration_sec"])))
            segment = jy.AudioSegment(
                material,
                jy.Timerange(seconds(clip["timeline_start_sec"]), seconds(clip["duration_sec"])),
                source_timerange=source_range,
                volume=float(clip.get("volume", 0.7)),
            )
            script.add_segment(segment, "audio_bgm")

    draft_dir = draft_root / draft_name
    script.save()
    bundle_result = bundle_video_media(draft_dir, plan)
    result = {
        "spec_version": "content_os_v0.1",
        "doc_type": "jianying_draft_result",
        "status": "done",
        "project_id": plan.get("project_id"),
        "idea_id": plan.get("idea_id", ""),
        "source_plan": str(plan_path),
        "draft_name": draft_name,
        "draft_dir": str(draft_dir),
        "draft_content": str(draft_dir / "draft_content.json"),
        "draft_meta_info": str(draft_dir / "draft_meta_info.json"),
        "jianying_draft_root": str(draft_root),
        "jianying_installed_draft_dir": str(draft_dir),
        **bundle_result,
        "validation_required": True,
        "human_open_check_required": True,
        "no_auto_export": True,
        "tools_used": {
            "pyJianYingDraft": "0.2.6",
        },
    }
    if result_output:
        write_yaml(result_output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--draft-root", required=True, type=Path)
    parser.add_argument("--result-output", type=Path)
    args = parser.parse_args()

    result = create_draft(
        args.plan.expanduser().resolve(),
        args.draft_root.expanduser().resolve(),
        args.result_output.expanduser().resolve() if args.result_output else None,
    )
    print(f"draft_dir={result['draft_dir']}")
    print(f"draft_content={result['draft_content']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
