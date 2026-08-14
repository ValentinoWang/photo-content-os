#!/usr/bin/env python3
"""Generate per-media AI analysis prompts from the manifest and keyframes."""

from __future__ import annotations

import argparse
from pathlib import Path

from media_common import eligible_item, load_manifest, project_path, safe_slug

VISUAL_SIMILARITY_THRESHOLD = 8
USER_INTENT_NOTES = "_ai_analysis/user_intent_notes.md"

CARD_SCHEMA = """# 作品内容概述

- 素材名称：
- 内容类型：
- 画面事实：
- 隐含叙事意图：
- 可表达观点：
- 适配作品风格：
- 情绪价值：
- 可用片段：
- 适合平台：
- 推荐用途：
- 推荐命名：
- 标签：
- 质量问题：
- 是否需要 Wink：
"""

PROMPT_TEMPLATE = """# 作品内容分析任务

你是一个自媒体内容策划和剪辑助理。请根据素材信息和随附关键帧，为该素材生成可沉淀到素材库的内容概述。

## 素材信息

- 文件名：{filename}
- 相对路径：{relative_path}
- 类型：{media_type}
- 来源：{source_type}
- 生命周期：{lifecycle}
- 文件大小：{size_mb} MB
- 时长：{duration_sec} 秒
- 分辨率：{width} x {height}
- 是否有音频：{has_audio}
- Live Photo 状态：{live_photo_status}
- GPS 原始值：{location_raw}
- GPS 坐标：{gps_latitude}, {gps_longitude}
- GPS 精度：{gps_horizontal_accuracy}
- 质量标记：{quality_flags}
- Raw 判别原因：{raw_decision_tokens}
- 判别备注：{decision_notes}
- 关键帧数量：{keyframe_count}
- 关键帧目录：{keyframe_dir}

## 用户/创作者意图笔记

{user_intent_notes}

## 关键帧文件

{keyframes}

## 分析要求

1. 不要只描述“有一个视频”，要判断它在自媒体叙事里的用途。
2. 优先从 GPS、画面文字、站牌、路牌、建筑标识里提取城市、地点、站名、线路、方向等信息。
3. 如果地点只能判断到城市，不要硬写具体站名；如果能看到站牌，例如“嘉禾望岗 / Jiahewanggang”，则写入具体站名。
4. 如果关键帧里人物、动作、场景不清楚，请明确写“不确定”，不要编造。
5. 必须区分“画面事实”和“隐含叙事意图”：画面事实只写能看见的主体、动作、设备、空间；隐含叙事意图写这个画面可能在项目里表达什么观点或幕后价值。
6. 不要把素材压扁成泛称。看到设备、道具、操作负担、准备成本、失败感、尴尬、等待、分心、幕后工作等线索时，要主动分析它们的叙事价值。
7. 如果画面出现相机、全景相机、胸前固定设备、手持控制器、补光、脚架、收音、箱包等创作工具，要判断它是否表达“创作幕后、设备不便捷、拍摄成本、第一视角准备、运动员兼拍摄者的负担”等价值。
8. 用户明确说过的素材意图优先于泛化分类；如果没有用户意图，只能给“可能表达”的假设，并标明依据，不要当作事实。
9. 可用片段请尽量用关键帧文件名里的时间戳推断，例如 00:02-00:06。
10. 不要判断是否进入 iCloud 照片精选库，也不要替用户选择高光照片。
11. 判断是否需要 Wink 修复、增强、防抖、降噪、调色、裁切、慢放或截帧做封面。
12. 推荐命名要遵守素材库规则：文件夹说明项目和场景，文件名只写画面事实和处理状态；叙事意图写进 summary / 资产卡片，不强行塞进文件名。
13. 不要让某一个作品风格锁死 L3 源文件名；`第一视角全景跑400米`、`400米比赛记录`、`全景相机幕后感` 等写进“适配作品风格”，只有风格化衍生物或 91 输出成片才把风格写进文件名。
14. 不要把短边达到 720p 或以上的素材称为低清；如果只是开头/结尾不可用，应写“待截取”，如果画面抖动，应写“待防抖”。

## 输出格式

请严格输出下面这张 Markdown 卡片，不要输出额外解释：

{card_schema}
"""

PROJECT_PROMPT = """# 项目总览分析任务

你是一个自媒体内容策划和剪辑助理。请根据项目的 media_manifest.json、各素材 prompt、关键帧和后续素材概述，生成项目总览。

## 用户/创作者意图笔记

{user_intent_notes}

## 请输出

- 项目一句话主题
- 叙事结构建议
- 隐含叙事线索：设备负担、创作幕后、准备成本、人物分心、真实尴尬、反差或失败感等
- 可发展的作品风格方向：例如第一视角全景跑400米、400米比赛记录、全景相机幕后感、人物状态短片
- 最值得剪的 5-10 个素材
- 适合做开头钩子的素材
- 适合做封面的素材
- 合照发放或剪辑取用时需要人工复核的素材
- 需要 Wink 修复 / 防抖 / 调色的素材
- 建议的抖音 / 小红书标题方向
- 项目标签
"""

L3_STRUCTURE_PROMPT_HEADER = """# 项目 L3 内容结构判读任务

你是素材库结构规划助理。请根据整个项目的 media_manifest.json、关键帧、素材 prompt 和项目总览，为项目生成 L3 内容目录结构和迁移计划。

## 核心规则

1. 不使用固定模板目录。不要因为脚本、旧项目或目录历史里出现过某些分类名就照抄。
2. 先判断这个项目真实叙事：它是单一事件、旅程、人物线、交付包，还是多主题集合。
3. L3 内容目录必须来自全局语义分析，目录名要服务剪辑和复核，不要服务“高光筛选”。
4. `80_To_iCloudPhotos_精选入库`、`90_Draft_Project`、`91_Output`、`92_Aliyun_SyncReady`、`待增加`、`_ai_analysis` 是工作流目录，不是内容分类目录。
5. `00_RawVault_不可直用` 可以按原始关联组或待重构类型建立子目录，但 OSV/LRF/INSV、HEIC/MOV/XMP 等关联组必须同组移动，不拆语义。
6. 输出结构计划时，只移动项目内已有素材，不覆盖已有文件，不删除素材。
7. 先检查“视觉相似候选组”。同一主体、同一机位、同一场景、同一动作链条的短片段，默认归入同一个 L3 内容目录；只有画面证据能证明功能不同，才允许拆开。
8. `同框 / 互动 / 交流 / 关系` 这类人物关系词必须有明确画面证据；如果只是单人主体，优先写 `站位`、`候场`、`示意`、`看台远景`、`号码布xx` 等可观察描述。
9. L3 目录不是只按物理场景切分，也要允许按叙事功能切分，例如 `创作幕后与设备准备`、`第一视角设备调试`、`人物呈现与候场状态`。如果一批素材的核心价值是拍摄设备带来的负担或幕后感，不要简单归为普通候场。

## 请输出 JSON

```json
{
  "plan_version": 1,
  "source": "LLM全局分析",
  "project_dir": "项目绝对路径",
  "rationale": "为什么采用这套 L3 结构",
  "folders": [
    {"path": "01_示例内容目录", "reason": "这个目录承载的叙事功能"}
  ],
  "moves": [
    {"from": "旧相对路径/文件名.mov", "to": "新相对路径/文件名.mov", "reason": "为什么放到这里"}
  ]
}
```

"""


def hamming_distance(left: int, right: int) -> int:
    return bin(int(left) ^ int(right)).count("1")


def average_hash(image_path: Path, hash_size: int = 8) -> int | None:
    try:
        from PIL import Image
    except Exception:
        return None

    try:
        image = Image.open(image_path).convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    except Exception:
        return None

    pixels = list(image.tobytes())
    if not pixels:
        return None
    average = sum(pixels) / len(pixels)
    value = 0
    for index, pixel in enumerate(pixels):
        if pixel >= average:
            value |= 1 << index
    return value


def keyframe_hashes(project: Path, item: dict[str, object], limit: int = 3) -> list[int]:
    hashes: list[int] = []
    for relative in (item.get("keyframes") or [])[:limit]:
        frame_path = project / str(relative)
        if not frame_path.exists():
            continue
        value = average_hash(frame_path)
        if value is not None:
            hashes.append(value)
    return hashes


def visual_similarity_groups(
    project: Path,
    items: list[dict[str, object]],
    threshold: int = VISUAL_SIMILARITY_THRESHOLD,
) -> tuple[list[list[dict[str, object]]], list[dict[str, object]]]:
    hashed = [(item, keyframe_hashes(project, item)) for item in items if item.get("keyframes")]
    hashed = [(item, hashes) for item, hashes in hashed if hashes]
    parents = {str(item.get("relative_path")): str(item.get("relative_path")) for item, _ in hashed}

    def find(value: str) -> str:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    pairs: list[dict[str, object]] = []
    for index, (left_item, left_hashes) in enumerate(hashed):
        for right_item, right_hashes in hashed[index + 1 :]:
            distance = min(hamming_distance(left, right) for left in left_hashes for right in right_hashes)
            if distance <= threshold:
                left_path = str(left_item.get("relative_path"))
                right_path = str(right_item.get("relative_path"))
                pairs.append({"distance": distance, "left": left_path, "right": right_path})
                union(left_path, right_path)

    grouped: dict[str, list[dict[str, object]]] = {}
    by_path = {str(item.get("relative_path")): item for item, _ in hashed}
    for relative in parents:
        grouped.setdefault(find(relative), []).append(by_path[relative])

    groups = [members for members in grouped.values() if len(members) >= 2]
    groups.sort(key=lambda members: [str(item.get("relative_path")) for item in members])
    pairs.sort(key=lambda pair: (int(pair["distance"]), str(pair["left"]), str(pair["right"])))
    return groups, pairs


def visual_similarity_markdown(groups: list[list[dict[str, object]]], pairs: list[dict[str, object]]) -> str:
    lines = [
        "## 视觉相似候选组",
        "",
        "这些只是基于关键帧感知哈希得到的复核候选，不代表重复删除。做 L3 目录划分和命名时，应先人工/LLM 对照关键帧，保持同一画面链条的目录一致。",
        "",
    ]
    if not groups:
        lines.extend(["无明显候选组。", ""])
        return "\n".join(lines)

    for group_index, members in enumerate(groups, start=1):
        lines.append(f"### G{group_index:02d}")
        lines.append("")
        for item in members:
            frames = item.get("keyframes") or []
            first_frame = frames[0] if frames else "无"
            lines.append(f"- {item.get('relative_path')} | 首帧：{first_frame}")
        related = [
            pair
            for pair in pairs
            if any(pair["left"] == member.get("relative_path") for member in members)
            and any(pair["right"] == member.get("relative_path") for member in members)
        ]
        if related:
            lines.append("")
            lines.append("候选距离：")
            for pair in related[:10]:
                lines.append(f"- {pair['distance']}: {pair['left']} ↔ {pair['right']}")
        lines.append("")
    return "\n".join(lines)


def l3_structure_item_block(item: dict[str, object]) -> str:
    frames = item.get("keyframes") or []
    keyframes = ", ".join(str(frame) for frame in frames[:6]) if frames else "无"
    return "\n".join(
        [
            f"### {item.get('relative_path')}",
            "",
            f"- 文件名：{item.get('filename')}",
            f"- 类型：{item.get('media_type')} / {item.get('source_type')}",
            f"- 生命周期：{item.get('lifecycle')}",
            f"- 时长：{item.get('duration_sec')}",
            f"- 分辨率：{item.get('width')} x {item.get('height')}",
            f"- Live Photo：{item.get('live_photo_status')} / {item.get('live_photo_role')}",
            f"- 质量标记：{', '.join(item.get('quality_flags') or []) or '无'}",
            f"- Raw 判别原因：{', '.join(item.get('raw_decision_tokens') or []) or '无'}",
            f"- 判别备注：{', '.join(item.get('decision_notes') or []) or '无'}",
            f"- 关键帧：{keyframes}",
            "",
        ]
    )


def l3_structure_prompt(
    project: Path,
    manifest: dict[str, object],
    include_derived: bool,
    similarity_groups: list[list[dict[str, object]]],
    similarity_pairs: list[dict[str, object]],
    user_intent_notes: str,
) -> str:
    items = [
        item
        for item in manifest["items"]
        if eligible_item(item, include_derived=include_derived) or item.get("lifecycle") == "raw_or_pending"
    ]
    body = "\n".join(l3_structure_item_block(item) for item in items)
    similarity_section = visual_similarity_markdown(similarity_groups, similarity_pairs)
    intent_section = f"## 用户/创作者意图笔记\n\n{user_intent_notes}\n\n"
    return f"{L3_STRUCTURE_PROMPT_HEADER}- 项目绝对路径：{project}\n- 素材数量：{len(items)}\n\n{intent_section}{similarity_section}\n## 项目素材清单\n\n{body}"


def keyframe_block(item: dict[str, object]) -> str:
    frames = item.get("keyframes") or []
    if not frames:
        return "无。请先运行 02_extract_keyframes.py，或仅根据素材信息保守判断。"
    return "\n".join(f"- {frame}" for frame in frames)


def item_prompt_path(prompt_dir: Path, item: dict[str, object]) -> Path:
    return prompt_dir / f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}_prompt.md"


def prune_stale_prompts(prompt_dir: Path, expected: set[Path]) -> int:
    removed = 0
    for path in prompt_dir.glob("*_prompt.md"):
        if path not in expected and path.is_file():
            path.unlink()
            removed += 1
    return removed


def render_template(text: str, project: Path) -> str:
    manifest_path = project / "_ai_analysis" / "media_manifest.json"
    return (
        text.replace("{{PROJECT_DIR}}", str(project))
        .replace("{{MANIFEST_PATH}}", str(manifest_path))
        .replace("{{ANALYSIS_DIR}}", str(project / "_ai_analysis"))
    )


def load_user_intent_notes(project: Path) -> str:
    notes_path = project / USER_INTENT_NOTES
    if not notes_path.exists():
        return f"暂无。可在 `{USER_INTENT_NOTES}` 中记录用户明确说过的素材意图。"
    text = notes_path.read_text(encoding="utf-8").strip()
    return text or f"`{USER_INTENT_NOTES}` 为空。"


def write_workflow_prompts(project: Path, prompt_dir: Path) -> int:
    template_dir = Path(__file__).resolve().parent / "prompt_templates"
    output_dir = prompt_dir / "workflows"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not template_dir.exists():
        return 0

    templates = sorted(path for path in template_dir.glob("*.md") if path.name != "README.md")
    expected = {output_dir / path.name for path in templates}
    for old in output_dir.glob("*.md"):
        if old not in expected:
            old.unlink()
    for template in templates:
        output = output_dir / template.name
        output.write_text(render_template(template.read_text(encoding="utf-8"), project), encoding="utf-8")
    return len(templates)


def main() -> None:
    parser = argparse.ArgumentParser(description="为每个素材生成 AI 分析 prompt")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--include-derived", action="store_true", help="同时为 80/91 等派生目录中的媒体生成 prompt")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    prompt_dir = project / "_ai_analysis" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    user_intent_notes = load_user_intent_notes(project)

    expected_prompts = {
        item_prompt_path(prompt_dir, item)
        for item in manifest["items"]
        if eligible_item(item, include_derived=args.include_derived)
    }
    expected_prompts.add(prompt_dir / "project_overview_prompt.md")
    expected_prompts.add(prompt_dir / "project_l3_structure_prompt.md")
    pruned = prune_stale_prompts(prompt_dir, expected_prompts)

    count = 0
    for item in manifest["items"]:
        if not eligible_item(item, include_derived=args.include_derived):
            continue
        output_file = item_prompt_path(prompt_dir, item)
        prompt = PROMPT_TEMPLATE.format(
            filename=item.get("filename"),
            relative_path=item.get("relative_path"),
            media_type=item.get("media_type"),
            source_type=item.get("source_type"),
            lifecycle=item.get("lifecycle"),
            size_mb=item.get("size_mb"),
            duration_sec=item.get("duration_sec"),
            width=item.get("width"),
            height=item.get("height"),
            has_audio=item.get("has_audio"),
            live_photo_status=item.get("live_photo_status"),
            location_raw=item.get("location_raw"),
            gps_latitude=item.get("gps_latitude"),
            gps_longitude=item.get("gps_longitude"),
            gps_horizontal_accuracy=item.get("gps_horizontal_accuracy"),
            quality_flags=", ".join(item.get("quality_flags") or []) or "无",
            raw_decision_tokens=", ".join(item.get("raw_decision_tokens") or []) or "无",
            decision_notes=", ".join(item.get("decision_notes") or []) or "无",
            keyframe_count=item.get("keyframe_count", 0),
            keyframe_dir=item.get("keyframe_dir", "无"),
            user_intent_notes=user_intent_notes,
            keyframes=keyframe_block(item),
            card_schema=CARD_SCHEMA,
        )
        output_file.write_text(prompt, encoding="utf-8")
        count += 1

    l3_items = [
        item
        for item in manifest["items"]
        if eligible_item(item, include_derived=args.include_derived) or item.get("lifecycle") == "raw_or_pending"
    ]
    similarity_groups, similarity_pairs = visual_similarity_groups(project, l3_items)
    (project / "_ai_analysis" / "visual_similarity_groups.md").write_text(
        visual_similarity_markdown(similarity_groups, similarity_pairs),
        encoding="utf-8",
    )

    (prompt_dir / "project_overview_prompt.md").write_text(
        PROJECT_PROMPT.format(user_intent_notes=user_intent_notes),
        encoding="utf-8",
    )
    (prompt_dir / "project_l3_structure_prompt.md").write_text(
        l3_structure_prompt(project, manifest, args.include_derived, similarity_groups, similarity_pairs, user_intent_notes),
        encoding="utf-8",
    )
    workflow_count = write_workflow_prompts(project, prompt_dir)
    print(f"Prompt 已生成：{prompt_dir}，共 {count} 个素材 prompt，workflow prompts {workflow_count} 个，清理陈旧 prompt {pruned} 个")


if __name__ == "__main__":
    main()
