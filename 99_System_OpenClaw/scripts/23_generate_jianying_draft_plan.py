#!/usr/bin/env python3
"""Convert a Content OS EDL into a strict Jianying draft plan."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from jianying_roughcut_common import (
    ContractError,
    is_raw360_media,
    load_json,
    local_project_path_from_assets,
    now_compact,
    parse_time_range,
    resolve_media_candidate,
    write_json,
)


def source_start_from_edl(selected: dict[str, Any], clip: dict[str, Any], required_duration: float) -> float:
    """Use only an EDL-declared source offset; never infer one from an event."""

    raw_start = clip.get("source_start_sec", 0.0)
    try:
        source_start = float(raw_start)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"EDL source_start_sec must be a non-negative number: {raw_start!r}") from exc
    if source_start < 0:
        raise ContractError("EDL source_start_sec must be non-negative")
    source_duration = float(selected.get("source_duration_sec") or selected.get("duration") or 0.0)
    if source_duration > 0 and source_start + required_duration > source_duration + 0.001:
        raise ContractError("EDL source_start_sec and clip duration exceed the selected source media")
    return source_start


def video_track_from_edl(
    edl: dict[str, Any],
    local_project_path: Path,
    *,
    allow_raw360_proxy: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    video_clips: list[dict[str, Any]] = []
    text_clips: list[dict[str, Any]] = []
    clips = edl.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ContractError("EDL must contain non-empty clips list")

    for index, clip in enumerate(clips, start=1):
        if not isinstance(clip, dict):
            raise ContractError(f"EDL clip #{index} must be an object")
        start, end = parse_time_range(str(clip.get("time_range", "")))
        duration = end - start
        selected = resolve_media_candidate(
            local_project_path,
            clip.get("candidate_files") or [],
            duration,
            allow_raw360_proxy=allow_raw360_proxy,
        )
        source_start = source_start_from_edl(selected, clip, duration)
        video_clip = {
            "slot": int(clip.get("slot") or index),
            "timeline_start_sec": start,
            "duration_sec": duration,
            "source_file": selected["path"],
            "source_start_sec": source_start,
            "source_duration_sec": selected["source_duration_sec"],
            "purpose": str(clip.get("purpose", "")),
            "visual_need": str(clip.get("visual_need", "")),
            "edit_note": str(clip.get("edit_note", "")),
            "transform": {
                "scale": 1.0,
                "position": [0, 0],
                "rotation": 0,
            },
        }
        if selected.get("is_raw360"):
            video_clip["source_kind"] = "raw360_reframed_proxy"
            video_clip["source_selection_note"] = "Uses LRF proxy when available; render step crops the right fisheye lens into a vertical roughcut clip."
        if "speed" in selected:
            video_clip["speed"] = selected["speed"]
        video_clips.append(video_clip)

        caption = str(clip.get("caption", "")).strip()
        if caption:
            text_clips.append(
                {
                    "slot": int(clip.get("slot") or index),
                    "timeline_start_sec": start,
                    "duration_sec": duration,
                    "text": caption,
                    "style": {
                        "font_size": 8.0,
                        "color": "#FFFFFF",
                        "bold": True,
                        "position": "bottom_center",
                    },
                }
            )
    return video_clips, text_clips


def generate_plan(
    edl_path: Path,
    local_assets_path: Path,
    output_path: Path,
    draft_name: str | None,
    *,
    allow_raw360_proxy: bool = False,
) -> dict[str, Any]:
    edl = load_json(edl_path)
    raw_local_project_path = str(edl.get("local_project_path") or "").strip()
    if raw_local_project_path:
        local_project_path = Path(raw_local_project_path).expanduser()
    else:
        local_project_path = Path()
    if not raw_local_project_path or not local_project_path.exists():
        local_project_path = local_project_path_from_assets(local_assets_path)

    video_clips, text_clips = video_track_from_edl(edl, local_project_path, allow_raw360_proxy=allow_raw360_proxy)
    end_time = max(float(clip["timeline_start_sec"]) + float(clip["duration_sec"]) for clip in video_clips)
    name = draft_name or f"jy_roughcut_{now_compact()}"
    target_input = edl.get("target") if isinstance(edl.get("target"), dict) else {}
    plan = {
        "spec_version": "content_os_v0.1",
        "doc_type": "jianying_draft_plan",
        "project_id": edl.get("project_id"),
        "idea_id": edl.get("idea_id", ""),
        "draft_name": name,
        "target": {
            "width": int(target_input.get("width") or 1080),
            "height": int(target_input.get("height") or 1920),
            "fps": int(target_input.get("fps") or 30),
            "duration_sec": round(end_time, 3),
            "platform": str(target_input.get("platform") or edl.get("platform") or "unspecified"),
        },
        "source_edl": str(edl_path),
        "local_project_path": str(local_project_path),
        "tracks": [
            {"track_id": "video_main", "type": "video", "clips": video_clips},
            {"track_id": "text_caption", "type": "text", "clips": text_clips},
            {"track_id": "audio_bgm", "type": "audio", "clips": []},
        ],
        "bgm": {
            "source_file": "",
            "timeline_start_sec": 0.0,
            "volume": 0.7,
        },
        "constraints": {
            "no_auto_export": True,
            "human_must_open_check": True,
            "strict_mode": True,
            "raw360_direct_use_allowed": allow_raw360_proxy,
        },
    }
    write_json(output_path, plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edl", required=True, type=Path)
    parser.add_argument("--local-assets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--draft-name")
    parser.add_argument(
        "--allow-raw360-proxy",
        action="store_true",
        help="Experimental only: allow OSV/LRF RawVault proxies. Production runner does not use this.",
    )
    args = parser.parse_args()

    plan = generate_plan(
        args.edl.expanduser().resolve(),
        args.local_assets.expanduser().resolve(),
        args.output.expanduser().resolve(),
        args.draft_name,
        allow_raw360_proxy=args.allow_raw360_proxy,
    )
    print(f"draft_plan={args.output.expanduser().resolve()}")
    print(f"draft_name={plan['draft_name']}")
    print(f"video_clips={len(plan['tracks'][0]['clips'])}")
    print(f"text_clips={len(plan['tracks'][1]['clips'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
