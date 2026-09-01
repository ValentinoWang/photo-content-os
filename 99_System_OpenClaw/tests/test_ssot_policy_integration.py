"""HTTP integration coverage for the R4 Studio policy surface.

Every mutable media fixture is created under ``TemporaryDirectory``.  The test
injects transport-free collaborators so it never contacts a provider, an
upstream account system, ChatCut, or the current machine's system Trash.
"""

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
if str(SYSTEM) not in sys.path:
    sys.path.insert(0, str(SYSTEM))

from desktop.chatcut_mcp import ChatCutMcp  # noqa: E402
from desktop.server import serve  # noqa: E402
from openclaw_product_contract import Compatibility  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class FakeTrashBackend:
    available = True
    recovery_proven = True

    def __init__(self, trash_root: Path) -> None:
        self.trash_root = trash_root
        self.trash_root.mkdir(parents=True)
        self.locations: dict[str, Path] = {}

    def move_to_trash(self, source: Path, *, candidate_number: str) -> str:
        location_id = f"fixture-{candidate_number}"
        target = self.trash_root / candidate_number
        source.rename(target)
        self.locations[location_id] = target
        return location_id

    def verify_in_trash(self, location_id: str, expected_sha256: str) -> bool:
        path = self.locations[location_id]
        return path.is_file() and sha256_file(path) == expected_sha256

    def restore_from_trash(self, location_id: str, destination: Path, *, candidate_number: str) -> Path:
        _ = candidate_number
        return self.locations[location_id].rename(destination)

    def verify_restored(self, destination: Path, expected_sha256: str) -> bool:
        return destination.is_file() and sha256_file(destination) == expected_sha256


class FakeUpstreamClient:
    def find_identity(self, local_pairing_intent: str) -> dict[str, object]:
        self.intent = local_pairing_intent
        return {"principal_id": "upstream-user"}

    def create_identity(self, local_pairing_intent: str) -> dict[str, object]:
        raise AssertionError(f"unexpected create for {local_pairing_intent}")

    def read_identity(self, principal_id: str) -> dict[str, object]:
        self.principal_id = principal_id
        return {
            "principal_id": principal_id,
            "roles": ["creator"],
            "revoked": False,
            "session_ref": "opaque-upstream-session",
        }


def compatible_checker(*, require_cloud_platform: bool) -> Compatibility:
    if not require_cloud_platform:
        raise AssertionError("pairing must use the upstream cloud platform gate")
    return Compatibility(
        available=True,
        compatible=True,
        platform="macos",
        package_version="fixture",
        expected_digest="sha256:" + "a" * 64,
        actual_digest="sha256:" + "a" * 64,
        upstream_commit="a" * 40,
        reason=None,
    )


class StudioPolicyIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.trash = FakeTrashBackend(self.root / "fixture-trash")
        self.client = FakeUpstreamClient()
        self.server = serve(
            state_dir=self.root / "state",
            host="127.0.0.1",
            port=0,
            upstream_client=self.client,
            compatibility_checker=compatible_checker,
            chatcut_mcp=ChatCutMcp(executor=lambda _command, _timeout: 0),
            trash_backend_factory=lambda _platform, _registry: self.trash,
        )
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

    def bootstrap(self) -> tuple[str, dict[str, object]]:
        status, payload = self.request("/api/bootstrap")
        self.assertEqual(status, 200)
        return payload["csrfToken"], payload

    def create_project(self, csrf: str) -> dict[str, object]:
        workspace = self.root / "workspace"
        workspace.mkdir(exist_ok=True)
        status, payload = self.request(
            "/api/projects",
            method="POST",
            csrf=csrf,
            body={"title": "R4 fixture", "localWorkspace": str(workspace)},
        )
        self.assertEqual(status, 201)
        return payload["project"]

    def test_settings_are_secret_free_and_keep_local_features_before_pairing(self) -> None:
        csrf, _ = self.bootstrap()
        status, initial = self.request("/api/settings")
        self.assertEqual(status, 200)
        self.assertTrue(initial["settings"]["upstream"]["local_features_available"])
        self.assertFalse(initial["settings"]["upstream"]["upstream_features_available"])

        config = {
            "id": "creative-codex",
            "provider": "codex_openai",
            "model": "gpt-5.6",
            "endpoint": "https://api.openai.com/v1",
            "secret_ref": "keychain:creative-codex",
        }
        status, configured = self.request(
            "/api/settings/model-providers",
            method="POST",
            csrf=csrf,
            body={"config": config},
        )
        self.assertEqual(status, 200)
        serialized = json.dumps(configured, ensure_ascii=False)
        self.assertNotIn(config["secret_ref"], serialized)
        self.assertNotIn('"secret_ref":', serialized)

        status, probed = self.request(
            "/api/settings/model-providers/creative-codex/probe",
            method="POST",
            csrf=csrf,
            body={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            probed["settings"]["model_providers"][0]["capability"]["reason_code"],
            "network_probe_disabled",
        )

    def test_archive_pairing_and_chatcut_surface_are_user_triggered_and_safe(self) -> None:
        csrf, _ = self.bootstrap()
        status, lifecycle = self.request(
            "/api/settings/archive/lifecycle",
            method="POST",
            csrf=csrf,
            body={"lifecycle": "archived"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(lifecycle["settings"]["archive"]["lifecycle"], "archived")
        status, location = self.request(
            "/api/settings/archive/locations",
            method="POST",
            csrf=csrf,
            body={
                "locationId": "fixture-disk",
                "displayName": "Fixture archive",
                "locationRef": "fixture/disk-a",
                "mediaManifest": [{"relative_path": "camera/a.jpg", "sha256": "a" * 64}],
                "observedAt": "2026-09-02T00:00:00Z",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(location["archive"]["locations"][0]["readback_state"], "unknown")

        status, paired = self.request(
            "/api/settings/upstream/pair",
            method="POST",
            csrf=csrf,
            body={"localPairingIntent": "fixture-intent"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(paired["upstream"]["local_features_available"])
        self.assertTrue(paired["upstream"]["upstream_features_available"])
        self.assertEqual(paired["upstream"]["upstream_principal_id"], "upstream-user")
        self.assertNotIn("session_ref", json.dumps(paired))
        self.assertNotIn("opaque-upstream-session", json.dumps(paired))

        status, probe = self.request("/api/settings/chatcut/probe", method="POST", csrf=csrf, body={})
        self.assertEqual(status, 200)
        self.assertEqual(probe["chatcut"]["status"], "awaiting_confirmation")
        status, connected = self.request("/api/settings/chatcut/confirm", method="POST", csrf=csrf, body={})
        self.assertEqual(status, 200)
        self.assertEqual(connected["chatcut"]["status"], "connected")

    def test_recommend_confirm_and_restore_use_only_selected_fixture_media(self) -> None:
        csrf, _ = self.bootstrap()
        project = self.create_project(csrf)
        workspace = self.root / "workspace"
        source = workspace / "camera" / "one.jpg"
        source.parent.mkdir()
        source.write_bytes(b"fixture media")
        item = {
            "media_id": hashlib.sha1(b"camera/one.jpg").hexdigest()[:12],
            "relative_path": "camera/one.jpg",
            "sha256": sha256_file(source),
            "image_health": "healthy",
            "image_readable": True,
        }
        base = f"/api/projects/{project['id']}/media-delete"
        status, suggested = self.request(
            base + "/recommendations",
            method="POST",
            csrf=csrf,
            body={"manifest": {"items": [item]}},
        )
        self.assertEqual(status, 200)
        candidate = suggested["candidates"][0]
        status, rejected = self.request(
            base + "/confirm",
            method="POST",
            csrf=csrf,
            body={"candidates": [candidate], "selectedCandidateNumbers": [candidate["candidate_number"]]},
        )
        self.assertEqual(status, 400)
        self.assertEqual(rejected["error"]["code"], "second_confirmation_required")
        self.assertTrue(source.exists())

        status, confirmed = self.request(
            base + "/confirm",
            method="POST",
            csrf=csrf,
            body={
                "candidates": [candidate],
                "selectedCandidateNumbers": [candidate["candidate_number"]],
                "secondConfirmation": True,
                "operator": "fixture-user",
            },
        )
        self.assertEqual(status, 200)
        receipt = confirmed["receipts"][0]
        self.assertFalse(source.exists())
        rendered = json.dumps(confirmed, ensure_ascii=False)
        self.assertNotIn(str(self.root), rendered)
        self.assertNotIn("trash_location_id", rendered)

        status, restored = self.request(
            base + "/restore",
            method="POST",
            csrf=csrf,
            body={"receiptId": receipt["receipt_id"], "operator": "fixture-user"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(restored["receipt"]["status"], "restored")
        self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
