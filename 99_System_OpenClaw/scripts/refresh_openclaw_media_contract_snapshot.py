#!/usr/bin/env python3
"""Regenerate a reviewed OpenClaw Media compatibility snapshot from a local checkout.

The command prints a candidate by default. Updating the checked-in compatibility
pin requires both --write and --approve-pin so a checkout observation cannot
silently change the fail-closed boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from openclaw_product_contract import SNAPSHOT_PATH, validate_snapshot


CATALOG_RELATIVE_PATH = Path("openclaw_media/data/pipelines.json")
PIPELINE_ALIASES = {
    "prepare": "media.project.prepare.v1",
    "organize": "media.material.organize.v1",
    "match": "media.material.match.v1",
    "handoff": "media.edit.handoff.v1",
    "timeline": "media.edit.timeline.v1",
    "revise": "media.edit.revise.v1",
    "output-review": "media.output.review.v1",
    "rhythm-review": "media.rhythm.review.v1",
    "semantic-review": "media.semantic.review.v1",
}


class SnapshotRefreshError(RuntimeError):
    """Raised when a local checkout cannot safely produce a compatibility pin."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def catalog_digest(pipelines: list[dict[str, Any]]) -> str:
    """Compute the upstream catalog digest without trusting its embedded stamp."""

    definitions: list[dict[str, Any]] = []
    for pipeline in pipelines:
        item = deepcopy(pipeline)
        item.pop("catalog_digest", None)
        definitions.append(item)
    try:
        definitions.sort(key=lambda item: (str(item["pipeline_id"]), str(item["version"])))
    except KeyError as exc:
        raise SnapshotRefreshError("catalog pipeline is missing pipeline_id or version") from exc
    return "sha256:" + hashlib.sha256(canonical_json(definitions)).hexdigest()


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotRefreshError(f"cannot read {label}: {path}") from exc
    if not isinstance(data, dict):
        raise SnapshotRefreshError(f"{label} root must be an object: {path}")
    return data


def checkout_commit(upstream_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(upstream_root), "rev-parse", "HEAD"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise SnapshotRefreshError("git is required to regenerate an OpenClaw Media snapshot") from exc
    commit = completed.stdout.strip()
    if completed.returncode != 0 or len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit.lower()):
        detail = completed.stderr.strip() or "not a Git checkout"
        raise SnapshotRefreshError(f"cannot resolve upstream commit: {detail}")
    return commit


def require_committed_catalog(upstream_root: Path, catalog_relative: Path) -> None:
    """Reject a catalog that would not be reproducible from the recorded commit."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(upstream_root), "status", "--porcelain", "--", catalog_relative.as_posix()],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise SnapshotRefreshError("git is required to inspect the OpenClaw Media catalog state") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "not a Git checkout"
        raise SnapshotRefreshError(f"cannot inspect upstream catalog state: {detail}")
    if completed.stdout.strip():
        raise SnapshotRefreshError("upstream pipeline catalog has uncommitted changes and cannot be pinned to HEAD")


def validated_catalog(upstream_root: Path, catalog_relative: Path) -> dict[str, Any]:
    if catalog_relative.is_absolute() or ".." in catalog_relative.parts:
        raise SnapshotRefreshError("catalog path must be relative to the upstream checkout")
    require_committed_catalog(upstream_root, catalog_relative)
    catalog_path = upstream_root / catalog_relative
    catalog = read_json(catalog_path, "upstream pipeline catalog")
    pipelines = catalog.get("pipelines")
    if not isinstance(pipelines, list) or not all(isinstance(item, dict) for item in pipelines):
        raise SnapshotRefreshError("upstream pipeline catalog.pipelines must be a list of objects")
    computed_digest = catalog_digest(pipelines)
    if catalog.get("catalog_digest") != computed_digest:
        raise SnapshotRefreshError("upstream pipeline catalog digest does not match its definitions")
    if catalog.get("pipeline_count") != len(pipelines):
        raise SnapshotRefreshError("upstream pipeline catalog pipeline_count does not match its definitions")
    if any(item.get("catalog_digest") != computed_digest for item in pipelines):
        raise SnapshotRefreshError("upstream pipeline digest stamp does not match catalog_digest")
    pipeline_ids = {item.get("pipeline_id") for item in pipelines}
    if pipeline_ids != set(PIPELINE_ALIASES.values()):
        raise SnapshotRefreshError("upstream pipeline ids do not match the supported local bridge aliases")
    if not isinstance(catalog.get("contract_id"), str) or not catalog["contract_id"].strip():
        raise SnapshotRefreshError("upstream pipeline catalog.contract_id must be non-empty text")
    if isinstance(catalog.get("contract_version"), bool) or not isinstance(catalog.get("contract_version"), int):
        raise SnapshotRefreshError("upstream pipeline catalog.contract_version must be an integer")
    return catalog


def regenerate_snapshot(
    upstream_root: Path,
    *,
    snapshot_path: Path = SNAPSHOT_PATH,
    catalog_relative: Path = CATALOG_RELATIVE_PATH,
) -> dict[str, Any]:
    """Build a candidate pin while preserving photo-owned compatibility policy."""

    root = upstream_root.expanduser().resolve()
    if not root.is_dir():
        raise SnapshotRefreshError(f"upstream checkout is not a directory: {root}")
    existing = read_json(snapshot_path.expanduser().resolve(), "existing compatibility snapshot")
    validate_snapshot(existing)
    catalog = validated_catalog(root, catalog_relative)
    candidate = dict(existing)
    candidate.update(
        {
            "upstream_commit": checkout_commit(root),
            "upstream_contract_id": catalog["contract_id"],
            "upstream_contract_version": catalog["contract_version"],
            "catalog_digest": catalog["catalog_digest"],
            "pipelines": dict(PIPELINE_ALIASES),
        }
    )
    validate_snapshot(candidate)
    return candidate


def write_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    """Atomically replace the photo-side pin after an explicit approval."""

    target = path.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    try:
        os.replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-root", required=True, type=Path, help="Local OpenClaw Media Git checkout")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH, help="Photo-side snapshot to refresh")
    parser.add_argument(
        "--catalog-relative",
        type=Path,
        default=CATALOG_RELATIVE_PATH,
        help="Pipeline catalog path relative to --upstream-root",
    )
    parser.add_argument("--write", action="store_true", help="Atomically write the regenerated snapshot")
    parser.add_argument(
        "--approve-pin",
        action="store_true",
        help="Required together with --write because it changes the checked-in compatibility pin",
    )
    args = parser.parse_args()
    if args.write and not args.approve_pin:
        parser.error("--write requires --approve-pin")
    if args.approve_pin and not args.write:
        parser.error("--approve-pin requires --write")

    try:
        candidate = regenerate_snapshot(
            args.upstream_root,
            snapshot_path=args.snapshot,
            catalog_relative=args.catalog_relative,
        )
        if args.write:
            write_snapshot(args.snapshot, candidate)
            print(f"snapshot={args.snapshot.expanduser().resolve()}")
        else:
            print(json.dumps(candidate, ensure_ascii=False, indent=2))
    except SnapshotRefreshError as exc:
        parser.exit(2, f"blocked: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
