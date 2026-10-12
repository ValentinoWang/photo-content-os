#!/usr/bin/env python3
"""Restore a completed, receipt-bound media migration without copying media."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from migrate_media_layout import inventory
from rewrite_media_references import sha256, write_atomic


def rollback(evidence: Path, *, execute: bool) -> dict:
    metadata = json.loads((evidence / 'metadata-migration.json').read_bytes())
    drafts = json.loads((evidence / 'draft-rewrite.json').read_bytes())
    final = json.loads((evidence / 'final-verification.json').read_bytes())
    expected_files = json.loads((evidence / 'final-files.json').read_bytes())
    if inventory([Path(root) for root in final['final_roots']]) != expected_files:
        raise ValueError('media tree edited since migration; refuse rollback')
    changes = metadata['records'] + drafts['records'] + final.get('extra_text_changes', [])
    for record in changes:
        path, backup = Path(record['file']), Path(record['backup'])
        if sha256(path.read_bytes()) != record['after_sha256']:
            raise ValueError(f'file edited since migration; refuse rollback: {path}')
        if sha256(backup.read_bytes()) != record['before_sha256']:
            raise ValueError(f'backup hash mismatch: {backup}')
    for record in final['created_files']:
        if sha256(Path(record['file']).read_bytes()) != record['sha256']:
            raise ValueError(f'new metadata edited since migration: {record["file"]}')
    operations = [json.loads(line) for line in (evidence / 'rename/completed-moves.jsonl').read_text().splitlines()]
    result = {'dry_run': not execute, 'restored_text_files': len(changes),
              'removed_created_metadata': len(final['created_files']), 'reverse_moves': len(operations)}
    if execute:
        for record in changes:
            write_atomic(Path(record['file']), Path(record['backup']).read_bytes())
        for record in final['created_files']:
            Path(record['file']).unlink()
        for operation in reversed(operations):
            source, target = Path(operation['from']), Path(operation['to'])
            if source.exists() and not source.samefile(target):
                raise FileExistsError(source)
            if source.exists() and source.samefile(target) and source.name != target.name:
                temporary = target.with_name('.rollback-case-rename')
                if temporary.exists():
                    raise FileExistsError(temporary)
                target.rename(temporary)
                temporary.rename(source)
            else:
                target.rename(source)
        before = json.loads((evidence / 'rename/before-files.json').read_bytes())
        actual = inventory([Path(root) for root in final['original_roots']])
        if actual != before:
            raise ValueError('rollback file hashes or counts differ from the original inventory')
        result['original_file_hashes_restored'] = True
        write_atomic(evidence / 'rollback-result.json', (json.dumps(result, indent=2) + '\n').encode())
    print(json.dumps(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    rollback(args.evidence, execute=args.execute)


if __name__ == '__main__':
    main()
