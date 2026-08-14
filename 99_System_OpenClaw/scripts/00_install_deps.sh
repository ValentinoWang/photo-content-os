#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "未找到 Homebrew。请先安装 Homebrew，或手动安装 ffmpeg / ffprobe。"
  exit 1
fi

brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
brew list exiftool >/dev/null 2>&1 || brew install exiftool

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pillow tqdm

echo "依赖安装完成。后续可运行：source .venv/bin/activate"

