#!/usr/bin/env python3
"""Strict local runner for Mac OpenClaw Content OS tasks.

The runner intentionally accepts only known task types and maps each action to
fixed local scripts. It never executes commands from a task file.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from runtime_paths import obsidian_root, runtime_python
from validate_content_os_task import (
    ValidationError,
    load_yaml as load_validator_yaml,
    validate_task,
    write_blocked_result,
)


SCRIPT_DIR = Path(__file__).resolve().parent
SYSTEM_ROOT = SCRIPT_DIR.parent
WORKSPACE_ROOT = SYSTEM_ROOT.parent if SYSTEM_ROOT.name == "99_System_OpenClaw" else SYSTEM_ROOT
DEFAULT_VAULT_ROOT = obsidian_root()

TASK_INBOX = Path("98_Agent任务队列/01_cloud_to_mac_ready")
RESULT_OUTBOX = Path("98_Agent任务队列/02_mac_to_cloud_results")
CAPABILITIES = Path("00_入口与总览/mac_runner_capabilities.yaml")
REQUIRED_CREATIVE_MODEL = "gpt-5.6-terra"
REQUIRED_CREATIVE_REASONING = "xhigh"
REQUIRED_CREATIVE_PROVIDER = "codex_cli"
CONTENT_OS_SPEC_VERSION = "content_os_v0.2"
OTIO_KDENLIVE_PYTHON = runtime_python(WORKSPACE_ROOT)

REQUIRED_ACTIONS = {
    "local_material_match": [
        "analyze_project",
        "match_materials_to_brief",
        "generate_storyboard_edl",
        "write_local_assets",
    ],
    "generate_edit_handoff_pack": [
        "generate_edit_handoff_pack",
        "validate_edit_handoff_pack",
    ],
    "generate_otio_kdenlive_timeline": [
        "generate_otio_timeline",
        "create_kdenlive_timeline",
        "validate_kdenlive_timeline",
    ],
    "revise_local_edit_artifacts": [
        "apply_confirmed_revision",
    ],
    "generate_ai_edit_log": [
        "generate_ai_edit_log",
    ],
    "local_output_review": [
        "review_output_video",
    ],
}


class RunnerError(Exception):
    """Raised when the runner cannot safely execute a task."""


def task_identity(task: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable identity that every Mac result must echo.

    Cloud verifies this tuple before accepting any evidence.  Keeping it in one
    helper prevents a new result writer from accidentally omitting revision or
    backend and thereby becoming impossible to reconcile safely.
    """

    identity = {
        "spec_version": CONTENT_OS_SPEC_VERSION,
        "doc_type": "mac_result",
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "completed_by": "mac_openclaw",
        "project_id": task["project_id"],
        "project_revision": task["project_revision"],
        "change_request_id": task.get("change_request_id") or None,
        "editor_backend": task["editor_backend"],
    }
    tenant_id = task.get("tenant_id")
    if isinstance(tenant_id, str) and tenant_id.strip():
        identity["tenant_id"] = tenant_id.strip()
    return identity


def script_path(name: str) -> str:
    return str(SCRIPT_DIR / name)


@dataclass(frozen=True)
class RunnerConfig:
    vault_root: Path
    workspace_root: Path

    @property
    def task_inbox(self) -> Path:
        return self.vault_root / TASK_INBOX

    @property
    def result_outbox(self) -> Path:
        return self.vault_root / RESULT_OUTBOX

    @property
    def capabilities_path(self) -> Path:
        return self.vault_root / CAPABILITIES


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RunnerError(f"YAML file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise RunnerError(f"YAML root must be a mapping: {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, allow_unicode=True, sort_keys=False)


def vault_abs(config: RunnerConfig, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise RunnerError(f"Obsidian task path must be vault-relative: {value}")
    return config.vault_root / path


def vault_rel(config: RunnerConfig, path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(config.vault_root.resolve()))
    except ValueError:
        return str(resolved)


def run_command(args: list[str], cwd: Path = WORKSPACE_ROOT) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(args)}")
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise RunnerError(f"command failed ({result.returncode}): {shlex.join(args)}")
    return result


def otio_kdenlive_python() -> str:
    """Return the sole approved interpreter for the optional OTIO backend.

    The regular Mac Runner interpreter intentionally stays independent from
    OpenTimelineIO.  This avoids an accidental global-package dependency and,
    more importantly, makes a missing OTIO environment a visible blocked task
    instead of silently invoking another editor adapter or the system Python.
    """

    if not OTIO_KDENLIVE_PYTHON.is_file() or not OTIO_KDENLIVE_PYTHON.stat().st_mode & 0o111:
        raise RunnerError(
            "otio_kdenlive runtime is unavailable: expected "
            f"{OTIO_KDENLIVE_PYTHON}; task is blocked and no fallback backend will be used"
        )
    probe = subprocess.run(
        [str(OTIO_KDENLIVE_PYTHON), "-c", "import opentimelineio; print(opentimelineio.__version__)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        detail = probe.stderr.strip() or "cannot import opentimelineio"
        raise RunnerError(
            "otio_kdenlive runtime is unavailable: required OpenTimelineIO is missing or broken "
            f"({detail}); task is blocked and no fallback backend will be used"
        )
    return str(OTIO_KDENLIVE_PYTHON)


def write_execution_blocked_result(path: Path, task: dict[str, Any], reason: str) -> None:
    result = {
        "spec_version": CONTENT_OS_SPEC_VERSION,
        "doc_type": "mac_result",
        "task_id": task.get("task_id", "unknown_task"),
        "task_type": task.get("task_type", "unknown_task_type"),
        "completed_by": "mac_openclaw",
        "status": "blocked",
        "blocked_reason": "execution_contract_failed",
        "detail": reason,
        "project_id": task.get("project_id"),
        "project_revision": task.get("project_revision"),
        "change_request_id": task.get("change_request_id") or None,
        "editor_backend": task.get("editor_backend"),
        "idea_id": task.get("idea_id"),
        "generation_provider_required": REQUIRED_CREATIVE_PROVIDER if task.get("task_type") == "local_material_match" else None,
        "generation_model_required": REQUIRED_CREATIVE_MODEL if task.get("task_type") == "local_material_match" else None,
        "generation_reasoning_required": REQUIRED_CREATIVE_REASONING if task.get("task_type") == "local_material_match" else None,
        "fallback_used": False,
    }
    tenant_id = task.get("tenant_id")
    if isinstance(tenant_id, str) and tenant_id.strip():
        result["tenant_id"] = tenant_id.strip()
    write_yaml(path, result)


def task_files(config: RunnerConfig) -> list[Path]:
    if not config.task_inbox.exists():
        return []
    return sorted(config.task_inbox.glob("*.yaml"))


def result_path_for(config: RunnerConfig, task_path: Path, task: dict[str, Any]) -> Path:
    name = task_path.name
    if name.startswith("task_"):
        result_name = "result_" + name[len("task_") :]
    else:
        result_name = f"result_{task.get('task_id', 'unknown')}_{task.get('task_type', 'unknown')}.yaml"
    return config.result_outbox / result_name


def resolve_task_ref(config: RunnerConfig, ref: str) -> Path:
    candidate = Path(ref).expanduser()
    if candidate.exists():
        return candidate.resolve()

    matches: list[Path] = []
    for path in task_files(config):
        try:
            task = load_yaml(path)
        except RunnerError:
            continue
        task_id = str(task.get("task_id", ""))
        if ref in {task_id, path.stem, path.name}:
            matches.append(path)
        elif ref and ref in task_id:
            matches.append(path)

    if not matches:
        raise RunnerError(f"task not found: {ref}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise RunnerError(f"task reference is ambiguous: {ref} -> {names}")
    return matches[0]


def validate_required_actions(task: dict[str, Any], canonical_actions: list[str]) -> None:
    task_type = str(task.get("task_type", ""))
    required = REQUIRED_ACTIONS.get(task_type)
    if required is None:
        raise RunnerError(f"unsupported task_type for Mac runner: {task_type}")
    missing = [action for action in required if action not in canonical_actions]
    if missing:
        raise RunnerError(f"task missing required allowed_actions for {task_type}: {', '.join(missing)}")
    unexpected = [action for action in canonical_actions if action not in required]
    if unexpected:
        raise RunnerError(f"task has disallowed actions for {task_type}: {', '.join(unexpected)}")


def validate_or_block(config: RunnerConfig, task_path: Path) -> tuple[dict[str, Any], Path, list[str]]:
    try:
        task = load_validator_yaml(task_path)
    except ValidationError as exc:
        raise RunnerError(str(exc)) from exc

    result_path = result_path_for(config, task_path, task)
    try:
        capabilities = load_validator_yaml(config.capabilities_path)
        summary = validate_task(task, capabilities, config.vault_root.resolve())
        canonical_actions = list(summary["canonical_actions"])
        validate_required_actions(task, canonical_actions)
    except (ValidationError, RunnerError) as exc:
        write_blocked_result(result_path, task, str(exc))
        raise RunnerError(f"task blocked, result written to {result_path}: {exc}") from exc
    return task, result_path, canonical_actions


def expected_output(config: RunnerConfig, task: dict[str, Any], filename: str) -> Path:
    for raw in task.get("expected_outputs") or []:
        if Path(str(raw)).name == filename:
            return vault_abs(config, str(raw))
    raise RunnerError(f"expected output not declared: {filename}")


def input_path(config: RunnerConfig, task: dict[str, Any], key: str) -> Path:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict) or key not in inputs:
        raise RunnerError(f"missing task input: {key}")
    return vault_abs(config, str(inputs[key]))


def input_file_path(config: RunnerConfig, task: dict[str, Any], key: str) -> Path:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict) or key not in inputs:
        raise RunnerError(f"missing task input: {key}")
    raw = str(inputs[key]).strip()
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (config.vault_root / path).resolve()


def optional_input_file_path(config: RunnerConfig, task: dict[str, Any], key: str) -> Path | None:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict) or key not in inputs:
        return None
    value = inputs.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (config.vault_root / path).resolve()


def optional_input_file_list(config: RunnerConfig, task: dict[str, Any], key: str) -> list[Path]:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict):
        return []
    values = inputs.get(key)
    if values is None:
        return []
    if not isinstance(values, list):
        raise RunnerError(f"inputs.{key} must be a list")
    paths = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise RunnerError(f"inputs.{key} entries must be non-empty strings")
        path = Path(value).expanduser()
        paths.append(path.resolve() if path.is_absolute() else (config.vault_root / path).resolve())
    return paths


def project_package_dir(config: RunnerConfig, task: dict[str, Any]) -> Path:
    project_id = str(task.get("project_id") or "").strip()
    if not project_id:
        raise RunnerError("task.project_id is required")
    path = config.vault_root / "08_内容项目" / project_id
    if not path.exists() or not path.is_dir():
        raise RunnerError(f"Content OS project package does not exist: {path}")
    return path


def project_standard_file(config: RunnerConfig, task: dict[str, Any], filename: str) -> Path:
    path = project_package_dir(config, task) / filename
    if not path.exists() or path.stat().st_size == 0:
        raise RunnerError(f"required project package file missing or empty: {path}")
    return path


def content_os_link_input(config: RunnerConfig, task: dict[str, Any]) -> Path | None:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict):
        return None
    value = inputs.get("content_os_link_path")
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (config.vault_root / path).resolve()


def validate_content_os_link(config: RunnerConfig, task: dict[str, Any], project_dir: Path) -> Path | None:
    path = content_os_link_input(config, task)
    if path is None:
        return None
    data = load_yaml(path)
    if data.get("doc_type") != "content_os_link":
        raise RunnerError(f"content_os_link_path must point to doc_type=content_os_link: {path}")
    obsidian = data.get("obsidian")
    if not isinstance(obsidian, dict):
        raise RunnerError(f"content_os_link.obsidian must be a mapping: {path}")
    if str(obsidian.get("project_id") or "") != str(task.get("project_id") or ""):
        raise RunnerError("content_os_link project_id does not match task.project_id")
    validation = data.get("validation")
    if not isinstance(validation, dict):
        raise RunnerError(f"content_os_link.validation must be a mapping: {path}")
    if validation.get("missing_required_files"):
        raise RunnerError(f"content_os_link still has missing required files: {path}")
    batch = data.get("batch")
    if not isinstance(batch, dict):
        raise RunnerError(f"content_os_link.batch must be a mapping: {path}")
    resolved_project = str(batch.get("target_project_resolved") or "").strip()
    if resolved_project and Path(resolved_project).expanduser().resolve() != project_dir.resolve():
        raise RunnerError("content_os_link target_project_resolved does not match local project path")
    return path


def find_project_by_id(config: RunnerConfig, project_id: str) -> Path:
    index_path = config.workspace_root / "01_Project_Workspace" / ".content_os_project_index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        indexed = Path(str(index.get(project_id, ""))).expanduser()
        if indexed.is_dir() and indexed.resolve().parent == (config.workspace_root / "01_Project_Workspace").resolve():
            return indexed.resolve()
    except (OSError, ValueError, AttributeError):
        pass
    roots = [config.workspace_root / "01_Project_Workspace"]
    matches: list[Path] = []
    for root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob(project_id):
            if path.is_dir():
                matches.append(path.resolve())
    unique = sorted({path for path in matches})
    if not unique:
        raise RunnerError(f"local project directory not found for project_id/local_project_hint: {project_id}")
    if len(unique) > 1:
        names = ", ".join(str(path) for path in unique)
        raise RunnerError(f"local project directory is ambiguous for {project_id}: {names}")
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        if not isinstance(index, dict):
            index = {}
        index[project_id] = str(unique[0])
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return unique[0]


def local_project_path(config: RunnerConfig, task: dict[str, Any]) -> Path:
    inputs = task.get("inputs")
    if not isinstance(inputs, dict):
        raise RunnerError("task.inputs must be a mapping")
    value = str(inputs.get("local_project_path") or "").strip()
    if value:
        path = Path(value).expanduser()
        if not path.exists() or not path.is_dir():
            raise RunnerError(f"local_project_path does not exist: {path}")
        return path
    hint = str(inputs.get("local_project_hint") or task.get("project_id") or "").strip()
    if not hint:
        raise RunnerError("missing task input: local_project_path, local_project_hint, or project_id")
    return find_project_by_id(config, hint)


def require_nonempty(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RunnerError(f"required output missing or empty: {path}")


def require_json(path: Path) -> None:
    require_nonempty(path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RunnerError(f"JSON root must be an object: {path}")


def write_local_assets(path: Path, task: dict[str, Any], project_dir: Path, edl_path: Path) -> None:
    candidates: list[dict[str, str]] = []
    if edl_path.exists():
        with edl_path.open("r", encoding="utf-8") as handle:
            edl = json.load(handle)
        for clip in edl.get("clips") or []:
            if not isinstance(clip, dict):
                continue
            files = clip.get("candidate_files") or []
            first = str(files[0]) if files else ""
            candidates.append(
                {
                    "file": first,
                    "purpose": str(clip.get("purpose", "")),
                    "note": str(clip.get("edit_note", "")),
                }
            )

    rows = "\n".join(
        f"| {item['file']} | {item['purpose']} | {item['note']} |" for item in candidates if item["file"]
    )
    if not rows:
        rows = "|  | 待人工确认 | EDL 未提供候选素材 |"

    text = f"""---
spec_version: content_os_v0.2
doc_type: local_assets
project_id: {task.get("project_id", "")}
idea_id: {task.get("idea_id", "")}
project_revision: {task.get("project_revision", "")}
change_request_id: {task.get("change_request_id") or ""}
editor_backend: {task.get("editor_backend", "")}
writer_agent: mac_openclaw
owner_agent: mac_openclaw
status: local_assets_recorded
---

# 本地项目路径

```text
{project_dir}
```

# AI 分析文件

```text
_ai_analysis/media_manifest.json
_ai_analysis/keyframes/
_ai_analysis/prompts/
_ai_analysis/summaries/
_ai_analysis/project_overview.md
```

# 剪辑工程区

```text
90_Draft_Project/
```

# 输出区

```text
91_Output/V1
91_Output/V2
91_Output/Final
```

# WorkCache

```text
App_WorkCache/
```

# 本次建议进入剪辑的素材

| 素材 | 用途 | 备注 |
|---|---|---|
{rows}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_runtime_check(skip: bool, task_type: str) -> None:
    if skip:
        return
    command = ["env", f"PYTHON_BIN={OTIO_KDENLIVE_PYTHON}", "bash", script_path("check_runtime_contract.sh")]
    if task_type not in {"generate_otio_kdenlive_timeline"}:
        command.append("--skip-package-pins")
    run_command(command)


def local_material_match_result(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    tools_used: dict[str, str],
    project_dir: Path,
    content_os_link: Path | None,
) -> None:
    report = expected_output(config, task, "03_material_match_report.md")
    storyboard = expected_output(config, task, "05_storyboard.md")
    edl = expected_output(config, task, "06_edit_decision_list.json")
    local_assets = expected_output(config, task, "08_local_assets.md")
    source_script = project_standard_file(config, task, "04_script.md")
    for path in [report, storyboard, local_assets]:
        require_nonempty(path)
    require_json(edl)
    edl_data = json.loads(edl.read_text(encoding="utf-8"))
    if not edl_data.get("source_script_used"):
        raise RunnerError("EDL must declare source_script_used: true")
    if edl_data.get("generation_model") != REQUIRED_CREATIVE_MODEL:
        raise RunnerError(f"EDL generation_model must be {REQUIRED_CREATIVE_MODEL}")
    if edl_data.get("generation_reasoning") != REQUIRED_CREATIVE_REASONING:
        raise RunnerError(f"EDL generation_reasoning must be {REQUIRED_CREATIVE_REASONING}")

    result = {
        **task_identity(task),
        "status": "done",
        "idea_id": task["idea_id"],
        "outputs": {
            "material_match_report": vault_rel(config, report),
            "storyboard": vault_rel(config, storyboard),
            "edit_decision_list": vault_rel(config, edl),
            "local_assets": vault_rel(config, local_assets),
        },
        "local_outputs": {
            "local_project_path": str(project_dir),
            "content_os_link": str(content_os_link) if content_os_link else "",
            "media_manifest": str(project_dir / "_ai_analysis" / "media_manifest.json"),
        },
        "source_script": vault_rel(config, source_script),
        "source_script_used": True,
        "generation_provider": REQUIRED_CREATIVE_PROVIDER,
        "generation_model": REQUIRED_CREATIVE_MODEL,
        "generation_reasoning": REQUIRED_CREATIVE_REASONING,
        "fallback_used": False,
        "tools_used": tools_used,
        "validation": {
            "material_match_report_nonempty": True,
            "storyboard_nonempty": True,
            "edl_json_parse_passed": True,
            "local_assets_nonempty": True,
            "source_script_used": True,
            "required_model_used": True,
            "content_os_link_validated": bool(content_os_link),
        },
        "notes": [
            "Mac Runner executed only whitelisted actions.",
            "Cloud OpenClaw must continue from Mac-written outputs and result YAML, not inferred Mac directories.",
            "This result does not advance the project stage; Cloud verifies evidence before changing the project overview.",
        ],
    }
    write_yaml(result_path, result)


def run_local_material_match(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
    skip_analyze: bool,
) -> None:
    project_dir = local_project_path(config, task)
    content_os_link = validate_content_os_link(config, task, project_dir)
    brief = optional_input_file_path(config, task, "project_brief_path") or project_standard_file(config, task, "02_project_brief.md")
    script = project_standard_file(config, task, "04_script.md")
    report = expected_output(config, task, "03_material_match_report.md")
    storyboard = expected_output(config, task, "05_storyboard.md")
    edl = expected_output(config, task, "06_edit_decision_list.json")
    local_assets = expected_output(config, task, "08_local_assets.md")
    tools_used: dict[str, str] = {}

    if execute:
        if skip_analyze:
            manifest = project_dir / "_ai_analysis" / "media_manifest.json"
            if not manifest.exists() or manifest.stat().st_size == 0:
                raise RunnerError(f"--skip-analyze requires existing media manifest: {manifest}")
            tools_used["analyze_project"] = "skipped_existing_media_manifest"
        else:
            run_command(["bash", script_path("run_analyze_project.sh"), str(project_dir), "--audio", "--transcript-provider", task.get("transcript_provider", "openai_api")])
            tools_used["analyze_project"] = script_path("run_analyze_project.sh")

        run_command(
            [
                sys.executable,
                script_path("17_match_materials_to_brief.py"),
                str(project_dir),
                "--brief",
                str(brief),
                "--output",
                str(report),
                "--script",
                str(script),
                "--model",
                REQUIRED_CREATIVE_MODEL,
                "--reasoning",
                REQUIRED_CREATIVE_REASONING,
            ]
        )
        tools_used["match_materials_to_brief"] = script_path("17_match_materials_to_brief.py")

        run_command(
            [
                sys.executable,
                script_path("18_generate_storyboard_edl.py"),
                str(project_dir),
                "--brief",
                str(brief),
                "--material-report",
                str(report),
                "--storyboard-output",
                str(storyboard),
                "--edl-output",
                str(edl),
                "--script",
                str(script),
                "--model",
                REQUIRED_CREATIVE_MODEL,
                "--reasoning",
                REQUIRED_CREATIVE_REASONING,
            ]
        )
        tools_used["generate_storyboard_edl"] = script_path("18_generate_storyboard_edl.py")

        write_local_assets(local_assets, task, project_dir, edl)
        tools_used["write_local_assets"] = str(Path(__file__).resolve())
    else:
        tools_used["write_result"] = "existing_outputs"

    local_material_match_result(config, task, result_path, tools_used, project_dir, content_os_link)


def ai_edit_log_result(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    tools_used: dict[str, str],
) -> None:
    edit_log = expected_output(config, task, "07_edit_log.md")
    require_nonempty(edit_log)
    text = edit_log.read_text(encoding="utf-8")
    try:
        end = text.find("\n---", 4)
        frontmatter = yaml.safe_load(text[4:end]) if text.startswith("---\n") and end > 0 else {}
    except yaml.YAMLError as exc:
        raise RunnerError("07_edit_log.md frontmatter is invalid YAML") from exc
    if not isinstance(frontmatter, dict) or frontmatter.get("doc_type") != "edit_log":
        raise RunnerError("07_edit_log.md must declare doc_type: edit_log")
    if frontmatter.get("generation_model") != REQUIRED_CREATIVE_MODEL:
        raise RunnerError(f"07_edit_log.md must declare generation_model: {REQUIRED_CREATIVE_MODEL}")
    if frontmatter.get("generation_reasoning") != REQUIRED_CREATIVE_REASONING:
        raise RunnerError("07_edit_log.md must declare generation_reasoning: xhigh")

    result = {
        **task_identity(task),
        "status": "done",
        "idea_id": task["idea_id"],
        "outputs": {
            "edit_log": vault_rel(config, edit_log),
        },
        "generation_provider": REQUIRED_CREATIVE_PROVIDER,
        "generation_model": REQUIRED_CREATIVE_MODEL,
        "generation_reasoning": REQUIRED_CREATIVE_REASONING,
        "fallback_used": False,
        "tools_used": tools_used,
        "validation": {
            "edit_log_nonempty": True,
            "doc_type_edit_log": True,
            "required_model_used": True,
            "separates_confirmed_and_inferred_changes": "# AI 推断修改" in text and "# 已确认人工修改" in text,
        },
        "notes": [
            "This edit log is generated from Content OS artifacts unless a human-confirmed note or exported video is provided.",
            "AI-inferred edits must be human-confirmed before they are treated as facts.",
            "This result does not advance the project stage.",
        ],
    }
    write_yaml(result_path, result)


def output_review_expected_report(config: RunnerConfig, task: dict[str, Any]) -> Path:
    for raw in task.get("expected_outputs") or []:
        path = vault_abs(config, str(raw))
        if path.name.endswith("_output_review.md") or path.name == f"{task['project_id']}_output_review.md":
            return path
    raise RunnerError("expected output not declared: *_output_review.md")


def output_review_result(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    local_result_path: Path,
    tools_used: dict[str, str],
) -> None:
    summary = load_yaml(local_result_path)
    report = Path(str(summary.get("report_path", "")))
    if not report.is_absolute():
        report = config.vault_root / report
    metrics = Path(str(summary.get("metrics_path", "")))
    contact_sheet = str(summary.get("contact_sheet_path", ""))
    scene_sheet = str(summary.get("scene_change_sheet_path", ""))
    if not metrics.is_absolute():
        metrics = local_project_path(config, task) / metrics
    require_nonempty(report)
    require_json(metrics)
    result = {
        **task_identity(task),
        "schema_version": "output_review_result.v1",
        "status": "done" if summary.get("task_status") == "success" else summary.get("task_status", "blocked"),
        "idea_id": task["idea_id"],
        "task_status": summary.get("task_status", "unknown"),
        "technical_status": summary.get("technical_status", "unknown"),
        "preferred_version": summary.get("preferred_version", "current"),
        "current_brief_fit": summary.get("current_brief_fit", "unknown"),
        "brief_fit_method": summary.get("brief_fit_method", "metadata_only"),
        "brief_fit_confidence": summary.get("brief_fit_confidence", "low"),
        "recommendation": summary.get("recommendation", "small_fix"),
        "publish_as_final": bool(summary.get("publish_as_final")),
        "human_decision_required": bool(summary.get("human_decision_required", True)),
        "reason": summary.get("reason", ""),
        "next_owner": summary.get("next_owner", "human_editor"),
        "risk_flags": summary.get("risk_flags") or [],
        "outputs": {
            "output_review": vault_rel(config, report),
        },
        "local_outputs": {
            "metrics": str(metrics),
            "contact_sheet": contact_sheet,
            "scene_change_sheet": scene_sheet,
        },
        "tools_used": tools_used,
        "validation": {
            "output_review_nonempty": True,
            "metrics_json_parse_passed": True,
            "result_yaml_parse_passed": True,
            "human_final_ready_confirmation_required": True,
        },
        "notes": [
            "Mac runner generated local output-review evidence only.",
            "Final selection and project-stage changes remain human decisions.",
        ],
    }
    write_yaml(result_path, result)


def backend_source_files(config: RunnerConfig, task: dict[str, Any]) -> tuple[Path, Path]:
    """Resolve the two source artifacts shared by both editor backends."""

    project_dir = project_package_dir(config, task)
    edl = optional_input_file_path(config, task, "edl_path") or project_standard_file(
        config, task, "06_edit_decision_list.json"
    )
    storyboard = optional_input_file_path(config, task, "storyboard_path") or project_standard_file(
        config, task, "05_storyboard.md"
    )
    return edl, storyboard


def backend_output_root(config: RunnerConfig, task: dict[str, Any]) -> Path:
    """Return the revision-scoped local handoff root without creating it."""

    return local_project_path(config, task) / "90_Draft_Project" / "edit_handoff"


def write_confirmed_revision_basis(config: RunnerConfig, task: dict[str, Any]) -> Path | None:
    """Persist a confirmed request so its selected backend can verify the basis."""

    if task.get("task_type") != "revise_local_edit_artifacts":
        return None
    change_request_id = str(task.get("change_request_id") or "").strip()
    if not change_request_id:
        raise RunnerError("revision task requires change_request_id")
    inputs = task.get("inputs")
    summary = inputs.get("change_summary") if isinstance(inputs, dict) else None
    if not isinstance(summary, dict):
        raise RunnerError("revision task requires inputs.change_summary")
    required = ("requested_location", "requested_change", "reason")
    if any(not isinstance(summary.get(key), str) or not summary[key].strip() for key in required):
        raise RunnerError("revision change_summary is incomplete")
    references = summary.get("references", [])
    if not isinstance(references, list) or any(not isinstance(item, str) for item in references):
        raise RunnerError("revision change_summary.references must be a text list")
    basis = {
        "spec_version": CONTENT_OS_SPEC_VERSION,
        "doc_type": "confirmed_revision_basis",
        "project_id": task["project_id"],
        "project_revision": task["project_revision"],
        "change_request_id": change_request_id,
        "editor_backend": task["editor_backend"],
        "change_summary": {
            "requested_location": summary["requested_location"].strip(),
            "requested_change": summary["requested_change"].strip(),
            "reason": summary["reason"].strip(),
            "urgency": str(summary.get("urgency") or "").strip(),
            "references": [item.strip() for item in references if item.strip()],
        },
    }
    path = (
        local_project_path(config, task)
        / "90_Draft_Project"
        / "revision_basis"
        / str(task["project_revision"])
        / f"{change_request_id}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(basis, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def require_json_identity(path: Path, task: dict[str, Any], expected_doc_type: str) -> dict[str, Any]:
    require_json(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("spec_version") != CONTENT_OS_SPEC_VERSION:
        raise RunnerError(f"backend result must use {CONTENT_OS_SPEC_VERSION}: {path}")
    if data.get("doc_type") != expected_doc_type:
        raise RunnerError(f"backend result has wrong doc_type: {path}")
    for key in ("project_id", "project_revision", "editor_backend"):
        if data.get(key) != task.get(key):
            raise RunnerError(f"backend result identity mismatch for {key}: {path}")
    return data


def revision_invalidation(task: dict[str, Any]) -> dict[str, Any]:
    """Describe, but never delete, artifacts superseded by a confirmed revision."""

    if task.get("task_type") != "revise_local_edit_artifacts":
        return {}
    raw = (task.get("inputs") or {}).get("invalidated_artifacts")
    if raw is None:
        raw = ["05_storyboard.md", "06_edit_decision_list.json", "editor_backend_artifacts"]
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise RunnerError("inputs.invalidated_artifacts must be a non-empty text list when provided")
    revision = int(task["project_revision"])
    return {
        "superseded_revision": revision - 1,
        "superseded_artifacts": raw,
        "preserved_for_comparison": True,
    }


def write_handoff_pack_result(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    validation_path: Path,
    tools_used: dict[str, str],
) -> None:
    pack_dir = backend_output_root(config, task) / str(task["project_revision"])
    manifest = pack_dir / "manifest.json"
    clips_csv = pack_dir / "clips.csv"
    captions = pack_dir / "captions.srt"
    handoff_note = pack_dir / "剪辑交接说明.md"
    preview_note = pack_dir / "预览说明.md"
    manifest_data = require_json_identity(manifest, task, "edit_handoff_manifest")
    validation_data = require_json_identity(validation_path, task, "edit_handoff_validation")
    if validation_data.get("status") != "passed":
        raise RunnerError(f"handoff backend validation did not pass: {validation_path}")
    if manifest_data.get("editor_backend") != "handoff_pack":
        raise RunnerError("handoff manifest editor_backend must be handoff_pack")
    for path in (clips_csv, captions, handoff_note, preview_note):
        require_nonempty(path)
    revision_basis = manifest_data.get("inputs") if task.get("task_type") == "revise_local_edit_artifacts" else None
    if revision_basis is not None:
        revision_basis = next(
            (
                item
                for item in revision_basis
                if isinstance(item, dict) and item.get("role") == "confirmed_revision_basis"
            ),
            None,
        )
        if not isinstance(revision_basis, dict):
            raise RunnerError("revision handoff manifest must reference its confirmed revision basis")
    result = {
        **task_identity(task),
        "status": "done",
        "idea_id": task["idea_id"],
        "outputs": {
            "handoff_manifest": str(manifest),
            "handoff_clips": str(clips_csv),
            "handoff_captions": str(captions),
            "handoff_readme": str(handoff_note),
            "handoff_preview_note": str(preview_note),
            **({"revision_basis": str(revision_basis["path"])} if revision_basis is not None else {}),
        },
        "backend_result": manifest_data,
        "backend_validation": validation_data,
        "tools_used": tools_used,
        "fallback_used": False,
        "summary": {
            "completed": True,
            "human_next_step": "打开剪辑交接包并开始精剪",
        },
        "invalidation": revision_invalidation(task),
    }
    write_yaml(result_path, result)


def run_edit_handoff_pack(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
    revision_basis: Path | None = None,
) -> None:
    edl, storyboard = backend_source_files(config, task)
    output_root = backend_output_root(config, task)
    pack_dir = output_root / str(task["project_revision"])
    generation_result = pack_dir / "handoff_generation.json"
    validation_result = pack_dir / "handoff_validation.json"
    materials = optional_input_file_path(config, task, "materials_path")
    tools_used: dict[str, str] = {}

    if execute:
        command = [
            sys.executable,
            script_path("edit_backends/handoff_pack.py"),
            "generate",
            "--project-id",
            str(task["project_id"]),
            "--project-revision",
            str(task["project_revision"]),
            "--edl",
            str(edl),
            "--storyboard",
            str(storyboard),
            "--output-root",
            str(output_root),
            "--result-output",
            str(generation_result),
        ]
        if materials:
            command.extend(["--materials", str(materials)])
        if revision_basis is not None:
            command.extend(["--revision-basis", str(revision_basis)])
        run_command(command)
        tools_used["generate_edit_handoff_pack"] = script_path("edit_backends/handoff_pack.py")
        run_command(
            [
                sys.executable,
                script_path("edit_backends/handoff_pack.py"),
                "validate",
                "--manifest",
                str(pack_dir / "manifest.json"),
                "--result-output",
                str(validation_result),
            ]
        )
        tools_used["validate_edit_handoff_pack"] = script_path("edit_backends/handoff_pack.py")
    else:
        tools_used["write_result"] = "existing_backend_outputs"
    write_handoff_pack_result(config, task, result_path, validation_result, tools_used)


def write_otio_kdenlive_result(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    validation_path: Path,
    tools_used: dict[str, str],
) -> None:
    pack_dir = backend_output_root(config, task) / str(task["project_revision"])
    otio = pack_dir / "timeline.otio"
    kdenlive = pack_dir / "timeline.kdenlive"
    handoff_note = pack_dir / "剪辑交接说明.md"
    validation = require_json_identity(validation_path, task, "otio_kdenlive_validation")
    manifest = require_json_identity(pack_dir / "manifest.json", task, "otio_kdenlive_handoff_manifest")
    if validation.get("status") != "passed":
        raise RunnerError(f"OTIO/Kdenlive backend validation did not pass: {validation_path}")
    for path in (otio, kdenlive, handoff_note):
        require_nonempty(path)
    revision_basis = manifest.get("revision_basis") if task.get("task_type") == "revise_local_edit_artifacts" else None
    if task.get("task_type") == "revise_local_edit_artifacts" and not isinstance(revision_basis, dict):
        raise RunnerError("revision OTIO manifest must reference its confirmed revision basis")
    result = {
        **task_identity(task),
        "status": "done",
        "idea_id": task["idea_id"],
        "outputs": {
            "otio_timeline": str(otio),
            "kdenlive_timeline": str(kdenlive),
            "timeline_validation": str(validation_path),
            "handoff_readme": str(handoff_note),
            **({"revision_basis": str(revision_basis["path"])} if isinstance(revision_basis, dict) else {}),
        },
        "backend_result": manifest,
        "backend_validation": validation,
        "tools_used": tools_used,
        "fallback_used": False,
        "summary": {
            "completed": True,
            "human_next_step": "在可编辑时间线中打开并继续精剪",
        },
        "invalidation": revision_invalidation(task),
    }
    write_yaml(result_path, result)


def run_otio_kdenlive_timeline(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
    revision_basis: Path | None = None,
) -> None:
    edl, storyboard = backend_source_files(config, task)
    output_root = backend_output_root(config, task)
    pack_dir = output_root / str(task["project_revision"])
    otio = pack_dir / "timeline.otio"
    kdenlive = pack_dir / "timeline.kdenlive"
    otio_result = pack_dir / "otio_generation.json"
    kdenlive_result = pack_dir / "kdenlive_generation.json"
    validation_result = pack_dir / "timeline_validation.json"
    tools_used: dict[str, str] = {}

    if execute:
        script = script_path("edit_backends/otio_kdenlive.py")
        interpreter = otio_kdenlive_python()
        run_command(
            [
                interpreter,
                script,
                "generate-otio",
                "--project-id",
                str(task["project_id"]),
                "--project-revision",
                str(task["project_revision"]),
                "--edl",
                str(edl),
                "--storyboard",
                str(storyboard),
                "--output-root",
                str(output_root),
                "--result-output",
                str(otio_result),
            ]
            + (["--revision-basis", str(revision_basis)] if revision_basis is not None else [])
        )
        tools_used["generate_otio_timeline"] = script
        run_command(
            [
                interpreter,
                script,
                "generate-kdenlive",
                "--otio",
                str(otio),
                "--project-id",
                str(task["project_id"]),
                "--project-revision",
                str(task["project_revision"]),
                "--output-root",
                str(output_root),
                "--result-output",
                str(kdenlive_result),
            ]
        )
        tools_used["create_kdenlive_timeline"] = script
        run_command(
            [
                interpreter,
                script,
                "validate",
                "--otio",
                str(otio),
                "--kdenlive",
                str(kdenlive),
                "--project-id",
                str(task["project_id"]),
                "--project-revision",
                str(task["project_revision"]),
                "--result-output",
                str(validation_result),
            ]
        )
        tools_used["validate_kdenlive_timeline"] = script
    else:
        tools_used["write_result"] = "existing_backend_outputs"
    write_otio_kdenlive_result(config, task, result_path, validation_result, tools_used)


def run_revision_task(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
) -> None:
    """Regenerate only the already-selected backend for a confirmed change."""

    backend = str(task["editor_backend"])
    if backend not in {"handoff_pack", "otio_kdenlive"}:
        raise RunnerError(f"unsupported editor_backend with no fallback: {backend}")
    revision_basis = write_confirmed_revision_basis(config, task)
    if backend == "handoff_pack":
        run_edit_handoff_pack(config, task, result_path, execute, revision_basis)
        return
    if backend == "otio_kdenlive":
        run_otio_kdenlive_timeline(config, task, result_path, execute, revision_basis)
        return
    raise AssertionError(f"validated editor backend was not dispatched: {backend}")


def run_ai_edit_log(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
    allow_replace_generated: bool,
) -> None:
    project_dir = project_package_dir(config, task)
    edit_log = expected_output(config, task, "07_edit_log.md")
    generation_dir = (
        local_project_path(config, task)
        / "90_Draft_Project"
        / "edit_handoff"
        / str(task["project_revision"])
        / "ai_edit_log"
        / str(task["task_id"])
    )
    prompt_output = generation_dir / "ai_edit_log_prompt.txt"
    tools_used: dict[str, str] = {}

    if execute:
        args = [
            sys.executable,
            script_path("29_generate_ai_edit_log.py"),
            "--project-package",
            str(project_dir),
            "--output",
            str(edit_log),
            "--model",
            REQUIRED_CREATIVE_MODEL,
            "--reasoning",
            REQUIRED_CREATIVE_REASONING,
            "--prompt-output",
            str(prompt_output),
        ]
        human_notes = optional_input_file_path(config, task, "human_notes_path")
        video = optional_input_file_path(config, task, "output_video_path")
        if human_notes and human_notes.exists():
            args.extend(["--human-notes", str(human_notes)])
        if video and video.exists():
            args.extend(["--video", str(video)])
        if allow_replace_generated:
            args.append("--allow-overwrite")
        run_command(args)
        tools_used["generate_ai_edit_log"] = script_path("29_generate_ai_edit_log.py")
    else:
        tools_used["write_result"] = "existing_outputs"

    ai_edit_log_result(config, task, result_path, tools_used)


def run_output_review(
    config: RunnerConfig,
    task: dict[str, Any],
    result_path: Path,
    execute: bool,
) -> None:
    project_dir = local_project_path(config, task)
    report = output_review_expected_report(config, task)
    video = input_file_path(config, task, "output_video_path")
    compare_videos = optional_input_file_list(config, task, "compare_video_paths")
    brief = optional_input_file_path(config, task, "project_brief_path")
    script = optional_input_file_path(config, task, "script_path") or (project_package_dir(config, task) / "04_script.md")
    publish_pack = optional_input_file_path(config, task, "publish_pack_path") or (project_package_dir(config, task) / "09_publish_pack.md")
    generation_dir = project_dir / "_ai_analysis" / "output_review" / str(task["task_id"])
    metrics = generation_dir / "metrics.json"
    local_result = generation_dir / "output_review_result.yaml"
    tools_used: dict[str, str] = {}

    if execute:
        args = [
            sys.executable,
            script_path("19_review_output_video.py"),
            "--task-id",
            str(task["task_id"]),
            "--project-id",
            str(task["project_id"]),
            "--idea-id",
            str(task["idea_id"]),
            "--video",
            f"current={video}",
            "--output-root",
            str(generation_dir),
            "--report-output",
            str(report),
            "--metrics-output",
            str(metrics),
            "--result-output",
            str(local_result),
            "--artifact-base",
            str(project_dir),
        ]
        args.extend(["--project-root", str(project_dir)])
        args.append("--rhythm-sync")
        if task.get("run_vlm_review") is True or os.getenv("OPENCLAW_RUN_VLM_REVIEW") == "1":
            args.append("--run-vlm-review")
        for index, compare in enumerate(compare_videos, start=1):
            args.extend(["--compare-video", f"compare_{index}={compare}"])
        if brief and brief.exists():
            args.extend(["--brief", str(brief)])
        if script.exists():
            args.extend(["--script", str(script)])
        if publish_pack.exists():
            args.extend(["--publish-pack", str(publish_pack)])
        run_command(args)
        tools_used["review_output_video"] = script_path("19_review_output_video.py")
    else:
        tools_used["write_result"] = "existing_outputs"

    output_review_result(config, task, result_path, local_result, tools_used)


def run_task(
    config: RunnerConfig,
    task_ref: str,
    execute: bool,
    allow_replace_result: bool,
    allow_replace_generated: bool,
    skip_runtime_check: bool,
    skip_analyze: bool,
) -> Path:
    task_path = resolve_task_ref(config, task_ref)
    task, result_path, _canonical_actions = validate_or_block(config, task_path)
    if result_path.exists() and not allow_replace_result:
        try:
            previous = load_validator_yaml(result_path)
        except ValidationError:
            previous = {}
        if previous.get("status") == "blocked":
            result_path.unlink()
        else:
            raise RunnerError(f"result already exists; use --allow-replace-result to overwrite: {result_path}")
    if execute:
        run_runtime_check(skip_runtime_check, str(task.get("task_type") or ""))

    task_type = str(task["task_type"])
    try:
        if task_type == "local_material_match":
            run_local_material_match(config, task, result_path, execute, skip_analyze)
        elif task_type == "generate_edit_handoff_pack":
            run_edit_handoff_pack(config, task, result_path, execute)
        elif task_type == "generate_otio_kdenlive_timeline":
            run_otio_kdenlive_timeline(config, task, result_path, execute)
        elif task_type == "revise_local_edit_artifacts":
            run_revision_task(config, task, result_path, execute)
        elif task_type == "generate_ai_edit_log":
            run_ai_edit_log(config, task, result_path, execute, allow_replace_generated)
        elif task_type == "local_output_review":
            run_output_review(config, task, result_path, execute)
        else:
            raise RunnerError(f"unsupported task_type: {task_type}")
    except RunnerError as exc:
        if execute:
            write_execution_blocked_result(result_path, task, str(exc))
        raise

    print(f"result={result_path}")
    return result_path


def list_tasks(config: RunnerConfig) -> None:
    rows: list[dict[str, Any]] = []
    for path in task_files(config):
        try:
            task = load_yaml(path)
            result_path = result_path_for(config, path, task)
            rows.append(
                {
                    "task_id": task.get("task_id", path.stem),
                    "task_type": task.get("task_type", ""),
                    "status": task.get("status", ""),
                    "project_id": task.get("project_id", ""),
                    "result_exists": result_path.exists(),
                    "file": str(path),
                }
            )
        except RunnerError as exc:
            rows.append({"task_id": path.stem, "task_type": "invalid_yaml", "status": str(exc), "file": str(path)})
    yaml.safe_dump(rows, sys.stdout, allow_unicode=True, sort_keys=False)


def validate_task_command(config: RunnerConfig, task_ref: str) -> None:
    task_path = resolve_task_ref(config, task_ref)
    task, result_path, canonical_actions = validate_or_block(config, task_path)
    summary = {
        "status": "valid",
        "task_id": task["task_id"],
        "task_type": task["task_type"],
        "project_id": task["project_id"],
        "canonical_actions": canonical_actions,
        "result_path": str(result_path),
        "result_exists": result_path.exists(),
    }
    yaml.safe_dump(summary, sys.stdout, allow_unicode=True, sort_keys=False)


def validate_project(config: RunnerConfig, project_id: str) -> None:
    project_dir = config.vault_root / "08_内容项目" / project_id
    files = [
        "00_项目总览.md",
        "01_idea_card.md",
        "02_project_brief.md",
        "03_material_match_report.md",
        "05_storyboard.md",
        "06_edit_decision_list.json",
        "08_local_assets.md",
    ]
    status = {
        "project_id": project_id,
        "project_dir": str(project_dir),
        "exists": project_dir.exists(),
        "files": {
            name: {
                "exists": (project_dir / name).exists(),
                "nonempty": (project_dir / name).exists() and (project_dir / name).stat().st_size > 0,
            }
            for name in files
        },
    }
    yaml.safe_dump(status, sys.stdout, allow_unicode=True, sort_keys=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", type=Path, default=DEFAULT_VAULT_ROOT)
    parser.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-tasks", help="List cloud-to-Mac ready tasks.")

    validate_parser = subparsers.add_parser("validate-task", help="Validate a task contract.")
    validate_parser.add_argument("task")

    run_parser = subparsers.add_parser("run-task", help="Validate and execute a task.")
    run_parser.add_argument("task")
    run_parser.add_argument("--allow-replace-result", action="store_true")
    run_parser.add_argument("--allow-replace-generated", action="store_true")
    run_parser.add_argument("--skip-runtime-check", action="store_true")
    run_parser.add_argument("--skip-analyze", action="store_true", help="Reuse existing _ai_analysis/media_manifest.json")

    write_parser = subparsers.add_parser("write-result", help="Write a result from existing task outputs.")
    write_parser.add_argument("task")
    write_parser.add_argument("--allow-replace-result", action="store_true")

    project_parser = subparsers.add_parser("validate-project", help="Check a Content OS project package.")
    project_parser.add_argument("project_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = RunnerConfig(
        vault_root=args.vault_root.expanduser().resolve(),
        workspace_root=args.workspace_root.expanduser().resolve(),
    )

    try:
        if args.command == "list-tasks":
            list_tasks(config)
        elif args.command == "validate-task":
            validate_task_command(config, args.task)
        elif args.command == "run-task":
            run_task(
                config,
                args.task,
                execute=True,
                allow_replace_result=args.allow_replace_result,
                allow_replace_generated=args.allow_replace_generated,
                skip_runtime_check=args.skip_runtime_check,
                skip_analyze=args.skip_analyze,
            )
        elif args.command == "write-result":
            run_task(
                config,
                args.task,
                execute=False,
                allow_replace_result=args.allow_replace_result,
                allow_replace_generated=False,
                skip_runtime_check=True,
                skip_analyze=True,
            )
        elif args.command == "validate-project":
            validate_project(config, args.project_id)
        else:
            parser.error(f"unknown command: {args.command}")
    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
