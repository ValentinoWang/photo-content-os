# Machine evidence

- Run ID: r310-e40196d-photo-dev
- Status: PASS
- Source identity: e40196d47b1edb7adcebc0422f420f2bacc1f3c9
- Layer: machine/unit

## Execution

Recorded at: 2026-11-24T04:24:31.708597+00:00

## Command 1

```
.agents/skills/photo-remote-dev-box/scripts/rbox run /Users/vsiyo/.local/share/task-worktrees/photo-content-os-binding-e40196d -- bash -c 'set -euo pipefail
actual=$(git rev-parse HEAD)
printf "remote source %s\n" "$actual"
test "$actual" = e40196d47b1edb7adcebc0422f420f2bacc1f3c9

export GIT_AUTHOR_NAME=R310Fixture GIT_AUTHOR_EMAIL=r310-fixture@example.invalid
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME" GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
if ! command -v shellcheck >/dev/null; then
  binroot=$(mktemp -d "$TMPDIR/shellcheck.XXXXXX")
  (cd "$binroot" && apt-get download shellcheck && dpkg-deb -x ./shellcheck_*.deb unpacked)
  export PATH="$binroot/unpacked/usr/bin:$PATH"
fi
shellcheck --version
bash .agents/skills/photo-remote-dev-box/scripts/lint_scripts.sh
bash .agents/skills/photo-remote-dev-box/scripts/test_push_rules.sh
bash .agents/skills/photo-remote-dev-box/scripts/test_ai_guard.sh
bash .agents/skills/photo-remote-dev-box/scripts/test_where.sh'
```

Exit code: 0

```
[rbox] 推送 2186 个文件，4 秒
remote source e40196d47b1edb7adcebc0422f420f2bacc1f3c9
Get:1 https://mirrors.ustc.edu.cn/ubuntu noble/universe amd64 shellcheck amd64 0.9.0-1 [2845 kB]
Fetched 2845 kB in 3s (1134 kB/s)
W: Download is performed unsandboxed as root as file '/root/.prbox/tmp/run-232415-41865/shellcheck.eYV6Jy/shellcheck_0.9.0-1_amd64.deb' couldn't be accessed by user '_apt'. - pkgAcquire::Run (13: Permission denied)
ShellCheck - shell script analysis tool
version: 0.9.0
license: GNU General Public License, version 3
website: https://www.shellcheck.net
脚本静态门禁通过
rbox 推送清单自测全过
开发机不跑 AI：门禁自测全过
rbox 在线判定自测全过
[rbox] 退出码 0，完整日志 /root/.prbox/run-232415-41865.log
```

## Command 2

```
.agents/skills/photo-remote-dev-box/scripts/rbox run /Users/vsiyo/.local/share/task-worktrees/photo-content-os-binding-e40196d -- bash -c 'set -euo pipefail
actual=$(git rev-parse HEAD)
printf "remote source %s\n" "$actual"
test "$actual" = e40196d47b1edb7adcebc0422f420f2bacc1f3c9
sha256sum .agents/skills/photo-remote-dev-box/scripts/lint_scripts.sh .agents/skills/photo-remote-dev-box/scripts/test_push_rules.sh .agents/skills/photo-remote-dev-box/scripts/test_ai_guard.sh .agents/skills/photo-remote-dev-box/scripts/test_where.sh tests/test_r280_light.py
.venv/bin/python -m pytest -q tests/test_r280_light.py'
```

Exit code: 0

```
[rbox] 推送 2186 个文件，3 秒
remote source e40196d47b1edb7adcebc0422f420f2bacc1f3c9
c67077fbb817becd343822be1e39e3efcca84b48d6e2c9bbbf2107dd6a5053d2  .agents/skills/photo-remote-dev-box/scripts/lint_scripts.sh
f2eb65355390d3811725c5b1093ebce36679cbb9cf3641e66c23bf53141bdc57  .agents/skills/photo-remote-dev-box/scripts/test_push_rules.sh
7d8000cd154bc48aab6e3e3a047151f1ffed8e693110e9a021e57148dd010161  .agents/skills/photo-remote-dev-box/scripts/test_ai_guard.sh
086d8446690b0940a3ff009b2dc68acf2c107168a435d629031f61a4de311f4d  .agents/skills/photo-remote-dev-box/scripts/test_where.sh
e98f6199f0f0a897e3a94fa53fa57d5b70b369225e2803e67259e1e1ffa585ef  tests/test_r280_light.py
.........                                                                [100%]
9 passed in 0.07s
[rbox] 退出码 0，完整日志 /root/.prbox/run-232425-43302.log
```

## Command 3

```
.agents/skills/photo-remote-dev-box/scripts/rbox run /Users/vsiyo/.local/share/task-worktrees/photo-content-os-binding-e40196d -- bash -c 'set -euo pipefail
actual=$(git rev-parse HEAD)
printf "remote source %s\n" "$actual"
test "$actual" = e40196d47b1edb7adcebc0422f420f2bacc1f3c9

skill=.agents/skills/photo-remote-dev-box
git diff --exit-code HEAD -- "$skill" AGENTS.md .gitignore
git ls-files --error-unmatch "$skill/SKILL.md" "$skill/references/2026-10-27-setup-review.md" >/dev/null
if git check-ignore --no-index -q "$skill/SKILL.md"; then echo "project skill is ignored"; exit 1; fi
link_blob=$(git ls-tree -r HEAD | awk '"'"'$1 == "120000" && $NF ~ /\/photo-remote-dev-box$/ {print $3}'"'"')
test "$(git cat-file blob "$link_blob")" = ../../.agents/skills/photo-remote-dev-box
printf '"'"'%s\n'"'"' "Git skill symlink verified: $link_blob"
for path in test_push_rules.sh test_ai_guard.sh test_where.sh; do
  git show "0422f6bf4ea9b92f319ef5a78dbaf9dc6be1da43:scripts/devbox/$path" | cmp - "$skill/scripts/$path"
done
grep -nF '"'"'FFMPEG_TAR=ffmpeg-n9.0'"'"' "$skill/scripts/rbox"
grep -nF '"'"'ffmpeg_upload >'"'"' "$skill/scripts/rbox"
grep -nF '"'"'"$HERE/setup_remote.sh"'"'"' "$skill/scripts/rbox"
grep -nF '"'"'wait $fpid || true'"'"' "$skill/scripts/rbox"
grep -nF '"'"'version n9'"'"' "$skill/scripts/setup_remote.sh"
grep -nF '"'"'what="${1:-r278}"'"'"' "$skill/scripts/rbox"
grep -nF '"'"'job="studio-r276/'"'"' "$skill/scripts/rbox"
grep -nF '"'"'img="docs/design-drafts/page-script-to-video--style-and-rescript--Pho_R278/img"'"'"' "$skill/scripts/rbox"
grep -nF '"'"'for s in studio-r278 evidence/R277-shot-visual-revision'"'"' "$skill/scripts/rbox"
sha256sum "$skill/SKILL.md" "$skill/references/2026-10-27-setup-review.md" "$skill"/scripts/* AGENTS.md .gitignore
'
```

Exit code: 0

```
[rbox] 推送 2186 个文件，3 秒
remote source e40196d47b1edb7adcebc0422f420f2bacc1f3c9
Git skill symlink verified: 7a3d2034e25f65e7c11c1ab51709b91de64fbcdc
140:FFMPEG_TAR=ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz
196:    ffmpeg_upload > "$freeze.ffmpeg.log" 2>&1 & fpid=$!
200:    rs "bash -s -- $(q "$LOCAL_ROOT") $pyv $LOGDIR" < "$HERE/setup_remote.sh" || { wait $fpid; cat "$freeze.ffmpeg.log"; rm -f "$freeze" "$freeze.ffmpeg.log"; die "开发机安装失败，见上面的输出"; }
201:    wait $fpid || true; cat "$freeze.ffmpeg.log"; rm -f "$freeze" "$freeze.ffmpeg.log"
78:if ! "$L/bin/ffmpeg" -version 2>/dev/null | head -1 | grep -q 'version n9\.0'; then
212:    shift; what="${1:-r278}"; t0=$SECONDS; bw="${RBOX_BWLIMIT:-3072}"; D="$HOME/.photo-content-os"
215:      job="studio-r276/direct-jobs-parked/project-fc6baa3294/dv_0e184e961bd14ac084c67411/job.json"
219:      img="docs/design-drafts/page-script-to-video--style-and-rescript--Pho_R278/img"   # 本机排除在 git 之外的媒体，推到开发机主目录同一路径
223:      for s in studio-r278 evidence/R277-shot-visual-revision; do
a730e0d0d1f39800f4603f9dcea4cd2b88df6fccf4cc58dc88232d2324cea6e6  .agents/skills/photo-remote-dev-box/SKILL.md
03a627a3a364a6653057c32649d860c944a7051127b99184da707b0babb11f47  .agents/skills/photo-remote-dev-box/references/2026-10-27-setup-review.md
647f43a81fbd2d2a8e3a9c996e3538c78cffe8347b284faee4be1e1a5cb400df  .agents/skills/photo-remote-dev-box/scripts/ai_check_remote.sh
60a10e155803cbaf7ac74376a61efe3c9c01b858a5e59a021f5662e8db22095f  .agents/skills/photo-remote-dev-box/scripts/ai_guard.py
38d8f24b20bf7d4a2088efd8ba2b5312ab5139254c3a997b92b5307d06b2fb7b  .agents/skills/photo-remote-dev-box/scripts/cp-shim
78b1cab690d209fa0e6cbe4bd762fcb1b7d1352d6304b1307478d16ddb105539  .agents/skills/photo-remote-dev-box/scripts/exposure_check_remote.sh
c67077fbb817becd343822be1e39e3efcca84b48d6e2c9bbbf2107dd6a5053d2  .agents/skills/photo-remote-dev-box/scripts/lint_scripts.sh
b894b3a72ea32c7cd983c44ac5b57c057c46942b9081878461715d30a51933ad  .agents/skills/photo-remote-dev-box/scripts/queue_run.sh
7992d116dde49b6674586ac2b350433eee2386d5ce0d4afa9cfb12ce584adc30  .agents/skills/photo-remote-dev-box/scripts/rbox
f8e2711efb66e38d6177d25b6b923c33a7321d69628e844e9fab8f7fef55aa4a  .agents/skills/photo-remote-dev-box/scripts/setup_remote.sh
7d8000cd154bc48aab6e3e3a047151f1ffed8e693110e9a021e57148dd010161  .agents/skills/photo-remote-dev-box/scripts/test_ai_guard.sh
f2eb65355390d3811725c5b1093ebce36679cbb9cf3641e66c23bf53141bdc57  .agents/skills/photo-remote-dev-box/scripts/test_push_rules.sh
086d8446690b0940a3ff009b2dc68acf2c107168a435d629031f61a4de311f4d  .agents/skills/photo-remote-dev-box/scripts/test_where.sh
f645c2068584eddcaed30e165a44442c901e0be50e38c3e7cdcc6e2058ed58eb  .agents/skills/photo-remote-dev-box/scripts/with-macos-cp
f03ff469daea81f9111f6c1d0865f9a5ef77cadd73f2b2977b1811c91f535b78  AGENTS.md
645277a76bb148674777f711f0287b32ec7e00baa990f9a794927a7b71ea1f0a  .gitignore
[rbox] 退出码 0，完整日志 /root/.prbox/run-232430-44065.log
```
