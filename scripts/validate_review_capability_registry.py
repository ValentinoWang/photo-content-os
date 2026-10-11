#!/usr/bin/env python3
"""Validate the GitHub-managed review capability registry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "review_capabilities.registry.v1"
ALLOWED_STATUS = {"active", "proposed", "deprecated"}
ALLOWED_OWNERS = {"mac_openclaw", "cloud_openclaw"}
ALLOWED_SURFACES = {
    "mac_local",
    "cloud_task_to_mac_runner",
    "codex_vlm",
    "remote_server",
    "obsidian_queue",
    "mac_runner",
}
ALLOWED_ALGORITHM_ROLES = {
    "scoring_core",
    "semantic_judgement_fusion",
    "remote_strategy_evaluation",
    "post_publish_data_review",
    "orchestrator_only",
}
CAPABILITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def default_registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / "review_capabilities.registry.json"


def repo_root_from_registry(registry_path: Path) -> Path:
    path = registry_path.resolve()
    if path.parent.name == "99_System_OpenClaw":
        return path.parent.parent
    return path.parent


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("registry root must be a JSON object")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    return [item for item in as_list(value) if isinstance(item, str)]


def require_string_list(errors: list[str], prefix: str, value: Any, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{prefix} must be a list")
        return []
    strings = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}[{index}] must be a non-empty string")
        else:
            strings.append(item)
    if not strings and not allow_empty:
        errors.append(f"{prefix} must not be empty")
    return strings


def validate_relative_existing_paths(
    errors: list[str],
    repo_root: Path,
    capability_id: str,
    field_name: str,
    paths: Any,
    *,
    allow_empty: bool = False,
) -> None:
    for raw_path in require_string_list(errors, f"{capability_id}.{field_name}", paths, allow_empty=allow_empty):
        path = Path(raw_path)
        if path.is_absolute():
            errors.append(f"{capability_id}.{field_name} must be repo-relative: {raw_path}")
            continue
        resolved = repo_root / path
        if not resolved.exists():
            errors.append(f"{capability_id}.{field_name} missing file: {raw_path}")


def validate_capability(
    capability: dict[str, Any],
    repo_root: Path,
    capability_ids: set[str],
    task_type_owners: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    capability_id = str(capability.get("capability_id") or "")
    prefix = capability_id or "<missing_capability_id>"

    if not capability_id:
        errors.append("capability_id is required")
    elif not CAPABILITY_ID_PATTERN.match(capability_id):
        errors.append(f"{capability_id}.capability_id must match {CAPABILITY_ID_PATTERN.pattern}")
    elif capability_id in capability_ids:
        errors.append(f"duplicate capability_id: {capability_id}")
    else:
        capability_ids.add(capability_id)

    display_name = capability.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        errors.append(f"{prefix}.display_name is required")

    status = capability.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"{prefix}.status must be one of {sorted(ALLOWED_STATUS)}")

    owner = capability.get("canonical_owner")
    if owner not in ALLOWED_OWNERS:
        errors.append(f"{prefix}.canonical_owner must be one of {sorted(ALLOWED_OWNERS)}")

    surfaces = require_string_list(errors, f"{prefix}.execution_surfaces", capability.get("execution_surfaces"))
    unknown_surfaces = sorted(set(surfaces) - ALLOWED_SURFACES)
    if unknown_surfaces:
        errors.append(f"{prefix}.execution_surfaces contains unknown values: {', '.join(unknown_surfaces)}")

    external_refs = string_list(capability.get("external_implementation_refs"))
    validate_relative_existing_paths(
        errors,
        repo_root,
        prefix,
        "implementation_files",
        capability.get("implementation_files"),
        allow_empty=bool(external_refs),
    )
    if capability.get("external_implementation_refs") is not None:
        require_string_list(errors, f"{prefix}.external_implementation_refs", capability.get("external_implementation_refs"))
    validate_relative_existing_paths(errors, repo_root, prefix, "contract_files", capability.get("contract_files"))

    contract = capability.get("execution_contract")
    if not isinstance(contract, dict):
        errors.append(f"{prefix}.execution_contract must be an object")
        contract = {}

    for task_type in string_list(contract.get("runner_task_types")):
        previous = task_type_owners.get(task_type)
        if previous and previous != capability_id:
            errors.append(f"runner task_type {task_type} is owned by both {previous} and {capability_id}")
        task_type_owners[task_type] = capability_id

    schemas = string_list(contract.get("schemas"))
    if "review" in capability_id and not schemas and capability_id != "remote_review_orchestration":
        errors.append(f"{prefix}.execution_contract.schemas is required for review implementations")

    github_policy = capability.get("github_policy")
    if not isinstance(github_policy, dict):
        errors.append(f"{prefix}.github_policy must be an object")
    else:
        required_checks = github_policy.get("required_pr_checks")
        require_string_list(errors, f"{prefix}.github_policy.required_pr_checks", required_checks)
        remote_rule = github_policy.get("remote_server_rule")
        if not isinstance(remote_rule, str) or not remote_rule.strip():
            errors.append(f"{prefix}.github_policy.remote_server_rule is required")

    dedupe_guard = capability.get("dedupe_guard")
    if not isinstance(dedupe_guard, str) or not dedupe_guard.strip():
        errors.append(f"{prefix}.dedupe_guard is required")

    algorithm_contract = capability.get("algorithm_contract")
    if not isinstance(algorithm_contract, dict):
        errors.append(f"{prefix}.algorithm_contract must be an object")
        algorithm_contract = {}
    role = algorithm_contract.get("algorithm_role")
    if role not in ALLOWED_ALGORITHM_ROLES:
        errors.append(f"{prefix}.algorithm_contract.algorithm_role must be one of {sorted(ALLOWED_ALGORITHM_ROLES)}")
    require_string_list(errors, f"{prefix}.algorithm_contract.judgement_outputs", algorithm_contract.get("judgement_outputs"))
    require_string_list(errors, f"{prefix}.algorithm_contract.decision_functions", algorithm_contract.get("decision_functions"))
    scoring_dimensions = algorithm_contract.get("scoring_dimensions")
    require_string_list(
        errors,
        f"{prefix}.algorithm_contract.scoring_dimensions",
        scoring_dimensions,
        allow_empty=role == "orchestrator_only",
    )
    human_boundary = algorithm_contract.get("human_boundary")
    if not isinstance(human_boundary, str) or not human_boundary.strip():
        errors.append(f"{prefix}.algorithm_contract.human_boundary is required")
    if role == "orchestrator_only" and scoring_dimensions:
        errors.append(f"{prefix}.algorithm_contract.scoring_dimensions must be empty for orchestrator_only")
    if owner == "mac_openclaw" and role == "orchestrator_only":
        errors.append(f"{prefix}.algorithm_contract.algorithm_role cannot be orchestrator_only for Mac-owned scoring capability")
    if owner == "cloud_openclaw" and role in {"scoring_core", "semantic_judgement_fusion"}:
        errors.append(f"{prefix}.algorithm_contract.algorithm_role must not be video scoring core for cloud_openclaw")
    strategy_weights = algorithm_contract.get("strategy_weights")
    if strategy_weights is not None:
        if not isinstance(strategy_weights, dict) or not strategy_weights:
            errors.append(f"{prefix}.algorithm_contract.strategy_weights must be a non-empty object")
        else:
            weight_sum = 0.0
            for key, value in strategy_weights.items():
                if not isinstance(key, str) or not key.strip():
                    errors.append(f"{prefix}.algorithm_contract.strategy_weights has an empty key")
                    continue
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(f"{prefix}.algorithm_contract.strategy_weights.{key} must be a non-negative number")
                    continue
                weight_sum += float(value)
            if abs(weight_sum - 1.0) > 0.0001:
                errors.append(f"{prefix}.algorithm_contract.strategy_weights must sum to 1.0, got {weight_sum:.4f}")
        weights_version = algorithm_contract.get("strategy_weights_version")
        if not isinstance(weights_version, str) or not weights_version.strip():
            errors.append(f"{prefix}.algorithm_contract.strategy_weights_version is required when strategy_weights is present")

    if owner == "cloud_openclaw" and role == "orchestrator_only":
        orchestrates = string_list(contract.get("orchestrates_task_types"))
        if not orchestrates:
            errors.append(f"{prefix} with cloud_openclaw owner must declare orchestrates_task_types")

    if owner == "mac_openclaw" and "remote_server" in surfaces:
        errors.append(f"{prefix} is Mac-owned; use cloud_task_to_mac_runner instead of remote_server")

    return errors


def validate_registry(registry: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    management = registry.get("canonical_management")
    if not isinstance(management, dict):
        errors.append("canonical_management must be an object")
        management = {}
    else:
        if management.get("system") != "github":
            errors.append("canonical_management.system must be github")
        for key in ["registry_path", "governance_doc", "algorithm_doc", "current_convergence_scope", "change_gate", "rule"]:
            if not isinstance(management.get(key), str) or not management.get(key, "").strip():
                errors.append(f"canonical_management.{key} is required")

    registry_path = management.get("registry_path")
    if isinstance(registry_path, str) and registry_path:
        candidate = repo_root / registry_path
        if not candidate.exists():
            errors.append(f"canonical_management.registry_path does not exist: {registry_path}")

    governance_doc = management.get("governance_doc")
    if isinstance(governance_doc, str) and governance_doc:
        candidate = repo_root / governance_doc
        if not candidate.exists():
            errors.append(f"canonical_management.governance_doc does not exist: {governance_doc}")

    algorithm_doc = management.get("algorithm_doc")
    if isinstance(algorithm_doc, str) and algorithm_doc:
        candidate = repo_root / algorithm_doc
        if not candidate.exists():
            errors.append(f"canonical_management.algorithm_doc does not exist: {algorithm_doc}")

    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("capabilities must be a non-empty list")
        capabilities = []

    capability_ids: set[str] = set()
    task_type_owners: dict[str, str] = {}
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            errors.append(f"capabilities[{index}] must be an object")
            continue
        errors.extend(validate_capability(capability, repo_root, capability_ids, task_type_owners))

    dedupe_rules = registry.get("dedupe_rules")
    if not isinstance(dedupe_rules, list) or not dedupe_rules:
        errors.append("dedupe_rules must be a non-empty list")
        dedupe_rules = []

    seen_rule_ids: set[str] = set()
    for index, rule in enumerate(dedupe_rules):
        if not isinstance(rule, dict):
            errors.append(f"dedupe_rules[{index}] must be an object")
            continue
        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            errors.append(f"dedupe_rules[{index}].rule_id is required")
        elif rule_id in seen_rule_ids:
            errors.append(f"duplicate dedupe rule_id: {rule_id}")
        else:
            seen_rule_ids.add(rule_id)
        canonical_id = rule.get("canonical_capability_id")
        if canonical_id not in capability_ids:
            errors.append(f"dedupe_rules[{index}].canonical_capability_id is unknown: {canonical_id}")
        require_string_list(errors, f"dedupe_rules[{index}].forbidden_duplicate_scope", rule.get("forbidden_duplicate_scope"))

    return errors


def markdown_summary(registry: dict[str, Any]) -> str:
    lines = [
        "# Review Capability Registry",
        "",
        "| Capability | Owner | Status | Surfaces |",
        "| --- | --- | --- | --- |",
    ]
    for capability in registry.get("capabilities", []):
        if not isinstance(capability, dict):
            continue
        surfaces = ", ".join(string_list(capability.get("execution_surfaces")))
        lines.append(
            "| "
            + str(capability.get("capability_id", ""))
            + " | "
            + str(capability.get("canonical_owner", ""))
            + " | "
            + str(capability.get("status", ""))
            + " | "
            + surfaces
            + " |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate review capability SSOT registry")
    parser.add_argument("--registry", default=str(default_registry_path()), help="Path to review_capabilities.registry.json")
    parser.add_argument("--summary-output", help="Optional Markdown summary output path")
    args = parser.parse_args()

    registry_path = Path(args.registry).expanduser().resolve()
    repo_root = repo_root_from_registry(registry_path)
    registry = load_registry(registry_path)
    errors = validate_registry(registry, repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.summary_output:
        summary_path = Path(args.summary_output).expanduser()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(markdown_summary(registry), encoding="utf-8")

    print(f"review capability registry OK: {len(registry.get('capabilities', []))} capabilities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
