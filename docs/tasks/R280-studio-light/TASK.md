# R280 Studio 界面换成浅色 · 前端任务单

需求卡：「Studio 界面换成浅色 · 待确认（2026-10-26-R280-photo-studio-light）」，在本 worktree 的 `acceptance/requests/2026-W44/2026-10-26-R280-photo-studio-light/`（只读）。验收项 H-01、H-02 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。用户已认可设计稿，由 Codex 账号 2 实现。

## 0. 位置和边界

- 只在任务 worktree `photo-content-os-r280-studio-light` 里改。这个 worktree 是 `task_worktree.py` 建的，基于 origin/main（R278、R283、R282 都已在里面），`.venv` 软链到主目录。
  - 不许 `git worktree add`，不改主目录，不提交、不推送。
- 端口 8765–8769 的 Studio 都不许动。门禁用 8768，状态目录用临时目录。
- **本机例外预算**：
  - 浏览器只开无头的（固定的 `chromium_headless_shell-1228`），同一时间只开一个，用完就关；门禁串行跑。
  - 不跑全量 pytest。
  - 磁盘低于 3 GB 停下。
  - 无头浏览器不见了（`~/Library/Caches/ms-playwright/chromium_headless_shell-1228/` 不存在）就停下汇报，不要换系统 Chrome 跑。
- 遇到要拍板的事：先做不受影响的部分，写进汇报后停下。

## 1. 设计稿（以它为准）

`docs/tasks/R280-studio-light/design/`：

- `index.html`：
  - 第 1 节：逐页对比，现在 → 浅色；
  - 第 2 节：颜色令牌，每个令牌的现在值、浅色值、用在哪；
  - 第 3 节：写死的颜色；
  - 第 4 节：门禁。
- `light.css`：浅色令牌和覆盖规则，「写死颜色」两节逐条列了要改的地方。

稿子里的页面截图（`img/`）不进仓库，稿子在主目录 `docs/tasks/R280-studio-light/design/img/` 里，需要就去那里打开看。

## 2. 要做什么

1. **改颜色令牌**：`studio/static/styles.css` 的 `:root` 令牌换成第 2 节的浅色值。
2. **改写死的颜色**：照第 3 节和 `light.css` 的「写死颜色」两节，在 `styles.css`、`workflow.css`、`review.css`、`direct*.css` 等样式表里逐条改。
   - 能换成令牌的换成令牌：侧栏、悬停、标签、提示框、步骤圆点、轨道底。
   - 主按钮和品牌标的字改成白色，主按钮悬停色 `#18767E`。
   - `studio/static/index.html` 的 `<meta name="color-scheme">` 改成 `light`，表单控件和滚动条跟着变浅。
3. **保持深色**：`.handoff .stage`（视频预览区）、播放钮、成片播放器、关键帧图本身、脚本直出的画面图和放大浮层里的画面。
4. **只换颜色**：页面结构、字号、间距不动；不加、不删可见文字和元素。
5. 不写内联 `style=`。

## 3. 门禁和截图

- **新测试** `tests/test_r280_light.py`，照第 4 节：
  - `styles.css` 的 `:root` 令牌等于第 2 节的值；
  - `styles.css`、`workflow.css` 里，除了允许的视频区规则，不再出现深色字面量（亮度低于 30% 的颜色）；
  - 正文和次要文字对底色的对比度 ≥ 4.5；`--ink-4` 只用在占位和说明小字上，对比度 ≥ 3。
  - 先在现在的代码上跑一遍，确认会失败，再改。
- **现有前端门禁全部重跑，文字和编号的合同不应该变**：
  - R276 `frontend_gate.mjs`、R277 `revision_frontend_gate.mjs`、R278/R282/R283 `rescript_frontend_gate.mjs`，都用 `--checks-only`；
  - R277 设 `R277_SOURCE_STATE=~/.photo-content-os/studio-r278`；
  - 环境变量照 R278 的 `docs/tasks/R278-direct-rescript/REPORT-F1.md` 第 7 节；
  - 前端测试：R276、R277、R278、R282、R283 的 `.mjs` 和前端 pytest。
- **截图**：用临时状态目录起 8768，每页拍 1440 一张，放仓库外 `~/.photo-content-os/evidence/R280-studio-light/`。逐张看过，确认：
  - 浅色底、文字清楚、没有残留的大块深色；
  - 视频区仍是深色。
  - 页面范围：工作台、整理台、项目、作品页三个分页（含脚本直出改分镜脚本那一屏）、素材库、音乐库、设置。
  再拍「脚本直出」和第 02 镜详情的 960 宽各一张。
- `scripts/check_repository_safety.py --base HEAD`。

## 4. 汇报

写到 `docs/tasks/R280-studio-light/REPORT.md`，内容：

- 改了哪些文件；
- 每个令牌和每处写死颜色的处理结果；
- 测试：实现前的失败摘要和实现后的结果；
- 门禁结果；
- 截图清单和看图结论；
- 稿外的东西（有就写出来，没有写「无」）。

写完停止。
