#!/usr/bin/env python3
"""Reject tracked personal workspaces, media, credentials, and large binaries."""

from __future__ import annotations

import argparse
import subprocess
import sys
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


def path_violations(root: Path, relative: Path) -> list[str]:
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
    if relative.suffix.lower() in PROHIBITED_SUFFIXES:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Git 跟踪文件是否越过协作仓库安全边界")
    parser.add_argument("--root", type=Path, default=repository_root(), help="Git 仓库根目录")
    parser.add_argument("--runtime-paths-only", action="store_true", help="只检查运行源码中的机器路径")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    failures: list[str] = []
    checked_sources = 0
    for relative in tracked_paths(root):
        checked_sources += int(is_runtime_source(relative))
        violations = source_violations(root, relative)
        if not args.runtime_paths_only:
            violations += path_violations(root, relative)
        for violation in violations:
            failures.append(f"{relative.as_posix()}: {violation}")

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
