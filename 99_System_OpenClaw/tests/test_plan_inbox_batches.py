import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import load_script


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "46_plan_inbox_batches.py"
planner = load_script("46_plan_inbox_batches.py", "plan_inbox_batches")


def item(media_id, captured_at, latitude, longitude, **extra):
    return {
        "media_id": media_id,
        "relative_path": f"intake/{media_id}.jpg",
        "stem": media_id,
        "source_type": "iPhone",
        "captured_at": captured_at,
        "gps_latitude": latitude,
        "gps_longitude": longitude,
        "live_photo_status": None,
        **extra,
    }


class InboxBatchPlannerTests(unittest.TestCase):
    def test_splits_events_by_time_and_distance_and_counts_sources(self):
        manifest = {
            "manifest_version": 2,
            "items": [
                item("a", "2026-09-02T09:00:00+00:00", 22.5431, 114.0579),
                item("b", "2026-09-02T09:10:00+00:00", 22.5432, 114.0580, source_type="相机"),
                item("c", "2026-09-02T10:00:01+00:00", 22.5432, 114.0580),
                item("d", "2026-09-02T10:05:00+00:00", 22.5632, 114.0580),
            ],
        }
        plan = planner.plan_batches(manifest, manifest_sha256="a" * 64)
        self.assertEqual([["a", "b"], ["c"], ["d"]], [batch["media_ids"] for batch in plan["batches"]])
        self.assertEqual(
            [{"source_type": "iPhone", "count": 1}, {"source_type": "相机", "count": 1}],
            plan["batches"][0]["source_composition"],
        )
        self.assertEqual("pending", plan["confirmation_status"])
        self.assertEqual("not_requested", plan["migration_status"])

    def test_live_group_is_an_atomic_unit_even_when_member_timestamps_differ(self):
        live_fields = {"live_photo_status": "complete_heic_mov_xmp", "relative_path": "intake/live/IMG_1.HEIC", "stem": "IMG_1"}
        manifest = {
            "manifest_version": 2,
            "items": [
                item("still", "2026-09-02T09:00:00+00:00", 22.5431, 114.0579, **live_fields),
                item("motion", "2026-09-02T09:04:00+00:00", 22.5431, 114.0579, **{**live_fields, "relative_path": "intake/live/IMG_1.MOV"}),
                item("next", "2026-09-02T09:05:00+00:00", 22.5431, 114.0579),
            ],
        }
        plan = planner.plan_batches(manifest, manifest_sha256="b" * 64)
        self.assertEqual(1, len(plan["batches"]))
        self.assertEqual(["motion", "still", "next"], plan["batches"][0]["media_ids"])
        self.assertEqual(["live:intake/live:IMG_1"], plan["batches"][0]["live_group_unit_ids"])

    def test_missing_metadata_is_pending_and_never_assigned(self):
        manifest = {
            "manifest_version": 2,
            "items": [
                item("no-time", None, 22.5431, 114.0579),
                item("no-gps", "2026-09-02T09:00:00+00:00", None, None),
                item("valid", "2026-09-02T09:01:00+00:00", 22.5431, 114.0579),
            ],
        }
        plan = planner.plan_batches(manifest, manifest_sha256="c" * 64)
        self.assertEqual([["valid"]], [batch["media_ids"] for batch in plan["batches"]])
        self.assertEqual(
            {"media:no-time": ["missing_captured_at"], "media:no-gps": ["missing_gps"]},
            {entry["unit_id"]: entry["reasons"] for entry in plan["pending_items"]},
        )

    def test_reordering_manifest_items_does_not_change_the_plan(self):
        items = [
            item("later", "2026-09-02T10:00:00+00:00", 22.5431, 114.0579),
            item("first", "2026-09-02T09:00:00+00:00", 22.5431, 114.0579),
            item("second", "2026-09-02T09:10:00+00:00", 22.5431, 114.0579),
        ]
        original = planner.plan_batches({"manifest_version": 2, "items": items}, manifest_sha256="d" * 64)
        reordered = planner.plan_batches({"manifest_version": 2, "items": list(reversed(items))}, manifest_sha256="d" * 64)
        self.assertEqual(original, reordered)

    def test_cli_writes_a_plan_only_and_uses_the_manifest_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "media_manifest.json"
            raw = json.dumps({"manifest_version": 2, "items": [item("one", "2026-09-02T09:00:00+00:00", 22.5, 114.0)]}).encode()
            manifest_path.write_bytes(raw)
            output_path = root / "nested" / "plan.json"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), str(manifest_path), "--output", str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual("planned", json.loads(completed.stdout)["status"])
            self.assertTrue(output_path.is_file())
            plan = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(f"sha256:{hashlib.sha256(raw).hexdigest()}", plan["input_manifest"]["manifest_sha256"])
            self.assertEqual([manifest_path, output_path], sorted(root.rglob("*.json")))


if __name__ == "__main__":
    unittest.main()
