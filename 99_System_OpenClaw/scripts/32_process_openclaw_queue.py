#!/usr/bin/env python3
"""Process lightweight cloud-to-Mac OpenClaw queue tasks.

This queue is for control metadata only. It intentionally does not copy raw
media into synced folders or include raw media filenames in cloud results.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from media_common import file_sha256 as sha256_file, now_iso, safe_slug
from project_bootstrap_common import BATCH_NOTE_NAME, LOCAL_LINK_DIR, count_media_files, ensure_formal_project_for_batch
from queue_identity import VOLATILE_TASK_FIELDS, request_fingerprint


SCRIPT_DIR = Path(__file__).resolve().parent
from runtime_paths import obsidian_root, workspace_root as _shared_workspace_root

WORKSPACE_ROOT = _shared_workspace_root(Path(__file__))
DEFAULT_OBSIDIAN_ROOT = obsidian_root()

QUEUE_DIR_NAME = "_OpenClawQueue"
CLOUD_TO_MAC_DIR = "cloud_to_mac"
MAC_TO_CLOUD_DIR = "mac_to_cloud"
PROCESSED_DIR = "processed"
FAILED_DIR = "failed"

TASK_BIND_BATCH = "bind_creation_run_to_local_batch"
SUPPORTED_TASK_TYPES = {TASK_BIND_BATCH}
RESULT_SPEC_VERSION = "openclaw_queue_result_v0.1"
LINK_SPEC_VERSION = "openclaw_queue_link_v0.1"
STATUS_SPEC_VERSION = "openclaw_queue_status_v0.1"

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


class QueueError(Exception):
    """Raised when a queue task cannot be safely processed."""


def idempotency_key(task: dict[str, Any], creation_run_id: str) -> str:
    source = task.get("source_agent_task") if isinstance(task.get("source_agent_task"), dict) else {}
    value = (
        task.get("idempotency_key")
        or source.get("idempotency_key")
        or task.get("creation_run_id")
        or creation_run_id
    )
    if not isinstance(value, str) or not value.strip():
        raise QueueError("idempotency_key must be non-empty text")
    return value.strip()


def result_idempotency_key(task: dict[str, Any], creation_run_id: str) -> str:
    """Keep malformed tasks diagnosable while still writing a blocked result."""

    try:
        return idempotency_key(task, creation_run_id)
    except QueueError:
        return creation_run_id


def source_identity(task: dict[str, Any]) -> dict[str, Any]:
    source = task.get("source_agent_task") if isinstance(task.get("source_agent_task"), dict) else {}
    identity: dict[str, Any] = {}
    for key in (
        "task_id",
        "task_type",
        "project_id",
        "idea_id",
        "project_revision",
        "change_request_id",
        "editor_backend",
        "tenant_id",
    ):
        value = source.get(key) if key in source else task.get(key)
        if value is not None and value != "":
            identity[key] = value
    return identity


@dataclass(frozen=True)
class QueueConfig:
    workspace_root: Path
    queue_root: Path

    @property
    def cloud_to_mac(self) -> Path:
        return self.queue_root / CLOUD_TO_MAC_DIR

    @property
    def mac_to_cloud(self) -> Path:
        return self.queue_root / MAC_TO_CLOUD_DIR

    @property
    def processed(self) -> Path:
        return self.queue_root / PROCESSED_DIR

    @property
    def failed(self) -> Path:
        return self.queue_root / FAILED_DIR

    @property
    def inbox_root(self) -> Path:
        return self.workspace_root / "00_Inbox_Mac_Intake"


def ensure_queue_dirs(config: QueueConfig) -> None:
    for path in (config.cloud_to_mac, config.mac_to_cloud, config.processed, config.failed):
        path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def task_manifest_path(path: Path) -> Path:
    return path / "manifest.json" if path.is_dir() else path


def load_json(path: Path) -> dict[str, Any]:
    json_path = task_manifest_path(path)
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QueueError(f"invalid JSON: {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise QueueError(f"task JSON root must be an object: {json_path}")
    return data


def validate_creation_run_id(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QueueError("missing required field: creation_run_id")
    creation_run_id = value.strip()
    if not RUN_ID_PATTERN.match(creation_run_id):
        raise QueueError("creation_run_id contains unsafe characters or invalid length")
    return creation_run_id


def validate_task_type(task: dict[str, Any]) -> str:
    task_type = task.get("task_type")
    if task_type not in SUPPORTED_TASK_TYPES:
        expected = ", ".join(sorted(SUPPORTED_TASK_TYPES))
        raise QueueError(f"unsupported task_type: {task_type!r}; expected one of: {expected}")
    return str(task_type)


def optional_text(task: dict[str, Any], key: str) -> str:
    value = task.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise QueueError(f"{key} must be a string")
    return value.strip()


def requested_outputs(task: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw = task.get("requested_outputs", [])
    if raw is None:
        return [], []
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise QueueError("requested_outputs must be a list of non-empty strings")

    outputs: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for item in raw:
        value = item.strip()
        if value in seen:
            warnings.append(f"duplicated_requested_output:{value}")
            continue
        seen.add(value)
        outputs.append(value)
    return outputs, warnings


def local_batch_raw_value(task: dict[str, Any]) -> Any:
    raw = task.get("local_batch_path") or task.get("mac_local_batch_path_hint")
    if raw:
        return raw
    local_batch = task.get("local_batch")
    if isinstance(local_batch, dict):
        return local_batch.get("path") or local_batch.get("local_batch_path")
    return None


def has_local_batch_reference(task: dict[str, Any]) -> bool:
    return bool(local_batch_raw_value(task) or optional_text(task, "batch_id"))


def default_local_batch_path_from_batch_id(task: dict[str, Any], config: QueueConfig) -> Path | None:
    batch_id = optional_text(task, "batch_id")
    if not batch_id:
        return None
    batch_id_path = Path(batch_id)
    if batch_id_path.is_absolute() or ".." in batch_id_path.parts or len(batch_id_path.parts) != 1:
        raise QueueError("batch_id must be a single safe Inbox directory name when local_batch_path is omitted")
    return (config.inbox_root / batch_id).resolve()


def read_json_quiet(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def find_existing_linked_batch(task: dict[str, Any], config: QueueConfig, creation_run_id: str) -> Path | None:
    inbox_root = config.inbox_root.resolve()
    if not inbox_root.exists():
        return None

    exact_run_matches: list[Path] = []
    batch_id_matches: list[Path] = []
    wanted_batch_id = optional_text(task, "batch_id")
    for link_path in sorted(inbox_root.glob(f"*/{LOCAL_LINK_DIR}/link.json")):
        link = read_json_quiet(link_path)
        if not link:
            continue
        batch_dir = link_path.parents[1].resolve()
        try:
            batch_dir.relative_to(inbox_root)
        except ValueError:
            continue
        if link.get("creation_run_id") == creation_run_id:
            exact_run_matches.append(batch_dir)
        elif wanted_batch_id and link.get("batch_id") == wanted_batch_id:
            batch_id_matches.append(batch_dir)

    if len(exact_run_matches) == 1:
        return exact_run_matches[0]
    if len(exact_run_matches) > 1:
        raise QueueError(f"multiple local batches already linked to creation_run_id: {creation_run_id}")
    if len(batch_id_matches) == 1:
        return batch_id_matches[0]
    if len(batch_id_matches) > 1:
        raise QueueError(f"multiple local batches already linked to batch_id: {wanted_batch_id}")
    return None


def resolve_local_batch_path(task: dict[str, Any], config: QueueConfig, creation_run_id: str) -> tuple[Path, list[str]]:
    raw = local_batch_raw_value(task)
    warnings: list[str] = []

    if isinstance(raw, str) and raw.strip():
        path = Path(raw).expanduser()
        candidate = path if path.is_absolute() else config.workspace_root / path
    else:
        candidate = default_local_batch_path_from_batch_id(task, config)
        if candidate is None:
            raise QueueError("missing required field: local_batch_path, local_batch.path, or batch_id")
        warnings.append("local_batch_path_derived_from_batch_id")
    batch = candidate.resolve()
    inbox_root = config.inbox_root.resolve()
    try:
        batch.relative_to(inbox_root)
    except ValueError as exc:
        raise QueueError(f"local_batch_path must stay under 00_Inbox_Mac_Intake: {batch}") from exc
    if batch.exists() and not batch.is_dir():
        raise QueueError(f"local_batch_path is not a directory: {batch}")
    if batch.exists():
        return batch, warnings

    linked_batch = find_existing_linked_batch(task, config, creation_run_id)
    if linked_batch:
        return linked_batch, [*warnings, "local_batch_path_resolved_from_existing_link"]
    return batch, warnings


def cloud_prefill_block(task: dict[str, Any], batch_dir: Path) -> str:
    source_task = task.get("source_agent_task") if isinstance(task.get("source_agent_task"), dict) else {}
    task_id = str(source_task.get("task_id") or task.get("creation_run_id") or "")
    task_type = str(source_task.get("task_type") or task.get("task_type") or "")
    topic = optional_text(task, "topic") or optional_text(task, "batch_id") or batch_dir.name
    platform = optional_text(task, "platform")
    content_type = optional_text(task, "content_type")
    batch_id = optional_text(task, "batch_id") or batch_dir.name
    feishu_link = optional_text(task, "feishu_doc_link")
    cloud_markdown = task.get("cloud_markdown") if isinstance(task.get("cloud_markdown"), dict) else {}
    cloud_markdown_path = str(cloud_markdown.get("source_cloud_markdown") or cloud_markdown.get("markdown_file") or "")
    outputs, _ = requested_outputs(task)
    requested_output_lines = "\n".join(f"- {item}" for item in outputs) if outputs else "- 无"
    return f"""## 云端自动填充区

> 这一段由 Mac OpenClaw 根据云端 task / 飞书 / Obsidian 路径自动写入。你可以修正明显错误，但不要把原始素材清单粘到这里。

creation_run_id：{optional_text(task, "creation_run_id") or "无"}
batch_id：{batch_id}
topic：{topic}
platform：{platform or "无"}
content_type：{content_type or "无"}
feishu_doc_link：{feishu_link or "无"}
source_task_id：{task_id or "无"}
source_task_type：{task_type or "无"}
cloud_markdown：{cloud_markdown_path or "无"}

requested_outputs：
{requested_output_lines}
"""


def batch_note_text(task: dict[str, Any], batch_dir: Path) -> str:
    source_task = task.get("source_agent_task") if isinstance(task.get("source_agent_task"), dict) else {}
    task_id = str(source_task.get("task_id") or task.get("creation_run_id") or "")
    topic = optional_text(task, "topic") or optional_text(task, "batch_id") or batch_dir.name
    feishu_link = optional_text(task, "feishu_doc_link")
    cloud_markdown = task.get("cloud_markdown") if isinstance(task.get("cloud_markdown"), dict) else {}
    cloud_markdown_path = str(cloud_markdown.get("source_cloud_markdown") or cloud_markdown.get("markdown_file") or "")
    return f"""# {batch_dir.name}

{cloud_prefill_block(task, batch_dir)}

## 云端项目引用

Obsidian 项目ID：

飞书文档：
- {feishu_link or "无"}

腾讯云初稿路径：
- 01_idea_card:
- 02_project_brief:
- 04_script:
- task: {task_id or "无"}
- cloud_markdown: {cloud_markdown_path or "无"}

## 本地素材批次

事件：{topic}
地点：
人物：
时间范围：
素材来源：
本地素材批次：{batch_dir}
目标项目：
是否已有正式项目目录：

## 人工补充线索

下面三项只写“文件本身看不出来、但你知道”的信息。它们不是最终分类结论，也不是让你提前筛片；只是防止后续 AI / OpenClaw 误判素材用途。

- “这批素材可能服务的内容”：这批素材可能用于哪些短视频、图文或项目，例如“活动第一视角”“人物回访 vlog”“路途混剪”。
- “必须保留 / 特别注意”：不能误删、不能拆散、不能当普通素材处理的内容，例如 Live Photo 同名组、360 原始组、设备调试画面、某个必须保留的人物片段。
- “不确定的地方”：你自己也拿不准、需要 AI 或人工复核的点，例如归属项目、是否值得修复、地点/人物是否确认。

如果没有信息，就保留 `- 无`。

这批素材可能服务的内容：

- 无

必须保留 / 特别注意：

- 无

不确定的地方：

- 无

## 临时初稿摘录

> 没有 Obsidian 路径时才填。
"""


def insert_cloud_prefill_if_missing(note_path: Path, task: dict[str, Any], batch_dir: Path) -> bool:
    try:
        text = note_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise QueueError(f"failed to read batch note: {note_path}: {exc}") from exc
    if "## 云端自动填充区" in text:
        return False

    block = cloud_prefill_block(task, batch_dir)
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# "):
        updated = "".join(lines[:1]).rstrip() + "\n\n" + block.rstrip() + "\n\n" + "".join(lines[1:]).lstrip()
    else:
        updated = block.rstrip() + "\n\n" + text
    try:
        note_path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        raise QueueError(f"failed to update batch note: {note_path}: {exc}") from exc
    return True


def ensure_local_batch_shell(task: dict[str, Any], config: QueueConfig, creation_run_id: str) -> tuple[Path, list[str]]:
    batch, warnings = resolve_local_batch_path(task, config, creation_run_id)
    if not batch.exists():
        try:
            batch.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise QueueError(f"failed to create local_batch_path: {batch}: {exc}") from exc
        warnings.append("auto_created_local_batch_dir")

    batch_note = batch / BATCH_NOTE_NAME
    if batch_note.exists() and not batch_note.is_file():
        raise QueueError(f"batch note path is not a file: {batch_note}")
    if not batch_note.exists():
        try:
            batch_note.write_text(batch_note_text(task, batch), encoding="utf-8")
        except OSError as exc:
            raise QueueError(f"failed to create batch note: {batch_note}: {exc}") from exc
        warnings.append("auto_created_batch_note")
    elif insert_cloud_prefill_if_missing(batch_note, task, batch):
        warnings.append("inserted_cloud_prefill_into_batch_note")
    return batch, warnings


def task_files(config: QueueConfig) -> list[Path]:
    ensure_queue_dirs(config)
    candidates: list[Path] = []
    for path in config.cloud_to_mac.iterdir():
        if path.is_file() and path.suffix.lower() == ".json":
            candidates.append(path)
        elif path.is_dir() and (path / "manifest.json").is_file():
            candidates.append(path)
    return sorted(candidates, key=lambda path: path.name)


def result_path_for(config: QueueConfig, creation_run_id: str) -> Path:
    return config.mac_to_cloud / f"{safe_slug(creation_run_id, 128)}.result.json"


def local_status_path(batch_dir: Path) -> Path:
    return batch_dir / LOCAL_LINK_DIR / "status.json"


def local_link_path(batch_dir: Path) -> Path:
    return batch_dir / LOCAL_LINK_DIR / "link.json"


def move_task_file(task_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / task_path.name
    if destination.exists():
        destination = dest_dir / f"{task_path.stem}_{safe_slug(now_iso(), 32)}{task_path.suffix}"
    shutil.move(str(task_path), str(destination))
    return destination


def markdown_info(task: dict[str, Any], task_path: Path) -> dict[str, Any]:
    markdown_file = optional_text(task, "markdown_file")
    if not markdown_file:
        return {}
    if Path(markdown_file).is_absolute() or ".." in Path(markdown_file).parts:
        raise QueueError("markdown_file must be a safe package-relative path")
    if not task_path.is_dir():
        raise QueueError("markdown_file requires a cloud_to_mac package directory with manifest.json")
    markdown_path = task_path / markdown_file
    if not markdown_path.exists() or not markdown_path.is_file():
        raise QueueError(f"markdown_file does not exist: {markdown_path}")
    if markdown_path.suffix.lower() != ".md":
        raise QueueError(f"markdown_file must be a Markdown file: {markdown_path}")

    actual_sha = sha256_file(markdown_path)
    expected_sha = optional_text(task, "markdown_sha256")
    if expected_sha and not SHA256_PATTERN.fullmatch(expected_sha):
        raise QueueError("markdown_sha256 must be a 64-character hexadecimal digest")
    if expected_sha and expected_sha.lower() != actual_sha:
        raise QueueError(f"markdown_sha256 mismatch for {markdown_file}")
    return {
        **source_identity(task),
        "markdown_file": markdown_file,
        "markdown_sha256": actual_sha,
        "markdown_sha256_expected": expected_sha,
        "local_markdown_path": str(markdown_path),
        "source_cloud_markdown": optional_text(task, "source_cloud_markdown"),
        "syncthing_relative_package": optional_text(task, "syncthing_relative_package"),
    }


def update_markdown_location(info: dict[str, Any], moved_task_path: Path) -> dict[str, Any]:
    if not info:
        return {}
    updated = dict(info)
    updated["local_markdown_path"] = str(moved_task_path / str(info["markdown_file"]))
    return updated


def build_link(
    *,
    task: dict[str, Any],
    task_path: Path,
    processed_task_path: Path | None,
    batch_dir: Path,
    creation_run_id: str,
    outputs: list[str],
    warnings: list[str],
    cloud_markdown: dict[str, Any] | None = None,
    local_project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    batch_note = batch_dir / BATCH_NOTE_NAME
    return {
        **source_identity(task),
        "spec_version": LINK_SPEC_VERSION,
        "doc_type": "openclaw_local_batch_link",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "owner_agent": "mac_openclaw",
        "status": "linked",
        "creation_run_id": creation_run_id,
        "feishu_doc_link": optional_text(task, "feishu_doc_link"),
        "batch_id": optional_text(task, "batch_id") or batch_dir.name,
        "topic": optional_text(task, "topic"),
        "platform": optional_text(task, "platform"),
        "content_type": optional_text(task, "content_type"),
        "local_batch_path": str(batch_dir),
        "local_project": local_project or {},
        "batch_note_path": str(batch_note),
        "queue_task_path": str(task_path),
        "processed_task_path": str(processed_task_path) if processed_task_path else "",
        "requested_outputs": outputs,
        "cloud_markdown": cloud_markdown or {},
        "media_file_count": count_media_files(batch_dir),
        "warnings": warnings,
        "sync_policy": [
            "_OpenClawQueue 只同步 JSON 控制文件。",
            "00_Inbox_Mac_Intake 原始照片和视频只留在 Mac 本地。",
            "mac_to_cloud result 不写入原素材文件名清单。",
        ],
    }


def build_status(
    *,
    status: str,
    creation_run_id: str,
    result_path: Path,
    detail: str = "",
    outputs: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "spec_version": STATUS_SPEC_VERSION,
        "doc_type": "openclaw_local_batch_status",
        "updated_at": now_iso(),
        "owner_agent": "mac_openclaw",
        "status": status,
        "creation_run_id": creation_run_id,
        "detail": detail,
        "requested_outputs": outputs or [],
        "warnings": warnings or [],
        "last_result_path": str(result_path),
    }


def success_result(
    *,
    task: dict[str, Any],
    task_type: str,
    creation_run_id: str,
    batch_dir: Path,
    result_path: Path,
    link_path: Path,
    status_path: Path,
    moved_task_path: Path,
    outputs: list[str],
    warnings: list[str],
    cloud_markdown: dict[str, Any] | None = None,
    local_project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    batch_note = batch_dir / BATCH_NOTE_NAME
    identity = source_identity(task)
    return {
        "spec_version": RESULT_SPEC_VERSION,
        "content_os_spec_version": "content_os_v0.2",
        "doc_type": "mac_result",
        "task_id": identity.get("task_id", ""),
        "task_type": task_type,
        "source_task_type": identity.get("task_type", ""),
        "project_id": identity.get("project_id"),
        "idea_id": identity.get("idea_id"),
        "project_revision": identity.get("project_revision"),
        "change_request_id": identity.get("change_request_id"),
        "editor_backend": identity.get("editor_backend"),
        "tenant_id": identity.get("tenant_id"),
        "creation_run_id": creation_run_id,
        "completed_by": "mac_openclaw",
        "status": "linked",
        "generated_at": now_iso(),
        "idempotency_key": result_idempotency_key(task, creation_run_id),
        "request_fingerprint": request_fingerprint(task),
        "feishu_doc_link": optional_text(task, "feishu_doc_link"),
        "batch_id": optional_text(task, "batch_id") or batch_dir.name,
        "topic": optional_text(task, "topic"),
        "platform": optional_text(task, "platform"),
        "content_type": optional_text(task, "content_type"),
        "local_batch_path": str(batch_dir),
        "local_project_path": str((local_project or {}).get("local_project_path", "")),
        "local_outputs": {
            "batch_note": str(batch_note),
            "local_link": str(link_path),
            "local_status": str(status_path),
            "local_project_link": str((local_project or {}).get("project_link", "")),
        },
        "local_project": local_project or {},
        "cloud_markdown": cloud_markdown or {},
        "queue": {
            "processed_task_path": str(moved_task_path),
            "result_path": str(result_path),
        },
        "requested_outputs": outputs,
        "media_file_count": count_media_files(batch_dir),
        "warnings": warnings,
        "next_actions": [
            "Mac 本地读取批次说明、正式项目目录和真实素材，生成素材匹配、Storyboard 或 EDL。",
            "腾讯云只读取本 result 和后续 Mac 回写产物，不同步 00_Inbox_Mac_Intake 原素材。",
        ],
    }


def blocked_result(
    *,
    task: dict[str, Any],
    task_path: Path,
    creation_run_id: str,
    reason: str,
    result_path: Path,
    moved_task_path: Path | None,
    status_path: Path | None,
) -> dict[str, Any]:
    identity = source_identity(task)
    return {
        "spec_version": RESULT_SPEC_VERSION,
        "content_os_spec_version": "content_os_v0.2",
        "doc_type": "mac_result",
        "task_id": identity.get("task_id", ""),
        "task_type": task.get("task_type", "unknown"),
        "source_task_type": identity.get("task_type", ""),
        "project_id": identity.get("project_id"),
        "idea_id": identity.get("idea_id"),
        "project_revision": identity.get("project_revision"),
        "change_request_id": identity.get("change_request_id"),
        "editor_backend": identity.get("editor_backend"),
        "tenant_id": identity.get("tenant_id"),
        "creation_run_id": creation_run_id,
        "completed_by": "mac_openclaw",
        "status": "blocked",
        "blocked_reason": "queue_contract_failed",
        "detail": reason,
        "generated_at": now_iso(),
        "idempotency_key": result_idempotency_key(task, creation_run_id),
        "request_fingerprint": request_fingerprint(task),
        "source_task_path": str(task_path),
        "failed_task_path": str(moved_task_path) if moved_task_path else "",
        "local_status_path": str(status_path) if status_path else "",
        "next_actions": [
            "如果 detail 指向路径越界、字段错误或文件占用了批次目录，修正 cloud_to_mac JSON 后重新投递一个新任务文件。",
            "本地批次目录和 00_批次说明.md 缺失时会由 Mac OpenClaw 自动创建。",
            "不要把 00_Inbox_Mac_Intake 原始素材同步到云端。",
        ],
    }


def process_task(task_path: Path, config: QueueConfig) -> dict[str, Any]:
    ensure_queue_dirs(config)
    task: dict[str, Any] = {}
    creation_run_id = f"invalid_{safe_slug(task_path.stem, 96)}"
    result_path = result_path_for(config, creation_run_id)
    status_path: Path | None = None
    moved_task_path: Path | None = None

    try:
        task = load_json(task_path)
        task_type = validate_task_type(task)
        creation_run_id = validate_creation_run_id(task.get("creation_run_id"))
        # Validate the retry key before moving the task or creating local
        # evidence, so malformed identity input produces a clean blocked result.
        idempotency_key(task, creation_run_id)
        result_path = result_path_for(config, creation_run_id)
        fingerprint = request_fingerprint(task)
        if result_path.exists():
            existing = read_json_quiet(result_path)
            if isinstance(existing, dict) and existing.get("request_fingerprint") == fingerprint:
                moved_task_path = move_task_file(task_path, config.processed) if task_path.exists() else None
                replay = dict(existing)
                replay["idempotent_replay"] = True
                replay["replayed_at"] = now_iso()
                replay["replayed_task_path"] = str(moved_task_path) if moved_task_path else ""
                return replay
            conflict_path = config.mac_to_cloud / (
                f"{safe_slug(creation_run_id, 128)}.conflict-"
                f"{fingerprint.removeprefix('sha256:')[:16]}.result.json"
            )
            moved_task_path = move_task_file(task_path, config.failed) if task_path.exists() else None
            conflict = blocked_result(
                task=task,
                task_path=task_path,
                creation_run_id=creation_run_id,
                reason="idempotency conflict: an existing result has a different request fingerprint",
                result_path=conflict_path,
                moved_task_path=moved_task_path,
                status_path=None,
            )
            conflict["blocked_reason"] = "idempotency_conflict"
            conflict["existing_result_path"] = str(result_path)
            atomic_write_json(conflict_path, conflict)
            return conflict
        outputs, warnings = requested_outputs(task)
        cloud_markdown = markdown_info(task, task_path)
        batch_dir, provision_warnings = ensure_local_batch_shell(task, config, creation_run_id)
        warnings.extend(provision_warnings)
        local_project = ensure_formal_project_for_batch(batch_dir, task=task, workspace_root=config.workspace_root)
        warnings.extend(f"project:{item}" for item in local_project.get("warnings", []))
        status_path = local_status_path(batch_dir)

        moved_task_path = move_task_file(task_path, config.processed)
        cloud_markdown = update_markdown_location(cloud_markdown, moved_task_path)
        link_path = local_link_path(batch_dir)
        link = build_link(
            task=task,
            task_path=task_path,
            processed_task_path=moved_task_path,
            batch_dir=batch_dir,
            creation_run_id=creation_run_id,
            outputs=outputs,
            warnings=warnings,
            cloud_markdown=cloud_markdown,
            local_project=local_project,
        )
        link["processed_task_path"] = str(moved_task_path)
        atomic_write_json(link_path, link)
        atomic_write_json(
            status_path,
            build_status(
                status="linked",
                creation_run_id=creation_run_id,
                result_path=result_path,
                outputs=outputs,
                warnings=warnings,
            ),
        )
        result = success_result(
            task=task,
            task_type=task_type,
            creation_run_id=creation_run_id,
            batch_dir=batch_dir,
            result_path=result_path,
            link_path=link_path,
            status_path=status_path,
            moved_task_path=moved_task_path,
            outputs=outputs,
            warnings=warnings,
            cloud_markdown=cloud_markdown,
            local_project=local_project,
        )
        atomic_write_json(result_path, result)
        return result

    except QueueError as exc:
        reason = str(exc)
        try:
            if task and has_local_batch_reference(task):
                batch_dir, _ = resolve_local_batch_path(task, config, creation_run_id)
                status_path = local_status_path(batch_dir)
                atomic_write_json(
                    status_path,
                    build_status(
                        status="blocked",
                        creation_run_id=creation_run_id,
                        result_path=result_path,
                        detail=reason,
                    ),
                )
        except QueueError:
            status_path = None
        moved_task_path = move_task_file(task_path, config.failed) if task_path.exists() else None
        result = blocked_result(
            task=task,
            task_path=task_path,
            creation_run_id=creation_run_id,
            reason=reason,
            result_path=result_path,
            moved_task_path=moved_task_path,
            status_path=status_path,
        )
        atomic_write_json(result_path, result)
        return result


def process_pending(config: QueueConfig) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in task_files(config):
        results.append(process_task(path, config))
    return results


def legacy_queue_packages(config: QueueConfig) -> list[Path]:
    legacy = config.queue_root.parent / "98_Agent任务队列" / "01_cloud_to_mac_ready"
    if not legacy.exists():
        return []
    return sorted(
        path
        for path in legacy.iterdir()
        if path.is_dir() and path.name.startswith("run_") and (path / "manifest.json").is_file()
    )


def print_legacy_route_warning(config: QueueConfig) -> None:
    packages = legacy_queue_packages(config)
    if not packages:
        return
    print("发现旧链路 Markdown 包，Mac OpenClaw 不会处理这些目录：", file=sys.stderr)
    for path in packages:
        print(f"- {path}", file=sys.stderr)
    print(
        f"请让云端改投：{config.cloud_to_mac}/run_id/manifest.json 或 run_id.json",
        file=sys.stderr,
    )


def print_results(results: list[dict[str, Any]], config: QueueConfig) -> None:
    if not results:
        print(f"没有待处理任务：{config.cloud_to_mac}")
        return
    for result in results:
        print(
            f"{result.get('status')} "
            f"{result.get('creation_run_id')} -> "
            f"{config.mac_to_cloud / (str(result.get('creation_run_id')) + '.result.json')}"
        )


def build_config(args: argparse.Namespace) -> QueueConfig:
    workspace_root = Path(args.workspace_root).expanduser().resolve()
    queue_root = Path(args.queue_root).expanduser() if args.queue_root else default_queue_root(workspace_root)
    if not queue_root.is_absolute():
        queue_root = workspace_root / queue_root
    return QueueConfig(workspace_root=workspace_root, queue_root=queue_root.resolve())


def default_queue_root(workspace_root: Path) -> Path:
    env_root = os.environ.get("OPENCLAW_QUEUE_ROOT", "").strip()
    if env_root:
        return Path(env_root).expanduser()
    return workspace_root / QUEUE_DIR_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description="处理 _OpenClawQueue/cloud_to_mac 中的轻量 JSON 任务")
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT, help="本地素材根目录")
    parser.add_argument("--queue-root", type=Path, default=None, help="轻量同步队列目录；默认使用本地素材根/_OpenClawQueue")
    parser.add_argument("--once", action="store_true", help="处理当前任务后退出；默认行为")
    parser.add_argument("--watch", action="store_true", help="常驻监听 cloud_to_mac")
    parser.add_argument("--interval", type=float, default=10.0, help="watch 模式轮询秒数")
    args = parser.parse_args()

    if args.once and args.watch:
        parser.error("--once and --watch cannot be used together")
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    config = build_config(args)
    ensure_queue_dirs(config)
    print_legacy_route_warning(config)
    if args.watch:
        print(f"Mac OpenClaw 队列监听中：{config.cloud_to_mac}")
        try:
            while True:
                print_results(process_pending(config), config)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n已停止监听")
            return 0

    print_results(process_pending(config), config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
