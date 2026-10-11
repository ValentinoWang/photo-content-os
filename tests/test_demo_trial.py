from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "39_create_demo_project.py"


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

            project = workspace / "01_Project_Workspace" / "00_Demo_试用" / project_name
            manifest_path = project / "_ai_analysis" / "media_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(3, len(manifest["items"]))
            self.assertTrue(all(item["analysis_eligible"] for item in manifest["items"]))
            self.assertTrue((project / "80_To_iCloudPhotos_精选入库").is_dir())
            self.assertTrue((project / "90_Draft_Project" / "edit_handoff").is_dir())
            self.assertTrue((project / "91_Output" / "Final").is_dir())

    def test_refuses_to_overwrite_existing_demo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            project_name = "existing_demo"
            project = workspace / "01_Project_Workspace" / "00_Demo_试用" / project_name
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
