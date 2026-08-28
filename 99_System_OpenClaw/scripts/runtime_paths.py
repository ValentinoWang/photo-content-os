#!/usr/bin/env python3
"""Cross-platform runtime path helpers used by setup, CI and the desktop app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 11)
RUNTIME_NAME = ".venv-content-os"
DEFAULT_OBSIDIAN_RELATIVE = Path("Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体")


def obsidian_root(value: Path | None = None) -> Path:
    """Resolve the vault from explicit config, environment, or host default."""
    if value is not None:
        return value.expanduser()
    configured = os.environ.get("OBSIDIAN_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / DEFAULT_OBSIDIAN_RELATIVE
    return Path.home() / "Obsidian" / "自媒体"


def repository_root(anchor: Path | None = None) -> Path:
    path = (anchor or Path(__file__)).expanduser().resolve()
    if path.is_file():
        path = path.parent
    for candidate in (path, *path.parents):
        if (candidate / "99_System_OpenClaw").is_dir() and (candidate / "requirements-dev.txt").is_file():
            return candidate
    raise RuntimeError(f"cannot locate repository root from {path}")


def runtime_dir(repo_root: Path | None = None) -> Path:
    root = repo_root.expanduser() if repo_root is not None else repository_root()
    return root / "99_System_OpenClaw" / RUNTIME_NAME


def runtime_python(repo_root: Path | None = None, *, platform: str | None = None) -> Path:
    runtime = runtime_dir(repo_root)
    platform_name = (platform or sys.platform).lower()
    if platform_name.startswith("win") or os.name == "nt" and platform is None:
        return runtime / "Scripts" / "python.exe"
    return runtime / "bin" / "python"


def runtime_pip(repo_root: Path | None = None, *, platform: str | None = None) -> Path:
    runtime = runtime_dir(repo_root)
    platform_name = (platform or sys.platform).lower()
    if platform_name.startswith("win") or os.name == "nt" and platform is None:
        return runtime / "Scripts" / "pip.exe"
    return runtime / "bin" / "pip"


def supported_python(version: tuple[int, ...] | None = None) -> bool:
    current = version or tuple(sys.version_info[:3])
    return current >= MINIMUM_PYTHON


def platform_contract_name(platform: str | None = None) -> str:
    name = (platform or sys.platform).lower()
    if name.startswith("darwin"):
        return "macos"
    if name.startswith("win"):
        return "windows"
    if name.startswith("linux"):
        return "linux"
    return name
