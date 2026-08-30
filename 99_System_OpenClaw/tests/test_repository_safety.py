from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _support import load_script


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "40_check_repository_safety.py"
repository_safety = load_script(SCRIPT.name, "repository_safety")


class RepositorySafetyTest(unittest.TestCase):
    def test_accepts_small_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path("99_System_OpenClaw/scripts/example.py")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_text("print('ok')\n", encoding="utf-8")

            self.assertEqual([], repository_safety.path_violations(root, relative))

    def test_rejects_personal_workspace_even_for_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path("01_Project_Workspace/private/readme.md")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_text("private\n", encoding="utf-8")

            self.assertIn("personal workspace path", repository_safety.path_violations(root, relative))

    def test_rejects_media_case_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path("fixtures/PHOTO.HEIC")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_bytes(b"not real media")

            self.assertIn("media or private-key extension", repository_safety.path_violations(root, relative))

    def test_rejects_machine_generated_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path(".github/.DS_Store")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_bytes(b"machine metadata")

            self.assertIn("machine-generated metadata", repository_safety.path_violations(root, relative))

    def test_rejects_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path("fixtures/oversized.bin")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_bytes(b"0" * (repository_safety.MAX_TRACKED_FILE_BYTES + 1))

            self.assertIn("file exceeds 5 MiB", repository_safety.path_violations(root, relative))


if __name__ == "__main__":
    unittest.main()
