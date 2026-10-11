#!/usr/bin/env python3
"""Focused tests for the local archive location configuration fixture."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESKTOP_DIR = PROJECT_ROOT / "99_System_OpenClaw" / "desktop"
if str(DESKTOP_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_DIR))

from archive_location_config import (  # noqa: E402
    ArchiveLocationConfig,
    ArchiveLocationConfigError,
    ArchiveLocationConfigStore,
    LifecycleState,
    MediaManifestEntry,
    ReadbackResult,
    ReadbackState,
    create_config,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
OBSERVED_A = "2026-09-01T01:02:03Z"
OBSERVED_B = "2026-09-01T02:03:04Z"


def manifest(path: str, digest: str = HASH_A) -> list[dict[str, str]]:
    return [{"relative_path": path, "sha256": digest}]


class ArchiveLocationConfigTests(unittest.TestCase):
    def configured(self) -> ArchiveLocationConfig:
        return (
            create_config()
            .add_location(
                location_id="disk-a",
                display_name="Primary archive",
                location_ref="local/disk-a",
                media_manifest=manifest("camera/a.jpg"),
                observed_at=OBSERVED_A,
            )
            .add_location(
                location_id="disk-b",
                display_name="Secondary archive",
                location_ref="local/disk-b",
                media_manifest=manifest("camera/b.jpg", HASH_B),
                observed_at=OBSERVED_B,
            )
        )

    def test_multiple_locations_keep_independent_manifests_and_readback(self) -> None:
        config = self.configured()
        checked = config.with_readback(
            "disk-a",
            lambda location: location.media_manifest[0].sha256 == HASH_A,
            checked_at="2026-09-01T03:04:05Z",
        )
        failed = checked.with_readback(
            "disk-b",
            lambda location: ReadbackResult.failed("fixture_unavailable"),
            checked_at="2026-09-01T03:05:05Z",
        )

        first = failed.location("disk-a")
        second = failed.location("disk-b")
        self.assertEqual(first.readback_state, ReadbackState.VERIFIED)
        self.assertEqual(second.readback_state, ReadbackState.FAILED)
        self.assertEqual(first.media_manifest[0].sha256, HASH_A)
        self.assertEqual(second.media_manifest[0].sha256, HASH_B)
        self.assertEqual(first.observed_at, OBSERVED_A)
        self.assertEqual(second.observed_at, OBSERVED_B)
        self.assertIsNone(config.location("disk-b").readback_at)

    def test_lifecycle_is_separate_from_location_and_readback_state(self) -> None:
        before = self.configured().with_readback(
            "disk-a",
            lambda _location: True,
            checked_at="2026-09-01T04:05:06Z",
        )
        after = before.with_lifecycle(LifecycleState.ARCHIVED)

        self.assertEqual(after.lifecycle, LifecycleState.ARCHIVED)
        self.assertEqual(after.locations, before.locations)
        self.assertEqual(after.location("disk-a").readback_state, ReadbackState.VERIFIED)
        self.assertEqual(after.location("disk-a").observed_at, OBSERVED_A)
        self.assertEqual(after.location("disk-b").readback_state, ReadbackState.UNKNOWN)

    def test_invalid_content_hashes_are_rejected(self) -> None:
        for digest in ("a" * 63, "A" * 64, "g" * 64):
            with self.subTest(digest=digest):
                with self.assertRaises(ArchiveLocationConfigError):
                    MediaManifestEntry(relative_path="clip.jpg", sha256=digest)

    def test_path_escape_absolute_path_and_url_are_rejected(self) -> None:
        bad_manifest_paths = ("../clip.jpg", "/clip.jpg", "C:\\clip.jpg", "camera/../clip.jpg")
        for path in bad_manifest_paths:
            with self.subTest(path=path):
                with self.assertRaises(ArchiveLocationConfigError):
                    MediaManifestEntry(relative_path=path, sha256=HASH_A)

        for location_ref in ("../disk", "/Volumes/archive", "https://example.invalid/archive", "local/../disk"):
            with self.subTest(location_ref=location_ref):
                with self.assertRaises(ArchiveLocationConfigError):
                    self.configured().add_location(
                        location_id="disk-c",
                        display_name="Third archive",
                        location_ref=location_ref,
                        media_manifest=manifest("clip.jpg"),
                    )

    def test_unknown_fields_duplicate_locations_and_invalid_records_are_rejected(self) -> None:
        raw = self.configured().to_dict()

        unknown_root = copy.deepcopy(raw)
        unknown_root["unexpected"] = True
        with self.assertRaises(ArchiveLocationConfigError):
            ArchiveLocationConfig.from_dict(unknown_root)

        unknown_entry = copy.deepcopy(raw)
        unknown_entry["locations"][0]["unexpected"] = True
        with self.assertRaises(ArchiveLocationConfigError):
            ArchiveLocationConfig.from_dict(unknown_entry)

        duplicate = copy.deepcopy(raw)
        duplicate["locations"].append(copy.deepcopy(duplicate["locations"][0]))
        with self.assertRaises(ArchiveLocationConfigError):
            ArchiveLocationConfig.from_dict(duplicate)

        invalid_state = copy.deepcopy(raw)
        invalid_state["locations"][0]["readback_state"] = "verified"
        with self.assertRaises(ArchiveLocationConfigError):
            ArchiveLocationConfig.from_dict(invalid_state)

    def test_persistence_and_atomic_write_keep_readback_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory) / "fixture-work"
            store = ArchiveLocationConfigStore(work_dir)
            initial = store.initialize()
            initial = initial.add_location(
                location_id="disk-a",
                display_name="Fixture archive",
                location_ref="fixture/disk-a",
                media_manifest=[MediaManifestEntry("clip.jpg", HASH_A)],
                observed_at=OBSERVED_A,
            )
            store.save(initial)
            persisted = store.readback_location(
                "disk-a",
                lambda location: location.media_manifest == (MediaManifestEntry("clip.jpg", HASH_A),),
                checked_at="2026-09-01T05:06:07Z",
            )
            reloaded = ArchiveLocationConfigStore(work_dir).load()

            self.assertEqual(reloaded, persisted)
            self.assertEqual(reloaded.location("disk-a").readback_state, ReadbackState.VERIFIED)
            self.assertEqual(reloaded.location("disk-a").readback_at, "2026-09-01T05:06:07Z")
            self.assertEqual(list(work_dir.glob("*.tmp")), [])
            payload = json.loads(store.config_path.read_text(encoding="utf-8"))
            self.assertNotIn(str(work_dir), json.dumps(payload, ensure_ascii=False))

    def test_reader_is_the_only_update_route_for_verified_state(self) -> None:
        config = self.configured()
        lifecycle_changed = config.with_lifecycle("archived")
        self.assertEqual(lifecycle_changed.location("disk-a").readback_state, ReadbackState.UNKNOWN)

        reader_calls: list[str] = []

        class FakeReader:
            def readback(self, location):
                reader_calls.append(location.location_id)
                return ReadbackResult.verified()

        verified = lifecycle_changed.with_readback(
            "disk-a",
            FakeReader(),
            checked_at="2026-09-01T06:07:08Z",
        )
        self.assertEqual(reader_calls, ["disk-a"])
        self.assertEqual(verified.location("disk-a").readback_state, ReadbackState.VERIFIED)


if __name__ == "__main__":
    unittest.main()
