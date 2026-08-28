#!/usr/bin/env bash
set -euo pipefail

if command -v brew >/dev/null 2>&1; then
  brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
  brew list exiftool >/dev/null 2>&1 || brew install exiftool
else
  echo "请安装 ffmpeg 和 exiftool，并确保它们在 PATH 中。" >&2
  exit 1
fi
echo "系统依赖检查完成。Python 环境请运行 41_setup_dev_environment.sh。"
