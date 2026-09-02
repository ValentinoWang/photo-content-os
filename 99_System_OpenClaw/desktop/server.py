#!/usr/bin/env python3
"""Loopback-only HTTP server for Photo Content OS Studio."""

from __future__ import annotations

import json
import importlib.util
import mimetypes
import os
import secrets
import sys
import tempfile
import urllib.parse
from collections.abc import Callable as CollectionCallable, Mapping
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
from desktop.archive_location_config import (  # type: ignore  # noqa: E402
    ArchiveLocationConfig,
    ArchiveLocationConfigError,
    ArchiveLocationConfigStore,
)
from desktop.chatcut_mcp import ChatCutMcp  # type: ignore  # noqa: E402
from desktop.edl_bridge import EDLBridgeError, bridge_state, read_edl_bridge  # type: ignore  # noqa: E402
from desktop.model_provider_config import (  # type: ignore  # noqa: E402
    ModelProviderConfig,
    ModelProviderConfigError,
    ModelProviderConfigStore,
)
from desktop.project_store import DOCUMENT_NAMES, ProjectStore, ProjectStoreError  # type: ignore  # noqa: E402
from desktop.upstream_session import UpstreamSessionConsumer, UpstreamSessionContractError  # type: ignore  # noqa: E402
from llm_common import LLMError, load_creator_context  # type: ignore  # noqa: E402
from media_delete_recommendations import (  # type: ignore  # noqa: E402
    DeleteRecommendationError,
    confirm_delete_selection,
    generate_delete_recommendations,
)
from media_trash_flow import MediaTrashFlow, MediaTrashFlowError, get_system_trash_backend  # type: ignore  # noqa: E402
from upstream_identity import (  # type: ignore  # noqa: E402
    PairingRequest,
    UpstreamIdentityContractError,
    pair_upstream_identity,
)
from asset_library_index import (  # type: ignore  # noqa: E402
    INDEX_NAME as ASSET_LIBRARY_INDEX_NAME,
    AssetIndexError,
    get_asset,
    load_index,
    query_assets,
)

STATIC_ROOT = SCRIPT_DIR / "static"
MAX_BODY_BYTES = 2 * 1024 * 1024
SETTINGS_DIRNAME = "settings"
ASSET_LIBRARY_DIRNAME = "asset-library"
TRASH_RECEIPT_SCHEMA_VERSION = "studio_trash_receipts_v1"
INBOX_MANIFEST_RELATIVE_PATH = Path("_ai_analysis") / "media_manifest.json"


def _inbox_batch_planner() -> object:
    """Load the numbered CLI script as a library without executing its CLI."""

    module_name = "content_os_inbox_batch_planner"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    source = SCRIPTS_DIR / "46_plan_inbox_batches.py"
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError("inbox batch planner is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


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


def _public_upstream_snapshot(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Keep the opaque upstream session reference exclusively server-side."""

    return {
        "session_state": snapshot.get("session_state"),
        "local_features_available": snapshot.get("local_features_available") is True,
        "upstream_features_available": snapshot.get("upstream_features_available") is True,
        "upstream_principal_id": snapshot.get("upstream_principal_id"),
        "roles": list(snapshot.get("roles") or []),
        "revoked": snapshot.get("revoked"),
        "pairing_status": snapshot.get("pairing_status"),
    }


def _unavailable_pairing() -> dict[str, object]:
    return {
        "upstream_principal_id": None,
        "roles": [],
        "revoked": None,
        "pairing_status": "unavailable",
        "session_ref": None,
    }


def _public_trash_receipt(receipt: Mapping[str, object]) -> dict[str, object]:
    """Expose auditable relative-path evidence, never a backend locator."""

    allowed = (
        "receipt_id",
        "status",
        "candidate_number",
        "media_id",
        "original_relative_path",
        "sha256",
        "content_sha256",
        "operator",
        "operation_time",
        "post_move_verification",
        "restore_result",
    )
    return {field: receipt[field] for field in allowed if field in receipt}


class StudioApplication:
    def __init__(
        self,
        store: ProjectStore,
        *,
        csrf_token: str | None = None,
        model_provider_store: ModelProviderConfigStore | None = None,
        archive_location_store: ArchiveLocationConfigStore | None = None,
        upstream_session: UpstreamSessionConsumer | None = None,
        upstream_client: object | None = None,
        compatibility_checker: CollectionCallable[..., object] | None = None,
        upstream_reader: CollectionCallable[[str], Mapping[str, object]] | None = None,
        chatcut_mcp: ChatCutMcp | None = None,
        trash_backend_factory: CollectionCallable[[str, Path], object] | None = None,
        asset_index_path: Path | None = None,
    ) -> None:
        self.store = store
        self.csrf_token = csrf_token or secrets.token_urlsafe(32)
        self.settings_dir = self.store.state_dir / SETTINGS_DIRNAME
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.model_provider_store = model_provider_store or ModelProviderConfigStore(self.settings_dir)
        self.archive_location_store = archive_location_store or ArchiveLocationConfigStore(self.settings_dir)
        self.upstream_session = upstream_session or UpstreamSessionConsumer()
        self.upstream_client = upstream_client
        self.compatibility_checker = compatibility_checker
        self.upstream_reader = upstream_reader
        self.chatcut_mcp = chatcut_mcp or ChatCutMcp()
        self.trash_backend_factory = trash_backend_factory or self._default_trash_backend
        self.asset_index_path = asset_index_path or self.store.state_dir / ASSET_LIBRARY_DIRNAME / ASSET_LIBRARY_INDEX_NAME

    @staticmethod
    def _default_trash_backend(platform_name: str, registry_path: Path) -> object:
        return get_system_trash_backend(platform_name, registry_path=registry_path)

    def _archive_config(self) -> ArchiveLocationConfig:
        try:
            return self.archive_location_store.load()
        except ArchiveLocationConfigError as exc:
            if exc.code != "config_not_found":
                raise
            return self.archive_location_store.initialize()

    def settings_projection(self) -> dict[str, object]:
        return {
            "model_providers": [config.to_public_dict() for config in self.model_provider_store.list_configs()],
            "archive": self._archive_config().to_dict(),
            "upstream": _public_upstream_snapshot(self.upstream_session.snapshot()),
            "chatcut": self.chatcut_mcp.state,
        }

    def load_asset_index(self) -> dict[str, Any]:
        try:
            return load_index(self.asset_index_path)
        except AssetIndexError as exc:
            # Index diagnostics may include the configured filesystem location.
            raise ProjectStoreError("asset_library_unavailable", "素材库索引不可用") from exc

    def inbox_batch_plan(self, project_id: str) -> dict[str, Any]:
        """Build a preview from a connected project's current manifest only."""

        workspace = self.store.local_workspace_path(project_id)
        manifest_path = (workspace / INBOX_MANIFEST_RELATIVE_PATH).resolve()
        try:
            manifest_path.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ProjectStoreError("inbox_manifest_invalid", "媒体清单位置无效") from exc
        if not manifest_path.is_file():
            raise ProjectStoreError("inbox_manifest_missing", "项目尚未生成可用于分批的媒体清单")
        try:
            planner = _inbox_batch_planner()
            manifest, digest = planner.read_manifest(manifest_path)
            return planner.plan_batches(manifest, manifest_sha256=digest)
        except Exception as exc:
            # The browser must receive a stable, path-free error even if a
            # malformed local manifest contains implementation detail.
            if exc.__class__.__name__ == "BatchPlanError":
                raise ProjectStoreError("inbox_manifest_invalid", "媒体清单无法用于生成分批计划") from exc
            raise

    @staticmethod
    def asset_library_statistics(index: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": index["schema_version"],
            "revision": index["revision"],
            "asset_count": index["asset_count"],
            "categories": index["categories"],
            "tags": index["tags"],
            "uses": index["uses"],
        }

    def _receipt_path(self, project_id: str) -> Path:
        # Project IDs are validated by ProjectStore before every caller reaches
        # this helper, and never form a browser-visible filesystem projection.
        self.store.get_project(project_id)
        return self.settings_dir / "trash-receipts" / f"{project_id}.json"

    def load_receipts(self, project_id: str) -> dict[str, dict[str, object]]:
        path = self._receipt_path(project_id)
        if not path.exists():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectStoreError("trash_receipts_unavailable", "回收站回执无法读取") from exc
        if (
            not isinstance(raw, dict)
            or raw.get("schema_version") != TRASH_RECEIPT_SCHEMA_VERSION
            or not isinstance(raw.get("receipts"), dict)
        ):
            raise ProjectStoreError("trash_receipts_invalid", "回收站回执格式无效")
        receipts = raw["receipts"]
        if not all(isinstance(receipt_id, str) and isinstance(receipt, dict) for receipt_id, receipt in receipts.items()):
            raise ProjectStoreError("trash_receipts_invalid", "回收站回执格式无效")
        return {receipt_id: dict(receipt) for receipt_id, receipt in receipts.items()}

    def save_receipts(self, project_id: str, receipts: Mapping[str, Mapping[str, object]]) -> None:
        path = self._receipt_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": TRASH_RECEIPT_SCHEMA_VERSION,
            "receipts": {receipt_id: dict(receipt) for receipt_id, receipt in receipts.items()},
        }
        temporary_path: str | None = None
        try:
            descriptor, temporary_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        except OSError as exc:
            raise ProjectStoreError("trash_receipts_unavailable", "回收站回执无法保存") from exc
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def trash_flow(self, project_id: str) -> MediaTrashFlow:
        workspace = self.store.local_workspace_path(project_id)
        registry_path = self.settings_dir / "system-trash" / f"{project_id}.json"
        backend = self.trash_backend_factory(sys.platform, registry_path)
        return MediaTrashFlow(workspace, backend, system_trash_registry_path=registry_path)

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
                    if parsed.path == "/api/settings":
                        self._json(HTTPStatus.OK, {"ok": True, "settings": app.settings_projection()})
                        return
                    if parsed.path == "/api/projects":
                        self._json(HTTPStatus.OK, {"ok": True, "projects": app.store.list_projects()})
                        return
                    if parsed.path == "/api/assets":
                        query = urllib.parse.parse_qs(parsed.query)
                        categories = query.get("category", [])
                        if len(categories) > 1:
                            raise ProjectStoreError("asset_query_invalid", "素材库筛选条件无效")
                        category = categories[0] if categories else None
                        tags = [*query.get("tags", []), *query.get("tag", [])]
                        try:
                            assets = query_assets(app.load_asset_index(), category=category, tags=tags)
                        except AssetIndexError as exc:
                            raise ProjectStoreError("asset_query_invalid", "素材库筛选条件无效") from exc
                        self._json(
                            HTTPStatus.OK,
                            {
                                "ok": True,
                                "assets": assets,
                                "query": {"category": category, "tags": tags},
                            },
                        )
                        return
                    if parsed.path == "/api/assets/statistics":
                        self._json(
                            HTTPStatus.OK,
                            {"ok": True, "statistics": app.asset_library_statistics(app.load_asset_index())},
                        )
                        return
                    if len(segments) == 3 and segments[:2] == ["api", "assets"]:
                        asset = get_asset(app.load_asset_index(), segments[2])
                        if asset is None:
                            self._json(HTTPStatus.NOT_FOUND, _error("asset_not_found", "素材不存在"))
                            return
                        self._json(HTTPStatus.OK, {"ok": True, "asset": asset})
                        return
                    if len(segments) == 3 and segments[:2] == ["api", "projects"]:
                        self._json(HTTPStatus.OK, {"ok": True, "project": app.store.get_project(segments[2])})
                        return
                    if (
                        len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["media-delete", "receipts"]
                    ):
                        receipts = app.load_receipts(segments[2])
                        self._json(
                            HTTPStatus.OK,
                            {
                                "ok": True,
                                "receipts": [
                                    _public_trash_receipt(receipt)
                                    for _, receipt in sorted(receipts.items())
                                ],
                            },
                        )
                        return
                    if len(segments) == 4 and segments[:2] == ["api", "projects"] and segments[3] == "edl-bridge":
                        try:
                            workspace = app.store.local_workspace_path(segments[2])
                        except ProjectStoreError as exc:
                            if exc.code not in {"workspace_not_connected", "workspace_not_found"}:
                                raise
                            payload = _error("edl_workspace_unavailable", "The project workspace is unavailable.")
                            payload["bridge"] = bridge_state("unavailable", validation_code="workspace_unavailable")
                            self._json(HTTPStatus.NOT_FOUND, payload)
                            return
                        try:
                            bridge = read_edl_bridge(workspace)
                        except EDLBridgeError as exc:
                            payload = _error(exc.code, exc.message)
                            payload["bridge"] = exc.state
                            self._json(exc.http_status, payload)
                            return
                        self._json(HTTPStatus.OK, {"ok": True, "bridge": bridge})
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
                    if method == "POST" and segments == ["api", "settings", "model-providers"]:
                        config = ModelProviderConfig.from_dict(body.get("config"))
                        app.model_provider_store.upsert(config)
                        self._json(HTTPStatus.OK, {"ok": True, "settings": app.settings_projection()})
                        return
                    if (
                        method == "POST"
                        and len(segments) == 5
                        and segments[:3] == ["api", "settings", "model-providers"]
                        and segments[4] == "probe"
                    ):
                        app.model_provider_store.probe(segments[3])
                        self._json(HTTPStatus.OK, {"ok": True, "settings": app.settings_projection()})
                        return
                    if method == "POST" and segments == ["api", "settings", "archive", "lifecycle"]:
                        current = app._archive_config()
                        updated = current.with_lifecycle(body.get("lifecycle"))
                        app.archive_location_store.save(updated)
                        self._json(HTTPStatus.OK, {"ok": True, "settings": app.settings_projection()})
                        return
                    if method == "POST" and segments == ["api", "settings", "archive", "locations"]:
                        app._archive_config()
                        updated = app.archive_location_store.add_location(
                            location_id=body.get("locationId"),
                            display_name=body.get("displayName"),
                            location_ref=body.get("locationRef"),
                            media_manifest=body.get("mediaManifest"),
                            observed_at=body.get("observedAt"),
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "archive": updated.to_dict(), "settings": app.settings_projection()})
                        return
                    if method == "POST" and segments == ["api", "settings", "upstream", "pair"]:
                        if app.upstream_client is None:
                            snapshot = app.upstream_session.consume(_unavailable_pairing())
                        else:
                            request = PairingRequest(
                                user_confirmed=True,
                                local_pairing_intent=str(body.get("localPairingIntent") or ""),
                            )
                            result = pair_upstream_identity(
                                request,
                                app.upstream_client,
                                compatibility_checker=app.compatibility_checker,
                            )
                            snapshot = app.upstream_session.consume(result)
                        self._json(HTTPStatus.OK, {"ok": True, "upstream": _public_upstream_snapshot(snapshot)})
                        return
                    if method == "POST" and segments == ["api", "settings", "upstream", "refresh"]:
                        snapshot = (
                            app.upstream_session.refresh(app.upstream_reader)
                            if app.upstream_reader is not None
                            else app.upstream_session.snapshot()
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "upstream": _public_upstream_snapshot(snapshot)})
                        return
                    if method == "POST" and segments == ["api", "settings", "upstream", "logout"]:
                        self._json(
                            HTTPStatus.OK,
                            {"ok": True, "upstream": _public_upstream_snapshot(app.upstream_session.logout())},
                        )
                        return
                    if method == "POST" and segments == ["api", "settings", "chatcut", "probe"]:
                        self._json(HTTPStatus.OK, {"ok": True, "chatcut": app.chatcut_mcp.probe()})
                        return
                    if method == "POST" and segments == ["api", "settings", "chatcut", "confirm"]:
                        self._json(HTTPStatus.OK, {"ok": True, "chatcut": app.chatcut_mcp.confirm_connection()})
                        return
                    if (
                        method == "POST"
                        and len(segments) == 4
                        and segments[:2] == ["api", "projects"]
                        and segments[3] == "inbox-plan"
                    ):
                        self._json(HTTPStatus.OK, {"ok": True, "plan": app.inbox_batch_plan(segments[2])})
                        return
                    if (
                        method == "POST"
                        and len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["media-delete", "recommendations"]
                    ):
                        candidates = generate_delete_recommendations(body.get("manifest"))
                        self._json(HTTPStatus.OK, {"ok": True, "candidates": candidates})
                        return
                    if (
                        method == "POST"
                        and len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["media-delete", "confirm"]
                    ):
                        confirmation = confirm_delete_selection(
                            body.get("candidates"),
                            body.get("selectedCandidateNumbers"),
                        )
                        result = app.trash_flow(segments[2]).trash_confirmed_candidates(
                            confirmation,
                            operator=str(body.get("operator") or "studio-user"),
                            second_confirmation=body.get("secondConfirmation") is True,
                        )
                        receipts = app.load_receipts(segments[2])
                        public_receipts: list[dict[str, object]] = []
                        for receipt in result["receipts"]:
                            stored = dict(receipt)
                            receipt_id = "receipt-" + secrets.token_urlsafe(18)
                            stored["receipt_id"] = receipt_id
                            receipts[receipt_id] = stored
                            public_receipts.append(_public_trash_receipt(stored))
                        app.save_receipts(segments[2], receipts)
                        self._json(
                            HTTPStatus.OK,
                            {
                                "ok": True,
                                "status": result["status"],
                                "receipts": public_receipts,
                                "pending": [_public_trash_receipt(item) for item in result["pending"]],
                            },
                        )
                        return
                    if (
                        method == "POST"
                        and len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["media-delete", "restore"]
                    ):
                        receipt_id = body.get("receiptId")
                        if not isinstance(receipt_id, str) or not receipt_id:
                            raise ProjectStoreError("receipt_id_invalid", "回收站回执编号无效")
                        receipts = app.load_receipts(segments[2])
                        if receipt_id not in receipts:
                            raise ProjectStoreError("receipt_not_found", "回收站回执不存在")
                        restored = app.trash_flow(segments[2]).restore_receipt(
                            receipts[receipt_id],
                            operator=str(body.get("operator") or "studio-user"),
                        )
                        restored["receipt_id"] = receipt_id
                        receipts[receipt_id] = dict(restored)
                        app.save_receipts(segments[2], receipts)
                        self._json(HTTPStatus.OK, {"ok": True, "receipt": _public_trash_receipt(restored)})
                        return
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
                except (
                    ArchiveLocationConfigError,
                    DeleteRecommendationError,
                    MediaTrashFlowError,
                    ModelProviderConfigError,
                    ProjectStoreError,
                    TypeError,
                    UpstreamIdentityContractError,
                    UpstreamSessionContractError,
                    ValueError,
                ) as exc:
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
    model_provider_store: ModelProviderConfigStore | None = None,
    archive_location_store: ArchiveLocationConfigStore | None = None,
    upstream_session: UpstreamSessionConsumer | None = None,
    upstream_client: object | None = None,
    compatibility_checker: CollectionCallable[..., object] | None = None,
    upstream_reader: CollectionCallable[[str], Mapping[str, object]] | None = None,
    chatcut_mcp: ChatCutMcp | None = None,
    trash_backend_factory: CollectionCallable[[str, Path], object] | None = None,
    asset_index_path: Path | None = None,
) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Photo Content OS Studio only supports loopback hosts")
    application = StudioApplication(
        ProjectStore(state_dir),
        model_provider_store=model_provider_store,
        archive_location_store=archive_location_store,
        upstream_session=upstream_session,
        upstream_client=upstream_client,
        compatibility_checker=compatibility_checker,
        upstream_reader=upstream_reader,
        chatcut_mcp=chatcut_mcp,
        trash_backend_factory=trash_backend_factory,
        asset_index_path=asset_index_path,
    )
    server = ThreadingHTTPServer((host, port), application.handler())
    actual_host, actual_port = server.server_address[:2]
    url_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{url_host}:{actual_port}/"
    if on_ready:
        on_ready(url)
    return server
