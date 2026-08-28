#!/usr/bin/env python3
"""Bridge a Content OS task into the local OpenClaw execution queue.

98_Agent任务队列 is the document/task layer. _OpenClawQueue is the local
material execution layer. This script creates the lower-layer JSON control
file from an upper-layer YAML task without copying media.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from media_common import now_iso, safe_slug
from runtime_paths import obsidian_root


SCRIPT_DIR = Path(__file__).resolve().parent
SYSTEM_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = SYSTEM_ROOT.parent if SYSTEM_ROOT.name == "99_System_OpenClaw" else SYSTEM_ROOT
DEFAULT_VAULT_ROOT = obsidian_root()
TASK_INBOX = Path("98_Agent任务队列/01_cloud_to_mac_ready")
RESULT_OUTBOX = Path("98_Agent任务队列/02_mac_to_cloud_results")
QUEUE_DIR_NAME = "_OpenClawQueue"


class EnqueueError(Exception):
    """Raised when the upper-layer task cannot produce a local queue job."""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise EnqueueError(f"task YAML does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise EnqueueError(f"task YAML root must be a mapping: {path}")
    return data


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temp.replace(path)


def atomic_write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)
    temp.replace(path)


def resolve_task_path(ref: str, vault_root: Path) -> Path:
    candidate = Path(ref).expanduser()
    if candidate.exists():
        return candidate.resolve()

    task_dir = vault_root / TASK_INBOX
    direct = task_dir / ref
    if direct.exists():
        return direct.resolve()
    if not ref.endswith(".yaml"):
        direct_yaml = task_dir / f"{ref}.yaml"
        if direct_yaml.exists():
            return direct_yaml.resolve()

    matches: list[Path] = []
    if task_dir.exists():
        for path in task_dir.glob("*.yaml"):
            try:
                task = load_yaml(path)
            except EnqueueError:
                continue
            task_id = str(task.get("task_id", ""))
            if ref in {task_id, path.name, path.stem}:
                matches.append(path)
            elif ref and ref in task_id:
                matches.append(path)
    if not matches:
        raise EnqueueError(f"task not found in 98_Agent任务队列: {ref}")
    if len(matches) > 1:
        raise EnqueueError(f"task reference is ambiguous: {ref} -> {', '.join(path.name for path in matches)}")
    return matches[0].resolve()


def resolve_queue_root(workspace_root: Path, raw: Path | None) -> Path:
    if raw is None:
        return workspace_root / QUEUE_DIR_NAME
    queue_root = raw.expanduser()
    return queue_root if queue_root.is_absolute() else workspace_root / queue_root


def ready_task_paths(vault_root: Path) -> list[Path]:
    task_dir = vault_root / TASK_INBOX
    if not task_dir.exists():
        return []
    return sorted(path for path in task_dir.glob("*.yaml") if path.is_file())


def task_result_path(task_path: Path, task: dict[str, Any], vault_root: Path) -> Path:
    if task_path.name.startswith("task_"):
        result_name = "result_" + task_path.name[len("task_") :]
    else:
        result_name = f"result_{task.get('task_id', task_path.stem)}.yaml"
    return vault_root / RESULT_OUTBOX / result_name


def dispatch_result_done(task_path: Path, task: dict[str, Any], vault_root: Path) -> bool:
    result_path = task_result_path(task_path, task, vault_root)
    if not result_path.exists():
        return False
    with result_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return isinstance(data, dict) and data.get("status") == "done"


def task_inputs(task: dict[str, Any]) -> dict[str, Any]:
    inputs = task.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


def resolve_input_path(value: str, vault_root: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (vault_root / path).resolve()


def local_batch_from_content_os_link(inputs: dict[str, Any], vault_root: Path) -> str:
    raw_link = inputs.get("content_os_link_path")
    if not isinstance(raw_link, str) or not raw_link.strip():
        return ""
    link_path = resolve_input_path(raw_link, vault_root)
    if not link_path.exists():
        raise EnqueueError(f"content_os_link_path does not exist: {link_path}")
    with link_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise EnqueueError(f"content_os_link_path root must be a mapping: {link_path}")
    batch = data.get("batch")
    if not isinstance(batch, dict):
        raise EnqueueError(f"content_os_link_path missing batch mapping: {link_path}")
    return str(batch.get("dir") or "").strip()


def local_batch_path(task: dict[str, Any], vault_root: Path) -> str:
    for key in ("local_batch_path", "mac_local_batch_path_hint"):
        value = task.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    inputs = task_inputs(task)
    for key in ("local_batch_path", "mac_local_batch_path_hint", "local_batch"):
        value = inputs.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict) and isinstance(value.get("path"), str):
            return value["path"].strip()
    nested = task.get("local_batch")
    if isinstance(nested, dict) and isinstance(nested.get("path"), str):
        return nested["path"].strip()
    return local_batch_from_content_os_link(inputs, vault_root)


def default_requested_outputs(task: dict[str, Any]) -> list[str]:
    task_type = str(task.get("task_type", "")).strip()
    if task_type == "local_material_match":
        return ["素材匹配", "Storyboard", "EDL", "local_assets"]
    if task_type == "local_output_review":
        return ["成片质检", "metrics", "问题清单"]
    return ["写入批次/_openclaw/link.json", "写入批次/_openclaw/status.json", "回写 _OpenClawQueue/mac_to_cloud/*.result.json"]


def requested_outputs(task: dict[str, Any]) -> list[str]:
    inputs = task_inputs(task)
    raw = inputs.get("openclaw_queue_requested_outputs") or inputs.get("requested_outputs")
    if raw is None:
        return default_requested_outputs(task)
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise EnqueueError("requested outputs must be a list of non-empty strings")
    return [item.strip() for item in raw]


def creation_run_id(task: dict[str, Any]) -> str:
    value = task.get("creation_run_id") or task_inputs(task).get("creation_run_id") or task.get("task_id")
    if not isinstance(value, str) or not value.strip():
        raise EnqueueError("task must contain task_id or creation_run_id")
    return value.strip()


def feishu_doc_link(task: dict[str, Any]) -> str:
    inputs = task_inputs(task)
    value = task.get("feishu_doc_link") or inputs.get("feishu_doc_link") or inputs.get("feishu_url")
    return value.strip() if isinstance(value, str) else ""


def batch_id(task: dict[str, Any]) -> str:
    inputs = task_inputs(task)
    value = task.get("batch_id") or inputs.get("batch_id") or task.get("project_id") or ""
    return value.strip() if isinstance(value, str) else ""


def build_queue_task(task: dict[str, Any], task_path: Path, vault_root: Path) -> dict[str, Any]:
    payload = task.get("openclaw_queue_payload")
    if isinstance(payload, dict):
        queue_task = dict(payload)
        if queue_task.get("task_type") != "bind_creation_run_to_local_batch":
            raise EnqueueError("openclaw_queue_payload.task_type must be bind_creation_run_to_local_batch")
        if not queue_task.get("creation_run_id"):
            queue_task["creation_run_id"] = creation_run_id(task)
        if not queue_task.get("feishu_doc_link"):
            queue_task["feishu_doc_link"] = feishu_doc_link(task)
        if not queue_task.get("batch_id"):
            task_batch_id = batch_id(task)
            if task_batch_id:
                queue_task["batch_id"] = task_batch_id
        if not queue_task.get("local_batch_path") and "local_batch" not in queue_task:
            batch_path = local_batch_path(task, vault_root)
            if batch_path:
                queue_task["local_batch_path"] = batch_path
        constraints = queue_task.get("constraints")
        if not isinstance(constraints, dict):
            constraints = {}
        constraints.update(
            {
                "do_not_sync_raw_media": True,
                "do_not_include_original_photos_or_videos_in_result": True,
                "mac_reads_local_inbox_batch": True,
                "old_queue_is_task_layer": True,
                "openclaw_queue_is_execution_layer": True,
            }
        )
        queue_task["constraints"] = constraints
        queue_task["schema_version"] = str(queue_task.get("schema_version") or "openclaw_mac_queue_task_v1")
        queue_task["created_at"] = str(queue_task.get("created_at") or now_iso())
        queue_task["source_agent_task"] = {
            "task_id": task.get("task_id", ""),
            "task_type": task.get("task_type", ""),
            "project_id": task.get("project_id", ""),
            "idea_id": task.get("idea_id", ""),
            "vault_task_path": str(task_path),
        }
        return queue_task

    batch_path = local_batch_path(task, vault_root)
    task_batch_id = batch_id(task)
    if not batch_path and not task_batch_id:
        raise EnqueueError(
            "cannot enqueue local material job: task must provide inputs.local_batch_path, "
            "inputs.local_batch.path, task.local_batch.path, inputs.content_os_link_path, or batch_id"
        )
    queue_task = {
        "schema_version": "openclaw_mac_queue_task_v1",
        "task_type": "bind_creation_run_to_local_batch",
        "created_at": now_iso(),
        "creation_run_id": creation_run_id(task),
        "feishu_doc_link": feishu_doc_link(task),
        "batch_id": task_batch_id,
        "source_agent_task": {
            "task_id": task.get("task_id", ""),
            "task_type": task.get("task_type", ""),
            "project_id": task.get("project_id", ""),
            "idea_id": task.get("idea_id", ""),
            "vault_task_path": str(task_path),
        },
        "platform": task.get("platform", ""),
        "content_type": task.get("content_type", ""),
        "topic": task.get("topic", ""),
        "requested_outputs": requested_outputs(task),
        "constraints": {
            "do_not_sync_raw_media": True,
            "do_not_include_original_photos_or_videos_in_result": True,
            "mac_reads_local_inbox_batch": True,
            "old_queue_is_task_layer": True,
            "openclaw_queue_is_execution_layer": True,
        },
    }
    if batch_path:
        queue_task["local_batch"] = {
            "path": batch_path,
            "required": True,
        }
    return queue_task


def enqueue_task(
    task_ref: str,
    *,
    vault_root: Path,
    workspace_root: Path,
    queue_root: Path,
    allow_replace: bool,
    process: bool,
) -> Path:
    task_path = resolve_task_path(task_ref, vault_root)
    task = load_yaml(task_path)
    queue_task = build_queue_task(task, task_path, vault_root)
    run_id = str(queue_task["creation_run_id"])
    output = queue_root / "cloud_to_mac" / f"{safe_slug(run_id, 128)}.json"
    if output.exists() and not allow_replace:
        raise EnqueueError(f"queue task already exists; use --allow-replace: {output}")
    atomic_write_json(output, queue_task)
    if process:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "32_process_openclaw_queue.py"),
                "--workspace-root",
                str(workspace_root),
                "--queue-root",
                str(queue_root),
                "--once",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        if result.returncode != 0:
            raise EnqueueError(f"32_process_openclaw_queue.py failed: {result.returncode}")
        write_dispatch_result(task, task_path, vault_root, queue_root, output, run_id)
    return output


def process_ready_tasks(
    *,
    vault_root: Path,
    workspace_root: Path,
    queue_root: Path,
    allow_replace: bool,
) -> list[tuple[Path, str]]:
    outcomes: list[tuple[Path, str]] = []
    for task_path in ready_task_paths(vault_root):
        try:
            task = load_yaml(task_path)
            if not allow_replace and dispatch_result_done(task_path, task, vault_root):
                outcomes.append((task_path, "skipped_done"))
                continue
            enqueue_task(
                str(task_path),
                vault_root=vault_root,
                workspace_root=workspace_root,
                queue_root=queue_root,
                allow_replace=True,
                process=True,
            )
            outcomes.append((task_path, "processed"))
        except EnqueueError as exc:
            outcomes.append((task_path, f"blocked:{exc}"))
    return outcomes


def load_queue_result(queue_root: Path, run_id: str) -> dict[str, Any]:
    path = queue_root / "mac_to_cloud" / f"{safe_slug(run_id, 128)}.result.json"
    if not path.exists():
        raise EnqueueError(f"queue result was not written: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise EnqueueError(f"queue result root must be an object: {path}")
    return data


def write_dispatch_result(
    task: dict[str, Any],
    task_path: Path,
    vault_root: Path,
    queue_root: Path,
    queue_task_path: Path,
    run_id: str,
) -> Path:
    queue_result = load_queue_result(queue_root, run_id)
    queue_result_path = queue_root / "mac_to_cloud" / f"{safe_slug(run_id, 128)}.result.json"
    result_path = task_result_path(task_path, task, vault_root)
    status = str(queue_result.get("status") or "blocked")
    dispatch_result = {
        "spec_version": "content_os_v0.1",
        "task_id": task.get("task_id", ""),
        "task_type": task.get("task_type", "openclaw_queue_dispatch"),
        "completed_by": "mac_openclaw",
        "status": "done" if status == "linked" else "blocked",
        "blocked_reason": queue_result.get("blocked_reason", "") if status != "linked" else "",
        "detail": queue_result.get("detail", ""),
        "creation_run_id": run_id,
        "feishu_doc_link": task.get("feishu_doc_link", ""),
        "outputs": {
            "openclaw_queue_source_task": queue_result.get("source_task_path", str(queue_task_path)),
            "openclaw_queue_failed_task": queue_result.get("failed_task_path", ""),
            "openclaw_queue_processed_task": (queue_result.get("queue") or {}).get("processed_task_path", ""),
            "openclaw_queue_result": str(queue_result_path),
        },
        "local_outputs": queue_result.get("local_outputs", {}),
        "queue_status": status,
        "queue_result_summary": {
            "media_file_count": queue_result.get("media_file_count"),
            "requested_outputs": queue_result.get("requested_outputs", []),
            "next_actions": queue_result.get("next_actions", []),
        },
        "validation": {
            "old_queue_is_task_layer": True,
            "openclaw_queue_is_execution_layer": True,
            "raw_media_synced": False,
            "queue_result_written": True,
        },
        "next_owner": "human" if status != "linked" else "mac_openclaw",
        "notes": [
            "98_Agent任务队列 only carries the task/result summary.",
            "_OpenClawQueue carries local material execution control.",
            "Original photos and videos remain only in the Mac local Inbox/project workspace.",
        ],
    }
    atomic_write_yaml(result_path, dispatch_result)
    print(f"dispatch_result={result_path}")
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser(description="把 98_Agent任务队列 YAML 任务桥接为 _OpenClawQueue JSON 执行任务")
    parser.add_argument("task", nargs="?", help="task_id、YAML 文件名或 YAML 路径")
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    parser.add_argument("--queue-root", type=Path, default=None)
    parser.add_argument("--allow-replace", action="store_true")
    parser.add_argument("--process", action="store_true", help="写入 JSON 后立即运行 32_process_openclaw_queue.py --once")
    parser.add_argument("--all-ready", action="store_true", help="处理 98_Agent任务队列/01_cloud_to_mac_ready 下所有未完成任务")
    parser.add_argument("--watch", action="store_true", help="常驻监听 98_Agent任务队列，云端有任务单就桥接并处理")
    parser.add_argument("--interval", type=float, default=10.0, help="watch 模式轮询秒数")
    args = parser.parse_args()

    if args.task and (args.all_ready or args.watch):
        parser.error("task cannot be combined with --all-ready or --watch")
    if not args.task and not args.all_ready and not args.watch:
        parser.error("provide task, --all-ready, or --watch")
    if args.interval <= 0:
        parser.error("--interval must be greater than 0")

    vault_root = args.vault_root.expanduser().resolve()
    workspace_root = args.workspace_root.expanduser().resolve()
    queue_root = resolve_queue_root(workspace_root, args.queue_root).resolve()

    if args.all_ready or args.watch:
        try:
            while True:
                outcomes = process_ready_tasks(
                    vault_root=vault_root,
                    workspace_root=workspace_root,
                    queue_root=queue_root,
                    allow_replace=args.allow_replace,
                )
                if not outcomes:
                    print(f"没有云端待处理任务：{vault_root / TASK_INBOX}")
                for path, status in outcomes:
                    print(f"{status} {path}")
                if not args.watch:
                    return 0
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n已停止监听")
            return 0

    try:
        assert args.task is not None
        output = enqueue_task(
            args.task,
            vault_root=vault_root,
            workspace_root=workspace_root,
            queue_root=queue_root,
            allow_replace=args.allow_replace,
            process=args.process,
        )
    except EnqueueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"queue_task={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
