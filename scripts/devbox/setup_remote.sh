#!/usr/bin/env bash
# rbox setup 的开发机那半（经 ssh 标准输入喂过来）：$1 = 主目录路径（和本机同一绝对路径），$2 = 本机 .venv 的 Python 版本，$3 = rbox 日志目录。
# 装的都在主目录副本里（.venv、.tools），worktree 由 rbox sync 软链过来；系统 /usr/bin/python3（3.10，apt 依赖它）不动。
# 镜像：PyPI 走华为云（同平台 10-27 实测 3.3 MB/s；阿里云 HTTP/1.1 只有约 110 KB/s，Core 网络一节）；npm、Node、Playwright 浏览器走 npmmirror；
# PyTorch 用 CPU 版（PyPI 上 Linux 的 torch 默认带 CUDA，多拉约 2.5 GB 的 nvidia 包，开发机没有显卡）。
set -euo pipefail
ROOT=$1; PYV=$2; L=$3
T0=$(date +%s); LAST=$T0; LAST_NAME=""; TIMES=""
step() { local now; now=$(date +%s); [ -n "$LAST_NAME" ] && TIMES+="$LAST_NAME	$((now - LAST))
"; LAST=$now; LAST_NAME="$*"; echo "== $(date +%H:%M:%S) $*"; }
PIP=https://repo.huaweicloud.com/repository/pypi/simple
TORCH=https://mirrors.aliyun.com/pytorch-wheels/cpu/
UV=/root/.local/bin/uv
export UV_HTTP_TIMEOUT=120
cd "$ROOT"

step "系统包（tmux、中文字体、Chromium 要的库、melt、mediainfo）"
export DEBIAN_FRONTEND=noninteractive
timeout -k 10 600 apt-get -o Acquire::http::Timeout=20 update -q >/dev/null
timeout -k 10 1500 apt-get install -y -q --no-install-recommends tmux rsync curl ca-certificates jq fonts-noto-cjk fonts-noto-color-emoji fonts-liberation \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 libatspi2.0-0 libxshmfence1 libsndfile1 libgl1 libglib2.0-0 \
  mediainfo libmediainfo0v5 melt >/dev/null
if [ ! -x /root/.local/bin/uv ]; then
  mkdir -p /root/.local/bin && timeout -k 10 300 wget -q -O /tmp/uv.tgz https://github.com/astral-sh/uv/releases/download/0.9.5/uv-x86_64-unknown-linux-gnu.tar.gz \
    && tar xzf /tmp/uv.tgz -C /tmp && cp /tmp/uv-x86_64-unknown-linux-gnu/uv /tmp/uv-x86_64-unknown-linux-gnu/uvx /root/.local/bin/
fi
tmux -V; melt --version 2>&1 | head -1; $UV --version

step "Python $PYV（uv）"
$UV python install "$PYV" 2>&1 | tail -1 || echo "uv 没有 ${PYV}，用已装的 3.13"
if ! .venv/bin/python -c 'import sys; sys.exit(0)' 2>/dev/null; then
  $UV venv -q --python "$PYV" .venv 2>/dev/null || $UV venv -q --python 3.13 .venv
fi
.venv/bin/python --version

step "Python 包（和本机 .venv 同版本；torch 系用 CPU 版）"
grep -vE '^(torch|torchvision|torchaudio)==' "$L/freeze.txt" > "$L/freeze-notorch.txt"
tv=$(grep -E '^(torch|torchvision|torchaudio)==' "$L/freeze.txt" | sed 's/$/+cpu/' | tr '\n' ' ')
# torch 系先装：它们钉的 CPU 版要从阿里云的 pytorch-wheels 取
if [ -n "$tv" ]; then $UV pip install -q --python .venv/bin/python --index-url $PIP --find-links $TORCH $tv; fi
$UV pip install -q --python .venv/bin/python --index-url $PIP --find-links $TORCH -r "$L/freeze-notorch.txt"
echo "开发机 .venv 第三方包 $($UV pip freeze --python .venv/bin/python | wc -l) 个，本机 $(wc -l < "$L/freeze.txt") 个"

step "Node（.tools/node，版本和哈希按 third_party/edit-tools.lock.json）"
read -r nv nfile nsha < <(.venv/bin/python -c 'import json; n=json.load(open("third_party/edit-tools.lock.json"))["node"]; a=n["artifacts"]["linux-x64"]; print(n["version"], a["file"], a["sha256"])')
mkdir -p .tools
if [ "$(.tools/node/bin/node --version 2>/dev/null)" != "v$nv" ]; then
  wget -q -O "/tmp/$nfile" "https://cdn.npmmirror.com/binaries/node/v$nv/$nfile"
  echo "$nsha  /tmp/$nfile" | sha256sum -c -
  rm -rf .tools/node && tar xzf "/tmp/$nfile" -C .tools && mv ".tools/${nfile%.tar.gz}" .tools/node && rm -f "/tmp/$nfile"
fi
.tools/node/bin/node --version

step "剪辑工具和 Playwright 浏览器（scripts/setup_edit_tools.py）"
export PATH="$ROOT/.tools/node/bin:$PATH" npm_config_registry=https://registry.npmmirror.com
export PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
# OpenChatCut 依赖的 onnxruntime-node 在 Linux x64 上会另下 CUDA 版的附加文件（NuGet 下载被重定向，它的脚本不跟，npm ci 整个失败，10-27 实测）；
# 开发机没有显卡，CPU 版本来就在 npm 包里，跳过这一步
export ONNXRUNTIME_NODE_INSTALL=skip
.venv/bin/python scripts/setup_edit_tools.py
ls .tools/browsers

step "ffmpeg（BtbN 静态版）"
# 开发机直连 GitHub 的发布文件只有 100–200 KB/s，157 MB 的包要 15 分钟以上；本机下载约 2 MB/s（10-27 实测 64 秒），
# 再用单独的连接限速传上来约 1 分钟。所以先用本机传上来的 $L/ffmpeg-upload.tar.xz（见 README「换机器」），没有才直接下，限时 20 分钟
mkdir -p "$L/bin"
if ! "$L/bin/ffmpeg" -version >/dev/null 2>&1; then
  src="$L/ffmpeg-upload.tar.xz"
  if [ ! -s "$src" ]; then
    src=/tmp/ffmpeg.tar.xz
    timeout -k 10 1200 wget -q -O "$src" https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
  fi
  rm -rf /tmp/ffmpeg-x && mkdir /tmp/ffmpeg-x && tar xJf "$src" -C /tmp/ffmpeg-x --strip-components=1
  cp /tmp/ffmpeg-x/bin/ffmpeg /tmp/ffmpeg-x/bin/ffprobe "$L/bin/" && rm -rf /tmp/ffmpeg-x /tmp/ffmpeg.tar.xz
fi
"$L/bin/ffmpeg" -version | head -1

step "macOS 替身：字体路径、cp -cR"
# 测试和门禁里写死了 macOS 的字体路径（tests/test_r277_boxes.py、test_pf_video_pipeline.py 等），在同一路径放链接指向开发机上的字体：
# STHeiti Medium → Noto Sans CJK Bold，Arial → Liberation Sans（和 Arial 等宽的替代字体）。渲染出来的字形和本机不一样，只保证能跑
mkdir -p /System/Library/Fonts/Supplemental
ln -sfn /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc "/System/Library/Fonts/STHeiti Medium.ttc"
ln -sfn /usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf /System/Library/Fonts/Supplemental/Arial.ttf
# cp -cR 替身：只在 with-macos-cp 包住的命令里生效（见 scripts/devbox/with-macos-cp）
mkdir -p "$L/shims" "$L/bin"
[ -x "$L/shims/cp.real" ] || cp /usr/bin/cp "$L/shims/cp.real"
install -m 755 scripts/devbox/cp-shim "$L/shims/cp"; install -m 755 scripts/devbox/with-macos-cp "$L/bin/with-macos-cp"
ls -la "/System/Library/Fonts/STHeiti Medium.ttc" /System/Library/Fonts/Supplemental/Arial.ttf "$L/bin/with-macos-cp"

step 完成
echo "== 前置部署时间（setup）：总计 $(( $(date +%s) - T0 )) 秒"; printf '%s' "$TIMES" | awk -F'\t' '{printf "   %4d 秒  %s\n", $2, $1}'
nproc; free -h | sed -n 2p; df -h / | tail -1
