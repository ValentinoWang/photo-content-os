#!/usr/bin/env python3
"""Convenience wrapper for 99_System_OpenClaw/scripts/mac_openclaw_runner.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from mac_openclaw_runner import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
