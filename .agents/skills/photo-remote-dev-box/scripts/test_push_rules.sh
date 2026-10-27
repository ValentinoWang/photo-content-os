#!/usr/bin/env bash
# rbox 推送清单自测（本机跑，不连开发机）：照片、证据、密钥、AI 配置不进清单；代码、点名的证据进清单。
# 在临时 git 仓库里造现场，RBOX_LOCAL_ROOT 指过去，用 rbox list 取清单。
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); fail=0
T=$(cd "$(mktemp -d)" && pwd -P); trap 'rm -rf "$T"' EXIT
R="$T/仓库"; mkdir -p "$R" && cd "$R" && git init -q
printf '*.jpg\n*.mp4\n.env\n.tools/\n' > .gitignore
mkdir -p scripts evidence/2026-09-01/ui agents-results/x studio .codex sub/.claude-account2 docs .tools/browsers
for f in scripts/a.py studio/s.js docs/说明.md evidence/2026-09-01/ui/page.html evidence/2026-09-01/ui/other.txt agents-results/x/r.md \
         .env .env.local studio/x.local.json key.pem id.key .codex/auth.json sub/.claude-account2/.credentials.json auth.json \
         photo.jpg clip.mp4 .tools/browsers/b; do echo x > "$f"; done
git add -A >/dev/null 2>&1; git add -f evidence agents-results >/dev/null 2>&1; git commit -qm init
echo y > scripts/新文件.py   # 未跟踪、未忽略：要推
list() { RBOX_LOCAL_ROOT="$R" "$@" "$here/rbox" list "$R"; }
out=$(list env)
want() { grep -qxF "$1" <<<"$out" || { echo "应推而没推：$1"; fail=1; }; }
deny() { grep -qxF "$1" <<<"$out" && { echo "不该推却推了：$1"; fail=1; }; return 0; }
for f in scripts/a.py studio/s.js docs/说明.md scripts/新文件.py .gitignore; do want "$f"; done
for f in evidence/2026-09-01/ui/page.html agents-results/x/r.md .env .env.local studio/x.local.json key.pem id.key \
         .codex/auth.json sub/.claude-account2/.credentials.json auth.json photo.jpg clip.mp4 .tools/browsers/b; do deny "$f"; done
out=$(list env RBOX_WITH=evidence/2026-09-01/ui)
want evidence/2026-09-01/ui/page.html; want evidence/2026-09-01/ui/other.txt; deny agents-results/x/r.md
# 只认仓库和 photo-content-os 的任务 worktree，别的路径一律拒
RBOX_LOCAL_ROOT="$R" "$here/rbox" list /tmp >/dev/null 2>&1 && { echo "仓库外的路径应被拒"; fail=1; }
[ $fail = 0 ] && echo "rbox 推送清单自测全过" || exit 1
