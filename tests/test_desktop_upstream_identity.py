from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.upstream_identity import (  # noqa: E402
    UpstreamIdentityDiagnosisState,
    diagnose_upstream_identity,
)


@dataclass(frozen=True)
class CompatibilityFixture:
    available: bool
    compatible: bool
    platform: str = "macos"
    reason: str | None = None


class DesktopUpstreamIdentityTests(unittest.TestCase):
    def test_windows_and_linux_are_explicitly_unsupported_without_probe_calls(self) -> None:
        for platform in ("windows", "linux"):
            with self.subTest(platform=platform):
                calls: list[bool] = []
                diagnosis = diagnose_upstream_identity(
                    platform,
                    lambda **kwargs: calls.append(kwargs["require_cloud_platform"]),
                )

                self.assertEqual(diagnosis.state, UpstreamIdentityDiagnosisState.UNSUPPORTED)
                self.assertEqual(diagnosis.reason_code, "upstream_platform_unsupported")
                self.assertTrue(diagnosis.local_features_available)
                self.assertFalse(diagnosis.pairing_available)
                self.assertEqual(calls, [])

    def test_compatible_macos_probe_is_ready_and_requests_cloud_contract(self) -> None:
        calls: list[bool] = []

        def checker(*, require_cloud_platform: bool) -> CompatibilityFixture:
            calls.append(require_cloud_platform)
            return CompatibilityFixture(available=True, compatible=True)

        diagnosis = diagnose_upstream_identity("macos", checker)

        self.assertEqual(diagnosis.state, UpstreamIdentityDiagnosisState.READY)
        self.assertTrue(diagnosis.pairing_available)
        self.assertTrue(diagnosis.local_features_available)
        self.assertEqual(calls, [True])

    def test_unavailable_dependency_and_probe_error_remain_distinct(self) -> None:
        unavailable = diagnose_upstream_identity(
            "macos",
            lambda **_: CompatibilityFixture(
                available=False,
                compatible=False,
                reason="openclaw_media_not_installed",
            ),
        )
        error = diagnose_upstream_identity(
            "macos",
            lambda **_: (_ for _ in ()).throw(RuntimeError("provider credential")),
        )

        self.assertEqual(unavailable.state, UpstreamIdentityDiagnosisState.UNAVAILABLE)
        self.assertEqual(error.state, UpstreamIdentityDiagnosisState.ERROR)
        self.assertEqual(error.reason_code, "upstream_probe_error")
        self.assertNotIn("credential", str(error.to_dict()))
        self.assertTrue(unavailable.local_features_available)
        self.assertTrue(error.local_features_available)

    def test_missing_probe_is_unavailable_and_projection_has_no_session_material(self) -> None:
        diagnosis = diagnose_upstream_identity("macos")

        self.assertEqual(diagnosis.state, UpstreamIdentityDiagnosisState.UNAVAILABLE)
        self.assertEqual(
            set(diagnosis.to_dict()),
            {
                "state",
                "platform",
                "reason_code",
                "local_features_available",
                "pairing_available",
            },
        )


if __name__ == "__main__":
    unittest.main()
