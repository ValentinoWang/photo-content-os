#!/usr/bin/env python3
"""Loopback-only HTTP server for Photo Content OS Studio."""

from __future__ import annotations

import json
import mimetypes
import secrets
import sys
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

SCRIPT_DIR = Path(__file__).resolve().parent
SYSTEM_ROOT = SCRIPT_DIR.parent
SCRIPTS_DIR = SYSTEM_ROOT / "scripts"
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from desktop.ai_patch import AIPatchError, generate_patch  # type: ignore  # noqa: E402
from desktop.project_store import DOCUMENT_NAMES, ProjectStore, ProjectStoreError  # type: ignore  # noqa: E402
from llm_common import LLMError, load_creator_context  # type: ignore  # noqa: E402

STATIC_ROOT = SCRIPT_DIR / "static"
MAX_BODY_BYTES = 2 * 1024 * 1024


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _public_contract_snapshot() -> dict[str, Any]:
    path = SYSTEM_ROOT / "schemas" / "openclaw_media_contract_snapshot.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "upstream_commit": data["upstream_commit"],
        "contract_id": data.get("contract_id") or data["upstream_contract_id"],
        "contract_version": data.get("contract_version") or data["upstream_contract_version"],
        "catalog_digest": data["catalog_digest"],
        "cloud_device_platforms": data["supported_device_platforms"],
        "pipelines": data["pipelines"],
        "privacy": data["privacy"],
    }


class StudioApplication:
    def __init__(self, store: ProjectStore, *, csrf_token: str | None = None) -> None:
        self.store = store
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)

    def handler(self) -> type[BaseHTTPRequestHandler]:
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "PhotoContentOSStudio/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:
                sys.stderr.write("studio: " + fmt % args + "\n")

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(body)

            def _json(self, status: int, value: Any) -> None:
                self._send(status, _json_bytes(value), "application/json; charset=utf-8")

            def _body(self) -> dict[str, Any]:
                raw_length = self.headers.get("Content-Length", "0")
                try:
                    length = int(raw_length)
                except ValueError as exc:
                    raise ProjectStoreError("body_invalid", "请求长度无效") from exc
                if length < 0 or length > MAX_BODY_BYTES:
                    raise ProjectStoreError("body_too_large", "请求内容过大")
                raw = self.rfile.read(length)
                if not raw:
                    return {}
                try:
                    value = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ProjectStoreError("body_invalid", "请求必须是 UTF-8 JSON") from exc
                if not isinstance(value, dict):
                    raise ProjectStoreError("body_invalid", "请求根节点必须是对象")
                return value

            def _assert_local(self) -> None:
                raw_host = (self.headers.get("Host") or "").lower()
                host = "[::1]" if raw_host.startswith("[::1]") else raw_host.split(":", 1)[0]
                if host not in {"127.0.0.1", "localhost", "[::1]"}:
                    raise ProjectStoreError("host_forbidden", "桌面工作台只接受本机访问")

            def _assert_write(self) -> None:
                self._assert_local()
                if self.headers.get("X-Content-OS-CSRF") != app.csrf_token:
                    raise ProjectStoreError("csrf_invalid", "安全令牌已失效，请刷新页面")
                origin = self.headers.get("Origin")
                if origin:
                    parsed = urllib.parse.urlparse(origin)
                    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                        raise ProjectStoreError("origin_forbidden", "只允许本机页面提交修改")

            @staticmethod
            def _segments(path: str) -> list[str]:
                return [urllib.parse.unquote(part) for part in path.split("/") if part]

            def do_GET(self) -> None:  # noqa: N802
                try:
                    self._assert_local()
                    parsed = urllib.parse.urlparse(self.path)
                    segments = self._segments(parsed.path)
                    if parsed.path == "/api/bootstrap":
                        self._json(
                            HTTPStatus.OK,
                            {
                                "ok": True,
                                "csrfToken": app.csrf_token,
                                "schemaVersion": "content_os_studio_bootstrap_v1",
                                "projects": app.store.list_projects(),
                                "contract": _public_contract_snapshot(),
                            },
                        )
                        return
                    if parsed.path == "/api/health":
                        self._json(HTTPStatus.OK, {"ok": True, "status": "ready", "localOnly": True})
                        return
                    if parsed.path == "/api/projects":
                        self._json(HTTPStatus.OK, {"ok": True, "projects": app.store.list_projects()})
                        return
                    if len(segments) == 3 and segments[:2] == ["api", "projects"]:
                        self._json(HTTPStatus.OK, {"ok": True, "project": app.store.get_project(segments[2])})
                        return
                    if len(segments) == 6 and segments[:2] == ["api", "projects"] and segments[3] == "documents" and segments[5] == "diff":
                        query = urllib.parse.parse_qs(parsed.query)
                        from_version = int(query.get("from", ["1"])[0])
                        to_version = int(query.get("to", ["1"])[0])
                        diff = app.store.document_diff(segments[2], segments[4], from_version, to_version)
                        self._json(HTTPStatus.OK, {"ok": True, "diff": diff})
                        return
                    if parsed.path.startswith("/api/"):
                        self._json(HTTPStatus.NOT_FOUND, _error("route_not_found", "接口不存在"))
                        return
                    self._static(parsed.path)
                except (ProjectStoreError, ValueError) as exc:
                    self._handle_error(exc)

            def do_POST(self) -> None:  # noqa: N802
                self._write_request("POST")

            def do_PATCH(self) -> None:  # noqa: N802
                self._write_request("PATCH")

            def _write_request(self, method: str) -> None:
                try:
                    self._assert_write()
                    parsed = urllib.parse.urlparse(self.path)
                    segments = self._segments(parsed.path)
                    body = self._body()
                    expected = body.get("expectedRevision")
                    expected_revision = int(expected) if expected is not None else None
                    if method == "POST" and parsed.path == "/api/projects":
                        project = app.store.create_project(
                            title=body.get("title", ""),
                            platform=body.get("platform", "未指定"),
                            local_workspace=body.get("localWorkspace"),
                            account=body.get("account", ""),
                        )
                        self._json(HTTPStatus.CREATED, {"ok": True, "project": project})
                        return
                    if method == "PATCH" and len(segments) == 3 and segments[:2] == ["api", "projects"]:
                        project = app.store.update_project(
                            segments[2],
                            body.get("changes") if isinstance(body.get("changes"), dict) else {},
                            expected_revision=expected_revision,
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "projects"] and segments[3] == "workspace":
                        project = app.store.connect_workspace(
                            segments[2],
                            str(body.get("localWorkspace") or ""),
                            expected_revision=expected_revision,
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    if method == "POST" and len(segments) == 6 and segments[:2] == ["api", "projects"] and segments[3] == "documents":
                        project_id, document, action = segments[2], segments[4], segments[5]
                        if document not in DOCUMENT_NAMES:
                            raise ProjectStoreError("document_invalid", "文档类型无效")
                        if action == "patch":
                            replacements = body.get("replacements")
                            selected = body.get("selectedBlockIds")
                            project = app.store.patch_document(
                                project_id,
                                document,
                                replacements if isinstance(replacements, dict) else {},
                                selected_block_ids=selected if isinstance(selected, list) else [],
                                expected_revision=expected_revision,
                            )
                        elif action in {"lock", "unlock"}:
                            project = app.store.set_block_lock(
                                project_id,
                                document,
                                str(body.get("blockId") or ""),
                                action == "lock",
                                expected_revision=expected_revision,
                            )
                        elif action == "rollback":
                            project = app.store.rollback_document(
                                project_id,
                                document,
                                int(body.get("targetVersion")),
                                expected_revision=expected_revision,
                            )
                        elif action == "ai-patch":
                            current = app.store.get_project(project_id)
                            blocks = current["documents"][document]["blocks"]
                            selected_ids = body.get("selectedBlockIds") if isinstance(body.get("selectedBlockIds"), list) else []
                            selected = [block for block in blocks if block["id"] in selected_ids]
                            if len(selected) != len(selected_ids):
                                raise ProjectStoreError("selection_invalid", "选中区块不存在")
                            persona = ""
                            try:
                                workspace = app.store.local_workspace_path(project_id)
                            except ProjectStoreError as exc:
                                if exc.code not in {"workspace_not_connected", "workspace_not_found"}:
                                    raise
                            else:
                                brief_text = "\n".join(
                                    str(block.get("body") or "")
                                    for block in current["documents"]["brief"]["blocks"]
                                )
                                persona = str(load_creator_context(workspace, brief_text=brief_text).get("persona") or "")
                            try:
                                from llm_common import generate_text

                                replacements = generate_patch(
                                    document_name=document,
                                    instruction=str(body.get("instruction") or ""),
                                    selected_blocks=selected,
                                    surrounding_blocks=blocks,
                                    project_context={
                                        "title": str(current.get("title") or ""),
                                        "platform": str(current.get("platform") or ""),
                                        "account": str(current.get("account") or ""),
                                        "persona": persona,
                                        "review_conclusion": str((current.get("publishing") or {}).get("review_conclusion") or ""),
                                        "next_constraint": str((current.get("publishing") or {}).get("next_constraint") or ""),
                                    },
                                    account_review_context=app.store.account_review_context(project_id),
                                    generate_text=generate_text,
                                    model=body.get("model"),
                                    reasoning=body.get("reasoning"),
                                )
                            except (LLMError, ImportError) as exc:
                                sys.stderr.write("studio: ai patch generation failed\n")
                                raise ProjectStoreError("ai_generate_failed", "本机 AI 生成失败，请检查配置后重试。") from exc
                            except AIPatchError as exc:
                                raise ProjectStoreError("ai_patch_failed", str(exc)) from exc
                            project = app.store.patch_document(
                                project_id,
                                document,
                                replacements,
                                selected_block_ids=selected_ids,
                                expected_revision=expected_revision,
                                actor="ai",
                                reason="ai_selected_blocks",
                            )
                        else:
                            raise ProjectStoreError("route_not_found", "操作不存在")
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "projects"] and segments[3] == "publishing":
                        project = app.store.record_publishing(
                            segments[2],
                            body.get("publishing") if isinstance(body.get("publishing"), dict) else {},
                            expected_revision=expected_revision,
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    if method == "POST" and len(segments) == 4 and segments[:2] == ["api", "projects"] and segments[3] == "references":
                        project = app.store.add_reference(
                            segments[2],
                            title=body.get("title", ""),
                            url=body.get("url", ""),
                            platform=body.get("platform", "未指定"),
                            note=body.get("note", ""),
                            expected_revision=expected_revision,
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    self._json(HTTPStatus.NOT_FOUND, _error("route_not_found", "接口不存在"))
                except (ProjectStoreError, ValueError, TypeError) as exc:
                    self._handle_error(exc)

            def _handle_error(self, exc: Exception) -> None:
                code = getattr(exc, "code", "request_invalid")
                message = getattr(exc, "message", str(exc) or "请求失败")
                status = HTTPStatus.CONFLICT if code == "revision_conflict" else HTTPStatus.FORBIDDEN if code in {"csrf_invalid", "origin_forbidden", "host_forbidden"} else HTTPStatus.BAD_REQUEST
                self._json(status, _error(code, message))

            def _static(self, request_path: str) -> None:
                relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
                candidate = (STATIC_ROOT / relative).resolve()
                try:
                    candidate.relative_to(STATIC_ROOT.resolve())
                except ValueError:
                    self._send(HTTPStatus.NOT_FOUND, b"not found\n", "text/plain; charset=utf-8")
                    return
                if not candidate.is_file():
                    candidate = STATIC_ROOT / "index.html"
                body = candidate.read_bytes()
                content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
                if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                    content_type += "; charset=utf-8"
                self._send(HTTPStatus.OK, body, content_type)

        return Handler


def serve(
    *,
    state_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    on_ready: Callable[[str], None] | None = None,
) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Photo Content OS Studio only supports loopback hosts")
    application = StudioApplication(ProjectStore(state_dir))
    server = ThreadingHTTPServer((host, port), application.handler())
    actual_host, actual_port = server.server_address[:2]
    url_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{url_host}:{actual_port}/"
    if on_ready:
        on_ready(url)
    return server
