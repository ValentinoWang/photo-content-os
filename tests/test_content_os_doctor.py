from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SYSTEM_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location("content_os_doctor", SCRIPTS_DIR / "43_content_os_doctor.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("doctor module could not be loaded")
doctor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = doctor
SPEC.loader.exec_module(doctor)


class ContentOsDoctorTests(unittest.TestCase):
    def test_optional_unsupported_capability_does_not_block_local_readiness(self) -> None:
        checks = [
            doctor.Check("local", True, True, "local ready"),
            doctor.Check(
                "cloud",
                False,
                False,
                "platform unsupported",
                state=doctor.CheckState.UNSUPPORTED,
            ),
        ]

        self.assertEqual(doctor.diagnosis_status(checks), "ready")

    def test_unavailable_optional_capability_requires_offline_mode(self) -> None:
        checks = [
            doctor.Check(
                "provider",
                False,
                False,
                "provider unavailable",
                state=doctor.CheckState.UNAVAILABLE,
            )
        ]

        self.assertEqual(doctor.diagnosis_status(checks), "blocked")
        self.assertEqual(doctor.diagnosis_status(checks, allow_offline=True), "ready")

    def test_required_error_blocks_even_in_offline_mode(self) -> None:
        checks = [doctor.Check("runtime", False, True, "runtime failed")]

        self.assertEqual(doctor.diagnosis_status(checks, allow_offline=True), "blocked")

    def test_windows_and_linux_collect_explicit_unsupported_pairing(self) -> None:
        for platform_name in ("windows", "linux"):
            with self.subTest(platform=platform_name), tempfile.TemporaryDirectory() as directory:
                with (
                    patch.object(doctor, "platform_contract_name", return_value=platform_name),
                    patch.object(doctor, "supported_python", return_value=True),
                    patch.object(doctor.shutil, "which", return_value="/fixture/tool"),
                ):
                    checks, metadata = doctor.collect_checks(Path(directory))

                pairing = next(check for check in checks if check.id == "openclaw_cloud_pairing")
                self.assertFalse(pairing.ok)
                self.assertFalse(pairing.required)
                self.assertEqual(pairing.state, doctor.CheckState.UNSUPPORTED.value)
                self.assertEqual(doctor.diagnosis_status(checks), "ready")
                self.assertTrue(metadata["local_core_supported"])


class EditingToolDoctorTests(unittest.TestCase):
    def apps(self, root):
        import plistlib
        for name in ("ChatCut.app", "kdenlive.app", "VideoFusion-macOS.app"):
            contents = root / name / "Contents"
            contents.mkdir(parents=True)
            with (contents / "Info.plist").open("wb") as handle:
                plistlib.dump({"CFBundleShortVersionString": "fixture-1"}, handle)

    def test_registered_without_handshake_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.apps(root)
            def failed(_):
                raise doctor.McpError("mcp_timeout")
            with patch.object(doctor, "melt_executable", return_value=None):
                tools = doctor.probe_editing_tools(applications=root, registration_reader=lambda: {"transport": {}}, session_factory=failed)
            self.assertEqual(tools["chatcut"]["status"], "unknown")
            self.assertTrue(tools["chatcut"]["mcp_registered"])
            self.assertFalse(tools["chatcut"]["connection_verified"])
            self.assertEqual(tools["jianying"]["scope"], "app_and_version_only")
            self.assertEqual(tools["jianying"]["version"], "fixture-1")
            self.assertNotIn("draft_roots", tools["jianying"])

    def test_real_handshake_evidence_required_for_online(self):
        class Session:
            def __init__(self, _): pass
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def list_tools(self): return []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.apps(root)
            with patch.object(doctor, "melt_executable", return_value=None):
                tools = doctor.probe_editing_tools(applications=root, registration_reader=lambda: {"transport": {}}, session_factory=Session)
            self.assertEqual(tools["chatcut"]["status"], "online")
            self.assertTrue(tools["chatcut"]["connection_verified"])

    def test_missing_registration_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.apps(root)
            def missing():
                raise doctor.McpError("mcp_not_registered")
            with patch.object(doctor, "melt_executable", return_value=None):
                tools = doctor.probe_editing_tools(applications=root, registration_reader=missing)
            self.assertEqual(tools["chatcut"]["status"], "unavailable")
            self.assertFalse(tools["chatcut"]["mcp_registered"])


if __name__ == "__main__":
    unittest.main()
