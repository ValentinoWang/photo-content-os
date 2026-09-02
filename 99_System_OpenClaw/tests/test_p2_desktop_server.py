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
from llm_common import LLMError  # noqa: E402


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

    def test_inbox_plan_reads_only_a_connected_projects_manifest(self):
        status, bootstrap = self.request("/api/bootstrap")
        self.assertEqual(status, 200)
        workspace = Path(self.temp.name) / "project-media"
        manifest_path = workspace / "_ai_analysis" / "media_manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(json.dumps({
            "manifest_version": 1,
            "items": [
                {"media_id": "clip-a", "captured_at": "2026-09-02T09:00:00+00:00", "gps_latitude": 22.5, "gps_longitude": 113.9},
                {"media_id": "clip-b", "captured_at": "2026-09-02T09:04:00+00:00", "gps_latitude": 22.5, "gps_longitude": 113.9},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        _, created = self.request(
            "/api/projects", method="POST", csrf=bootstrap["csrfToken"],
            body={"title": "分批计划", "localWorkspace": str(workspace)},
        )
        project_id = created["project"]["id"]
        status, payload = self.request(
            f"/api/projects/{project_id}/inbox-plan", method="POST", csrf=bootstrap["csrfToken"], body={},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["plan"]["confirmation_status"], "pending")
        self.assertEqual(payload["plan"]["migration_status"], "not_requested")
        self.assertEqual(payload["plan"]["batches"][0]["media_ids"], ["clip-a", "clip-b"])
        self.assertNotIn(str(workspace.resolve()), json.dumps(payload, ensure_ascii=False))

    def test_static_frontend_is_served(self):
        with urllib.request.urlopen(self.base + "/") as response:
            html = response.read().decode("utf-8")
        with urllib.request.urlopen(self.base + "/app.js") as response:
            app = response.read().decode("utf-8")
        self.assertIn("Photo Content OS Studio", html)
        self.assertIn('data-screen="project"', html)
        self.assertIn("发布与复盘", app)

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

    def test_ai_patch_uses_explicit_project_platform_account_and_persona(self):
        _, bootstrap = self.request("/api/bootstrap")
        workspace = Path(self.temp.name) / "project"
        workspace.mkdir()
        (workspace / "readme.md").write_text("账号人设：只讲真实拍摄过程\n", encoding="utf-8")
        _, created = self.request(
            "/api/projects",
            method="POST",
            csrf=bootstrap["csrfToken"],
            body={
                "title": "真实项目",
                "platform": "B站",
                "account": "摄影账号",
                "localWorkspace": str(workspace),
            },
        )
        project = created["project"]
        response_text = json.dumps({"replacements": {"brief-goal": "只改这一块"}}, ensure_ascii=False)
        with patch("llm_common.generate_text", return_value=response_text) as generate_text:
            status, _ = self.request(
                f"/api/projects/{project['id']}/documents/brief/ai-patch",
                method="POST",
                csrf=bootstrap["csrfToken"],
                body={
                    "instruction": "只修改目标",
                    "selectedBlockIds": ["brief-goal"],
                    "expectedRevision": project["revision"],
                },
            )
        self.assertEqual(status, 200)
        prompt = json.loads(generate_text.call_args.kwargs["user_prompt"])
        context = prompt["read_only_context"]["current_project"]
        self.assertEqual(context["platform"], "B站")
        self.assertEqual(context["account"], "摄影账号")
        self.assertEqual(context["persona"], "只讲真实拍摄过程")
        self.assertNotIn(str(workspace), json.dumps(prompt, ensure_ascii=False))
        self.assertIn("平台、账号和人设", generate_text.call_args.kwargs["system_prompt"])

    def test_ai_patch_llm_error_is_stable_chinese_json_without_raw_detail(self):
        _, bootstrap = self.request("/api/bootstrap")
        _, created = self.request(
            "/api/projects",
            method="POST",
            csrf=bootstrap["csrfToken"],
            body={"title": "生成失败", "platform": "小红书"},
        )
        project = created["project"]
        raw_error = "codex backend model-x failed at /private/secret/project"
        with patch("llm_common.generate_text", side_effect=LLMError(raw_error)):
            status, payload = self.request(
                f"/api/projects/{project['id']}/documents/brief/ai-patch",
                method="POST",
                csrf=bootstrap["csrfToken"],
                body={
                    "instruction": "只修改目标",
                    "selectedBlockIds": ["brief-goal"],
                    "expectedRevision": project["revision"],
                },
            )
        self.assertEqual(status, 400)
        self.assertEqual(
            payload,
            {"ok": False, "error": {"code": "ai_generate_failed", "message": "本机 AI 生成失败，请检查配置后重试。"}},
        )
        serialised = json.dumps(payload, ensure_ascii=False).lower()
        for leaked in ("codex", "backend", "model-x", "/private/secret", raw_error.lower()):
            self.assertNotIn(leaked, serialised)

    def test_publishing_write_is_csrf_protected_and_versioned(self):
        _, bootstrap = self.request("/api/bootstrap")
        _, created = self.request(
            "/api/projects", method="POST", csrf=bootstrap["csrfToken"],
            body={"title": "发布记录", "account": "账号 A"},
        )
        project = created["project"]
        body = {
            "expectedRevision": project["revision"],
            "publishing": {
                "publishedAt": "2026-08-28T09:30:00Z",
                "links": ["https://example.com/post/1"],
                "metrics": {"views": 100, "likes": 8},
                "reviewConclusion": "结论前置更有效。",
                "nextConstraint": "开头不要先铺垫。",
            },
        }
        status, saved = self.request(f"/api/projects/{project['id']}/publishing", method="POST", body=body)
        self.assertEqual(status, 403)
        self.assertEqual(saved["error"]["code"], "csrf_invalid")
        status, saved = self.request(
            f"/api/projects/{project['id']}/publishing", method="POST", csrf=bootstrap["csrfToken"], body=body,
        )
        self.assertEqual(status, 200)
        self.assertEqual(saved["project"]["publishing"]["metrics"], {"views": 100, "likes": 8})
        status, stale = self.request(
            f"/api/projects/{project['id']}/publishing", method="POST", csrf=bootstrap["csrfToken"], body=body,
        )
        self.assertEqual(status, 409)
        self.assertEqual(stale["error"]["code"], "revision_conflict")

    def test_ai_patch_reads_only_same_account_review_history(self):
        _, bootstrap = self.request("/api/bootstrap")
        csrf = bootstrap["csrfToken"]

        def create(title, account):
            _, payload = self.request("/api/projects", method="POST", csrf=csrf, body={"title": title, "account": account, "platform": "小红书"})
            return payload["project"]

        same_account = create("同账号已发布", "账号 A")
        other_account = create("其他账号已发布", "账号 B")
        target = create("当前创作", "账号 A")
        for project, conclusion in ((same_account, "同账号结论"), (other_account, "其他账号结论")):
            status, _ = self.request(
                f"/api/projects/{project['id']}/publishing", method="POST", csrf=csrf,
                body={"expectedRevision": project["revision"], "publishing": {"reviewConclusion": conclusion, "nextConstraint": "下一次约束"}},
            )
            self.assertEqual(status, 200)

        response_text = json.dumps({"replacements": {"brief-goal": "只改这一块"}}, ensure_ascii=False)
        with patch("llm_common.generate_text", return_value=response_text) as generate_text:
            status, _ = self.request(
                f"/api/projects/{target['id']}/documents/brief/ai-patch", method="POST", csrf=csrf,
                body={"instruction": "只修改目标", "selectedBlockIds": ["brief-goal"], "expectedRevision": target["revision"]},
            )
        self.assertEqual(status, 200)
        prompt = json.loads(generate_text.call_args.kwargs["user_prompt"])
        context = prompt["read_only_context"]
        self.assertEqual(context["current_project"]["title"], "当前创作")
        self.assertEqual(context["current_project"]["account"], "账号 A")
        self.assertIn("同账号结论", json.dumps(context["same_account_review_conclusions"], ensure_ascii=False))
        self.assertNotIn("其他账号结论", json.dumps(prompt, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
