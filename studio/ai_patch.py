#!/usr/bin/env python3
"""Bounded AI patch generation for selected, unlocked document blocks."""

from __future__ import annotations

import json
from typing import Any, Callable


class AIPatchError(ValueError):
    pass


if __package__:
    from .constants import (
        SYSTEM_PROMPT,
    )
else:
    try:
        from studio.constants import (
            SYSTEM_PROMPT,
        )
    except ImportError:
        from constants import (
            SYSTEM_PROMPT,
        )


def build_patch_prompt(
    *,
    document_name: str,
    instruction: str,
    selected_blocks: list[dict[str, Any]],
    surrounding_blocks: list[dict[str, Any]],
    project_context: dict[str, str] | None = None,
    account_review_context: list[dict[str, str]] | None = None,
) -> str:
    if not selected_blocks:
        raise AIPatchError("未选择任何区块")
    selected_ids = [str(block.get("id") or "") for block in selected_blocks]
    if any(not value for value in selected_ids) or len(set(selected_ids)) != len(selected_ids):
        raise AIPatchError("选中区块 ID 无效")
    if any(block.get("locked") for block in selected_blocks):
        raise AIPatchError("选中区块包含已锁定内容")
    payload = {
        "document": document_name,
        "instruction": str(instruction or "").strip(),
        "selected_blocks": [
            {"id": block["id"], "title": block.get("title", ""), "body": block.get("body", "")}
            for block in selected_blocks
        ],
        "read_only_context": {
            "document_blocks": [
                {"id": block.get("id"), "title": block.get("title", ""), "body": block.get("body", "")}
                for block in surrounding_blocks
                if block.get("id") not in selected_ids
            ],
            "current_project": {
                "title": str((project_context or {}).get("title") or "")[:120],
                "platform": str((project_context or {}).get("platform") or "")[:80],
                "account": str((project_context or {}).get("account") or "")[:80],
                "persona": str((project_context or {}).get("persona") or "")[:240],
                "review_conclusion": str((project_context or {}).get("review_conclusion") or "")[:4_000],
                "next_constraint": str((project_context or {}).get("next_constraint") or "")[:2_000],
            },
            "same_account_review_conclusions": [
                {
                    "review_conclusion": str(item.get("review_conclusion") or "")[:4_000],
                    "next_constraint": str(item.get("next_constraint") or "")[:2_000],
                }
                for item in (account_review_context or [])
                if isinstance(item, dict)
            ][-12:],
        },
        "contract": {
            "only_ids": selected_ids,
            "all_selected_ids_required": True,
            "extra_ids_forbidden": True,
        },
    }
    if not payload["instruction"]:
        raise AIPatchError("修改要求不能为空")
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_patch_response(text: str, *, selected_ids: list[str]) -> dict[str, str]:
    if text.strip().startswith("```"):
        raise AIPatchError("AI 返回不能使用代码围栏")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIPatchError("AI 返回不是有效 JSON") from exc
    replacements = payload.get("replacements") if isinstance(payload, dict) else None
    if not isinstance(replacements, dict):
        raise AIPatchError("AI 返回缺少 replacements")
    if set(replacements) != set(selected_ids):
        raise AIPatchError("AI 返回区块与用户选择不一致")
    result: dict[str, str] = {}
    for block_id in selected_ids:
        value = replacements.get(block_id)
        if not isinstance(value, str):
            raise AIPatchError(f"区块 {block_id} 的正文必须是字符串")
        if len(value) > 50_000:
            raise AIPatchError(f"区块 {block_id} 超过长度限制")
        result[block_id] = value.strip()
    return result


def generate_patch(
    *,
    document_name: str,
    instruction: str,
    selected_blocks: list[dict[str, Any]],
    surrounding_blocks: list[dict[str, Any]],
    project_context: dict[str, str] | None = None,
    account_review_context: list[dict[str, str]] | None = None,
    generate_text: Callable[..., str],
    model: str | None = None,
    reasoning: str | None = None,
) -> dict[str, str]:
    prompt = build_patch_prompt(
        document_name=document_name,
        instruction=instruction,
        selected_blocks=selected_blocks,
        surrounding_blocks=surrounding_blocks,
        project_context=project_context,
        account_review_context=account_review_context,
    )
    text = generate_text(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        model=model,
        reasoning_effort=reasoning,
    )
    return parse_patch_response(text, selected_ids=[block["id"] for block in selected_blocks])
