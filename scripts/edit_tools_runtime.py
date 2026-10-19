"""Repository-owned editing runtime paths and fail-closed installation checks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INSTALL = 'python3 scripts/setup_edit_tools.py'


def read_lock(root=ROOT):
    value = json.loads((root / 'third_party/edit-tools.lock.json').read_text())
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('unsupported edit-tools lock schema')
    return value


def node_path(root=ROOT):
    return root / '.tools/node' / ('node.exe' if os.name == 'nt' else 'bin/node')


def browser_path(*, root=ROOT, headless=False):
    """Use Playwright's pinned platform registry, never a user's cache."""
    node = node_path(root)
    # Playwright computes OS-specific executable names and revision overrides.
    script = "const {chromium}=require('./node_modules/playwright'); console.log(chromium.executablePath())"
    if headless:
        script = "const {registry}=require('./node_modules/playwright-core/lib/coreBundle.js'); console.log(registry.registry.findExecutable('chromium-headless-shell').executablePath())"
    result = subprocess.run([str(node), '-e', script], cwd=root / ".tools/browser-runtime",
                            env={**os.environ, 'PLAYWRIGHT_BROWSERS_PATH': str(root / '.tools/browsers')},
                            capture_output=True, text=True, check=True, timeout=10)
    # Full Chromium works for rendering and visible refinement alike.
    return Path(result.stdout.strip())


def configured_browser(key, root=ROOT):
    override = os.environ.get(key)
    if override:
        return Path(override).expanduser().resolve()
    try:
        return browser_path(root=root)
    except (OSError, ValueError, subprocess.SubprocessError):
        return root / '.tools/browsers/NOT_INSTALLED'


def tool_status(name, root=ROOT):
    """A missing, unreadable or drifted runtime is never reported ready."""
    result = {'name': name, 'version': None, 'expected_version': 'unknown',
              'path': '.tools/' + name, 'installed': False, 'status': 'unavailable',
              'reason': '', 'action': INSTALL}
    try:
        lock = read_lock(root)
        spec = lock['tools'][name]
        path = root / spec['directory']
        result.update(expected_version=spec['version'], path=spec['directory'], installed=path.is_dir())
        package = path / ('node_modules/openfilm/package.json' if name == 'openfilm' else 'package.json')
        result['version'] = json.loads(package.read_text())['version']
        if result['version'] != spec['version']:
            raise ValueError('version mismatch')
        if name == 'openchatcut':
            commit = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                                    capture_output=True, text=True, check=True, timeout=10).stdout.strip()
            if commit != spec['commit']:
                raise ValueError('git commit mismatch')
            subprocess.run(['git', '-C', str(path), 'diff', '--quiet', 'HEAD'], check=True, timeout=10)
            for file in ['cli/main.ts', 'node_modules/tsx/dist/loader.mjs', 'node_modules/playwright/package.json']:
                if not (path / file).is_file():
                    raise ValueError(f'missing {file}')
        else:
            for file in ['node_modules/openfilm/src/render.mjs', 'node_modules/openfilm/src/host.mjs', 'node_modules/playwright-core/package.json']:
                if not (path / file).is_file():
                    raise ValueError(f'missing {file}')
            core = json.loads((path / 'node_modules/playwright-core/package.json').read_text())
            if core['version'] != lock['browser']['package_version']:
                raise ValueError('OpenFilm Playwright version mismatch')
        marker = json.loads((path / '.content-os-installed.json').read_text())
        if marker != {'version': spec['version'], 'package_lock_sha256': hashlib.sha256((path / 'package-lock.json').read_bytes()).hexdigest()}:
            raise ValueError('installation completion marker mismatch')
        expected_lock = spec['package_lock_sha256'] if name == 'openchatcut' else hashlib.sha256((root / 'third_party/openfilm/package-lock.json').read_bytes()).hexdigest()
        if marker['package_lock_sha256'] != expected_lock:
            raise ValueError('npm lock differs from repository lock')
        node = node_path(root)
        version = subprocess.run([str(node), '--version'], capture_output=True, text=True,
                                 check=True, timeout=10).stdout.strip()
        if version != 'v' + lock['node']['version']:
            raise ValueError(f'Node mismatch: {version}')
        browser = browser_path(root=root)
        if not browser.is_file():
            raise ValueError('Chromium missing')
        actual_browser = subprocess.run([str(browser), '--version'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if lock['browser']['version'] not in actual_browser.split():
            raise ValueError(f'Chromium executable version mismatch: {actual_browser}')
        if name == 'openfilm':
            shell = browser_path(root=root, headless=True)
            shell_version = subprocess.run([str(shell), '--version'], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
            if lock['browser']['version'] not in shell_version.split():
                raise ValueError('Chromium headless shell version mismatch')
        registry = json.loads((root / '.tools/browser-runtime/node_modules/playwright-core/browsers.json').read_text())
        chromium = next(b for b in registry['browsers'] if b['name'] == 'chromium')
        if chromium['revision'] != lock['browser']['revision'] or chromium['browserVersion'] != lock['browser']['version']:
            raise ValueError('Chromium version mismatch')
        if not (root / 'scripts/qa/with_chromium_slot.sh').is_file():
            raise ValueError('Chromium slot script missing')
        result.update(status='online', reason='locked versions verified', browser=str(browser.relative_to(root)))
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as exc:
        result['reason'] = f'{type(exc).__name__}: {exc}'.replace(str(root) + os.sep, '')
    return result
