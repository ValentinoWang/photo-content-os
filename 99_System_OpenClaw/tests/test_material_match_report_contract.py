import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "17_match_materials_to_brief.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("match_materials_to_brief", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _report(*, sections: tuple[str, ...] | None = None, **overrides: object) -> str:
    metadata: dict[str, object] = {
        "spec_version": "content_os_v0.2",
        "doc_type": "material_match_report",
        "project_id": "project_demo",
        "idea_id": "idea_demo",
        "writer_agent": "mac_openclaw",
        "owner_agent": "mac_openclaw",
        "next_owner": "human_editor",
        "status": "materials_matched",
        "source_brief": "01_Project_Brief.md",
        "strict_contract": True,
        "generation_model": "gpt-test",
        "generation_reasoning": "high",
    }
    metadata.update(overrides)
    lines = ["---"]
    for key, value in metadata.items():
        rendered = "true" if value is True else str(value)
        lines.append(f"{key}: {rendered}")
    rendered_sections = sections or MODULE.REQUIRED_REPORT_SECTIONS
    body = ["---", ""]
    for section in rendered_sections:
        body.extend([f"## {section}", "内容"])
    body.extend(["```text", "正文允许包含示例", "```", ""])
    return "\n".join([*lines, *body])


class MaterialMatchReportContractTests(unittest.TestCase):
    def test_validate_report_accepts_complete_frontmatter_and_body_fence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            MODULE.validate_report(_report(), Path(temp_dir) / "report.md")

    def test_validate_report_rejects_each_missing_declared_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.md"
            for field in MODULE.REQUIRED_REPORT_FRONTMATTER:
                with self.subTest(field=field):
                    with self.assertRaisesRegex(RuntimeError, field):
                        MODULE.validate_report(_report(**{field: ""}), output)

    def test_validate_report_rejects_outer_code_fence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "must not be wrapped"):
                MODULE.validate_report("```markdown\n" + _report() + "```", Path(temp_dir) / "report.md")

    def test_validate_report_rejects_malformed_closing_fence(self) -> None:
        """Regression test for the L-03 frontmatter-parsing bug fix.

        Before the fix, 17_match_materials_to_brief.py's own parse_frontmatter
        located the closing fence with `text.find("\n---", 4)` -- a byte
        substring search that matches ANY line starting with "---", not just a
        line that IS exactly "---". A malformed closing fence such as
        "---foo" (three dashes plus trailing text, e.g. a stray LLM comment)
        was therefore silently accepted as if it correctly closed the
        frontmatter: since every required field already appears before it,
        the report used to pass validate_report despite its frontmatter fence
        never actually being closed per the strict_contract format.

        After the fix (parse_frontmatter now delegates to llm_common's
        line-exact "---" closing detection), "---foo" is no longer treated as
        a closing fence, this document has no usable frontmatter at all, and
        validate_report must reject it as missing every required field
        instead of silently accepting the malformed markdown.
        """
        metadata: dict[str, object] = {
            "spec_version": "content_os_v0.2",
            "doc_type": "material_match_report",
            "project_id": "project_demo",
            "idea_id": "idea_demo",
            "writer_agent": "mac_openclaw",
            "owner_agent": "mac_openclaw",
            "next_owner": "human_editor",
            "status": "materials_matched",
            "source_brief": "01_Project_Brief.md",
            "strict_contract": True,
            "generation_model": "gpt-test",
            "generation_reasoning": "high",
        }
        lines = ["---"]
        for key, value in metadata.items():
            rendered = "true" if value is True else str(value)
            lines.append(f"{key}: {rendered}")
        lines.append("---foo")  # malformed closing fence, not a bare "---"
        body = [""]
        for section in MODULE.REQUIRED_REPORT_SECTIONS:
            body.extend([f"## {section}", "内容"])
        text = "\n".join([*lines, *body])

        # The malformed fence yields no real frontmatter, so parse_frontmatter
        # must fall back to {} rather than the old lenient (and wrong) parse.
        self.assertEqual(MODULE.parse_frontmatter(text), {})
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "frontmatter missing"):
                MODULE.validate_report(text, Path(temp_dir) / "report.md")

    def test_validate_report_rejects_execution_sections_after_macro_rationale(self) -> None:
        sections = (
            "宏观创作判断",
            "是否建议进入剪辑",
            "推荐镜头组",
            "缺失素材",
            "风险",
            "素材覆盖度",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "execution handoff before macro rationale"):
                MODULE.validate_report(_report(sections=sections), Path(temp_dir) / "report.md")


if __name__ == "__main__":
    unittest.main()
