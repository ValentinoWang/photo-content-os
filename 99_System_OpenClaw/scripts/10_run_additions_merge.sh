#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ "$(basename "$ROOT_DIR")" == "99_System_OpenClaw" ]]; then
  ROOT_DIR="$(cd "$ROOT_DIR/.." && pwd)"
fi

usage() {
  cat <<'USAGE'
用法：
  ./99_System_OpenClaw/scripts/10_run_additions_merge.sh 目标正式项目目录
  ./99_System_OpenClaw/scripts/10_run_additions_merge.sh 目标正式项目目录 --plan
  ./99_System_OpenClaw/scripts/10_run_additions_merge.sh 目标正式项目目录 --apply

兼容旧写法：
  ./99_System_OpenClaw/scripts/10_run_additions_merge.sh 目标正式项目目录/待增加 目标正式项目目录
  ./99_System_OpenClaw/scripts/10_run_additions_merge.sh 目标正式项目目录/待增加 目标正式项目目录 --plan

默认会直接合并。执行时会：
  1. 重新生成 additions_merge_plan
  2. 按计划移动全部 pending 素材
  3. 允许 needs_review 条目执行
  4. 自动重跑目标项目 AI 分析
  5. 清空待增加目录

加 --plan 时只生成计划，不移动文件。
USAGE
}

MODE="--apply"
if [[ "$#" -eq 0 ]]; then
  usage
  exit 1
fi

if [[ "${@: -1}" == "--plan" || "${@: -1}" == "--apply" ]]; then
  MODE="${@: -1}"
  set -- "${@:1:$(($# - 1))}"
fi

if [[ "$#" -eq 1 ]]; then
  TARGET_PROJECT_DIR="$1"
  ADDITIONS_DIR="$TARGET_PROJECT_DIR/待增加"
  DEFAULT_ADDITIONS=1
elif [[ "$#" -eq 2 ]]; then
  ADDITIONS_DIR="$1"
  TARGET_PROJECT_DIR="$2"
  DEFAULT_ADDITIONS=0
else
  usage
  exit 1
fi

if [[ "$MODE" != "--plan" && "$MODE" != "--apply" ]]; then
  usage
  exit 1
fi

if [[ ! -d "$TARGET_PROJECT_DIR" ]]; then
  echo "目标正式项目目录不存在：$TARGET_PROJECT_DIR"
  exit 1
fi

TARGET_PROJECT_DIR="$(cd "$TARGET_PROJECT_DIR" && pwd)"
EXPECTED_ADDITIONS_DIR="$TARGET_PROJECT_DIR/待增加"
if [[ "$DEFAULT_ADDITIONS" == "1" ]]; then
  ADDITIONS_DIR="$EXPECTED_ADDITIONS_DIR"
fi

if [[ ! -d "$ADDITIONS_DIR" && "$ADDITIONS_DIR" == "$EXPECTED_ADDITIONS_DIR" ]]; then
  mkdir -p "$EXPECTED_ADDITIONS_DIR"
fi

if [[ ! -d "$ADDITIONS_DIR" ]]; then
  echo "待增加目录不存在：$ADDITIONS_DIR"
  exit 1
fi

ADDITIONS_DIR="$(cd "$ADDITIONS_DIR" && pwd)"

if [[ "$(basename "$ADDITIONS_DIR")" != "待增加" ]]; then
  echo "为避免误删，待增加目录的最后一级目录名必须是：待增加"
  echo "当前目录：$ADDITIONS_DIR"
  exit 1
fi

if [[ "$ADDITIONS_DIR" != "$EXPECTED_ADDITIONS_DIR" ]]; then
  echo "待增加目录必须位于正式项目内：$EXPECTED_ADDITIONS_DIR"
  echo "当前目录：$ADDITIONS_DIR"
  exit 1
fi

if [[ -f "$ROOT_DIR/99_System_OpenClaw/docs/00_本地素材与剪映HyperFrames流转总纲.md" ]]; then
  python3 "$SCRIPT_DIR/06_check_outline_contract.py" "$ROOT_DIR"
fi

python3 "$SCRIPT_DIR/08_plan_additions_merge.py" "$ADDITIONS_DIR" "$TARGET_PROJECT_DIR"

PLAN_PATH="$ADDITIONS_DIR/_ai_analysis/additions_merge_plan.json"
ITEM_COUNT="$(python3 - "$PLAN_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print(len(data.get("items", [])))
PY
)"

BLOCKED_COUNT="$(python3 - "$PLAN_PATH" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
print(sum(1 for item in data.get("items", []) if item.get("status") == "blocked"))
PY
)"

if [[ "$ITEM_COUNT" == "0" ]]; then
  echo "待增加目录没有发现可合并媒体。"
  if [[ "$MODE" == "--apply" ]]; then
    rm -rf "$ADDITIONS_DIR/_ai_analysis"
  fi
  exit 0
fi

if [[ "$MODE" == "--plan" ]]; then
  echo "已生成合并计划：$ADDITIONS_DIR/_ai_analysis/additions_merge_plan.md"
  echo "默认运行本脚本会直接合并："
  echo "$0 \"$TARGET_PROJECT_DIR\""
  exit 0
fi

if [[ "$BLOCKED_COUNT" != "0" ]]; then
  echo "有 $BLOCKED_COUNT 个素材无法可靠分类，已停止自动合并。"
  echo "请查看：$ADDITIONS_DIR/_ai_analysis/additions_merge_plan.md"
  echo "如果是视频，可查看：$ADDITIONS_DIR/_ai_analysis/addition_keyframes"
  echo "修正 JSON 里的 target_relative_path 并把 status 改成 pending 后，再重新运行本脚本。"
  exit 1
fi

python3 "$SCRIPT_DIR/09_apply_additions_merge.py" "$ADDITIONS_DIR" "$TARGET_PROJECT_DIR" --apply-all-pending --allow-review-items

find "$ADDITIONS_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

echo "待增加素材已合并，待增加目录已清空：$ADDITIONS_DIR"
