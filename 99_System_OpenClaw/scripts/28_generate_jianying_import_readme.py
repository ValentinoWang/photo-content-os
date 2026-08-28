#!/usr/bin/env python3
"""Generate the human-facing Jianying import README for a native import pack."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jianying_roughcut_common import ContractError, load_yaml


def target_video_spec(edit_manifest: Path) -> tuple[int, int, int]:
    try:
        manifest = json.loads(edit_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read native import pack manifest: {edit_manifest}") from exc
    target = manifest.get("target") if isinstance(manifest, dict) else None
    if not isinstance(target, dict):
        raise ContractError("native import pack manifest.target must be an object")
    try:
        width = int(target["width"])
        height = int(target["height"])
        fps = int(target["fps"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("native import pack manifest.target must define integer width, height, and fps") from exc
    if min(width, height, fps) <= 0:
        raise ContractError("native import pack manifest.target values must be positive")
    return width, height, fps


def write_readme(result_path: Path, output: Path | None) -> Path:
    result = load_yaml(result_path)
    if result.get("doc_type") != "native_import_pack_result":
        raise ContractError("result.doc_type must be native_import_pack_result")
    contents = result.get("contents")
    if not isinstance(contents, dict):
        raise ContractError("result.contents must be an object")

    pack_dir = Path(str(result.get("pack_dir", ""))).expanduser()
    clips_dir = Path(str(contents.get("clips_dir", ""))).expanduser()
    captions_srt = Path(str(contents.get("captions_srt", ""))).expanduser()
    bgm_optional = str(contents.get("bgm_optional") or "")
    preview_video = Path(str(contents.get("preview_video", ""))).expanduser()
    edit_manifest = Path(str(contents.get("edit_manifest", ""))).expanduser()
    width, height, fps = target_video_spec(edit_manifest)

    readme = output.expanduser() if output else pack_dir / "README_导入剪映.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# 剪映原生导入包

这个包不写剪映私有草稿 JSON。真实可编辑草稿由剪映自己创建。

## 包路径

```text
{pack_dir}
```

## 内容

| 类型 | 路径 |
|---|---|
| 片段 | `{clips_dir}` |
| 字幕 | `{captions_srt}` |
| 可选 BGM | `{bgm_optional or '未提供，建议在剪映/平台曲库中人工选择'}` |
| 预览 | `{preview_video}` |
| 清单 | `{edit_manifest}` |
| 目标规格 | `H.264 / yuv420p / {width}x{height} / {fps}fps` |

## 操作

1. 打开剪映，新建空项目。
2. 导入 `01_clips/` 下全部 mp4。
3. 按文件名排序。
4. 全选拖入主时间线。
5. 不要在“媒体/导入”里导入 `captions.srt`。字幕要走 `文本 -> 本地字幕`。
6. 在 `文本 -> 本地字幕` 中选择 `02_captions/captions.srt`，预览后添加到时间线。
7. 保存草稿。
8. 在 `11_roughcut_review.md` 里记录人工验收结果。
"""
    readme.write_text(text, encoding="utf-8")
    return readme


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    readme = write_readme(args.result.expanduser().resolve(), args.output.expanduser().resolve() if args.output else None)
    print(f"readme={readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
