#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OTIO_KDENLIVE_PYTHON="$RUNNER_ROOT/.venv-content-os/bin/python"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! "$PYTHON_BIN" -c 'import sys' >/dev/null 2>&1; then
  echo "Python runtime is unavailable or invalid: $PYTHON_BIN" >&2
  exit 1
fi

echo "== Python version =="
"$PYTHON_BIN" --version

echo "== Compile scripts =="
"$PYTHON_BIN" -m compileall "$SCRIPT_DIR"

echo "== Check required Python packages =="
"$PYTHON_BIN" - <<'PY'
from importlib import metadata

required = {
    "pyjianyingdraft": "0.2.6",
}

for package, expected in required.items():
    actual = metadata.version(package)
    if actual != expected:
        raise SystemExit(f"{package} version mismatch: expected {expected}, got {actual}")

import pyJianYingDraft  # noqa: F401
PY

echo "== Check fixed OTIO/Kdenlive runtime =="
if [[ ! -x "$OTIO_KDENLIVE_PYTHON" ]]; then
  echo "OTIO/Kdenlive runtime missing: $OTIO_KDENLIVE_PYTHON" >&2
  exit 1
fi
"$OTIO_KDENLIVE_PYTHON" - <<'PY'
from importlib import metadata

expected = "0.18.1"
actual = metadata.version("opentimelineio")
if actual != expected:
    raise SystemExit(f"opentimelineio version mismatch: expected {expected}, got {actual}")

import opentimelineio  # noqa: F401
PY

echo "== Check disallowed Python features =="
if grep -R "\.bit_count(" "$SCRIPT_DIR" --include="*.py"; then
  echo "Direct .bit_count() usage found. Current runtime contract is Python 3.9." >&2
  exit 1
fi

echo "Runtime contract check passed."
