#!/usr/bin/env python3
"""Check local execution docs and Obsidian protocol docs stay aligned."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OBSIDIAN_ROOT = Path("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体").expanduser()


def default_local_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_contract_path(local_root: Path) -> Path:
    return local_root / "99_System_OpenClaw" / "doc_sync_contract.json"


def expand_contract_path(raw_path: str, local_root: Path, obsidian_root: Path) -> Path:
    expanded = raw_path.replace("$LOCAL_ROOT", str(local_root)).replace("$OBSIDIAN_ROOT", str(obsidian_root))
    return Path(expanded).expanduser()


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required doc: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"expected doc file but found directory: {path}")
    return path.read_text(encoding="utf-8")


def missing_markers(text: str, markers: list[str]) -> list[str]:
    return [marker for marker in markers if marker not in text]


def normalize_targets(raw_targets: list[Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for raw_target in raw_targets:
        if isinstance(raw_target, str):
            targets.append({"path": raw_target, "markers": []})
        elif isinstance(raw_target, dict) and isinstance(raw_target.get("path"), str):
            markers = raw_target.get("markers", [])
            if not isinstance(markers, list) or not all(isinstance(marker, str) for marker in markers):
                raise ValueError(f"target markers must be a list of strings: {raw_target['path']}")
            targets.append({"path": raw_target["path"], "markers": markers})
        else:
            raise ValueError(f"invalid target definition: {raw_target!r}")
    return targets


def resolve_source_paths(pair: dict[str, Any], local_root: Path, obsidian_root: Path) -> list[Path]:
    raw_paths = pair.get("source_paths")
    if raw_paths is None:
        raw_paths = [pair.get("source_path")]
    if not isinstance(raw_paths, list) or not all(isinstance(raw_path, str) for raw_path in raw_paths):
        raise ValueError(f"{pair.get('name', '<unnamed>')} source_paths must be a list of strings")
    return [expand_contract_path(raw_path, local_root, obsidian_root) for raw_path in raw_paths]


def resolve_target_paths(pair: dict[str, Any], local_root: Path, obsidian_root: Path) -> list[dict[str, Any]]:
    raw_targets = pair.get("target_paths")
    if raw_targets is None:
        raw_targets = [pair.get("target_path")]
    if not isinstance(raw_targets, list):
        raise ValueError(f"{pair.get('name', '<unnamed>')} target_paths must be a list")
    targets = normalize_targets(raw_targets)
    for target in targets:
        target["resolved_path"] = expand_contract_path(target["path"], local_root, obsidian_root)
    return targets


def load_contract(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing doc sync contract: {path}")
    with path.open(encoding="utf-8") as handle:
        contract = json.load(handle)
    if not isinstance(contract.get("pairs"), list):
        raise ValueError("doc sync contract must contain pairs[]")
    return contract


def check_mtime(
    pair_name: str,
    source_paths: list[Path],
    target_paths: list[Path],
    grace_seconds: int,
) -> list[str]:
    newest_source = max(path.stat().st_mtime for path in source_paths)
    oldest_target = min(path.stat().st_mtime for path in target_paths)
    if newest_source <= oldest_target + grace_seconds:
        return []

    newest_sources = [path for path in source_paths if path.stat().st_mtime == newest_source]
    oldest_targets = [path for path in target_paths if path.stat().st_mtime == oldest_target]
    return [
        f"{pair_name}: source doc is newer than Obsidian target; sync required "
        f"(newest source: {newest_sources[0]}, oldest target: {oldest_targets[0]})"
    ]


def check_pair(
    pair: dict[str, Any],
    local_root: Path,
    obsidian_root: Path,
    default_fail_if_source_newer: bool,
    default_grace_seconds: int,
) -> list[str]:
    pair_name = str(pair.get("name", "<unnamed>"))
    source_paths = resolve_source_paths(pair, local_root, obsidian_root)
    targets = resolve_target_paths(pair, local_root, obsidian_root)
    target_paths = [target["resolved_path"] for target in targets]

    source_text = "\n\n".join(read_text(path) for path in source_paths)
    target_texts = {path: read_text(path) for path in target_paths}
    common_markers = pair.get("common_markers", [])
    if not isinstance(common_markers, list) or not all(isinstance(marker, str) for marker in common_markers):
        raise ValueError(f"{pair_name} common_markers must be a list of strings")

    errors: list[str] = []
    missing_in_source = missing_markers(source_text, common_markers)
    if missing_in_source:
        errors.append(f"{pair_name}: source docs missing common markers: {', '.join(missing_in_source)}")

    for target in targets:
        target_path = target["resolved_path"]
        target_text = target_texts[target_path]
        missing_common = missing_markers(target_text, common_markers)
        missing_specific = missing_markers(target_text, target["markers"])
        if missing_common:
            errors.append(f"{pair_name}: {target_path} missing common markers: {', '.join(missing_common)}")
        if missing_specific:
            errors.append(f"{pair_name}: {target_path} missing target markers: {', '.join(missing_specific)}")

    fail_if_source_newer = bool(pair.get("fail_if_source_newer_than_target", default_fail_if_source_newer))
    grace_seconds = int(pair.get("mtime_grace_seconds", default_grace_seconds))
    if fail_if_source_newer:
        errors.extend(check_mtime(pair_name, source_paths, target_paths, grace_seconds))
    return errors


def run_checks(contract_path: Path, local_root: Path, obsidian_root: Path) -> list[str]:
    contract = load_contract(contract_path)
    defaults = contract.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("doc sync contract defaults must be an object")
    fail_if_source_newer = bool(defaults.get("fail_if_source_newer_than_target", True))
    grace_seconds = int(defaults.get("mtime_grace_seconds", 5))

    errors: list[str] = []
    for pair in contract["pairs"]:
        if not isinstance(pair, dict):
            raise ValueError(f"invalid pair definition: {pair!r}")
        errors.extend(check_pair(pair, local_root, obsidian_root, fail_if_source_newer, grace_seconds))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="检查本地执行文档与 Obsidian 协议文档是否同步")
    parser.add_argument("--local-root", default=str(default_local_root()), help="本地素材根目录")
    parser.add_argument("--obsidian-root", default=str(DEFAULT_OBSIDIAN_ROOT), help="Obsidian 自媒体库根目录")
    parser.add_argument("--contract", default=None, help="doc_sync_contract.json 路径")
    args = parser.parse_args()

    local_root = Path(args.local_root).expanduser().resolve()
    obsidian_root = Path(args.obsidian_root).expanduser().resolve()
    contract_path = Path(args.contract).expanduser().resolve() if args.contract else default_contract_path(local_root)

    errors = run_checks(contract_path, local_root, obsidian_root)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Obsidian 文档同步检查失败：\n{details}")

    print("本地执行文档 ↔ Obsidian 协议文档同步检查通过")


if __name__ == "__main__":
    main()
