from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "22_probe_jianying_environment.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("jianying_probe_paths", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class JianyingProbePathTests(unittest.TestCase):
    def test_windows_probe_uses_known_projects_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            candidate = home / "AppData/Local/JianyingPro/User Data/Projects"
            capcut = home / "AppData/Local/CapCut/User Data/Projects"
            candidate.mkdir(parents=True)
            capcut.mkdir(parents=True)

            self.assertEqual(MODULE.find_jianying_roots(platform="win32", home=home), [str(candidate), str(capcut)])
            candidates = MODULE.jianying_root_candidates(platform="win32", home=home)
            self.assertIn(candidate, candidates)
            self.assertIn(capcut, candidates)


if __name__ == "__main__":
    unittest.main()
