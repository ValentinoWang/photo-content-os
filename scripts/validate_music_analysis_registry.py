#!/usr/bin/env python3
"""Validate music taxonomy structure, published identities, versioning and UI copy."""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def display_copy(registry):
    values = [k['name'] for k in registry['sections']['kinds']]
    for category in registry['tag_categories']:
        values.extend(category[k] for k in ('name', 'empty_text', 'uncertain_text') if k in category)
        values.extend(t['name'] for t in category['tags'] if t['name'])
    values.append(registry['display']['panel_title'])
    return values


def identities(registry):
    return [x['id'] for x in registry['sections']['kinds']] + [x['id'] for x in registry['analyzers']['tags']['models']] + [c['id'] for c in registry['tag_categories']] + [t['id'] for c in registry['tag_categories'] for t in c['tags']]


def validate(registry, previous=None):
    schema = json.loads((ROOT / 'schemas/music-analysis-registry.schema.json').read_text())
    errors = [f'{e.json_path}: {e.message}' for e in Draft202012Validator(schema).iter_errors(registry)]
    if errors:
        return errors
    ids = identities(registry)
    if len(ids) != len(set(ids)):
        errors.append('duplicate id')
    categories = {c['id'] for c in registry['tag_categories']}
    models = {m['id'] for m in registry['analyzers']['tags']['models'] if m['role'] == 'classifier'}
    for category in registry['tag_categories']:
        if category['model'] not in models:
            errors.append(f"{category['id']}: unknown model")
        for tag in category['tags']:
            if tag['status'] == 'active' and (not tag['name'] or not re.search('[\u4e00-\u9fff]', tag['name'])):
                errors.append(f"{tag['id']}: active tag needs Chinese name")
    display = registry['display']
    refs = display['panel_order'] + display['filter_order'] + [v for row in display['row'] for k, v in row.items() if k in ('category', 'fallback')]
    if set(refs) - categories:
        errors.append('display references unknown category')
    def thresholds(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if k.endswith('_score') and (not isinstance(v, (float, int)) or isinstance(v, bool) or not 0 <= v <= 1):
                    errors.append(f'{k}: threshold outside 0–1')
                thresholds(v)
        elif isinstance(value, list):
            for v in value:
                thresholds(v)
    thresholds(registry)
    if previous is not None and registry != previous:
        missing = set(identities(previous)) - set(ids)
        if missing:
            errors.append(f'published ids deleted: {sorted(missing)}; use deprecated')
        # An identity cannot be reused for another source label/model.
        old = {t['id']: (c['model'], t['source_label']) for c in previous['tag_categories'] for t in c['tags']}
        for c in registry['tag_categories']:
            for t in c['tags']:
                if t['id'] in old and old[t['id']] != (c['model'], t['source_label']):
                    errors.append(f"{t['id']}: published identity reused")
        if registry['registry_version'] != previous['registry_version'] + 1:
            errors.append('registry_version must increase by exactly 1')
        if len(registry['changelog']) != len(previous['changelog']) + 1 or registry['changelog'][:-1] != previous['changelog']:
            errors.append('append exactly one changelog entry; preserve history')
    if registry['changelog'][-1]['registry_version'] != registry['registry_version']:
        errors.append('latest changelog version does not match registry_version')
    return errors


def published_registry(base, root=ROOT):
    subprocess.run(['git', 'rev-parse', '--verify', base + '^{commit}'], cwd=root, check=True, capture_output=True)
    paths = subprocess.run(['git', 'ls-tree', '--name-only', base, '--', 'music-analysis.registry.json'], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    if not paths:
        return None  # This is the first publication; an unreadable base fails above.
    return json.loads(subprocess.run(['git', 'show', base + ':music-analysis.registry.json'], cwd=root, check=True, capture_output=True, text=True).stdout)


def check_copy(registry, checker):
    if not checker or not Path(checker).is_file():
        raise ValueError('set UI_COPY_QUALITY_CHECKER to Core ui-copy-quality/scripts/check_ui_copy_quality.py')
    with tempfile.TemporaryDirectory(prefix='music-copy-') as temp:
        path = Path(temp) / 'copy.html'
        path.write_text('<!doctype html><html lang="zh"><body>' + ''.join('<p>' + html.escape(s) + '</p>' for s in display_copy(registry)) + '</body></html>')
        result = subprocess.run([sys.executable, checker, str(path), '--project-root', temp], capture_output=True, text=True)
        if result.returncode:
            raise ValueError('UI copy check failed: ' + result.stdout + result.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path, default=ROOT / 'music-analysis.registry.json')
    parser.add_argument('--base', default='origin/main')
    parser.add_argument('--copy-checker', default=os.environ.get('UI_COPY_QUALITY_CHECKER'))
    args = parser.parse_args()
    try:
        registry = json.loads(args.registry.read_text())
        errors = validate(registry, published_registry(args.base))
        if errors:
            raise ValueError('; '.join(errors))
        check_copy(registry, args.copy_checker)
        print(f'music-analysis-registry OK: {len(identities(registry))} ids; {len(display_copy(registry))} copy entries')
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'music-analysis-registry: {exc}; repair schema/ids/version/changelog/copy; see docs/music-analysis-registry-guard.md', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
