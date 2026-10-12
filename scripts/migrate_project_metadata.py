#!/usr/bin/env python3
"""Update local manifest and index paths after a verified media rename."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from migrate_media_layout import mapped_path
from rewrite_media_references import replace_fields, sha256, string_fields, write_atomic

PATH_KEYS = {'path', 'paths', 'file', 'files', 'frame', 'frames', 'source', 'target', 'group',
             'from', 'to', 'output', 'artifacts', 'keyframes', 'contact_sheet', 'addition_contact_sheet',
             'audio_wav', 'preview_video', 'captions_srt', 'source_project'}


def path_field(pointer: str) -> bool:
    key = next((part for part in reversed(pointer.split('/')) if not part.isdigit()), '')
    return key in PATH_KEYS or key.endswith(('_path', '_paths', '_dir', '_dirs', '_file', '_files', '_root'))


def project_roots(plan: dict) -> list[Path]:
    root = Path(plan['roots'][1])
    return sorted(Path(move['from']) for move in plan['moves']
                  if root in Path(move['from']).parents
                  and len(Path(move['from']).relative_to(root).parts) in (1, 2)
                  and Path(move['from']).suffix == '')


def migrate(plan: dict, before: dict, *, evidence: Path, execute: bool) -> dict:
    mapping = {Path(move['from']): Path(move['to']) for move in plan['moves']}
    roots = [Path(root) for root in plan['roots']]
    media = roots[0].parent
    projects = project_roots(plan)
    known = {Path(name) for name in before} | set(mapping)
    names = {path.name: mapped_path(path, mapping).name for path in projects}
    records, unparseable, titles, index = [], [], [], {}
    final_paths = {source: mapped_path(source, mapping) for source in mapping}
    markdown_patterns = {}
    previous_file = evidence / 'metadata-migration.json'
    previous = {record['file']: record for record in json.loads(previous_file.read_bytes())['records']} if previous_file.exists() else {}

    def bound_project(original: Path) -> Path | None:
        return next((root for root in sorted(projects, key=lambda p: len(p.parts), reverse=True)
                     if root in original.parents or root == original), None)

    def relink(value: str, original: Path, key: str = '') -> str:
        if not value or '\n' in value:
            return value
        source = Path(value)
        if source.is_absolute():
            if media not in source.parents and source != media:
                return value
            return str(mapped_path(source, mapping)) + ('/' if value.endswith('/') else '')
        if key == 'source_project' and value in names:
            return names[value]
        project = bound_project(original)
        anchors = [project, original.parent, media, roots[2]] if project else [original.parent, media, roots[2]]
        for anchor in (p for p in anchors if p is not None):
            source = anchor / value
            target = mapped_path(source, mapping)
            if source not in known and not any(parent in mapping for parent in source.parents):
                continue
            new_anchor = mapped_path(anchor, mapping)
            try:
                relative = target.relative_to(new_anchor).as_posix()
            except ValueError:
                relative = str(target)
            if relative != value:
                return relative + ('/' if value.endswith('/') else '')
        return value

    def markdown(text: str, original: Path) -> str:
        project = bound_project(original)
        if project not in markdown_patterns:
            replacements = {}
            for source, final in final_paths.items():
                replacements[str(source)] = str(final)
                for anchor in [project, media, roots[2]]:
                    if anchor is None:
                        continue
                    try:
                        old = source.relative_to(anchor).as_posix()
                        new = final.relative_to(mapped_path(anchor, mapping)).as_posix()
                    except ValueError:
                        continue
                    if old != new:
                        replacements[old] = new
            for source, target in plan.get('software_moves', []):
                if plan.get('software_source_root') and source.startswith(plan['software_source_root'] + '/'):
                    replacements[source] = str(Path(plan['software_root']) / target)
                    old_parts, new_parts = Path(source).parts[:-1], Path(target).parts[:-1]
                    if len(old_parts) == len(new_parts) + 1:
                        for length in range(1, len(old_parts) + 1):
                            replacements[str(Path(*old_parts[:length]))] = str(Path(plan['software_root']).joinpath(*new_parts[:length - 1]))
                    if Path(source).name != Path(target).name:
                        replacements[Path(source).name] = Path(target).name
            pattern = re.compile('|'.join(re.escape(key) for key in sorted(replacements, key=len, reverse=True)))
            absolute = re.compile('|'.join(re.escape(key) for key in sorted(replacements, key=len, reverse=True) if key.startswith('/')))
            markdown_patterns[project] = (replacements, pattern, absolute)
        replacements, pattern, absolute = markdown_patterns[project]
        def replace_span(match: re.Match) -> str:
            return pattern.sub(lambda found: replacements[found.group()], match.group())
        # Path-bearing spans and labelled path lines; ordinary Chinese prose stays intact.
        text = re.sub(r'`[^`\n]+`|\]\([^\n)]+\)', replace_span, text)
        text = re.sub(r'^.*(?:路径|位置|目录|文件|source|target|project).*$', replace_span, text, flags=re.MULTILINE)
        text = re.sub(r'```[^\n]*\n[\s\S]*?```', replace_span, text)
        return absolute.sub(lambda match: replacements[match.group()], text)

    for name, identity in sorted(before.items()):
        original = Path(name)
        if original.suffix.lower() not in {'.json', '.md', '.yaml', '.yml', '.csv', '.txt'}:
            continue
        current = mapped_path(original, mapping)
        current_raw = current.read_bytes()
        raw = current_raw
        if sha256(raw) != identity['sha256']:
            prior = previous.get(str(current))
            if prior is None or sha256(raw) != prior['after_sha256']:
                raise ValueError(f'metadata changed outside the recorded migration: {current}')
            raw = Path(prior['backup']).read_bytes()
            if sha256(raw) != identity['sha256']:
                raise ValueError(f'metadata backup drift: {current}')
        if original.suffix.lower() == '.json':
            try:
                fields = string_fields(raw)
            except (ValueError, UnicodeDecodeError):
                unparseable.append(str(current))
                continue
            changes = []
            for pointer, (_, _, value) in fields.items():
                is_existing_absolute = value.startswith(str(media) + '/') and mapped_path(Path(value), mapping).exists()
                if not path_field(pointer) and not is_existing_absolute:
                    continue
                target = relink(value, original, pointer.rsplit('/', 1)[-1])
                if target != value:
                    changes.append({'json_pointer': pointer, 'before': value, 'after': target})
            updated = replace_fields(raw, changes)
        else:
            updated = markdown(raw.decode('utf-8'), original).encode('utf-8')
            changes = []
        if updated == raw:
            continue
        backup = evidence / 'metadata-before' / ('metadata-' + sha256(str(original).encode())[:20] + original.suffix.lower())
        record = {'file': str(current), 'original_file': str(original), 'backup': str(backup),
                  'before_sha256': sha256(raw), 'after_sha256': sha256(updated), 'changes': changes}
        records.append(record)
        if execute:
            if backup.exists() and backup.read_bytes() != raw:
                raise FileExistsError(backup)
            write_atomic(backup, raw)
            with (evidence / 'metadata-records.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            if current_raw != updated:
                write_atomic(current, updated)
    for project in projects:
        current = mapped_path(project, mapping)
        if not current.is_dir():
            raise FileNotFoundError(current)
        data = {'title': project.name, 'directory': current.name}
        manifest = current / 'project-manifest.json'
        if manifest.exists() and json.loads(manifest.read_bytes()) != data:
            raise FileExistsError(f'project manifest differs from migration: {manifest}')
        titles.append({'file': str(manifest), 'title': project.name})
        if len(project.relative_to(roots[1]).parts) == 2:
            index[project.name] = str(current)
        if execute and not manifest.exists():
            write_atomic(manifest, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
    index_path = mapped_path(roots[1], mapping) / '.content-os-project-index.json'
    if index_path.exists() and json.loads(index_path.read_bytes()) != index:
        raise FileExistsError(f'project index differs from migration: {index_path}')
    if execute and not index_path.exists():
        write_atomic(index_path, (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode())
    result = {'dry_run': not execute, 'records': records, 'titles': titles, 'index': str(index_path),
              'project_index': index, 'unparseable_unchanged': unparseable}
    evidence.mkdir(parents=True, exist_ok=True)
    write_atomic(evidence / ('metadata-migration.json' if execute else 'metadata-plan.json'),
                 (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'metadata_files': len(records), 'title_manifests': len(titles),
                      'indexed_projects': len(index), 'dry_run': not execute}))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--before-files', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    migrate(json.loads(args.plan.read_bytes()), json.loads(args.before_files.read_bytes()),
            evidence=args.evidence, execute=args.execute)


if __name__ == '__main__':
    main()
