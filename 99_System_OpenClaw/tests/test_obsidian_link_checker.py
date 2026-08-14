from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("obsidian_link_checker", ROOT / "scripts" / "38_check_obsidian_links.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ObsidianLinkCheckerTests(unittest.TestCase):
    def test_resolves_wikilinks_relative_links_and_embeds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            (vault / "sub").mkdir()
            (vault / "assets").mkdir()
            (vault / "目标.md").write_text("# 目标\n", encoding="utf-8")
            (vault / "sub" / "相对.md").write_text("# 相对\n", encoding="utf-8")
            (vault / "assets" / "cover.png").write_bytes(b"png")
            (vault / "入口.md").write_text(
                "[[目标]]\n[相对](sub/相对.md)\n![封面](assets/cover.png)\n[外部](https://example.com)\n",
                encoding="utf-8",
            )
            self.assertEqual(MODULE.check(vault), [])

    def test_reports_missing_and_ambiguous_wikilinks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            (vault / "a").mkdir()
            (vault / "b").mkdir()
            (vault / "a" / "同名.md").write_text("# a\n", encoding="utf-8")
            (vault / "b" / "同名.md").write_text("# b\n", encoding="utf-8")
            (vault / "入口.md").write_text("[[不存在]]\n[[同名]]\n[坏链接](missing.md)\n", encoding="utf-8")
            errors = MODULE.check(vault)
            self.assertEqual(len(errors), 3)
            self.assertTrue(any("无法解析" in error for error in errors))
            self.assertTrue(any("多个同名" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
