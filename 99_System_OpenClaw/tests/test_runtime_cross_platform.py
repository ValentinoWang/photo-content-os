from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from runtime_paths import platform_contract_name, runtime_dir, runtime_python, supported_python  # noqa: E402


class RuntimePathTests(unittest.TestCase):
    def test_platform_runtime_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(runtime_python(root, platform="win32"), root / "99_System_OpenClaw" / ".venv-content-os" / "Scripts" / "python.exe")
            self.assertEqual(runtime_python(root, platform="darwin"), root / "99_System_OpenClaw" / ".venv-content-os" / "bin" / "python")
        self.assertEqual(platform_contract_name("win32"), "windows")
        self.assertEqual(platform_contract_name("darwin"), "macos")
        self.assertTrue(supported_python((3, 11, 0)))
        self.assertFalse(supported_python((3, 10, 9)))

    def test_explicit_repository_root_is_not_resolved(self):
        root = Path("/var/tmp/photo-content-os")
        self.assertEqual(runtime_dir(root), root / "99_System_OpenClaw" / ".venv-content-os")


if __name__ == "__main__":
    unittest.main()
