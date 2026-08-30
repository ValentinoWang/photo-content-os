#!/usr/bin/env python3
"""Validate a Jianying-native import pack."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from jianying_roughcut_common import ContractError, count_plan_clips, ffprobe_duration_sec, load_json, load_yaml, write_yaml


def ffprobe_video_stream(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,pix_fmt,r_frame_rate",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ContractError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise ContractError(f"video stream missing: {path}")
    stream = streams[0]
    rate = str(stream.get("r_frame_rate", "0/1"))
    numerator, denominator = rate.split("/", 1)
    fps = float(numerator) / float(denominator or "1")
    return {
        "codec_name": stream.get("codec_name", ""),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "pix_fmt": stream.get("pix_fmt", ""),
        "fps": round(fps, 3),
    }


def validate_video_spec(path: Path, spec: dict[str, Any], width: int, height: int, fps: int) -> None:
    if spec["codec_name"] != "h264":
        raise ContractError(f"clip must be h264: {path} codec={spec['codec_name']}")
    if spec["pix_fmt"] != "yuv420p":
        raise ContractError(f"clip must be yuv420p: {path} pix_fmt={spec['pix_fmt']}")
    if spec["width"] != width or spec["height"] != height:
        raise ContractError(f"clip resolution mismatch: {path} got={spec['width']}x{spec['height']} expected={width}x{height}")
    if abs(float(spec["fps"]) - float(fps)) > 0.02:
        raise ContractError(f"clip fps mismatch: {path} got={spec['fps']} expected={fps}")


def count_srt_captions(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return text.count(" --> ")


def validate(plan_path: Path, result_path: Path, validation_output: Path | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    target = plan.get("target") if isinstance(plan.get("target"), dict) else {}
    width = int(target.get("width", 1080))
    height = int(target.get("height", 1920))
    fps = int(target.get("fps", 30))
    result = load_yaml(result_path)
    if result.get("doc_type") != "native_import_pack_result":
        raise ContractError("result.doc_type must be native_import_pack_result")
    contents = result.get("contents")
    if not isinstance(contents, dict):
        raise ContractError("result.contents must be an object")
    pack_dir = Path(str(result.get("pack_dir", ""))).expanduser()
    clips_dir = Path(str(contents.get("clips_dir", ""))).expanduser()
    srt_path = Path(str(contents.get("captions_srt", ""))).expanduser()
    caption_readme = Path(str(contents.get("caption_readme", ""))).expanduser()
    preview = Path(str(contents.get("preview_video", ""))).expanduser()
    edit_manifest = Path(str(contents.get("edit_manifest", ""))).expanduser()
    readme = Path(str(contents.get("readme", result.get("readme", "")))).expanduser()

    for path in [pack_dir, clips_dir]:
        if not path.exists() or not path.is_dir():
            raise ContractError(f"required directory missing: {path}")
    for path in [srt_path, caption_readme, preview, edit_manifest, readme]:
        if not path.exists() or path.stat().st_size == 0:
            raise ContractError(f"required file missing or empty: {path}")
    manifest = load_json(edit_manifest)
    if manifest.get("doc_type") != "native_import_pack_manifest":
        raise ContractError("edit_manifest.doc_type must be native_import_pack_manifest")

    clips = sorted(clips_dir.glob("*.mp4"))
    plan_video = count_plan_clips(plan, "video_main")
    plan_text = count_plan_clips(plan, "text_caption")
    if len(clips) != plan_video:
        raise ContractError(f"clip count mismatch: package={len(clips)} plan={plan_video}")
    captions = count_srt_captions(srt_path)
    if plan_text <= 0:
        raise ContractError("text_caption track must contain at least one subtitle")
    if captions <= 0:
        raise ContractError(f"captions.srt must contain at least one subtitle: {srt_path}")
    if captions != plan_text:
        raise ContractError(f"caption count mismatch: srt={captions} plan={plan_text}")

    clip_durations = []
    for clip in clips:
        # L-16: ffprobe_duration_sec already guarantees duration > 0 (raises
        # ContractError itself otherwise), so the former separate `duration
        # <= 0` re-check here is now redundant and dropped.
        duration = ffprobe_duration_sec(clip)
        spec = ffprobe_video_stream(clip)
        validate_video_spec(clip, spec, width, height, fps)
        clip_durations.append({"clip": str(clip), "duration_sec": round(duration, 3), **spec})

    preview_duration = ffprobe_duration_sec(preview)
    preview_spec = ffprobe_video_stream(preview)
    validate_video_spec(preview, preview_spec, width, height, fps)
    validation = {
        "spec_version": "content_os_v0.1",
        "doc_type": "native_import_pack_validation",
        "status": "passed",
        "project_id": plan.get("project_id"),
        "idea_id": plan.get("idea_id", ""),
        "pack_dir": str(pack_dir),
        "clips_dir": str(clips_dir),
        "captions_srt": str(srt_path),
        "caption_readme": str(caption_readme),
        "caption_import_method": contents.get("caption_import_method", "Jianying: 文本 -> 本地字幕 -> 选择 captions.srt"),
        "preview_video": str(preview),
        "edit_manifest": str(edit_manifest),
        "readme": str(readme),
        "clip_count": len(clips),
        "caption_count": captions,
        "preview_duration_sec": round(preview_duration, 3),
        "target_video_spec": {
            "codec_name": "h264",
            "width": width,
            "height": height,
            "pix_fmt": "yuv420p",
            "fps": fps,
        },
        "preview_video_spec": preview_spec,
        "clip_durations": clip_durations,
        "native_import_required": True,
        "human_drag_to_timeline_required": True,
        "no_direct_draft_json": True,
        "raw360_direct_use_blocked": bool((result.get("validation") or {}).get("raw360_direct_use_blocked")),
    }
    if validation_output:
        write_yaml(validation_output, validation)
    return validation


def write_review(path: Path, validation: dict[str, Any]) -> None:
    text = f"""---
spec_version: content_os_v0.1
doc_type: roughcut_review
project_id: {validation.get("project_id", "")}
idea_id: {validation.get("idea_id", "")}
status: native_import_pack_ready
writer_agent: mac_openclaw
owner_agent: human
next_owner: human
---

# Jianying Native Import Pack Review

pyJianYingDraft 直写草稿路线已阻断。当前使用剪映原生导入包路线。

## 导入包

```text
{validation["pack_dir"]}
```

## 文件

| 项目 | 路径 |
|---|---|
| 预裁剪片段 | `{validation["clips_dir"]}` |
| 字幕 SRT | `{validation["captions_srt"]}` |
| 字幕导入说明 | `{validation["caption_readme"]}` |
| 预览视频 | `{validation["preview_video"]}` |
| 导入清单 | `{validation["edit_manifest"]}` |

## 自动校验

| 项目 | 结果 |
|---|---|
| 片段数 | {validation["clip_count"]} |
| 字幕数 | {validation["caption_count"]} |
| 预览时长 | {validation["preview_duration_sec"]} 秒 |
| 直接写剪映 JSON | no |

## 人工导入检查

- [ ] 新建剪映空项目
- [ ] 导入 `01_clips/` 下全部 mp4
- [ ] 按文件名排序
- [ ] 全选拖入主时间线
- [ ] 进入 `文本 -> 本地字幕`
- [ ] 在本地字幕里选择并添加 `02_captions/captions.srt`
- [ ] 视频画面能正常预览
- [ ] 可以继续精剪

结论：等待人使用剪映原生导入并保存真实剪映草稿。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--validation-output", type=Path)
    parser.add_argument("--roughcut-review-output", type=Path)
    args = parser.parse_args()

    validation = validate(
        args.plan.expanduser().resolve(),
        args.result.expanduser().resolve(),
        args.validation_output.expanduser().resolve() if args.validation_output else None,
    )
    if args.roughcut_review_output:
        write_review(args.roughcut_review_output.expanduser().resolve(), validation)
    print(f"status={validation['status']}")
    print(f"pack_dir={validation['pack_dir']}")
    print(f"clip_count={validation['clip_count']}")
    print(f"caption_count={validation['caption_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
