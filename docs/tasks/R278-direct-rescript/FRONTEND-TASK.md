# R278 改分镜脚本、先定视频风格 · 前端任务单（第二段）

需求卡：「脚本直出先定视频风格，生成过以后能回到分镜脚本改了重新生成 · 待确认（2026-10-26-R278-photo-direct-rescript）」，在主目录 `acceptance/requests/2026-W44/2026-10-26-R278-photo-direct-rescript/`（只读）。验收项 H-01–H-03 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。**用户 2026-10-26 已认可设计稿**，由 Codex 账号 2 实现。

后端已由 Codex 账号 1 在同一个 worktree 里做完（线程 `01a17852-…`），没有提交。汇报在 worktree 的 `docs/tasks/R278-direct-rescript/REPORT-A.md`，接口和投影字段以那里和代码为准。

## 0. 工作位置和边界

- 只在 `任务 worktree` 里改。
  - 不许 `git worktree add`，不许改主目录。
  - 不提交、不推送、不杀别人的进程。
- **你可以改的文件**：
  - `studio/static/direct-view.js`、`studio/static/direct.css`；
  - 新建 `studio/static/direct-*.js`、`studio/static/direct-*.css`：建议把分镜脚本表、视频风格各拆一个文件，单个文件别再长成几千行；
  - `studio/static/index.html`：只加样式表或脚本链接；
  - 测试：新建 `tests/test_r278_direct_rescript.mjs`、`tests/test_r278_direct_frontend.py`，夹具放 `tests/fixtures/r278-direct/`；
  - 截图和合同检查：`scripts/direct_video/frontend_gate.mjs`（R276 的），或新建 `scripts/direct_video/rescript_frontend_gate.mjs`；
  - R276、R277 的前端测试、夹具、`approved-extras`：只在设计稿让它们变了的地方改，逐条写进汇报。
- **不许碰**：后端文件。包括 `scripts/direct_video/*.py`、`studio/direct_video.py`、`studio/direct_style_contract.py`、`studio/server.py`、`studio/api_contract.py`、`schemas/`。接口不够用就写进汇报「需要的接口」，不要自己改。
- **R277 的单镜详情**：`direct-shot-detail.js`、`direct-shot-detail.css`、`direct-revision-log.js` 不改。详情里的「口播「…」」也不改。
- **端口**：
  - 8765（用户在用）、8766（R276/R277 验收）、8767（总控的临时 Studio）都不许动；
  - `frontend_gate.mjs` 现在把 8767 写死了：改成读环境变量（例如 `DIRECT_GATE_PORT`，默认还是 8767），这次用 8768，状态目录用临时目录。
- **本机负载**：用户要求本机少跑重活。
  - 浏览器只开无头模式，同一时间只开一个，截完立刻关；
  - 截图只拍下面第 4 节列的状态，1440 和 960 两个宽度；
  - 中间试拍的图删掉，只留最后一轮；
  - 不跑全量 pytest；
  - 磁盘低于 3 GB 时停下汇报。
- 遇到要拍板的事：先做不受影响的部分，写进汇报后停下。

## 1. 先读

设计稿在主目录 `docs/tasks/R278-direct-rescript/design/`，以它为准：

- `spec.html`：给你的实现说明。
  - 第 1 节：交互规则。
  - 第 2 节：所有状态，每块标了 `data-design-state="<状态>-<块>"`。
  - 第 3 节：设计编号，有尺寸、颜色令牌、代码依据。
  - 第 4 节：文案表。
  - 第 5 节：数字公式和接口。
  - 第 6 节：门禁。
  - **标「R282」「R283」的规则、文案、状态这次都不做。**
- `draft.css`：新块的样式。照抄进 `direct*.css`，颜色只用 `studio/static/styles.css` 的令牌。稿子里用 `style="--swatch:…"` 的地方，Studio 里改成在脚本里 `el.style.setProperty('--swatch', …)`，因为 Studio 的内容安全策略拦内联 `style=`。
- `draft.js`：各块的画法、可点演示（拆镜、并镜、粘贴、放大浮层、选风格、样张流程）。逻辑照它，但要按 Studio 现有写法重写，不要整份搬。
- `contract.json`：文案表和设计编号合同，由 `spec.html` 导出。
- `index.html`：给用户看的短页，可以打开点一点，了解用户认可的样子。
- 现有前端：
  - `studio/static/direct-view.js`、`direct.css`；
  - `review-view.js`（`api()`、路由、分页）；
  - `tests/test_r276_direct_frontend.mjs`、`scripts/direct_video/frontend_gate.mjs`；
  - `docs/tasks/R276-direct-video-opus/FRONTEND-TASK.md`：R276 前端当时的做法，夹具、截图、合同检查照它来。
- Core 规则（`~/Desktop/Opensource_Tool/Harness_Engineering/Core/harnesses/`）：
  - `product-frontend-harness.md`；
  - `ui-copy-quality-guard-card.md`；
  - `frontend-screenshot-completion-guard-card.md`；
  - `agent-collaboration-harness.md` 里「派前端活」那几条：不许自加可见文字和稿外元素。

## 2. 要做什么

按 `spec.html` 第 1 节逐条实现，每条都要能对照截图或测试检查。要点：

1. **入口**：生成过以后，步骤条「分镜脚本」那一格整格可点，右边写「改分镜脚本」；正在写、正在合成时灰字写原因。点进去是「改分镜脚本，重新生成」一屏，各列预填，默认沿用这条的风格；「回到现在这条」不发请求。
2. **版式**：第一屏和改分镜脚本一屏都是整行从上到下排：
   - 分镜脚本；
   - 视频风格；
   - 「点「生成」以后」和「配音」两张卡并排；
   - 生成条。
   右栏 340 不要了。≤960 宽时上下排。
3. **分镜脚本表**：六列，列名和中台一字不差。
   - 镜头列写镜号和起止时间，按 spec 第 5 节公式算。
   - 画面列放画面图或动画，旁边是来源标签和说明。改分镜脚本时画面是这一版每镜的小片段，用 `video[muted][loop][playsinline]`，封面是关键帧：
     - 进屏播放、出屏暂停；
     - 减少动态效果时不播；
     - 读不到片段时换成关键帧。
   - 点画面图放大成浮层，规则照 spec 第 1 节。
   - 台词里回车拆成两镜，台词开头退格并到上一镜，带换行的粘贴拆成多镜，输入法组字时的回车不拆。
   - 每镜的字在页面上只出现一次。
   - 空状态是大粘贴框；「导入分镜文件」把四列放进对应列。
   - 发出去的是带新字段的 `storyboard`，台词空的镜不发。
4. **视频风格**：分段按钮「选现成的风格」「从头定风格」。
   - 「这台电脑上做过的」卡片取自 `GET /api/direct/styles`；右边大预览；「在这个风格上改哪里」。
   - 从头定：说明框、六个提示小按钮、「先定风格」。样张流程对 `style-drafts` 三个接口，包括「正在定风格 · 已用 m:ss」、「再改一句」「改」、「就用这个」「已选用」「重新定」、失败和重试。
   - 切换分段时两边写的字都保留。
   - 这台电脑上没有做过的成片时，照 `first-none-r278` 状态：「选现成的风格」灰掉，默认从头定。
5. **生成条**：放在最底下，左边写清用的是哪个风格，右边「生成」。可点条件照 spec 第 5 节；发出的 `styleBase`、`style` 照接口。
6. **全片设计一行**：两个标题「动作规矩」「不用」，内容用 `motionSummary`、`bannedShort`，不划删除线；前面写来源（`design.source`）。老任务两字段为 `null` 时显示原话，不超过两行。
7. **改名**：`direct-view.js` 里所有「口播稿」改成「分镜脚本」，每镜那句叫「台词」。
8. 不写内联 `style=`；新颜色只用令牌。

## 3. 测试

- `tests/test_r278_direct_rescript.mjs`：`spec.html` 第 6 节「前端」那一条里不带 R282 的全部内容；第 5 节的公式各一条。
- `tests/test_r278_direct_frontend.py`：新文件里没有 `style=`；`direct-view.js` 里不再有「口播稿」；`index.html` 引了新文件。
- 先在现在的代码上跑一遍，确认会失败，再实现。

## 4. 夹具、截图和合同检查

- **夹具**：照下面每个状态各写一份接口返回，形状照后端真实投影，放 `tests/fixtures/r278-direct/`。截图脚本用 Playwright 拦截接口返回夹具，打开真实 Studio 页面（8768，临时状态目录）。
- **这次要做的状态**（`spec.html` 第 2 节里的名字）：
  - 入口：`entry`、`writing`、`composing`；
  - 改分镜脚本：`rescript`、`rescript-zoom`、`rescript-adjust`、`rescript-other`；
  - 第一次：`first-empty`、`first`、`first-new`、`first-new-text`、`first-new-drafting`、`first-new-ready`、`first-new-revising`、`first-new-accepted`、`first-new-failed`、`first-none-r278`；
  - 全片设计一行：`designing`、`inherited`、`adjusted`。
  - **不做**：`rescript-newer`、`first-handoff`、`first-lib`、`first-none`、`library`。
- **合同检查**：
  - 用 `~/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/ui-copy-quality/assets/collect_design_inventory.js` 的 `options.states`，把上面每个状态的每一块指到真实页面的对应块；
  - 再跑 `check_design_contract.py check --contract <主目录 design/contract.json> --inventory …`，只查上面这些状态，全部通过；
  - 需要新文案或稿外元素时，写进汇报，不要自己加进 `approved-extras.json`。
- **截图**：
  - 每个状态拍 1440 和 960 两张，放仓库外 `~/.photo-content-os/evidence/R278-direct-rescript/frontend/`；
  - 再拍一张真实数据最差首屏：用 `~/.photo-content-os/studio-r276/direct-jobs-parked/project-fc6baa3294/dv_0e184e961bd14ac084c67411` 的 `job.json` 做「改分镜脚本」的投影。这个目录只读，拷贝出来再用。
  - 你先逐张看一遍截图，再交给总控；总控会逐张再看。
- **R276/R277 门禁**：
  - R276 的 `frontend_gate.mjs` 里 empty、filled、unavailable 的版式，各任务状态的步骤条，以及 `DV-DESIGN` 的写法都变了，要同步更新；
  - R277 门禁里带步骤条的截图同样要更新；
  - 每处改动逐条写进汇报，之后总控按 G16 处理。

## 5. 要跑的检查

- `node tests/test_r278_direct_rescript.mjs`；
- `.venv/bin/python -m pytest -q tests/test_r278_direct_frontend.py tests/test_r276_direct_frontend.py tests/test_r277_frontend.py`；
- `node tests/test_r276_direct_frontend.mjs`、`node tests/test_r277_frontend.mjs`；
- 截图和合同检查脚本。`HARNESS_CORE` 指向 Core 目录；Playwright 用：
  - `VIDEO_RENDER_PLAYWRIGHT_MODULE=~/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js`（ESM 入口用同目录 `index.mjs`）；
  - `VIDEO_RENDER_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`。
- `scripts/check_repository_safety.py --base origin/main`。

## 6. 汇报

写到 worktree 的 `docs/tasks/R278-direct-rescript/REPORT-F1.md`，内容：

- 改了哪些文件；
- 第 2 节每条做到什么程度；
- 测试：实现前的失败摘要和实现后的结果；
- 合同检查结果；
- 截图清单（状态 × 宽度 × 路径），以及你自己看图发现、已经改掉的问题；
- 改了哪些 R276/R277 测试、夹具、门禁（逐条）；
- 需要的接口、需要新文案、稿外元素；
- 没做完的地方。

写完停止。
