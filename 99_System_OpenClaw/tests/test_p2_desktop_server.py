from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SYSTEM))

from desktop.server import serve  # noqa: E402


class DesktopServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = serve(state_dir=Path(self.temp.name) / "state", host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, *, method="GET", body=None, csrf=None):
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

    def test_csrf_and_project_projection(self):
        status, bootstrap = self.request("/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertTrue(bootstrap["contract"]["pipelines"])
        status, error = self.request("/api/projects", method="POST", body={"title": "项目"})
        self.assertEqual(status, 403)
        self.assertEqual(error["error"]["code"], "csrf_invalid")

        workspace = Path(self.temp.name) / "private" / "media"
        workspace.mkdir(parents=True)
        status, payload = self.request(
            "/api/projects", method="POST", csrf=bootstrap["csrfToken"],
            body={"title": "项目", "platform": "抖音", "localWorkspace": str(workspace)},
        )
        self.assertEqual(status, 201)
        serialised = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(str(workspace.resolve()), serialised)
        self.assertTrue(payload["project"]["local_workspace"]["connected"])

    def test_static_frontend_is_served(self):
        with urllib.request.urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
        self.assertIn("Photo Content OS Studio", html)
        self.assertIn("发布与复盘", html)

    def test_ai_patch_changes_only_selected_unlocked_block(self):
        _, bootstrap = self.request("/api/bootstrap")
        _, created = self.request(
            "/api/projects", method="POST", csrf=bootstrap["csrfToken"],
            body={"title": "AI 区块测试", "platform": "小红书"},
        )
        project = created["project"]
        response_text = json.dumps({"replacements": {"brief-goal": "只改这一块"}}, ensure_ascii=False)
        with patch("llm_common.generate_text", return_value=response_text):
            status, payload = self.request(
                f"/api/projects/{project['id']}/documents/brief/ai-patch",
                method="POST", csrf=bootstrap["csrfToken"],
                body={
                    "instruction": "只修改目标",
                    "selectedBlockIds": ["brief-goal"],
                    "expectedRevision": project["revision"],
                },
            )
        self.assertEqual(status, 200)
        blocks = {block["id"]: block["body"] for block in payload["project"]["documents"]["brief"]["blocks"]}
        self.assertEqual(blocks["brief-goal"], "只改这一块")
        self.assertEqual(blocks["brief-audience"], "")


if __name__ == "__main__":
    unittest.main()
