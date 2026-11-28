#!/usr/bin/env python3
"""Ensure a project has the standard workflow directories from the local media flow outline."""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import json
from pathlib import Path

from media import ANALYSIS_DIR, MEDIA_EXTS, now_iso, path_inside as inside, project_path, relative_posix


if __package__ and "." in __package__:
    from ..constants import (
        PROJECT_DIRS,
        WORKCACHE_DIRS,
        PLACEHOLDER_FILES,
        PROTECTED_TOP_LEVEL_DIRS,
    )
else:
    import sys as _sys
    from pathlib import Path as _Path
    _sdir = str(_Path(__file__).resolve().parents[1])
    if _sdir not in _sys.path:
        _sys.path.insert(0, _sdir)
    from constants import (
        PROJECT_DIRS,
        WORKCACHE_DIRS,
        PLACEHOLDER_FILES,
        PROTECTED_TOP_LEVEL_DIRS,
    )





def workcache_root_for_project(project: Path) -> Path:
    return project / "work-cache"


def is_inbox_batch_path(project: Path) -> bool:
    return any(parent.name == "inbox" for parent in [project, *project.parents])


def ensure_structure(project: Path) -> tuple[list[Path], list[Path], list[Path], Path]:
    created_dirs: list[Path] = []
    created_workcache_dirs: list[Path] = []
    created_files: list[Path] = []
    workcache_root = workcache_root_for_project(project)

    for relative in PROJECT_DIRS:
        path = project / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(path)
        elif not path.is_dir():
            raise NotADirectoryError(f"expected directory but found file: {path}")

    for relative in WORKCACHE_DIRS:
        path = workcache_root / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_workcache_dirs.append(path)
        elif not path.is_dir():
            raise NotADirectoryError(f"expected directory but found file: {path}")

    for relative, content in PLACEHOLDER_FILES.items():
        path = project / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created_files.append(path)
        elif not path.is_file():
            raise IsADirectoryError(f"expected file but found directory: {path}")

    return created_dirs, created_workcache_dirs, created_files, workcache_root


def load_l3_plan(project: Path, plan_path: str) -> dict[str, object]:
    path = Path(plan_path).expanduser()
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"L3 structure plan not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        plan = json.load(f)
    if not isinstance(plan, dict):
        raise ValueError(f"invalid L3 structure plan: {path}")
    plan_project = plan.get("project_dir")
    if plan_project and Path(str(plan_project)).expanduser().resolve() != project.resolve():
        raise RuntimeError("plan project_dir does not match the provided project_dir")
    return plan


def ensure_plan_folder(project: Path, relative: str) -> Path:
    path = (project / relative).resolve()
    if not inside(path, project):
        raise RuntimeError(f"folder escapes project_dir: {relative}")
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f"expected directory but found file: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def plan_moves(plan: dict[str, object]) -> list[dict[str, object]]:
    moves = plan.get("moves")
    if not isinstance(moves, list):
        raise ValueError("L3 structure plan must contain a moves list")
    return [move for move in moves if isinstance(move, dict)]


def append_l3_structure_log(project: Path, moved: list[dict[str, object]], plan: dict[str, object]) -> None:
    if not moved:
        return
    log_path = project / "material-organization.md"
    lines: list[str] = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 素材整理记录", ""])
    lines.extend(
        [
            f"## L3 结构计划执行记录 {now_iso()}",
            "",
            f"- 计划来源：{plan.get('source', 'LLM/人工全局结构分析')}",
            f"- 计划说明：{plan.get('rationale', '')}",
            "",
            "| 原位置 | 新位置 | 依据 |",
            "| --- | --- | --- |",
        ]
    )
    for move in moved:
        lines.append(f"| {move['from']} | {move['to']} | {move.get('reason', '')} |")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def apply_l3_plan(project: Path, plan: dict[str, object]) -> list[dict[str, object]]:
    folders = plan.get("folders", [])
    if not isinstance(folders, list):
        raise ValueError("L3 structure plan folders must be a list")
    for folder in folders:
        if isinstance(folder, str):
            ensure_plan_folder(project, folder)
        elif isinstance(folder, dict) and isinstance(folder.get("path"), str):
            ensure_plan_folder(project, str(folder["path"]))
        else:
            raise ValueError(f"invalid folder entry in L3 structure plan: {folder!r}")

    moved: list[dict[str, object]] = []
    planned_targets: set[str] = set()
    for move in plan_moves(plan):
        source_rel = str(move.get("from", ""))
        target_rel = str(move.get("to", ""))
        if not source_rel or not target_rel:
            raise ValueError(f"invalid move entry in L3 structure plan: {move!r}")

        source = (project / source_rel).resolve()
        target = (project / target_rel).resolve()
        if not inside(source, project):
            raise RuntimeError(f"source escapes project_dir: {source_rel}")
        if not inside(target, project):
            raise RuntimeError(f"target escapes project_dir: {target_rel}")
        if not source.exists():
            raise FileNotFoundError(f"source file not found: {source}")
        if not source.is_file():
            raise IsADirectoryError(f"source is not a file: {source}")
        if source.suffix.lower() not in MEDIA_EXTS:
            raise RuntimeError(f"source is not a supported media/metadata file: {source.name}")
        if str(target) in planned_targets:
            raise RuntimeError(f"duplicate target in L3 structure plan: {target_rel}")
        planned_targets.add(str(target))
        if source == target:
            continue
        if target.exists():
            raise FileExistsError(f"target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        moved.append(
            {
                "from": source_rel,
                "to": relative_posix(target, project),
                "reason": move.get("reason", ""),
            }
        )
    append_l3_structure_log(project, moved, plan)
    return moved


def main() -> None:
    parser = argparse.ArgumentParser(description="补齐项目标准工作流目录")
    parser.add_argument("project_dir", help="项目目录")
    parser.add_argument("--apply-l3-plan", help="执行由 LLM/人工全局分析确认的 L3 结构计划 JSON")
    args = parser.parse_args()

    project = project_path(args.project_dir)
    if is_inbox_batch_path(project):
        raise SystemExit(
            "error: ensure_project_structure.py 只能用于 projects 下的正式项目，"
            "不能直接作用于 inbox 批次。\n"
            f"请先运行：python3 {Path(__file__).resolve().parent / 'intake/ensure_project_from_inbox_batch.py'} \"{project}\""
        )
    created_dirs, created_workcache_dirs, created_files, workcache_root = ensure_structure(project)
    print(f"项目结构检查完成：{project}")
    print(f"新建项目目录：{len(created_dirs)} 个")
    print(f"项目级 WorkCache：{workcache_root}")
    print(f"新建 WorkCache 目录：{len(created_workcache_dirs)} 个")
    print(f"新建文件：{len(created_files)} 个")
    for path in created_dirs:
        print(f"dir  {path.relative_to(project)}")
    for path in created_workcache_dirs:
        print(f"workcache {path.relative_to(workcache_root)}")
    for path in created_files:
        print(f"file {path.relative_to(project)}")

    if args.apply_l3_plan:
        plan = load_l3_plan(project, args.apply_l3_plan)
        moved = apply_l3_plan(project, plan)
        print(f"已执行 L3 结构计划：{len(moved)} 个文件")
        for move in moved:
            print(f"move {move['from']} -> {move['to']}")


if __name__ == "__main__":
    main()
