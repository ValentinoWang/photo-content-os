import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "45_archive_project.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("archive_project", SCRIPT_PATH)
archive_project = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(archive_project)


class ArchiveProjectTests(unittest.TestCase):
    def make_project(self, ready=True):
        root = Path(tempfile.mkdtemp()) / "20260829_demo"
        for name in ("90_Draft_Project", "91_Output/Final", "92_Aliyun_SyncReady", "待增加"):
            (root / name).mkdir(parents=True)
        (root / "91_Output/Final/final.mp4").write_bytes(b"final")
        checklist = "# check\n" if ready else "- [ ] remote mirror\n"
        (root / "92_Aliyun_SyncReady/项目同步检查清单.md").write_text(checklist, encoding="utf-8")
        return root

    def test_manifest_excludes_work_cache_and_hashes_files(self):
        project = self.make_project()
        (project / "App_WorkCache").mkdir()
        (project / "App_WorkCache/tmp.txt").write_text("x", encoding="utf-8")
        gate = archive_project.readiness(project)
        manifest = archive_project.build_manifest(project, gate)
        paths = {item["path"] for item in manifest["files"]}
        self.assertIn("91_Output/Final/final.mp4", paths)
        self.assertNotIn("App_WorkCache/tmp.txt", paths)
        self.assertEqual(len(manifest["files"][-1]["sha256"]), 64)

    def test_write_creates_index_and_manifest_without_deleting_media(self):
        project = self.make_project()
        gate = archive_project.readiness(project)
        manifest = archive_project.build_manifest(project, gate)
        archive_dir = project / "05_Archive_Cold_Storage" / "YYYY_Completed_Projects" / project.name
        archive_dir.mkdir(parents=True)
        (archive_dir / "archive_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        index = project / "02_Asset_Library" / "Project_Archive_Index"
        index.mkdir(parents=True)
        (index / f"{project.name}.archive.md").write_text(archive_project.index_card(project, gate, manifest), encoding="utf-8")
        self.assertTrue((project / "91_Output/Final/final.mp4").exists())
        self.assertTrue((archive_dir / "archive_manifest.json").exists())
        self.assertTrue((index / f"{project.name}.archive.md").exists())

    def test_unchecked_sync_blocks_readiness(self):
        project = self.make_project(ready=False)
        self.assertFalse(archive_project.readiness(project)["ready"])

    def test_verify_target_detects_hash_drift(self):
        project = self.make_project()
        gate = archive_project.readiness(project)
        manifest = archive_project.build_manifest(project, gate)
        manifest_path = project / "archive_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        target = Path(tempfile.mkdtemp())
        (target / "91_Output/Final").mkdir(parents=True)
        (target / "91_Output/Final/final.mp4").write_bytes(b"changed")
        result = archive_project.verify_target(manifest_path, target)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("mismatch" in item for item in result["failures"]))

    def test_restore_copies_and_verifies_to_new_directory(self):
        project = self.make_project()
        gate = archive_project.readiness(project)
        manifest = archive_project.build_manifest(project, gate)
        manifest_path = project / "archive_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        destination = Path(tempfile.mkdtemp()) / "restore"
        result = archive_project.restore_from_manifest(manifest_path, project, destination)
        self.assertEqual(result["status"], "passed")
        self.assertTrue((destination / "91_Output/Final/final.mp4").exists())

    def test_prune_plan_is_blocked_without_replica_receipts(self):
        project = self.make_project()
        result = archive_project.prune_plan(project, project / "missing.json", project / "missing.md", [])
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["safe"])


if __name__ == "__main__":
    unittest.main()
