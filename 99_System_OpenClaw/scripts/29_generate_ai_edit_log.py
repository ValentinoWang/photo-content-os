#!/usr/bin/env python3
"""Generate an AI-assisted Content OS edit log from script, EDL, and roughcut artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from llm_common import (
    DEFAULT_CREATIVE_MODEL,
    DEFAULT_REASONING_EFFORT,
    generate_text,
    load_creator_context,
    parse_markdown_frontmatter_or_empty,
)


MAX_TEXT_CHARS = 14000
MAX_JSON_CHARS = 16000


class EditLogError(Exception):
    """Raised when the edit log contract cannot be satisfied."""


SYSTEM_PROMPT = """你是 Mac OpenClaw 的 AI 跟剪日志代理。

目标：根据项目脚本、分镜、EDL、剪映原生导入包计划/结果、可选人工备注和可选成片信息，生成 07_edit_log.md。

硬约束：
1. 你只能把输入中明确出现的事实写成“已确认人工修改”。
2. 你可以根据内容结构提出“AI 建议修改”和“AI 推断修改”，但必须标注确认状态或置信度。
3. 不允许编造已经添加的 BGM、音效、特效、变速、贴纸、转场、调色或删除动作。
4. 如果没有 V1/Final 成片或剪映草稿解析证据，所有“已经发生”的操作必须保持空表或 pending_confirm。
5. 允许根据脚本/EDL/导入包内容建议节奏、变速、卡点、字幕强调、音效和 BGM 方向。
6. 结果必须是完整 Markdown，必须包含 YAML frontmatter。
7. frontmatter 必须包含 spec_version、doc_type、project_id、idea_id、status、writer_agent、owner_agent、next_owner、generation_model、generation_reasoning、evidence_level。
8. doc_type 必须是 edit_log；writer_agent 必须是 mac_openclaw。
9. evidence_level 只能是 content_plan_only、output_video_reviewed、jianying_draft_parsed、human_confirmed 中的一个。当前没有成片/草稿解析/人确认时用 content_plan_only。
10. 正文必须包含这些一级标题：AI 跟剪摘要、已确认人工修改、AI 建议修改、AI 推断修改、需要人确认、下一版建议、记录规则。
11. creator_context 只包含项目明确提供的账号、人设、口吻、平台、受众和题材边界；它只能约束建议的表达方式，不能证明素材或剪辑事实。未提供的字段不得猜测。
12. 不要输出 Markdown 代码围栏，不要解释生成过程，不要输出额外寒暄。"""


def read_text(path: Path, *, limit: int = MAX_TEXT_CHARS) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + "\n\n[TRUNCATED]\n"
    return text


def load_json_text(path: Path, *, limit: int = MAX_JSON_CHARS) -> str:
    if not path.exists() or path.stat().st_size == 0:
        return ""
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > limit:
        return text[:limit] + "\n\n[TRUNCATED]\n"
    return text


def parse_frontmatter(text: str) -> dict[str, Any]:
    return parse_markdown_frontmatter_or_empty(text)


def ffprobe_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise EditLogError(f"video path does not exist: {path}")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
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
        raise EditLogError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return {"path": str(path), "ffprobe": data}


def project_file(project_package: Path, name: str) -> Path:
    return project_package / name


def collect_context(
    *,
    project_package: Path,
    output: Path,
    human_notes: Path | None,
    video: Path | None,
    model: str,
    reasoning: str,
) -> dict[str, Any]:
    index_text = read_text(project_file(project_package, "00_项目总览.md"))
    index_meta = parse_frontmatter(index_text)
    creator_context = load_creator_context(project_package, brief_text=index_text)
    script_text = read_text(project_file(project_package, "04_script.md"))
    if not script_text:
        raise EditLogError(f"required source missing or empty: {project_file(project_package, '04_script.md')}")
    edl_text = load_json_text(project_file(project_package, "06_edit_decision_list.json"))
    if not edl_text:
        raise EditLogError(f"required source missing or empty: {project_file(project_package, '06_edit_decision_list.json')}")

    return {
        "project_package": str(project_package),
        "output_path": str(output),
        "project_id": index_meta.get("project_id") or project_package.name,
        "idea_id": index_meta.get("idea_id") or "",
        "generation_model": model,
        "generation_reasoning": reasoning,
        "creator_context": creator_context,
        "existing_edit_log_markdown": read_text(output, limit=10000),
        "project_index_markdown": index_text,
        "material_match_report_markdown": read_text(project_file(project_package, "03_material_match_report.md"), limit=10000),
        "script_markdown": script_text,
        "storyboard_markdown": read_text(project_file(project_package, "05_storyboard.md"), limit=12000),
        "edit_decision_list_json": edl_text,
        "local_assets_markdown": read_text(project_file(project_package, "08_local_assets.md"), limit=8000),
        "jianying_draft_plan_json": load_json_text(project_file(project_package, "06b_jianying_draft_plan.json"), limit=12000),
        "native_import_pack_result_yaml": read_text(project_file(project_package, "06d_native_import_pack_result.yaml"), limit=10000),
        "roughcut_review_markdown": read_text(project_file(project_package, "11_roughcut_review.md"), limit=8000),
        "other_materials_plan_json": load_json_text(project_file(project_package, "06e_other_materials_edit_plan.json"), limit=12000),
        "other_materials_pack_result_yaml": read_text(project_file(project_package, "06f_other_materials_edit_pack_result.yaml"), limit=10000),
        "other_materials_review_markdown": read_text(project_file(project_package, "11b_other_materials_edit_pack_review.md"), limit=8000),
        "human_notes_markdown": read_text(human_notes, limit=8000) if human_notes else "",
        "output_video_probe": ffprobe_summary(video) if video else {},
    }


def build_user_prompt(context: dict[str, Any]) -> str:
    return "请根据以下 JSON 上下文生成 07_edit_log.md：\n\n" + json.dumps(context, ensure_ascii=False, indent=2)


def validate_markdown(text: str, *, project_id: str, model: str, reasoning: str) -> None:
    if not text.strip():
        raise EditLogError("edit log output is empty")
    if text.strip().startswith("```"):
        raise EditLogError("edit log output must be raw Markdown, not a code fence")
    meta = parse_frontmatter(text)
    required_meta = {
        "spec_version": "content_os_v0.1",
        "doc_type": "edit_log",
        "project_id": project_id,
        "writer_agent": "mac_openclaw",
        "generation_model": model,
        "generation_reasoning": reasoning,
    }
    for key, expected in required_meta.items():
        if meta.get(key) != expected:
            raise EditLogError(f"frontmatter {key} must be {expected!r}")
    if meta.get("evidence_level") not in {
        "content_plan_only",
        "output_video_reviewed",
        "jianying_draft_parsed",
        "human_confirmed",
    }:
        raise EditLogError("frontmatter evidence_level is invalid")
    for heading in [
        "# AI 跟剪摘要",
        "# 已确认人工修改",
        "# AI 建议修改",
        "# AI 推断修改",
        "# 需要人确认",
        "# 下一版建议",
        "# 记录规则",
    ]:
        if heading not in text:
            raise EditLogError(f"required heading missing: {heading}")


def generate(
    *,
    project_package: Path,
    output: Path,
    human_notes: Path | None,
    video: Path | None,
    model: str,
    reasoning: str,
    prompt_output: Path | None,
    allow_overwrite: bool,
) -> None:
    if not project_package.exists() or not project_package.is_dir():
        raise EditLogError(f"project package does not exist: {project_package}")
    if output.exists() and output.stat().st_size > 0 and not allow_overwrite:
        raise EditLogError(f"output already exists; pass --allow-overwrite to replace: {output}")

    context = collect_context(
        project_package=project_package,
        output=output,
        human_notes=human_notes,
        video=video,
        model=model,
        reasoning=reasoning,
    )
    user_prompt = build_user_prompt(context)
    if prompt_output:
        prompt_output.parent.mkdir(parents=True, exist_ok=True)
        prompt_output.write_text(f"{SYSTEM_PROMPT}\n\n--- USER CONTEXT ---\n\n{user_prompt}\n", encoding="utf-8")
    markdown = generate_text(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=model,
        reasoning_effort=reasoning,
    ).strip()
    validate_markdown(markdown, project_id=str(context["project_id"]), model=model, reasoning=reasoning)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-package", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--human-notes", type=Path)
    parser.add_argument("--video", type=Path, help="Optional V1/V2/Final export for metadata-level evidence.")
    parser.add_argument("--model", default=DEFAULT_CREATIVE_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--prompt-output", type=Path)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    generate(
        project_package=args.project_package.expanduser().resolve(),
        output=args.output.expanduser().resolve(),
        human_notes=args.human_notes.expanduser().resolve() if args.human_notes else None,
        video=args.video.expanduser().resolve() if args.video else None,
        model=args.model,
        reasoning=args.reasoning,
        prompt_output=args.prompt_output.expanduser().resolve() if args.prompt_output else None,
        allow_overwrite=args.allow_overwrite,
    )
    print(f"edit_log={args.output.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
