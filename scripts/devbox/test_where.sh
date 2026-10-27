#!/usr/bin/env bash
# rbox 在线判定自测（本机跑，不连开发机）：devbox_status.py where 返回 10（local）或读不到状态时，run/bg 在推送之前就停下；
# 读不到状态的报错不能写成「不在线」。用假的 devbox_status.py 造三种返回值。
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); fail=0
T=$(cd "$(mktemp -d)" && pwd -P); trap 'rm -rf "$T"' EXIT
R="$T/仓库"; mkdir -p "$R" && git -C "$R" init -q && echo x > "$R/a.py" && git -C "$R" add a.py && git -C "$R" commit -qm init
fake() { printf 'import sys\nprint(%s)\nsys.exit(%s)\n' "'$1'" "$2" > "$T/status.py"; }
try() { RBOX_LOCAL_ROOT="$R" RBOX_DEVBOX_STATUS="$T/status.py" RBOX_HOST=rbox-selftest-unreachable.invalid "$here/rbox" run "$R" -- true 2>&1; }
fake local 10; out=$(try); rc=$?
{ [ $rc != 0 ] && grep -q '不在线' <<<"$out" && ! grep -q '推送' <<<"$out"; } || { echo "local（10）应在推送前停下并说不在线：$out"; fail=1; }
fake 'boom' 2; out=$(try); rc=$?
{ [ $rc != 0 ] && grep -q '读不到开发机在线状态' <<<"$out" && grep -q '不当成不在线' <<<"$out"; } || { echo "读不到状态（2）应停下并说读不到：$out"; fail=1; }
fake devbox 0; out=$(try); rc=$?
grep -qE '读不到开发机在线状态|不在线（' <<<"$out" && { echo "devbox（0）不该被在线判定拦下：$out"; fail=1; }
[ $fail = 0 ] && echo "rbox 在线判定自测全过" || exit 1
