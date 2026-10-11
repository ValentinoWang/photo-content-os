#!/usr/bin/env python3
"""Move an Inbox batch into its formal project and remove the Inbox copy."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from media_common import ANALYSIS_DIR, MEDIA_EXTS, now_iso, safe_slug, write_json_atomic
from project_bootstrap_common import ensure_formal_project_for_batch
from runtime_paths import workspace_root as _shared_workspace_root


WORKSPACE_ROOT = _shared_workspace_root(Path(__file__))

BATCH_NOTE_NAME = "00_批次说明.md"
LOCAL_LINK_DIR = "_openclaw"
PROJECT_INBOX_DIR = "00_Inbox_待分类"
PROMOTED_ANALYSIS_ROOT = f"{ANALYSIS_DIR}/promoted_inbox_batches"
PROMOTED_LINK_ROOT = "_openclaw/promoted_inbox_batches"
NON_MEDIA_DIR = "_随批次非素材"
PROMOTION_RECORD_DIR = "_openclaw/promotion_records"
PROMOTION_RECORD_SUFFIX = ".promotion.json"
PROMOTION_JOURNAL_SUFFIX = ".promotion.journal.json"
PROMOTION_JOURNAL_VERSION = "openclaw_inbox_promotion_journal_v0.1"

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


def path_exists(path: Path) -> bool:
    """Return true for regular paths and broken symlinks."""

    return os.path.lexists(path)


def json_temp_path(path: Path) -> Path:
    return path.with_suffix(f"{path.suffix}.tmp")


def write_json_cleanly(path: Path, data: Any) -> None:
    """Use the shared atomic writer without leaving its fixed temp file on failure."""

    temporary = json_temp_path(path)
    try:
        write_json_atomic(path, data)
    except Exception as exc:
        try:
            if path_exists(temporary) and not temporary.is_dir():
                temporary.unlink()
        except OSError as cleanup_exc:
            raise PromoteError(
                f"atomic JSON write failed for {path}: {exc}; temp cleanup failed: {cleanup_exc}"
            ) from exc
        raise


def write_text_atomic(path: Path, text: str) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except Exception as exc:
        try:
            if path_exists(temporary) and not temporary.is_dir():
                temporary.unlink()
        except OSError as cleanup_exc:
            raise PromoteError(
                f"atomic text write failed for {path}: {exc}; temp cleanup failed: {cleanup_exc}"
            ) from exc
        raise


def read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromoteError(f"cannot read {label}: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PromoteError(f"{label} root must be an object: {path}")
    return data


def assert_project_dir(project_dir: Path, workspace_root: Path) -> None:
    project_root = (workspace_root / "01_Project_Workspace").resolve()
    try:
        project_dir.resolve().relative_to(project_root)
    except ValueError as exc:
        raise PromoteError(f"formal project must stay under 01_Project_Workspace: {project_dir}") from exc
    if not project_dir.is_dir():
        raise PromoteError(f"formal project does not exist: {project_dir}")


def assert_target_inside_project(target: Path, project_dir: Path) -> None:
    try:
        target.parent.resolve().relative_to(project_dir.resolve())
    except ValueError as exc:
        raise PromoteError(f"promotion target escapes formal project: {target}") from exc


def move_path(source: Path, target: Path) -> Path:
    if not path_exists(source):
        raise PromoteError(f"promotion source disappeared before move: {source}")
    if path_exists(target):
        raise PromoteError(f"promotion target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    if path_exists(source) or not path_exists(target):
        raise PromoteError(f"move did not reach its exact target: {source} -> {target}")
    return target


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


def build_move_plan(batch_dir: Path, project_dir: Path, batch_slug: str) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    archive_root = project_dir / PROMOTED_ANALYSIS_ROOT / batch_slug / "generated_scaffold_from_inbox"
    for source in sorted(batch_dir.iterdir(), key=lambda path: path.name):
        if source.name in IGNORED_NAMES:
            continue
        if source.name in GENERATED_PROJECT_DIRS or source.name in GENERATED_PROJECT_FILES:
            target = archive_root / source.name
            kind = "archived_scaffold"
        else:
            target = top_level_item_target(source, batch_dir, project_dir, batch_slug)
            if target is None:
                raise PromoteError(f"unclassified promotion source: {source}")
            kind = "moved"
        plan.append(
            {
                "source": str(source),
                "target": str(target),
                "kind": kind,
                "status": "pending",
            }
        )

    # Parent targets must be materialized before another operation writes below them.
    plan.sort(key=lambda item: (len(Path(item["target"]).parts), item["target"], item["source"]))
    return plan


def validate_move_plan(
    plan: list[dict[str, str]],
    *,
    project_dir: Path,
    record_path: Path,
    journal_path: Path,
) -> None:
    collisions: list[str] = []
    seen_targets: dict[Path, Path] = {}

    for operation in plan:
        source = Path(operation["source"])
        target = Path(operation["target"])
        if not path_exists(source):
            collisions.append(f"source is missing: {source}")
        try:
            assert_target_inside_project(target, project_dir)
        except PromoteError as exc:
            collisions.append(str(exc))
        if path_exists(target):
            collisions.append(f"target already exists: {target}")
        target_key = target.absolute()
        if target_key in seen_targets:
            collisions.append(f"duplicate target for {seen_targets[target_key]} and {source}: {target}")
        else:
            seen_targets[target_key] = source

        ancestor = target.parent
        while ancestor != project_dir and ancestor != ancestor.parent:
            if path_exists(ancestor) and not ancestor.is_dir():
                collisions.append(f"target ancestor is not a directory: {ancestor}")
                break
            ancestor = ancestor.parent

    for parent_operation in plan:
        parent_target = Path(parent_operation["target"])
        parent_source = Path(parent_operation["source"])
        for child_operation in plan:
            if child_operation is parent_operation:
                continue
            child_target = Path(child_operation["target"])
            try:
                child_relative = child_target.relative_to(parent_target)
            except ValueError:
                continue
            if not child_relative.parts:
                continue
            if not parent_source.is_dir() or parent_source.is_symlink():
                collisions.append(f"planned parent target cannot contain another target: {parent_target}")
                continue
            nested_source_path = parent_source / child_relative
            if path_exists(nested_source_path):
                collisions.append(
                    f"planned nested target collides with content already in {parent_source}: {child_target}"
                )
                continue
            nested_parent = nested_source_path.parent
            while nested_parent != parent_source:
                if path_exists(nested_parent) and not nested_parent.is_dir():
                    collisions.append(f"planned nested target has a non-directory ancestor: {nested_parent}")
                    break
                nested_parent = nested_parent.parent

    for output in (record_path, journal_path):
        try:
            assert_target_inside_project(output, project_dir)
        except PromoteError as exc:
            collisions.append(str(exc))
        if path_exists(output):
            collisions.append(f"transaction output already exists: {output}")

    if collisions:
        detail = "\n".join(f"- {item}" for item in sorted(set(collisions)))
        raise PromoteError(f"promotion preflight collision validation failed:\n{detail}")


def missing_parent_dirs(paths: list[Path], project_dir: Path) -> list[str]:
    missing: set[Path] = set()
    for path in paths:
        parent = path.parent
        while parent != project_dir and parent != parent.parent:
            if not path_exists(parent):
                missing.add(parent)
            parent = parent.parent
    return [str(path) for path in sorted(missing, key=lambda item: (len(item.parts), str(item)))]


def promotion_paths(project_dir: Path, batch_slug: str) -> tuple[Path, Path]:
    record_dir = project_dir / PROMOTION_RECORD_DIR
    return (
        record_dir / f"{batch_slug}{PROMOTION_RECORD_SUFFIX}",
        record_dir / f"{batch_slug}{PROMOTION_JOURNAL_SUFFIX}",
    )


def write_promotion_record(
    project_dir: Path,
    *,
    batch_dir: Path,
    moved: list[dict[str, str]],
    archived_scaffold: list[str],
    bootstrap: dict[str, Any],
) -> Path:
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
    output, _journal_path = promotion_paths(project_dir, safe_slug(batch_dir.name, 80))
    if path_exists(output):
        raise PromoteError(f"promotion record already exists: {output}")
    write_json_cleanly(output, record)
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
    write_text_atomic(log_path, "\n".join(lines).rstrip() + "\n")


def persist_journal(journal: dict[str, Any]) -> None:
    journal_path = Path(str(journal["journal_path"]))
    write_json_cleanly(journal_path, journal)


def unlink_file(path: Path, errors: list[str], label: str) -> None:
    try:
        if not path_exists(path):
            return
        if path.is_dir() and not path.is_symlink():
            errors.append(f"{label} is unexpectedly a directory: {path}")
            return
        path.unlink()
    except OSError as exc:
        errors.append(f"cannot remove {label} {path}: {exc}")


def rollback_transaction(journal: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    journal_path = Path(str(journal["journal_path"]))
    record_path = Path(str(journal["promotion_record"]))
    log_path = Path(str(journal["project_log"]))

    journal["status"] = "rolling_back"
    try:
        if path_exists(journal_path):
            persist_journal(journal)
    except Exception:
        # The on-disk journal remains useful even if this progress update fails.
        pass

    log_before = journal.get("project_log_before")
    if log_before is None:
        unlink_file(log_path, errors, "new project log")
    elif isinstance(log_before, str):
        try:
            write_text_atomic(log_path, log_before)
        except Exception as exc:
            errors.append(f"cannot restore project log {log_path}: {exc}")
    else:
        errors.append("journal project_log_before must be a string or null")
    unlink_file(log_path.with_suffix(f"{log_path.suffix}.tmp"), errors, "project log temp file")

    unlink_file(record_path, errors, "promotion record")
    unlink_file(json_temp_path(record_path), errors, "promotion record temp file")

    operations = journal.get("operations")
    if not isinstance(operations, list):
        errors.append("journal operations must be a list")
        operations = []
    for operation in reversed(operations):
        if not isinstance(operation, dict):
            errors.append("journal operation must be an object")
            continue
        source_value = operation.get("source")
        target_value = operation.get("target")
        if not isinstance(source_value, str) or not isinstance(target_value, str):
            errors.append("journal operation paths must be strings")
            continue
        source = Path(source_value)
        target = Path(target_value)
        source_exists = path_exists(source)
        target_exists = path_exists(target)
        if source_exists and not target_exists:
            operation["status"] = "rolled_back"
            continue
        if source_exists and target_exists:
            errors.append(f"rollback collision; source and target both exist: {source} | {target}")
            continue
        if not source_exists and not target_exists:
            errors.append(f"rollback cannot find source or target: {source} | {target}")
            continue
        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(source))
            if not path_exists(source) or path_exists(target):
                raise PromoteError(f"rollback move did not restore exact source: {target} -> {source}")
            operation["status"] = "rolled_back"
        except Exception as exc:
            errors.append(f"cannot roll back {target} -> {source}: {exc}")

    if errors:
        journal["status"] = "rollback_failed"
        journal["rollback_errors"] = errors
        try:
            persist_journal(journal)
        except Exception:
            pass
        return errors

    journal["status"] = "rolled_back"
    try:
        persist_journal(journal)
    except Exception:
        pass
    unlink_file(journal_path, errors, "promotion journal")
    unlink_file(json_temp_path(journal_path), errors, "promotion journal temp file")

    for raw_path in sorted(
        journal.get("created_parent_dirs", []),
        key=lambda item: (len(Path(str(item)).parts), str(item)),
        reverse=True,
    ):
        directory = Path(str(raw_path))
        if not path_exists(directory):
            continue
        if not directory.is_dir() or directory.is_symlink():
            errors.append(f"created parent is no longer an ordinary directory: {directory}")
            continue
        try:
            directory.rmdir()
        except OSError:
            # A non-empty directory may contain pre-existing or concurrent project state.
            try:
                if not any(directory.iterdir()):
                    errors.append(f"cannot remove empty transaction directory: {directory}")
            except OSError as exc:
                errors.append(f"cannot inspect transaction directory {directory}: {exc}")
    return errors


def discover_artifact(
    workspace_root: Path,
    *,
    batch_dir: Path,
    suffix: str,
    label: str,
) -> tuple[Path, dict[str, Any]] | None:
    project_root = workspace_root / "01_Project_Workspace"
    if not project_root.is_dir():
        return None
    filename = f"{safe_slug(batch_dir.name, 80)}{suffix}"
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(project_root.rglob(filename)):
        data = read_json_object(path, label)
        if data.get("source_batch_path") == str(batch_dir):
            matches.append((path, data))
    if len(matches) > 1:
        paths = ", ".join(str(path) for path, _data in matches)
        raise PromoteError(f"multiple {label} files match source batch {batch_dir}: {paths}")
    return matches[0] if matches else None


def finalize_source_batch(batch_dir: Path) -> bool:
    if not batch_dir.is_dir():
        return not path_exists(batch_dir)
    for name in sorted(IGNORED_NAMES):
        path = batch_dir / name
        try:
            if path_exists(path) and (not path.is_dir() or path.is_symlink()):
                path.unlink()
        except OSError:
            return False
    try:
        batch_dir.rmdir()
    except OSError:
        return False
    return True


def result_from_completed_record(
    record_path: Path,
    record: dict[str, Any],
    *,
    batch_dir: Path,
    workspace_root: Path,
) -> dict[str, Any]:
    if record.get("spec_version") != "openclaw_inbox_promotion_v0.1":
        raise PromoteError(f"unsupported promotion record version: {record_path}")
    if record.get("doc_type") != "openclaw_inbox_promotion" or record.get("status") != "promoted":
        raise PromoteError(f"promotion record is not completed: {record_path}")
    if record.get("source_batch_path") != str(batch_dir):
        raise PromoteError(f"promotion record source does not match retry: {record_path}")

    project_value = record.get("local_project_path")
    if not isinstance(project_value, str):
        raise PromoteError(f"promotion record local_project_path must be a string: {record_path}")
    project_dir = Path(project_value).expanduser().resolve()
    assert_project_dir(project_dir, workspace_root)
    if record.get("project_inbox_path") != str(project_dir / PROJECT_INBOX_DIR):
        raise PromoteError(f"promotion record project_inbox_path is invalid: {record_path}")
    expected_record, _journal_path = promotion_paths(project_dir, safe_slug(batch_dir.name, 80))
    if record_path.resolve() != expected_record.resolve():
        raise PromoteError(f"promotion record is outside its expected project location: {record_path}")

    moved = record.get("moved")
    if not isinstance(moved, list):
        raise PromoteError(f"promotion record moved must be a list: {record_path}")
    validated_moved: list[dict[str, str]] = []
    targets: set[str] = set()
    for item in moved:
        if not isinstance(item, dict) or not isinstance(item.get("from"), str) or not isinstance(item.get("to"), str):
            raise PromoteError(f"promotion record contains an invalid move: {record_path}")
        source = Path(item["from"])
        target = Path(item["to"])
        if source.parent != batch_dir:
            raise PromoteError(f"promotion record source is outside the batch: {source}")
        assert_target_inside_project(target, project_dir)
        if path_exists(source) or not path_exists(target):
            raise PromoteError(f"completed promotion move does not match disk state: {source} -> {target}")
        if str(target) in targets:
            raise PromoteError(f"promotion record repeats a target: {target}")
        targets.add(str(target))
        validated_moved.append({"from": str(source), "to": str(target)})

    archived = record.get("archived_generated_scaffold")
    if not isinstance(archived, list) or not all(isinstance(item, str) for item in archived):
        raise PromoteError(f"promotion record archived_generated_scaffold must be a string list: {record_path}")
    for target_value in archived:
        target = Path(target_value)
        assert_target_inside_project(target, project_dir)
        if target.name not in GENERATED_PROJECT_DIRS | GENERATED_PROJECT_FILES:
            raise PromoteError(f"promotion record has an unknown scaffold archive: {target}")
        source = batch_dir / target.name
        if path_exists(source) or not path_exists(target):
            raise PromoteError(f"completed scaffold archive does not match disk state: {source} -> {target}")
        if str(target) in targets:
            raise PromoteError(f"promotion record repeats a target: {target}")
        targets.add(str(target))

    if path_exists(batch_dir) and not batch_dir.is_dir():
        raise PromoteError(f"completed promotion source path is no longer a directory: {batch_dir}")
    if batch_dir.is_dir():
        leftovers = [path for path in batch_dir.iterdir() if path.name not in IGNORED_NAMES]
        if leftovers:
            names = ", ".join(str(path) for path in sorted(leftovers))
            raise PromoteError(f"completed promotion retry found unrecorded batch content: {names}")

    log_path = project_dir / "素材整理记录.md"
    try:
        log_text = log_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromoteError(f"completed promotion is missing its project log: {log_path}: {exc}") from exc
    if f"- 迁移记录：{record_path}" not in log_text:
        raise PromoteError(f"project log does not reference completed promotion record: {record_path}")

    batch_removed = finalize_source_batch(batch_dir)
    return {
        "spec_version": "openclaw_inbox_promotion_v0.1",
        "status": "promoted",
        "source_batch_path": str(batch_dir),
        "source_batch_removed": batch_removed,
        "local_project_path": str(project_dir),
        "project_inbox_path": str(project_dir / PROJECT_INBOX_DIR),
        "promotion_record": str(record_path),
        "moved_count": len(validated_moved),
        "moved": validated_moved,
        "archived_generated_scaffold": list(archived),
    }


def validate_recovery_journal(
    journal: dict[str, Any],
    *,
    journal_path: Path,
    batch_dir: Path,
    project_dir: Path,
) -> None:
    allowed_statuses = {
        "prepared",
        "moving",
        "writing_record",
        "record_written",
        "writing_log",
        "log_written",
        "committed",
        "rolling_back",
        "rollback_failed",
        "rolled_back",
    }
    if journal.get("doc_type") != "openclaw_inbox_promotion_journal":
        raise PromoteError(f"promotion journal doc_type is invalid: {journal_path}")
    if journal.get("source_batch_path") != str(batch_dir):
        raise PromoteError(f"promotion journal source does not match retry: {journal_path}")
    if journal.get("status") not in allowed_statuses:
        raise PromoteError(f"promotion journal status is invalid: {journal_path}")
    if not isinstance(journal.get("project_log_before"), (str, type(None))):
        raise PromoteError(f"promotion journal project_log_before is invalid: {journal_path}")

    operations = journal.get("operations")
    if not isinstance(operations, list):
        raise PromoteError(f"promotion journal operations must be a list: {journal_path}")
    seen_sources: set[str] = set()
    seen_targets: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise PromoteError(f"promotion journal operation must be an object: {journal_path}")
        source_value = operation.get("source")
        target_value = operation.get("target")
        if not isinstance(source_value, str) or not isinstance(target_value, str):
            raise PromoteError(f"promotion journal operation paths must be strings: {journal_path}")
        source = Path(source_value)
        target = Path(target_value)
        if source.parent != batch_dir:
            raise PromoteError(f"promotion journal source is outside the batch: {source}")
        assert_target_inside_project(target, project_dir)
        if operation.get("kind") not in {"moved", "archived_scaffold"}:
            raise PromoteError(f"promotion journal operation kind is invalid: {journal_path}")
        if operation.get("status") not in {"pending", "moving", "moved", "rolled_back"}:
            raise PromoteError(f"promotion journal operation status is invalid: {journal_path}")
        if source_value in seen_sources or target_value in seen_targets:
            raise PromoteError(f"promotion journal repeats a source or target: {journal_path}")
        seen_sources.add(source_value)
        seen_targets.add(target_value)

    created_parent_dirs = journal.get("created_parent_dirs")
    if not isinstance(created_parent_dirs, list) or not all(
        isinstance(item, str) for item in created_parent_dirs
    ):
        raise PromoteError(f"promotion journal created_parent_dirs must be a string list: {journal_path}")
    for value in created_parent_dirs:
        directory = Path(value)
        try:
            directory.absolute().relative_to(project_dir.absolute())
        except ValueError as exc:
            raise PromoteError(f"promotion journal cleanup path escapes the project: {directory}") from exc
        if directory == project_dir:
            raise PromoteError(f"promotion journal cannot remove the project root: {journal_path}")


def recover_matching_journal(batch_dir: Path, workspace_root: Path) -> dict[str, Any] | None:
    discovered = discover_artifact(
        workspace_root,
        batch_dir=batch_dir,
        suffix=PROMOTION_JOURNAL_SUFFIX,
        label="promotion journal",
    )
    if discovered is None:
        return None
    journal_path, journal = discovered
    if journal.get("spec_version") != PROMOTION_JOURNAL_VERSION:
        raise PromoteError(f"unsupported promotion journal version: {journal_path}")
    if journal.get("journal_path") != str(journal_path):
        raise PromoteError(f"promotion journal path does not match its location: {journal_path}")

    project_value = journal.get("local_project_path")
    if not isinstance(project_value, str):
        raise PromoteError(f"promotion journal local_project_path must be a string: {journal_path}")
    project_dir = Path(project_value).expanduser().resolve()
    assert_project_dir(project_dir, workspace_root)
    expected_record, expected_journal = promotion_paths(project_dir, safe_slug(batch_dir.name, 80))
    if journal_path.resolve() != expected_journal.resolve():
        raise PromoteError(f"promotion journal is outside its expected project location: {journal_path}")
    if journal.get("promotion_record") != str(expected_record):
        raise PromoteError(f"promotion journal record path is invalid: {journal_path}")
    if journal.get("project_log") != str(project_dir / "素材整理记录.md"):
        raise PromoteError(f"promotion journal project log path is invalid: {journal_path}")
    validate_recovery_journal(
        journal,
        journal_path=journal_path,
        batch_dir=batch_dir,
        project_dir=project_dir,
    )

    if journal.get("status") == "committed":
        record = read_json_object(expected_record, "promotion record")
        result = result_from_completed_record(
            expected_record,
            record,
            batch_dir=batch_dir,
            workspace_root=workspace_root,
        )
        try:
            journal_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise PromoteError(f"completed promotion journal cannot be removed: {journal_path}: {exc}") from exc
        return result

    rollback_errors = rollback_transaction(journal)
    if rollback_errors:
        detail = "; ".join(rollback_errors)
        raise PromoteError(f"incomplete promotion rollback failed for {journal_path}: {detail}")
    return None


def promote_batch(batch_dir: Path, workspace_root: Path) -> dict[str, Any]:
    batch_dir = batch_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    assert_inbox_batch(batch_dir, workspace_root)

    recovered_result = recover_matching_journal(batch_dir, workspace_root)
    if recovered_result is not None:
        return recovered_result

    completed = discover_artifact(
        workspace_root,
        batch_dir=batch_dir,
        suffix=PROMOTION_RECORD_SUFFIX,
        label="promotion record",
    )
    if completed is not None:
        record_path, record = completed
        return result_from_completed_record(
            record_path,
            record,
            batch_dir=batch_dir,
            workspace_root=workspace_root,
        )

    if not batch_dir.exists() or not batch_dir.is_dir():
        raise PromoteError(f"batch_dir does not exist and has no completed promotion record: {batch_dir}")

    project_dir, bootstrap = resolve_project_dir(batch_dir, workspace_root)
    project_dir = project_dir.expanduser().resolve()
    assert_project_dir(project_dir, workspace_root)
    batch_slug = safe_slug(batch_dir.name, 80)
    record_path, journal_path = promotion_paths(project_dir, batch_slug)
    log_path = project_dir / "素材整理记录.md"
    plan = build_move_plan(batch_dir, project_dir, batch_slug)
    validate_move_plan(
        plan,
        project_dir=project_dir,
        record_path=record_path,
        journal_path=journal_path,
    )
    assert_target_inside_project(log_path, project_dir)
    if log_path.is_symlink():
        raise PromoteError(f"project log cannot be a symlink during promotion: {log_path}")

    try:
        log_before: str | None = log_path.read_text(encoding="utf-8") if path_exists(log_path) else None
    except OSError as exc:
        raise PromoteError(f"cannot capture project log before promotion: {log_path}: {exc}") from exc
    created_parent_dirs = missing_parent_dirs(
        [Path(operation["target"]) for operation in plan] + [record_path, journal_path, log_path],
        project_dir,
    )
    journal: dict[str, Any] = {
        "spec_version": PROMOTION_JOURNAL_VERSION,
        "doc_type": "openclaw_inbox_promotion_journal",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "status": "prepared",
        "source_batch_path": str(batch_dir),
        "local_project_path": str(project_dir),
        "promotion_record": str(record_path),
        "journal_path": str(journal_path),
        "project_log": str(log_path),
        "project_log_before": log_before,
        "created_parent_dirs": created_parent_dirs,
        "operations": plan,
        "bootstrap": bootstrap,
    }

    try:
        persist_journal(journal)
        journal["status"] = "moving"
        journal["updated_at"] = now_iso()
        persist_journal(journal)
        for operation in plan:
            operation["status"] = "moving"
            journal["updated_at"] = now_iso()
            persist_journal(journal)
            move_path(Path(operation["source"]), Path(operation["target"]))
            operation["status"] = "moved"
            journal["updated_at"] = now_iso()
            persist_journal(journal)

        moved = [
            {"from": operation["source"], "to": operation["target"]}
            for operation in plan
            if operation["kind"] == "moved"
        ]
        archived_scaffold = [
            operation["target"] for operation in plan if operation["kind"] == "archived_scaffold"
        ]
        journal["status"] = "writing_record"
        journal["updated_at"] = now_iso()
        persist_journal(journal)
        actual_record = write_promotion_record(
            project_dir,
            batch_dir=batch_dir,
            moved=moved,
            archived_scaffold=archived_scaffold,
            bootstrap=bootstrap,
        )
        if actual_record != record_path or not record_path.is_file():
            raise PromoteError(f"promotion record was not written to its exact path: {record_path}")
        journal["status"] = "record_written"
        journal["updated_at"] = now_iso()
        persist_journal(journal)

        journal["status"] = "writing_log"
        journal["updated_at"] = now_iso()
        persist_journal(journal)
        append_project_log(project_dir, batch_dir, moved, record_path)
        journal["status"] = "log_written"
        journal["updated_at"] = now_iso()
        persist_journal(journal)

        journal["status"] = "committed"
        journal["updated_at"] = now_iso()
        persist_journal(journal)
    except Exception as exc:
        rollback_errors = rollback_transaction(journal)
        if rollback_errors:
            detail = "; ".join(rollback_errors)
            raise PromoteError(f"promotion failed: {exc}; rollback incomplete: {detail}") from exc
        raise PromoteError(f"promotion failed and was rolled back: {exc}") from exc

    batch_removed = finalize_source_batch(batch_dir)
    try:
        journal_path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise PromoteError(f"promotion committed but journal cleanup failed: {journal_path}: {exc}") from exc

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
