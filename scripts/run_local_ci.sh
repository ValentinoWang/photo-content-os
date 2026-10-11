#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="$REPOSITORY_ROOT/99_System_OpenClaw/.venv-content-os/bin/python"
DEFAULT_OBSIDIAN_ROOT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体"
OBSIDIAN_ROOT="${OBSIDIAN_ROOT:-$DEFAULT_OBSIDIAN_ROOT}"
TEMP_ROOT="${TMPDIR:-/tmp}"
TEMP_ROOT="${TEMP_ROOT%/}"
[[ -n "$TEMP_ROOT" ]] || TEMP_ROOT="/"

if [[ "${OS:-}" == "Windows_NT" ]]; then
  echo "检测到 Windows。请运行 42_run_local_ci.ps1。" >&2
  exit 2
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Fixed development runtime is missing: $PYTHON_BIN" >&2
  echo "Run: bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh" >&2
  exit 1
fi

DEMO_WORKSPACE="$(mktemp -d "$TEMP_ROOT/photo-content-os-ci.XXXXXX")"
cleanup() {
  if [[ -n "${DEMO_WORKSPACE:-}" && -d "$DEMO_WORKSPACE" && "$(basename "$DEMO_WORKSPACE")" == photo-content-os-ci.* ]]; then
    rm -rf -- "$DEMO_WORKSPACE"
  else
    echo "Refusing to clean an unexpected CI path: ${DEMO_WORKSPACE:-<empty>}" >&2
  fi
}
trap cleanup EXIT
cd "$REPOSITORY_ROOT"

echo "== Runtime contract =="
"$PYTHON_BIN" "$SCRIPT_DIR/check_runtime_contract.py"

echo "== Doctor (offline-tolerant) =="
"$PYTHON_BIN" "$SCRIPT_DIR/43_content_os_doctor.py" --allow-offline

echo "== Unit tests =="
"$PYTHON_BIN" -m unittest discover -s 99_System_OpenClaw/tests

if [[ -d "$OBSIDIAN_ROOT" ]]; then
  echo "== Outline and Obsidian synchronization contracts =="
  "$PYTHON_BIN" "$SCRIPT_DIR/06_check_outline_contract.py" .
else
  echo "== Outline contract =="
  echo "Skipping only the Obsidian integration check; vault not found: $OBSIDIAN_ROOT"
  "$PYTHON_BIN" "$SCRIPT_DIR/06_check_outline_contract.py" . --skip-obsidian-sync
fi

echo "== Review capability registry =="
"$PYTHON_BIN" "$SCRIPT_DIR/36_validate_review_capability_registry.py"

echo "== Repository safety boundary =="
"$PYTHON_BIN" "$SCRIPT_DIR/40_check_repository_safety.py"

echo "== Public entry points =="
for entry in validate_content_os_task.py 25_validate_jianying_draft.py 03_transcribe_audio.py 20_render_preview.py 43_content_os_doctor.py 44_launch_desktop.py openclaw_media_agent.py; do
  "$PYTHON_BIN" "$SCRIPT_DIR/$entry" --help >/dev/null
done

echo "== Synthetic trial =="
"$PYTHON_BIN" "$SCRIPT_DIR/39_create_demo_project.py" --workspace-root "$DEMO_WORKSPACE" --project-name local_ci_demo

echo "Local CI passed."
