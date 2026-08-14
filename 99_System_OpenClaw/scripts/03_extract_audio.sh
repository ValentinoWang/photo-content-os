#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${1:-}"
INCLUDE_DERIVED="${2:-}"

if [[ -z "$PROJECT_DIR" ]]; then
  echo "用法：$0 项目文件夹路径 [--include-derived]"
  exit 1
fi

python3 "$SCRIPT_DIR/03_extract_audio_helper.py" "$PROJECT_DIR" "$INCLUDE_DERIVED"

