from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any


SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from desktop.upstream_session import (  # noqa: E402
    UpstreamSessionConsumer,
    UpstreamSessionContractError,
)


def paired_result(
    *,
    principal_id: str = "principal-1",
    roles: list[str] | None = None,
    session_ref: str = "session-ref-1",
    revoked: bool = False,
) -> dict[str, Any]:
    return {
        "upstream_principal_id": principal_id,
        "roles": list(roles or ["creator"]),
        "revoked": revoked,
        "pairing_status": "paired",
        "session_ref": session_ref,
    }


def inactive_result(status: str) -> dict[str, Any]:
    return {
        "upstream_principal_id": None,
        "roles": [],
        "revoked": None,
        "pairing_status": status,
        "session_ref": None,
    }


class UpstreamSessionConsumerTests(unittest.TestCase):
    def test_default_state_keeps_all_local_features_available(self) -> None:
        consumer = UpstreamSessionConsumer()

        state = consumer.snapshot()

        self.assertTrue(state["local_features_available"])
        self.assertFalse(state["upstream_features_available"])
        self.assertIsNone(state["session_ref"])
        self.assertEqual(state["session_state"], "default")

    def test_accepts_safe_pairing_projection_and_enables_upstream_features(self) -> None:
        consumer = UpstreamSessionConsumer()

        state = consumer.consume(paired_result(roles=["creator", "reviewer"]))

        self.assertTrue(state["local_features_available"])
        self.assertTrue(state["upstream_features_available"])
        self.assertEqual(state["upstream_principal_id"], "principal-1")
        self.assertEqual(state["roles"], ["creator", "reviewer"])
        self.assertEqual(state["session_ref"], "session-ref-1")

    def test_missing_unknown_and_secret_fields_are_rejected_without_echoing_values(self) -> None:
        consumer = UpstreamSessionConsumer()
        secret = "super-secret-token-value"

        for malformed in (
            {key: value for key, value in paired_result().items() if key != "session_ref"},
            {**paired_result(), "unexpected": "ignored"},
            {**paired_result(), "access_token": secret},
        ):
            with self.subTest(malformed_keys=sorted(malformed)):
                with self.assertRaises(UpstreamSessionContractError) as raised:
                    consumer.consume(malformed)
                self.assertNotIn(secret, str(raised.exception))
                self.assertFalse(consumer.snapshot()["upstream_features_available"])
                self.assertIsNone(consumer.snapshot()["session_ref"])

    def test_rejected_and_unavailable_results_keep_local_workbench_complete(self) -> None:
        consumer = UpstreamSessionConsumer()

        for status, expected_state in (
            ("rejected", "unpaired"),
            ("unavailable", "unavailable"),
            ("unsupported", "unsupported"),
        ):
            with self.subTest(status=status):
                state = consumer.consume(inactive_result(status))
                self.assertTrue(state["local_features_available"])
                self.assertFalse(state["upstream_features_available"])
                self.assertEqual(state["session_state"], expected_state)
                self.assertIsNone(state["session_ref"])

    def test_refresh_uses_injected_reader_and_replaces_old_session(self) -> None:
        consumer = UpstreamSessionConsumer()
        consumer.consume(paired_result(session_ref="old-ref"))
        calls: list[str] = []

        def reader(session_ref: str) -> dict[str, Any]:
            calls.append(session_ref)
            return paired_result(principal_id="principal-2", session_ref="new-ref", roles=["publisher"])

        state = consumer.refresh(reader)

        self.assertEqual(calls, ["old-ref"])
        self.assertEqual(state["upstream_principal_id"], "principal-2")
        self.assertEqual(state["session_ref"], "new-ref")
        self.assertEqual(state["roles"], ["publisher"])

    def test_expiry_revocation_and_reader_failure_remove_session_reference(self) -> None:
        consumer = UpstreamSessionConsumer()
        consumer.consume(paired_result())

        expired = consumer.expire()
        self.assertEqual(expired["session_state"], "expired")
        self.assertTrue(expired["local_features_available"])
        self.assertFalse(expired["upstream_features_available"])
        self.assertIsNone(expired["session_ref"])

        consumer.consume(paired_result())
        revoked = consumer.refresh(lambda _ref: paired_result(revoked=True))
        self.assertEqual(revoked["session_state"], "revoked")
        self.assertTrue(revoked["local_features_available"])
        self.assertFalse(revoked["upstream_features_available"])
        self.assertIsNone(revoked["session_ref"])

        consumer.consume(paired_result())
        failed = consumer.refresh(lambda _ref: (_ for _ in ()).throw(RuntimeError("provider secret")))
        self.assertEqual(failed["session_state"], "invalid")
        self.assertTrue(failed["local_features_available"])
        self.assertFalse(failed["upstream_features_available"])
        self.assertIsNone(failed["session_ref"])

    def test_logout_clears_all_upstream_state(self) -> None:
        consumer = UpstreamSessionConsumer()
        consumer.consume(paired_result())

        state = consumer.logout()

        self.assertEqual(state["session_state"], "signed_out")
        self.assertTrue(state["local_features_available"])
        self.assertFalse(state["upstream_features_available"])
        self.assertIsNone(state["upstream_principal_id"])
        self.assertEqual(state["roles"], [])
        self.assertIsNone(state["session_ref"])

    def test_refresh_does_not_call_reader_without_a_current_session(self) -> None:
        consumer = UpstreamSessionConsumer()
        calls: list[str] = []

        state = consumer.refresh(lambda ref: calls.append(ref) or paired_result())

        self.assertEqual(calls, [])
        self.assertEqual(state["session_state"], "default")
        self.assertTrue(state["local_features_available"])


if __name__ == "__main__":
    unittest.main()
