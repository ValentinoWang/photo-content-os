#!/usr/bin/env bash
# 照寸木 cunmu-remote-dev-box/scripts/lint_scripts.sh（源自 Cadenvo）。本技能脚本的静态门禁：bash -n、shellcheck -S warning，
# 加上 shellcheck 查不出的「$变量紧跟中文」（Core E-86）。本技能 10-27 犯过一次：rbox setup 最后一行的 `$DEPLOY_LOG` 后面直接跟了中文逗号，set -u 下整条命令退出码 1。
# perl 按字节读、不加 -CSD：[^\x00-\x7F] 照样认得中文，加了中文路径的文件名会二次编码成乱码（寸木 10-26）
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); fail=0
files=("$here"/rbox "$here"/with-macos-cp "$here"/cp-shim "$here"/*.sh)
for f in "${files[@]}"; do bash -n "$f" || fail=1; done
if command -v shellcheck >/dev/null; then shellcheck -S warning "${files[@]}" || fail=1; else echo "本机没有 shellcheck，这一项没查（brew 装之前先问用户，见规则卡）"; fi
# macOS grep 没有 -P：用 perl；perl 本身出错也算门禁失败，不当成「没查到」
hits=$(perl -ne 'print "$ARGV:$.: $_" if /\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F]/; close ARGV if eof' "${files[@]}") || { echo "检查变量写法的 perl 出错"; fail=1; }
[ -n "$hits" ] && { echo "$hits"; echo "↑ 变量后面紧跟中文，要写成 \${变量}"; fail=1; }
[ $fail = 0 ] && echo "脚本静态门禁通过" || exit 1
