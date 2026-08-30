#!/usr/bin/env python3
"""Move an Inbox batch into its formal project and remove the Inbox copy."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from media_common import MEDIA_EXTS, now_iso, relative_posix, safe_slug
from project_bootstrap_common import ensure_formal_project_for_batch


SCRIPT_DIR = Path(__file__).resolve().parent
SYSTEM_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = SYSTEM_ROOT.parent if SYSTEM_ROOT.name == "99_System_OpenClaw" else SYSTEM_ROOT

BATCH_NOTE_NAME = "00_批次说明.md"
LOCAL_LINK_DIR = "_openclaw"
PROJECT_LINK_NAME = "project.json"
ANALYSIS_DIR = "_ai_analysis"
PROJECT_INBOX_DIR = "00_Inbox_待分类"
PROMOTED_ANALYSIS_ROOT = "_ai_analysis/promoted_inbox_batches"
PROMOTED_LINK_ROOT = "_openclaw/promoted_inbox_batches"
NON_MEDIA_DIR = "_随批次非素材"

GENERATED_PROJECT_DIRS = {
    "80_To_iCloudPhotos_精选入库",
    "90_Draft_Project",
    "91_Output",
    "92_Aliyun_SyncReady",
    "待增加",
}

GENERATED_PROJECT_FILES = {
    "aliyun_sync_manifest.md",
}

IGNORED_NAMES = {
    ".DS_Store",
}


class PromoteError(Exception):
    """Raised when an Inbox batch cannot be promoted safely."""


def workspace_inbox_root(workspace_root: Path) -> Path:
    return workspace_root / "00_Inbox_Mac_Intake"


def assert_inbox_batch(batch_dir: Path, workspace_root: Path) -> None:
    inbox_root = workspace_inbox_root(workspace_root).resolve()
    try:
        batch_dir.resolve().relative_to(inbox_root)
    except ValueError as exc:
        raise PromoteError(f"batch_dir must stay under 00_Inbox_Mac_Intake: {batch_dir}") from exc


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for index in range(2, 1000):
        candidate = parent / f"{stem}_{index:02d}{suffix}"
        if not candidate.exists():
            return candidate
    raise PromoteError(f"too many duplicate paths near: {path}")


def move_path(source: Path, target: Path) -> Path:
    target = unique_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    return target


def load_project_link(batch_dir: Path) -> dict[str, Any]:
    link_path = batch_dir / LOCAL_LINK_DIR / PROJECT_LINK_NAME
    if not link_path.exists():
        return {}
    data = json.loads(link_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def resolve_project_dir(batch_dir: Path, workspace_root: Path) -> tuple[Path, dict[str, Any]]:
    bootstrap = ensure_formal_project_for_batch(batch_dir, workspace_root=workspace_root)
    project_dir = Path(str(bootstrap["local_project_path"])).expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        raise PromoteError(f"formal project was not created: {project_dir}")
    return project_dir, bootstrap


def has_media(path: Path) -> bool:
    if path.is_file():
        return path.suffix.lower() in MEDIA_EXTS
    return any(child.is_file() and child.suffix.lower() in MEDIA_EXTS for child in path.rglob("*"))


def top_level_item_target(source: Path, batch_dir: Path, project_dir: Path, batch_slug: str) -> Path | None:
    rel = source.relative_to(batch_dir)
    first = rel.parts[0]
    if first in IGNORED_NAMES:
        return None
    if first in GENERATED_PROJECT_DIRS:
        return None
    if first == ANALYSIS_DIR:
        return project_dir / PROMOTED_ANALYSIS_ROOT / batch_slug
    if first == LOCAL_LINK_DIR:
        return project_dir / PROMOTED_LINK_ROOT / batch_slug
    if rel.as_posix() == BATCH_NOTE_NAME:
        return project_dir / PROJECT_INBOX_DIR / BATCH_NOTE_NAME
    if source.is_file() and source.suffix.lower() in MEDIA_EXTS:
        return project_dir / PROJECT_INBOX_DIR / rel
    if source.is_dir() and has_media(source):
        return project_dir / PROJECT_INBOX_DIR / rel
    if source.is_file() and first in GENERATED_PROJECT_FILES:
        return None
    return project_dir / PROJECT_INBOX_DIR / NON_MEDIA_DIR / rel


def archive_generated_scaffold(batch_dir: Path, project_dir: Path, batch_slug: str) -> list[str]:
    archived: list[str] = []
    archive_root = project_dir / PROMOTED_ANALYSIS_ROOT / batch_slug / "generated_scaffold_from_inbox"
    for name in GENERATED_PROJECT_DIRS:
        path = batch_dir / name
        if path.exists():
            actual = move_path(path, archive_root / name)
            archived.append(str(actual))
    for name in GENERATED_PROJECT_FILES:
        path = batch_dir / name
        if path.exists():
            actual = move_path(path, archive_root / name)
            archived.append(str(actual))
    for name in IGNORED_NAMES:
        path = batch_dir / name
        if path.exists() and path.is_file():
            path.unlink()
    return archived


def write_promotion_record(
    project_dir: Path,
    *,
    batch_dir: Path,
    moved: list[dict[str, str]],
    archived_scaffold: list[str],
    bootstrap: dict[str, Any],
) -> Path:
    record_dir = project_dir / "_openclaw" / "promotion_records"
    record_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "spec_version": "openclaw_inbox_promotion_v0.1",
        "doc_type": "openclaw_inbox_promotion",
        "created_at": now_iso(),
        "owner_agent": "mac_openclaw",
        "status": "promoted",
        "source_batch_path": str(batch_dir),
        "local_project_path": str(project_dir),
        "project_inbox_path": str(project_dir / PROJECT_INBOX_DIR),
        "moved": moved,
        "archived_generated_scaffold": archived_scaffold,
        "bootstrap": bootstrap,
    }
    output = record_dir / f"{safe_slug(batch_dir.name, 80)}.promotion.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def append_project_log(project_dir: Path, batch_dir: Path, moved: list[dict[str, str]], record_path: Path) -> None:
    log_path = project_dir / "素材整理记录.md"
    lines: list[str] = []
    if log_path.exists():
        lines.append(log_path.read_text(encoding="utf-8").rstrip())
        lines.append("")
    else:
        lines.extend(["# 素材整理记录", ""])
    lines.extend(
        [
            f"## Inbox 批次迁移 {now_iso()}",
            "",
            f"- 来源批次：{batch_dir}",
            f"- 迁移记录：{record_path}",
            f"- 移动条目：{len(moved)}",
            "",
            "| 原位置 | 新位置 |",
            "| --- | --- |",
        ]
    )
    for item in moved:
        lines.append(f"| {item['from']} | {item['to']} |")
    log_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def promote_batch(batch_dir: Path, workspace_root: Path) -> dict[str, Any]:
    batch_dir = batch_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    if not batch_dir.exists() or not batch_dir.is_dir():
        raise PromoteError(f"batch_dir does not exist: {batch_dir}")
    assert_inbox_batch(batch_dir, workspace_root)

    project_dir, bootstrap = resolve_project_dir(batch_dir, workspace_root)
    batch_slug = safe_slug(batch_dir.name, 80)
    moved: list[dict[str, str]] = []

    for source in sorted(batch_dir.iterdir(), key=lambda path: path.name):
        target = top_level_item_target(source, batch_dir, project_dir, batch_slug)
        if target is None:
            continue
        actual = move_path(source, target)
        moved.append({"from": str(source), "to": str(actual)})

    archived_scaffold = archive_generated_scaffold(batch_dir, project_dir, batch_slug)
    leftovers = [path for path in sorted(batch_dir.iterdir(), key=lambda p: p.name) if path.name not in IGNORED_NAMES]
    if leftovers:
        non_media_root = project_dir / PROJECT_INBOX_DIR / NON_MEDIA_DIR / batch_slug
        for source in leftovers:
            actual = move_path(source, non_media_root / source.name)
            moved.append({"from": str(source), "to": str(actual)})

    try:
        batch_dir.rmdir()
        batch_removed = True
    except OSError:
        batch_removed = False

    record_path = write_promotion_record(
        project_dir,
        batch_dir=batch_dir,
        moved=moved,
        archived_scaffold=archived_scaffold,
        bootstrap=bootstrap,
    )
    append_project_log(project_dir, batch_dir, moved, record_path)

    return {
        "spec_version": "openclaw_inbox_promotion_v0.1",
        "status": "promoted",
        "source_batch_path": str(batch_dir),
        "source_batch_removed": batch_removed,
        "local_project_path": str(project_dir),
        "project_inbox_path": str(project_dir / PROJECT_INBOX_DIR),
        "promotion_record": str(record_path),
        "moved_count": len(moved),
        "moved": moved,
        "archived_generated_scaffold": archived_scaffold,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_dir", type=Path, help="00_Inbox_Mac_Intake 下的事件批次目录")
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT, help="本地素材根目录")
    args = parser.parse_args()

    result = promote_batch(args.batch_dir, args.workspace_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
