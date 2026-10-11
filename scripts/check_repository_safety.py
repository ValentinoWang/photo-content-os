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
    "00_Inbox_Mac_Intake",
    "01_Project_Workspace",
    "02_Asset_Library",
    "03_Jianying_Active_Drafts",
    "04_Delivery_External",
    "05_Archive_Cold_Storage",
    "90_SSOT_E2E",
    "_OpenClawQueue",
    "demo_workspace",
}
PROHIBITED_PARTS = {
    ".venv-content-os",
    "App_WorkCache",
    ANALYSIS_DIR,
    "_openclaw",
    "restructure_audit",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Git 跟踪文件是否越过协作仓库安全边界")
    parser.add_argument("--root", type=Path, default=repository_root(), help="Git 仓库根目录")
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    failures: list[str] = []
    for relative in tracked_paths(root):
        for violation in path_violations(root, relative):
            failures.append(f"{relative.as_posix()}: {violation}")

    if failures:
        print("repository safety check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Repository safety check passed.")


if __name__ == "__main__":
    main()
