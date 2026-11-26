"""Studio side of the installed Agent's first-project handoff.

The installed ``openclaw_media`` Agent owns pairing, polling, receipts and the
server calls. This module implements the two Studio ports it injects:
``select_project`` turns a paired selection request into a locally confirmed
CreativeProject (existing or created) and ``stage_handoff`` records where one
verified job landed. Both persist under ``local_media_root()`` so a restarted
device finds the same project, version and job. When the real Studio selection
UI exists it only replaces the confirmation provider.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from openclaw_product_contract import ProductContractError, video_digest  # noqa: E402
from runtime_paths import local_media_root  # noqa: E402
from studio.direct_handoff_contract import (  # noqa: E402
    RUN_RECORD_IDENTITY_KEYS,
    RUN_RECORD_SCHEMA,
    binding_from_record,
    read_run_record,
    run_record_path,
    selection_root,
)
from studio.project_store import ProjectStoreError  # noqa: E402

DEFAULT_STATE_DIR = Path.home() / ".photo-content-os" / "studio"
VIDEO_SUFFIXES = (".mp4", ".mov", ".mkv")
_ID = re.compile(r"[A-Za-z0-9_-]{8,160}")
_REQUEST_FIELDS = frozenset({"request_id", "public_variant_id", "public_account_id", "public_session_id",
                             "expected_work_revision", "expires_at", "revision"})
_RUN_BINDING_FIELDS = frozenset({"job_id", "device_id", "project_id", "project_revision", "confirmation_ref",
                                 "handoff_digest", "input_ref", "binding_generation"})
_PAIRS = {"jobId": "job_id", "publicVariantId": "work_id", "workRevision": "work_revision",
          "photoProjectId": "project_id", "photoProjectRevision": "project_revision",
          "catalogDigest": "catalog_digest", "confirmationRef": "confirmation_ref"}

ConfirmationProvider = Callable[[Mapping[str, Any]], "Mapping[str, Any] | None"]


class SelectionError(RuntimeError, ValueError):
    """Carries a stable code. The Agent maps unknown codes to a generic stage failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_confirmation_provider(request: Mapping[str, Any]) -> None:
    """No Studio selection UI yet: every request stays pending until a provider is supplied.

    A provider answers with one explicit local confirmation:
    ``{"confirmed": True, "selection_mode": "existing", "project_id": ...}`` or
    ``{"confirmed": True, "selection_mode": "created", "title": ...}``; ``None`` keeps it pending.
    """
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as output:
            temporary = Path(output.name)
            output.write(json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False).encode())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise SelectionError("video_selection_store_invalid") from exc


def source_plan(project_root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    """Source files and the single editor step, read from the selected project's own workspace."""
    files = sorted(item.name for item in project_root.iterdir() if item.is_file())
    videos = [name for name in files if Path(name).suffix.lower() in VIDEO_SUFFIXES]
    subtitles = [name for name in files if Path(name).suffix.lower() == ".srt"]
    if len(videos) != 1 or len(subtitles) > 1:
        raise SelectionError("video_source_unavailable")
    kwargs: dict[str, Any] = {"source": {"local_ref": videos[0]}, "output_dir": "$output_root"}
    refs = [videos[0]]
    if subtitles:
        kwargs["subtitles"] = {"local_ref": subtitles[0]}
        refs.append(subtitles[0])
    if (project_root / "ai-analysis" / "edit_suggestions.json").is_file():
        kwargs["suggestions_path"] = {"local_ref": "ai-analysis/edit_suggestions.json"}
    return refs, [{"action": "editor", "function": "render", "kwargs": kwargs}]


class StudioSelectionPort:
    """The ``StudioPort`` the installed Agent calls; Media and render are not involved."""

    def __init__(self, store, *, device_id: str, workspace: Path, confirm: ConfirmationProvider | None = None,
                 media_root: Path | None = None) -> None:
        self.store = store
        self.device_id = device_id
        self.workspace = Path(workspace).expanduser().resolve()
        self.confirm = confirm or default_confirmation_provider
        self.media = local_media_root(media_root)
        self.root = selection_root(self.media)

    def _request_path(self, request_id: str) -> Path:
        if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
            raise SelectionError("invalid_request")
        return self.root / "requests" / (request_id + ".json")

    def _project(self, project_id: str) -> dict[str, Any]:
        try:
            return self.store.get_project(project_id)
        except ProjectStoreError as exc:
            raise SelectionError("video_identity_stale") from exc

    def _create_project(self, request_id: str, title: Any) -> dict[str, Any]:
        if not isinstance(title, str) or not title.strip():
            raise SelectionError("invalid_request")
        folder = self.media / "p1a-projects" / request_id
        folder.mkdir(parents=True, exist_ok=True)
        # A crash between creating the project and saving the selection must not create a second one.
        for known in self.store.list_projects():
            try:
                if self.store.local_workspace_path(known["id"]).resolve() == folder.resolve():
                    return known
            except ProjectStoreError:
                continue
        try:
            return self.store.create_project(title=title.strip(), local_workspace=str(folder))
        except ProjectStoreError as exc:
            raise SelectionError("invalid_request") from exc

    def _confirmed(self, request: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(decision, Mapping) or decision.get("confirmed") is not True:
            raise SelectionError("invalid_request")
        confirmed_at = _now()
        if confirmed_at >= datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00")):
            raise SelectionError("video_selection_expired")
        mode = decision.get("selection_mode")
        if mode == "existing" and decision.keys() == {"confirmed", "selection_mode", "project_id"}:
            project = self._project(decision["project_id"])
        elif mode == "created" and decision.keys() == {"confirmed", "selection_mode", "title"}:
            project = self._create_project(request["request_id"], decision["title"])
        else:
            raise SelectionError("invalid_request")
        return {**{key: request[key] for key in ("request_id", "public_variant_id", "public_account_id",
                                                  "public_session_id", "expected_work_revision")},
                "device_id": self.device_id, "project_id": project["id"], "project_revision": project["revision"],
                "selection_mode": mode, "confirmed_at": confirmed_at.isoformat()}

    def select_project(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not isinstance(request, Mapping) or request.keys() != _REQUEST_FIELDS:
            raise SelectionError("invalid_request")
        path = self._request_path(request["request_id"])
        saved = _read_json(path)
        if saved is not None:
            if not isinstance(saved, dict) or saved.get("request") != dict(request) or not isinstance(saved.get("selection"), dict):
                raise SelectionError("video_identity_stale")
            return {"status": "confirmed", "local_selection": dict(saved["selection"])}
        decision = self.confirm(dict(request))
        if decision is None or decision == {"status": "pending"}:
            return {"status": "pending"}
        selection = self._confirmed(request, decision)
        _write_json(path, {"request": dict(request), "selection": selection})
        return {"status": "confirmed", "local_selection": selection}

    def _checked_input(self, descriptor: Mapping[str, Any], input_ref: str) -> tuple[str, Mapping[str, Any]]:
        try:
            identity, mx = descriptor["identity"], descriptor["mxHandoff"]
            mx_identity = mx["identity"]
            job_id = identity["jobId"]
            if (not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job_id)
                    or input_ref != f"video-inputs/{job_id}/video.json"
                    or any(identity[key] != mx_identity[value] for key, value in _PAIRS.items())
                    or video_digest({k: v for k, v in mx.items() if k != "handoff_digest"}) != mx["handoff_digest"]):
                raise SelectionError("video_identity_stale")
            folder = (self.workspace / "video-inputs" / job_id).resolve()
            if (not folder.is_relative_to(self.workspace) or _read_json(folder / "handoff.json") != mx
                    or _read_json(folder / "video.json") != descriptor):
                raise SelectionError("video_identity_stale")
        except SelectionError:
            raise
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise SelectionError("invalid_request") from exc
        return job_id, mx

    def stage_handoff(self, descriptor: Mapping[str, Any], input_ref: str, local_selection: Mapping[str, Any]) -> Mapping[str, Any]:
        selection = dict(local_selection) if isinstance(local_selection, Mapping) else {}
        saved = _read_json(self._request_path(selection.get("request_id")))
        if not isinstance(saved, dict) or saved.get("selection") != selection:
            raise SelectionError("video_selection_missing")
        if selection["device_id"] != self.device_id:
            raise SelectionError("video_identity_stale")
        job_id, mx = self._checked_input(descriptor, input_ref)
        identity = descriptor["identity"]
        project = self._project(selection["project_id"])
        generation = descriptor.get("binding_generation")
        if (identity["photoProjectId"] != selection["project_id"] or project["revision"] != selection["project_revision"]
                or identity["photoProjectRevision"] != selection["project_revision"]
                or identity["publicVariantId"] != selection["public_variant_id"]
                or descriptor.get("public_account_id") != selection["public_account_id"]
                or type(generation) is not int or generation < 1 or not _ID.fullmatch(str(descriptor.get("binding_id")))):
            raise SelectionError("video_identity_stale")
        try:
            project_root = self.store.local_workspace_path(selection["project_id"]).resolve()
            if not project_root.is_relative_to(self.media) or not self.workspace.is_relative_to(self.media):
                raise SelectionError("video_identity_stale")
            sources, steps = source_plan(project_root)
        except ProjectStoreError as exc:
            raise SelectionError("video_identity_stale") from exc
        record = {
            "schema": RUN_RECORD_SCHEMA, "job_id": job_id, "device_id": self.device_id,
            "project_id": selection["project_id"], "project_revision": selection["project_revision"],
            "binding_id": descriptor["binding_id"], "binding_generation": generation,
            "confirmation_ref": identity["confirmationRef"], "handoff_digest": mx["handoff_digest"],
            "input_ref": input_ref, "catalog_digest": identity["catalogDigest"], "identity": dict(mx["identity"]),
            "workspace_ref": self.workspace.relative_to(self.media).as_posix(),
            "project_root_ref": project_root.relative_to(self.media).as_posix(),
            "source_refs": sources, "steps": steps, "candidate_ref": "candidate.json",
            "request_id": selection["request_id"], "delivered_at": _now().isoformat(),
        }
        existing = read_run_record(self.root, job_id)
        if existing is not None:
            if {k: existing[k] for k in RUN_RECORD_IDENTITY_KEYS} != {k: record[k] for k in RUN_RECORD_IDENTITY_KEYS}:
                raise SelectionError("idempotency_conflict")
        elif run_record_path(self.root, job_id).exists():
            raise SelectionError("video_selection_store_invalid")
        else:
            _write_json(run_record_path(self.root, job_id), record)
        return {key: record[key] for key in _RUN_BINDING_FIELDS}


def resolve_run_binding(run_binding: Mapping[str, Any], *, store, device_id: str, media_root: Path | None = None) -> dict[str, Any]:
    """Binding for ``PhotoNodeRegistry``, read from the delivered record of exactly this job."""
    media = local_media_root(media_root)
    record = read_run_record(selection_root(media), run_binding.get("job_id") if isinstance(run_binding, Mapping) else None)
    if (record is None or record["device_id"] != device_id or run_binding.keys() != _RUN_BINDING_FIELDS
            or any(run_binding[key] != record[key] for key in _RUN_BINDING_FIELDS)):
        raise ProductContractError("photo_binding_rejected")
    return binding_from_record(record, store.path, media)
