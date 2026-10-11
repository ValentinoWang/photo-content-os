from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SYSTEM))

from desktop.server import serve  # noqa: E402


class StructuredEDLBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.server = serve(state_dir=Path(self.temp.name) / "state", host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path: str, *, method: str = "GET", body: dict | None = None, csrf: str | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if csrf:
            headers["X-Content-OS-CSRF"] = csrf
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def create_project(self, workspace: Path):
        _, bootstrap = self.request("/api/bootstrap")
        status, payload = self.request(
            "/api/projects",
            method="POST",
            csrf=bootstrap["csrfToken"],
            body={"title": "EDL bridge fixture", "localWorkspace": str(workspace)},
        )
        self.assertEqual(status, 201)
        return payload["project"], bootstrap["csrfToken"]

    @staticmethod
    def valid_source() -> dict:
        return {
            "schema_version": "edit_decision_list_v1",
            "doc_type": "edit_decision_list",
            "source_script_used": True,
            "generation_model": "fixture-model",
            "generation_reasoning": "fixture-reasoning",
            "clips": [
                {
                    "slot": 1,
                    "time_range": {"timeline_in": 0, "timeline_out": 2},
                    "source_start_sec": 0,
                    "purpose": "opening",
                    "visual_need": "person enters frame",
                    "caption": "start",
                    "candidate_files": ["01_Media/clip.mp4"],
                    "edit_note": "hard cut",
                }
            ],
            "missing_materials": [],
        }

    def test_valid_bridge_is_authoritative_and_keeps_studio_text_editable(self):
        workspace = Path(self.temp.name) / "workspace"
        workspace.mkdir()
        source_path = workspace / "06_edit_decision_list.json"
        raw_bytes = (json.dumps(self.valid_source(), separators=(",", ":")) + "\n").encode("utf-8")
        source_path.write_bytes(raw_bytes)
        project, csrf = self.create_project(workspace)

        status, saved = self.request(
            f"/api/projects/{project['id']}/documents/edl/patch",
            method="POST",
            csrf=csrf,
            body={
                "selectedBlockIds": ["edl-plan"],
                "replacements": {"edl-plan": "Studio editable text"},
                "expectedRevision": project["revision"],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(saved["project"]["documents"]["edl"]["blocks"][0]["body"], "Studio editable text")

        status, payload = self.request(f"/api/projects/{project['id']}/edl-bridge")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        bridge = payload["bridge"]
        self.assertEqual(bridge["status"], "valid")
        self.assertEqual(bridge["source"]["authority_file"], "06_edit_decision_list.json")
        self.assertEqual(
            bridge["source"]["content_digest"],
            "sha256:" + hashlib.sha256(raw_bytes).hexdigest(),
        )
        self.assertEqual(bridge["validation"]["status"], "valid")
        self.assertEqual(bridge["validation"]["validator"], "edl_contract.normalise_edl")
        self.assertEqual(bridge["content"]["schema_version"], "edit_decision_list_v1")
        self.assertEqual(bridge["content"]["clips"][0]["time_range"], "0.000-2.000")
        self.assertNotIn("Studio editable text", json.dumps(bridge, ensure_ascii=False))

    def test_required_schema_fields_fail_closed_before_normalisation(self):
        workspace = Path(self.temp.name) / "workspace-required"
        workspace.mkdir()
        source_path = workspace / "06_edit_decision_list.json"
        project, _ = self.create_project(workspace)
        route = f"/api/projects/{project['id']}/edl-bridge"

        for field in (
            "schema_version",
            "doc_type",
            "source_script_used",
            "generation_model",
            "generation_reasoning",
            "clips",
            "missing_materials",
        ):
            with self.subTest(scope="document", field=field):
                payload = self.valid_source()
                del payload[field]
                source_path.write_text(json.dumps(payload), encoding="utf-8")
                status, response = self.request(route)
                self.assertEqual(status, 422)
                self.assertEqual(response["bridge"]["validation"]["code"], f"{field}_missing")
                self.assertIsNone(response["bridge"]["content"])

        for field in (
            "slot",
            "time_range",
            "source_start_sec",
            "purpose",
            "visual_need",
            "caption",
            "candidate_files",
            "edit_note",
        ):
            with self.subTest(scope="clip", field=field):
                payload = self.valid_source()
                del payload["clips"][0][field]
                source_path.write_text(json.dumps(payload), encoding="utf-8")
                status, response = self.request(route)
                self.assertEqual(status, 422)
                self.assertEqual(response["bridge"]["validation"]["code"], f"clip_{field}_missing")
                self.assertIsNone(response["bridge"]["content"])

    def test_missing_malformed_schema_and_identity_fail_without_guessing(self):
        workspace = Path(self.temp.name) / "workspace"
        workspace.mkdir()
        project, _ = self.create_project(workspace)
        route = f"/api/projects/{project['id']}/edl-bridge"

        status, missing = self.request(route)
        self.assertEqual(status, 404)
        self.assertEqual(missing["error"]["code"], "edl_source_missing")
        self.assertEqual(missing["bridge"]["validation"]["status"], "missing")
        self.assertIsNone(missing["bridge"]["content"])

        source_path = workspace / "06_edit_decision_list.json"
        source_path.write_bytes(b"{\"clips\":")
        status, malformed = self.request(route)
        self.assertEqual(status, 422)
        self.assertEqual(malformed["error"]["code"], "edl_source_invalid")
        self.assertEqual(malformed["bridge"]["validation"]["code"], "invalid_json")
        self.assertIsNone(malformed["bridge"]["content"])
        self.assertNotIn(str(workspace), json.dumps(malformed, ensure_ascii=False))
        self.assertEqual(malformed, self.request(route)[1])

        invalid_schema = self.valid_source()
        invalid_schema["doc_type"] = "not_an_edl"
        source_path.write_text(json.dumps(invalid_schema), encoding="utf-8")
        status, schema_error = self.request(route)
        self.assertEqual(status, 422)
        self.assertEqual(schema_error["error"]["code"], "edl_contract_invalid")
        self.assertEqual(schema_error["bridge"]["validation"]["code"], "doc_type_invalid")
        self.assertIsNone(schema_error["bridge"]["content"])

        invalid_contract = self.valid_source()
        invalid_contract["clips"] = []
        source_path.write_text(json.dumps(invalid_contract), encoding="utf-8")
        status, contract_error = self.request(route)
        self.assertEqual(status, 422)
        self.assertEqual(contract_error["bridge"]["validation"]["code"], "edl_clips_missing")
        self.assertIsNone(contract_error["bridge"]["content"])

        source_path.unlink()
        source_path.mkdir()
        status, identity_error = self.request(route)
        self.assertEqual(status, 409)
        self.assertEqual(identity_error["error"]["code"], "edl_source_identity_invalid")
        self.assertEqual(identity_error["bridge"]["status"], "unavailable")
        self.assertIsNone(identity_error["bridge"]["content"])


if __name__ == "__main__":
    unittest.main()
