#!/usr/bin/env python3
"""Rewrite local path references only in documents declared by the sync contract."""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path
from check_obsidian_doc_sync import load_contract, resolve_target_paths
from runtime_paths import repository_root, obsidian_root


def sync(mapping: dict[str, str], *, vault: Path, evidence: Path) -> list[str]:
    local = repository_root()
    contract = load_contract(local / "doc-sync-contract.json")
    targets = {target["resolved_path"] for pair in contract["pairs"]
               for target in resolve_target_paths(pair, local, vault)}
    pattern = re.compile("|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True)))
    updated = []
    evidence.mkdir(parents=True, exist_ok=True)
    for index, target in enumerate(sorted(targets)):
        source = target.read_text(encoding="utf-8")
        rewritten = pattern.sub(lambda match: mapping[match.group()], source)
        shutil.copy2(target, evidence / f"document-{index}.md")
        target.write_text(rewritten, encoding="utf-8")
        updated.append(str(target))
    (evidence / "updated-documents.json").write_text(json.dumps(updated, ensure_ascii=False, indent=2))
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    for target in sync(json.loads(args.mapping.read_text()), vault=obsidian_root(), evidence=args.evidence):
        print(target)

if __name__ == "__main__":
    main()
