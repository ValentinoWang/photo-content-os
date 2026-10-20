#!/usr/bin/env python3
"""Install locked editing tools inside this checkout; never modify global tools."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

from edit_tools_runtime import ROOT, node_path, read_lock, tool_status


def run(command, *, cwd=None, env=None):
    print('+ ' + ' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, env=env, check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def matching_node(path, version):
    try:
        return subprocess.run([str(path), '--version'], capture_output=True, text=True,
                              check=True, timeout=10).stdout.strip() == 'v' + version
    except (OSError, subprocess.SubprocessError):
        return False


def install_node(root, spec):
    target = root / '.tools/node'
    node = node_path(root)
    if matching_node(node, spec['version']):
        return node
    if target.exists() or target.is_symlink():
        print('Node 版本不一致或损坏，重新安装。', flush=True)
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    system = shutil.which('node')
    # Both node and npm must belong to the matching distribution.
    if system and matching_node(system, spec['version']):
        prefix = Path(system).resolve().parent
        distribution = prefix if os.name == 'nt' else prefix.parent
        if (distribution / ('node_modules/npm/bin/npm-cli.js' if os.name == 'nt' else 'lib/node_modules/npm/bin/npm-cli.js')).is_file():
            target.symlink_to(distribution, target_is_directory=True)
            return node
    machine = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'x64', 'amd64': 'x64'}.get(platform.machine().lower())
    system_name = {'Darwin': 'darwin', 'Linux': 'linux', 'Windows': 'win'}.get(platform.system())
    key = f'{system_name}-{machine}'
    artifact = spec['artifacts'][key]
    with tempfile.TemporaryDirectory(prefix='node-install-', dir=root / '.tools') as temp:
        temp = Path(temp)
        archive = temp / artifact['file']
        print(f"Node {spec['version']}: 下载并校验固定安装包。", flush=True)
        urllib.request.urlretrieve(f"https://nodejs.org/dist/v{spec['version']}/{artifact['file']}", archive)
        if digest(archive) != artifact['sha256']:
            raise ValueError('Node archive SHA-256 mismatch')
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(temp)
        else:
            with tarfile.open(archive) as handle:
                # Archives are authenticated against the pinned official SHA-256 above.
                handle.extractall(temp)
        shutil.move(str(temp / artifact['file'].removesuffix('.tar.gz').removesuffix('.zip')), target)
    if not matching_node(node, spec['version']):
        raise ValueError('installed Node version mismatch')
    return node


def install(root=ROOT):
    lock = read_lock(root)
    tools = root / '.tools'
    tools.mkdir(exist_ok=True)
    node = install_node(root, lock['node'])
    npm = tools / 'node' / ('node_modules/npm/bin/npm-cli.js' if os.name == 'nt' else 'lib/node_modules/npm/bin/npm-cli.js')
    env = {**os.environ, 'PATH': str(node.parent) + os.pathsep + os.environ.get('PATH', ''),
           'PLAYWRIGHT_BROWSERS_PATH': str(tools / 'browsers'), 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD': '1',
           'ELECTRON_SKIP_BINARY_DOWNLOAD': '1'}
    lock_hash = hashlib.sha256((root / 'third_party/edit-tools.lock.json').read_bytes()).hexdigest()
    stamp = tools / 'edit-tools-installed.json'
    for name, spec in lock['tools'].items():
        path = root / spec['directory']
        status = tool_status(name, root)
        healthy = status['status'] == 'online'
        if healthy:
            print(f'{name}: 已安装且版本匹配，跳过。', flush=True)
            continue
        print(f"{name}: 当前版本 {status['version'] or '未知'}，要求 {spec['version']}；{status['reason']}；重新安装。", flush=True)
        if spec['source_type'] == 'git':
            reusable = (path / '.git').is_dir() and not (path / '.git').is_symlink()
            if reusable:
                remote = subprocess.run(['git', '-C', str(path), 'remote', 'get-url', 'origin'],
                                        capture_output=True, text=True, check=True).stdout.strip()
                reusable = remote == spec['url']
            if not reusable:
                if path.exists():
                    shutil.rmtree(path)
                path.mkdir(parents=True)
                run(['git', 'init', path])
                run(['git', 'remote', 'add', 'origin', spec['url']], cwd=path)
            present = subprocess.run(['git', '-C', str(path), 'cat-file', '-e', spec['commit'] + '^{commit}'],
                                     capture_output=True).returncode == 0
            if not present:
                run(['git', '-c', 'http.version=HTTP/1.1', 'fetch', '--depth=1', 'origin', spec['commit']], cwd=path)
            run(['git', 'checkout', '--detach', '--force', spec['commit']], cwd=path)
            run(['git', 'clean', '-fd'], cwd=path)
            if digest(path / 'package-lock.json') != spec['package_lock_sha256']:
                raise ValueError(f'{name}: upstream package-lock mismatch')
        else:
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
            for file in ['package.json', 'package-lock.json']:
                shutil.copy2(root / 'third_party' / name / file, path / file)
        marker = path / '.content-os-installed.json'
        marker.unlink(missing_ok=True)
        run([node, npm, 'ci', '--no-audit', '--no-fund'], cwd=path, env=env)
        if name == 'openchatcut':
            # Upstream does not declare Playwright; use the separately locked host runtime.
            browser_pkg = Path('../../browser-runtime/node_modules')
            for package in ['playwright', 'playwright-core']:
                link = path / 'node_modules' / package
                if link.is_symlink():
                    link.unlink()
                link.symlink_to(browser_pkg / package, target_is_directory=True)
        marker.write_text(json.dumps({'version': spec['version'], 'package_lock_sha256': digest(path / 'package-lock.json')}) + '\n')
    browser_runtime = tools / 'browser-runtime'
    browser_runtime.mkdir(exist_ok=True)
    for file in ['package.json', 'package-lock.json']:
        shutil.copy2(root / 'third_party/browser-runtime' / file, browser_runtime / file)
    run([node, npm, 'ci', '--no-audit', '--no-fund'], cwd=browser_runtime, env=env)
    run([node, browser_runtime / 'node_modules/playwright/cli.js', 'install', 'chromium'], env=env)
    for name in lock['tools']:
        status = tool_status(name, root)
        if status['status'] != 'online':
            raise ValueError(f"{name}: {status['reason']}")
    stamp.write_text(json.dumps({'lock_sha256': lock_hash, **{name: digest(root / spec['directory'] / 'package-lock.json')
                                                          for name, spec in lock['tools'].items()}}, indent=2) + '\n')
    print('剪辑工具安装完成。', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--music-analysis', action='store_true', help='install only the isolated music analysis runtime')
    args = parser.parse_args()
    try:
        if args.music_analysis:
            from music_analysis.install import install as install_music
            install_music(ROOT)
        else:
            install()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f'剪辑工具安装失败：{exc}；修复后重跑 python3 scripts/setup_edit_tools.py。未切换版本或后端。', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
