#!/usr/bin/env python3
"""Generate an AI-assisted Content OS edit log from script, EDL, and roughcut artifacts."""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from llm import (
    DEFAULT_CREATIVE_MODEL,
    DEFAULT_REASONING_EFFORT,
    generate_text,
    load_creator_context,
    parse_markdown_frontmatter_or_empty,
)


if __package__ and "." in __package__:
    from ..constants import (
        MAX_TEXT_CHARS,
        MAX_JSON_CHARS,
        GENERATE_AI_EDIT_LOG_SYSTEM_PROMPT as SYSTEM_PROMPT,
    )
else:
    import sys as _sys
    from pathlib import Path as _Path
    _sdir = str(_Path(__file__).resolve().parents[1])
    if _sdir not in _sys.path:
        _sys.path.insert(0, _sdir)
    from constants import (
        MAX_TEXT_CHARS,
        MAX_JSON_CHARS,
        GENERATE_AI_EDIT_LOG_SYSTEM_PROMPT as SYSTEM_PROMPT,
    )


class EditLogError(Exception):
    """Raised when the edit log contract cannot be satisfied."""




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
    parser.add_argument("--video", type=Path, help="Optional V1/v2/Final export for metadata-level evidence.")
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
