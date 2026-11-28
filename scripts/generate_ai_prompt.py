#!/usr/bin/env python3
"""Generate per-media AI analysis prompts from the manifest and keyframes."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm import creator_context_block
from media import (
    ANALYSIS_DIR,
    PROMPT_GLOB,
    analysis_dir,
    eligible_item,
    item_prompt_path,
    load_manifest,
    manifest_path as manifest_json_path,
    project_path,
    prompts_dir,
)

if __package__:
    from .constants import (
        VISUAL_SIMILARITY_THRESHOLD,
        USER_INTENT_NOTES,
        CARD_SCHEMA,
        PROMPT_TEMPLATE,
        PROJECT_PROMPT,
        L3_STRUCTURE_PROMPT_HEADER,
    )
else:
    from constants import (
        VISUAL_SIMILARITY_THRESHOLD,
        USER_INTENT_NOTES,
        CARD_SCHEMA,
        PROMPT_TEMPLATE,
        PROJECT_PROMPT,
        L3_STRUCTURE_PROMPT_HEADER,
    )






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
    creator_context: str = "",
) -> str:
    items = [
        item
        for item in manifest["items"]
        if eligible_item(item, include_derived=include_derived) or item.get("lifecycle") == "raw_or_pending"
    ]
    body = "\n".join(l3_structure_item_block(item) for item in items)
    similarity_section = visual_similarity_markdown(similarity_groups, similarity_pairs)
    intent_section = f"## 用户/创作者意图笔记\n\n{user_intent_notes}\n\n"
    context_section = f"## 账号上下文\n\n{creator_context or '项目未提供账号人设资料；不得自行猜测。'}\n\n"
    return f"{L3_STRUCTURE_PROMPT_HEADER}- 项目绝对路径：{project}\n- 素材数量：{len(items)}\n\n{intent_section}{context_section}{similarity_section}\n## 项目素材清单\n\n{body}"


def keyframe_block(item: dict[str, object]) -> str:
    frames = item.get("keyframes") or []
    if not frames:
        return "无。请先运行 extract_keyframes.py，或仅根据素材信息保守判断。"
    return "\n".join(f"- {frame}" for frame in frames)


def prune_stale_prompts(prompt_dir: Path, expected: set[Path]) -> int:
    removed = 0
    for path in prompt_dir.glob(PROMPT_GLOB):
        if path not in expected and path.is_file():
            path.unlink()
            removed += 1
    return removed


def render_template(text: str, project: Path, creator_context: str = "") -> str:
    rendered = (
        text.replace("{{PROJECT_DIR}}", str(project))
        .replace("{{MANIFEST_PATH}}", str(manifest_json_path(project)))
        .replace("{{ANALYSIS_DIR}}", str(analysis_dir(project)))
    )
    context = creator_context or creator_context_block(project)
    return f"## 当前账号上下文\n\n{context}\n\n{rendered}"


def load_user_intent_notes(project: Path) -> str:
    notes_path = project / USER_INTENT_NOTES
    if not notes_path.exists():
        return f"暂无。可在 `{USER_INTENT_NOTES}` 中记录用户明确说过的素材意图。"
    text = notes_path.read_text(encoding="utf-8").strip()
    return text or f"`{USER_INTENT_NOTES}` 为空。"


def write_workflow_prompts(project: Path, prompt_dir: Path, creator_context: str = "") -> int:
    template_dir = Path(__file__).resolve().parent / "prompt-templates"
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
        output.write_text(render_template(template.read_text(encoding="utf-8"), project, creator_context), encoding="utf-8")
    return len(templates)


def main() -> None:
    parser = argparse.ArgumentParser(description="为每个素材生成 AI 分析 prompt")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--include-derived", action="store_true", help="同时为 80/91 等派生目录中的媒体生成 prompt")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    prompt_dir = prompts_dir(project)
    prompt_dir.mkdir(parents=True, exist_ok=True)
    user_intent_notes = load_user_intent_notes(project)
    creator_context = creator_context_block(project)

    expected_prompts = {
        item_prompt_path(prompt_dir, item)
        for item in manifest["items"]
        if eligible_item(item, include_derived=args.include_derived)
    }
    expected_prompts.add(prompt_dir / "project-overview-prompt.md")
    expected_prompts.add(prompt_dir / "project-l3-structure-prompt.md")
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
            creator_context=creator_context,
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
    (analysis_dir(project) / "visual-similarity-groups.md").write_text(
        visual_similarity_markdown(similarity_groups, similarity_pairs),
        encoding="utf-8",
    )

    (prompt_dir / "project-overview-prompt.md").write_text(
        PROJECT_PROMPT.format(user_intent_notes=user_intent_notes, creator_context=creator_context),
        encoding="utf-8",
    )
    (prompt_dir / "project-l3-structure-prompt.md").write_text(
        l3_structure_prompt(project, manifest, args.include_derived, similarity_groups, similarity_pairs, user_intent_notes, creator_context),
        encoding="utf-8",
    )
    workflow_count = write_workflow_prompts(project, prompt_dir, creator_context)
    print(f"Prompt 已生成：{prompt_dir}，共 {count} 个素材 prompt，workflow prompts {workflow_count} 个，清理陈旧 prompt {pruned} 个")


if __name__ == "__main__":
    main()
