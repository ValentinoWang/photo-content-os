#!/usr/bin/env python3
"""Generate storyboard and EDL with gpt-5.5/xhigh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from llm_common import DEFAULT_CREATIVE_MODEL, DEFAULT_REASONING_EFFORT, generate_text
from media_common import eligible_item, load_manifest, project_path


MAX_ITEMS = 140
MAX_SUMMARY_CHARS = 700


SYSTEM_PROMPT = """你是 Mac OpenClaw 的短视频分镜与 EDL 编排代理。

你必须先做宏观创作判断：识别这个项目真正要表达的内容类型、核心冲突、情绪曲线、平台观看动机和素材证据边界，然后再生成分镜和 EDL。不要套用任何固定项目模板，不要把旧项目表达、旧字幕、旧节奏结构或脚本内置规则自动搬到新项目；只有输入证据支持时才能使用。

硬约束：
1. 04_script.md 是强输入，默认按脚本叙事生成可剪执行方案；只有素材清单完全没有相关证据时，才把段落标成缺失或替代。
2. 不允许编造素材、成绩、地点、人物关系、BGM 或镜头。
3. EDL 的 candidate_files 只能来自输入 manifest 或 03_material_match_report。
4. 如果素材不足，必须在 missing_materials 写清楚，不要硬凑。
5. 输出必须是严格 JSON，不能有 Markdown 代码围栏或额外解释。
6. JSON 顶层必须有 storyboard_markdown 和 edl_json 两个字段。
7. storyboard_markdown 必须是完整 Markdown 文档，含 YAML frontmatter，doc_type=storyboard，writer_agent=mac_openclaw。
8. edl_json 必须是对象，doc_type=edit_decision_list，clips 必须是非空数组。
9. 每个 clips 条目必须包含 slot、time_range、purpose、visual_need、caption、candidate_files、edit_note。
10. generation_model 必须写入 storyboard frontmatter 和 edl_json。generation_reasoning 也必须写入。
11. edl_json 必须包含 source_script_used=true。
12. RawVault / 360相机原始组 / reframe_needed 素材是第一视角或全景视角存在的强证据，不能因为还需要重构就判定为第一视角缺失。
13. 如果 EDL 使用 RawVault / 360 原始素材，candidate_files 可以写原始 .OSV/.LRF 路径，但 edit_note 必须明确“先转码/重构视角/导出可剪片段后再剪”。
14. 禁止把结果描述为脚本自动判定、机械分组或临时版本生成。
15. 不要输出任何固定叙事模板；先按输入项目建立独立表达策略。"""


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else {}


def nearby_script_path(brief_path: Path) -> Path:
    return brief_path.with_name("04_script.md")


def is_raw360_reference(item: dict[str, Any]) -> bool:
    relative_path = str(item.get("relative_path") or "")
    source_type = str(item.get("source_type") or "")
    raw_tokens = item.get("raw_decision_tokens") or []
    return (
        source_type == "360相机原始组"
        or "00_RawVault_不可直用" in relative_path
        or "reframe_needed" in raw_tokens
    )


def raw360_reference_summary(item: dict[str, Any]) -> str:
    duration = item.get("duration_sec")
    width = item.get("width")
    height = item.get("height")
    rel = item.get("relative_path")
    return (
        "这是项目里的 360/全景相机原始素材证据，位于 RawVault 或标记为 reframe_needed。"
        "它不能直接等同于已导出的剪映片段，但它证明第一视角/全景视角素材存在。"
        f"路径：{rel}；时长：{duration} 秒；分辨率：{width}x{height}。"
        "EDL 可把它列为候选素材，并在 edit_note 中要求先转码、重构视角或导出可剪片段。"
    )


def summary_text(project: Path, item: dict[str, Any]) -> str:
    media_id = str(item.get("media_id") or item.get("id") or "")
    stem = Path(str(item.get("relative_path", ""))).stem
    summaries = project / "_ai_analysis" / "summaries"
    candidates = list(summaries.glob(f"{media_id}_*.summary.md")) if media_id else []
    candidates.extend(summaries.glob(f"*_{stem}.summary.md"))
    for path in candidates:
        if path.exists():
            return path.read_text(encoding="utf-8")[:MAX_SUMMARY_CHARS]
    if is_raw360_reference(item):
        return raw360_reference_summary(item)
    return ""


def context_items(project: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        item
        for item in manifest.get("items", [])
        if isinstance(item, dict) and (eligible_item(item) or is_raw360_reference(item))
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
                "keyframes": (item.get("keyframes") or [])[:6],
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
    payload = {
        "project_dir": str(project),
        "project_id": meta.get("project_id") or project.name,
        "idea_id": meta.get("idea_id") or "",
        "brief_path": str(brief_path),
        "script_path": str(script_path) if script_path else "",
        "material_report_path": str(report_path),
        "storyboard_output_path": str(storyboard_path),
        "edl_output_path": str(edl_path),
        "generation_model": model,
        "generation_reasoning": reasoning,
        "brief_markdown": brief_text,
        "script_markdown": script_text,
        "material_match_report_markdown": report_text,
        "eligible_items": context_items(project, manifest),
    }
    return "请根据以下 JSON 上下文生成 storyboard_markdown 和 edl_json：\n\n" + json.dumps(payload, ensure_ascii=False, indent=2)


def parse_llm_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        raise RuntimeError("LLM storyboard response must be raw JSON, not a code fence")
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise RuntimeError("LLM storyboard response JSON root must be an object")
    return data


def validate_outputs(data: dict[str, Any], *, model: str, reasoning: str) -> tuple[str, dict[str, Any]]:
    storyboard = data.get("storyboard_markdown")
    edl = data.get("edl_json")
    if not isinstance(storyboard, str) or not storyboard.strip():
        raise RuntimeError("storyboard_markdown must be non-empty text")
    if not isinstance(edl, dict):
        raise RuntimeError("edl_json must be an object")

    meta = parse_frontmatter(storyboard)
    if meta.get("doc_type") != "storyboard":
        raise RuntimeError("storyboard_markdown frontmatter doc_type must be storyboard")
    if meta.get("writer_agent") != "mac_openclaw":
        raise RuntimeError("storyboard_markdown writer_agent must be mac_openclaw")
    if edl.get("doc_type") != "edit_decision_list":
        raise RuntimeError("edl_json.doc_type must be edit_decision_list")
    if edl.get("source_script_used") is not True:
        raise RuntimeError("edl_json.source_script_used must be true")
    if edl.get("generation_model") != model:
        raise RuntimeError(f"edl_json.generation_model must be {model}")
    if edl.get("generation_reasoning") != reasoning:
        raise RuntimeError(f"edl_json.generation_reasoning must be {reasoning}")
    clips = edl.get("clips")
    if not isinstance(clips, list) or not clips:
        raise RuntimeError("edl_json.clips must be a non-empty list")
    required = {"slot", "time_range", "purpose", "visual_need", "caption", "candidate_files", "edit_note"}
    for index, clip in enumerate(clips, start=1):
        if not isinstance(clip, dict):
            raise RuntimeError(f"edl_json.clips[{index}] must be an object")
        missing = sorted(required - set(clip))
        if missing:
            raise RuntimeError(f"edl_json.clips[{index}] missing fields: {', '.join(missing)}")
        if not isinstance(clip.get("candidate_files"), list):
            raise RuntimeError(f"edl_json.clips[{index}].candidate_files must be a list")
    return storyboard, edl


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
    edl_path.parent.mkdir(parents=True, exist_ok=True)
    storyboard_path.write_text(storyboard.rstrip() + "\n", encoding="utf-8")
    with edl_path.open("w", encoding="utf-8") as handle:
        json.dump(edl, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


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
