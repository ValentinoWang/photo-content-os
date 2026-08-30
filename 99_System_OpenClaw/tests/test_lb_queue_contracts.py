import json
import sys
import tempfile
import unittest
from pathlib import Path

from _support import load_script

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load(name):
    return load_script(name, register=True)


queue = load("33_enqueue_openclaw_queue_job")
runner = load("mac_openclaw_runner")
validator = load("validate_content_os_task")


class LBQueueContractTests(unittest.TestCase):
    def test_obsolete_native_import_type_has_no_output_branch(self):
        self.assertNotIn("create_jianying_native_import_pack", queue.default_requested_outputs({"task_type": "create_jianying_native_import_pack"}))

    def test_local_task_types_match_cloud_six(self):
        expected = {
            "local_material_match",
            "generate_edit_handoff_pack",
            "revise_local_edit_artifacts",
            "generate_otio_kdenlive_timeline",
            "local_output_review",
            "generate_ai_edit_log",
        }
        self.assertEqual(set(validator.SUPPORTED_TASK_TYPES), expected)
        self.assertEqual(set(runner.REQUIRED_ACTIONS), expected)

    def test_project_index_hit_and_miss_are_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "01_Project_Workspace"
            project = workspace / "project-a"
            project.mkdir(parents=True)
            (workspace / ".content_os_project_index.json").write_text(json.dumps({"project-a": str(project)}), encoding="utf-8")
            config = runner.RunnerConfig(vault_root=root, workspace_root=root)
            self.assertEqual(runner.find_project_by_id(config, "project-a"), project.resolve())
            with self.assertRaisesRegex(runner.RunnerError, "not found"):
                runner.find_project_by_id(config, "missing")

    def test_task_id_format_gate_rejects_ambiguous_ids(self):
        with self.assertRaisesRegex(validator.ValidationError, "task_id"):
            validator.validate_task({"spec_version": "content_os_v0.2", "task_id": "arbitrary", "task_type": "local_output_review"}, {}, Path("/tmp"))


if __name__ == "__main__":
    unittest.main()
