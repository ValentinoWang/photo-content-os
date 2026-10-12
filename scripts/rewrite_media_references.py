#!/usr/bin/env python3
"""Relink explicitly authorized Jianying path fields without reserializing JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from migrate_media_layout import mapped_path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_atomic(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def string_fields(raw: bytes) -> dict[str, tuple[int, int, str]]:
    text = raw.decode('utf-8')
    json.loads(text)
    decoder = json.JSONDecoder()
    fields = {}

    def whitespace(pos: int) -> int:
        while pos < len(text) and text[pos] in ' \t\r\n':
            pos += 1
        return pos

    def visit(pos: int, pointer: str) -> int:
        pos = whitespace(pos)
        if text[pos] == '{':
            pos = whitespace(pos + 1)
            if text[pos] == '}':
                return pos + 1
            while True:
                key, end = decoder.raw_decode(text, pos)
                pos = whitespace(end)
                if text[pos] != ':':
                    raise ValueError('object separator missing')
                escaped = key.replace('~', '~0').replace('/', '~1')
                pos = whitespace(visit(pos + 1, pointer + '/' + escaped))
                if text[pos] == '}':
                    return pos + 1
                pos = whitespace(pos + 1)
        if text[pos] == '[':
            pos = whitespace(pos + 1)
            if text[pos] == ']':
                return pos + 1
            index = 0
            while True:
                pos = whitespace(visit(pos, pointer + '/' + str(index)))
                if text[pos] == ']':
                    return pos + 1
                pos = whitespace(pos + 1)
                index += 1
        value, end = decoder.raw_decode(text, pos)
        if isinstance(value, str):
            if pointer in fields:
                raise ValueError(f'duplicate JSON string field: {pointer}')
            fields[pointer] = (pos, end, value)
        return end

    visit(0, '')
    return fields


def replace_fields(raw: bytes, changes: list[dict]) -> bytes:
    fields = string_fields(raw)
    text = raw.decode('utf-8')
    spans = []
    seen = set()
    for change in changes:
        pointer = change['json_pointer']
        if pointer in seen:
            raise ValueError(f'duplicate replacement: {pointer}')
        seen.add(pointer)
        start, end, value = fields[pointer]
        if value != change['before']:
            raise ValueError(f'source field drift: {pointer}')
        spans.append((start, end, json.dumps(change['after'], ensure_ascii=False)))
    for start, end, replacement in sorted(spans, reverse=True):
        text = text[:start] + replacement + text[end:]
    return text.encode('utf-8')


def verify_rewrite(record: dict, *, require_targets: bool = True) -> dict:
    before = Path(record['backup']).read_bytes()
    after = Path(record['file']).read_bytes()
    if sha256(before) != record['before_sha256']:
        raise ValueError('backup hash drift')
    expected = replace_fields(before, record['changes'])
    if after != expected or sha256(after) != record['after_sha256']:
        raise ValueError('bytes outside authorized path replacements changed')
    parsed_expected = json.loads(before)
    for change in record['changes']:
        parts = [part.replace('~1', '/').replace('~0', '~')
                 for part in change['json_pointer'].split('/')[1:]]
        container = parsed_expected
        for part in parts[:-1]:
            container = container[int(part)] if isinstance(container, list) else container[part]
        key = int(parts[-1]) if isinstance(container, list) else parts[-1]
        container[key] = change['after']
    if json.loads(after) != parsed_expected:
        raise ValueError('JSON differs outside authorized paths')
    before_fields, after_fields = string_fields(before), string_fields(after)
    authorized = {change['json_pointer'] for change in record['changes']}
    if before_fields.keys() != after_fields.keys():
        raise ValueError('JSON shape changed')
    for pointer in before_fields:
        if pointer not in authorized and before_fields[pointer][2] != after_fields[pointer][2]:
            raise ValueError(f'unauthorized JSON field changed: {pointer}')
    missing = [change['after'] for change in record['changes'] if not Path(change['after']).is_file()]
    if require_targets and missing:
        raise FileNotFoundError(f'relinked media missing: {missing}')
    return {'file': record['file'], 'changed_fields': len(authorized),
            'only_authorized_bytes_changed': True, 'json_only_path_differences': True,
            'targets_exist': not missing}


def rewrite_drafts(plan: dict, *, draft_root: Path, backup_root: Path,
                   evidence: Path, execute: bool) -> dict:
    mapping = {Path(move['from']): Path(move['to']) for move in plan['moves']}
    media_root = Path(plan['roots'][0]).parent
    proposed, missing, skipped = [], [], []
    for path in sorted(draft_root.rglob('*.json')):
        raw = path.read_bytes()
        try:
            fields = string_fields(raw)
        except (ValueError, UnicodeDecodeError):
            skipped.append(str(path))
            continue
        changes = []
        for pointer, (_, _, value) in fields.items():
            if not value.startswith(str(media_root) + '/'):
                continue
            if pointer.rsplit('/', 1)[-1] not in {'path', 'source_path'}:
                raise ValueError(f'non-path field references media root: {path} {pointer}')
            source = Path(value)
            if not source.is_file():
                missing.append({'file': str(path), 'json_pointer': pointer, 'value': value})
                continue
            target = mapped_path(source, mapping)
            if target != source:
                changes.append({'json_pointer': pointer, 'before': value, 'after': str(target)})
        if changes:
            if path.is_symlink():
                raise ValueError(f'refusing to rewrite symlink: {path}')
            updated = replace_fields(raw, changes)
            proposed.append({'file': str(path), 'backup': str(backup_root / path.relative_to(draft_root)),
                             'before_sha256': sha256(raw), 'after_sha256': sha256(updated),
                             'bytes': len(raw), 'changes': changes})
    result = {'dry_run': not execute, 'records': proposed, 'unchanged_missing': missing,
              'unparseable_files_untouched': skipped}
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / 'draft-rewrite-plan.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    if execute:
        # Finish and verify all backups before the first source JSON is edited.
        for record in proposed:
            source, backup = Path(record['file']), Path(record['backup'])
            raw = source.read_bytes()
            if sha256(raw) != record['before_sha256']:
                raise ValueError(f'draft changed since preflight: {source}')
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                if backup.read_bytes() != raw:
                    raise FileExistsError(f'backup collision: {backup}')
            else:
                write_atomic(backup, raw)
            if sha256(backup.read_bytes()) != record['before_sha256']:
                raise ValueError(f'backup verification failed: {backup}')
        manifest = {'draft_root': str(draft_root), 'files': [
            {key: record[key] for key in ('file', 'backup', 'before_sha256', 'bytes')} for record in proposed]}
        (backup_root / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        for record in proposed:
            source = Path(record['file'])
            if sha256(source.read_bytes()) != record['before_sha256']:
                raise ValueError(f'draft changed after backup: {source}')
            write_atomic(source, replace_fields(Path(record['backup']).read_bytes(), record['changes']))
            verify_rewrite(record, require_targets=False)
        (evidence / 'draft-rewrite.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'changed_files': len(proposed), 'changed_fields': sum(len(x['changes']) for x in proposed),
                      'unchanged_missing': len(missing), 'dry_run': not execute}))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--draft-root', type=Path, required=True)
    parser.add_argument('--backup-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    rewrite_drafts(json.loads(args.plan.read_bytes()), draft_root=args.draft_root,
                   backup_root=args.backup_root, evidence=args.evidence, execute=args.execute)


if __name__ == '__main__':
    main()
