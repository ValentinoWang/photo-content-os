#!/usr/bin/env python3
"""Generate storyboard and canonical EDL from project evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from edl_contract import EDLContractError, normalise_edl, write_edl
from llm_common import (
    DEFAULT_CREATIVE_MODEL,
    DEFAULT_REASONING_EFFORT,
    MAX_PROMPT_SUMMARY_CHARS,
    creator_context_block,
    generate_text,
    load_creator_context,
    parse_json_response,
    parse_markdown_frontmatter,
    parse_markdown_frontmatter_or_empty,
    render_markdown_frontmatter,
)
from llm_evidence_context import (
    keyframe_evidence,
    nearby_script_path,
    read_text,
    summary_text as _shared_summary_text,
    transcript_segments as _shared_transcript_segments,
)
from media_common import eligible_item, is_raw360_item, load_manifest, project_path

MAX_ITEMS = 140
MAX_SUMMARY_CHARS = MAX_PROMPT_SUMMARY_CHARS
MAX_TRANSCRIPT_CHARS = 1600

SYSTEM_PROMPT = """你是 Photo Content OS 的短视频分镜与剪辑方案编排代理。

先判断项目真正要表达的内容类型、核心冲突、情绪曲线、平台观看动机和素材证据边界，再生成分镜与 EDL。不要套用固定模板，不要把旧项目表达、字幕、节奏或脚本规则搬到新项目。

硬约束：
1. 04_script.md 和明确提供的 creator_context 是强输入；creator_context 只约束账号口吻、平台与题材边界，不能覆盖素材事实。没有提供的人设、平台或受众不得猜测。只有真实素材证据不足时才把内容写入 missing_materials，不能硬凑。
2. 不允许编造素材、成绩、地点、人物关系、BGM、对白或镜头。
3. clips 中的 source_file/candidate_files 只能来自输入 manifest；不可执行的缺失素材不能进入 clips。
4. 输出必须是严格 JSON，顶层只有 storyboard_markdown 和 edl_json；优先输出裸 JSON，单个 ```json 围栏也会被解析器规范化。
5. storyboard_markdown 必须含 YAML frontmatter：doc_type=storyboard、writer_agent=mac_openclaw；generation_model、generation_reasoning 和 spec_version 由脚本写入，不要把它们当作内容事实。
6. edl_json 必须满足 edit_decision_list：doc_type=edit_decision_list、source_script_used=true、clips 非空。
7. 每个 clip 必须有唯一正整数 slot、字符串 time_range（如 0.000-4.000）、source_start_sec、purpose、visual_need、caption、candidate_files、edit_note。
7.1 每个 clip 还要写 role，取值只能是 a_roll（口播/对白主轴）、b_roll（盖跳切或可视化所讲内容的空镜）、overlay（叠加信息，如标题条）、title（片头片尾卡）。role 只描述这段素材在叙事里干什么，不决定它放在哪一轨。
7.2 layer 决定合成轨，取值只能是 primary、overlay、background。**默认全部留空（等同 primary），整条时间线保持单轨**；只有当分镜确实需要「画面同时出现两层」——例如口播继续出镜、右下角同时放一个小窗 B-roll——才把那一段写成 layer=overlay。role 和 layer 是两件事：全屏切走的空镜是 role=b_roll 且 layer=primary，同一段素材做小窗才是 layer=overlay。
7.3 写了任何非 primary 的 layer，这条 EDL 就只能由多轨后端渲染，剪映草稿和本地预览会明确拒绝。所以不确定时一律用 primary。
8. time_range 精确到毫秒。同一 layer 内必须按时间升序且不重叠；不同 layer 之间允许重叠（叠加层本来就压在主轴上）。primary 层必须从 0.000 开始、段与段首尾相接不留空隙，叠加层不能超出 primary 层的结束时间。
9. RawVault / 360 原始素材只证明视角存在，不能直接作为可剪片段；如使用必须先在 missing_materials 中要求转码/重构。
10. 你拿到的 keyframes 只有 evidence_ref 和帧路径，没有画面本身；视觉结论只能来自各素材 summary 里的分析文字，并回指对应 keyframes 的 evidence_ref。声音结论必须回指 transcript_segments。summary 和转写都支撑不了的视觉/声音断言，一律标记人工复核，不得凭路径名或文件名脑补画面内容。
11. 禁止把结果描述为脚本机械判定或临时版本生成。
12. caption 是最终上屏文字，不是镜头说明：一条不超过 14 个字，用观众能读出声的口语，补充画面没说出来的信息（情绪、代价、悬念），不复述画面里已经看得见的内容；整支视频的 caption 要有同一个说话的人的口气。不需要上屏文字的 clip，caption 留空字符串，不硬凑。
13. storyboard_markdown 面向拍摄和剪辑的人：先给能直接执行的镜头信息，任何选择理由或论证说明只放在文档末尾的备注段，不得放在分镜表之前。"""


def parse_frontmatter(text: str) -> dict[str, Any]:
    return parse_markdown_frontmatter_or_empty(text)


def summary_text(project: Path, item: dict[str, Any]) -> str:
    return _shared_summary_text(project, item, max_chars=MAX_SUMMARY_CHARS)


def transcript_segments(project: Path, item: dict[str, Any]) -> list[dict[str, Any]]:
    return _shared_transcript_segments(project, item, max_segments=60, max_chars=MAX_TRANSCRIPT_CHARS)


def context_items(project: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        item
        for item in manifest.get("items", [])
        if isinstance(item, dict) and (eligible_item(item) or is_raw360_item(item))
    ]
    result: list[dict[str, Any]] = []
    for item in items[:MAX_ITEMS]:
        result.append(
            {
                "media_id": item.get("media_id") or item.get("id"),
                "relative_path": item.get("relative_path"),
                "filename": item.get("filename"),
                "media_type": item.get("media_type"),
                "source_type": item.get("source_type"),
                "lifecycle": item.get("lifecycle"),
                "analysis_eligible": item.get("analysis_eligible"),
                "duration_sec": item.get("duration_sec"),
                "width": item.get("width"),
                "height": item.get("height"),
                "raw_decision_tokens": item.get("raw_decision_tokens") or [],
                "keyframes": keyframe_evidence(item),
                "transcript_segments": transcript_segments(project, item),
                "summary": summary_text(project, item),
            }
        )
    return result


def build_user_prompt(
    *,
    project: Path,
    brief_path: Path,
    script_path: Path | None,
    report_path: Path,
    storyboard_path: Path,
    edl_path: Path,
    model: str,
    reasoning: str,
) -> str:
    brief_text = read_text(brief_path)
    script_text = read_text(script_path) if script_path and script_path.exists() else "未提供 04_script.md。"
    report_text = read_text(report_path)
    meta = parse_frontmatter(brief_text)
    manifest = load_manifest(project)
    creator_context = load_creator_context(project, brief_text=brief_text)
    payload = {
        "project_dir": str(project),
        "project_id": meta.get("project_id") or project.name,
        "project_revision": meta.get("project_revision") or 1,
        "idea_id": meta.get("idea_id") or "",
        "brief_path": str(brief_path),
        "script_path": str(script_path) if script_path else "",
        "material_report_path": str(report_path),
        "storyboard_output_path": str(storyboard_path),
        "edl_output_path": str(edl_path),
        "generation_model": model,
        "generation_reasoning": reasoning,
        "creator_context": creator_context,
        "edl_contract": {
            "schema_version": "edit_decision_list_v1",
            "time_range_example": "0.000-4.000",
            "slot": "unique positive integer",
            "source_start_sec": "non-negative seconds with millisecond precision",
            "missing_material_policy": "write unresolved needs to missing_materials, never executable clips",
        },
        "brief_markdown": brief_text,
        "script_markdown": script_text,
        "material_match_report_markdown": report_text,
        "eligible_items": context_items(project, manifest),
    }
    return (
        "请根据以下 JSON 证据生成 storyboard_markdown 和 edl_json。账号上下文只能用于口吻、平台与题材边界；"
        "没有提供的字段必须标记人工确认，不得猜测：\n\n"
        + creator_context_block(project, brief_text=brief_text)
        + "\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def parse_llm_json(text: str) -> dict[str, Any]:
    try:
        data = parse_json_response(text)
    except (ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"LLM storyboard response is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM storyboard response JSON root must be an object")
    return data


def canonicalize_storyboard(storyboard: str, *, model: str, reasoning: str) -> str:
    """Validate content metadata and stamp invocation-owned generation metadata."""
    try:
        metadata, body = parse_markdown_frontmatter(storyboard)
    except ValueError as exc:
        raise RuntimeError(f"storyboard_markdown frontmatter invalid: {exc}") from exc
    if metadata.get("doc_type") != "storyboard":
        raise RuntimeError("storyboard_markdown frontmatter doc_type must be storyboard")
    if metadata.get("writer_agent") != "mac_openclaw":
        raise RuntimeError("storyboard_markdown writer_agent must be mac_openclaw")
    declared_model = metadata.get("generation_model")
    if declared_model is not None and (
        not isinstance(declared_model, str) or declared_model.strip() != model
    ):
        raise RuntimeError(f"storyboard generation_model must be {model}")
    declared_reasoning = metadata.get("generation_reasoning")
    if declared_reasoning is not None and (
        not isinstance(declared_reasoning, str) or declared_reasoning.strip() != reasoning
    ):
        raise RuntimeError(f"storyboard generation_reasoning must be {reasoning}")
    canonical = dict(metadata)
    canonical.update(
        {
            "spec_version": "content_os_v0.1",
            "generation_model": model,
            "generation_reasoning": reasoning,
        }
    )
    return render_markdown_frontmatter(canonical, body)


def validate_outputs(data: dict[str, Any], *, model: str, reasoning: str) -> tuple[str, dict[str, Any]]:
    storyboard = data.get("storyboard_markdown")
    edl = data.get("edl_json")
    if not isinstance(storyboard, str) or not storyboard.strip():
        raise RuntimeError("storyboard_markdown must be non-empty text")
    if not isinstance(edl, dict):
        raise RuntimeError("edl_json must be an object")

    storyboard = canonicalize_storyboard(storyboard, model=model, reasoning=reasoning)
    try:
        canonical_edl = normalise_edl(edl, generation_model=model, generation_reasoning=reasoning)
    except EDLContractError as exc:
        raise RuntimeError(f"EDL contract rejected model output: {exc}") from exc
    return storyboard, canonical_edl


def generate(
    project: Path,
    brief_path: Path,
    report_path: Path,
    storyboard_path: Path,
    edl_path: Path,
    *,
    script_path: Path | None,
    model: str,
    reasoning: str,
    prompt_output: Path | None,
) -> None:
    user_prompt = build_user_prompt(
        project=project,
        brief_path=brief_path,
        script_path=script_path,
        report_path=report_path,
        storyboard_path=storyboard_path,
        edl_path=edl_path,
        model=model,
        reasoning=reasoning,
    )
    if prompt_output:
        prompt_output.parent.mkdir(parents=True, exist_ok=True)
        prompt_output.write_text(f"{SYSTEM_PROMPT}\n\n--- USER CONTEXT ---\n\n{user_prompt}\n", encoding="utf-8")
    raw = generate_text(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, model=model, reasoning_effort=reasoning)
    storyboard, edl = validate_outputs(parse_llm_json(raw), model=model, reasoning=reasoning)
    storyboard_path.parent.mkdir(parents=True, exist_ok=True)
    storyboard_path.write_text(storyboard.rstrip() + "\n", encoding="utf-8")
    write_edl(edl_path, edl)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir")
    parser.add_argument("--brief", required=True, type=Path)
    parser.add_argument("--material-report", required=True, type=Path)
    parser.add_argument("--storyboard-output", required=True, type=Path)
    parser.add_argument("--edl-output", required=True, type=Path)
    parser.add_argument("--script", type=Path, help="04_script.md path; defaults to the brief sibling when present")
    parser.add_argument("--model", default=DEFAULT_CREATIVE_MODEL)
    parser.add_argument("--reasoning", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--prompt-output", type=Path, help="Optional debug file containing the exact LLM prompt")
    args = parser.parse_args()

    brief = args.brief.expanduser().resolve()
    script = args.script.expanduser().resolve() if args.script else nearby_script_path(brief)
    generate(
        project_path(args.project_dir),
        brief,
        args.material_report.expanduser().resolve(),
        args.storyboard_output.expanduser().resolve(),
        args.edl_output.expanduser().resolve(),
        script_path=script,
        model=args.model,
        reasoning=args.reasoning,
        prompt_output=args.prompt_output.expanduser().resolve() if args.prompt_output else None,
    )
    print(f"storyboard={args.storyboard_output.expanduser().resolve()}")
    print(f"edl={args.edl_output.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
