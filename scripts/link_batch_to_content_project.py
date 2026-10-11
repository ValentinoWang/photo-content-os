#!/usr/bin/env python3
"""Link a local intake batch to an Obsidian Content OS project package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from media_common import ANALYSIS_DIR, now_iso
from project_bootstrap_common import BATCH_NOTE_NAME as BATCH_NOTE
from project_bootstrap_common import count_media_files
from project_bootstrap_common import normalize_label
from project_bootstrap_common import parse_batch_note as _shared_parse_batch_note


from runtime_paths import obsidian_root
from runtime_paths import workspace_root as _shared_workspace_root

DEFAULT_OBSIDIAN_ROOT = obsidian_root()
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = _shared_workspace_root(Path(__file__))
LINK_RELATIVE_PATH = Path(ANALYSIS_DIR) / "content_os_link.yaml"

FIELD_TO_KEY = {
    "Obsidian 项目ID": "obsidian_project_id",
    "01_idea_card": "declared_idea_card",
    "02_project_brief": "declared_project_brief",
    "04_script": "declared_script",
    "task": "declared_task",
    "事件": "event",
    "地点": "location",
    "人物": "people",
    "时间范围": "time_range",
    "素材来源": "source",
    "本地素材批次": "local_batch",
    "目标项目": "target_project",
    "这批素材可能服务的内容": "possible_content",
    "必须保留 / 特别注意": "must_keep_or_attention",
    "不确定的地方": "uncertainties",
}

REQUIRED_PROJECT_FILES = {
    "idea_card": "01_idea_card.md",
    "project_brief": "02_project_brief.md",
    "script": "04_script.md",
}


class BatchLinkError(Exception):
    """Raised when a batch cannot be read safely."""


def workspace_root() -> Path:
    return WORKSPACE_ROOT.resolve()


def parse_batch_note(path: Path) -> dict[str, str]:
    return _shared_parse_batch_note(path, FIELD_TO_KEY)


def resolve_obsidian_path(raw: str, obsidian_root: Path) -> Path | None:
    value = raw.strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    parts = path.parts
    if parts and parts[0] == obsidian_root.name:
        path = Path(*parts[1:])
    return (obsidian_root / path).resolve()


def resolve_target_project(raw: str, root: Path) -> str:
    value = raw.strip()
    if not value:
        return ""
    path = Path(value).expanduser()
    if path.is_absolute():
        return str(path.resolve()) if path.exists() else ""
    direct = (root / path).resolve()
    if direct.exists():
        return str(direct)
    project_root = root / "01_Project_Workspace"
    if project_root.exists():
        matches = [candidate.resolve() for candidate in project_root.rglob(value) if candidate.is_dir()]
        unique = sorted({match for match in matches})
        if len(unique) == 1:
            return str(unique[0])
    return ""


def path_info(path: Path | None, *, required: bool = False, declared: str = "") -> dict[str, Any]:
    return {
        "declared": declared,
        "path": str(path) if path else "",
        "exists": bool(path and path.exists() and path.is_file() and path.stat().st_size > 0),
        "required": required,
    }


def build_link(batch_dir: Path, obsidian_root: Path, root: Path) -> dict[str, Any]:
    note = batch_dir / BATCH_NOTE
    if not note.exists() or not note.is_file():
        raise BatchLinkError(f"missing batch note: {note}")

    fields = parse_batch_note(note)
    project_id = fields["obsidian_project_id"].strip()
    project_package = obsidian_root / "08_内容项目" / project_id if project_id else None

    expected: dict[str, Path | None] = {}
    if project_package:
        for key, filename in REQUIRED_PROJECT_FILES.items():
            expected[key] = project_package / filename
    else:
        expected = {key: None for key in REQUIRED_PROJECT_FILES}

    declared = {
        "idea_card": resolve_obsidian_path(fields["declared_idea_card"], obsidian_root),
        "project_brief": resolve_obsidian_path(fields["declared_project_brief"], obsidian_root),
        "script": resolve_obsidian_path(fields["declared_script"], obsidian_root),
        "task": resolve_obsidian_path(fields["declared_task"], obsidian_root),
    }
    task_required = bool(fields["declared_task"].strip())

    files = {
        "idea_card": path_info(expected["idea_card"], required=True, declared=fields["declared_idea_card"]),
        "project_brief": path_info(expected["project_brief"], required=True, declared=fields["declared_project_brief"]),
        "script": path_info(expected["script"], required=True, declared=fields["declared_script"]),
        "task": path_info(declared["task"], required=task_required, declared=fields["declared_task"]),
    }

    missing_required = [name for name, info in files.items() if info["required"] and not info["exists"]]
    warnings: list[str] = []
    for key in ("idea_card", "project_brief", "script"):
        declared_path = declared[key]
        expected_path = expected[key]
        if declared_path and expected_path and declared_path != expected_path.resolve():
            warnings.append(f"declared_{key}_differs_from_project_id_default")

    status = "brief_ready" if project_id and not missing_required else "pending_cloud_brief"
    target_project_resolved = resolve_target_project(fields["target_project"], root)
    link_path = batch_dir / LINK_RELATIVE_PATH
    return {
        "spec_version": "content_os_batch_link_v0.1",
        "doc_type": "content_os_link",
        "created_at": now_iso(),
        "owner_agent": "mac_openclaw",
        "status": status,
        "batch": {
            "dir": str(batch_dir),
            "note": str(note),
            "media_file_count": count_media_files(batch_dir),
            "local_batch": fields["local_batch"] or batch_dir.name,
            "event": fields["event"],
            "location": fields["location"],
            "people": fields["people"],
            "time_range": fields["time_range"],
            "source": fields["source"],
            "target_project": fields["target_project"],
            "target_project_resolved": target_project_resolved,
            "possible_content": fields["possible_content"],
            "must_keep_or_attention": fields["must_keep_or_attention"],
            "uncertainties": fields["uncertainties"],
        },
        "obsidian": {
            "vault_root": str(obsidian_root),
            "project_id": project_id,
            "project_package": str(project_package) if project_package else "",
            "files": files,
        },
        "local_outputs": {
            "content_os_link": str(link_path),
        },
        "validation": {
            "project_id_present": bool(project_id),
            "project_package_exists": bool(project_package and project_package.exists() and project_package.is_dir()),
            "missing_required_files": missing_required,
            "warnings": warnings,
        },
        "state_flow": [
            "pending_cloud_brief",
            "brief_ready",
            "materials_analyzed",
            "materials_matched",
            "storyboard_ready",
        ],
        "next_actions": next_actions(status),
    }


def next_actions(status: str) -> list[str]:
    if status == "brief_ready":
        return [
            "确认或创建正式项目目录。",
            "运行 run_analyze_project.sh 生成 manifest / keyframes / summary。",
            "再执行 Mac Runner task，或用 brief/script 生成素材匹配和 Storyboard / EDL。",
        ]
    return [
        "让腾讯云 OpenClaw 先补齐 08_内容项目/{project_id}/01_idea_card.md、02_project_brief.md、04_script.md。",
        "项目包齐全后重新运行 31_link_batch_to_content_project.py。",
    ]


def write_link(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_dir", type=Path)
    parser.add_argument("--obsidian-root", type=Path, default=DEFAULT_OBSIDIAN_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=workspace_root())
    args = parser.parse_args()

    batch_dir = args.batch_dir.expanduser().resolve()
    if not batch_dir.exists() or not batch_dir.is_dir():
        raise SystemExit(f"error: batch_dir does not exist or is not a directory: {batch_dir}")
    obsidian_root = args.obsidian_root.expanduser().resolve()
    if not obsidian_root.exists() or not obsidian_root.is_dir():
        raise SystemExit(f"error: obsidian root does not exist: {obsidian_root}")
    root = args.workspace_root.expanduser().resolve()

    try:
        link = build_link(batch_dir, obsidian_root, root)
    except BatchLinkError as exc:
        raise SystemExit(f"error: {exc}") from exc

    output = batch_dir / LINK_RELATIVE_PATH
    write_link(output, link)
    print(f"content_os_link={output}")
    print(f"status={link['status']}")
    missing = link["validation"]["missing_required_files"]
    if missing:
        print("missing_required_files=" + ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
