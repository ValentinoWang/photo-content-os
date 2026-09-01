#!/usr/bin/env python3
"""Contract tests for the injected, fail-closed media trash flow."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from media_delete_recommendations import (
    confirm_delete_selection,
    generate_delete_recommendations,
)
from media_trash_flow import (
    MacOSSystemTrashBackend,
    MediaTrashFlow,
    MediaTrashFlowError,
    UnavailableSystemTrashBackend,
    get_system_trash_backend,
)
import media_trash_flow


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class FakeTrashBackend:
    available = True
    recovery_proven = True

    def __init__(self, trash_root: Path) -> None:
        self.trash_root = trash_root
        self.trash_root.mkdir()
        self.fail_move: set[str] = set()
        self.fail_move_verification: set[str] = set()
        self.fail_restore_verification: set[str] = set()
        self.locations: dict[str, Path] = {}

    def move_to_trash(self, source: Path, *, candidate_number: str) -> str:
        if candidate_number in self.fail_move:
            raise RuntimeError("simulated backend move failure")
        location_id = f"fake-location-{candidate_number}"
        target = self.trash_root / candidate_number
        source.rename(target)
        self.locations[location_id] = target
        return location_id

    def verify_in_trash(self, trash_location_id: str, expected_sha256: str) -> bool:
        if trash_location_id.split("fake-location-", 1)[-1] in self.fail_move_verification:
            return False
        path = self.locations[trash_location_id]
        return path.is_file() and sha256_file(path) == expected_sha256

    def restore_from_trash(
        self,
        trash_location_id: str,
        destination: Path,
        *,
        candidate_number: str,
    ) -> object:
        source = self.locations[trash_location_id]
        source.rename(destination)
        return destination

    def verify_restored(self, restored_path: Path, expected_sha256: str) -> bool:
        candidate_number = restored_path.name
        if candidate_number in self.fail_restore_verification:
            return False
        return restored_path.is_file() and sha256_file(restored_path) == expected_sha256


class FakeMacOSRunner:
    """Move a temporary fixture as Foundation would, without calling macOS."""

    def __init__(self, trash_root: Path) -> None:
        self.trash_root = trash_root
        self.trash_root.mkdir()
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def __call__(self, command: Any, timeout_seconds: float) -> SimpleNamespace:
        self.calls.append((tuple(command), timeout_seconds))
        source = Path(command[-1])
        target = self.trash_root / f"system-{source.name}"
        source.replace(target)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"trash_path": str(target)}),
        )


class MediaTrashFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "work-root"
        self.root.mkdir()
        self.trash = Path(self.temp_dir.name) / "fake-trash"
        self.backend = FakeTrashBackend(self.trash)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_media(self, name: str, content: bytes) -> tuple[str, dict[str, Any]]:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        item = {
            "media_id": hashlib.sha1(name.encode("utf-8")).hexdigest()[:12],
            "relative_path": name,
            "sha256": sha256_file(path),
            "image_health": "healthy",
            "image_readable": True,
        }
        return name, item

    def confirmation_for(self, *items: dict[str, Any]) -> dict[str, Any]:
        candidates = generate_delete_recommendations({"items": list(items)})
        return confirm_delete_selection(
            candidates,
            [candidate["candidate_number"] for candidate in candidates],
            operation_time="2026-09-02T00:00:00Z",
        )

    def flow(self) -> MediaTrashFlow:
        return MediaTrashFlow(self.root, self.backend)

    def assert_flow_error(self, code: str, callback: Any) -> None:
        with self.assertRaises(MediaTrashFlowError) as context:
            callback()
        self.assertEqual(context.exception.code, code)

    def test_unconfirmed_and_missing_second_confirmation_are_rejected(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        confirmation = self.confirmation_for(item)
        suggested = dict(confirmation)
        suggested["state"] = "suggested"
        self.assert_flow_error(
            "confirmation_not_confirmed",
            lambda: self.flow().trash_confirmed_candidates(
                suggested,
                operator="operator-a",
                second_confirmation=True,
            ),
        )
        self.assert_flow_error(
            "second_confirmation_required",
            lambda: self.flow().trash_confirmed_candidates(
                confirmation,
                operator="operator-a",
                second_confirmation=False,
            ),
        )
        self.assertTrue((self.root / "one.jpg").is_file())

    def test_path_resolving_outside_explicit_work_root_is_rejected(self) -> None:
        outside = Path(self.temp_dir.name) / "outside.jpg"
        outside.write_bytes(b"outside")
        link = self.root / "linked.jpg"
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        _, item = self.write_media("placeholder.jpg", b"placeholder")
        item["relative_path"] = "linked.jpg"
        item["sha256"] = sha256_file(outside)
        confirmation = self.confirmation_for(item)
        self.assert_flow_error(
            "path_outside_work_root",
            lambda: self.flow().trash_confirmed_candidates(
                confirmation,
                operator="operator-a",
                second_confirmation=True,
            ),
        )
        self.assertTrue(outside.is_file())

    def test_successful_move_retains_a_complete_receipt(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        result = self.flow().trash_confirmed_candidates(
            self.confirmation_for(item),
            operator="operator-a",
            second_confirmation=True,
            operation_time="2026-09-02T01:00:00Z",
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["receipts"]), 1)
        receipt = result["receipts"][0]
        for field in (
            "candidate_number",
            "original_relative_path",
            "sha256",
            "operator",
            "operation_time",
            "trash_location_id",
            "post_move_verification",
            "restore_result",
        ):
            self.assertIn(field, receipt)
        self.assertEqual(receipt["original_relative_path"], "one.jpg")
        self.assertEqual(receipt["post_move_verification"]["verified"], True)
        self.assertFalse((self.root / "one.jpg").exists())

    def test_post_move_verification_failure_is_pending(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        candidate = generate_delete_recommendations({"items": [item]})[0]
        self.backend.fail_move_verification.add(candidate["candidate_number"])
        result = self.flow().trash_confirmed_candidates(
            self.confirmation_for(item),
            operator="operator-a",
            second_confirmation=True,
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["receipts"], [])
        self.assertEqual(result["pending"][0]["failure_code"], "post_move_verification_failed")
        self.assertEqual(result["pending"][0]["original_relative_path"], "one.jpg")

    def test_partial_failure_keeps_failed_source_in_place(self) -> None:
        _, first = self.write_media("first.jpg", b"first")
        _, second = self.write_media("second.jpg", b"second")
        candidates = generate_delete_recommendations({"items": [first, second]})
        self.backend.fail_move.add(candidates[1]["candidate_number"])
        result = self.flow().trash_confirmed_candidates(
            self.confirmation_for(first, second),
            operator="operator-a",
            second_confirmation=True,
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["receipts"]), 1)
        self.assertEqual(len(result["pending"]), 1)
        self.assertEqual(result["pending"][0]["candidate_number"], candidates[1]["candidate_number"])
        self.assertTrue((self.root / "second.jpg").is_file())

    def test_restore_success_is_verified_and_recorded(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        flow = self.flow()
        result = flow.trash_confirmed_candidates(
            self.confirmation_for(item),
            operator="operator-a",
            second_confirmation=True,
        )
        restored = flow.restore_receipt(result["receipts"][0], operation_time="2026-09-02T02:00:00Z")
        self.assertEqual(restored["status"], "restored")
        self.assertTrue(restored["restore_result"]["verified"])
        self.assertEqual(sha256_file(self.root / "one.jpg"), item["sha256"])

    def test_restore_verification_failure_is_pending(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        flow = self.flow()
        result = flow.trash_confirmed_candidates(
            self.confirmation_for(item),
            operator="operator-a",
            second_confirmation=True,
        )
        self.backend.fail_restore_verification.add("one.jpg")
        restored = flow.restore_receipt(result["receipts"][0])
        self.assertEqual(restored["status"], "pending")
        self.assertEqual(restored["restore_result"]["failure_code"], "restore_verification_failed")
        self.assertTrue((self.root / "one.jpg").is_file())

    def test_unavailable_backend_fails_closed(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        flow = MediaTrashFlow(self.root, UnavailableSystemTrashBackend("linux"))
        self.assert_flow_error(
            "unsupported_backend",
            lambda: flow.trash_confirmed_candidates(
                self.confirmation_for(item),
                operator="operator-a",
                second_confirmation=True,
            ),
        )
        self.assertTrue((self.root / "one.jpg").is_file())

    def test_macos_backend_uses_system_trash_receipt_and_recovers_after_restart(self) -> None:
        _, item = self.write_media("one.jpg", b"one")
        registry = Path(self.temp_dir.name) / "private-state" / "trash-receipts.json"
        runner = FakeMacOSRunner(Path(self.temp_dir.name) / "system-trash")
        with patch.object(media_trash_flow.sys, "platform", "darwin"):
            backend = MacOSSystemTrashBackend(registry_path=registry, runner=runner)
            flow = MediaTrashFlow(self.root, backend)
            result = flow.trash_confirmed_candidates(
                self.confirmation_for(item),
                operator="operator-a",
                second_confirmation=True,
            )
            receipt = result["receipts"][0]
            self.assertTrue(receipt["trash_location_id"].startswith("macos-"))
            self.assertNotIn(str(Path(self.temp_dir.name)), json.dumps(receipt))
            self.assertFalse((self.root / "one.jpg").exists())
            self.assertEqual(runner.calls[0][0][:4], ("/usr/bin/osascript", "-l", "JavaScript", "-e"))

            restarted = MacOSSystemTrashBackend(registry_path=registry, runner=runner)
            restored = MediaTrashFlow(self.root, restarted).restore_receipt(receipt)

        self.assertEqual(restored["status"], "restored")
        self.assertEqual(sha256_file(self.root / "one.jpg"), item["sha256"])
        self.assertEqual(json.loads(registry.read_text(encoding="utf-8"))["locations"], {})

    def test_macos_factory_is_available_only_on_macos(self) -> None:
        registry = Path(self.temp_dir.name) / "private-state" / "trash-receipts.json"
        with patch.object(media_trash_flow.sys, "platform", "darwin"):
            self.assertIsInstance(get_system_trash_backend("macos", registry_path=registry), MacOSSystemTrashBackend)
        with patch.object(media_trash_flow.sys, "platform", "linux"):
            self.assertIsInstance(get_system_trash_backend("macos", registry_path=registry), UnavailableSystemTrashBackend)


if __name__ == "__main__":
    unittest.main()
