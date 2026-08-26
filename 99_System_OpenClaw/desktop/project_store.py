#!/usr/bin/env python3
"""Versioned local CreativeProject store with block locks and safe projections."""
from __future__ import annotations

import copy, difflib, hashlib, json, os, re, secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "creative_project_store_v1"
PROJECT_SCHEMA_VERSION = "creative_project_v1"
DOCUMENT_NAMES = ("brief", "script", "storyboard", "edl")
DOCUMENT_LABELS = {"brief": "创作 Brief", "script": "脚本", "storyboard": "分镜", "edl": "剪辑方案"}
DOWNSTREAM = {"brief": ("script", "storyboard", "edl", "delivery"), "script": ("storyboard", "edl", "delivery"), "storyboard": ("edl", "delivery"), "edl": ("delivery",)}
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
DEFAULTS = {
    "brief": (("brief-goal", "创作目标"), ("brief-audience", "目标受众"), ("brief-angle", "核心角度"), ("brief-constraints", "平台与边界")),
    "script": (("script-hook", "开头钩子"), ("script-body", "主体推进"), ("script-ending", "结尾与行动")),
    "storyboard": (("storyboard-opening", "开场镜头"), ("storyboard-development", "展开镜头"), ("storyboard-ending", "收束镜头")),
    "edl": (("edl-plan", "剪辑顺序"), ("edl-captions", "字幕与声音"), ("edl-notes", "人工精剪提示")),
}

@dataclass(frozen=True)
class ProjectStoreError(ValueError):
    code: str
    message: str
    def __str__(self) -> str: return f"{self.code}: {self.message}"

def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _digest(value: str) -> str: return "sha256:" + hashlib.sha256(value.encode()).hexdigest()
def _slug(value: str) -> str: return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:28] or "project"
def _atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)
def _blocks(name: str) -> list[dict[str, Any]]: return [{"id": i, "title": t, "body": "", "locked": False} for i, t in DEFAULTS[name]]
def _history(version: int, blocks: list[dict[str, Any]], reason: str, actor: str) -> dict[str, Any]:
    snapshot = copy.deepcopy(blocks)
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"version": version, "created_at": _now(), "reason": reason, "actor": actor, "digest": _digest(canonical), "blocks": snapshot}
def _document(name: str) -> dict[str, Any]:
    blocks = _blocks(name)
    return {"name": name, "label": DOCUMENT_LABELS[name], "version": 1, "state": "draft", "stale": False, "stale_reason": "", "blocks": blocks, "history": [_history(1, blocks, "project_created", "system")]}
def _public(project: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(project); workspace = result.get("local_workspace") or {}
    result["local_workspace"] = {"workspace_id": workspace.get("workspace_id"), "label": workspace.get("label"), "path_digest": workspace.get("path_digest"), "connected": bool(workspace.get("local_path")), "kind": "local_directory", "privacy": "local_only"}
    return result
def _text(blocks: list[dict[str, Any]]) -> str: return "\n\n".join(f"## {b.get('title','')}\n\n{b.get('body','')}".rstrip() for b in blocks).rstrip() + "\n"

class ProjectStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir.expanduser().resolve(); self.path = self.state_dir / "creative-projects.json"
        if not self.path.exists(): _atomic(self.path, {"schema_version": SCHEMA_VERSION, "revision": 1, "projects": []})
        self._load()
    def _load(self) -> dict[str, Any]:
        try: data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ProjectStoreError("store_unavailable", "项目存储无法读取") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION or not isinstance(data.get("projects"), list): raise ProjectStoreError("store_schema_invalid", "项目存储版本或格式无效")
        return data
    def _save(self, data: dict[str, Any]) -> None: data["revision"] = int(data.get("revision", 0)) + 1; _atomic(self.path, data)
    @staticmethod
    def _find(data: dict[str, Any], project_id: str) -> dict[str, Any]:
        if not SAFE_ID.fullmatch(project_id): raise ProjectStoreError("project_id_invalid", "项目 ID 无效")
        for project in data["projects"]:
            if project.get("id") == project_id: return project
        raise ProjectStoreError("project_not_found", "项目不存在")
    @staticmethod
    def _revision(project: dict[str, Any], expected: int | None) -> None:
        if expected is not None and int(expected) != int(project.get("revision", 0)): raise ProjectStoreError("revision_conflict", "项目已被更新，请刷新后重试")
    @staticmethod
    def _touch(project: dict[str, Any], actor: str, action: str, detail: dict[str, Any]) -> None:
        project["revision"] = int(project.get("revision", 0)) + 1; project["updated_at"] = _now()
        project.setdefault("audit", []).append({"id": "audit-" + secrets.token_hex(8), "at": project["updated_at"], "actor": actor, "action": action, "detail": copy.deepcopy(detail)})
    @staticmethod
    def _invalidate(project: dict[str, Any], document: str) -> None:
        reason = f"{DOCUMENT_LABELS[document]} 已更新"
        for target in DOWNSTREAM[document]:
            if target == "delivery":
                project["delivery"]["stale"] = True
                if project["delivery"].get("state") != "not_started": project["delivery"]["state"] = "stale"
            else: project["documents"][target].update(stale=True, stale_reason=reason)
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
        now = _now(); project = {"schema_version": PROJECT_SCHEMA_VERSION, "id": f"{_slug(title)}-{secrets.token_hex(5)}", "title": title, "platform": str(platform or "未指定")[:40], "account": str(account or "")[:80], "status": "planning", "revision": 1, "created_at": now, "updated_at": now, "local_workspace": {"workspace_id": "workspace-" + secrets.token_hex(8), "label": label, "local_path": local_path, "path_digest": _digest(local_path) if local_path else None}, "references": [], "documents": {n: _document(n) for n in DOCUMENT_NAMES}, "delivery": {"state": "not_started", "stale": False, "artifacts": []}, "publishing": {"state": "not_published", "published_at": None, "links": [], "metrics": {}}, "analysis": {"state": "not_started", "tier": "metadata", "transcript_state": "not_started", "preview_state": "not_started"}, "audit": [{"id": "audit-" + secrets.token_hex(8), "at": now, "actor": "user", "action": "project_created", "detail": {"platform": str(platform or "未指定")[:40]}}]}
        data = self._load(); data["projects"].append(project); self._save(data); return _public(project)
    def update_project(self, project_id: str, changes: dict[str, Any], *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision); applied = {}
        for key, value in changes.items():
            if key not in {"title", "platform", "account", "status"}: raise ProjectStoreError("field_not_editable", f"字段不可编辑：{key}")
            text = str(value or "").strip()
            if key == "title" and not text: raise ProjectStoreError("title_required", "项目名称不能为空")
            applied[key] = text[:120 if key == "title" else 80]; project[key] = applied[key]
        self._touch(project, actor, "project_updated", applied); self._save(data); return _public(project)
    def connect_workspace(self, project_id: str, local_workspace: str, *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        path = Path(local_workspace).expanduser().resolve()
        if not path.is_dir(): raise ProjectStoreError("workspace_not_found", "本地素材目录不存在")
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision)
        project["local_workspace"] = {"workspace_id": project.get("local_workspace", {}).get("workspace_id") or "workspace-" + secrets.token_hex(8), "label": path.name, "local_path": str(path), "path_digest": _digest(str(path))}; project["analysis"]["state"] = "not_started"
        self._touch(project, actor, "workspace_connected", {"label": path.name}); self._save(data); return _public(project)
    def local_workspace_path(self, project_id: str) -> Path:
        project = self._find(self._load(), project_id); value = str((project.get("local_workspace") or {}).get("local_path") or "")
        path = Path(value).expanduser().resolve() if value else None
        if path is None: raise ProjectStoreError("workspace_not_connected", "尚未连接本地素材目录")
        if not path.is_dir(): raise ProjectStoreError("workspace_not_found", "已连接的本地素材目录不可用")
        return path
    def patch_document(self, project_id: str, document_name: str, replacements: dict[str, str], *, selected_block_ids: list[str], expected_revision: int | None = None, actor: str = "user", reason: str = "manual_patch") -> dict[str, Any]:
        if document_name not in DOCUMENT_NAMES: raise ProjectStoreError("document_invalid", "文档类型无效")
        if not selected_block_ids or len(set(selected_block_ids)) != len(selected_block_ids): raise ProjectStoreError("selection_invalid", "必须选择至少一个且不重复的区块")
        if set(replacements) != set(selected_block_ids): raise ProjectStoreError("patch_contract_invalid", "替换内容必须与选中区块完全一致")
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision); doc = project["documents"][document_name]; by_id = {b["id"]: b for b in doc["blocks"]}
        unknown = [i for i in selected_block_ids if i not in by_id]
        if unknown: raise ProjectStoreError("block_not_found", "区块不存在：" + "、".join(unknown))
        locked = [i for i in selected_block_ids if by_id[i].get("locked")]
        if locked: raise ProjectStoreError("block_locked", "区块已锁定：" + "、".join(locked))
        for block_id in selected_block_ids:
            body = str(replacements[block_id]).strip()
            if len(body) > 50_000: raise ProjectStoreError("block_too_large", "单个区块不能超过 50,000 字符")
            by_id[block_id]["body"] = body
        doc["version"] += 1; doc.update(state="draft", stale=False, stale_reason=""); doc["history"].append(_history(doc["version"], doc["blocks"], reason, actor)); self._invalidate(project, document_name)
        self._touch(project, actor, "document_patched", {"document": document_name, "blocks": selected_block_ids, "version": doc["version"], "reason": reason}); self._save(data); return _public(project)
    def set_block_lock(self, project_id: str, document_name: str, block_id: str, locked: bool, *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision)
        try: block = next(b for b in project["documents"][document_name]["blocks"] if b["id"] == block_id)
        except (KeyError, StopIteration): raise ProjectStoreError("block_not_found", "区块不存在")
        block["locked"] = bool(locked); self._touch(project, actor, "block_locked" if locked else "block_unlocked", {"document": document_name, "block_id": block_id}); self._save(data); return _public(project)
    def document_diff(self, project_id: str, document_name: str, from_version: int, to_version: int) -> str:
        project = self._find(self._load(), project_id); doc = project["documents"].get(document_name)
        if doc is None: raise ProjectStoreError("document_invalid", "文档类型无效")
        versions = {int(v["version"]): v for v in doc["history"]}
        if from_version not in versions or to_version not in versions: raise ProjectStoreError("version_not_found", "版本不存在")
        return "".join(difflib.unified_diff(_text(versions[from_version]["blocks"]).splitlines(True), _text(versions[to_version]["blocks"]).splitlines(True), fromfile=f"{document_name}@v{from_version}", tofile=f"{document_name}@v{to_version}"))
    def rollback_document(self, project_id: str, document_name: str, target_version: int, *, expected_revision: int | None = None, actor: str = "user") -> dict[str, Any]:
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision); doc = project["documents"].get(document_name)
        if doc is None: raise ProjectStoreError("document_invalid", "文档类型无效")
        target = next((v for v in doc["history"] if int(v["version"]) == int(target_version)), None)
        if target is None: raise ProjectStoreError("version_not_found", "回滚目标版本不存在")
        doc["blocks"] = copy.deepcopy(target["blocks"]); doc["version"] += 1; doc.update(state="draft", stale=False, stale_reason=""); doc["history"].append(_history(doc["version"], doc["blocks"], f"rollback_from_v{target_version}", actor)); self._invalidate(project, document_name)
        self._touch(project, actor, "document_rolled_back", {"document": document_name, "target_version": target_version, "new_version": doc["version"]}); self._save(data); return _public(project)
    def add_reference(self, project_id: str, *, title: str, url: str, platform: str, note: str = "", expected_revision: int | None = None) -> dict[str, Any]:
        title, url = str(title or "").strip(), str(url or "").strip()
        if not title or not url or not url.startswith(("https://", "http://")): raise ProjectStoreError("reference_invalid", "参考素材需要标题和有效链接")
        data = self._load(); project = self._find(data, project_id); self._revision(project, expected_revision); project["references"].append({"id": "reference-" + secrets.token_hex(8), "asset_role": "reference", "title": title[:160], "url": url[:2000], "platform": str(platform or "未指定")[:40], "note": str(note or "")[:2000], "created_at": _now()})
        self._touch(project, "user", "reference_added", {"title": title[:160]}); self._save(data); return _public(project)
