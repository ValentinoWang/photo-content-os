# R283 视频风格加风格库 · 前端任务单

需求卡：「脚本直出的视频风格加风格库：九种现成风格直接挑 · 待确认（2026-10-26-R283-photo-direct-style-library）」，在本 worktree 的 `acceptance/requests/2026-W44/2026-10-26-R283-photo-direct-style-library/`。验收项 H-01–H-03 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。由 Codex 账号 2 实现；前后端两段已经做完：

- 样张段：九种风格的数据在 `scripts/direct_video/style_library/`，汇报 `REPORT-S.md`；
- 后端段：接口已实现，汇报 `REPORT-B.md`。

## 0. 位置和边界

- 只在任务 worktree 里改，不提交、不推送，不改写已有提交，不许 `git worktree add`，不改主目录。
- **你可以改的文件**：
  - `studio/static/direct-style.js`、`studio/static/direct-view.js`、`studio/static/direct-rescript.css`；
  - 新测试 `tests/test_r283_frontend.mjs`、`tests/test_r283_frontend.py`，夹具 `tests/fixtures/r283-direct/`；
  - 门禁 `scripts/direct_video/rescript_frontend_gate.mjs`；R276、R277 的门禁只在合同组合需要时改；
  - R278 的前端测试和夹具只在风格库让它们变了的地方改，逐条写进汇报。
- **不许碰**：
  - 后端 `.py`、`schemas/`；
  - `scripts/direct_video/style_library/` 下的数据；
  - `acceptance/`、`agents-results/`。
- 端口 8765–8769 都不许动，门禁用 8768。
- **本机例外预算**：
  - 浏览器只开无头的，同一时间只开一个，用完就关；
  - 门禁串行跑；
  - 不跑全量 pytest；
  - 磁盘低于 3 GB 停下。
- 遇到要拍板的事：先做不受影响的部分，写进汇报后停下。

## 1. 设计稿（以它为准）

在 `docs/tasks/R278-direct-rescript/design/`：

- `spec.html` 里标「R283」的内容：
  - 第 1 节「风格库（R283）」和「其他」里 R283 上线后的那段；
  - 第 3 节 `DV-STYLE-LIB`；
  - 第 4 节「视频风格 · 风格库（R283）」那行文案；
  - 第 5 节 R283 接口三行；
  - 第 6 节「R283 前端」。
- `draft.js`、`draft.css`、`lib-data.js`：风格库那组的画法。
- `contract.json`：已重新生成，2026-10-27 起风格库在「选现成的风格」里**一直显示**：
  - 所有 R278 的选现成风格状态（`rescript`、`rescript-zoom`、`rescript-adjust`、`rescript-other`、`first` 等）都多了「风格库」一组九张卡；
  - R278 单独上线时的 `first-none-r278` 状态已经删掉，由 R283 的 `first-none` 取代。

## 2. 要做什么

1. **「选现成的风格」分两组**：
   - 上面「这台电脑上做过的」，和 R278 一样；
   - 下面「风格库」，小字「样张都是同一段台词」，九张卡，顺序照接口返回。卡片和做过的一样（样张图 45×80、名字、四个色块），没有时间那一行。
   两组合起来单选，同一时间只能选中一张。
2. **选中风格库的一张**：
   - 右边放样张动画：`video`，静音、循环、自动播放，进屏播放、出屏暂停，减少动态效果时不播，读不到就换成样张图；
   - 下面写「样张 · 同一段台词」；
   - 旁边标题「风格库 · 〈名字〉」，加四色、字号、动作规矩、不用。
3. **「在这个风格上改哪里」**对风格库同样有效。生成条写「风格：风格库「〈名字〉」」，写了改哪里再接「，改：〈改哪里〉」。
4. **生成**：请求体 `styleBase: {kind:'library', id}`，加上可选的 `style`。
5. **全片设计一行**：`design.source.kind === 'library'` 时写「用风格库「〈名字〉」的风格」。
6. **这台电脑上没有做过的成片时**（`first-none`）：
   - 「选现成的风格」照常可点，并且默认选中它；
   - 「这台电脑上做过的」那组换成一句「这台电脑上还没有做过的成片，先从风格库里挑一个。」；
   - 风格库一张都不预选，右半边虚线框「还没选风格 / 在左边选一个」；
   - 生成条用警示色写「风格还没选：在下面选一个现成的风格，或者从头定」，「生成」灰掉。
7. 不写内联 `style=`，色块照 R278 的做法用 CSSOM；新颜色只用令牌。

## 3. 测试、合同和截图

- **测试**：`tests/test_r283_frontend.mjs` 覆盖 spec 第 6 节「R283 前端」那一条；`tests/test_r283_frontend.py` 做静态检查。先在现在的代码上跑一遍，确认会失败，再实现。
- **夹具**：`first-lib`、`first-none`、`library` 三个状态各一份，形状照后端真实投影，`/api/direct/styles` 带 `library`。R278 那 19 个状态的 styles 夹具也要带上 `library`。
- **合同**：
  - 用 `collect_design_inventory.js` 的 `options.states`，把 `contract.json` 里除 `rescript-newer`、`first-handoff`（R282）以外的状态都指到真实页面的对应块；
  - 跑 `check_design_contract.py check`，全部通过；
  - 不许用 approved-extras 绕过。
- **截图**：1440 和 960 各一张，范围：
  - 新的三个状态 `first-lib`、`first-none`、`library`；
  - 风格块变了的 R278 状态：`rescript`、`rescript-adjust`、`rescript-other`、`first`。
  放仓库外 `~/.photo-content-os/evidence/R283-direct-style-library/frontend/`，逐张看过。
- **R276、R277 门禁**：合同组合里补上 R283 已批准的文案，照 R278 当时的做法，逐条写进汇报。
- **要跑的检查**：
  - `node tests/test_r283_frontend.mjs`、`node tests/test_r278_direct_rescript.mjs`；
  - 前端 pytest：R283、R278、R276、R277；
  - `rescript_frontend_gate.mjs --checks-only`，然后截图；
  - R276 `frontend_gate.mjs --checks-only`；
  - R277 `revision_frontend_gate.mjs --checks-only`，设 `R277_SOURCE_STATE=~/.photo-content-os/studio-r278`；
  - `scripts/check_repository_safety.py --base HEAD`，查工作区和暂存区。
  环境变量照 R278 的 `REPORT-F1.md` 第 7 节。

## 4. 汇报

写到 `docs/tasks/R283-direct-style-library/REPORT-F.md`，内容：

- 改了哪些文件；
- 第 2 节每条做到什么程度；
- 测试：实现前的失败摘要和实现后的结果；
- 合同检查结果；
- 截图清单和看图结论；
- 改了哪些 R276/R277/R278 的测试、夹具、门禁（逐条）；
- 需要的接口、需要新文案、稿外元素。

写完停止。
