#!/usr/bin/env python3
"""Unit tests for the user-initiated upstream identity pairing contract."""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import upstream_identity
from openclaw_product_contract import Compatibility
from upstream_identity import PairingRequest, pair_upstream_identity


def compatibility_state(*, platform: str, compatible: bool = True) -> Compatibility:
    return Compatibility(
        available=True,
        compatible=compatible,
        platform=platform,
        package_version="test",
        expected_digest="sha256:" + "0" * 64,
        actual_digest="sha256:" + "0" * 64,
        upstream_commit="0" * 40,
        reason=None if compatible else "upstream_platform_unsupported",
    )


def compatible_checker(*, require_cloud_platform: bool) -> Compatibility:
    if not require_cloud_platform:
        raise AssertionError("pairing must request the cloud-platform contract")
    return compatibility_state(platform="macos")


class FakeUpstreamClient:
    def __init__(self, existing: dict[str, object] | None = None) -> None:
        self.existing = existing
        self.readbacks: dict[str, dict[str, object]] = {}
        self.find_calls: list[str] = []
        self.create_calls: list[str] = []
        self.read_calls: list[str] = []

    def find_identity(self, local_pairing_intent: str) -> dict[str, object] | None:
        self.find_calls.append(local_pairing_intent)
        return self.existing

    def create_identity(self, local_pairing_intent: str) -> dict[str, object]:
        self.create_calls.append(local_pairing_intent)
        if self.existing is None:
            self.existing = {"principal_id": "upstream-created"}
        return self.existing

    def read_identity(self, principal_id: str) -> dict[str, object]:
        self.read_calls.append(principal_id)
        return self.readbacks[principal_id]


class UpstreamIdentityContractTests(unittest.TestCase):
    def test_unconfirmed_request_does_not_call_client(self) -> None:
        client = FakeUpstreamClient()
        result = pair_upstream_identity(
            PairingRequest(user_confirmed=False, local_pairing_intent="pair-now"),
            client,
            compatibility_checker=compatible_checker,
        )

        self.assertEqual(result["pairing_status"], "rejected")
        self.assertEqual(client.find_calls, [])
        self.assertEqual(client.create_calls, [])
        self.assertEqual(client.read_calls, [])

    def test_missing_confirmation_or_intent_is_rejected_without_client_call(self) -> None:
        client = FakeUpstreamClient()
        for request in (
            {"local_pairing_intent": "pair-now"},
            {"user_confirmed": True, "local_pairing_intent": "   "},
        ):
            with self.subTest(request=request):
                result = pair_upstream_identity(request, client, compatibility_checker=compatible_checker)
                self.assertEqual(result["pairing_status"], "rejected")

        self.assertEqual(client.find_calls, [])
        self.assertEqual(client.create_calls, [])
        self.assertEqual(client.read_calls, [])

    def test_existing_account_is_read_back(self) -> None:
        client = FakeUpstreamClient(existing={"principal_id": "upstream-existing"})
        client.readbacks["upstream-existing"] = {
            "principal_id": "upstream-existing",
            "roles": ["editor", "editor", "reviewer"],
            "revoked": False,
            "session_ref": "session-existing",
        }

        result = pair_upstream_identity(
            PairingRequest(user_confirmed=True, local_pairing_intent="  local-intent  "),
            client,
            compatibility_checker=compatible_checker,
        )

        self.assertEqual(result["upstream_principal_id"], "upstream-existing")
        self.assertEqual(result["roles"], ["editor", "reviewer"])
        self.assertIs(result["revoked"], False)
        self.assertEqual(result["pairing_status"], "paired")
        self.assertEqual(result["session_ref"], "session-existing")
        self.assertEqual(client.find_calls, ["local-intent"])
        self.assertEqual(client.create_calls, [])
        self.assertEqual(client.read_calls, ["upstream-existing"])

    def test_absent_account_is_created_once_and_then_reused(self) -> None:
        client = FakeUpstreamClient()
        client.readbacks["upstream-created"] = {
            "principal_id": "upstream-created",
            "roles": ["creator"],
            "revoked": False,
            "session_ref": "session-created",
        }
        request = PairingRequest(user_confirmed=True, local_pairing_intent="local-intent")

        first = pair_upstream_identity(request, client, compatibility_checker=compatible_checker)
        second = pair_upstream_identity(request, client, compatibility_checker=compatible_checker)

        self.assertEqual(first, second)
        self.assertEqual(client.create_calls, ["local-intent"])
        self.assertEqual(client.find_calls, ["local-intent", "local-intent"])
        self.assertEqual(client.read_calls, ["upstream-created", "upstream-created"])

    def test_revoked_account_is_returned_as_paired_and_revoked(self) -> None:
        client = FakeUpstreamClient(existing={"principal_id": "upstream-revoked"})
        client.readbacks["upstream-revoked"] = {
            "principal_id": "upstream-revoked",
            "roles": ["viewer"],
            "revoked": True,
            "session_ref": "session-revoked",
        }

        result = pair_upstream_identity(
            PairingRequest(user_confirmed=True, local_pairing_intent="local-intent"),
            client,
            compatibility_checker=compatible_checker,
        )

        self.assertIs(result["revoked"], True)
        self.assertEqual(result["pairing_status"], "paired")

    def test_windows_and_linux_are_stably_unavailable_without_client_calls(self) -> None:
        for platform in ("windows", "linux"):
            with self.subTest(platform=platform):
                client = FakeUpstreamClient()
                result = pair_upstream_identity(
                    PairingRequest(user_confirmed=True, local_pairing_intent="local-intent"),
                    client,
                    compatibility_checker=lambda **_: compatibility_state(platform=platform, compatible=False),
                )

                self.assertEqual(result["pairing_status"], "unavailable")
                self.assertIsNone(result["upstream_principal_id"])
                self.assertEqual(result["roles"], [])
                self.assertIsNone(result["revoked"])
                self.assertIsNone(result["session_ref"])
                self.assertEqual(client.find_calls, [])
                self.assertEqual(client.create_calls, [])
                self.assertEqual(client.read_calls, [])

    def test_default_compatibility_uses_cloud_platform_requirement(self) -> None:
        client = FakeUpstreamClient()
        with patch.object(
            upstream_identity,
            "compatibility",
            return_value=compatibility_state(platform="linux", compatible=False),
        ) as checker:
            result = pair_upstream_identity(
                PairingRequest(user_confirmed=True, local_pairing_intent="local-intent"),
                client,
            )

        checker.assert_called_once_with(require_cloud_platform=True)
        self.assertEqual(result["pairing_status"], "unavailable")
        self.assertEqual(client.find_calls, [])

    def test_readback_is_allowlisted_and_roles_are_deduplicated(self) -> None:
        client = FakeUpstreamClient(existing={"principal_id": "upstream-safe"})
        client.readbacks["upstream-safe"] = {
            "principal_id": "upstream-safe",
            "roles": ["editor", "editor", "reviewer"],
            "revoked": False,
            "session_ref": "session-safe",
            "password": "must-not-escape",
            "access_token": "must-not-escape",
            "refresh_token": "must-not-escape",
            "api_key": "must-not-escape",
            "unrelated": "must-not-escape",
        }

        result = pair_upstream_identity(
            PairingRequest(user_confirmed=True, local_pairing_intent="local-intent"),
            client,
            compatibility_checker=compatible_checker,
        )

        self.assertEqual(set(result), {
            "upstream_principal_id",
            "roles",
            "revoked",
            "pairing_status",
            "session_ref",
        })
        self.assertEqual(result["roles"], ["editor", "reviewer"])
        for forbidden in ("password", "access_token", "refresh_token", "api_key", "unrelated"):
            self.assertNotIn(forbidden, result)

    def test_production_module_has_no_local_account_store_or_transport(self) -> None:
        source = inspect.getsource(upstream_identity)
        for forbidden in ("sqlite3", "shelve", "dbm", "requests", "urllib", "http.client"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
