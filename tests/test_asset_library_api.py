"""Focused HTTP contracts for the read-only reusable asset library API."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
SCRIPTS = SYSTEM / "scripts"
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import asset_library_index  # noqa: E402
from desktop.server import serve  # noqa: E402


class AssetLibraryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.index_path = self.root / "outside-state" / "index.json"
        self.write_index()
        self.server = serve(
            state_dir=self.root / "state",
            host="127.0.0.1",
            port=0,
            asset_index_path=self.index_path,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path: str) -> tuple[int, dict]:
        request = urllib.request.Request(self.base + path, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def write_index(self) -> None:
        assets = [
            self.asset("0123456789ab", "Reusable_人物", ["人物", "开场"], ["开场"]),
            self.asset("abcdef012345", "Reusable_校园", ["校园", "转场"], ["转场"]),
        ]
        index = asset_library_index.empty_index()
        for asset in assets:
            index, changed = asset_library_index.upsert_asset(index, asset)
            self.assertTrue(changed)
        asset_library_index.save_index(self.index_path, index)

    @staticmethod
    def asset(asset_id: str, category: str, tags: list[str], uses: list[str]) -> dict:
        source_relative_path = f"media/{asset_id}.mp4"
        source_project = "fixture-project"
        return {
            "asset_id": asset_library_index.stable_asset_id(source_project, source_relative_path),
            "title": f"素材 {asset_id}",
            "category": category,
            "card_path": f"{category}/{asset_id}.asset.md",
            "source_project": source_project,
            "source_relative_path": source_relative_path,
            "source_sha256": "a" * 64,
            "source_size": 42,
            "public_status": "待确认",
            "tags": asset_library_index.normalize_values(tags),
            "uses": asset_library_index.normalize_values(uses),
            "cuts": ["00:00-00:03"],
            "icloud_copy": None,
            "notes": "fixture",
        }

    def test_lists_filtered_assets_and_never_exposes_index_path(self) -> None:
        status, payload = self.request("/api/assets?category=Reusable_%E4%BA%BA%E7%89%A9&tags=%E4%BA%BA%E7%89%A9&tags=%E5%BC%80%E5%9C%BA")

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["query"], {"category": "Reusable_人物", "tags": ["人物", "开场"]})
        self.assertEqual(len(payload["assets"]), 1)
        self.assertEqual(payload["assets"][0]["category"], "Reusable_人物")
        self.assertNotIn(str(self.root), json.dumps(payload, ensure_ascii=False))
        self.assertNotIn(str(self.index_path), json.dumps(payload, ensure_ascii=False))

    def test_unavailable_index_does_not_disclose_its_absolute_location(self) -> None:
        self.index_path.write_text("{", encoding="utf-8")

        status, payload = self.request("/api/assets")

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "asset_library_unavailable")
        self.assertNotIn(str(self.root), json.dumps(payload, ensure_ascii=False))
        self.assertNotIn(str(self.index_path), json.dumps(payload, ensure_ascii=False))

    def test_statistics_and_asset_detail_are_read_only_public_index_projections(self) -> None:
        status, statistics = self.request("/api/assets/statistics")
        self.assertEqual(status, 200)
        self.assertEqual(statistics["statistics"]["asset_count"], 2)
        self.assertEqual(statistics["statistics"]["categories"], [
            {"name": "Reusable_人物", "asset_count": 1},
            {"name": "Reusable_校园", "asset_count": 1},
        ])

        asset_id = asset_library_index.stable_asset_id("fixture-project", "media/0123456789ab.mp4")
        status, detail = self.request(f"/api/assets/{asset_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["asset"]["asset_id"], asset_id)
        self.assertNotIn(str(self.root), json.dumps(detail, ensure_ascii=False))

        status, missing = self.request("/api/assets/000000000000")
        self.assertEqual(status, 404)
        self.assertEqual(missing["error"]["code"], "asset_not_found")

    def test_default_index_path_is_state_scoped_and_missing_index_is_empty(self) -> None:
        server = serve(state_dir=self.root / "missing-state", host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urllib.request.urlopen(base + "/api/assets/statistics") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["statistics"]["asset_count"], 0)
            self.assertFalse((self.root / "missing-state" / "asset-library" / "index.json").exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
