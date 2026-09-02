"""Protected acceptance baseline for the 45-item OpenClaw Media checklist."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path


SYSTEM = Path(__file__).resolve().parents[1]
ROOT = SYSTEM.parent
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))

STATIC = SYSTEM / "desktop" / "static"
OPENAPI = SYSTEM / "schemas" / "desktop_openapi.json"
TRACEABILITY = SYSTEM / "schemas" / "full_checklist_traceability.json"

EXPECTED_ITEMS = {
    "D1", "D2", "D3", "A1", "A2",
    *{f"H{index}" for index in range(1, 5)},
    *{f"I{index}" for index in range(1, 6)},
    *{f"L{index}" for index in range(1, 6)},
    *{f"P{index}" for index in range(1, 7)},
    *{f"S{index}" for index in range(1, 6)},
    *{f"C{index}" for index in range(1, 4)},
    *{f"T{index}" for index in range(1, 7)},
    *{f"K{index}" for index in range(1, 7)},
}

REQUIRED_OPERATIONS = {
    "getBootstrap",
    "getDiagnostics",
    "getAnalysisBudget",
    "updateAnalysisBudget",
    "confirmInboxPlan",
    "addProjectAsset",
    "getSetupState",
    "updateSetupState",
    "getUpstreamTasks",
}


class FullChecklistStaticAcceptanceTests(unittest.TestCase):
    def test_openapi_is_generated_from_the_canonical_contract(self) -> None:
        api_contract = importlib.import_module("desktop.api_contract")
        checked_in = json.loads(OPENAPI.read_text(encoding="utf-8"))
        self.assertEqual(checked_in, api_contract.build_openapi())
        operation_ids = {
            operation["operationId"]
            for path_item in checked_in["paths"].values()
            for operation in path_item.values()
            if isinstance(operation, dict) and "operationId" in operation
        }
        self.assertTrue(REQUIRED_OPERATIONS.issubset(operation_ids))

    def test_all_45_items_have_executable_traceability(self) -> None:
        traceability = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
        items = traceability["items"]
        self.assertEqual(set(items), EXPECTED_ITEMS)
        for item_id, item in items.items():
            self.assertEqual(item["source_requirement_id"], f"SRC-CHECKLIST-{item_id}")
            self.assertTrue(item["implementation_paths"])
            self.assertTrue(item["acceptance_assertions"])
            self.assertNotIn("<", json.dumps(item, ensure_ascii=False))

    def test_prototype_tokens_and_nine_real_entries_are_preserved(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        app = (STATIC / "app.js").read_text(encoding="utf-8")
        css = (STATIC / "styles.css").read_text(encoding="utf-8")

        for token in ("--bg:#0D1314", "--ac:#4FB3BD", "Archivo", "Asap", "JetBrains Mono"):
            self.assertIn(token, css)
        for screen in ("home", "inbox", "library", "project", "settings"):
            self.assertIn(f'data-screen="{screen}"', html)
            self.assertIn(f'data-screen-panel="{screen}"', html)
        for surface in ("login", "setup", "cloud"):
            self.assertIn(f'data-surface-panel="{surface}"', html)
        self.assertIn('id="project-dialog"', html)
        for anchor in ("data-batch", "data-del", "data-set-pane", "data-preserved-k", "data-edl-view"):
            self.assertIn(anchor, app)
        for item in range(1, 7):
            self.assertIn(f'data-preserved-k="k{item}"', app)
        self.assertNotIn("/studio", html + app)

    def test_frontend_mutations_use_real_versioned_routes(self) -> None:
        app = (STATIC / "app.js").read_text(encoding="utf-8")
        for route in (
            "/api/diagnostics",
            "/api/settings/analysis-budget",
            "/inbox-plan/confirm",
            "/assets",
            "/api/setup/state",
            "/api/upstream/tasks",
        ):
            self.assertIn(route, app)
        self.assertIn("expectedRevision", app)
        self.assertIn("secondConfirmation", app)
        for status in ("queued", "running", "completed", "failed", "expired", "cancelled"):
            self.assertIn(status, app)


class FullChecklistHttpAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        server_module = importlib.import_module("desktop.server")
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp.name) / "state"
        self.server = server_module.serve(
            state_dir=self.state_dir,
            host="127.0.0.1",
            port=0,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def install_asset_index(self) -> str:
        asset_library = importlib.import_module("asset_library_index")
        asset_id = asset_library.stable_asset_id("source-project", "media/clip-a.mov")
        asset = {
            "asset_id": asset_id,
            "title": "验收素材",
            "category": "视频",
            "card_path": f"assets/{asset_id}.asset.md",
            "source_project": "source-project",
            "source_relative_path": "media/clip-a.mov",
            "source_sha256": "a" * 64,
            "source_size": 123,
            "public_status": "private",
            "tags": ["验收"],
            "uses": ["补充镜头"],
            "cuts": [],
            "icloud_copy": None,
            "notes": "",
        }
        index, _ = asset_library.upsert_asset(asset_library.empty_index(), asset)
        path = self.state_dir / "asset-library" / "index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        asset_library.save_index(path, index)
        return asset_id

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        csrf: str | None = None,
    ) -> tuple[int, dict]:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if csrf is not None:
            headers["X-Content-OS-CSRF"] = csrf
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_settings_diagnostics_setup_and_upstream_are_real_readbacks(self) -> None:
        _, bootstrap = self.request("/api/bootstrap")
        csrf = bootstrap["csrfToken"]

        status, diagnostics = self.request("/api/diagnostics")
        self.assertEqual(status, 200)
        self.assertIsInstance(diagnostics["diagnostics"]["checks"], list)
        self.assertNotIn("checkCount", diagnostics["diagnostics"])

        status, current_budget = self.request("/api/settings/analysis-budget")
        self.assertEqual(status, 200)
        revision = current_budget["analysisBudget"]["revision"]
        new_budget = {
            "preview_images_per_asset": 4,
            "deep_images_per_asset": 10,
            "max_preview_assets": 80,
            "max_deep_assets": 20,
            "max_audio_minutes": 90,
        }
        status, saved_budget = self.request(
            "/api/settings/analysis-budget",
            method="POST",
            csrf=csrf,
            body={"expectedRevision": revision, "budget": new_budget},
        )
        self.assertEqual(status, 200)
        self.assertEqual(saved_budget["analysisBudget"]["budget"], new_budget)
        status, conflict = self.request(
            "/api/settings/analysis-budget",
            method="POST",
            csrf=csrf,
            body={"expectedRevision": revision, "budget": new_budget},
        )
        self.assertEqual(status, 409)
        self.assertEqual(conflict["error"]["code"], "revision_conflict")

        _, setup = self.request("/api/setup/state")
        current_step = setup["setup"]["current_step"]
        status, setup = self.request(
            "/api/setup/state",
            method="POST",
            csrf=csrf,
            body={
                "expectedRevision": setup["setup"]["revision"],
                "step": current_step,
                "status": "ready",
            },
        )
        self.assertEqual(status, 200)
        self.assertNotEqual(setup["setup"]["current_step"], current_step)

        status, tasks = self.request("/api/upstream/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(tasks["tasks"], [])
        self.assertTrue(tasks["localFeaturesAvailable"])

    def test_project_batch_confirmation_and_asset_reference_are_versioned(self) -> None:
        _, bootstrap = self.request("/api/bootstrap")
        csrf = bootstrap["csrfToken"]
        workspace = Path(self.temp.name) / "workspace"
        manifest_path = workspace / "_ai_analysis" / "media_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "manifest_version": 1,
                    "items": [
                        {
                            "media_id": "clip-a",
                            "captured_at": "2026-09-02T09:00:00+00:00",
                            "gps_latitude": 22.5,
                            "gps_longitude": 113.9,
                            "source_type": "iphone",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        _, created = self.request(
            "/api/projects",
            method="POST",
            csrf=csrf,
            body={"title": "验收项目", "localWorkspace": str(workspace)},
        )
        project = created["project"]
        _, planned = self.request(
            f"/api/projects/{project['id']}/inbox-plan",
            method="POST",
            csrf=csrf,
            body={},
        )
        plan = planned["plan"]
        status, confirmed = self.request(
            f"/api/projects/{project['id']}/inbox-plan/confirm",
            method="POST",
            csrf=csrf,
            body={
                "expectedRevision": project["revision"],
                "planDigest": plan["plan_digest"],
                "batchId": plan["batches"][0]["batch_id"],
                "targetProjectId": project["id"],
            },
        )
        self.assertEqual(status, 200)
        project = confirmed["project"]
        self.assertEqual(confirmed["confirmation"]["status"], "confirmed")

        asset_id = self.install_asset_index()
        status, added = self.request(
            f"/api/projects/{project['id']}/assets",
            method="POST",
            csrf=csrf,
            body={
                "expectedRevision": project["revision"],
                "assetId": asset_id,
                "intendedUse": "b_roll",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(added["project"]["assets"][0]["asset_id"], asset_id)


if __name__ == "__main__":
    unittest.main()
