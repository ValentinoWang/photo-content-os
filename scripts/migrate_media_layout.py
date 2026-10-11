#!/usr/bin/env python3
"""Apply an explicit media rename plan with byte-preservation verification."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def inventory(roots: list[Path]) -> dict[str, dict[str, object]]:
    result = {}
    for root in roots:
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise ValueError(f'symlink requires explicit review: {path}')
            if path.is_file():
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                        digest.update(chunk)
                result[str(path)] = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
    return result


def apply_plan(plan: dict, *, execute: bool, evidence: Path) -> dict:
    moves = [(Path(m['from']), Path(m['to'])) for m in plan['moves']]
    if len({str(s) for s, _ in moves}) != len(moves) or len({str(d) for _, d in moves}) != len(moves):
        raise ValueError('duplicate source or target')
    before = inventory([Path(p) for p in plan['roots']])
    for source, target in moves:
        if not source.exists():
            raise FileNotFoundError(source)
        if target.exists() and not source.samefile(target):
            raise FileExistsError(target)
        print(f'{source} -> {target}')
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'before-files.json').write_text(json.dumps(before, ensure_ascii=False, indent=2))
    totals = {'files': len(before), 'bytes': sum(x['bytes'] for x in before.values())}
    if not execute:
        result = {'dry_run': True, 'moves': len(moves), 'before': totals}
    else:
        # Sources remain in their original tree until their deepest children move.
        for source, target in sorted(moves, key=lambda m: len(m[0].parts), reverse=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and source.samefile(target) and source.name != target.name:
                temporary = source.with_name(".migration-case-rename")
                if temporary.exists():
                    raise FileExistsError(temporary)
                source.rename(temporary)
                temporary.rename(target)
            else:
                source.rename(target)
        after = inventory([Path(p) for p in plan['final_roots']])
        expected = {}
        for name, record in before.items():
            path = Path(name)
            for source, target in sorted(moves, key=lambda m: len(m[0].parts), reverse=True):
                if path == source or source in path.parents:
                    path = target / path.relative_to(source)
            expected[str(path)] = record
        if expected != after:
            raise RuntimeError('file identities, byte counts or hashes changed during rename; retain evidence and stop')
        result = {'dry_run': False, 'moves': len(moves), 'before': totals,
                  'after': {'files': len(after), 'bytes': sum(x['bytes'] for x in after.values())}, 'hashes_equal': True}
        (evidence / 'after-files.json').write_text(json.dumps(after, ensure_ascii=False, indent=2))
    (evidence / ('dry-run.json' if not execute else 'migration.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    apply_plan(json.loads(args.plan.read_text()), execute=args.execute, evidence=args.evidence)

if __name__ == '__main__':
    main()
