#!/usr/bin/env python3
"""Validate a generated Jianying roughcut draft against its draft plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jianying_roughcut_common import ContractError, load_json, load_yaml, write_yaml


def json_parseable(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return True


def count_plan_clips(plan: dict[str, Any], track_id: str) -> int:
    for track in plan.get("tracks", []):
        if isinstance(track, dict) and track.get("track_id") == track_id:
            return len(track.get("clips") or [])
    raise ContractError(f"track not found in plan: {track_id}")


def count_draft_segments(tracks: list[Any], *, track_type: str, track_name: str | None = None) -> int:
    for track in tracks:
        if not isinstance(track, dict) or track.get("type") != track_type:
            continue
        if track_name is not None and track.get("name") != track_name:
            continue
        return len(track.get("segments") or [])
    return -1


def require_video_render_fields(track: dict[str, Any]) -> None:
    if track.get("name") != "":
        raise ContractError("main video track must use the default empty Jianying track name")
    if track.get("is_default_name") is not True:
        raise ContractError("main video track must set is_default_name=true")
    for index, segment in enumerate(track.get("segments") or []):
        if not isinstance(segment, dict):
            raise ContractError(f"video segment {index} must be an object")
        if segment.get("visible") is not True:
            raise ContractError(f"video segment {index} must set visible=true")
        clip = segment.get("clip")
        if not isinstance(clip, dict):
            raise ContractError(f"video segment {index} clip settings missing")
        if clip.get("alpha") != 1.0:
            raise ContractError(f"video segment {index} clip.alpha must be 1.0")
        if "rotation" not in clip:
            raise ContractError(f"video segment {index} clip.rotation missing")
        flip = clip.get("flip")
        if not isinstance(flip, dict) or "horizontal" not in flip or "vertical" not in flip:
            raise ContractError(f"video segment {index} clip.flip must include horizontal and vertical")
        uniform_scale = segment.get("uniform_scale")
        if not isinstance(uniform_scale, dict) or uniform_scale.get("on") is not True:
            raise ContractError(f"video segment {index} uniform_scale.on must be true")
        source_timerange = segment.get("source_timerange")
        if not isinstance(source_timerange, dict) or "start" not in source_timerange:
            raise ContractError(f"video segment {index} source_timerange.start missing")


def validate(plan_path: Path, result_path: Path, validation_output: Path | None) -> dict[str, Any]:
    plan = load_json(plan_path)
    result = load_yaml(result_path)
    draft_dir = Path(str(result.get("draft_dir", ""))).expanduser()
    if not draft_dir.exists() or not draft_dir.is_dir():
        raise ContractError(f"draft_dir does not exist: {draft_dir}")

    draft_content = draft_dir / "draft_content.json"
    meta_candidates = [draft_dir / "draft_meta_info.json", draft_dir / "draft_mate_info.json"]
    if not draft_content.exists():
        raise ContractError(f"draft_content.json missing: {draft_content}")
    meta = next((path for path in meta_candidates if path.exists()), None)
    if meta is None:
        raise ContractError(f"draft meta info missing in {draft_dir}")

    content = json.loads(draft_content.read_text(encoding="utf-8"))
    draft_meta_info_parseable = json_parseable(meta)
    tracks = content.get("tracks")
    if not isinstance(tracks, list):
        raise ContractError("draft_content.tracks must be a list")

    installed_dir_value = result.get("jianying_installed_draft_dir")
    installed_dir = Path(str(installed_dir_value)).expanduser() if installed_dir_value else None
    installed_copy_json_parse_passed = False
    if installed_dir:
        if not installed_dir.exists() or not installed_dir.is_dir():
            raise ContractError(f"jianying_installed_draft_dir does not exist: {installed_dir}")
        installed_content = installed_dir / "draft_content.json"
        installed_meta_candidates = [
            installed_dir / "draft_meta_info.json",
            installed_dir / "draft_mate_info.json",
        ]
        if not installed_content.exists():
            raise ContractError(f"installed draft_content.json missing: {installed_content}")
        installed_meta = next((path for path in installed_meta_candidates if path.exists()), None)
        if installed_meta is None:
            raise ContractError(f"installed draft meta info missing in {installed_dir}")
        json.loads(installed_content.read_text(encoding="utf-8"))
        installed_copy_json_parse_passed = True

    draft_track_counts: dict[str, int] = {}
    for track in tracks:
        if isinstance(track, dict):
            name = str(track.get("name") or track.get("type") or "unknown")
            draft_track_counts[name] = len(track.get("segments") or [])
            if track.get("type") == "video":
                require_video_render_fields(track)

    bundled_media_paths_exist = False
    if result.get("media_bundled_into_draft"):
        bundled_media_paths_exist = True
        videos = content.get("materials", {}).get("videos", [])
        if not isinstance(videos, list):
            raise ContractError("draft_content.materials.videos must be a list")
        for item in videos:
            if not isinstance(item, dict):
                continue
            path_value = str(item.get("path") or "")
            marker = "##/"
            if not path_value.startswith("##_draftpath_placeholder_") or marker not in path_value:
                raise ContractError(f"bundled media path must use draft placeholder: {path_value}")
            relative = path_value.split(marker, 1)[1]
            bundled_file = draft_dir / relative
            if not bundled_file.exists() or bundled_file.stat().st_size == 0:
                raise ContractError(f"bundled media file missing: {bundled_file}")

    plan_video = count_plan_clips(plan, "video_main")
    plan_text = count_plan_clips(plan, "text_caption")
    draft_video = count_draft_segments(tracks, track_type="video")
    draft_text = count_draft_segments(tracks, track_type="text", track_name="text_caption")
    if draft_video != plan_video:
        raise ContractError(f"video segment count mismatch: draft={draft_video} plan={plan_video}")
    if draft_text != plan_text:
        raise ContractError(f"text segment count mismatch: draft={draft_text} plan={plan_text}")

    for track in plan.get("tracks", []):
        if not isinstance(track, dict):
            continue
        for clip in track.get("clips") or []:
            if isinstance(clip, dict) and clip.get("source_file"):
                source = Path(str(clip["source_file"])).expanduser()
                if not source.exists():
                    raise ContractError(f"source media missing: {source}")

    validation = {
        "spec_version": "content_os_v0.1",
        "doc_type": "jianying_draft_validation",
        "status": "passed",
        "project_id": plan.get("project_id"),
        "idea_id": plan.get("idea_id", ""),
        "draft_dir": str(draft_dir),
        "jianying_installed_draft_dir": str(installed_dir) if installed_dir else "",
        "draft_content_exists": True,
        "draft_meta_info_exists": True,
        "draft_meta_info_parseable": draft_meta_info_parseable,
        "json_parse_passed": True,
        "installed_copy_json_parse_passed": installed_copy_json_parse_passed,
        "media_paths_exist": True,
        "bundled_media_paths_exist": bundled_media_paths_exist,
        "video_render_fields_exist": True,
        "plan_video_clips": plan_video,
        "plan_text_clips": plan_text,
        "draft_track_counts": draft_track_counts,
        "human_open_check_required": True,
    }
    if validation_output:
        write_yaml(validation_output, validation)
    return validation


def write_review(path: Path, validation: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    installed_dir = validation["jianying_installed_draft_dir"]
    if installed_dir and installed_dir == validation["draft_dir"]:
        directory_section = f"""## 剪映草稿目录（唯一事实来源）

```text
{validation["draft_dir"]}
```
"""
        installed_label = "剪映草稿目录 JSON 可解析"
    else:
        directory_section = f"""## 本地草稿目录

```text
{validation["draft_dir"]}
```

## 剪映草稿目录副本

```text
{installed_dir or "未安装到剪映草稿根目录"}
```
"""
        installed_label = "剪映草稿目录副本 JSON 可解析"
    text = f"""---
spec_version: content_os_v0.1
doc_type: roughcut_review
project_id: {validation.get("project_id", "")}
idea_id: {validation.get("idea_id", "")}
status: pending_human_open_check
writer_agent: mac_openclaw
owner_agent: human
next_owner: human
---

# Jianying Roughcut Review

粗剪草稿已通过文件级校验，但还不是 Final。

{directory_section}

## 自动校验

| 项目 | 结果 |
|---|---|
| draft_content.json 存在 | yes |
| draft_meta_info.json 存在 | yes |
| draft_content.json 可解析 | yes |
| draft_meta_info.json 可解析 | {"yes" if validation["draft_meta_info_parseable"] else "opened_by_jianying"} |
| {installed_label} | {"yes" if validation["installed_copy_json_parse_passed"] else "not_checked"} |
| 素材路径存在 | yes |
| 草稿内置媒体存在 | {"yes" if validation["bundled_media_paths_exist"] else "not_checked"} |
| 视频渲染字段完整 | yes |
| 视频片段数 | {validation["plan_video_clips"]} |
| 字幕片段数 | {validation["plan_text_clips"]} |

## 人工打开检查

- [ ] 剪映能看到这个草稿
- [ ] 时间线上有视频素材
- [ ] 字幕能显示
- [ ] 顺序大致符合 EDL
- [ ] 可以继续精剪

结论：粗剪草稿已通过自动校验；等待人打开剪映确认。
"""
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
    print(f"draft_dir={validation['draft_dir']}")
    print(f"video_clips={validation['plan_video_clips']}")
    print(f"text_clips={validation['plan_text_clips']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
