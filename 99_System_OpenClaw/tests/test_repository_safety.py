from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "40_check_repository_safety.py"
SPEC = importlib.util.spec_from_file_location("repository_safety", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load repository safety module: {SCRIPT}")
repository_safety = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repository_safety)


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

    def test_rejects_oversized_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            relative = Path("fixtures/oversized.bin")
            (root / relative).parent.mkdir(parents=True)
            (root / relative).write_bytes(b"0" * (repository_safety.MAX_TRACKED_FILE_BYTES + 1))

            self.assertIn("file exceeds 5 MiB", repository_safety.path_violations(root, relative))


if __name__ == "__main__":
    unittest.main()
