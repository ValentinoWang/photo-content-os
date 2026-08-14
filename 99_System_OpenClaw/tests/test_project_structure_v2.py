from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("project_structure", ROOT / "scripts" / "13_ensure_project_structure.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectStructureV2Tests(unittest.TestCase):
    def test_new_project_creates_edit_handoff_not_legacy_editor_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            project.mkdir()
            MODULE.ensure_structure(project)
            self.assertTrue((project / "90_Draft_Project" / "edit_handoff" / "README.md").is_file())
            self.assertFalse((project / "90_Draft_Project" / "剪映工程").exists())
            note = (project / "90_Draft_Project" / "工程说明.md").read_text(encoding="utf-8")
            self.assertIn("标准剪辑交接包", note)
            self.assertIn("可编辑时间线", note)


if __name__ == "__main__":
    unittest.main()
