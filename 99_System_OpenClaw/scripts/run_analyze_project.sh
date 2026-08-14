#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ "$(basename "$ROOT_DIR")" == "99_System_OpenClaw" ]]; then
  ROOT_DIR="$(cd "$ROOT_DIR/.." && pwd)"
fi
PROJECT_DIR="${1:-}"
WITH_AUDIO="${2:-}"

if [[ -z "$PROJECT_DIR" ]]; then
  echo "用法：$0 项目文件夹路径 [--audio]"
  exit 1
fi

if [[ -f "$ROOT_DIR/99_System_OpenClaw/docs/00_本地素材与剪映HyperFrames流转总纲.md" ]]; then
  python3 "$SCRIPT_DIR/06_check_outline_contract.py" "$ROOT_DIR"
fi

PROJECT_DIR_ABS="$(cd "$PROJECT_DIR" && pwd)"
INBOX_ROOT_ABS="$(cd "$ROOT_DIR/00_Inbox_Mac_Intake" 2>/dev/null && pwd || true)"
if [[ -n "$INBOX_ROOT_ABS" && "$PROJECT_DIR_ABS" == "$INBOX_ROOT_ABS/"* ]]; then
  echo "检测到 Inbox 批次：跳过正式项目结构创建。"
  echo "需要正式项目壳时运行：python3 $SCRIPT_DIR/34_ensure_project_from_inbox_batch.py \"$PROJECT_DIR_ABS\""
else
  python3 "$SCRIPT_DIR/13_ensure_project_structure.py" "$PROJECT_DIR"
fi
python3 "$SCRIPT_DIR/01_scan_media_manifest.py" "$PROJECT_DIR"
python3 "$SCRIPT_DIR/07_validate_media_decisions.py" "$PROJECT_DIR"
python3 "$SCRIPT_DIR/02_extract_keyframes.py" "$PROJECT_DIR"

if [[ "$WITH_AUDIO" == "--audio" ]]; then
  "$SCRIPT_DIR/03_extract_audio.sh" "$PROJECT_DIR"
fi

python3 "$SCRIPT_DIR/04_generate_ai_prompt.py" "$PROJECT_DIR"
python3 "$SCRIPT_DIR/05_write_content_summary.py" "$PROJECT_DIR"

echo "AI 分析准备完成。"
echo "清单：$PROJECT_DIR/_ai_analysis/media_manifest.json"
echo "判别校验：$PROJECT_DIR/_ai_analysis/media_decision_warnings.md"
echo "关键帧：$PROJECT_DIR/_ai_analysis/keyframes"
echo "Prompt：$PROJECT_DIR/_ai_analysis/prompts"
echo "LLM Summary：$PROJECT_DIR/_ai_analysis/summaries"
echo "项目总览模板：$PROJECT_DIR/_ai_analysis/project_overview.md"
