#!/usr/bin/env python3
"""Create a Jianying-native import pack from a draft plan.

This route does not write Jianying project JSON. It prepares pre-trimmed,
Jianying-friendly H.264 clips and SRT captions so Jianying can create the
timeline through its native import/drag workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from edl_contract import EDLContractError
from edl_contract import parse_seconds as canonical_parse_seconds
from jianying_roughcut_common import ContractError, ensure_dir, load_json, write_json, write_yaml


RAW360_EXTS = {".osv", ".lrf"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


def track_by_id(plan: dict[str, Any], track_id: str) -> dict[str, Any]:
    tracks = plan.get("tracks")
    if not isinstance(tracks, list):
        raise ContractError("plan.tracks must be a list")
    for track in tracks:
        if isinstance(track, dict) and track.get("track_id") == track_id:
            return track
    raise ContractError(f"track not found in plan: {track_id}")


def sec(value: Any) -> float:
    """Validate a non-negative, finite seconds value.

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
        return canonical_parse_seconds(value, path="time_value")
    except EDLContractError as exc:
        if exc.code == "timing_precision":
            return canonical_parse_seconds(round(float(value), 3), path="time_value")
        raise ContractError(f"invalid time value: {value!r}: {exc}") from exc


def srt_time(value: float) -> str:
    millis_total = int(round(value * 1000))
    millis = millis_total % 1000
    seconds_total = millis_total // 1000
    seconds = seconds_total % 60
    minutes_total = seconds_total // 60
    minutes = minutes_total % 60
    hours = minutes_total // 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def slug_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:24] or "clip"


def time_label(seconds: float) -> str:
    return f"{int(round(seconds)):03d}"


def safe_clip_name(index: int, clip: dict[str, Any]) -> str:
    start = sec(clip.get("timeline_start_sec", 0.0))
    end = start + sec(clip["duration_sec"])
    purpose = slug_text(clip.get("purpose", "clip"))
    return f"{index:03d}_{time_label(start)}-{time_label(end)}_{purpose}.mp4"


def ffmpeg_filter(width: int, height: int, fps: int) -> str:
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease:in_range=auto:out_range=tv,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={fps},format=yuv420p"
    )


def raw360_lrf_filter(width: int, height: int, fps: int, *, lens: str = "right") -> str:
    if lens not in {"left", "right"}:
        raise ContractError("raw360 lens must be left or right")
    offset = "0" if lens == "left" else "iw/2"
    return (
        f"crop=iw/2:ih:{offset}:0,"
        f"scale=-2:{height}:in_range=auto:out_range=tv,"
        f"crop={width}:{height}:(iw-{width})/2:0,"
        f"setsar=1,fps={fps},format=yuv420p"
    )


def filter_for_source(source: Path, width: int, height: int, fps: int, *, raw360_lens: str = "right") -> str:
    if source.suffix.lower() == ".lrf" or "360原始组" in source.name:
        return raw360_lrf_filter(width, height, fps, lens=raw360_lens)
    return ffmpeg_filter(width, height, fps)


def is_forbidden_raw360_source(source: Path) -> bool:
    text = source.as_posix()
    return source.suffix.lower() in RAW360_EXTS or "360原始组" in text or "00_RawVault_不可直用" in text


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise ContractError(f"ffmpeg failed:\n{' '.join(args)}\n{result.stderr.strip()}")


def heic_proxy(source: Path, output: Path) -> Path:
    if source.suffix.lower() not in {".heic", ".heif"}:
        return source
    cache_dir = output.parent.parent / "_source_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    proxy = cache_dir / f"{slug_text(source.stem)}.jpg"
    if proxy.exists() and proxy.stat().st_size > 0:
        return proxy
    result = subprocess.run(
        ["sips", "-s", "format", "jpeg", str(source), "--out", str(proxy)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not proxy.exists() or proxy.stat().st_size == 0:
        raise ContractError(f"HEIC proxy conversion failed for {source}: {result.stderr.strip()}")
    return proxy


def render_clip(source: Path, output: Path, clip: dict[str, Any], width: int, height: int, fps: int, *, raw360_lens: str = "right") -> None:
    duration = sec(clip["duration_sec"])
    source_start = sec(clip.get("source_start_sec", 0.0))
    source = heic_proxy(source, output)
    filt = filter_for_source(source, width, height, fps, raw360_lens=raw360_lens)
    output.parent.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()

    if suffix in IMAGE_EXTS:
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-loop",
            "1",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source),
            "-vf",
            filt,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(output),
        ]
    elif suffix in VIDEO_EXTS:
        args = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{source_start:.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration:.3f}",
            "-vf",
            filt,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(output),
        ]
    else:
        raise ContractError(f"unsupported source media type: {source}")
    run_ffmpeg(args)


def write_srt(path: Path, text_clips: list[dict[str, Any]]) -> int:
    lines: list[str] = []
    index = 1
    for clip in text_clips:
        text = str(clip.get("text", "")).strip()
        if not text:
            continue
        start = sec(clip["timeline_start_sec"])
        end = start + sec(clip["duration_sec"])
        lines.extend([str(index), f"{srt_time(start)} --> {srt_time(end)}", text, ""])
        index += 1
    if index == 1:
        raise ContractError("text_caption track must contain at least one non-empty subtitle")
    path.write_text("\n".join(lines), encoding="utf-8")
    return index - 1


def write_caption_readme(captions_dir: Path, srt_path: Path) -> Path:
    readme = captions_dir / "README_字幕导入.md"
    text = f"""# 字幕导入说明

剪映不会因为你导入视频片段就自动把字幕放到时间线。

字幕文件已经生成在：

```text
{srt_path}
```

正确操作：

1. 在剪映里先导入 `01_clips/` 下全部视频，并拖入时间线。
2. 打开 `文本 -> 本地字幕`。
3. 选择本目录下的 `captions.srt`。
4. 预览字幕后添加到时间线。

不要在“媒体/导入”里导入 `captions.srt`，剪映会提示需要到 `文本 -> 本地字幕` 使用。
"""
    readme.write_text(text, encoding="utf-8")
    return readme


def concat_preview(package_dir: Path, preview_dir: Path, clips: list[Path]) -> Path:
    list_path = package_dir / "_concat_list.txt"
    list_path.write_text("\n".join(f"file '{clip}'" for clip in clips) + "\n", encoding="utf-8")
    preview = preview_dir / "preview_roughcut.mp4"
    run_ffmpeg(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(preview),
        ]
    )
    return preview


def write_readme(
    path: Path,
    pack_dir: Path,
    clips_dir: Path,
    captions_dir: Path,
    audio_dir: Path,
    preview_dir: Path,
    *,
    width: int,
    height: int,
    fps: int,
) -> None:
    text = f"""# 剪映原生导入包

这个包不写剪映私有草稿 JSON，只使用剪映自己的原生导入和拖入时间线动作。

## 文件

- 片段目录：`{clips_dir}`
- 字幕目录：`{captions_dir}`
- 可选音频目录：`{audio_dir}`
- 预览目录：`{preview_dir}`
- 包根目录：`{pack_dir}`

## 剪映导入步骤

1. 打开剪映，新建空项目。
2. 导入 `01_clips/` 下全部 mp4。
3. 按文件名排序。
4. 全选所有片段，拖入主时间线。
5. 字幕文件已经在 `02_captions/captions.srt`，但剪映不会自动把它放到时间线。
6. 不要在“媒体/导入”里导入 `captions.srt`。字幕必须走 `文本 -> 本地字幕`。
7. 在 `文本 -> 本地字幕` 中选择 `02_captions/captions.srt`，预览后添加到时间线。
8. BGM 优先在剪映或平台曲库里人工选择；如果 `03_audio/` 有文件，可按需导入。
9. 保存草稿后，在 `11_roughcut_review.md` 里勾选人工检查项。

## 说明

- `04_preview/preview_roughcut.mp4` 只用于预览，不用于最终精剪。
- `01_clips/` 中每段都是独立可编辑片段。
- `02_captions/README_字幕导入.md` 是单独的字幕操作说明。
- 所有片段均按 H.264 / yuv420p / {width}x{height} / {fps}fps 生成。
- Mac OpenClaw 不自动插入 BGM。
"""
    path.write_text(text, encoding="utf-8")


def copy_optional_bgm(plan: dict[str, Any], audio_dir: Path) -> str:
    bgm = plan.get("bgm")
    if not isinstance(bgm, dict):
        return ""
    source_value = str(bgm.get("source_file") or "").strip()
    if not source_value:
        return ""
    source = Path(source_value).expanduser()
    if not source.exists() or not source.is_file():
        raise ContractError(f"bgm.source_file does not exist: {source}")
    target = audio_dir / f"bgm_optional{source.suffix.lower()}"
    shutil.copy2(source, target)
    return str(target)


def create_package(plan_path: Path, output_root: Path, result_output: Path | None, allow_replace: bool) -> dict[str, Any]:
    plan = load_json(plan_path)
    if plan.get("doc_type") != "jianying_draft_plan":
        raise ContractError("plan.doc_type must be jianying_draft_plan")
    if not plan.get("constraints", {}).get("strict_mode"):
        raise ContractError("plan.constraints.strict_mode must be true")

    target = plan.get("target")
    if not isinstance(target, dict):
        raise ContractError("plan.target must be an object")
    width = int(target.get("width", 1080))
    height = int(target.get("height", 1920))
    fps = int(target.get("fps", 30))
    raw360_lens = str(target.get("raw360_lens") or "right")
    if raw360_lens not in {"left", "right"}:
        raise ContractError("plan.target.raw360_lens must be left or right")

    pack_name = str(plan.get("draft_name") or "").strip()
    pack_name = pack_name.replace("jy_roughcut", "jy_import_pack").replace("jy_native_import", "jy_import_pack")
    if not pack_name:
        raise ContractError("plan.draft_name is required")
    pack_dir = output_root / pack_name
    if pack_dir.exists():
        if not allow_replace:
            raise ContractError(f"pack already exists: {pack_dir}")
        shutil.rmtree(pack_dir)
    clips_dir = ensure_dir(pack_dir / "01_clips")
    captions_dir = ensure_dir(pack_dir / "02_captions")
    audio_dir = ensure_dir(pack_dir / "03_audio")
    preview_dir = ensure_dir(pack_dir / "04_preview")

    rendered_clips: list[Path] = []
    manifest_clips: list[dict[str, Any]] = []
    for index, clip in enumerate(track_by_id(plan, "video_main").get("clips", []), start=1):
        if not isinstance(clip, dict):
            raise ContractError("video clip entries must be objects")
        source = Path(str(clip.get("source_file", ""))).expanduser()
        if not source.exists() or not source.is_file():
            raise ContractError(f"source media does not exist: {source}")
        if is_forbidden_raw360_source(source):
            raise ContractError(
                "native import pack cannot render RawVault/OSV/LRF 360 source directly. "
                "Export a reframed editable MP4 first and use that MP4 in the draft plan: "
                f"{source}"
            )
        output = clips_dir / safe_clip_name(index, clip)
        render_clip(source, output, clip, width, height, fps, raw360_lens=raw360_lens)
        start = sec(clip.get("timeline_start_sec", 0.0))
        duration = sec(clip["duration_sec"])
        rendered_clips.append(output)
        manifest_clips.append(
            {
                "slot": int(clip.get("slot", index)),
                "filename": output.name,
                "relative_path": f"01_clips/{output.name}",
                "output": str(output),
                "source_file": str(source),
                "timeline_start_sec": start,
                "duration_sec": duration,
                "timeline_end_sec": start + duration,
                "purpose": clip.get("purpose", ""),
                "visual_need": clip.get("visual_need", ""),
                "edit_note": clip.get("edit_note", ""),
            }
        )

    srt_path = captions_dir / "captions.srt"
    caption_count = write_srt(srt_path, [clip for clip in track_by_id(plan, "text_caption").get("clips", []) if isinstance(clip, dict)])
    caption_readme = write_caption_readme(captions_dir, srt_path)
    bgm_optional = copy_optional_bgm(plan, audio_dir)
    preview = concat_preview(pack_dir, preview_dir, rendered_clips)
    edit_manifest = pack_dir / "edit_manifest.json"
    manifest = {
        "spec_version": "content_os_v0.1",
        "doc_type": "native_import_pack_manifest",
        "project_id": plan.get("project_id"),
        "idea_id": plan.get("idea_id", ""),
        "pack_name": pack_name,
        "source_plan": str(plan_path),
        "target": {
            "width": width,
            "height": height,
            "fps": fps,
            "duration_sec": target.get("duration_sec"),
            "platform": target.get("platform", ""),
        },
        "import_order": [item["relative_path"] for item in manifest_clips],
        "clips": manifest_clips,
        "captions_srt": "02_captions/captions.srt",
        "caption_readme": "02_captions/README_字幕导入.md",
        "caption_import_method": "Jianying: 文本 -> 本地字幕 -> 选择 captions.srt",
        "bgm_optional": "03_audio/" + Path(bgm_optional).name if bgm_optional else "",
        "preview_video": "04_preview/preview_roughcut.mp4",
        "human_steps_required": [
            "open_jianying",
            "create_new_project",
            "import_clips_sorted_by_filename",
            "drag_clips_to_timeline",
            "import_captions_srt",
            "save_as_editable_draft",
        ],
    }
    write_json(edit_manifest, manifest)
    readme = pack_dir / "README_导入剪映.md"
    write_readme(
        readme,
        pack_dir,
        clips_dir,
        captions_dir,
        audio_dir,
        preview_dir,
        width=width,
        height=height,
        fps=fps,
    )

    result = {
        "spec_version": "content_os_v0.1",
        "doc_type": "native_import_pack_result",
        "status": "done",
        "writer_agent": "mac_openclaw",
        "owner_agent": "mac_openclaw",
        "next_owner": "human",
        "project_id": plan.get("project_id"),
        "idea_id": plan.get("idea_id", ""),
        "source_plan": str(plan_path),
        "pack_name": pack_name,
        "pack_dir": str(pack_dir),
        "contents": {
            "clips_dir": str(clips_dir),
            "captions_srt": str(srt_path),
            "caption_readme": str(caption_readme),
            "caption_import_method": manifest["caption_import_method"],
            "bgm_optional": bgm_optional,
            "preview_video": str(preview),
            "edit_manifest": str(edit_manifest),
            "readme": str(readme),
        },
        "readme": str(readme),
        "clip_count": len(rendered_clips),
        "caption_count": caption_count,
        "validation": {
            "native_import_required": True,
            "human_drag_to_timeline_required": True,
            "no_direct_draft_json": True,
            "no_auto_export": True,
            "all_clip_files_exist": True,
            "srt_exists": True,
            "srt_nonempty": True,
            "preview_exists": True,
            "raw360_direct_use_blocked": True,
        },
        "clips": manifest_clips,
        "human_steps_required": manifest["human_steps_required"],
        "proposed_next_status": "native_import_pack_ready",
        "tools_used": {
            "ffmpeg": "native_import_pack",
        },
    }
    if result_output:
        write_yaml(result_output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--result-output", type=Path)
    parser.add_argument("--allow-replace", action="store_true")
    args = parser.parse_args()

    result = create_package(
        args.plan.expanduser().resolve(),
        args.output_root.expanduser().resolve(),
        args.result_output.expanduser().resolve() if args.result_output else None,
        args.allow_replace,
    )
    print(f"pack_dir={result['pack_dir']}")
    print(f"clip_count={result['clip_count']}")
    print(f"captions_srt={result['contents']['captions_srt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
