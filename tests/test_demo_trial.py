from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "create_demo_project.py"


class DemoTrialTest(unittest.TestCase):
    def test_creates_scannable_synthetic_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_name = "20260814_照片整理协作测试"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--workspace-root",
                    str(workspace),
                    "--project-name",
                    project_name,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            project = workspace / "projects" / "demo" / project_name
            manifest_path = project / "ai-analysis" / "media-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(3, len(manifest["items"]))
            self.assertTrue(all(item["analysis_eligible"] for item in manifest["items"]))
            self.assertTrue((project / "icloud-selected").is_dir())
            self.assertTrue((project / "draft-project" / "edit-handoff").is_dir())
            self.assertTrue((project / "output" / "final").is_dir())

    def test_refuses_to_overwrite_existing_demo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_name = "existing_demo"
            project = workspace / "projects" / "demo" / project_name
            project.mkdir(parents=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--workspace-root",
                    str(workspace),
                    "--project-name",
                    project_name,
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("demo project already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()
