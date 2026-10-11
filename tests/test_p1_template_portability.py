#!/usr/bin/env python3
"""Keep copied batch templates and their root conventions portable."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_DOCUMENTS = (
    ROOT / "templates/00_Inbox_事件批次_TEMPLATE/README.md",
    ROOT / "docs/01_术语与目录层级.md",
    ROOT / "AGENTS.md",
)
NONEXECUTING_ABSTRACT_MARKER = "PORTABILITY-ABSTRACT-NONEXECUTING"
PERSONAL_ROOT_PATTERNS = (
    re.compile(r"/(?:Users|home)/[^/\s`]+/Desktop/照片筛选(?:/|$)"),
    re.compile(
        r"/(?:Users|home)/[^/\s`]+/Library/Mobile Documents/"
        r"iCloud~md~obsidian/Documents/自媒体(?:/|$)"
    ),
)


def is_nonexecuting_abstract_example(line: str) -> bool:
    stripped = line.strip()
    return (
        NONEXECUTING_ABSTRACT_MARKER in stripped
        and stripped.startswith("<!--")
        and stripped.endswith("-->")
    )


def personal_root_violations(text: str) -> list[str]:
    violations: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if is_nonexecuting_abstract_example(line):
            continue
        if any(pattern.search(line) for pattern in PERSONAL_ROOT_PATTERNS):
            violations.append(f"line {line_number}: {line.strip()}")
    return violations


class TemplatePortabilityTest(unittest.TestCase):
    def test_controlled_documents_expose_no_personal_root(self) -> None:
        violations: list[str] = []
        for document in CONTROLLED_DOCUMENTS:
            violations.extend(f"{document}: {item}" for item in personal_root_violations(document.read_text(encoding="utf-8")))
        self.assertEqual([], violations, "\n".join(violations))

    def test_unmarked_personal_roots_are_rejected(self) -> None:
        self.assertTrue(personal_root_violations("cd /Users/alice/Desktop/照片筛选\n"))
        self.assertTrue(
            personal_root_violations(
                "/home/alice/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体\n"
            )
        )

    def test_marked_html_comment_is_an_allowed_abstract_example(self) -> None:
        example = "<!-- PORTABILITY-ABSTRACT-NONEXECUTING: /Users/example/Desktop/照片筛选 -->\n"
        self.assertEqual([], personal_root_violations(example))

    def test_template_requires_a_configured_root_and_fails_closed(self) -> None:
        template = CONTROLLED_DOCUMENTS[0].read_text(encoding="utf-8")
        self.assertIn("${LOCAL_MEDIA_ROOT:-}", template)
        self.assertIn("${OBSIDIAN_ROOT:-}", template)
        self.assertIn("31_link_batch_to_content_project.py", template)
        self.assertIn('--obsidian-root "$OBSIDIAN_ROOT"', template)
        self.assertIn("exit 1", template)
        self.assertIn("$LOCAL_MEDIA_ROOT/00_Inbox_Mac_Intake/", template)


if __name__ == "__main__":
    unittest.main()
