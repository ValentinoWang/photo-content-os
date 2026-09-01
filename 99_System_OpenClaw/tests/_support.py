"""Shared helper for tests that load a script under 99_System_OpenClaw/scripts/
as a module via importlib, instead of each test file re-implementing the
same spec_from_file_location / module_from_spec / exec_module triple.

This module is local to the photo-content-os repo's own test suite. The
openclaw-media repo has its own independent sibling helper (also named
``_support.py``, under openclaw-tag-router/tests/); the two are not shared
across repos.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# Scripts are loaded by file path below, so sibling imports need the same
# module-search root that direct script execution receives from Python.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_script(
    filename_or_name: str,
    module_name: str | None = None,
    *,
    register: bool = False,
) -> ModuleType:
    filename = filename_or_name if filename_or_name.endswith(".py") else f"{filename_or_name}.py"
    name = module_name or Path(filename).stem
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
