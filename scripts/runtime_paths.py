#!/usr/bin/env python3
"""Cross-platform runtime path helpers used by setup, CI and the studio app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 11)
RUNTIME_NAME = ".venv"
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
        if (candidate / "scripts").is_dir() and (candidate / "studio").is_dir() and (candidate / "requirements-dev.txt").is_file():
            return candidate
    raise RuntimeError(f"cannot locate repository root from {path}")


def local_media_root(value: Path | None = None) -> Path:
    """The sole media-root configuration; independent of the software checkout."""
    configured = value or os.environ.get("LOCAL_MEDIA_ROOT", "").strip()
    root = Path(configured).expanduser() if configured else Path.home() / "Desktop" / "照片筛选"
    return root.resolve()


def workspace_root(anchor: Path | None = None) -> Path:
    return local_media_root()


def runtime_dir(repo_root: Path | None = None) -> Path:
    root = repo_root.expanduser() if repo_root is not None else repository_root()
    return root / RUNTIME_NAME


def is_windows(platform: str | None = None) -> bool:
    """True when `platform` (or the running host, if omitted) is Windows.

    `platform`, when given, is matched by its "win" prefix (accepts values
    like "win32"/"windows"). When omitted, also falls back to `os.name ==
    "nt"` so this still resolves correctly on a host whose `sys.platform`
    string doesn't start with "win" (pe-10). Baseline: runtime_python's and
    runtime_pip's identical two-line check, also duplicated verbatim in
    probe_jianying_environment.jianying_root_candidates. Deliberately NOT
    consulted by platform_contract_name() below, which is a pure mapper over
    the platform string only -- see its own docstring.
    """
    name = (platform or sys.platform).lower()
    return name.startswith("win") or (os.name == "nt" and platform is None)


def runtime_python(repo_root: Path | None = None, *, platform: str | None = None) -> Path:
    runtime = runtime_dir(repo_root)
    if is_windows(platform):
        return runtime / "Scripts" / "python.exe"
    return runtime / "bin" / "python"


def runtime_pip(repo_root: Path | None = None, *, platform: str | None = None) -> Path:
    runtime = runtime_dir(repo_root)
    if is_windows(platform):
        return runtime / "Scripts" / "pip.exe"
    return runtime / "bin" / "pip"


def supported_python(version: tuple[int, ...] | None = None) -> bool:
    current = version or tuple(sys.version_info[:3])
    return current >= MINIMUM_PYTHON


def platform_contract_name(platform: str | None = None) -> str:
    """Map a platform string to its contract name (used to name contract artifacts).

    Deliberately a pure function of `platform`/`sys.platform` only -- unlike
    is_windows() above, it does NOT fall back to `os.name == "nt"`. Folding
    that fallback in here would change what this returns for `platform=None`
    on a Windows host in exactly the edge case the pure string check avoids,
    which openclaw_product_contract.py relies on to name contract artifacts.
    Not a "fourth spelling" of is_windows() -- keep it independent (pe-10).
    """
    name = (platform or sys.platform).lower()
    if name.startswith("darwin"):
        return "macos"
    if name.startswith("win"):
        return "windows"
    if name.startswith("linux"):
        return "linux"
    return name
