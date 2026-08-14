#!/usr/bin/env python3
"""Validate a Content OS v0.2 task before the Mac runner executes it.

The validator deliberately reads the project overview and, for revision work,
the canonical change request.  A ready queue file is therefore only an
instruction: it cannot make an old project revision or an unconfirmed idea
executable on its own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


SPEC_VERSION = "content_os_v0.2"
PROJECT_OVERVIEW = "00_项目总览.md"
SUPPORTED_EDITOR_BACKENDS = frozenset({"handoff_pack", "otio_kdenlive"})
SUPPORTED_TASK_TYPES = frozenset(
    {
        "local_material_match",
        "generate_edit_handoff_pack",
        "generate_otio_kdenlive_timeline",
        "revise_local_edit_artifacts",
        "local_output_review",
        "generate_ai_edit_log",
    }
)
BACKEND_TASK_TYPES = {
    "generate_edit_handoff_pack": "handoff_pack",
    "generate_otio_kdenlive_timeline": "otio_kdenlive",
}
REVISION_TASK_TYPES = {"revise_local_edit_artifacts"}
LOCAL_EDITOR_OUTPUT_TASK_TYPES = {
    "generate_edit_handoff_pack",
    "generate_otio_kdenlive_timeline",
    "revise_local_edit_artifacts",
}


class ValidationError(Exception):
    """Raised when a task violates the Content OS task contract."""


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"YAML file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValidationError(f"YAML root must be a mapping: {path}")
    return data


def load_markdown_frontmatter(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"project overview does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValidationError(f"project overview must start with YAML frontmatter: {path}")
    end = text.find("\n---", len("---\n"))
    if end < 0:
        raise ValidationError(f"project overview frontmatter is not closed: {path}")
    try:
        data = yaml.safe_load(text[len("---\n") : end])
    except yaml.YAMLError as exc:
        raise ValidationError(f"project overview frontmatter is invalid YAML: {path}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"project overview frontmatter must be a mapping: {path}")
    return data


def require_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"missing required text field: {key}")
    return value.strip()


def require_positive_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(f"{key} must be a positive integer")
    return value


def require_true(data: dict[str, Any], key: str) -> None:
    if data.get(key) is not True:
        raise ValidationError(f"{key} must be true")


def as_list(value: Any, key: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError(f"{key} must be a list")
    return value


def vault_relative_path(value: str, vault_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValidationError(f"Obsidian path must be relative to the vault, got absolute path: {value}")
    parts = path.parts
    if parts and parts[0] == vault_root.name:
        raise ValidationError(f"Obsidian path must not include the vault root name: {value}")
    return path


def resolve_action(action: str, capabilities: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    supported = capabilities.get("supported_actions") or {}
    if not isinstance(supported, dict):
        raise ValidationError("capabilities.supported_actions must be a mapping")
    metadata = supported.get(action)
    if not isinstance(metadata, dict):
        raise ValidationError(f"unsupported action: {action}")
    return action, metadata


def validate_actions(task: dict[str, Any], capabilities: dict[str, Any]) -> list[str]:
    canonical_actions: list[str] = []
    for raw_action in as_list(task.get("allowed_actions"), "allowed_actions"):
        if not isinstance(raw_action, str) or not raw_action.strip():
            raise ValidationError("allowed_actions entries must be non-empty strings")
        canonical, metadata = resolve_action(raw_action.strip(), capabilities)
        if not bool(metadata.get("implemented")):
            raise ValidationError(f"action is not implemented: {raw_action}")
        canonical_actions.append(canonical)
    if not canonical_actions:
        raise ValidationError("allowed_actions cannot be empty")
    if len(canonical_actions) != len(set(canonical_actions)):
        raise ValidationError("allowed_actions must not contain duplicates")
    return canonical_actions


def validate_inputs(task: dict[str, Any], vault_root: Path) -> None:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict):
        raise ValidationError("inputs must be a mapping")

    for key, value in inputs.items():
        if key == "compare_video_paths":
            if not isinstance(value, list):
                raise ValidationError("inputs.compare_video_paths must be a list")
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise ValidationError("inputs.compare_video_paths entries must be text")
                path = Path(item).expanduser()
                if path.is_absolute():
                    if not path.exists() or not path.is_file():
                        raise ValidationError(f"inputs.compare_video_paths entry does not exist: {path}")
                elif not (vault_root / vault_relative_path(item, vault_root)).exists():
                    raise ValidationError(f"inputs.compare_video_paths entry does not exist under vault root: {item}")
            continue
        if not key.endswith("_path") or key == "local_project_path":
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"inputs.{key} must be text")
        if key in {"output_video_path", "content_os_link_path"}:
            path = Path(value).expanduser()
            if path.is_absolute():
                if not path.exists() or not path.is_file():
                    raise ValidationError(f"inputs.{key} does not exist: {path}")
                continue
        path = vault_relative_path(value, vault_root)
        if not (vault_root / path).exists():
            raise ValidationError(f"inputs.{key} does not exist under vault root: {value}")

    local_project_path = inputs.get("local_project_path")
    if local_project_path is not None:
        if not isinstance(local_project_path, str) or not local_project_path.strip():
            raise ValidationError("inputs.local_project_path must be text")
        path = Path(local_project_path).expanduser()
        if not path.is_absolute():
            raise ValidationError("inputs.local_project_path must be an absolute Mac path")
        if not path.exists() or not path.is_dir():
            raise ValidationError(f"inputs.local_project_path does not exist: {path}")


def is_revision_scoped_local_editor_output(task: dict[str, Any], output: str) -> bool:
    """Accept only the fixed local editor-output notation used by v0.2 tasks."""

    if task.get("task_type") not in LOCAL_EDITOR_OUTPUT_TASK_TYPES:
        return False
    path = Path(output)
    expected_prefix = ("90_Draft_Project", "edit_handoff", str(task["project_revision"]))
    return not path.is_absolute() and len(path.parts) > len(expected_prefix) and path.parts[:3] == expected_prefix


def validate_expected_outputs(task: dict[str, Any], vault_root: Path) -> None:
    expected_outputs = as_list(task.get("expected_outputs"), "expected_outputs")
    if not expected_outputs:
        raise ValidationError("expected_outputs cannot be empty")
    for output in expected_outputs:
        if not isinstance(output, str) or not output.strip():
            raise ValidationError("expected_outputs entries must be non-empty strings")
        if is_revision_scoped_local_editor_output(task, output):
            continue
        path = vault_relative_path(output, vault_root)
        parent = (vault_root / path).parent
        if not parent.exists():
            raise ValidationError(f"expected output parent directory does not exist: {output}")


def project_overview_path(vault_root: Path, project_id: str) -> Path:
    return vault_root / "08_内容项目" / project_id / PROJECT_OVERVIEW


def validate_project_identity(task: dict[str, Any], vault_root: Path) -> dict[str, Any]:
    project_id = require_text(task, "project_id")
    overview = load_markdown_frontmatter(project_overview_path(vault_root, project_id))
    if require_text(overview, "spec_version") != SPEC_VERSION:
        raise ValidationError("project overview.spec_version must be content_os_v0.2")
    if require_text(overview, "project_id") != project_id:
        raise ValidationError("project overview project_id does not match task.project_id")
    task_revision = require_positive_int(task, "project_revision")
    overview_revision = require_positive_int(overview, "project_revision")
    if task_revision != overview_revision:
        raise ValidationError(
            f"stale project_revision: task={task_revision}, current={overview_revision}"
        )
    backend = require_text(task, "editor_backend")
    if backend not in SUPPORTED_EDITOR_BACKENDS:
        raise ValidationError(f"unknown editor_backend: {backend}")
    overview_backend = require_text(overview, "editor_backend")
    if overview_backend != backend:
        raise ValidationError(
            f"editor_backend does not match project overview: task={backend}, current={overview_backend}"
        )
    return overview


def validate_backend_capability(task: dict[str, Any], capabilities: dict[str, Any]) -> None:
    backend = require_text(task, "editor_backend")
    editor_backends = capabilities.get("editor_backends")
    if not isinstance(editor_backends, dict):
        raise ValidationError("capabilities.editor_backends must be a mapping")
    supported = editor_backends.get("supported")
    if not isinstance(supported, dict):
        raise ValidationError("capabilities.editor_backends.supported must be a mapping")
    metadata = supported.get(backend)
    if not isinstance(metadata, dict) or not bool(metadata.get("implemented")):
        raise ValidationError(f"editor_backend is not implemented: {backend}")
    expected_backend = BACKEND_TASK_TYPES.get(require_text(task, "task_type"))
    if expected_backend and backend != expected_backend:
        raise ValidationError(
            f"task_type {task['task_type']} requires editor_backend={expected_backend}, got {backend}"
        )
    if task.get("allow_editor_backend_fallback") is not None or task.get("fallback_editor_backend") is not None:
        raise ValidationError("editor backend fallback fields are forbidden")
    if task.get("fallback_used") is True:
        raise ValidationError("fallback_used must not be true")


def change_request_path(vault_root: Path, change_request_id: str) -> Path:
    return vault_root / "98_Agent任务队列" / "00_change_requests" / f"{change_request_id}.yaml"


def validate_change_request(task: dict[str, Any], vault_root: Path) -> str | None:
    value = task.get("change_request_id")
    if value is None or value == "":
        if require_text(task, "task_type") in REVISION_TASK_TYPES:
            raise ValidationError("revise_local_edit_artifacts requires change_request_id")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("change_request_id must be text when provided")
    change_request_id = value.strip()
    require_true(task, "human_confirmed_impact")
    request = load_yaml(change_request_path(vault_root, change_request_id))
    if require_text(request, "spec_version") != SPEC_VERSION:
        raise ValidationError("change request.spec_version must be content_os_v0.2")
    if require_text(request, "doc_type") != "content_revision_request":
        raise ValidationError("change request.doc_type must be content_revision_request")
    if require_text(request, "change_id") != change_request_id:
        raise ValidationError("change request.change_id does not match task.change_request_id")
    if require_text(request, "project_id") != require_text(task, "project_id"):
        raise ValidationError("change request project_id does not match task.project_id")
    if require_text(request, "assigned_owner") != "mac_openclaw":
        raise ValidationError("change request is not assigned to mac_openclaw")
    if require_text(request, "request_status") != "executing":
        raise ValidationError("change request must be executing before Mac execution")
    if require_text(request, "execution_intent") == "note_only":
        raise ValidationError("note_only change request cannot create a Mac task")
    if not request.get("execution_confirmed_at"):
        raise ValidationError("change request requires execution_confirmed_at")
    if require_positive_int(request, "target_revision") != require_positive_int(task, "project_revision"):
        raise ValidationError("change request.target_revision does not match task.project_revision")
    if require_positive_int(request, "base_revision") >= require_positive_int(request, "target_revision"):
        raise ValidationError("change request.target_revision must be greater than base_revision")
    return change_request_id


def validate_project_package_inputs(task: dict[str, Any], vault_root: Path) -> None:
    if require_text(task, "task_type") != "local_material_match":
        return
    project_id = require_text(task, "project_id")
    project_dir = vault_root / "08_内容项目" / project_id
    if not project_dir.exists() or not project_dir.is_dir():
        raise ValidationError(f"project package does not exist for project_id: {project_id}")
    script = project_dir / "04_script.md"
    if not script.exists() or script.stat().st_size == 0:
        raise ValidationError(f"local_material_match requires project package script: 08_内容项目/{project_id}/04_script.md")


def validate_task(task: dict[str, Any], capabilities: dict[str, Any], vault_root: Path) -> dict[str, Any]:
    if require_text(task, "spec_version") != SPEC_VERSION:
        raise ValidationError("task.spec_version must be content_os_v0.2")
    task_id = require_text(task, "task_id")
    task_type = require_text(task, "task_type")
    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValidationError(f"unsupported task_type: {task_type}")
    require_text(task, "project_id")
    require_text(task, "idea_id")
    if require_text(task, "owner") != "mac_openclaw":
        raise ValidationError("task.owner must be mac_openclaw for local runner tasks")
    if require_text(task, "status") != "ready":
        raise ValidationError("task.status must be ready before execution")

    overview = validate_project_identity(task, vault_root)
    validate_backend_capability(task, capabilities)
    change_request_id = validate_change_request(task, vault_root)
    canonical_actions = validate_actions(task, capabilities)
    validate_inputs(task, vault_root)
    validate_expected_outputs(task, vault_root)
    validate_project_package_inputs(task, vault_root)

    return {
        "status": "valid",
        "task_id": task_id,
        "task_type": task_type,
        "project_id": task["project_id"],
        "project_revision": task["project_revision"],
        "change_request_id": change_request_id,
        "editor_backend": task["editor_backend"],
        "project_status_observed": overview.get("status"),
        "canonical_actions": canonical_actions,
    }


def write_blocked_result(path: Path, task: dict[str, Any], reason: str) -> None:
    result = {
        "spec_version": SPEC_VERSION,
        "task_id": task.get("task_id", "unknown_task"),
        "task_type": task.get("task_type", "unknown_task_type"),
        "completed_by": "mac_openclaw",
        "status": "blocked",
        "blocked_reason": "invalid_task_contract",
        "detail": reason,
        "project_id": task.get("project_id"),
        "project_revision": task.get("project_revision"),
        "change_request_id": task.get("change_request_id") or None,
        "editor_backend": task.get("editor_backend"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(result, handle, allow_unicode=True, sort_keys=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, type=Path)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--blocked-result-out", type=Path)
    args = parser.parse_args()

    try:
        task = load_yaml(args.task)
        capabilities = load_yaml(args.capabilities)
        summary = validate_task(task, capabilities, args.vault_root.expanduser().resolve())
    except ValidationError as exc:
        if args.blocked_result_out:
            try:
                task_data = load_yaml(args.task) if args.task.exists() else {}
            except ValidationError:
                task_data = {}
            write_blocked_result(args.blocked_result_out, task_data, str(exc))
        print(f"blocked: {exc}", file=sys.stderr)
        return 1

    yaml.safe_dump(summary, sys.stdout, allow_unicode=True, sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
