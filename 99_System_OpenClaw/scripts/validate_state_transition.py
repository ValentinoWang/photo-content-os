#!/usr/bin/env python3
"""Validate a Content OS project state transition without editing files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from llm_common import load_markdown_frontmatter
from media_common import read_yaml_mapping


class TransitionError(Exception):
    """Raised when a state transition violates the state machine contract."""


def load_yaml(path: Path) -> dict[str, Any]:
    return read_yaml_mapping(path, error=TransitionError)


def parse_frontmatter(path: Path) -> dict[str, Any]:
    return load_markdown_frontmatter(path, error=TransitionError)


def non_empty(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def parse_json_file(path: Path) -> None:
    if not non_empty(path):
        raise TransitionError(f"required JSON evidence is missing or empty: {path}")
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def evidence_paths(values: list[str], vault_root: Path) -> list[Path]:
    paths: list[Path] = []
    for value in values:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = vault_root / path
        paths.append(path)
    return paths


def has_valid_yaml(
    paths: list[Path],
    expected_status: str | None = None,
    *,
    project_id: str | None = None,
    project_revision: int | None = None,
    editor_backend: str | None = None,
    change_request_id: str | None = None,
) -> bool:
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".yaml", ".yml"}:
            continue
        try:
            data = load_yaml(path)
        except TransitionError:
            continue
        if expected_status is not None and data.get("status") != expected_status:
            continue
        if project_id is not None and data.get("project_id") != project_id:
            continue
        if project_revision is not None and data.get("project_revision") != project_revision:
            continue
        if editor_backend is not None and data.get("editor_backend") != editor_backend:
            continue
        if change_request_id and data.get("change_request_id") != change_request_id:
            continue
        return True
    return False


def check_named_evidence(
    evidence: str,
    project_dir: Path,
    frontmatter: dict[str, Any],
    provided_evidence: list[Path],
    human_confirmed: bool,
    args: argparse.Namespace,
) -> None:
    local_project_path = Path(str(frontmatter.get("local_project_path", ""))).expanduser()

    if evidence == "local_project_path_exists":
        if not local_project_path.exists() or not local_project_path.is_dir():
            raise TransitionError(f"local_project_path is missing: {local_project_path}")
        return

    if evidence == "media_manifest_exists":
        path = local_project_path / "_ai_analysis" / "media_manifest.json"
        parse_json_file(path)
        return

    if evidence == "keyframes_generated":
        path = local_project_path / "_ai_analysis" / "keyframes"
        if not path.exists() or not any(path.rglob("*")):
            raise TransitionError(f"keyframes are missing: {path}")
        return

    if evidence == "task_yaml_valid":
        if not has_valid_yaml(provided_evidence):
            raise TransitionError("no parseable task YAML evidence was provided")
        return

    if evidence == "result_yaml_valid":
        if not has_valid_yaml(provided_evidence, expected_status="done"):
            raise TransitionError("no parseable done result YAML evidence was provided")
        return

    if evidence == "result_identity_valid":
        revision = frontmatter.get("project_revision")
        if not isinstance(revision, int) or revision < 1:
            raise TransitionError("project_revision must be a positive integer in project overview")
        if not has_valid_yaml(
            provided_evidence,
            expected_status="done",
            project_id=str(frontmatter.get("project_id") or ""),
            project_revision=revision,
            change_request_id=args.change_request_id,
        ):
            raise TransitionError("no done result matches the current project id, revision and change request")
        return

    if evidence == "selected_editor_backend_result_valid":
        backend = frontmatter.get("editor_backend")
        if backend not in {"handoff_pack", "otio_kdenlive"}:
            raise TransitionError("project overview editor_backend must be handoff_pack or otio_kdenlive")
        revision = frontmatter.get("project_revision")
        if not isinstance(revision, int) or revision < 1:
            raise TransitionError("project_revision must be a positive integer in project overview")
        if not has_valid_yaml(
            provided_evidence,
            expected_status="done",
            project_id=str(frontmatter.get("project_id") or ""),
            project_revision=revision,
            editor_backend=backend,
            change_request_id=args.change_request_id,
        ):
            raise TransitionError("no done result matches the selected editor backend")
        return

    if evidence == "selected_editor_backend_recorded":
        if frontmatter.get("editor_backend") not in {"handoff_pack", "otio_kdenlive"}:
            raise TransitionError("project overview must record a supported editor_backend")
        return

    if evidence == "cloud_script_reviewed":
        if not non_empty(project_dir / "04_script.md"):
            raise TransitionError("cloud script review evidence missing: 04_script.md")
        return

    if evidence == "output_video_exists":
        video_paths = [path for path in provided_evidence if path.suffix.lower() in {".mp4", ".mov", ".m4v"}]
        if not any(path.exists() and path.stat().st_size > 0 for path in video_paths):
            raise TransitionError("no non-empty output video evidence was provided")
        return

    if evidence in {"output_review_exists", "output_review_evidence_exists"}:
        review_paths = [path for path in provided_evidence if path.name.endswith("_output_review.md")]
        if not any(non_empty(path) for path in review_paths):
            raise TransitionError("no output review markdown evidence was provided")
        return

    if evidence in {"human_confirmed_edit_start", "human_final_selected", "human_confirmed_draft_open", "human_confirmed_impact"}:
        if not human_confirmed:
            raise TransitionError(f"human confirmation required for evidence: {evidence}")
        return

    if evidence == "human_published_confirmation":
        if not human_confirmed:
            raise TransitionError("human confirmation required for evidence: human_published_confirmation")
        if not str(frontmatter.get("publication_confirmed_at") or "").strip():
            raise TransitionError("project overview publication_confirmed_at is empty")
        if not str(frontmatter.get("publication_confirmed_by") or "").strip():
            raise TransitionError("project overview publication_confirmed_by is empty")
        return

    if evidence == "project_revision_matches_current":
        revision = frontmatter.get("project_revision")
        if not isinstance(revision, int) or revision < 1:
            raise TransitionError("project_revision must be a positive integer in project overview")
        if args.project_revision is not None and args.project_revision != revision:
            raise TransitionError("provided project_revision does not match project overview")
        return

    path = project_dir / evidence
    if path.suffix.lower() == ".json":
        parse_json_file(path)
    elif not non_empty(path):
        raise TransitionError(f"required evidence is missing or empty: {path}")


def find_transition(rules: dict[str, Any], from_status: str, to_status: str) -> dict[str, Any]:
    transitions = rules.get("transitions")
    if not isinstance(transitions, dict):
        raise TransitionError("state rules must contain transitions mapping")
    for metadata in transitions.values():
        if not isinstance(metadata, dict):
            continue
        if metadata.get("from") == from_status and metadata.get("to") == to_status:
            return metadata
    raise TransitionError(f"unknown transition: {from_status} -> {to_status}")


def validate_transition(args: argparse.Namespace) -> dict[str, Any]:
    vault_root = args.vault_root.expanduser().resolve()
    project_index = args.project_index.expanduser().resolve()
    project_dir = project_index.parent
    rules = load_yaml(args.rules.expanduser().resolve())
    frontmatter = parse_frontmatter(project_index)

    current_status = frontmatter.get("status")
    if current_status != args.from_status:
        raise TransitionError(f"project current status is {current_status!r}, expected {args.from_status!r}")

    transition = find_transition(rules, args.from_status, args.to_status)
    actor = transition.get("allowed_actor")
    permitted_actors = set(str(actor).split("_or_"))
    if args.actor not in permitted_actors:
        raise TransitionError(f"actor {args.actor!r} cannot perform transition; required {actor!r}")

    statuses = rules.get("project_statuses")
    if isinstance(statuses, list) and (args.from_status not in statuses or args.to_status not in statuses):
        raise TransitionError("transition statuses are not in the active project status list")

    provided = evidence_paths(args.evidence or [], vault_root)
    required = transition.get("required_evidence") or []
    if not isinstance(required, list):
        raise TransitionError("required_evidence must be a list")
    for item in required:
        if not isinstance(item, str):
            raise TransitionError("required_evidence entries must be strings")
        check_named_evidence(item, project_dir, frontmatter, provided, args.human_confirmed, args)

    return {
        "status": "valid",
        "project_id": frontmatter.get("project_id"),
        "from": args.from_status,
        "to": args.to_status,
        "actor": args.actor,
        "evidence_checked": required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-root", required=True, type=Path)
    parser.add_argument("--project-index", required=True, type=Path)
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--from", dest="from_status", required=True)
    parser.add_argument("--to", dest="to_status", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--human-confirmed", action="store_true")
    parser.add_argument("--project-revision", type=int, default=None)
    parser.add_argument("--change-request-id", default=None)
    args = parser.parse_args()

    try:
        summary = validate_transition(args)
    except TransitionError as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1

    yaml.safe_dump(summary, sys.stdout, allow_unicode=True, sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
