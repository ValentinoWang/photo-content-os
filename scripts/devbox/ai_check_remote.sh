#!/usr/bin/env bash
# 在开发机上执行：开发机不许有 Claude、Codex（用户 2026-10-26，与寸木 agent-6a 商定）。查到就打印并退出 1；只报不删。
# 只查 CLI、配置目录、凭据、密钥变量；产品依赖里的 openai/anthropic SDK（venv、node_modules/openai）不算。
# AI_ROOT 只给自测用（指向假目录，跳过进程和 PATH 检查），平时查整台机器。
if [ "${1:-}" = --selftest ]; then   # 假目录自测：red 必须报红（凭据、home 级 .claude、CLI、npm 包），green 必须绿（SDK、项目自带 .claude）
  T=$(mktemp -d /root/.prbox/ai-selftest.XXXX); me=$(readlink -f "$0")
  mkdir -p "$T"/red/.codex "$T"/red/.claude-account2 "$T"/red/bin "$T"/red/x/node_modules/@openai/codex \
           "$T"/green/venv/lib/python3.10/site-packages/openai "$T"/green/proj/.claude "$T"/green/x/node_modules/openai
  echo '{}' > "$T"/red/.codex/auth.json; touch "$T"/red/bin/codex; chmod +x "$T"/red/bin/codex
  touch "$T"/green/venv/lib/python3.10/site-packages/openai/__init__.py "$T"/green/proj/.claude/settings.json
  red=$(AI_ROOT="$T"/red bash "$me"); rr=$?; green=$(AI_ROOT="$T"/green bash "$me"); gr=$?; rm -rf "$T"; ok=1
  { [ $rr = 1 ] && grep -q '登录凭据' <<<"$red" && grep -q 'claude-account2' <<<"$red" && grep -q '@openai/codex' <<<"$red" && grep -q 'bin/codex' <<<"$red"; } || { echo "red 应报红：$red"; ok=0; }
  [ $gr = 0 ] || { echo "green 应为绿：$green"; ok=0; }
  [ $ok = 1 ] && echo "ai-check 假目录自测通过" && exit 0; exit 1
fi
R="${AI_ROOT:-/root}"; found=0; cred=0
hit() { echo "AI 痕迹：$*"; found=1; }
if [ -z "${AI_ROOT:-}" ]; then
  while IFS= read -r l; do hit "进程 $l"; done < <(ps -eo pid=,args= | grep -E '(^|[ /])(claude|codex)( |$)|@anthropic-ai/claude-code|@openai/codex' | grep -vE 'grep|ai_check_remote')
  for b in claude codex; do p=$(command -v "$b" 2>/dev/null) && hit "PATH 里有 ${b}：$p"; done
  for n in /root/.prbox/node/bin/npm; do [ -x "$n" ] && "$n" ls -g --depth=0 2>/dev/null | grep -E '@openai/codex|@anthropic-ai/claude-code' | while read -r l; do echo "AI 痕迹：npm 全局包 ${l}（${n}）"; done; done | grep . && found=1
  ROOTS=(/root /home /opt /usr/local /tmp)
else ROOTS=("$R"); fi
while IFS= read -r f; do hit "CLI $f"; done < <(find "${ROOTS[@]}" -xdev -maxdepth 8 \( -path '*/node_modules/@openai/codex' -o -path '*/node_modules/@anthropic-ai/claude-code' -o \( \( -type f -o -type l \) \( -name claude -o -name codex \) -path '*/bin/*' \) \) -prune -print 2>/dev/null | head -10)
# 家目录这一层的 .claude*/.codex* 一律报；更深的（项目、Flutter 仓库自带的 .claude）只在里面有登录凭据时报
HOMES=("$R"); [ -z "${AI_ROOT:-}" ] && HOMES=(/root /home/*)
while IFS= read -r d; do
  c=$(find "$d" -maxdepth 3 \( -name auth.json -o -name .credentials.json \) 2>/dev/null | head -1)
  hit "配置目录 $d${c:+（含登录凭据 ${c}）}"; [ -n "$c" ] && cred=1
done < <(find "${HOMES[@]}" -mindepth 1 -maxdepth 1 -type d \( -name '.claude' -o -name '.claude-account*' -o -name '.codex' -o -name '.codex-account*' \) 2>/dev/null)
while IFS= read -r c; do hit "登录凭据 $c"; cred=1; done < <(find "${ROOTS[@]}" -xdev -mindepth 3 -maxdepth 6 \( -path '*/.claude*/.credentials.json' -o -path '*/.codex*/auth.json' \) 2>/dev/null | grep -vE "^($(IFS='|'; echo "${HOMES[*]}"))/\.(claude|codex)[^/]*/[^/]+$")
for f in /etc/environment "$R"/.bashrc "$R"/.profile /etc/profile.d/*; do [ -f "$f" ] && grep -qE '(ANTHROPIC|OPENAI)_API_KEY' "$f" 2>/dev/null && { hit "密钥变量写在 $f"; cred=1; }; done
[ "$cred" = 1 ] && echo "凭据已落到开发机上：按已泄漏处理，请用户在本机把那个账号重新登录或吊销会话；删不删由用户定，删了也不等于安全。"
[ "$found" = 0 ] && echo "开发机无 AI 痕迹" || exit 1
