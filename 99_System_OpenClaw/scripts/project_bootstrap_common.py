#!/usr/bin/env python3
"""Helpers for creating a formal project shell from a local Inbox batch."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

from media_common import now_iso, safe_slug


SCRIPT_DIR = Path(__file__).resolve().parent
BATCH_NOTE_NAME = "00_批次说明.md"
LOCAL_LINK_DIR = "_openclaw"
PROJECT_LINK_NAME = "project.json"

EMPTY_VALUES = {"", "无", "none", "null", "待定", "未定", "unknown"}

FIELD_ALIASES = {
    "事件": "event",
    "地点": "location",
    "人物": "people",
    "时间范围": "time_range",
    "素材来源": "source",
    "本地素材批次": "local_batch",
    "目标项目": "target_project",
    "是否已有正式项目目录": "has_formal_project",
    "这批素材可能服务的内容": "possible_content",
    "必须保留 / 特别注意": "must_keep_or_attention",
    "不确定的地方": "uncertainties",
}

PROJECT_FIELD_LABELS = {
    "local_batch": "本地素材批次",
    "target_project": "目标项目",
    "has_formal_project": "是否已有正式项目目录",
}

TITLE_REPLACEMENTS = {
    "清华大学深圳国际研究生院": "清华SIGS",
    "深圳国际研究生院": "SIGS",
}


class ProjectBootstrapError(Exception):
    """Raised when a formal project shell cannot be created safely."""


def ensure_structure_function():
    module_path = SCRIPT_DIR / "13_ensure_project_structure.py"
    spec = importlib.util.spec_from_file_location("openclaw_ensure_project_structure", module_path)
    if spec is None or spec.loader is None:
        raise ProjectBootstrapError(f"failed to load ensure project structure module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ensure_structure


def normalize_label(label: str) -> str:
    return " ".join(label.strip().strip("-").strip().split())


def split_note_field(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith(">"):
        return None
    if stripped.startswith("-"):
        stripped = stripped[1:].strip()
    for separator in ("：", ":"):
        if separator in stripped:
            label, value = stripped.split(separator, 1)
            label = normalize_label(label)
            if label in FIELD_ALIASES:
                return label, value.strip()
    return None


def read_batch_note_fields(note_path: Path) -> dict[str, str]:
    fields = {key: "" for key in FIELD_ALIASES.values()}
    if not note_path.exists() or not note_path.is_file():
        return fields
    for line in note_path.read_text(encoding="utf-8").splitlines():
        parsed = split_note_field(line)
        if not parsed:
            continue
        label, value = parsed
        fields[FIELD_ALIASES[label]] = value
    return fields


def is_empty_value(value: str) -> bool:
    return value.strip().lower() in EMPTY_VALUES


def strip_date_prefix(name: str) -> str:
    text = re.sub(r"^\d{8}[_ -]*", "", name.strip())
    text = re.sub(r"(?:_?待整理|_?待增加)$", "", text)
    return text.strip("_ -")


def clean_title(value: str, *, fallback: str = "内容项目") -> str:
    text = value.strip()
    text = re.sub(r"#([^\s#]+)", r"\1", text)
    text = re.sub(r"\b\d{4}年", "", text)
    text = re.sub(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b", "", text)
    for source, target in TITLE_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", text, flags=re.UNICODE).strip("._-")
    text = re.sub(r"_+", "_", text)
    return text or fallback


def date_token_from_fields(fields: dict[str, str], batch_dir: Path) -> str:
    candidates = [fields.get("time_range", ""), batch_dir.name]
    for value in candidates:
        match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
        if match:
            year, month, day = (int(part) for part in match.groups())
            return f"{year:04d}{month:02d}{day:02d}"
        match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", value)
        if match:
            year, month, day = (int(part) for part in match.groups())
            return f"{year:04d}{month:02d}{day:02d}"
        match = re.search(r"(\d{8})", value)
        if match:
            return match.group(1)
    return now_iso()[:10].replace("-", "")


def optional_task_text(task: dict[str, Any] | None, key: str) -> str:
    if not task:
        return ""
    value = task.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def project_workspace_root(workspace_root: Path) -> Path:
    return workspace_root / "01_Project_Workspace"


def inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def resolve_existing_project(raw: str, workspace_root: Path) -> Path | None:
    value = raw.strip()
    if is_empty_value(value):
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve() if path.exists() or inside(path, project_workspace_root(workspace_root)) else None
    direct = (workspace_root / path).resolve()
    if direct.exists() or inside(direct, project_workspace_root(workspace_root)):
        return direct
    project_root = project_workspace_root(workspace_root)
    if project_root.exists():
        matches = [candidate.resolve() for candidate in project_root.rglob(value) if candidate.is_dir()]
        unique = sorted({match for match in matches})
        if len(unique) == 1:
            return unique[0]
    return None


def declared_project_from_task(task: dict[str, Any] | None) -> str:
    if not task:
        return ""
    for key in ("local_project_path", "target_project", "project_path"):
        value = optional_task_text(task, key)
        if value:
            return value
    project = task.get("project")
    if isinstance(project, dict):
        for key in ("local_project_path", "target_project", "path"):
            value = project.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def generated_project_path(batch_dir: Path, fields: dict[str, str], task: dict[str, Any] | None, workspace_root: Path) -> Path:
    date_token = date_token_from_fields(fields, batch_dir)
    year = date_token[:4]
    batch_title = clean_title(strip_date_prefix(optional_task_text(task, "batch_id") or batch_dir.name), fallback="内容项目")
    theme_title = batch_title
    topic = optional_task_text(task, "topic")
    project_source = topic or fields.get("event") or batch_title
    project_title = clean_title(project_source, fallback=batch_title)
    theme_dir = safe_slug(f"{year}年{theme_title}内容创作", 80)
    project_dir = safe_slug(f"{date_token}_{project_title}", 96)
    return project_workspace_root(workspace_root) / theme_dir / project_dir


def replace_or_append_note_field(note_path: Path, label: str, value: str) -> bool:
    if not note_path.exists():
        return False
    lines = note_path.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, line in enumerate(lines):
        parsed = split_note_field(line)
        if parsed and parsed[0] == label:
            replacement = f"{label}：{value}"
            if line != replacement:
                lines[index] = replacement
                changed = True
            break
    else:
        lines.extend(["", f"{label}：{value}"])
        changed = True
    if changed:
        note_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return changed


def update_batch_note_project_fields(note_path: Path, batch_dir: Path, project_dir: Path) -> list[str]:
    changed: list[str] = []
    updates = {
        PROJECT_FIELD_LABELS["local_batch"]: str(batch_dir),
        PROJECT_FIELD_LABELS["target_project"]: str(project_dir),
        PROJECT_FIELD_LABELS["has_formal_project"]: "是",
    }
    for label, value in updates.items():
        if replace_or_append_note_field(note_path, label, value):
            changed.append(label)
    return changed


def write_project_readme(project_dir: Path, batch_dir: Path, fields: dict[str, str], task: dict[str, Any] | None) -> Path:
    readme = project_dir / "readme.md"
    if readme.exists() and readme.stat().st_size > 0:
        return readme
    topic = optional_task_text(task, "topic") or fields.get("event") or project_dir.name
    platform = optional_task_text(task, "platform") or "待定"
    content_type = optional_task_text(task, "content_type") or "待定"
    feishu = optional_task_text(task, "feishu_doc_link") or "无"
    readme.write_text(
        f"""# {project_dir.name}

## 项目定位

主题集合：{project_dir.parent.name}
项目ID：
Obsidian 项目路径：
腾讯云 task：{optional_task_text(task, "creation_run_id") or "无"}
飞书文档：{feishu}
剪辑目标：{topic}
发布平台：{platform}
预计成片：{content_type}

## 来源批次

- Inbox 批次：{batch_dir}
- 事件：{fields.get("event") or "待补"}
- 地点：{fields.get("location") or "待补"}
- 人物：{fields.get("people") or "待补"}
- 时间范围：{fields.get("time_range") or "待补"}

## 当前状态

- [ ] 素材已从 Inbox 合并进入项目 L3
- [ ] 已运行 `13_ensure_project_structure.py`
- [ ] 已运行 `run_analyze_project.sh`
- [ ] 已融合 Obsidian brief / script
- [ ] 已生成素材匹配 / Storyboard / EDL / native import pack
- [ ] 已进入剪映人工精剪
- [ ] 已导出 V1 / V2 / Final
- [ ] 已完成 local_output_review
- [ ] 已发布 / 入库 / 归档

## 关键判断

必须保留：
可删除候选：
需要修复 / 增强：
需要 HyperFrames：
需要补充素材：
""",
        encoding="utf-8",
    )
    return readme


def write_project_link(batch_dir: Path, project_dir: Path, *, created: bool, warnings: list[str]) -> Path:
    link_path = batch_dir / LOCAL_LINK_DIR / PROJECT_LINK_NAME
    link_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "spec_version": "openclaw_project_link_v0.1",
        "doc_type": "openclaw_local_project_link",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "owner_agent": "mac_openclaw",
        "status": "project_ready",
        "local_batch_path": str(batch_dir),
        "local_project_path": str(project_dir),
        "project_created_by_openclaw": created,
        "warnings": warnings,
    }
    link_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return link_path


def ensure_formal_project_for_batch(
    batch_dir: Path,
    *,
    task: dict[str, Any] | None = None,
    workspace_root: Path,
) -> dict[str, Any]:
    batch_dir = batch_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    note_path = batch_dir / BATCH_NOTE_NAME
    fields = read_batch_note_fields(note_path)
    warnings: list[str] = []

    declared = declared_project_from_task(task) or fields.get("target_project", "")
    project_dir = resolve_existing_project(declared, workspace_root)
    if project_dir is None:
        project_dir = generated_project_path(batch_dir, fields, task, workspace_root).resolve()
        warnings.append("auto_generated_local_project_path")
    elif not inside(project_dir, project_workspace_root(workspace_root)):
        raise ProjectBootstrapError(f"formal project must stay under 01_Project_Workspace: {project_dir}")

    existed_before = project_dir.exists()
    project_dir.mkdir(parents=True, exist_ok=True)
    ensure_structure = ensure_structure_function()
    created_dirs, created_workcache_dirs, created_files, workcache_root = ensure_structure(project_dir)
    readme = write_project_readme(project_dir, batch_dir, fields, task)
    changed_fields = update_batch_note_project_fields(note_path, batch_dir, project_dir) if note_path.exists() else []
    project_link = write_project_link(batch_dir, project_dir, created=not existed_before, warnings=warnings)

    return {
        "spec_version": "openclaw_project_bootstrap_v0.1",
        "status": "project_ready",
        "local_project_path": str(project_dir),
        "project_created": not existed_before,
        "project_readme": str(readme),
        "project_link": str(project_link),
        "workcache_root": str(workcache_root),
        "created_project_dirs": [str(path) for path in created_dirs],
        "created_workcache_dirs": [str(path) for path in created_workcache_dirs],
        "created_files": [str(path) for path in created_files],
        "updated_batch_note_fields": changed_fields,
        "warnings": warnings,
    }
