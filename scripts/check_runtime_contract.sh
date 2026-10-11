#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXED_RUNTIME_PYTHON="$SCRIPT_DIR/../.venv-content-os/bin/python"
PYTHON_BIN="${PYTHON_BIN:-$FIXED_RUNTIME_PYTHON}"
exec "$PYTHON_BIN" "$SCRIPT_DIR/check_runtime_contract.py" "$@"
