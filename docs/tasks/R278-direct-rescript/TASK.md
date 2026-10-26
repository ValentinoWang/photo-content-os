# R278 改分镜脚本、先定视频风格 · 后端任务单（第一段）

需求卡：「脚本直出先定视频风格，生成过以后能回到分镜脚本改了重新生成 · 待确认（2026-10-26-R278-photo-direct-rescript）」，在主目录 `acceptance/requests/2026-W44/2026-10-26-R278-photo-direct-rescript/`（只读）。验收项 H-01–H-03 原样照卡，不许自行改。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（会话名 photo-content-os-f8，账号 3）。本段只做**后端**；前端等这一段验收后另派 cdx 2。

## 0. 工作位置和边界（必须遵守）

- **只在任务 worktree 里改**：`任务 worktree`。
  - 总控已经用 `task_worktree.py create` 建好，基于 origin/main `107b56e`，`.venv` 软链到主目录。
  - **不许**自己 `git worktree add`，不许改主目录 `~/Desktop/创业项目/photo-content-os`：主目录里有别的会话没提交的改动。
- 设计稿和本任务单在主目录 `docs/tasks/R278-direct-rescript/`，只读。收尾时由总控把它们拷进 worktree。
- 不提交、不推送、不回退别人的改动、不杀别人的进程。
- 端口 8765（用户在用）、8766（R276/R277 验收用）、8767（临时）上的 Studio 一律不许动、不许重启，也不许写它们的状态目录。
- **本机负载**：用户要求重活不放本机，本项目还没有开发机。所以：
  - pytest 只跑本任务相关的测试文件，不跑全量；
  - 这一段不起浏览器；
  - 真调 Opus、真渲染只做第 4 节那一次；
  - 渲染出的中间帧用完就删；
  - 磁盘可用低于 3 GB 时停下汇报。
- 遇到要拍板的事：先做不受影响的部分，把问题写进汇报后停下。
- 证据（日志、JSON）放 worktree 里的 `evidence/2026-10-26/R278-direct-rescript/`；渲染出的帧、MP4 放仓库外 `~/.photo-content-os/evidence/R278-direct-rescript/`。

## 1. 先读

- worktree 里的 `AGENTS.md`、`CONTRIBUTING.md`、`docs/execution-rules.md`。
- **设计稿的实现说明**：主目录 `docs/tasks/R278-direct-rescript/design/spec.html`（浏览器打开或直接读源码）。本段看：
  - 第 1 节「交互规则」，了解前端要什么；
  - 第 5 节「数字公式和接口」：接口以这一节为准；
  - 第 6 节「门禁」的后端几条。
  - **标「R282」「R283」的行这次都不做**，那是另外两张卡。
- R276、R277 的现有实现，照它们的写法扩展，不重写：
  - `studio/direct_video.py`、`studio/direct_revision_contract.py`；
  - `scripts/direct_video/` 下的 `generate.py`、`lint.py`、`media.py`、`revisions.py`、`revision_library.py`、`rules/shots.md`；
  - `studio/server.py` 的路由登记、`studio/api_contract.py`、`schemas/studio-openapi.json`；
  - `tests/test_r276_*.py`、`tests/test_r277_*.py`；
  - `docs/tasks/R276-direct-video-opus/TASK.md`、`docs/tasks/R277-shot-visual-revision/` 的任务单和汇报。
- Core 规则（`~/Desktop/Opensource_Tool/Harness_Engineering/Core/harnesses/`）：
  - `backend-ai-harness.md`、`api-contract-ai-harness.md`；
  - `ai-egress-ownership-guard-card.md`：模型调用一律走 `llm_common.generate_text`；
  - `delivery-handoff-harness.md` 里 G16 受保护测试那一节。

## 2. 要做什么

### 2.1 分镜脚本多四列

`POST …/direct/jobs` 的 `storyboard.shots[]` 加可选字段 `visual`、`subtitle`、`camera`、`audio`，规则照 spec 第 5 节「storyboard.shots[] 新的可选字段」那一行：

- 字符串，去空白后 1–2000 字，空当没有；超长或不是字符串返回 400 `script_invalid`。
- 存进任务的 `shots[]`，没有的为 `null`，任务投影带出。
- 定全片设计的提示里列出每镜的画面、字幕 / 花字、景别 · 运镜，`perShot.mainAction` 照画面定。
- 写这一镜代码的提示里带上这三列，写成「编导写的画面 / 画面上要出现的字 / 景别 · 运镜（照着做；颜色、字号以全片设计为准）」。R277 的重写这一镜同样带上。
- `audio` 只保存，不进任何提示，不进成片。
- `script` 字段照旧收，兼容老的调用。

### 2.2 全片设计加两个给人看的字段

照 spec「全片设计加两个字段」那一行：

- 定设计时（从头定、沿用并改、样张），Opus 在同一次回复里多写两样：
  - `motionSummary`：一句，≤30 字，不含「数字 + 单位」、坐标、百分比；
  - `bannedShort`：1–8 条，每条 ≤12 字。
- 和现有设计校验一起校验。不合格当作定设计失败，照现有规则重试一次。
- 沿用不改时原样复制。老设计没有这两个字段时，投影里为 `null`。

### 2.3 风格从哪来

- **`GET /api/direct/styles`**（新）：列出所有作品里 `design.status==='done'` 的生成，新到旧排；设计内容相同的只留最新一条；`posterUrl` 取镜号最小、有关键帧的那一镜。
- **`POST …/direct/jobs` 加可选 `styleBase`**：
  - `{kind:'job', projectId, jobId}`：
    - `style` 为空 → `design` 原样复制，跳过定设计，不调模型；
    - `style` 不空 → Opus 只在原设计上按这句改，只调一次模型。
  - `{kind:'draft', projectId, draftId}`：
    - 样张必须是 ready，否则 409 `draft_not_ready`；
    - 设计原样复制；
    - 第 01 镜的台词、画面、字幕 / 花字、景别 · 运镜都和样张那一镜一字不差时，直接用样张的代码和关键帧（字节相同）。任一列不一样，第 01 镜照常重写。
  - 不带 `styleBase` 时 `style` 必填，否则 400 `style_required`；读不到 404 `style_base_not_found`。
- **任务投影加字段**：
  - `design.source`：`null` 或 `{kind:'inherited'|'adjusted'|'drafted', projectId, jobId|draftId, title, instruction}`；
  - 第 01 镜用了样张时 `fromDraft: true`。

### 2.4 样张（从头定风格时先出一镜）

照 spec 里 `style-drafts` 那三行：

- `POST /api/projects/{id}/direct/style-drafts`，`{text, shot}` → 202 `{draft}`。后台依次：
  1. 定全片设计（现有校验）；
  2. 用 `shot` 写一镜（现有自查，不过关自动重写一次）；
  3. 本机渲染关键帧。
- `GET …/style-drafts/{draftId}` 和 `…/poster.jpg?v=`：投影字段照 spec 写。
- `POST …/style-drafts/{draftId}/revise`，`{instruction}` 1–1000 字 → 202；在写时返回 409 `draft_busy`。
- 状态落盘在 Studio 状态目录下 `direct-style-drafts/<作品编号>/<样张编号>/`，写入原子化。进程重启后能读回；正在写的标失败，可以重试。

### 2.5 每镜小片段

照 spec「clip.mp4」那一行：

- `GET /api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/clip.mp4?v={posterRevision}`。
- 片段规格：360×640，H.264 `crf 28`，30 帧，无音轨，`+faststart`，长度等于这一镜时长。
- 生成时机：
  - 在出关键帧的同一步，从这一镜**当前版本**的帧压出来，存 `clips/<镜>.mp4`；
  - 换版本（`posterRevision` 变）时重压；
  - 老任务没有片段时，第一次请求现压（帧还在）；
  - 帧也没了返回 404。
- 照现有媒体路由支持 Range。

### 2.6 契约和兼容

- `studio/api_contract.py`、`schemas/studio-openapi.json` 同步。投影里不出现本机绝对路径。写请求照旧要 loopback、同源、`X-Content-OS-CSRF`。
- **R276 受保护测试**：R276 后端测试里有些用例建任务时不带风格，现在要补 `style` 或 `styleBase`。
  - 只做这类最小改动，不改断言的意思；
  - 每改一处，都在汇报里列出文件、用例名和原因；
  - 之后由总控按 G16 给 R276 卡 rebaseline。
- R277 的测试不应该需要改；如果要改，同样逐条列出。

## 3. 先写测试，再实现

- 新建 `tests/test_r278_style_base.py`，覆盖 spec 第 6 节「后端 tests/test_r278_style_base.py」那一条里**不带 R282 的全部内容**。
- 再加两组：
  - spec 第 6 节「后端每镜小片段」那一条：可以用合成的小帧，不用真渲染；
  - 2.1 的四列（存、投影、进哪些提示、`audio` 不进提示、空白当没有、超 2000 字 400）。
- 先在现在的代码上跑一遍，确认会失败，把失败摘要写进汇报，再实现。
- 测试里不真调模型：照 R276、R277 测试的做法，用假生成器或假的可执行文件。

## 4. 实测（只做一次）

全部测试通过后，用一个**临时状态目录**（不是 8765、8766、8767 的）起一个只给自己用的后台进程，或者直接调用服务层，真跑一次样张：

- `text`：「浅米色底，深青做主色，结论只用橙色。标题要粗，数字特别大。每句只动一个东西，动完就停。」
- `shot`：《断更一年，我拆了四句话》第 01 镜的台词。

等到 ready，确认关键帧和 `clips/01.mp4`（或样张对应的片段）能读，再 `revise` 一次「主色再深一点」。

记录：每一步耗时、模型调用次数、成败。跑完关掉进程、删掉临时目录里的帧。本机 Claude 调不通就停下汇报。

## 5. 要跑的检查

- `tests/test_r278_style_base.py` 和这一段新加的测试文件；
- `tests/test_r276_*.py`、`tests/test_r277_*.py`（`.py` 的那几个）。渲染相关的测试需要环境变量：
  - `VIDEO_RENDER_PLAYWRIGHT_MODULE=~/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js`
  - `VIDEO_RENDER_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`
- `scripts/check_repository_safety.py --base origin/main`。
- 已知和本任务无关的：全量 pytest 有 9 个失败、6 个错误（本机 ffmpeg 缺 drawtext、Obsidian 文档时间戳）。本段不跑全量。

## 6. 汇报

写到 worktree 的 `docs/tasks/R278-direct-rescript/REPORT-A.md`，内容：

- 改了哪些文件；
- 第 2 节每一小节做到什么程度；
- 新测试数，实现前的失败摘要，实现后的结果；
- 改了哪些 R276/R277 测试（逐条：文件、用例、原因）；
- 第 4 节实测的耗时、调用次数、成败；
- 要总控拍板的问题；
- 没做完的地方。

写完停止。

## 交接

- 2026-10-26 第一段（后端）已派给 cdx 1，Codex 线程 `01a17852-4a78-7212-b0e1-40a9b619b152`。日志在总控 scratchpad 的 `r278/phaseA.jsonl`，汇报写在 worktree 的 `docs/tasks/R278-direct-rescript/REPORT-A.md`。
- 下一步：总控核对第一段，再派第二段前端给 cdx 2。前端用设计稿 `design/spec.html`、文案合同 `design/contract.json`，标 R282、R283 的状态不做。然后做 R282，再做 R283。R280 另外派。

## 交接 2

- 第一段（后端）做完：汇报 `REPORT-A.md`，新测试 64 项和 R276/R277 专项共 260 项通过（总控重跑新测试 64 项通过）。真跑一次样张：定设计约 20 秒、写镜约 161 秒、渲染加压片约 34 秒；改一次约 169 秒；画面总控看过。
- R276/R277 受保护测试有改动，`REPORT-A.md` 第 4 节逐条列出，交付前按 G16 rebaseline。
- 第二段（前端）已派给 cdx 2，线程 `01a178b3-b596-7042-bbb6-168905880b7a`，任务单 `FRONTEND-TASK.md`，汇报写到 `REPORT-F1.md`。门禁端口改成 8768，因为 8767 是总控的临时 Studio。
- 设计稿 2026-10-26 补了 `first-none-r278` 状态；风格库那组只出现在 R283 的状态里。`contract.json` 已重出，共 126 个状态。

## 交接 3

- 第二段（前端）做完：线程 `01a178b3-…`，中途撞上一次模型容量不足，续跑后完成。汇报在 worktree 的 `REPORT-F1.md`。
  - 20 个状态 × 1440/960 共 40 张，加 1 张真实旧任务最差首屏，合计 41 张截图，在 `~/.photo-content-os/evidence/R278-direct-rescript/frontend/gallery.html`。
  - 合同分块比对 204 处全部通过。
- 总控看过 rescript、rescript-zoom、first-new-ready、entry/writing 步骤条、rescript-960，版式、文案、放大浮层、样张流程和稿子一致，没有要退回的问题。截图是深色界面，浅色归 R280。
- 还没做：
  - 把设计稿、任务单、需求卡拷进 worktree 并提交；
  - 验收物：合同、binding、claims、baseline；
  - R276/R277 受保护测试和门禁的 G16 rebaseline，两份汇报里逐条列了；
  - 起一个跑 R278 代码的 Studio 给用户验收；
  - 推送。
  推送要用户点头；验收用的 Studio 放本机还是开发机，也等用户定。
