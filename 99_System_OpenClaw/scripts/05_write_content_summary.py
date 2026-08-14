#!/usr/bin/env python3
"""Generate media summaries with gpt-5.5/xhigh."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm_common import DEFAULT_CREATIVE_MODEL, DEFAULT_REASONING_EFFORT, generate_text
from media_common import eligible_item, load_manifest, project_path, safe_slug


SYSTEM_PROMPT = """你是 Mac OpenClaw 的素材内容理解代理。

你要基于素材 prompt、manifest 元数据、关键帧文件名和用户意图笔记生成可沉淀到素材库的内容 summary。必须保持宏观判断能力：先判断素材在项目表达中的可能功能，再拆分画面事实、隐含叙事价值、剪辑用途和风险。判断不能来自脚本内置分类、关键词匹配或固定项目模板。

硬约束：
1. 不允许套用固定项目模板。
2. 不允许编造关键帧中没有证据支持的人物、地点、成绩或动作。
3. 如果仅有文件名和关键帧路径，无法确认画面内容时，必须写“不确定”并列出需要人工复核的证据。
4. 文件名建议只写画面事实和可复核状态，不把作品风格强行塞进 L3 源文件名。
5. 输出必须是 Markdown，不能用代码围栏。
6. 必须包含“# 作品内容概述”，并按输入 prompt 要求输出完整卡片。"""


PROJECT_SYSTEM_PROMPT = """你是 Mac OpenClaw 的项目总览分析代理。

你要基于项目 manifest、单素材 summary 和项目 prompt 做宏观创作判断：项目真实主题、叙事结构、可剪素材、风险、平台标题方向和人工复核点。不要套用固定项目模板，不要把旧项目叙事线、关键词分组或脚本规则迁移到当前项目。输出 Markdown。"""


def item_prompt_path(prompt_dir: Path, item: dict[str, object]) -> Path:
    return prompt_dir / f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}_prompt.md"


def summary_path(summary_dir: Path, item: dict[str, object]) -> Path:
    return summary_dir / f"{item['media_id']}_{safe_slug(Path(str(item['relative_path'])).stem)}.summary.md"


def has_llm_summary(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return "# 作品内容概述" in text and "待 AI 分析" not in text


def generate_item_summary(prompt_path: Path, output_path: Path, *, model: str, reasoning: str) -> None:
    prompt = prompt_path.read_text(encoding="utf-8")
    summary = generate_text(system_prompt=SYSTEM_PROMPT, user_prompt=prompt, model=model, reasoning_effort=reasoning)
    if "# 作品内容概述" not in summary:
        raise RuntimeError(f"LLM summary missing required heading: {output_path}")
    output_path.write_text(summary.rstrip() + "\n", encoding="utf-8")


def generate_project_overview(project: Path, prompt_dir: Path, summary_dir: Path, *, model: str, reasoning: str) -> None:
    prompt_path = prompt_dir / "project_overview_prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"project overview prompt not found: {prompt_path}")
    summary_index = []
    for path in sorted(summary_dir.glob("*.summary.md")):
        text = path.read_text(encoding="utf-8")
        summary_index.append(f"## {path.name}\n\n{text[:1600]}")
    user_prompt = "\n\n".join(
        [
            prompt_path.read_text(encoding="utf-8"),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="为每个待分析素材调用 LLM 生成 summary")
    parser.add_argument("project_dir", help="项目文件夹路径")
    parser.add_argument("--include-derived", action="store_true", help="同时为 80/91 等派生目录中的媒体生成 summary")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有 LLM summary")
    parser.add_argument("--model", default=DEFAULT_CREATIVE_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--limit", type=int, help="最多生成多少个素材 summary，主要用于人工分批运行")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    manifest = load_manifest(project)
    prompt_dir = project / "_ai_analysis" / "prompts"
    summary_dir = project / "_ai_analysis" / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)

    items = [item for item in manifest["items"] if eligible_item(item, include_derived=args.include_derived)]
    generated = 0
    skipped = 0
    for item in items:
        if args.limit is not None and generated >= args.limit:
            break
        output = summary_path(summary_dir, item)
        if has_llm_summary(output) and not args.overwrite:
            skipped += 1
            continue
        prompt_path = item_prompt_path(prompt_dir, item)
        if not prompt_path.exists():
            raise FileNotFoundError(f"item prompt not found, run 04_generate_ai_prompt.py first: {prompt_path}")
        generate_item_summary(prompt_path, output, model=args.model, reasoning=args.reasoning)
        generated += 1

    generate_project_overview(project, prompt_dir, summary_dir, model=args.model, reasoning=args.reasoning)
    print(f"LLM Summary 已生成：{summary_dir}，新增/覆盖 {generated} 个，跳过已有 {skipped} 个")


if __name__ == "__main__":
    main()
