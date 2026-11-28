"""Studio side of the installed Agent's first-project handoff.

The installed ``openclaw_media`` Agent owns pairing, polling, receipts and the
server calls. This module implements the two Studio ports it injects:
``select_project`` turns a paired selection request into a locally confirmed
CreativeProject (existing or created) and ``stage_handoff`` records where one
verified job landed. Both persist under ``local_media_root()`` so a restarted
device finds the same project, version and job. The installed Agent uses the
local Studio inbox to collect explicit operator decisions.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SYSTEM_ROOT = Path(__file__).resolve().parents[1]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from openclaw_product_contract import ProductContractError, video_digest  # noqa: E402
from media import utc_now_datetime as _now  # noqa: E402
from runtime_paths import local_media_root  # noqa: E402
from studio.direct_handoff_contract import (  # noqa: E402
    RUN_RECORD_IDENTITY_KEYS,
    RUN_RECORD_SCHEMA,
    binding_from_record,
    local_file,
    read_delivered_handoff,
    read_run_record,
    run_record_path,
    selection_root,
)
from studio.project_store import ProjectStoreError  # noqa: E402

if __package__:
    from .constants import (
        DEFAULT_STATE_DIR,
        VIDEO_SUFFIXES,
    )
else:
    from constants import (
        DEFAULT_STATE_DIR,
        VIDEO_SUFFIXES,
    )
_ID = re.compile(r"[A-Za-z0-9_-]{8,160}")
_REQUEST_FIELDS = frozenset({"request_id", "public_variant_id", "public_account_id", "public_session_id",
                             "expected_work_revision", "expires_at", "revision"})
_RUN_BINDING_FIELDS = frozenset({"job_id", "device_id", "project_id", "project_revision", "confirmation_ref",
                                 "handoff_digest", "input_ref", "binding_generation"})
_PAIRS = {"jobId": "job_id", "publicVariantId": "work_id", "workRevision": "work_revision",
          "photoProjectId": "project_id", "photoProjectRevision": "project_revision",
          "catalogDigest": "catalog_digest", "confirmationRef": "confirmation_ref"}
_OPENED = {"editor_backend": "concat", "project_built": True, "opened_for_refine": True}

ConfirmationProvider = Callable[[Mapping[str, Any]], "Mapping[str, Any] | None"]


class SelectionError(RuntimeError, ValueError):
    """Carries a stable code. The Agent maps unknown codes to a generic stage failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def default_confirmation_provider(request: Mapping[str, Any]) -> None:
    """Keep requests pending when a caller supplies no confirmation provider.

    A provider answers with one explicit local confirmation:
    ``{"confirmed": True, "selection_mode": "existing", "project_id": ...}`` or
    ``{"confirmed": True, "selection_mode": "created", "title": ...}``; ``None`` keeps it pending.
    """
    return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False, suffix=".tmp") as output:
            temporary = Path(output.name)
            output.write(json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False).encode())
            output.flush()
            os.fsync(output.fileno())
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


_SELECTION_TTL = timedelta(minutes=15)
_TAIPEI = ZoneInfo("Asia/Taipei")
_MISSING = object()


def _expires_at(request: Mapping[str, Any]) -> datetime:
    try:
        expires = datetime.fromisoformat(request["expires_at"].replace("Z", "+00:00"))
        if expires.tzinfo is None:
            raise ValueError("missing timezone")
        return expires
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise SelectionError("video_selection_store_invalid") from exc


@contextmanager
def _selection_lock(root: Path, name: str):
    root.mkdir(parents=True, exist_ok=True)
    with (root / name).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _selection_path(root: Path, directory: str, request_id: str) -> Path:
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
        raise SelectionError("invalid_request")
    return root / directory / (request_id + ".json")


def _read_selection_json(path: Path) -> Any:
    # A missing file is expected before a decision. A file containing JSON null is corrupt.
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except FileNotFoundError:
        return _MISSING
    except (OSError, ValueError) as exc:
        raise SelectionError("video_selection_store_invalid") from exc


class StudioConfirmationStore:
    """Durable local inbox and immutable operator decisions, keyed by request ID."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _read_pending(self, path: Path) -> Any:
        item = _read_selection_json(path)
        if item is _MISSING:
            return item
        if (not isinstance(item, dict) or item.keys() != _REQUEST_FIELDS
                or item["request_id"] != path.stem
                or not all(isinstance(item[key], str) and _ID.fullmatch(item[key])
                           for key in ("request_id", "public_variant_id", "public_account_id", "public_session_id"))
                or not all(type(item[key]) is int and item[key] > 0
                           for key in ("expected_work_revision", "revision"))):
            raise SelectionError("video_selection_store_invalid")
        _expires_at(item)
        return item

    def _decision_path(self, request_id: str) -> Path:
        return _selection_path(self.root, "confirmations", request_id)

    @staticmethod
    def _valid_decision(decision: Any) -> bool:
        if not isinstance(decision, dict) or decision.get("confirmed") is not True:
            return False
        mode = decision.get("selection_mode")
        if mode == "existing":
            project_id = decision.get("project_id")
            return (decision.keys() == {"confirmed", "selection_mode", "project_id"}
                    and isinstance(project_id, str) and bool(_ID.fullmatch(project_id)))
        if mode == "created":
            title = decision.get("title")
            return (decision.keys() == {"confirmed", "selection_mode", "title"}
                    and isinstance(title, str) and 0 < len(title.strip()) <= 120)
        return False

    def _read_decision(self, request_id: str) -> Any:
        decision = _read_selection_json(self._decision_path(request_id))
        if decision is not _MISSING and not self._valid_decision(decision):
            raise SelectionError("video_selection_store_invalid")
        return decision

    def provider(self, request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        request_id = request["request_id"]
        path = _selection_path(self.root, "pending", request_id)
        with _selection_lock(self.root, ".confirmation.lock"):
            saved = self._read_pending(path)
            if saved is not _MISSING and saved != request:
                raise SelectionError("video_identity_stale")
            if saved is _MISSING:
                _write_json(path, dict(request))
            decision = self._read_decision(request_id)
            return None if decision is _MISSING else decision

    def list_pending(self) -> list[dict[str, Any]]:
        directory = self.root / "pending"
        try:
            paths = sorted(directory.iterdir())
        except FileNotFoundError:
            return []
        now = _now()
        items = []
        for path in paths:
            if path.suffix != ".json":
                continue
            item = self._read_pending(path)
            if item is _MISSING:
                continue
            expires = _expires_at(item)
            if expires <= now or self._read_decision(item["request_id"]) is not _MISSING:
                continue
            items.append({
                "requestId": item["request_id"],
                "workRevision": item["expected_work_revision"],
                "expiresAt": expires.isoformat(),
                "defaultTitle": (expires - _SELECTION_TTL).astimezone(_TAIPEI).strftime("策划台作品 %m-%d %H:%M"),
            })
        # Every request has the same TTL, so expiry and submission sort alike.
        return sorted(items, key=lambda item: datetime.fromisoformat(item["expiresAt"]), reverse=True)

    def submit(self, request_id: str, decision: dict[str, Any]) -> None:
        path = _selection_path(self.root, "pending", request_id)
        with _selection_lock(self.root, ".confirmation.lock"):
            request = self._read_pending(path)
            if request is _MISSING:
                raise SelectionError("video_selection_missing")
            if _now() >= _expires_at(request):
                raise SelectionError("video_selection_expired")
            if not self._valid_decision(decision):
                raise SelectionError("invalid_request")
            previous = self._read_decision(request_id)
            if previous is not _MISSING and previous != decision:
                raise SelectionError("video_identity_stale")
            if previous is _MISSING:
                _write_json(self._decision_path(request_id), decision)

    def project_source(self, project_id: str) -> dict[str, int] | None:
        try:
            paths = sorted((self.root / "requests").iterdir())
        except FileNotFoundError:
            return None
        matches = []
        for path in paths:
            if path.suffix != ".json":
                continue
            saved = _read_selection_json(path)
            if not isinstance(saved, dict) or not isinstance(saved.get("selection"), dict):
                raise SelectionError("video_selection_store_invalid")
            selection = saved["selection"]
            if selection.get("project_id") == project_id:
                try:
                    revision = selection["expected_work_revision"]
                    if type(revision) is not int or revision < 1:
                        raise ValueError("invalid revision")
                    confirmed = datetime.fromisoformat(selection["confirmed_at"])
                    if confirmed.tzinfo is None:
                        raise ValueError("missing timezone")
                except (KeyError, TypeError, ValueError) as exc:
                    raise SelectionError("video_selection_store_invalid") from exc
                matches.append((confirmed, revision))
        return {"workRevision": max(matches)[1]} if matches else None


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
        return _selection_path(self.root, "requests", request_id)

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
        with _selection_lock(self.root, ".selection.lock"):
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

    def _refine_run(self, identity: Mapping[str, Any]):
        if not isinstance(identity, Mapping) or identity.get("device_id") != self.device_id:
            raise SelectionError("video_identity_stale")
        job = identity.get("job_id")
        record = read_run_record(self.root, job)
        if record is None and isinstance(job, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", job):
            if not run_record_path(self.root, job).exists():
                return None
        if not record or record["device_id"] != self.device_id:
            raise SelectionError("video_identity_stale")
        ctx = delivered_context(self.store, record["project_id"], identity.get("video_identity"), media=self.media)
        run = RefineRun(ctx)
        if video_digest(run.identity) != video_digest(dict(identity)) or ctx["workspace"] != self.workspace:
            raise SelectionError("video_identity_stale")
        return run

    def refine_status(self, job_identity: Mapping[str, Any]) -> Mapping[str, Any] | None:
        try:
            run = self._refine_run(job_identity)
            state = run.read() if run else None
        except (SelectionError, OSError) as exc:
            from openclaw_media.remote_client import RemoteError
            raise RemoteError(getattr(exc, "code", "video_refine_evidence_rejected")) from exc
        if state is None:
            return None
        evidence = {key: state[key] for key in ("identity", "handoff_digest", "opened")}
        return {"identity": run.identity, **_OPENED, "evidence_digest": video_digest(evidence)}

    def read_refined_candidate(self, job_identity: Mapping[str, Any]) -> Mapping[str, Any] | None:
        try:
            run = self._refine_run(job_identity)
            state = run.read() if run else None
            if state is None or "candidate" not in state:
                return None
            return {"identity": run.identity, **run.candidate_receipt(state)}
        except (SelectionError, OSError) as exc:
            from openclaw_media.remote_client import RemoteError
            raise RemoteError(getattr(exc, "code", "video_refine_candidate_changed")) from exc


def delivered_context(store, project_id, identity, *, media=None):
    """Resolve one delivered job. A caller-supplied identity only selects and compares."""
    media = local_media_root(media)
    job = identity.get("jobId") if isinstance(identity, Mapping) else None
    journal = selection_root(media)
    record = read_run_record(journal, job)
    if record is None or record["project_id"] != project_id:
        raise SelectionError("video_identity_stale")
    ctx = read_delivered_handoff(store, project_id, device_id=record["device_id"], job_id=job,
                                root=journal, media_root=media)
    if ctx is None or video_digest(ctx["identity"]) != video_digest(dict(identity)):
        raise SelectionError("video_identity_stale")
    if ctx["run_record"] != record:
        raise SelectionError("video_identity_stale")
    return ctx


class RefineRun:
    """The single handoff between Photo, Studio and the installed Agent for one run."""

    def __init__(self, ctx):
        record = ctx["run_record"]
        self.workspace = ctx["workspace"]
        self.identity = {
            "job_id": record["job_id"], "device_id": record["device_id"],
            "binding_id": record["binding_id"], "binding_generation": record["binding_generation"],
            "public_account_id": ctx["descriptor"]["public_account_id"], "video_identity": ctx["identity"],
        }
        key = hashlib.sha256(record["job_id"].encode()).hexdigest()[:32]
        self.directory = (self.workspace / "runs" / key).resolve()
        if self.directory != self.workspace / "runs" / key:
            raise SelectionError("video_identity_stale")
        self.path = self.directory / "studio-refine.json"
        self.handoff_digest = record["handoff_digest"]

    def read(self):
        state = _read_json(self.path)
        if state is None and not self.path.exists() and not self.path.is_symlink():
            return None
        if (not isinstance(state, dict) or state.get("identity") != self.identity
                or state.get("handoff_digest") != self.handoff_digest or not isinstance(state.get("opened"), dict)):
            raise SelectionError("video_refine_evidence_rejected")
        opened = state["opened"]
        if (opened.get("editor_backend") != "concat" or opened.get("project_built") is not True
                or opened.get("opened_for_refine") is not True):
            raise SelectionError("video_refine_evidence_rejected")
        self.project_directory(state)
        return state

    @contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "studio-refine.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def project_directory(self, state):
        project = local_file(self.workspace, state["opened"].get("project_ref"))
        if project is None or project != self.directory / "editor/concat-project/concat.json":
            raise SelectionError("video_refine_evidence_rejected")
        return project.parent.parent

    def record_opened(self, project, opened, source_sha256):
        manifest = (project / "concat.json").resolve()
        if (manifest != self.directory / "editor/concat-project/concat.json"
                or not manifest.is_file() or opened.get("editor_backend") != "concat" or opened.get("opened") is not True):
            raise SelectionError("video_refine_evidence_rejected")
        state = {"identity": self.identity, "handoff_digest": self.handoff_digest,
                 "opened": {**_OPENED, "project_ref": manifest.relative_to(self.workspace).as_posix(),
                            "source_sha256": source_sha256}}
        _write_json(self.path, state)

    @staticmethod
    def digest_file(path):
        with path.open("rb") as stream:
            return "sha256:" + hashlib.file_digest(stream, "sha256").hexdigest()

    def candidate_receipt(self, state):
        receipt = state["candidate"]
        if not isinstance(receipt, dict) or set(receipt) != {"candidate_ref", "candidate_sha256", "preview_ref", "preview_sha256"}:
            raise SelectionError("video_refine_candidate_changed")
        for kind in ("candidate", "preview"):
            path = local_file(self.workspace, receipt[kind + "_ref"])
            if path is None or not path.is_relative_to(self.directory) or self.digest_file(path) != receipt[kind + "_sha256"]:
                raise SelectionError("video_refine_candidate_changed")
        return receipt

    def pin_candidate(self, payload, video, check_current):
        with self.locked():
            check_current()
            state = self.read()
            if state is None:
                raise SelectionError("video_refine_evidence_rejected")
            export_digest = self.digest_file(video)
            if "candidate" in state:
                if state.get("export_sha256") != export_digest:
                    raise SelectionError("video_refine_candidate_changed")
                receipt = self.candidate_receipt(state)
                return _read_json(self.workspace / receipt["candidate_ref"])
            preview = local_file(self.workspace, payload["preview_ref"])
            if preview is None or preview != video.parent / "preview.mp4":
                raise SelectionError("video_refine_candidate_rejected")
            candidate = video.parent / "verified-candidate.json"
            # Studio's EDL digest is local metadata; the uploader has a closed payload shape.
            wire = {key: payload[key] for key in ("candidate", "progress", "preview_ref")}
            candidate_id = video_digest({"identity": self.identity, "export_sha256": export_digest})
            wire["candidate"]["publicCandidateId"] = "candidate_" + candidate_id.removeprefix("sha256:")[:32]
            wire["candidate"]["preview"]["artifact"] = None  # Agent supplies the server-scoped reference.
            wire["candidate"].pop("candidateDigest", None)
            wire["candidate"]["candidateDigest"] = video_digest(wire["candidate"])
            _write_json(candidate, wire)
            state["candidate"] = {"candidate_ref": candidate.relative_to(self.workspace).as_posix(),
                                  "candidate_sha256": self.digest_file(candidate),
                                  "preview_ref": payload["preview_ref"], "preview_sha256": self.digest_file(preview)}
            state["export_sha256"] = export_digest
            _write_json(self.path, state)
            return payload


def resolve_run_binding(run_binding: Mapping[str, Any], *, store, device_id: str, media_root: Path | None = None) -> dict[str, Any]:
    """Binding for ``PhotoNodeRegistry``, read from the delivered record of exactly this job."""
    media = local_media_root(media_root)
    record = read_run_record(selection_root(media), run_binding.get("job_id") if isinstance(run_binding, Mapping) else None)
    if (record is None or record["device_id"] != device_id or run_binding.keys() != _RUN_BINDING_FIELDS
            or any(run_binding[key] != record[key] for key in _RUN_BINDING_FIELDS)):
        raise ProductContractError("photo_binding_rejected")
    return binding_from_record(record, store.path, media)
