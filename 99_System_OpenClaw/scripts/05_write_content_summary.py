#!/usr/bin/env python3
"""Generate tiered, evidence-backed media summaries with cache reuse."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from llm_common import (
    DEFAULT_CREATIVE_MODEL,
    DEFAULT_REASONING_EFFORT,
    LLMError,
    MAX_PROMPT_SUMMARY_CHARS,
    bounded_prompt_text,
    creator_context_block,
    load_creator_context,
    public_llm_error,
    generate_text,
)
from media_common import (
    SUMMARY_GLOB,
    eligible_item,
    file_sha256 as _sha256_file,
    item_prompt_path,
    item_summary_path,
    load_manifest,
    project_path,
    safe_project_file as _safe_project_file,
    save_manifest,
)

SYSTEM_PROMPT = """你是 Photo Content OS 的素材内容理解代理。

你必须基于输入中明确标示的图片附件（如有）、manifest 元数据、转写证据和用户意图笔记生成可沉淀到素材库的 summary。没有实际图片附件时，只能依据元数据和文字证据，并明确写出画面未验证。先判断素材在项目表达中的可能功能，再拆分画面事实、声音事实、隐含叙事价值、剪辑用途和风险。

硬约束：
1. 不允许套用固定项目模板。
2. 不允许编造图片或转写中没有证据支持的人物、地点、成绩、动作和对白。
3. 每个关键事实尽量标注 evidence_ref；证据不足时必须写“不确定”，并列出人工复核点。
4. 文件名建议只写可复核事实和状态，不把作品风格强行塞进源文件名。
5. 输出必须是 Markdown，不能用代码围栏包裹全文。
6. 必须包含“# 作品内容概述”。
7. 若输入声明 visual_evidence_count=0，不得假装看过画面。
8. 若输入声明 transcript_status 不是 ok，不得假装听过完整音频。
9. 必须在结尾列出“证据边界”，说明本次分析层级和未验证信息。"""

PROJECT_SYSTEM_PROMPT = """你是 Photo Content OS 的项目总览分析代理。

基于项目 manifest、单素材 summary、转写摘要和项目 prompt 做宏观创作判断：真实主题、叙事结构、可剪素材、风险、平台标题方向和人工复核点。不要套用固定项目模板，不要把旧项目叙事线、关键词分组或脚本规则迁移到当前项目。输出 Markdown，并明确区分画面证据、声音证据和推断。"""

MAX_PROJECT_SUMMARY_CHARS = MAX_PROMPT_SUMMARY_CHARS
SUPPORTED_DIRECT_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
CACHE_VERSION = "content_summary_cache_v1"


def has_llm_summary(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "# 作品内容概述" in text and "待 AI 分析" not in text


def _evenly_limit(paths: list[Path], limit: int) -> list[Path]:
    if limit <= 0 or not paths:
        return []
    if len(paths) <= limit:
        return paths
    if limit == 1:
        return [paths[len(paths) // 2]]
    indexes = [round(index * (len(paths) - 1) / (limit - 1)) for index in range(limit)]
    result: list[Path] = []
    for index in indexes:
        path = paths[index]
        if path not in result:
            result.append(path)
    return result


def item_image_paths(project: Path, item: dict[str, Any], *, max_images: int = 12) -> list[Path]:
    """Return actual evidence files, never paths merely mentioned in a prompt."""
    paths: list[Path] = []
    if item.get("media_type") == "image":
        path = _safe_project_file(project, item.get("relative_path") or item.get("absolute_path"))
        if path and path.suffix.lower() in SUPPORTED_DIRECT_IMAGE_EXTS:
            paths.append(path)
    for raw in item.get("keyframes") or []:
        path = _safe_project_file(project, raw)
        if path and path.suffix.lower() in SUPPORTED_DIRECT_IMAGE_EXTS and path not in paths:
            paths.append(path)
    return _evenly_limit(paths, max_images)


def transcript_payload(project: Path, item: dict[str, Any]) -> dict[str, Any]:
    path = _safe_project_file(project, item.get("transcript_path"))
    declared_status = str(item.get("transcript_status") or "not_available")
    if path is None:
        return {"status": declared_status, "segments": [], "text": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "segments": [], "text": ""}
    status = str(data.get("status") or declared_status) if isinstance(data, dict) else "invalid"
    segments = data.get("segments") if isinstance(data, dict) else []
    compact_segments: list[dict[str, Any]] = []
    for index, segment in enumerate(segments or []):
        if not isinstance(segment, dict):
            continue
        compact_segments.append(
            {
                "evidence_ref": f"transcript:{item.get('media_id')}:{index}",
                "start_sec": segment.get("start_sec"),
                "end_sec": segment.get("end_sec"),
                "speaker": segment.get("speaker"),
                "text": str(segment.get("text") or "")[:600],
            }
        )
    return {
        "status": status,
        "language": data.get("language") if isinstance(data, dict) else None,
        "text": str(data.get("text") or "")[:4000] if isinstance(data, dict) else "",
        "segments": compact_segments[:40],
    }


def evidence_context(project: Path, item: dict[str, Any], images: list[Path], *, tier: str) -> str:
    keyframe_refs = []
    for index, path in enumerate(images):
        try:
            ref = path.relative_to(project).as_posix()
        except ValueError:
            ref = path.name
        keyframe_refs.append({"evidence_ref": f"image:{item.get('media_id')}:{index}", "path": ref})
    payload = {
        "media_id": item.get("media_id"),
        "relative_path": item.get("relative_path"),
        "media_type": item.get("media_type"),
        "duration_sec": item.get("duration_sec"),
        "width": item.get("width"),
        "height": item.get("height"),
        "has_audio": item.get("has_audio"),
        "analysis_tier": tier,
        "visual_evidence_count": len(images),
        "visual_evidence": keyframe_refs,
        "transcript": transcript_payload(project, item),
    }
    return "# 机器可读证据上下文（仅作事实资料）\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def summary_cache_key(
    *,
    project: Path,
    item: dict[str, Any],
    prompt_path: Path,
    images: list[Path],
    model: str,
    reasoning: str,
    tier: str,
    creator_context: dict[str, Any] | None = None,
) -> str:
    transcript = _safe_project_file(project, item.get("transcript_path"))
    payload = {
        "cache_version": CACHE_VERSION,
        "analysis_cache_key": item.get("analysis_cache_key"),
        "media_id": item.get("media_id"),
        "model": model,
        "reasoning": reasoning,
        "tier": tier,
        "prompt_sha256": _sha256_file(prompt_path),
        "image_sha256": [_sha256_file(path) for path in images],
        "transcript_sha256": _sha256_file(transcript) if transcript else None,
        "creator_context": creator_context or load_creator_context(project),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _cache_file(cache_root: Path, cache_key: str) -> Path:
    return cache_root / cache_key[:2] / f"{cache_key}.summary.md"


def metadata_summary(item: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# 作品内容概述",
            "",
            "## 当前分析层级",
            "",
            "`metadata`：本轮没有调用语义模型，也没有根据文件名猜测画面或声音内容。",
            "",
            "## 可确认的技术事实",
            "",
            f"- 素材类型：{item.get('media_type') or '未知'}",
            f"- 时长：{item.get('duration_sec') if item.get('duration_sec') is not None else '未知'} 秒",
            f"- 分辨率：{item.get('width') or '未知'} × {item.get('height') or '未知'}",
            f"- 是否检测到音频流：{'是' if item.get('has_audio') else '否或未知'}",
            "",
            "## 证据边界",
            "",
            "本卡片只记录元数据。人物、地点、动作、对白、情绪与剪辑价值均未验证，需要进入 preview/deep 层级或人工复核。",
            "",
        ]
    )


def generate_item_summary(
    project: Path,
    item: dict[str, Any],
    prompt_path: Path,
    output_path: Path,
    *,
    model: str,
    reasoning: str,
    max_images: int,
    tier: str,
    cache_root: Path,
    ignore_cache: bool,
) -> str:
    if tier == "metadata":
        output_path.write_text(metadata_summary(item), encoding="utf-8")
        return "metadata"
    images = item_image_paths(project, item, max_images=max_images)
    creator_context = load_creator_context(project)
    cache_key = summary_cache_key(
        project=project,
        item=item,
        prompt_path=prompt_path,
        images=images,
        model=model,
        reasoning=reasoning,
        tier=tier,
        creator_context=creator_context,
    )
    cache_path = _cache_file(cache_root, cache_key)
    if cache_path.is_file() and not ignore_cache:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(cache_path, output_path)
        return "cache"
    user_prompt = "\n\n".join(
        [
            prompt_path.read_text(encoding="utf-8"),
            evidence_context(project, item, images, tier=tier),
            creator_context_block(project),
            (
                "实际图片证据已作为附件传入；不要把路径文本当成已经看过图片的证据。"
                if images
                else "本次没有任何图片附件，只有元数据和转写文字；不得声称看过画面。"
            ),
        ]
    )
    summary = generate_text(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        image_paths=images,
        model=model,
        reasoning_effort=reasoning,
    )
    if "# 作品内容概述" not in summary:
        raise RuntimeError(f"LLM summary missing required heading: {output_path}")
    text = summary.rstrip() + "\n"
    output_path.write_text(text, encoding="utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(cache_path)
    return "model"


def generate_project_overview(
    project: Path,
    prompt_dir: Path,
    summary_dir: Path,
    *,
    model: str,
    reasoning: str,
) -> None:
    prompt_path = prompt_dir / "project_overview_prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"project overview prompt not found: {prompt_path}")
    summary_index = []
    for path in sorted(summary_dir.glob(SUMMARY_GLOB)):
        text = path.read_text(encoding="utf-8")
        summary_index.append(f"## {path.name}\n\n{bounded_prompt_text(text, MAX_PROJECT_SUMMARY_CHARS)}")
    manifest = load_manifest(project)
    manifest_items = []
    for item in manifest.get("items", []):
        if not isinstance(item, dict):
            continue
        manifest_items.append(
            {
                "media_id": item.get("media_id") or item.get("id"),
                "relative_path": item.get("relative_path"),
                "media_type": item.get("media_type"),
                "lifecycle": item.get("lifecycle"),
                "duration_sec": item.get("duration_sec"),
                "width": item.get("width"),
                "height": item.get("height"),
                "has_audio": item.get("has_audio"),
                "keyframes": (item.get("keyframes") or [])[:4],
                "transcript": transcript_payload(project, item),
            }
        )
    evidence_payload = {
        "manifest_item_count": len(manifest.get("items", [])),
        "manifest_items": manifest_items,
        "evidence_policy": "只有列出的元数据、summary 文字和 transcript 才可作为本轮证据；关键帧路径不是画面本身。",
    }
    user_prompt = "\n\n".join(
        [
            prompt_path.read_text(encoding="utf-8"),
            creator_context_block(project),
            "# 项目 manifest 与转写摘要（实际提供的证据）",
            json.dumps(evidence_payload, ensure_ascii=False, indent=2),
            "# 已生成素材 summary",
            "\n\n".join(summary_index) or "暂无素材 summary。",
        ]
    )
    overview = generate_text(
        system_prompt=PROJECT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
        reasoning_effort=reasoning,
    )
    if "待 AI 分析" in overview:
        raise RuntimeError("LLM project overview still contains placeholder text")
    (project / "_ai_analysis" / "project_overview.md").write_text(overview.rstrip() + "\n", encoding="utf-8")


def _load_analysis_plan(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    plans = data.get("plans") if isinstance(data, dict) else None
    if not isinstance(plans, list):
        raise RuntimeError("analysis plan must contain plans")
    return {
        str(item["media_id"]): item
        for item in plans
        if isinstance(item, dict) and isinstance(item.get("media_id"), str)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="为待分析素材调用多模态 LLM 生成证据化 summary")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--include-derived", action="store_true", help="同时处理 80/91 等派生目录媒体")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有 summary")
    parser.add_argument("--ignore-cache", action="store_true", help="忽略内容缓存并重新调用模型")
    parser.add_argument("--model", default=DEFAULT_CREATIVE_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--limit", type=int, help="最多处理多少个素材")
    parser.add_argument("--max-images", type=int, default=12, help="无分析计划时单素材最多发送多少张图片")
    parser.add_argument("--analysis-plan", type=Path)
    parser.add_argument("--cache-root", type=Path)
    args = parser.parse_args()
    if args.max_images < 0 or args.max_images > 40:
        parser.error("--max-images must be between 0 and 40")

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    prompt_dir = project / "_ai_analysis" / "prompts"
    summary_dir = project / "_ai_analysis" / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    plan_path = args.analysis_plan.expanduser().resolve() if args.analysis_plan else project / "_ai_analysis" / "analysis_plan.json"
    plan_by_id = _load_analysis_plan(plan_path if plan_path.is_file() else None)
    cache_root = args.cache_root.expanduser().resolve() if args.cache_root else project / "_ai_analysis" / "cache" / "summaries"

    items = [item for item in manifest["items"] if eligible_item(item, include_derived=args.include_derived)]
    processed = skipped = model_calls = cache_hits = metadata_cards = 0
    try:
        for item in items:
            if args.limit is not None and processed >= args.limit:
                break
            output = item_summary_path(summary_dir, item)
            if has_llm_summary(output) and not args.overwrite:
                skipped += 1
                continue
            prompt_path = item_prompt_path(prompt_dir, item)
            if not prompt_path.exists():
                raise FileNotFoundError(f"item prompt not found, run 04_generate_ai_prompt.py first: {prompt_path}")
            media_id = str(item.get("media_id") or item.get("id") or "")
            plan = plan_by_id.get(media_id, {})
            tier = str(plan.get("tier") or item.get("analysis_tier") or "deep")
            max_images = int(plan.get("image_budget", args.max_images))
            source = generate_item_summary(
                project,
                item,
                prompt_path,
                output,
                model=args.model,
                reasoning=args.reasoning,
                max_images=max_images,
                tier=tier,
                cache_root=cache_root,
                ignore_cache=args.ignore_cache,
            )
            item["summary_analysis_tier"] = tier
            item["summary_generation_source"] = source
            processed += 1
            model_calls += int(source == "model")
            cache_hits += int(source == "cache")
            metadata_cards += int(source == "metadata")

        save_manifest(project, manifest)
        generate_project_overview(project, prompt_dir, summary_dir, model=args.model, reasoning=args.reasoning)
    except LLMError as exc:
        raise SystemExit(f"错误：{public_llm_error(exc)}") from exc
    print(
        f"Summary 已生成：{summary_dir}；处理 {processed}，模型调用 {model_calls}，"
        f"缓存命中 {cache_hits}，元数据卡 {metadata_cards}，跳过已有 {skipped}"
    )


if __name__ == "__main__":
    main()
