#!/usr/bin/env python3
"""Shared LLM material-evidence-context helpers for 17/18's generation scripts.

17_match_materials_to_brief.py and 18_generate_storyboard_edl.py each grew an
almost-identical set of helpers for turning one manifest item into evidence a
model can be trusted to reason from (RawVault/360 framing, transcript
segments, keyframe references, cached summaries). This module is their single
source of truth for the boundary-clear parts of that evidence pipeline --
i.e. the helpers below whose input/output shape does not differ between the
two scripts. context_items() itself (the per-item field set each script sends
the model) is deliberately NOT unified here: 17 and 18 send materially
different field sets -- 17 adds has_audio/quality_flags/decision_notes and
sends raw keyframe paths, 18 sends the keyframe_evidence()-wrapped structure
its own SYSTEM_PROMPT explicitly promises the model ("你拿到的 keyframes
只有 evidence_ref 和帧路径") -- and there is no existing test coverage that
would catch a field silently dropped or reshaped during such a merge. Each
script keeps its own context_items() referencing the shared helpers below.

05_write_content_summary.py's transcript_payload() is also deliberately left
unmerged: it returns a different-shaped status/language/text envelope (not a
plain segment list), it silently slices per-segment text instead of using
bounded_prompt_text's explicit truncation marker, and unifying that truncation
style would change what is sent to the model without any test to validate the
change is safe.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_common import MAX_PROMPT_SUMMARY_CHARS, bounded_prompt_text
from media_common import find_item_summary, is_raw360_item, safe_project_file


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def nearby_script_path(brief_path: Path) -> Path:
    return brief_path.with_name("04_script.md")


def raw360_reference_summary(item: dict[str, Any]) -> str:
    """Describe a RawVault/360 item as strong first-person evidence, not a missing clip.

    This is 17_match_materials_to_brief.py's original (longer) wording, which
    18_generate_storyboard_edl.py's own copy was missing one sentence of --
    "报告中不得再把第一视角素材简单判为缺失" -- the explicit instruction not
    to report this kind of evidence as missing footage. Both scripts now get
    the fuller text.
    """
    duration = item.get("duration_sec")
    width = item.get("width")
    height = item.get("height")
    rel = item.get("relative_path")
    return (
        "这是项目里的 360/全景相机原始素材证据，位于 RawVault 或标记为 reframe_needed。"
        "它不应被当作已经可直接剪辑的成片素材，但应被当作第一视角/全景视角存在的强证据。"
        f"路径：{rel}；时长：{duration} 秒；分辨率：{width}x{height}。"
        "使用方式：先转码、重构视角、裁切或导出为可剪片段，再进入剪映/粗剪；报告中不得再把第一视角素材简单判为缺失。"
    )


def summary_text(project: Path, item: dict[str, Any], *, max_chars: int = MAX_PROMPT_SUMMARY_CHARS) -> str:
    """Return the cached content summary for `item`, or a RawVault/360 fallback."""
    summaries = project / "_ai_analysis" / "summaries"
    path = find_item_summary(summaries, item)
    if path is not None:
        return bounded_prompt_text(path.read_text(encoding="utf-8"), max_chars)
    if is_raw360_item(item):
        return raw360_reference_summary(item)
    return ""


def keyframe_evidence(item: dict[str, Any], *, max_images: int = 12) -> list[dict[str, str]]:
    """Wrap an item's keyframe paths with the evidence_ref the model must cite back."""
    return [
        {"evidence_ref": f"image:{item.get('media_id')}:{index}", "path": str(path)}
        for index, path in enumerate((item.get("keyframes") or [])[:max_images])
    ]


def transcript_segments(
    project: Path,
    item: dict[str, Any],
    *,
    max_segments: int = 60,
    max_chars: int = 1600,
) -> list[dict[str, Any]]:
    """Load an item's transcript segments, evidence_ref-tagged and length-bounded.

    max_segments and max_chars are parameters (not shared module constants)
    because 17/18 currently agree on both (60 segments, 1600 chars/segment)
    but are free to diverge -- do not fold these into a single hardcoded
    value a future caller can't override.
    """
    resolved = safe_project_file(project, item.get("transcript_path"))
    if resolved is None:
        return []
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    result: list[dict[str, Any]] = []
    for index, segment in enumerate(data.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        result.append(
            {
                "evidence_ref": f"transcript:{item.get('media_id')}:{index}",
                "start_sec": segment.get("start_sec"),
                "end_sec": segment.get("end_sec"),
                "speaker": segment.get("speaker"),
                "text": bounded_prompt_text(str(segment.get("text") or ""), max_chars),
            }
        )
    return result[:max_segments]
