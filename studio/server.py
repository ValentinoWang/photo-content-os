#!/usr/bin/env python3
"""Loopback-only HTTP server for Photo Content OS Studio."""

from __future__ import annotations

import hashlib
import json
import importlib.util
import mimetypes
import os
import math
import re
import threading
from datetime import datetime, timezone
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

from studio.media_review import MediaReview
from studio.review_jobs import ReviewJobs
from music_library.errors import MusicError

from studio.ai_patch import AIPatchError, generate_patch  # type: ignore  # noqa: E402
from studio.analysis_budget import AnalysisBudgetError, AnalysisBudgetStore  # type: ignore  # noqa: E402
from studio.api_contract import is_registered_route, route_inventory  # type: ignore  # noqa: E402
from studio.archive_location_config import (  # type: ignore  # noqa: E402
    ArchiveLocationConfig,
    ArchiveLocationConfigError,
    ArchiveLocationConfigStore,
)
from studio.chatcut_mcp import ChatCutMcp  # type: ignore  # noqa: E402
from studio.edl_bridge import EDLBridgeError, bridge_state, read_edl_bridge  # type: ignore  # noqa: E402
from studio.model_provider_config import (  # type: ignore  # noqa: E402
    ModelProviderConfig,
    ModelProviderConfigError,
    ModelProviderConfigStore,
)
from studio.onboarding_state import (  # type: ignore  # noqa: E402
    OnboardingStateError,
    VersionedOnboardingStateStore,
)
from studio.project_store import DOCUMENT_NAMES, ProjectStore, ProjectStoreError  # type: ignore  # noqa: E402
from studio.upstream_session import UpstreamSessionConsumer, UpstreamSessionContractError  # type: ignore  # noqa: E402
from llm_common import LLMError, load_creator_context  # type: ignore  # noqa: E402
from direct_video.generate import DirectVideoError  # noqa: E402
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
INBOX_MANIFEST_RELATIVE_PATH = Path("ai-analysis") / "media-manifest.json"


def _inbox_batch_planner() -> object:
    """Load the numbered CLI script as a library without executing its CLI."""

    module_name = "content_os_inbox_batch_planner"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    source = SCRIPTS_DIR / "plan_inbox_batches.py"
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
    path = SYSTEM_ROOT / "schemas" / "openclaw-media-contract-snapshot.json"
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
        upstream_task_reader: CollectionCallable[[], list[Mapping[str, object]]] | None = None,
    ) -> None:
        self.store = store
        self.media_review = MediaReview(store)
        self.review_jobs = ReviewJobs(self.media_review)
        self.doctor_checks = []
        self.doctor_checked_at = None
        self.doctor_thread = None
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
        self.analysis_budget_store = AnalysisBudgetStore(self.settings_dir)
        self.onboarding_store = VersionedOnboardingStateStore(self.settings_dir)
        self.upstream_task_reader = upstream_task_reader
        self.video_choice_lock = threading.Lock()
        from studio.video_workflow import VideoWorkflow
        self.video_workflow = VideoWorkflow(self)
        from studio.direct_video import DirectVideo
        self.direct_video = DirectVideo(self.store)

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

    def video_editor_choice(self, project_id: str, value: dict | None = None) -> dict:
        """Local next-handoff preference; never rewrite a run or project stage."""
        self.store.get_project(project_id)
        name = hashlib.sha256(project_id.encode()).hexdigest() + ".json"
        path = self.settings_dir / "video-editors" / name
        with self.video_choice_lock:
            current = json.loads(path.read_text()) if path.is_file() else {"editor": "otio_kdenlive", "method": "external", "revision": 1}
            # PS persisted this exact software under the old local ID. Reading
            # it preserves the user's choice and CAS; it does not rewrite a run.
            if current.get('editor')=='kdenlive': current={**current,'editor':'otio_kdenlive'}
            current.setdefault('method','external')
            if value is not None:
                from edit_backends.registry import BACKENDS
                if value.get("editor") not in {*BACKENDS, "chatcut"} or value.get("method", current.get("method", "external")) not in {"external", "guide", "self"}:
                    raise ProjectStoreError("editor_invalid", "剪辑软件选择无效")
                if type(value.get("revision")) is not int or value["revision"] != current["revision"]:
                    raise ProjectStoreError("revision_conflict", "剪辑软件选择已变化")
                current = {"editor": value["editor"], "method": value.get("method", current.get("method", "external")), "revision": current["revision"] + 1}
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
                    json.dump(current, handle)
                    temporary = Path(handle.name)
                os.replace(temporary, path)
            return current

    @staticmethod
    def _video_json(root: Path, ref: str) -> dict:
        path = (root / ref).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > MAX_BODY_BYTES:
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def video_handoff_projection(self, project_id: str) -> dict | None:
        data = self._video_handoff_projection(project_id)
        return self.video_workflow.projection(project_id, data) if data is not None else None

    def _video_handoff_projection(self, project_id: str) -> dict | None:
        """Read PF's explicitly bound inputs and results, with no local locators."""
        from runtime_paths import local_media_root
        from doctor import probe_app
        from studio.video_workflow import candidate_failed
        project = self.store.get_project(project_id)
        try:
            root = self.store.local_workspace_path(project_id).resolve()
        except ProjectStoreError:
            return None
        if not root.is_relative_to(local_media_root()):
            return None
        binding_ref = os.environ.get("PHOTO_STUDIO_VIDEO_BINDING")
        binding = {}
        if binding_ref:
            binding_path = Path(binding_ref).expanduser().resolve()
            binding = self._video_json(binding_path.parent, binding_path.name)
            if (binding.get("identity", {}).get("project_id") != project_id
                    or Path(binding.get("project_root", "")).resolve() != root):
                return None
            canonical_path = Path(binding.get("creative_store", "")).expanduser().resolve()
            canonical = self._video_json(canonical_path.parent, canonical_path.name)
            active = [p for p in canonical.get("projects", []) if p.get("id") == project_id]
            if len(active) != 1 or active[0].get("revision") != binding["identity"].get("project_revision"):
                return None
            revision = active[0]["revision"]
        else:
            revision = project["revision"]
        workspace = Path(os.environ.get("PHOTO_STUDIO_VIDEO_WORKSPACE", str(root))).expanduser().resolve()
        if not workspace.is_relative_to(local_media_root()):
            return None
        job = binding.get("identity", {}).get("job_id")
        if job:
            descriptor = self._video_json(workspace, "video-inputs/" + job + "/video.json")
            if not descriptor:
                descriptor = self._video_json(workspace, "video.json")
        else:
            descriptor = self._video_json(workspace, "video.json")
        identity = descriptor.get("identity", {})
        if not isinstance(identity.get("jobId"), str) or not identity["jobId"] or "/" in identity["jobId"] or "\\" in identity["jobId"]:
            return None
        if (descriptor.get("scope") != "video_handoff_v1" or identity.get("photoProjectId") != project_id
                or identity.get("photoProjectRevision") != revision or (job and identity.get("jobId") != job)):
            return None
        run = workspace / "runs" / hashlib.sha256(identity["jobId"].encode()).hexdigest()[:32]
        handoff = self._video_json(run, "handoff_manifest.json")
        payload = self._video_json(root, binding.get("candidate_ref", "candidate.json")) or handoff
        candidate = payload.get("candidate") or {}
        if candidate.get("identity") != identity:
            candidate = {}
            payload = {}
        progress = payload.get("progress") or {}
        suggestions = self._video_json(run, "native-suggest.json")
        if not suggestions:
            suggestions = self._video_json(root, "ai-analysis/edit_suggestions.json")
        native = self._video_json(run, "native-kdenlive.json")
        package = {}
        package_root = root
        for step in binding.get("steps", []):
            if step.get("action") == "chatcut":
                package_arg = step.get("kwargs", {}).get("package", {})
                ref = package_arg.get("local_ref") if isinstance(package_arg, dict) else None
                if ref:
                    package_root = (root / ref).resolve()
                    if package_root.is_relative_to(root):
                        package = self._video_json(package_root, "handoff.json")
                break
        if package.get("project_id") != project_id or package.get("project_revision") != revision:
            package = {}
        result = self._video_json(package_root, "handoff-result.json") if package else {}
        results = self._video_json(package_root, "mcp-results.json") if package and result.get("connection_verified") is True else {}
        # Only named structured editor facts are used. Textual tool output is not a receipt.
        imported = results.get("import", {}).get("structuredContent", {})
        precut = results.get("precut", {}).get("structuredContent", {})
        project_ref = imported.get("projectRef") if result.get("status") == "candidate" else None
        if not isinstance(project_ref, str) or not project_ref.strip():
            project_ref = None
        deep_link = imported.get("projectUrl") if project_ref else None
        if not isinstance(deep_link, str) or not deep_link.startswith("chatcut://project/") or any(c in deep_link for c in "\r\n\x00"):
            deep_link = None
        installed = probe_app(Path("/Applications/ChatCut.app"))
        kdenlive = probe_app(Path("/Applications/kdenlive.app"))
        report_ref = os.environ.get("OPENCLAW_MEDIA_VIDEO_TOOLS_REPORT")
        report = {}
        if report_ref:
            report_path = Path(report_ref).expanduser().resolve()
            report = self._video_json(report_path.parent, report_path.name)
        tool = report.get("editor") or {}
        now = datetime.now(timezone.utc)
        try:
            checked = datetime.fromisoformat(tool["checkedAt"].replace("Z", "+00:00"))
            expires = datetime.fromisoformat(tool["expiresAt"].replace("Z", "+00:00"))
            fresh = checked <= now < expires
        except (KeyError, TypeError, ValueError):
            fresh = False
        if fresh and tool.get("toolId") == "chatcut":
            installed = {"installed": tool.get("installed") is True, "version": tool.get("version")}
        else:
            tool = {}
        connected = self.chatcut_mcp.state.get("available") is True
        handshake = connected or (tool.get("status") == "online" and tool.get("evidenceKind") == "mcp_handshake")
        # Historical package success is not a current connection or login probe.
        login = True if handshake or tool.get("reasonCode") == "logged_in" else False if tool.get("reasonCode") == "not_logged_in" else None
        editor = candidate.get("editor") or {"displayName": "Kdenlive" if native and native.get("status") == "candidate" else None}
        duration = candidate.get("sourceDurationSeconds") or suggestions.get("duration")
        def number(value):
            return value if type(value) in {int, float} and math.isfinite(value) and value >= 0 else None
        cuts = []
        for item in suggestions.get("suggestions", []):
            if item.get("type") not in {"silence", "repetition", "animation", "review"}:
                continue
            start, end = number(item.get("start")), number(item.get("end"))
            if start is None or end is None or end <= start or (number(duration) is not None and end > duration):
                continue
            cuts.append({"type": item["type"], "start": start, "end": end,
                         "id": len(cuts), "basis": item.get("basis"), "text": item.get("evidence_text", ""), "animationId": item.get("animation_id"),
                         "automatic": item.get("auto_cut_allowed") is True and suggestions.get("auto_cut_allowed") is not False
                         and (item["type"] != "repetition" or suggestions.get("precision") == "word")})
        existing_animations={c['animationId'] for c in cuts if c['type']=='animation'}
        for animation in descriptor.get('animations',[]):
            start=number(animation.get('suggestedStartSeconds'));length=number(animation.get('durationSeconds'))
            aid=animation.get('animationId')
            if aid in existing_animations or animation.get('timeBasis')!='source' or start is None or not length or number(duration) is None or start+length>duration: continue
            cuts.append({'id':len(cuts),'type':'animation','start':start,'end':start+length,'text':animation.get('requirement',''),'animationId':aid,'automatic':False,'basis':'confirmed_animation'})
        peaks = payload.get("progress", {}).get("waveformPeaks", [])
        if progress.get("waveformSource") != "source" or not isinstance(peaks, list) or len(peaks) > 400 or any(number(p) is None or p > 1 for p in peaks):
            peaks = []
        assets = []
        if package:
            assets = [{"role": entry["role"], "name": Path(entry["path"]).name} for entry in package.get("files", [])
                      if entry.get("role") not in {"suggestions", "executable_suggestions"}]
        if not any(a["role"] == "original" for a in assets):
            for ref in binding.get("source_refs", []):
                source_path = (root / ref).resolve()
                if source_path.is_relative_to(root) and source_path.is_file() and source_path.suffix.lower() in {".mp4", ".mov", ".mkv"}:
                    assets.append({"role": "original", "name": source_path.name})
        manifest = self._video_json(root, "ai-analysis/media-manifest.json")
        for item in manifest.get("items", []):
            transcript = self._video_json(root, item.get("transcript_path", ""))
            if transcript.get("status") == "ok":
                chars = sum(len(segment.get("text", "")) for segment in transcript.get("segments", []))
                assets.append({"role": "transcript", "characters": chars, "precision": transcript.get("precision")})
        if not any(a["role"] == "subtitles" for a in assets) and candidate.get("subtitles"):
            assets.append({"role": "subtitles", "count": len(re.findall(r"(?m)^\d+\s*$", candidate["subtitles"]))})
        shots = [{"shotId": row["shot"]["shotId"], "start": row["shot"]["startSeconds"]} for row in descriptor.get("shots", [])]
        animations = []
        by_id = {s["shotId"]: s for s in progress.get("shotProgress", [])}
        teaching = self._video_json(run, "native-teaching_clips.json")
        for shot in teaching.get("shots", []):
            by_id.setdefault(shot["id"], {"status": shot.get("status"), "renderedFrames": shot.get("progress_frames"), "totalFrames": shot.get("total_frames")})
        for item in descriptor.get("animations", []):
            fact = by_id.get(item["shotId"], {})
            animations.append({"shotId": item["shotId"], "title": item.get("requirement", ""),
                               "duration": item.get("durationSeconds"), "status": fact.get("status"),
                               "frames": fact.get("renderedFrames"), "totalFrames": fact.get("totalFrames")})
        uploaded = False
        for journal_path in run.glob("video-result-*.json"):
            journal = self._video_json(run, journal_path.name)
            remote_result = journal.get("video_result") or {}
            if (journal.get("result_status") == "succeeded" and remote_result.get("identity") == identity
                    and remote_result.get("candidateArtifact") and remote_result.get("previewArtifact") and remote_result.get("subtitleArtifact")):
                uploaded = True
        images = [r["visual"]["image"] for r in descriptor.get("shots", []) if r.get("visual", {}).get("image") and r["visual"]["image"].get("status") in {"saved", "unsaved"}]
        if images:
            assets.append({"role": "images", "count": len(images), "pending": sum(i.get("rightsStatus") != "confirmed" for i in images)})
        return {"state": "check-failed" if candidate and candidate_failed(candidate) else "returned" if candidate else "connected" if handshake else "offline", "scriptAlignment": suggestions.get("script_alignment", {}), "mediaUrl": descriptor.get("mediaUrl") if isinstance(descriptor.get("mediaUrl"), str) and urllib.parse.urlparse(descriptor["mediaUrl"]).scheme in {"http", "https"} else None, "title": project["title"],
                "line": "direct" if any(step.get("action") == "compose" for step in binding.get("steps", [])) else None,
                "sourceDuration": number(duration), "materials": assets, "animations": animations,
                "suggestions": cuts, "shots": shots, "waveformPeaks": peaks,
                "tools": {"chatcut": {"installed": installed["installed"], "version": installed["version"],
                                      "login": login, "handshake": handshake, "projectRef": project_ref, "projectUrl": deep_link},
                          "kdenlive": {"installed": kdenlive["installed"], "version": kdenlive["version"]}},
                "precutCount": precut.get("precutCount") if type(precut.get("precutCount")) is int and precut["precutCount"] >= 0 else None,
                "exported": progress.get("exported") is True, "animationCount": len(candidate.get("animations", [])),
                "candidate": {key: candidate[key] for key in ("status", "durationSeconds", "frameCount", "cutCount", "removedSeconds", "returnedAt", "checks") if key in candidate},
                "editorName": editor.get("displayName"), "choice": self.video_editor_choice(project_id),
                "uploaded": uploaded}

    def load_asset_index(self) -> dict[str, Any]:
        try:
            return load_index(self.asset_index_path)
        except AssetIndexError as exc:
            # Index diagnostics may include the configured filesystem location.
            raise ProjectStoreError("asset_library_unavailable", "素材库索引不可用") from exc

    def media_manifest(self, project_id: str) -> dict[str, Any]:
        """Read the connected project's manifest without exposing its path."""

        workspace = self.store.local_workspace_path(project_id)
        manifest_path = (workspace / INBOX_MANIFEST_RELATIVE_PATH).resolve()
        try:
            manifest_path.relative_to(workspace.resolve())
        except ValueError as exc:
            raise ProjectStoreError("inbox_manifest_invalid", "媒体清单位置无效") from exc
        if not manifest_path.is_file():
            raise ProjectStoreError("inbox_manifest_missing", "项目尚未生成媒体清单")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProjectStoreError("inbox_manifest_invalid", "媒体清单无法读取") from exc
        if not isinstance(manifest, dict):
            raise ProjectStoreError("inbox_manifest_invalid", "媒体清单格式无效")
        return manifest

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

    def refresh_doctor(self):
        if self.doctor_thread and self.doctor_thread.is_alive():
            return
        def run():
            from doctor import collect_checks
            checks, metadata = collect_checks()
            labels = {'openchatcut': 'OpenChatCut', 'openfilm': 'OpenFilm'}
            public = []
            for check in checks:
                if check.id == 'openclaw_cloud_pairing':
                    continue
                if check.id.startswith('edit_tool_'):
                    tool = check.id.removeprefix('edit_tool_')
                    summary = labels[tool] + ' · ' + (metadata['edit_tools'][tool]['version'] or '未知版本')
                else:
                    summary = check.summary
                public.append(dict(id=check.id, status='ready' if check.ok else check.state, summary=summary,
                                   repair=check.action if not check.ok else None))
            for name, title in [('chatcut', 'ChatCut Desktop'), ('jianying', '剪映'), ('kdenlive', 'Kdenlive')]:
                tool = metadata['tools'][name]
                ready = tool['status'] == 'online'
                public.append(dict(id='chatcut_mcp' if name=='chatcut' else name, status='ready' if ready else tool['status'],
                                   summary=title + (' · ' + str(tool['version']) if ready else ' 还没连上本机'),
                                   repair=None if ready else '还没连上本机。在 ChatCut 里开启本机连接后，点「重新检查」。' if name=='chatcut' else title + '：' + tool['reason']))
            self.doctor_checks = public
            self.doctor_checked_at = datetime.now(timezone.utc).isoformat()
        self.doctor_thread = threading.Thread(target=run, daemon=True)
        self.doctor_thread.start()

    def diagnostics_projection(self, *, refresh=False) -> dict[str, Any]:
        checks = [
            {
                "id": "project_store",
                "status": "ready",
                "summary": "项目存储可读写",
                "repair": None,
            },
            {
                "id": "asset_library",
                "status": "ready" if self.asset_index_path.is_file() else "not_configured",
                "summary": "结构化素材索引已就绪" if self.asset_index_path.is_file() else "尚未建立结构化素材索引",
                "repair": None if self.asset_index_path.is_file() else "登记一项可复用素材",
            },
        ]
        providers = self.model_provider_store.list_configs()
        checks.append(
            {
                "id": "creative_model",
                "status": "ready" if providers else "not_configured",
                "summary": "创意模型已配置" if providers else "尚未配置创意模型",
                "repair": None if providers else "在设置中添加模型提供方",
            }
        )
        upstream = self.upstream_session.snapshot()
        checks.append(
            {
                "id": "upstream_identity",
                "status": "ready" if upstream.get("upstream_features_available") is True else "optional",
                "summary": "上游身份已连接" if upstream.get("upstream_features_available") is True else "上游身份未连接，本地功能仍可用",
                "repair": None,
            }
        )
        checks.extend(self.doctor_checks)
        if refresh or not self.doctor_checks:
            self.refresh_doctor()
        canonical = json.dumps(checks, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {
            "schemaVersion": "photo_content_os_diagnostics_v1",
            "checks": checks,
            "checked_at": self.doctor_checked_at,
            "checking": bool(self.doctor_thread and self.doctor_thread.is_alive()),
            "reportDigest": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        }

    def upstream_tasks_projection(self) -> list[dict[str, object]]:
        allowed = {"queued", "running", "completed", "failed", "expired", "cancelled"}
        raw_tasks = self.upstream_task_reader() if self.upstream_task_reader is not None else []
        tasks: list[dict[str, object]] = []
        for raw in raw_tasks:
            status = raw.get("status")
            task_id = raw.get("task_id")
            if status not in allowed or not isinstance(task_id, str) or not task_id:
                raise ProjectStoreError("upstream_task_invalid", "上游任务投影无效")
            tasks.append({"taskId": task_id, "status": status, "title": str(raw.get("title") or "")[:160]})
        return tasks

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

            def _send(self, status: int, body: bytes, content_type: str, headers: dict[str, str] | None = None) -> None:
                self._send_headers(status, len(body), content_type, headers)
                self.wfile.write(body)

            def _send_headers(self, status, length, content_type, headers=None):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(length))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.send_header("Cache-Control", "no-store" if content_type.startswith("application/json") else "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self'; frame-ancestors 'none'")
                origin = self.headers.get('Origin')
                if app.video_workflow.allowed_origin(origin) or (origin and getattr(self, '_validated_response_origin', None) == origin):
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                self.end_headers()

            def _media(self, path):
                if path is None:
                    self._json(404, _error('media_not_found', '预览不存在'))
                    return
                size = path.stat().st_size
                start, end = 0, size - 1
                requested = self.headers.get('Range')
                headers = {'Accept-Ranges': 'bytes'}
                content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
                if requested:
                    match = re.fullmatch(r'bytes=(\d{0,20})-(\d{0,20})', requested)
                    valid = bool(match and any(match.groups()))
                    if valid:
                        first, last = match.groups()
                        if first:
                            start = int(first)
                            end = min(int(last), end) if last else end
                        else:
                            start = max(0, size - int(last))
                            valid = int(last) > 0
                        valid = valid and 0 <= start <= end < size
                    if not valid:
                        self._send(416, b'', content_type, {**headers, 'Content-Range': f'bytes */{size}'})
                        return
                    headers['Content-Range'] = f'bytes {start}-{end}/{size}'
                length = end - start + 1
                self._send_headers(206 if requested else 200, length, content_type, headers)
                with path.open('rb') as source:
                    source.seek(start)
                    while length:
                        data = source.read(min(length, 256 * 1024))
                        if not data:
                            break
                        self.wfile.write(data)
                        length -= len(data)

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

            def do_OPTIONS(self) -> None:  # noqa: N802
                origin = self.headers.get('Origin')
                if not app.video_workflow.allowed_origin(origin):
                    self._json(HTTPStatus.FORBIDDEN, _error('origin_forbidden', '只允许本机页面提交修改'))
                    return
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Content-OS-CSRF, X-Video-Identity')
                self.send_header('Content-Length', '0')
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                try:
                    self._assert_local()
                    parsed = urllib.parse.urlparse(self.path)
                    segments = self._segments(parsed.path)
                    if parsed.path.startswith("/api/") and not is_registered_route("GET", parsed.path):
                        self._json(HTTPStatus.NOT_FOUND, _error("route_not_found", "接口不存在"))
                        return
                    if segments[:2] == ['api', 'direct']:
                        query = urllib.parse.parse_qs(parsed.query)
                        if segments[2] == 'samples' and 'poster' in query:
                            self._media(app.direct_video.generator.library.poster(query['poster'][0]))
                        elif segments[2] == 'styles':
                            self._json(200, {'ok': True, **app.direct_video.styles()})
                        else:
                            self._json(200, {'ok': True, **app.direct_video.library(segments[2])})
                        return
                    if len(segments) >= 6 and segments[:2] == ['api', 'projects'] and segments[3:5] == ['direct', 'style-drafts']:
                        project_id, draft_id = segments[2], segments[5]
                        if len(segments) == 6:
                            self._json(200, {'ok': True, 'draft': app.direct_video.draft(project_id, draft_id)})
                        else:
                            app.direct_video.generator.read_draft(project_id, draft_id)
                            self._media(app.direct_video.artifact(project_id, draft_id, segments[6], '01'))
                        return
                    if len(segments) >= 6 and segments[:2] == ['api', 'projects'] and segments[3:5] == ['direct', 'jobs']:
                        project_id, job_id = segments[2], segments[5]
                        if len(segments) == 6:
                            self._json(200, {'ok': True, 'job': app.direct_video.get(project_id, job_id)})
                        elif len(segments) == 7 and segments[6] == 'output.mp4':
                            self._media(app.direct_video.artifact(project_id, job_id, 'output.mp4'))
                        elif len(segments) == 9 and segments[6] == 'shots':
                            version = urllib.parse.parse_qs(parsed.query).get('version', [None])[0]
                            path = app.direct_video.artifact(project_id, job_id, segments[8], segments[7], version)
                            if segments[8] == 'code':
                                self._send(200, path.read_bytes(), 'text/plain; charset=utf-8')
                            else:
                                self._media(path)
                        return
                    if parsed.path.startswith('/api/review/'):
                        if parsed.query:
                            self._json(404, _error('media_not_found', '预览不存在'))
                            return
                        review = app.media_review
                        if parsed.path == '/api/review/catalog':
                            self._json(200, {'ok': True, **review.catalog()})
                        elif parsed.path == '/api/review/music':
                            self._json(200, {'ok': True, **review.music_payload()})
                        elif parsed.path == '/api/review/music-settings':
                            self._json(200, {'ok': True, **app.review_jobs.music_settings()})
                        elif len(segments) == 4 and segments[2] == 'imports':
                            job = app.review_jobs.import_status(segments[3])
                            self._json(200 if job else 404, {'ok': bool(job), 'job': job})
                        elif len(segments) == 5 and segments[2] == 'pieces' and segments[4] == 'shots':
                            self._json(200, {'ok': True, **review.shots(segments[3])})
                        elif len(segments) == 7 and segments[2] == 'pieces' and segments[4] == 'media':
                            try:
                                path = review.media(segments[3], segments[5], segments[6])
                            except ProjectStoreError as exc:
                                if exc.code not in ('project_not_found', 'workspace_not_connected', 'workspace_not_found'):
                                    raise
                                path = None
                            self._media(path)
                        elif len(segments) == 5 and segments[2] == 'assets' and segments[4] == 'preview':
                            asset = get_asset(app.load_asset_index(), segments[3])
                            self._media(review.asset_preview(asset) if asset else None)
                        elif len(segments) == 5 and segments[2] == 'music' and segments[4] == 'audio':
                            self._media(review.music_audio(segments[3]))
                        else:
                            self._json(404, _error('route_not_found', '接口不存在'))
                        return
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
                    if parsed.path == "/api/diagnostics":
                        self._json(HTTPStatus.OK, {"ok": True, "diagnostics": app.diagnostics_projection(refresh=parsed.query == 'refresh=1')})
                        return
                    if parsed.path == "/api/settings":
                        self._json(HTTPStatus.OK, {"ok": True, "settings": app.settings_projection()})
                        return
                    if parsed.path == "/api/settings/analysis-budget":
                        self._json(HTTPStatus.OK, {"ok": True, "analysisBudget": app.analysis_budget_store.load()})
                        return
                    if parsed.path == "/api/setup/state":
                        self._json(HTTPStatus.OK, {"ok": True, "setup": app.onboarding_store.snapshot()})
                        return
                    if parsed.path == "/api/upstream/tasks":
                        upstream = app.upstream_session.snapshot()
                        self._json(
                            HTTPStatus.OK,
                            {
                                "ok": True,
                                "tasks": app.upstream_tasks_projection(),
                                "localFeaturesAvailable": upstream.get("local_features_available") is True,
                                "upstreamFeaturesAvailable": upstream.get("upstream_features_available") is True,
                            },
                        )
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
                    if len(segments)==5 and segments[:2]==['api','projects'] and segments[3]=='video-preview':
                        preview=app.video_workflow.preview(segments[2],segments[4])
                        body = preview.read_bytes()
                        size = len(body)
                        requested = self.headers.get('Range')
                        headers = {'Accept-Ranges': 'bytes'}
                        if requested:
                            match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                            start, end = 0, size - 1
                            valid = bool(match and any(match.groups()) and all(len(part) <= 20 for part in match.groups()))
                            if valid:
                                first, last = match.groups()
                                if first:
                                    start = int(first)
                                    end = min(int(last), size - 1) if last else size - 1
                                else:
                                    suffix = int(last)
                                    start = max(0, size - suffix)
                                    valid = suffix > 0
                                valid = valid and 0 <= start <= end < size
                            if not valid:
                                self._send(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, b'', 'video/mp4',
                                           {**headers, 'Content-Range': f'bytes */{size}'})
                                return
                            self._send(HTTPStatus.PARTIAL_CONTENT, body[start:end+1], 'video/mp4',
                                       {**headers, 'Content-Range': f'bytes {start}-{end}/{size}'})
                        else:
                            self._send(HTTPStatus.OK, body, 'video/mp4', headers)
                        return
                    if len(segments) == 4 and segments[:2] == ['api', 'projects'] and segments[3] == 'video-subtitles':
                        self._send(HTTPStatus.OK, app.video_workflow.subtitles(segments[2]), 'application/x-subrip; charset=utf-8')
                        return
                    if len(segments) == 3 and segments[:2] == ["api", "projects"]:
                        self._json(HTTPStatus.OK, {"ok": True, "project": app.store.get_project(segments[2]), "videoHandoff": app.video_handoff_projection(segments[2])})
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
                except (ProjectStoreError, DirectVideoError, ValueError, MusicError) as exc:
                    self._handle_error(exc)

            def do_POST(self) -> None:  # noqa: N802
                self._write_request("POST")

            def do_PATCH(self) -> None:  # noqa: N802
                self._write_request("PATCH")

            def do_PUT(self) -> None:  # noqa: N802
                self._write_request('PUT')

            def do_DELETE(self) -> None:  # noqa: N802
                self._write_request('DELETE')

            def _write_request(self, method: str) -> None:
                try:
                    self._assert_write()
                    # Reopening the native engine rotates its origin during this
                    # request. Preserve only the origin validated at entry.
                    origin = self.headers.get('Origin')
                    self._validated_response_origin = origin if app.video_workflow.allowed_origin(origin) else None
                    parsed = urllib.parse.urlparse(self.path)
                    segments = self._segments(parsed.path)
                    if not is_registered_route(method, parsed.path):
                        self._json(HTTPStatus.NOT_FOUND, _error("route_not_found", "接口不存在"))
                        return
                    if segments[:2] == ['api', 'direct']:
                        self._assert_direct_origin()
                        self._body()
                        self._json(200, {'ok': True, **app.direct_video.library('decision', segments[4], segments[5] == 'adopt')})
                        return
                    if method == 'POST' and len(segments) >= 5 and segments[:2] == ['api', 'projects'] and segments[3:5] == ['direct', 'style-drafts']:
                        self._assert_direct_origin()
                        draft = app.direct_video.draft(segments[2], segments[5] if len(segments) > 5 else None,
                                                       self._body(), revise=len(segments) > 5)
                        self._json(202, {'ok': True, 'draft': draft})
                        return
                    if method in {'POST', 'PUT', 'DELETE'} and len(segments) >= 5 and segments[:2] == ['api', 'projects'] and segments[3:5] == ['direct', 'jobs']:
                        self._assert_direct_origin()
                        project_id = segments[2]
                        if len(segments) == 7 and segments[6] == 'narration':
                            try:
                                length = int(self.headers.get('Content-Length', '0'))
                            except ValueError as exc:
                                raise DirectVideoError('narration_invalid') from exc
                            job = app.direct_video.narration(project_id, segments[5], self.rfile, length, self.headers.get('Content-Type', ''))
                        else:
                            body = self._body()
                            if len(segments) == 5:
                                job = app.direct_video.create(project_id, body)
                            elif len(segments) == 7:
                                job = app.direct_video.command(project_id, segments[5], 'compose', body)
                            else:
                                action = 'unsample' if method == 'DELETE' else segments[8]
                                job = app.direct_video.command(project_id, segments[5], action, body, sid=segments[7])
                        self._json(201 if len(segments) == 5 else 200, {'ok': True, 'job': job})
                        return
                    if parsed.path.startswith('/api/review/'):
                        value = self._body()
                        if parsed.path == '/api/review/music/import':
                            result = {'job': app.review_jobs.import_music(value)}
                        elif len(segments) == 5 and segments[2] == 'music' and segments[4] == 'reanalyze':
                            if value.get('part') not in ('beat', 'tags'):
                                self._json(HTTPStatus.BAD_REQUEST, _error('music_part_invalid', '分析部分必须是 beat 或 tags'))
                                return
                            queue = app.media_review.analysis_queue
                            if not any(track['file_sha256'] == segments[3] for track in queue.library.list_tracks()):
                                self._json(HTTPStatus.NOT_FOUND, _error('music_track_not_found', '曲目不存在'))
                                return
                            result = queue.enqueue(segments[3], value['part'])
                        elif len(segments) == 5 and segments[2] == 'pieces' and segments[4] == 'decisions':
                            result = app.media_review.decide(segments[3], value)
                        elif len(segments) == 5 and segments[2] == 'pieces' and segments[4] == 'jobs':
                            result = app.review_jobs.shots(segments[3], value.get('action'))
                        else:
                            self._json(404, _error('route_not_found', '接口不存在'))
                            return
                        self._json(200, {'ok': True, **result})
                        return
                    segments = self._segments(urllib.parse.urlparse(self.path).path)
                    if method == 'POST' and len(segments) == 4 and segments[:2] == ['api', 'projects'] and segments[3] == 'video-return':
                        try:
                            identity = json.loads(self.headers.get('X-Video-Identity', ''))
                            length = int(self.headers.get('Content-Length', '0'))
                        except (ValueError, TypeError) as exc:
                            raise ProjectStoreError('body_invalid', '成片交接信息无效') from exc
                        data = app.video_workflow.receive(segments[2], self.rfile, length, identity)
                        self._json(HTTPStatus.OK, {'ok': True, 'videoHandoff': data})
                        return
                    body = self._body()
                    expected = body.get("expectedRevision")
                    if expected is not None and type(expected) is not int:
                        raise ProjectStoreError("revision_invalid", "expectedRevision 必须是整数")
                    expected_revision = expected
                    if method == "POST" and segments == ["api", "settings", "analysis-budget"]:
                        if expected_revision is None:
                            raise ProjectStoreError("revision_invalid", "expectedRevision 必须是整数")
                        updated = app.analysis_budget_store.update(
                            body.get("budget"), expected_revision=expected_revision
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "analysisBudget": updated})
                        return
                    if method == "POST" and segments == ["api", "setup", "state"]:
                        if expected_revision is None:
                            raise ProjectStoreError("revision_invalid", "expectedRevision 必须是整数")
                        setup = app.onboarding_store.transition(
                            body.get("step"),
                            body.get("status"),
                            expected_revision=expected_revision,
                            reason_code=body.get("reasonCode"),
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "setup": setup})
                        return
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
                        and len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["inbox-plan", "confirm"]
                    ):
                        if expected_revision is None:
                            raise ProjectStoreError("revision_invalid", "expectedRevision 必须是整数")
                        plan = app.inbox_batch_plan(segments[2])
                        supplied_digest = body.get("planDigest")
                        if supplied_digest != plan.get("plan_digest"):
                            raise ProjectStoreError("plan_digest_conflict", "分批计划已变化，请重新预览")
                        batch_id = body.get("batchId")
                        batch = next((item for item in plan["batches"] if item.get("batch_id") == batch_id), None)
                        if batch is None:
                            raise ProjectStoreError("batch_not_found", "分批不存在")
                        project, confirmation = app.store.confirm_inbox_batch(
                            segments[2],
                            plan_digest=str(supplied_digest),
                            batch_id=str(batch_id),
                            target_project_id=str(body.get("targetProjectId") or ""),
                            expected_revision=expected_revision,
                            media_ids=list(batch["media_ids"]),
                        )
                        self._json(
                            HTTPStatus.OK,
                            {"ok": True, "project": project, "confirmation": confirmation},
                        )
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
                        and len(segments) == 4
                        and segments[:2] == ["api", "projects"]
                        and segments[3] == "assets"
                    ):
                        if expected_revision is None:
                            raise ProjectStoreError("revision_invalid", "expectedRevision 必须是整数")
                        asset_id = body.get("assetId")
                        if not isinstance(asset_id, str) or not asset_id:
                            raise ProjectStoreError("asset_id_invalid", "素材 ID 无效")
                        asset = get_asset(app.load_asset_index(), asset_id)
                        if asset is None:
                            raise ProjectStoreError("asset_not_found", "素材不存在")
                        project = app.store.add_asset_reference(
                            segments[2],
                            asset=asset,
                            intended_use=str(body.get("intendedUse") or ""),
                            expected_revision=expected_revision,
                        )
                        self._json(HTTPStatus.OK, {"ok": True, "project": project})
                        return
                    if (
                        method == "POST"
                        and len(segments) == 5
                        and segments[:2] == ["api", "projects"]
                        and segments[3:] == ["media-delete", "recommendations"]
                    ):
                        candidates = generate_delete_recommendations(app.media_manifest(segments[2]))
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
                    if method == 'POST' and len(segments) == 4 and segments[:2] == ['api', 'projects'] and segments[3] == 'video-workflow':
                        data = app.video_workflow.command(segments[2], body)
                        self._json(HTTPStatus.OK, {'ok': True, 'videoHandoff': data})
                        return
                    if method == "PATCH" and len(segments) == 3 and segments[:2] == ["api", "projects"]:
                        if "videoEditor" in body:
                            project = app.store.get_project(segments[2])
                            if expected_revision != project["revision"]:
                                raise ProjectStoreError("revision_conflict", "项目已变化")
                            if body.get("changes"):
                                raise ProjectStoreError("editor_invalid", "剪辑软件选择不能混合修改")
                            choice = app.video_editor_choice(segments[2], body["videoEditor"])
                            self._json(HTTPStatus.OK, {"ok": True, "project": project, "videoEditor": choice})
                            return
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
                    DirectVideoError,
                    ArchiveLocationConfigError,
                    AnalysisBudgetError,
                    DeleteRecommendationError,
                    MediaTrashFlowError,
                    ModelProviderConfigError,
                    OnboardingStateError,
                    ProjectStoreError,
                    MusicError,
                    TypeError,
                    UpstreamIdentityContractError,
                    UpstreamSessionContractError,
                    ValueError,
                ) as exc:
                    self._handle_error(exc)

            def _assert_direct_origin(self) -> None:
                origin = self.headers.get('Origin')
                if not origin:
                    return
                parsed = urllib.parse.urlparse(origin)
                try:
                    valid = parsed.scheme == 'http' and parsed.netloc.lower() == (self.headers.get('Host') or '').lower() and parsed.path in {'', '/'} and not parsed.query and not parsed.fragment and not parsed.username
                except ValueError:
                    valid = False
                if not valid:
                    raise ProjectStoreError('origin_forbidden', '只允许同一工作台页面提交修改')

            def _handle_error(self, exc: Exception) -> None:
                if isinstance(exc, DirectVideoError):
                    code = exc.code
                    status = 404 if code in {'job_not_found', 'shot_not_found', 'artifact_not_found', 'version_not_found', 'sample_not_found', 'proposal_not_found', 'style_base_not_found', 'draft_not_found'} else 409 if code in {'job_busy', 'shots_not_ready', 'design_not_ready', 'output_not_ready', 'proposal_not_ready', 'draft_not_ready', 'draft_busy'} else 400
                    self._json(status, _error(code, '直出任务暂时无法执行，请检查输入或任务状态后重试。'))
                    return
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
    prepare_caches: bool = False,
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
    upstream_task_reader: CollectionCallable[[], list[Mapping[str, object]]] | None = None,
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
        upstream_task_reader=upstream_task_reader,
    )
    server = ThreadingHTTPServer((host, port), application.handler())
    application.media_review.analysis_queue.start(server)
    actual_host, actual_port = server.server_address[:2]
    url_host = "127.0.0.1" if actual_host in {"0.0.0.0", "::"} else actual_host
    url = f"http://{url_host}:{actual_port}/"
    application.video_workflow.origin = url.rstrip('/')
    original_close = server.server_close
    def close_owned_sessions():
        application.review_jobs.close()
        try:
            application.video_workflow.close()
        finally:
            original_close()
    server.server_close = close_owned_sessions
    if prepare_caches:
        application.review_jobs.prepare()
    if on_ready:
        on_ready(url)
    return server


def served_route_inventory() -> list[dict[str, str]]:
    """Expose the exact canonical registration used to guard every API request."""

    return route_inventory()
