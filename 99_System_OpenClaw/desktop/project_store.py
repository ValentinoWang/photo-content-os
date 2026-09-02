#!/usr/bin/env python3
"""Versioned local CreativeProject store with block locks and safe projections."""
from __future__ import annotations

import copy, difflib, hashlib, json, os, re, secrets, tempfile, threading, urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows uses msvcrt below.
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:  # pragma: no cover - POSIX uses fcntl above.
    msvcrt = None  # type: ignore[assignment]

SCHEMA_VERSION = "creative_project_store_v1"
PROJECT_SCHEMA_VERSION = "creative_project_v1"
DOCUMENT_NAMES = ("brief", "script", "storyboard", "edl")
DOCUMENT_LABELS = {"brief": "创作 Brief", "script": "脚本", "storyboard": "分镜", "edl": "剪辑方案"}
DOWNSTREAM = {"brief": ("script", "storyboard", "edl", "delivery"), "script": ("storyboard", "edl", "delivery"), "storyboard": ("edl", "delivery"), "edl": ("delivery",)}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
PUBLISHING_METRICS = ("views", "likes", "comments", "shares", "saves", "follows")
MAX_PUBLIC_LINKS = 8
LOCAL_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/(?:Users|home|private|var|Volumes)/|[A-Za-z]:[\\/])")
REFERENCE_ASSET_ROLE = "reference"
AUTHORITY_BRIDGE_SCHEMA_VERSION = "document_authority_bridge_v1"
AUTHORITY_BRIDGE_TARGETS = {"brief": "02_project_brief.md", "script": "04_script.md"}
DEFAULTS = {
    "brief": (("brief-goal", "创作目标"), ("brief-audience", "目标受众"), ("brief-angle", "核心角度"), ("brief-constraints", "平台与边界")),
    "script": (("script-hook", "开头钩子"), ("script-body", "主体推进"), ("script-ending", "结尾与行动")),
    "storyboard": (("storyboard-opening", "开场镜头"), ("storyboard-development", "展开镜头"), ("storyboard-ending", "收束镜头")),
    "edl": (("edl-plan", "剪辑顺序"), ("edl-captions", "字幕与声音"), ("edl-notes", "人工精剪提示")),
}

_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()

@dataclass
class ProjectStoreError(ValueError):
    code: str
    message: str
    def __str__(self) -> str: return f"{self.code}: {self.message}"

# Semantic baseline: scripts/media_common.py's utc_now_z() (TF-09) -- byte-identical
# to this function. Kept as its own definition rather than importing across the
# desktop/ <-> scripts/ boundary: desktop/server.py adds scripts/ to sys.path before
# importing this module, but tests/test_p2_project_store.py imports it directly with
# only the repo root on sys.path, so `from media_common import utc_now_z` would break
# under that entrypoint without also adding path-setup here. If either producer's
# format ever needs to change, change both together.
def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _digest(value: str) -> str: return "sha256:" + hashlib.sha256(value.encode()).hexdigest()
def _is_digest(value: Any) -> bool: return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None
def _slug(value: str) -> str: return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:28] or "project"
def _text(blocks: list[dict[str, Any]]) -> str: return "\n\n".join(f"## {b.get('title','')}\n\n{b.get('body','')}".rstrip() for b in blocks).rstrip() + "\n"


def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path)
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.RLock())


def _lock_file(handle: Any) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return
    if msvcrt is None:  # pragma: no cover - all supported desktop platforms provide one.
        raise RuntimeError("no supported file locking primitive")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)


def _unlock_file(handle: Any) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    if msvcrt is not None:  # pragma: no branch - paired with _lock_file.
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _blocks(name: str) -> list[dict[str, Any]]: return [{"id": i, "title": t, "body": "", "locked": False} for i, t in DEFAULTS[name]]
def _history(version: int, blocks: list[dict[str, Any]], reason: str, actor: str) -> dict[str, Any]:
    snapshot = copy.deepcopy(blocks)
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"version": version, "created_at": _now(), "reason": reason, "actor": actor, "digest": _digest(canonical), "consumer_surface_digest": _digest(_text(snapshot)), "blocks": snapshot}


def _document_identity(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_version": int(document["version"]),
        "consumer_surface_digest": _digest(_text(document["blocks"])),
    }


def _refresh_authority_bridge(name: str, document: dict[str, Any]) -> None:
    target = AUTHORITY_BRIDGE_TARGETS.get(name)
    if target is None:
        return
    identity = _document_identity(document)
    bridge = document.setdefault("authority_bridge", {})
    if not isinstance(bridge, dict):
        raise ProjectStoreError("bridge_schema_invalid", "Brief/脚本桥接元数据格式无效")
    if bridge.get("schema_version") not in {None, AUTHORITY_BRIDGE_SCHEMA_VERSION}:
        raise ProjectStoreError("bridge_schema_invalid", "Brief/脚本桥接元数据版本无效")
    if bridge.get("target_relative_path") not in {None, target}:
        raise ProjectStoreError("bridge_target_invalid", "Brief/脚本桥接目标不允许变更")
    bridge.update(
        schema_version=AUTHORITY_BRIDGE_SCHEMA_VERSION,
        authoring_authority="creative_project_store",
        target_relative_path=target,
        source_document_version=identity["document_version"],
        source_consumer_surface_digest=identity["consumer_surface_digest"],
    )
    exported_matches = (
        bridge.get("exported_source_document_version") == identity["document_version"]
        and bridge.get("exported_source_consumer_surface_digest") == identity["consumer_surface_digest"]
        and _is_digest(bridge.get("target_content_digest"))
    )
    bridge["export_state"] = "current" if exported_matches else "pending_export"
    bridge.setdefault("exported_source_document_version", None)
    bridge.setdefault("exported_source_consumer_surface_digest", None)
    bridge.setdefault("target_content_digest", None)
    bridge.setdefault("exported_at", None)


def _document(name: str) -> dict[str, Any]:
    blocks = _blocks(name)
    document = {"name": name, "label": DOCUMENT_LABELS[name], "version": 1, "state": "draft", "stale": False, "stale_reason": "", "stale_sources": [], "consumed_inputs": {}, "blocks": blocks, "history": [_history(1, blocks, "project_created", "system")]}
    _refresh_authority_bridge(name, document)
    return document


def _normalize_project(project: dict[str, Any]) -> None:
    documents = project.get("documents")
    if not isinstance(documents, dict):
        raise ProjectStoreError("store_schema_invalid", "项目文档存储格式无效")
    for name in DOCUMENT_NAMES:
        document = documents.get(name)
        if not isinstance(document, dict) or not isinstance(document.get("blocks"), list) or not isinstance(document.get("history"), list):
            raise ProjectStoreError("store_schema_invalid", "项目文档存储格式无效")
        for history in document["history"]:
            if not isinstance(history, dict) or not isinstance(history.get("blocks"), list):
                raise ProjectStoreError("store_schema_invalid", "项目历史存储格式无效")
            history.setdefault("consumer_surface_digest", _digest(_text(history["blocks"])))
        document.setdefault("stale_sources", [])
        document.setdefault("consumed_inputs", {})
        if not isinstance(document["stale_sources"], list) or any(not isinstance(item, dict) for item in document["stale_sources"]):
            raise ProjectStoreError("store_schema_invalid", "文档过期来源格式无效")
        if not isinstance(document["consumed_inputs"], dict):
            raise ProjectStoreError("store_schema_invalid", "文档消费依据格式无效")
        _refresh_authority_bridge(name, document)
    delivery = project.setdefault("delivery", {"state": "not_started", "stale": False, "artifacts": []})
    if not isinstance(delivery, dict):
        raise ProjectStoreError("store_schema_invalid", "项目交付存储格式无效")
    delivery.setdefault("stale_sources", [])
    delivery.setdefault("consumed_inputs", {})
    if not isinstance(delivery["stale_sources"], list) or any(not isinstance(item, dict) for item in delivery["stale_sources"]):
        raise ProjectStoreError("store_schema_invalid", "交付过期来源格式无效")
    if not isinstance(delivery["consumed_inputs"], dict):
        raise ProjectStoreError("store_schema_invalid", "交付消费依据格式无效")
    history = project.setdefault("publishing_history", [])
    if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
        raise ProjectStoreError("store_schema_invalid", "发布历史存储格式无效")
    references = project.setdefault("references", [])
    if not isinstance(references, list):
        raise ProjectStoreError("store_schema_invalid", "参考资料存储格式无效")
    for reference in references:
        if not isinstance(reference, dict):
            raise ProjectStoreError("store_schema_invalid", "参考资料存储格式无效")
        role = reference.setdefault("asset_role", REFERENCE_ASSET_ROLE)
        if role != REFERENCE_ASSET_ROLE:
            raise ProjectStoreError("reference_role_invalid", "references 中的资产必须保持 reference 角色")
        reference["editing_eligible"] = False


def _public(project: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(project); workspace = result.get("local_workspace") or {}
    result["local_workspace"] = {"workspace_id": workspace.get("workspace_id"), "label": workspace.get("label"), "path_digest": workspace.get("path_digest"), "connected": bool(workspace.get("local_path")), "kind": "local_directory", "privacy": "local_only"}
    return result

class ProjectStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir.expanduser().resolve()
        self.path = self.state_dir / "creative-projects.json"
        self.lock_path = self.state_dir / "creative-projects.lock"
        self._thread_lock = _thread_lock(self.path)
        with self._mutation_lock():
            if not self.path.exists():
                _atomic(self.path, {"schema_version": SCHEMA_VERSION, "revision": 1, "projects": []})
            self._load()

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        with self._thread_lock:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with self.lock_path.open("a+b") as handle:
                _lock_file(handle)
                try:
                    yield
                finally:
                    _unlock_file(handle)

    @contextmanager
    def _transaction(self) -> Iterator[dict[str, Any]]:
        with self._mutation_lock():
            data = self._load()
            expected_store_revision = int(data["revision"])
            yield data
            self._save(data, expected_store_revision=expected_store_revision)

    def _load(self) -> dict[str, Any]:
        try: data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ProjectStoreError("store_unavailable", "项目存储无法读取") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("projects"), list): raise ProjectStoreError("store_schema_invalid", "项目存储版本或格式无效")
        if isinstance(data.get("revision"), bool) or not isinstance(data.get("revision"), int) or int(data["revision"]) < 1:
            raise ProjectStoreError("store_schema_invalid", "项目存储 revision 无效")
        for project in data["projects"]:
            if not isinstance(project, dict):
                raise ProjectStoreError("store_schema_invalid", "项目存储格式无效")
            _normalize_project(project)
        return data

    def _save(self, data: dict[str, Any], *, expected_store_revision: int) -> None:
        current = self._load()
        if int(current["revision"]) != expected_store_revision:
            raise ProjectStoreError("revision_conflict", "项目存储已被更新，请重试")
        data["revision"] = expected_store_revision + 1
        _atomic(self.path, data)

    @staticmethod
    def _find(data: dict[str, Any], project_id: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(project_id): raise ProjectStoreError("project_id_invalid", "项目 ID 无效")
        for project in data["projects"]:
            if project.get("id") == project_id: return project
        raise ProjectStoreError("project_not_found", "项目不存在")
    @staticmethod
    def _revision(project: dict[str, Any], expected: int | None) -> None:
        if expected is None:
            return
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise ProjectStoreError("revision_invalid", "expected revision 必须是整数")
        if expected != int(project.get("revision", 0)):
            raise ProjectStoreError("revision_conflict", "项目已被更新，请刷新后重试")
    @staticmethod
    def _touch(project: dict[str, Any], actor: str, action: str, detail: dict[str, Any]) -> None:
        project["revision"] = int(project.get("revision", 0)) + 1; project["updated_at"] = _now()
        project.setdefault("audit", []).append({"id": "audit-" + secrets.token_hex(8), "at": project["updated_at"], "actor": actor, "action": action, "detail": copy.deepcopy(detail)})

    @staticmethod
    def _invalidate(project: dict[str, Any], document: str) -> None:
        identity = _document_identity(project["documents"][document])
        source = {
            "document": document,
            "document_version": identity["document_version"],
            "consumer_surface_digest": identity["consumer_surface_digest"],
            "invalidated_at": _now(),
        }
        for target in DOWNSTREAM[document]:
            consumer = project["delivery"] if target == "delivery" else project["documents"][target]
            existing = [item for item in consumer.setdefault("stale_sources", []) if item.get("document") != document]
            consumer["stale_sources"] = existing + [copy.deepcopy(source)]
            labels = [DOCUMENT_LABELS.get(str(item.get("document")), str(item.get("document"))) for item in consumer["stale_sources"]]
            consumer.update(stale=True, stale_reason="、".join(labels) + " 已更新")
            if target == "delivery" and consumer.get("state") != "not_started":
                consumer["state"] = "stale"

    @staticmethod
    def _consume_stale_inputs(project: dict[str, Any], document_name: str, consumed_upstream: dict[str, dict[str, Any]] | None) -> None:
        document = project["documents"][document_name]
        stale_sources = document.setdefault("stale_sources", [])
        if not stale_sources:
            if consumed_upstream:
                raise ProjectStoreError("stale_provenance_unexpected", "当前文档没有待确认的上游输入")
            return
        if consumed_upstream is None:
            return
        if not isinstance(consumed_upstream, dict):
            raise ProjectStoreError("stale_provenance_invalid", "上游消费依据必须是对象")
        required = {str(item.get("document")): item for item in stale_sources}
        if set(consumed_upstream) != set(required):
            raise ProjectStoreError("stale_provenance_incomplete", "上游消费依据必须覆盖全部过期来源")
        consumed_at = _now()
        normalized: dict[str, dict[str, Any]] = {}
        for source_name, stale_source in required.items():
            supplied = consumed_upstream[source_name]
            if not isinstance(supplied, dict):
                raise ProjectStoreError("stale_provenance_invalid", "上游消费依据格式无效")
            current_source = project["documents"].get(source_name)
            if current_source is None:
                raise ProjectStoreError("stale_provenance_invalid", "上游文档不存在")
            current = _document_identity(current_source)
            expected = {
                "document_version": stale_source.get("document_version"),
                "consumer_surface_digest": stale_source.get("consumer_surface_digest"),
            }
            actual = {
                "document_version": supplied.get("document_version"),
                "consumer_surface_digest": supplied.get("consumer_surface_digest"),
            }
            if isinstance(actual["document_version"], bool) or not isinstance(actual["document_version"], int) or not _is_digest(actual["consumer_surface_digest"]):
                raise ProjectStoreError("stale_provenance_invalid", "上游文档版本或消费面摘要格式无效")
            if expected != current or actual != current:
                raise ProjectStoreError("stale_provenance_mismatch", "上游文档版本或消费面摘要不匹配")
            normalized[source_name] = {**current, "consumed_at": consumed_at}
        document["consumed_inputs"] = normalized
        document.update(stale=False, stale_reason="", stale_sources=[])
    def list_projects(self) -> list[dict[str, Any]]: return [_public(p) for p in sorted(self._load()["projects"], key=lambda x: x.get("updated_at", ""), reverse=True)]
    def get_project(self, project_id: str) -> dict[str, Any]: return _public(self._find(self._load(), project_id))
    def create_project(self, *, title: str, platform: str = "未指定", local_workspace: str | None = None, account: str = "") -> dict[str, Any]:
        title = str(title or "").strip()
        if not title: raise ProjectStoreError("title_required", "项目名称不能为空")
        if len(title) > 120: raise ProjectStoreError("title_too_long", "项目名称不能超过 120 个字符")
        local_path = ""; label = "尚未连接本地素材"
        if local_workspace:
            path = Path(local_workspace).expanduser().resolve()
            if not path.is_dir(): raise ProjectStoreError("workspace_not_found", "本地素材目录不存在")
            local_path, label = str(path), path.name
        now = _now(); project = {"schema_version": PROJECT_SCHEMA_VERSION, "id": f"{_slug(title)}-{secrets.token_hex(5)}", "title": title, "platform": str(platform or "未指定")[:40], "account": str(account or "")[:80], "status": "planning", "revision": 1, "created_at": now, "updated_at": now, "local_workspace": {"workspace_id": "workspace-" + secrets.token_hex(8), "label": label, "local_path": local_path, "path_digest": _digest(local_path) if local_path else None}, "references": [], "documents": {n: _document(n) for n in DOCUMENT_NAMES}, "delivery": {"state": "not_started", "stale": False, "stale_reason": "", "stale_sources": [], "consumed_inputs": {}, "artifacts": []}, "publishing": {"state": "not_published", "published_at": None, "links": [], "metrics": {}}, "publishing_history": [], "analysis": {"state": "not_started", "tier": "metadata", "transcript_state": "not_started", "preview_state": "not_started"}, "audit": [{"id": "audit-" + secrets.token_hex(8), "at": now, "actor": "user", "action": "project_created", "detail": {"platform": str(platform or "未指定")[:40]}}]}
        with self._transaction() as data:
            data["projects"].append(project)
        return _public(project)

    def update_project(self, project_id: str, changes: dict[str, Any], *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision); applied = {}
            for key, value in changes.items():
                if key not in {"title", "platform", "account", "status"}: raise ProjectStoreError("field_not_editable", f"字段不可编辑：{key}")
                text = str(value or "").strip()
                if key == "title" and not text: raise ProjectStoreError("title_required", "项目名称不能为空")
                applied[key] = text[:120 if key == "title" else 80]; project[key] = applied[key]
            self._touch(project, actor, "project_updated", applied)
        return _public(project)

    def connect_workspace(self, project_id: str, local_workspace: str, *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        path = Path(local_workspace).expanduser().resolve()
        if not path.is_dir(): raise ProjectStoreError("workspace_not_found", "本地素材目录不存在")
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision)
            project["local_workspace"] = {"workspace_id": project.get("local_workspace", {}).get("workspace_id") or "workspace-" + secrets.token_hex(8), "label": path.name, "local_path": str(path), "path_digest": _digest(str(path))}; project["analysis"]["state"] = "not_started"
            self._touch(project, actor, "workspace_connected", {"label": path.name})
        return _public(project)
    def local_workspace_path(self, project_id: str) -> Path:
        project = self._find(self._load(), project_id); value = str((project.get("local_workspace") or {}).get("local_path") or "")
        path = Path(value).expanduser().resolve() if value else None
        if path is None: raise ProjectStoreError("workspace_not_connected", "尚未连接本地素材目录")
        if not path.is_dir(): raise ProjectStoreError("workspace_not_found", "已连接的本地素材目录不可用")
        return path
    def patch_document(self, project_id: str, document_name: str, replacements: dict[str, str], *, selected_block_ids: list[str], consumed_upstream: dict[str, dict[str, Any]] | None = None, expected_revision: int | None = None, actor: str = "user", reason: str = "manual_patch") -> dict[str, Any]:
        if document_name not in DOCUMENT_NAMES: raise ProjectStoreError("document_invalid", "文档类型无效")
        if not isinstance(selected_block_ids, list) or not selected_block_ids or any(not isinstance(value, str) or not value for value in selected_block_ids) or len(set(selected_block_ids)) != len(selected_block_ids): raise ProjectStoreError("selection_invalid", "必须选择至少一个且不重复的区块")
        if not isinstance(replacements, dict): raise ProjectStoreError("patch_contract_invalid", "替换内容必须是对象")
        if set(replacements) != set(selected_block_ids): raise ProjectStoreError("patch_contract_invalid", "替换内容必须与选中区块完全一致")
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision); doc = project["documents"][document_name]; by_id = {b["id"]: b for b in doc["blocks"]}
            unknown = [i for i in selected_block_ids if i not in by_id]
            if unknown: raise ProjectStoreError("block_not_found", "区块不存在：" + "、".join(unknown))
            locked = [i for i in selected_block_ids if by_id[i].get("locked")]
            if locked: raise ProjectStoreError("block_locked", "区块已锁定：" + "、".join(locked))
            self._consume_stale_inputs(project, document_name, consumed_upstream)
            for block_id in selected_block_ids:
                body = str(replacements[block_id]).strip()
                if len(body) > 50_000: raise ProjectStoreError("block_too_large", "单个区块不能超过 50,000 字符")
                by_id[block_id]["body"] = body
            doc["version"] += 1
            doc["state"] = "draft"
            doc["history"].append(_history(doc["version"], doc["blocks"], reason, actor))
            _refresh_authority_bridge(document_name, doc)
            self._invalidate(project, document_name)
            self._touch(project, actor, "document_patched", {"document": document_name, "blocks": selected_block_ids, "version": doc["version"], "reason": reason})
        return _public(project)

    def set_block_lock(self, project_id: str, document_name: str, block_id: str, locked: bool, *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        if document_name not in DOCUMENT_NAMES: raise ProjectStoreError("document_invalid", "文档类型无效")
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision)
            try: block = next(b for b in project["documents"][document_name]["blocks"] if b["id"] == block_id)
            except StopIteration: raise ProjectStoreError("block_not_found", "区块不存在")
            block["locked"] = bool(locked); self._touch(project, actor, "block_locked" if locked else "block_unlocked", {"document": document_name, "block_id": block_id})
        return _public(project)
    def document_diff(self, project_id: str, document_name: str, from_version: int, to_version: int) -> str:
        project = self._find(self._load(), project_id); doc = project["documents"].get(document_name)
        if doc is None: raise ProjectStoreError("document_invalid", "文档类型无效")
        versions = {int(v["version"]): v for v in doc["history"]}
        if from_version not in versions or to_version not in versions: raise ProjectStoreError("version_not_found", "版本不存在")
        return "".join(difflib.unified_diff(_text(versions[from_version]["blocks"]).splitlines(True), _text(versions[to_version]["blocks"]).splitlines(True), fromfile=f"{document_name}@v{from_version}", tofile=f"{document_name}@v{to_version}"))
    def rollback_document(self, project_id: str, document_name: str, target_version: int, *, consumed_upstream: dict[str, dict[str, Any]] | None = None, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision); doc = project["documents"].get(document_name)
            if doc is None: raise ProjectStoreError("document_invalid", "文档类型无效")
            target = next((v for v in doc["history"] if int(v["version"]) == int(target_version)), None)
            if target is None: raise ProjectStoreError("version_not_found", "回滚目标版本不存在")
            self._consume_stale_inputs(project, document_name, consumed_upstream)
            doc["blocks"] = copy.deepcopy(target["blocks"]); doc["version"] += 1; doc["state"] = "draft"; doc["history"].append(_history(doc["version"], doc["blocks"], f"rollback_from_v{target_version}", actor)); _refresh_authority_bridge(document_name, doc); self._invalidate(project, document_name)
            self._touch(project, actor, "document_rolled_back", {"document": document_name, "target_version": target_version, "new_version": doc["version"]})
        return _public(project)

    def add_reference(self, project_id: str, *, title: str, url: str, platform: str, note: str = "", expected_revision: int | None = None) -> dict[str, Any]:
        title, url = str(title or "").strip(), str(url or "").strip()
        if not title or not url or not url.startswith(("https://", "http://")): raise ProjectStoreError("reference_invalid", "参考素材需要标题和有效链接")
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision); project["references"].append({"id": "reference-" + secrets.token_hex(8), "asset_role": REFERENCE_ASSET_ROLE, "editing_eligible": False, "title": title[:160], "url": url[:2000], "platform": str(platform or "未指定")[:40], "note": str(note or "")[:2000], "created_at": _now()})
            self._touch(project, "user", "reference_added", {"title": title[:160]})
        return _public(project)

    def reject_known_reference_ids(self, project_id: str, asset_ids: list[str]) -> list[str]:
        if not isinstance(asset_ids, list) or any(not isinstance(value, str) or not value for value in asset_ids) or len(set(asset_ids)) != len(asset_ids):
            raise ProjectStoreError("asset_ids_invalid", "资产 ID 必须是不重复的非空字符串")
        project = self._find(self._load(), project_id)
        reference_ids = {str(item.get("id")) for item in project.get("references", [])}
        rejected = [asset_id for asset_id in asset_ids if asset_id in reference_ids]
        if rejected:
            raise ProjectStoreError("reference_asset_forbidden", "reference 资产不能进入可剪候选：" + "、".join(rejected))
        return list(asset_ids)

    def record_document_bridge_export(self, project_id: str, document_name: str, *, source_document_version: int, source_consumer_surface_digest: str, target_content_digest: str, expected_revision: int | None = None, actor: str = "system") -> dict[str, Any]:
        if document_name not in AUTHORITY_BRIDGE_TARGETS:
            raise ProjectStoreError("bridge_document_invalid", "只有 Brief 和脚本需要项目包输入桥接")
        if isinstance(source_document_version, bool) or not isinstance(source_document_version, int) or not _is_digest(source_consumer_surface_digest):
            raise ProjectStoreError("bridge_source_invalid", "桥接源版本或消费面摘要格式无效")
        if not _is_digest(target_content_digest):
            raise ProjectStoreError("bridge_target_digest_invalid", "桥接目标内容摘要无效")
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision)
            document = project["documents"][document_name]
            current = _document_identity(document)
            supplied = {"document_version": source_document_version, "consumer_surface_digest": source_consumer_surface_digest}
            if supplied != current:
                raise ProjectStoreError("bridge_source_conflict", "Brief/脚本桥接源版本或消费面摘要已过期")
            bridge = document["authority_bridge"]
            bridge.update(
                exported_source_document_version=current["document_version"],
                exported_source_consumer_surface_digest=current["consumer_surface_digest"],
                target_content_digest=target_content_digest,
                exported_at=_now(),
                export_state="current",
            )
            self._touch(project, actor, "document_bridge_exported", {"document": document_name, "document_version": current["document_version"], "source_consumer_surface_digest": current["consumer_surface_digest"], "target_content_digest": target_content_digest})
        return _public(project)

    @staticmethod
    def _publishing_payload(value: dict[str, Any]) -> dict[str, Any]:
        allowed = {"publishedAt", "links", "metrics", "reviewConclusion", "nextConstraint"}
        unknown = set(value) - allowed
        if unknown:
            raise ProjectStoreError("publishing_field_invalid", "发布记录包含不可编辑字段")

        published_at = str(value.get("publishedAt") or "").strip()
        if published_at:
            try:
                parsed_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ProjectStoreError("published_at_invalid", "发布时间格式无效") from exc
            if parsed_at.tzinfo is None:
                raise ProjectStoreError("published_at_invalid", "发布时间必须包含时区")
            published_at = parsed_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        raw_links = value.get("links", [])
        if not isinstance(raw_links, list) or len(raw_links) > MAX_PUBLIC_LINKS:
            raise ProjectStoreError("publishing_links_invalid", "公开链接数量无效")
        links: list[str] = []
        for raw_link in raw_links:
            link = str(raw_link or "").strip()
            parsed_link = urllib.parse.urlsplit(link)
            if parsed_link.scheme not in {"https", "http"} or not parsed_link.hostname or parsed_link.username or parsed_link.password or len(link) > 2_000:
                raise ProjectStoreError("publishing_link_invalid", "发布链接必须是有效公开链接")
            if link not in links:
                links.append(link)

        raw_metrics = value.get("metrics", {})
        if not isinstance(raw_metrics, dict) or set(raw_metrics) - set(PUBLISHING_METRICS):
            raise ProjectStoreError("publishing_metrics_invalid", "指标字段无效")
        metrics: dict[str, int] = {}
        for name, raw_metric in raw_metrics.items():
            if isinstance(raw_metric, bool):
                raise ProjectStoreError("publishing_metric_invalid", "指标必须是非负整数")
            try:
                metric = int(raw_metric)
            except (TypeError, ValueError) as exc:
                raise ProjectStoreError("publishing_metric_invalid", "指标必须是非负整数") from exc
            if metric < 0 or metric > 2_000_000_000:
                raise ProjectStoreError("publishing_metric_invalid", "指标超出允许范围")
            metrics[name] = metric

        review_conclusion = str(value.get("reviewConclusion") or "").strip()
        next_constraint = str(value.get("nextConstraint") or "").strip()
        if len(review_conclusion) > 4_000 or len(next_constraint) > 2_000:
            raise ProjectStoreError("publishing_review_too_long", "复盘内容超出长度限制")
        if LOCAL_ABSOLUTE_PATH.search(review_conclusion) or LOCAL_ABSOLUTE_PATH.search(next_constraint):
            raise ProjectStoreError("publishing_review_private", "复盘内容不能包含本地绝对路径")
        if not (published_at or links or metrics or review_conclusion or next_constraint):
            raise ProjectStoreError("publishing_empty", "请至少填写一项发布或复盘信息")
        return {
            "state": "published" if (published_at or links) else "reviewed",
            "published_at": published_at or None,
            "links": links,
            "metrics": metrics,
            "review_conclusion": review_conclusion,
            "next_constraint": next_constraint,
            "reviewed_at": _now(),
        }

    def record_publishing(self, project_id: str, value: dict[str, Any], *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ProjectStoreError("publishing_invalid", "发布记录必须是对象")
        publishing = self._publishing_payload(value)
        with self._transaction() as data:
            project = self._find(data, project_id); self._revision(project, expected_revision)
            history = project.setdefault("publishing_history", [])
            snapshot_core = {
                **copy.deepcopy(publishing),
                "snapshot_version": len(history) + 1,
                "project_revision": int(project["revision"]) + 1,
                "account": str(project.get("account") or "").strip(),
                "platform": str(project.get("platform") or "").strip(),
            }
            canonical = json.dumps(snapshot_core, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            snapshot = {
                **snapshot_core,
                "snapshot_id": "publishing-" + secrets.token_hex(8),
                "snapshot_digest": _digest(canonical),
            }
            history.append(copy.deepcopy(snapshot))
            project["publishing"] = {
                **copy.deepcopy(publishing),
                "snapshot_id": snapshot["snapshot_id"],
                "snapshot_version": snapshot["snapshot_version"],
                "snapshot_digest": snapshot["snapshot_digest"],
            }
            audit_detail = {
                "snapshot_id": snapshot["snapshot_id"],
                "snapshot_version": snapshot["snapshot_version"],
                "snapshot_digest": snapshot["snapshot_digest"],
                "has_published_at": bool(publishing["published_at"]),
                "link_count": len(publishing["links"]),
                "metric_fields": sorted(publishing["metrics"]),
                "has_review_conclusion": bool(publishing["review_conclusion"]),
                "has_next_constraint": bool(publishing["next_constraint"]),
            }
            self._touch(project, actor, "publishing_recorded", audit_detail)
        return _public(project)

    def account_review_context(self, project_id: str) -> list[dict[str, str]]:
        data = self._load(); current = self._find(data, project_id)
        account = str(current.get("account") or "").strip()
        platform = str(current.get("platform") or "").strip()
        if not account:
            return []
        context: list[dict[str, str]] = []
        for project in data["projects"]:
            if project.get("id") == current["id"]:
                continue
            snapshots = project.get("publishing_history") or []
            if not snapshots:
                legacy = project.get("publishing") or {}
                snapshots = [{**legacy, "account": str(project.get("account") or "").strip(), "platform": str(project.get("platform") or "").strip(), "snapshot_id": "", "snapshot_digest": ""}]
            for snapshot in snapshots:
                if str(snapshot.get("account") or "").strip() != account or str(snapshot.get("platform") or "").strip() != platform:
                    continue
                conclusion = str(snapshot.get("review_conclusion") or "").strip()
                constraint = str(snapshot.get("next_constraint") or "").strip()
                if conclusion or constraint:
                    context.append({
                        "review_conclusion": conclusion,
                        "next_constraint": constraint,
                        "snapshot_id": str(snapshot.get("snapshot_id") or ""),
                        "snapshot_digest": str(snapshot.get("snapshot_digest") or ""),
                        "project_id": str(project.get("id") or ""),
                        "recorded_at": str(snapshot.get("reviewed_at") or ""),
                    })
        context.sort(key=lambda item: (item["recorded_at"], item["snapshot_id"]), reverse=True)
        return context[:12]
