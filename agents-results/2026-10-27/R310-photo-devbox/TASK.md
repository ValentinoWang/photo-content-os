# R310 交付准备：photo-content-os 用自己的开发机跑测试、门禁和渲染

任务卡：「photo-content-os 用自己的开发机跑测试、门禁和渲染 · 需求卡（2026-10-27-R310-photo-devbox）」。

## 背景

用户 2026-10-27 租了一台专给 photo-content-os 的开发机（本机 `~/.ssh/config` 别名 `photo-dev`），要求 3 小时内弄好。总控（Claude）已经写完并在开发机上实测了工具，代码在本 worktree 的三笔提交里（`cd10bae`、`c4faa52`、`40cf307`，基于 `origin/main` 的 `c1465ff`）：

- `scripts/devbox/`：`rbox`（推送 + 远端执行 + 排队）、`setup_remote.sh`、`queue_run.sh`、`ai_guard.py`、`ai_check_remote.sh`、`exposure_check_remote.sh`、`with-macos-cp`、`cp-shim`、三份自测 `test_push_rules.sh`、`test_ai_guard.sh`、`test_where.sh`、说明 `README.md`；
- `AGENTS.md` 加了一段「检查和门禁走开发机」；
- 需求卡 `acceptance/requests/2026-W44/2026-10-27-R310-photo-devbox/`（已按实际做法更新过理解、不做的、H-02 预期）。

总控在开发机上已经跑过（证据在开发机 `/root/.prbox/*.log`，可以用 `scripts/devbox/rbox log <名字>` 看）：

| 跑了什么 | 结果 |
|---|---|
| 全量 pytest（`full-pytest-2`） | 1204 过、12 红、36 跳过。9 红本机同样会红（8 项 ffmpeg 9 已删 `-filter_complex_script`，1 项 `test_full_checklist_acceptance` 还查 R280 之前的深色令牌）；3 红是开发机环境（没有 Obsidian 库；melt 7.4 对本机 7.39 的两项像素） |
| R276 `frontend_gate.mjs --checks-only`（`r276-gate-1`） | PASS，26 次设计比对 |
| R278 `rescript_frontend_gate.mjs --checks-only`（`r278-gate-1`） | PASS，R278/R282/R283 54 次合同比较 |
| R277 `revision_frontend_gate.mjs --checks-only`（`r277-gate-2`） | 夹具、真实首屏、标注回放过；固定标注框位置因字体度量不同失败，所以 R277 门禁留在本机（README 有说明） |
| `tests/test_r280_light.py` | 9 过 |

`harnessctl acceptance check-delivery --project . --range origin/main..HEAD --read-only` 目前：G1 FAIL（三笔提交没有验收卡）、G12 FAIL（R310 没有同编号验收卡）、G16 FAIL（本 worktree 稀疏检出，读不到 R223、R276、R277、R278、R280、R282、R283 七张旧卡在 `agents-results/` 下的 acceptance-contract.md）。G6 WARN（`scripts/devbox/*` 没映射进 `acceptance/surfaces.yaml`）。

## 要你做的

给 R310 递交一张验收卡，让 check-delivery 的 **G16 通过**、G12 通过；G1 允许只剩「人工未签」那一种失败。照 Core 规则做，不要绕过任何门禁：

1. 先读：
   - `Harness Engineering 仓库/Core/harnesses/delivery-handoff-harness.md`
   - `Harness Engineering 仓库/Core/harnesses/ai-coding-rules.md`（写代码规则卡，单独读完）
   - `Harness Engineering 仓库/Core/skills/design-acceptance-contract/`、`Core/skills/acceptance-handoff/` 的 SKILL.md 和 references
   - 本项目 `AGENTS.md`、`scripts/devbox/README.md`、`acceptance/surfaces.yaml`
   - 参照样例：`origin/main` 上的 R280 递交物 `agents-results/2026-10-27/R280-studio-light/` 和 `acceptance/human/2026-W44/未-2026-10-26-R280-photo-studio-light/`（用 `git show origin/main:<路径>` 读，不用检出）。
2. G16：用 `git sparse-checkout add` 只补检出那七张旧卡的合同所在子目录（报错里列的 `agents-results/<日期>/<目录>`），不要整份检出 agents-results。
3. 建任务根 `agents-results/2026-10-27/R310-photo-devbox/`：验收合同、baseline、claims、机器结果等，格式照 R280。
   - 卡片 `--request-id 2026-10-27-R310-photo-devbox`，人工项就是需求卡上的 H-01、H-02，原样沿用，不增删改。
   - 这是开发工具，不是用户界面：用 `--non-blocking`，`--estimated-minutes 5`，`--required-role` 写任务委托人。
   - 机器证据必须是 verified head（`40cf307`，范围里最后一个改了验收物以外文件的提交）上的 PASS。需要重跑时：三份自测（纯 shell/python，秒级）可以在本机跑；`tests/test_r280_light.py` 和任何 pytest、门禁、浏览器一律经 `scripts/devbox/rbox run <本 worktree> -- …` 在开发机上跑，不许在本机跑。
   - G6：在 `acceptance/surfaces.yaml` 给 `scripts/devbox/**` 加映射（是开发工具，不是用户界面）。注意：这会改验收物以外的文件吗？`acceptance/**` 是验收物，不推进 verified head。
4. 跑 `check-delivery --range origin/main..HEAD`，直到 G16、G12 通过；把每个门禁的结果原样写进汇报。
5. 只提交验收物（`acceptance/**`、`agents-results/**`），`git add -f` 只加合同需要的文件，不整目录加。**不推送**，推送由总控做。

## 不要动

- 不改 `scripts/devbox/` 和别的产品代码、测试、AGENTS.md。发现这些文件有问题，写进汇报后停下。
- 不改需求卡的 H 项。
- 不碰开发机上的数据（`/root/.photo-content-os`、`/root/media-root`），不重装开发机环境，不起常驻服务。
- 不在本机跑 pytest、门禁、浏览器；不推送；不回退别人的改动；不杀别人的进程。
- 别的会话在主检出里的改动、`/private/tmp/task-worktrees/` 下别的 worktree 一律不碰。

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
|---|---|---|---|
| 开工改代码（这里是提交验收物） | 所有 git 写操作前断言当前目录是本 worktree | 在主检出里提交 | `[ "$(git rev-parse --show-toplevel)" = /private/tmp/task-worktrees/photo-content-os-devbox-rbox ]` |
| 提交和递交验收 | G16 必须过；改了被旧卡保护的测试要同一次交付更新那些卡（本任务不改测试，应无此情况） | 读不到旧卡合同就当成「不相关」 | `python3 Harness Engineering 仓库/tools/harnessctl.py acceptance check-delivery --project . --range origin/main..HEAD` |
| 提交证据 | `git add -f` 只加合同需要的文件；不放本机绝对路径（写 `~/…`、「任务 worktree」） | 整目录 add 把日志、截图带进去；汇报里写 `/Users/vsiyo/...` | `python3 scripts/check_repository_safety.py --base origin/main`（经 rbox 在开发机跑或本机跑都行，它不开浏览器） |
| 说「通过」之前 | 只说真正跑通的那段；开发机替身（字体链接、cp 替身）、R277 留本机、9 项本机同样红的失败都要写明 | 把开发机全量写成「全绿」 | 汇报逐条对照上面的结果表 |
| 在本机跑测试和浏览器 | 本机只跑三份 shell 自测；其余经 rbox | 本机直接 `.venv/bin/python -m pytest` | 汇报写明开跑前数到的本机重活进程数 |

## 遇到要拍板的事

先做不受影响的部分，把问题写进汇报后停下。汇报写到 `docs/tasks/R310-photo-devbox/REPORT.md`（不提交它，总控看完再定）。
