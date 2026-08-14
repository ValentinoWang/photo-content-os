#!/usr/bin/env python3
"""Shared LLM helpers for Mac-local creative generation scripts."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_CREATIVE_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "xhigh"
DEFAULT_CREATIVE_PROVIDER = "codex_cli"
DEFAULT_CODEX_TIMEOUT_SEC = 1800


class LLMError(Exception):
    """Raised when LLM generation cannot produce a usable result."""


def configured_model(value: str | None = None) -> str:
    return (value or os.getenv("OPENCLAW_CREATIVE_MODEL") or DEFAULT_CREATIVE_MODEL).strip()


def configured_reasoning(value: str | None = None) -> str:
    return (value or os.getenv("OPENCLAW_CREATIVE_REASONING") or DEFAULT_REASONING_EFFORT).strip()


def configured_provider(value: str | None = None) -> str:
    return (value or os.getenv("OPENCLAW_CREATIVE_PROVIDER") or DEFAULT_CREATIVE_PROVIDER).strip().lower()


def require_openai_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise LLMError("OPENAI_API_KEY is required when OPENCLAW_CREATIVE_PROVIDER=openai_api")


def codex_model_name(model: str) -> str:
    if "/" in model:
        return model.rsplit("/", 1)[-1]
    return model


def codex_prompt(system_prompt: str, user_prompt: str) -> str:
    return "\n\n".join(
        [
            "你是 Mac OpenClaw 的本地创作代理。必须严格遵守 system 指令和用户输入合同。",
            "不要解释你的执行过程，不要输出额外寒暄，只输出任务要求的正文。",
            "## System Prompt",
            system_prompt.strip(),
            "## User Context",
            user_prompt.strip(),
        ]
    ).strip()


def response_text(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    if hasattr(response, "model_dump"):
        data = response.model_dump()
    elif isinstance(response, dict):
        data = response
    else:
        data = {}

    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") in {"output_text", "text"} and isinstance(value.get("text"), str):
                texts.append(value["text"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data.get("output", data))
    text = "\n".join(part for part in texts if part.strip()).strip()
    if not text:
        raise LLMError("OpenAI response did not contain output text")
    return text


def generate_text_with_openai_api(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> str:
    require_openai_key()
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - environment issue
        raise LLMError("openai Python package is required for LLM generation") from exc

    resolved_model = configured_model(model)
    resolved_reasoning = configured_reasoning(reasoning_effort)
    client = OpenAI()
    response = client.responses.create(
        model=resolved_model,
        reasoning={"effort": resolved_reasoning},
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            },
        ],
    )
    return response_text(response)


def generate_text_with_codex_cli(
    *,
    system_prompt: str,
    user_prompt: str,
    image_paths: list[Path] | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> str:
    codex_bin = os.getenv("OPENCLAW_CODEX_BIN") or "codex"
    codex_path = shutil.which(codex_bin)
    if not codex_path:
        raise LLMError("codex CLI is required when OPENCLAW_CREATIVE_PROVIDER=codex_cli")

    resolved_model = codex_model_name(configured_model(model))
    resolved_reasoning = configured_reasoning(reasoning_effort)
    timeout = int(os.getenv("OPENCLAW_CODEX_TIMEOUT_SEC", str(DEFAULT_CODEX_TIMEOUT_SEC)))
    prompt = codex_prompt(system_prompt, user_prompt)

    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".codex-output.txt", delete=False) as handle:
        output_path = Path(handle.name)

    args = [
        codex_path,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-m",
        resolved_model,
        "-c",
        f'model_reasoning_effort="{resolved_reasoning}"',
        "-C",
        str(Path.cwd()),
        "-o",
        str(output_path),
    ]
    for image_path in image_paths or []:
        resolved = image_path.expanduser().resolve()
        if not resolved.exists():
            raise LLMError(f"image path does not exist: {resolved}")
        args.extend(["--image", str(resolved)])
    args.append("-")
    try:
        completed = subprocess.run(
            args,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise LLMError(f"codex CLI generation failed ({completed.returncode}): {detail}")
        text = output_path.read_text(encoding="utf-8").strip()
        if not text:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise LLMError(f"codex CLI did not write output text: {detail}")
        return text
    except subprocess.TimeoutExpired as exc:
        raise LLMError(f"codex CLI generation timed out after {timeout}s") from exc
    finally:
        try:
            output_path.unlink()
        except FileNotFoundError:
            pass


def generate_text(
    *,
    system_prompt: str,
    user_prompt: str,
    image_paths: list[Path] | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    provider: str | None = None,
) -> str:
    resolved_provider = configured_provider(provider)
    if resolved_provider in {"codex", "codex_cli", "codex-cli"}:
        return generate_text_with_codex_cli(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_paths=image_paths,
            model=model,
            reasoning_effort=reasoning_effort,
        )
    if resolved_provider in {"openai", "openai_api", "openai-api"}:
        if image_paths:
            raise LLMError("image_paths are currently supported through codex_cli provider only")
        return generate_text_with_openai_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            reasoning_effort=reasoning_effort,
        )
    raise LLMError(f"unsupported OPENCLAW_CREATIVE_PROVIDER: {resolved_provider}")
