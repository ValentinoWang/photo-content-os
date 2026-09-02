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


if __name__ == "__main__":
    unittest.main()
