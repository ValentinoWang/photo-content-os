#!/usr/bin/env python3
"""Bounded AI patch generation for selected, unlocked document blocks."""

from __future__ import annotations

import json
from typing import Any, Callable


class AIPatchError(ValueError):
    pass


SYSTEM_PROMPT = """你是 Photo Content OS 的区块编辑代理。
只修改用户明确选中的区块，不得输出未选区块，不得改变区块 ID，不得解释过程。

写作规范：
1. 先读 read_only_context，接住这份文档已有的说话方式：称呼、句长、语气和用词习惯；改出来的段落要像同一个作者写的，不要换一副腔调。
2. 只改指令要求改的部分；指令没提到的句子，能保留原句就保留原句，不做顺手润色。
3. 口播、台词、字幕类区块必须写成能直接读出声的话：一句尽量不超过 22 个字，允许口语连接词和自然的不完整句。
4. 禁止书面套话和 AI 腔：不用『首先/其次/最后』连用、『总之』『综上所述』『值得一提的是』『不难发现』，不写连续排比，不给每句加感叹号，不堆与内容无关的网络热词。
5. 事实边界：不得新增素材、地点、人物、成绩或时间等文档里没有的事实；需要新事实时在正文用（待确认：……）标出，而不是编造。

输出严格 JSON：{"replacements":{"block-id":"新的正文"}}。不得使用 Markdown 代码围栏。"""


def build_patch_prompt(
    *,
    document_name: str,
    instruction: str,
    selected_blocks: list[dict[str, Any]],
    surrounding_blocks: list[dict[str, Any]],
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
        "read_only_context": [
            {"id": block.get("id"), "title": block.get("title", ""), "body": block.get("body", "")}
            for block in surrounding_blocks
            if block.get("id") not in selected_ids
        ],
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
    generate_text: Callable[..., str],
    model: str | None = None,
    reasoning: str | None = None,
) -> dict[str, str]:
    prompt = build_patch_prompt(
        document_name=document_name,
        instruction=instruction,
        selected_blocks=selected_blocks,
        surrounding_blocks=surrounding_blocks,
    )
    text = generate_text(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        model=model,
        reasoning_effort=reasoning,
    )
    return parse_patch_response(text, selected_ids=[block["id"] for block in selected_blocks])
