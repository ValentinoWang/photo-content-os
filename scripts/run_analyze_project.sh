#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -x "$REPOSITORY_ROOT/99_System_OpenClaw/.venv-content-os/bin/python" ]]; then
  PYTHON_BIN="$REPOSITORY_ROOT/99_System_OpenClaw/.venv-content-os/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/run_analyze_project.py" "$@"
