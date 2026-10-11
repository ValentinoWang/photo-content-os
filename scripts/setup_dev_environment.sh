#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$REPOSITORY_ROOT/99_System_OpenClaw/.venv-content-os"
RUNTIME_PYTHON="$RUNTIME_DIR/bin/python"
REQUIREMENTS_FILE="$REPOSITORY_ROOT/requirements-dev.txt"
BOOTSTRAP_PYTHON="${PYTHON_BIN:-python3}"

if [[ "${OS:-}" == "Windows_NT" ]]; then
  echo "检测到 Windows。请运行 PowerShell 入口：" >&2
  echo "  powershell -ExecutionPolicy Bypass -File 99_System_OpenClaw/scripts/41_setup_dev_environment.ps1" >&2
  exit 2
fi

check_supported_python() {
  "$1" - <<'PY'
import sys
minimum = (3, 11)
if sys.version_info < minimum:
    raise SystemExit(
        f"Python {minimum[0]}.{minimum[1]} or newer is required; found {sys.version.split()[0]}"
    )
PY
}

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
  echo "Development requirements are missing: $REQUIREMENTS_FILE" >&2
  exit 1
fi

if [[ -e "$RUNTIME_DIR" ]]; then
  if [[ ! -d "$RUNTIME_DIR" || ! -f "$RUNTIME_DIR/pyvenv.cfg" || ! -x "$RUNTIME_PYTHON" ]]; then
    echo "Existing fixed runtime is malformed; refusing to overwrite it: $RUNTIME_DIR" >&2
    exit 1
  fi
else
  if ! "$BOOTSTRAP_PYTHON" -c 'import sys' >/dev/null 2>&1; then
    echo "Bootstrap Python is unavailable or invalid: $BOOTSTRAP_PYTHON" >&2
    exit 1
  fi
  check_supported_python "$BOOTSTRAP_PYTHON"
  echo "== Create fixed development runtime =="
  "$BOOTSTRAP_PYTHON" -m venv "$RUNTIME_DIR"
fi

"$RUNTIME_PYTHON" - "$RUNTIME_DIR" <<'PY'
from pathlib import Path
import sys
expected = Path(sys.argv[1]).resolve()
actual = Path(sys.prefix).resolve()
if actual != expected:
    raise SystemExit(f"fixed runtime prefix mismatch: expected {expected}, got {actual}")
PY
check_supported_python "$RUNTIME_PYTHON"
if ! "$RUNTIME_PYTHON" -m pip --version >/dev/null 2>&1; then
  echo "Existing fixed runtime has an invalid pip installation; refusing to overwrite it: $RUNTIME_DIR" >&2
  exit 1
fi

echo "== Install pinned development dependencies =="
"$RUNTIME_PYTHON" -m pip install --upgrade pip
"$RUNTIME_PYTHON" -m pip install --upgrade --requirement "$REQUIREMENTS_FILE"

echo "== Verify fixed development runtime =="
PYTHON_BIN="$RUNTIME_PYTHON" bash "$SCRIPT_DIR/check_runtime_contract.sh"
"$RUNTIME_PYTHON" "$SCRIPT_DIR/43_content_os_doctor.py" --allow-offline

echo "Development environment is ready: $RUNTIME_DIR"
