#!/usr/bin/env python3
"""Fail when internal Obsidian links or embeds cannot be resolved.

External URLs, heading-only links and Obsidian commands are intentionally out
of scope.  The checker understands WikiLinks, Markdown relative links and
image/file embeds; it does not modify the vault.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "obsidian:", "data:")


def markdown_files(vault: Path) -> list[Path]:
    return sorted(path for path in vault.rglob("*.md") if ".obsidian" not in path.parts)


def target_without_alias_or_anchor(value: str) -> str:
    value = value.split("|", 1)[0].split("#", 1)[0].strip()
    return unquote(value)


def is_external(value: str) -> bool:
    return not value or value.startswith("#") or value.startswith(EXTERNAL_PREFIXES)


def wiki_index(files: list[Path], vault: Path) -> dict[str, list[Path]]:
    index: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        relative = path.relative_to(vault)
        index[path.stem].append(path)
        index[relative.with_suffix("").as_posix()].append(path)
    return index


def resolve_wikilink(raw_target: str, source: Path, vault: Path, index: dict[str, list[Path]]) -> str | None:
    target = target_without_alias_or_anchor(raw_target)
    if is_external(target):
        return None
    relative_candidate = source.parent / target
    candidates = [
        relative_candidate,
        relative_candidate.with_suffix(".md") if not relative_candidate.suffix else relative_candidate,
        vault / target,
        (vault / target).with_suffix(".md") if not Path(target).suffix else vault / target,
    ]
    if any(candidate.is_file() for candidate in candidates):
        return None
    matches = index.get(target, [])
    if len(matches) == 1:
        return None
    if len(matches) > 1:
        return f"WikiLink 指向多个同名笔记：{target}"
    return f"WikiLink 无法解析：{target}"


def resolve_markdown_link(raw_target: str, source: Path, vault: Path) -> str | None:
    target = raw_target.strip().strip("<>").split(" ", 1)[0]
    target = target_without_alias_or_anchor(target)
    if is_external(target):
        return None
    path = Path(target)
    if path.is_absolute():
        return f"内部链接不能使用绝对路径：{target}"
    resolved = (source.parent / path).resolve()
    try:
        resolved.relative_to(vault.resolve())
    except ValueError:
        return f"链接跳出了 vault：{target}"
    if not resolved.exists():
        return f"Markdown 链接无法解析：{target}"
    return None


def check(vault: Path) -> list[str]:
    files = markdown_files(vault)
    index = wiki_index(files, vault)
    errors: list[str] = []
    for source in files:
        text = source.read_text(encoding="utf-8")
        for target in WIKILINK.findall(text):
            error = resolve_wikilink(target, source, vault, index)
            if error:
                errors.append(f"{source.relative_to(vault)}: {error}")
        for target in MARKDOWN_LINK.findall(text):
            error = resolve_markdown_link(target, source, vault)
            if error:
                errors.append(f"{source.relative_to(vault)}: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", type=Path, required=True)
    args = parser.parse_args()
    errors = check(args.vault_root.expanduser().resolve())
    if errors:
        print("Obsidian 链接检查失败：", file=sys.stderr)
        print("\n".join(f"- {item}" for item in errors), file=sys.stderr)
        return 1
    print("Obsidian 内部链接检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
