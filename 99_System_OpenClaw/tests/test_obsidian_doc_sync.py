from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from _support import load_script


check_obsidian_doc_sync = load_script("30_check_obsidian_doc_sync.py", "check_obsidian_doc_sync")


class ObsidianDocSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.local_root = self.base / "local"
        self.obsidian_root = self.base / "obsidian"
        self.local_root.mkdir()
        self.obsidian_root.mkdir()
        self.source = self.local_root / "source.md"
        self.target = self.obsidian_root / "target.md"
        self.contract = self.local_root / "contract.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_contract(self, common_markers: list[str] | None = None, target_markers: list[str] | None = None) -> None:
        contract = {
            "spec_version": "content_os_doc_sync_v0.1",
            "defaults": {
                "fail_if_source_newer_than_target": True,
                "mtime_grace_seconds": 0,
            },
            "pairs": [
                {
                    "name": "sample_pair",
                    "source_paths": ["$LOCAL_ROOT/source.md"],
                    "target_paths": [
                        {
                            "path": "$OBSIDIAN_ROOT/target.md",
                            "markers": target_markers or ["target-only"],
                        }
                    ],
                    "common_markers": common_markers or ["shared-rule"],
                }
            ],
        }
        self.contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_sync_check(self) -> list[str]:
        return check_obsidian_doc_sync.run_checks(self.contract, self.local_root, self.obsidian_root)

    def test_passes_when_source_and_target_contain_required_markers(self) -> None:
        self.write_contract()
        self.source.write_text("shared-rule\nsource note\n", encoding="utf-8")
        self.target.write_text("shared-rule\ntarget-only\n", encoding="utf-8")
        os.utime(self.source, (100, 100))
        os.utime(self.target, (200, 200))

        self.assertEqual([], self.run_sync_check())

    def test_fails_when_target_is_missing_marker(self) -> None:
        self.write_contract()
        self.source.write_text("shared-rule\n", encoding="utf-8")
        self.target.write_text("shared-rule\n", encoding="utf-8")
        os.utime(self.source, (100, 100))
        os.utime(self.target, (200, 200))

        errors = self.run_sync_check()

        self.assertTrue(any("missing target markers: target-only" in error for error in errors))

    def test_fails_when_source_is_newer_than_target(self) -> None:
        self.write_contract()
        self.source.write_text("shared-rule\n", encoding="utf-8")
        self.target.write_text("shared-rule\ntarget-only\n", encoding="utf-8")
        os.utime(self.source, (300, 300))
        os.utime(self.target, (200, 200))

        errors = self.run_sync_check()

        self.assertTrue(any("source doc is newer than Obsidian target" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
