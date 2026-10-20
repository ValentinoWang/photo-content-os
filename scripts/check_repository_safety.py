#!/usr/bin/env python3
"""Reject tracked personal workspaces, media, credentials, and large binaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from media_common import ANALYSIS_DIR
from runtime_paths import repository_root as _repository_root

MAX_TRACKED_FILE_BYTES = 5 * 1024 * 1024
PROHIBITED_TOP_LEVELS = {
    "inbox",
    "projects",
    "library",
    "jianying-drafts",
    "deliveries",
    "archive",
    "ssot-e2e",
    "openclaw-queue",
    "demo_workspace",
}
PROHIBITED_PARTS = {
    ".venv",
    ".tools",
    "node_modules",
    "work-cache",
    ANALYSIS_DIR,
    "openclaw",
    "restructure-audit",
}
PROHIBITED_MACHINE_NAMES = {
    ".ds_store",
}
PROHIBITED_NAMES = {
    ".env",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
PROHIBITED_SUFFIXES = {
    ".3gp",
    ".aac",
    ".aiff",
    ".arw",
    ".avi",
    ".bmp",
    ".cr2",
    ".cr3",
    ".dng",
    ".flac",
    ".gif",
    ".heic",
    ".heif",
    ".insv",
    ".jpeg",
    ".jpg",
    ".lrf",
    ".m2ts",
    ".m4a",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".nef",
    ".ogg",
    ".orf",
    ".osv",
    ".pem",
    ".png",
    ".raf",
    ".rw2",
    ".tif",
    ".tiff",
    ".wav",
    ".webp",
}


def repository_root() -> Path:
    """L-15: delegates to the marker-based runtime_paths.repository_root,
    anchored at this file, instead of this script's former hardcoded
    parents[2]. This CI safety gate now fails loudly (RuntimeError) rather
    than silently checking the wrong directory if it is ever run from
    outside a real checkout -- a strictly safer failure mode for a
    repository-safety check."""
    return _repository_root(Path(__file__))


def tracked_paths(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [Path(raw.decode("utf-8")) for raw in result.stdout.split(b"\0") if raw]


def path_violations(root: Path, relative: Path, *, check_media: bool = True) -> list[str]:
    violations: list[str] = []
    parts = relative.parts
    if parts and parts[0] in PROHIBITED_TOP_LEVELS:
        violations.append("personal workspace path")
    if any(part in PROHIBITED_PARTS for part in parts):
        violations.append("generated or machine-specific path")

    name_lower = relative.name.lower()
    if name_lower in PROHIBITED_MACHINE_NAMES:
        violations.append("machine-generated metadata")
    if name_lower in PROHIBITED_NAMES or name_lower.startswith(".env."):
        violations.append("credential filename")
    if relative.suffix.lower() == '.pem' or (check_media and relative.suffix.lower() in PROHIBITED_SUFFIXES):
        violations.append("media or private-key extension")

    absolute = root / relative
    if absolute.is_file() and absolute.stat().st_size > MAX_TRACKED_FILE_BYTES:
        violations.append(f"file exceeds {MAX_TRACKED_FILE_BYTES // (1024 * 1024)} MiB")
    return violations


# Runtime source only: docs and tests/fixtures retain historical/negative examples.
RUNTIME_SUFFIXES = {'.py', '.sh', '.ps1', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.html', '.css', '.json', '.yaml', '.yml', '.toml'}
MACHINE_PATH_TOKENS = ('/' + 'Users/', 'Opensource' + '_Tool', '自媒体' + '创作Agent')


def is_runtime_source(relative: Path) -> bool:
    return (bool(relative.parts) and relative.parts[0] in {'scripts', 'studio'}
            and relative.suffix in RUNTIME_SUFFIXES and 'fixtures' not in relative.parts
            and not relative.name.startswith('test_'))


def source_violations(root: Path, relative: Path) -> list[str]:
    if not is_runtime_source(relative):
        return []
    try:
        source = (root / relative).read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        return [f'machine-runtime-path: cannot read source ({type(exc).__name__}); restore readable UTF-8 source']
    return [f'machine-runtime-path:{number}: {token}; use repository paths or explicit environment configuration'
            for number, line in enumerate(source.splitlines(), 1)
            for token in MACHINE_PATH_TOKENS if token in line]


# Exact files only: neither an evidence directory nor a fixture directory is exempt.
MEDIA_ALLOWLIST = 'scripts/repository-safety-media-allowlist.json'
PATH_BASELINE = 'scripts/repository-safety-path-baseline.json'
LOCAL_PATH_TOKENS = ('/' + 'Users/', '/' + 'private/var/', '/' + 'home/')
MEDIA_SUFFIXES = PROHIBITED_SUFFIXES - {'.pem'}
MEDIA_REPAIR = '媒体可能含私人素材，不能进 Git；截图、帧图、视频和音频放 ~/.photo-content-os/evidence/<任务>/；仅公开测试图或图标可逐文件登记理由和 SHA-256'
PATH_REPAIR = '新增本机绝对路径会泄露本机信息；路径改成相对素材根，截图和帧图放 ~/.photo-content-os/evidence/<任务>/'


def privacy_scope(path: str) -> bool:
    return path.startswith(('evidence/', 'acceptance/', 'docs/tasks/'))


def privacy_input(path: str) -> bool:
    return privacy_scope(path) or Path(path).suffix.lower() in MEDIA_SUFFIXES or path in {MEDIA_ALLOWLIST, PATH_BASELINE}


def git_output(root: Path, *args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def git_snapshot(root: Path, ref: str | None, blobs: dict[str, bytes]) -> dict[str, bytes]:
    selected = {}
    command = ('ls-tree', '-rz', ref) if ref else ('ls-files', '--stage', '-z')
    for record in git_output(root, *command).split(b'\0'):
        if not record:
            continue
        metadata, raw_path = record.split(b'\t', 1)
        path = raw_path.decode('utf-8')
        fields = metadata.decode().split()
        if not ref and fields[2] != '0':
            raise ValueError(f'{path}: Git 索引冲突；先解决冲突再运行检查')
        if not privacy_input(path):
            continue
        oid = fields[2] if ref else fields[1]
        selected[path] = oid
    missing = sorted(set(selected.values()) - blobs.keys())
    if missing:
        batch = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'],
                               input=('\n'.join(missing) + '\n').encode(),
                               check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        offset = 0
        for oid in missing:
            end = batch.index(b'\n', offset)
            header = batch[offset:end].split()
            if len(header) != 3 or header[1] != b'blob':
                raise ValueError(f'Git 对象 {oid} 不可读取；fetch 完整对象后重跑检查')
            size = int(header[2])
            offset = end + 1
            blobs[oid] = batch[offset:offset + size]
            if len(blobs[oid]) != size or batch[offset + size:offset + size + 1] != b'\n':
                raise ValueError(f'Git 对象 {oid} 不完整；fetch 完整对象后重跑检查')
            offset += size + 1
    return {path: blobs[oid] for path, oid in selected.items()}


def worktree_snapshot(root: Path, index: dict[str, bytes]) -> dict[str, bytes]:
    result = dict(index)
    # Sparse files retain index contents; actual worktree deletions must not be hidden.
    deleted = set(git_output(root, 'ls-files', '--deleted', '-z').decode().split('\0'))
    for path in list(result):
        target = root / path
        if path in deleted:
            del result[path]
        elif target.is_symlink():
            result[path] = str(target.readlink()).encode()
        elif target.exists():
            result[path] = target.read_bytes()
    return result


def local_path_lines(snapshot: dict[str, bytes]) -> dict[str, dict[str, int]]:
    result = {}
    for path, content in snapshot.items():
        if not privacy_scope(path) or Path(path).suffix.lower() in MEDIA_SUFFIXES:
            continue
        if content.startswith((b'\xff\xfe', b'\xfe\xff')):
            text = content.decode('utf-16')
        elif b'\0' in content:
            # Known textual artifacts cannot evade inspection with NUL/invalid encoding.
            if Path(path).suffix.lower() in {'.json', '.jsonl', '.md', '.txt', '.log', '.yaml', '.yml', '.html', '.csv', '.xml', '.sh', '.py'}:
                raise ValueError(f'{path}: 文本含 NUL、无法检查；恢复可读 UTF-8 文本再运行检查')
            continue
        else:
            try:
                text = content.decode('utf-8-sig')
            except UnicodeError as exc:
                raise ValueError(f'{path}: 无法读取文本；恢复可读 UTF-8 文本再运行检查') from exc
        lines = Counter(hashlib.sha256(line.encode()).hexdigest() for line in text.splitlines()
                        if any(token in line for token in LOCAL_PATH_TOKENS))
        if lines:
            result[path] = dict(lines)
    return result


def load_policy(snapshot: dict[str, bytes], path: str, key: str) -> dict:
    try:
        value = json.loads(snapshot[path])
        if value['schema_version'] != 1 or not isinstance(value[key], dict):
            raise ValueError('invalid schema')
        for name in value[key]:
            if Path(name).is_absolute() or '..' in Path(name).parts or any(c in name for c in '*?['):
                raise ValueError('only exact repository-relative files are allowed')
        return value
    except (KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise ValueError(f'{path}: 安全清单缺失或格式无效；从 Git 恢复清单后重跑检查') from exc


def baseline_subset(current: dict, previous: dict) -> bool:
    return all(path in previous and all(digest in previous[path] and count <= previous[path][digest]
               for digest, count in lines.items()) for path, lines in current.items())


def privacy_violations(root: Path, base: str) -> list[str]:
    blobs: dict[str, bytes] = {}
    base_sha = git_output(root, 'rev-parse', '--verify', f'{base}^{{commit}}').decode().strip()
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', base_sha, 'HEAD'], check=True, stderr=subprocess.PIPE)
    base_snapshot = git_snapshot(root, base_sha, blobs)
    previous = load_policy(base_snapshot, PATH_BASELINE, 'entries') if PATH_BASELINE in base_snapshot else None
    commits = git_output(root, 'rev-list', '--reverse', f'{base_sha}..HEAD').decode().splitlines()
    snapshots = [(commit, git_snapshot(root, commit, blobs)) for commit in commits]
    index = git_snapshot(root, None, blobs)
    snapshots.extend([('暂存区', index), ('工作区', worktree_snapshot(root, index))])
    failures = []
    for label, snapshot in snapshots:
        policy = load_policy(snapshot, MEDIA_ALLOWLIST, 'files')
        baseline = load_policy(snapshot, PATH_BASELINE, 'entries')
        entries = baseline['entries']
        try:
            for path, lines in entries.items():
                if not privacy_scope(path) or not isinstance(lines, dict) or not lines:
                    raise ValueError('invalid entry')
                for digest, count in lines.items():
                    if not re.fullmatch('[0-9a-f]{64}', digest) or type(count) is not int or count <= 0:
                        raise ValueError('invalid line digest/count')
            anchor = baseline['source_commit']
            if not isinstance(anchor, str) or not re.fullmatch('[0-9a-f]{40,64}', anchor):
                raise ValueError('invalid source commit')
            if previous is not None:
                if anchor != previous['source_commit'] or not baseline_subset(entries, previous['entries']):
                    raise ValueError('清单只许变短，不许增加或改写存量来源')
            else:
                if anchor != base_sha:
                    raise ValueError('首次清单必须绑定检查基线提交')
            if previous is None and not baseline_subset(entries, local_path_lines(base_snapshot)):
                raise ValueError('清单包含来源提交不存在的条目')
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'{PATH_BASELINE}: {exc}；删掉新增条目，清单仅保留原有违规行散列') from exc
        actual = local_path_lines(snapshot)
        for path, lines in actual.items():
            if not baseline_subset({path: lines}, entries):
                failures.append(f'{label}: {path}: repository-local-path: {PATH_REPAIR}')
        for path, lines in entries.items():
            if not baseline_subset({path: lines}, actual):
                failures.append(f'{label}: {path}: repository-path-baseline-stale: 存量条目已消失或减少，请从 {PATH_BASELINE} 删掉对应条目或减少计数')
        for path, item in policy['files'].items():
            if (Path(path).suffix.lower() not in MEDIA_SUFFIXES or not isinstance(item, dict)
                    or not isinstance(item.get('reason'), str) or not item['reason'].strip()
                    or not isinstance(item.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', item['sha256'])):
                raise ValueError(f'{MEDIA_ALLOWLIST}: {path}: 白名单必须逐文件填写理由和 SHA-256；禁止目录通配')
        for path, content in snapshot.items():
            if Path(path).suffix.lower() not in MEDIA_SUFFIXES:
                continue
            item = policy['files'].get(path)
            if item is None or hashlib.sha256(content).hexdigest() != item['sha256']:
                failures.append(f'{label}: {path}: repository-private-media: {MEDIA_REPAIR}')
        previous = baseline
    return list(dict.fromkeys(failures))


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Git 跟踪文件是否越过协作仓库安全边界")
    parser.add_argument("--root", type=Path, default=repository_root(), help="Git 仓库根目录")
    parser.add_argument("--runtime-paths-only", action="store_true", help="只检查运行源码中的机器路径")
    parser.add_argument('--base', help='逐笔检查 base..HEAD（默认 origin/main，无远端时 HEAD），同时检查暂存区和工作区')
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    failures: list[str] = []
    checked_sources = 0
    for relative in tracked_paths(root):
        checked_sources += int(is_runtime_source(relative))
        violations = source_violations(root, relative)
        if not args.runtime_paths_only:
            violations += path_violations(root, relative, check_media=False)
        for violation in violations:
            failures.append(f"{relative.as_posix()}: {violation}")

    if not args.runtime_paths_only:
        try:
            base = args.base
            if base is None:
                probe = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', 'origin/main'], capture_output=True)
                base = 'origin/main' if probe.returncode == 0 else 'HEAD'
            failures.extend(privacy_violations(root, base))
        except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError) as exc:
            failures.append(f'repository-privacy-input: {exc}; 检查 --root/--base，恢复可读 Git 对象和安全清单后重跑')

    if checked_sources == 0:
        failures.append("machine-runtime-path: no tracked runtime sources; check --root and Git index")
    if failures:
        print("repository safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Repository safety check passed.")


if __name__ == "__main__":
    main()
