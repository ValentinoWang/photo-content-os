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
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from openclaw_product_contract import ProductContractError, SNAPSHOT_PATH, p1a_content_digest, validate_snapshot
from media import write_json_atomic


if __package__:
    from .constants import (
        CATALOG_RELATIVE_PATH,
        PRODUCT_CONTRACT_RELATIVE_PATH,
        PIPELINE_ALIASES,
    )
else:
    from constants import (
        CATALOG_RELATIVE_PATH,
        PRODUCT_CONTRACT_RELATIVE_PATH,
        PIPELINE_ALIASES,
    )


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


def read_json(path: Path, label: str, *, raw: bytes | None = None) -> dict[str, Any]:
    try:
        data = json.loads(raw if raw is not None else path.read_bytes())
    except (OSError, UnicodeError, ValueError) as exc:
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


def require_committed_catalog(upstream_root: Path, relative: Path, commit: str) -> bytes:
    """Return source bytes from the pinned commit after checking the checkout."""
    try:
        committed = subprocess.run(
            ["git", "-C", str(upstream_root), "show", f"{commit}:{relative.as_posix()}"],
            check=True,
            capture_output=True,
        ).stdout
        current = (upstream_root / relative).read_bytes()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SnapshotRefreshError(f"cannot read upstream file from checkout and commit: {relative}") from exc
    if current != committed:
        raise SnapshotRefreshError(f"upstream file has uncommitted changes: {relative}")
    return committed


def require_clean_checkout(upstream_root: Path) -> None:
    try:
        status = subprocess.run(
            ["git", "-C", str(upstream_root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SnapshotRefreshError("cannot inspect upstream checkout state") from exc
    if status:
        raise SnapshotRefreshError("upstream checkout has uncommitted changes and cannot be pinned")


def validated_catalog(upstream_root: Path, catalog_relative: Path, commit: str) -> dict[str, Any]:
    if catalog_relative.is_absolute() or ".." in catalog_relative.parts:
        raise SnapshotRefreshError("catalog path must be relative to the upstream checkout")
    raw = require_committed_catalog(upstream_root, catalog_relative, commit)
    catalog = read_json(upstream_root / catalog_relative, "upstream pipeline catalog", raw=raw)
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
    require_clean_checkout(root)
    commit = checkout_commit(root)
    catalog = validated_catalog(root, catalog_relative, commit)
    source_bytes = require_committed_catalog(root, PRODUCT_CONTRACT_RELATIVE_PATH, commit)
    product_contract = read_json(root / PRODUCT_CONTRACT_RELATIVE_PATH, "upstream product contract", raw=source_bytes)
    api_base = product_contract.get("api_base")
    if not isinstance(api_base, str) or not api_base.startswith("/") or not api_base.strip("/"):
        raise SnapshotRefreshError("upstream product contract.api_base must be an absolute API path")
    section = product_contract.get("p1a_first_project")
    if not isinstance(section, dict):
        raise SnapshotRefreshError("upstream product contract missing P1a first-project definitions")
    all_schemas = product_contract.get("api_schemas")
    if not isinstance(all_schemas, dict):
        raise SnapshotRefreshError("upstream product contract missing api_schemas")
    included: dict[str, Any] = {}

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if (key == "$ref" or key.endswith("_schema_ref")) and isinstance(child, str) and child.startswith("#/api_schemas/"):
                    name = child.removeprefix("#/api_schemas/")
                    if name not in all_schemas:
                        raise SnapshotRefreshError(f"missing upstream schema: {name}")
                    if name not in included:
                        included[name] = all_schemas[name]
                        collect(included[name])
                else:
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(section)
    candidate = dict(existing)
    candidate.update(
        {
            "p1a_first_project": {
                "source_sha256": "sha256:" + hashlib.sha256(source_bytes).hexdigest(),
                "content_sha256": p1a_content_digest(section, included),
                "contract": section,
                "api_schemas": included,
            },
            "upstream_commit": commit,
            "upstream_contract_id": catalog["contract_id"],
            "upstream_contract_version": catalog["contract_version"],
            "catalog_digest": catalog["catalog_digest"],
            "api_base": api_base,
            "pipelines": dict(PIPELINE_ALIASES),
        }
    )
    validate_snapshot(candidate)
    if checkout_commit(root) != commit:
        raise SnapshotRefreshError("upstream HEAD changed during snapshot generation")
    return candidate


def write_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    """Atomically replace the photo-side pin after an explicit approval."""

    target = path.expanduser().resolve()
    write_json_atomic(target, snapshot, random_temp=True, cleanup='replace_error')


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
    except (SnapshotRefreshError, ProductContractError) as exc:
        parser.exit(2, f"blocked: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
