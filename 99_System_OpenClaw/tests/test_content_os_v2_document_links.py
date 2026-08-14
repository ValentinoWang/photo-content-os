#!/usr/bin/env python3
"""Ensure the v0.2 protocol pages do not introduce broken local links."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


LOCAL_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_ROOT = LOCAL_ROOT / "99_System_OpenClaw"
OBSIDIAN_ROOT = Path("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体").expanduser()

LOCAL_DOCUMENTS = [
    SYSTEM_ROOT / "AGENTS.md",
    SYSTEM_ROOT / "docs/00_本地素材与剪映HyperFrames流转总纲.md",
    SYSTEM_ROOT / "docs/05_剪映与HyperFrames.md",
    SYSTEM_ROOT / "docs/08_usage_guides_使用指南/08.05_需要进入剪映或成片复核_导入包与验收.md",
    SYSTEM_ROOT / "docs/README.md",
    SYSTEM_ROOT / "scripts/README.md",
]
OBSIDIAN_DOCUMENTS = [
    OBSIDIAN_ROOT / "00_入口与总览/剪辑交接与可编辑时间线.md",
    OBSIDIAN_ROOT / "00_入口与总览/Jianying_Roughcut_Draft_Pipeline.md",
    OBSIDIAN_ROOT / "00_入口与总览/Feishu_Tag_Router_Collaboration.md",
    OBSIDIAN_ROOT / "00_入口与总览/Media_Bot_Content_OS_Bridge_Audit.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/腾讯云OpenClaw与MAC_OpenClaw本地素材协同流转规范.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/媒体Bot创作提示词内容/00-主索引.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/媒体Bot创作提示词内容/00-总览与运行边界.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/媒体Bot创作提示词内容/01-入口模板与请求解析.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/媒体Bot创作提示词内容/08-项目修改入口.md",
]
OPERATOR_DOCUMENTS = [
    OBSIDIAN_ROOT / "00_入口与总览/Feishu_Tag_Router_Collaboration.md",
    OBSIDIAN_ROOT / "06_技术栈与自动化/媒体Bot创作提示词内容/08-项目修改入口.md",
]
OPERATOR_FORBIDDEN_TERMS = (
    "/Users/",
    "task_",
    ".yaml",
    "handoff_pack",
    "otio_kdenlive",
    "OTIO",
    "Kdenlive",
    "Traceback",
    "exception",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


def is_external(target: str) -> bool:
    return target.startswith(("#", "http://", "https://", "mailto:", "data:"))


def resolve_markdown_target(document: Path, raw_target: str) -> Path | None:
    target = raw_target.strip().strip("<>").split(maxsplit=1)[0].split("#", 1)[0]
    if not target or is_external(target):
        return None
    return (document.parent / target).resolve()


def resolve_wikilink_target(document: Path, raw_target: str) -> Path | None:
    target = raw_target.split("|", 1)[0].split("#", 1)[0].strip()
    if not target or is_external(target):
        return None
    direct = (document.parent / target).resolve()
    markdown = direct if direct.suffix else direct.with_suffix(".md")
    if markdown.is_file():
        return markdown
    # Obsidian WikiLinks may omit the folder and resolve from the vault root.
    filename = markdown.name
    matches = list(OBSIDIAN_ROOT.rglob(filename))
    return matches[0] if len(matches) == 1 else markdown


class ContentOsV2DocumentLinksTest(unittest.TestCase):
    def require_obsidian_vault(self) -> None:
        if not OBSIDIAN_ROOT.is_dir():
            self.skipTest(f"Obsidian vault is unavailable: {OBSIDIAN_ROOT}")

    def assert_documents_exist(self, documents: list[Path]) -> None:
        for document in documents:
            self.assertTrue(document.is_file(), document)

    def assert_links_resolve(self, documents: list[Path]) -> None:
        broken: list[str] = []
        for document in documents:
            text = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(text):
                target = resolve_markdown_target(document, raw_target)
                if target is not None and not target.exists():
                    broken.append(f"{document}: Markdown link -> {raw_target}")
            for raw_target in WIKILINK.findall(text):
                target = resolve_wikilink_target(document, raw_target)
                if target is not None and not target.is_file():
                    broken.append(f"{document}: WikiLink -> {raw_target}")
        self.assertEqual([], broken, "\n".join(broken))

    def test_local_protocol_documents_exist(self) -> None:
        self.assert_documents_exist(LOCAL_DOCUMENTS)

    def test_local_markdown_and_wikilinks_resolve(self) -> None:
        self.assert_links_resolve(LOCAL_DOCUMENTS)

    def test_obsidian_protocol_documents_exist(self) -> None:
        self.require_obsidian_vault()
        self.assert_documents_exist(OBSIDIAN_DOCUMENTS)

    def test_obsidian_markdown_and_wikilinks_resolve(self) -> None:
        self.require_obsidian_vault()
        self.assert_links_resolve(OBSIDIAN_DOCUMENTS)

    def test_operator_documents_do_not_expose_internal_implementation(self) -> None:
        self.require_obsidian_vault()
        leaked: list[str] = []
        for document in OPERATOR_DOCUMENTS:
            text = document.read_text(encoding="utf-8")
            for term in OPERATOR_FORBIDDEN_TERMS:
                if term in text:
                    leaked.append(f"{document}: {term}")
        self.assertEqual([], leaked, "\n".join(leaked))


if __name__ == "__main__":
    unittest.main()
