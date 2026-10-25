# R276 脚本直出 · 前端任务单

需求卡：「Studio 里一键直出：Opus 按口播稿写每一镜动画，本机渲染出成片 · 待确认（2026-10-26-R276-photo-direct-video-opus）」。验收 H-01–H-03 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。**用户 2026-10-26 已认可设计稿**，指定由 Codex 账号 2 实现。后端已由另一个 Codex 线程（账号 1，`01a173fd-…`）在同一个 worktree 里做完第一段，第二段（真跑）正在跑。

## 0. 工作位置和边界

- 只在 `/private/tmp/task-worktrees/photo-content-os-r276-direct-video` 里改。不许 `git worktree add`，不许改主目录 `~/Desktop/创业项目/photo-content-os`。不提交、不推送、不杀别人的进程。
- **你只许改这些文件**：
  - 新建 `studio/static/direct-view.js`、`studio/static/direct.css`：脚本直出整页（除单镜详情外的全部）。
  - 新建 `studio/static/direct-shot-detail.js`、`studio/static/direct-shot-detail.css`：「选中一镜后的详情」整块。**这两个文件以后会被 R277 整块替换**，对外只有一个入口（见第 3 节），别的文件不许直接画详情里的东西。
  - `studio/static/review-view.js`：只加分页「脚本直出」和 `ptab=direct` 的路由，调用 `direct-view.js` 的入口。改动越少越好。
  - `studio/static/index.html`：只加两个样式表链接。
  - 新测试 `tests/test_r276_direct_frontend.py`、`tests/test_r276_direct_frontend.mjs`，以及截图和合同检查脚本 `scripts/direct_video/frontend_gate.mjs`（或同名 .py）。
- **不许碰**：`scripts/direct_video/*.py`、`studio/direct_video.py`、`studio/server.py`、`studio/api_contract.py`、`schemas/`、`scripts/llm_common.py`，这些归后端线程。接口不够用时写进汇报「需要的接口」，不要自己改后端。
- 端口：8765 是用户在用的 Studio，不许动；8766 归后端线程真跑。你要起 Studio 就用 8767，状态目录用临时目录。

## 1. 先读

- 设计稿（权威）：主目录 `docs/tasks/R276-direct-video-opus/design/`
  - `index.html`：交互规则（第 1 节）、设计编号和接口字段（第 4 节）、失败代码翻译表（第 5 节）、数字公式（第 6 节）、门禁（第 7 节）。
  - `direct.html`：可以点的稿，十个状态，底部状态条切换。新组件样式在它头部 `<style>` 里（`.dv-` 开头），照抄到 `direct.css` / `direct-shot-detail.css`；颜色只用 `studio/static/styles.css` 里的令牌。
  - `contract.json`：文案表和设计编号合同（由 `export_states.py` 从稿导出）。
- 接口和任务投影：主目录 `docs/tasks/R276-direct-video-opus/TASK.md` 第 2.3 节；实际实现看 worktree 里 `studio/direct_video.py` 的投影函数。字段以代码为准，和任务单不一致时写进汇报。
- 现有前端写法：`studio/static/review-view.js`（路由、`api()`、`top()`、`mark()`、分页）、`review-shots.js`（挑镜头页，步骤条 `flowSteps`）、`review-common.js`。照它的写法，不引第三方库。
- 设计合同检查：`~/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/ui-copy-quality/scripts/check_design_contract.py`（`check --contract … --inventory …`），页面清点脚本 `…/ui-copy-quality/assets/collect_design_inventory.js`。

## 2. 要做什么（每条都要能对照截图或测试检查）

1. 作品页分页变成「按素材剪 vlog · 按脚本做视频 · 脚本直出」，`ptab=direct` 打开脚本直出；`localStorage` 记住上次分页的现有逻辑照旧（`['vlog','script','direct']`）。
2. 进页时取 `GET …/direct/jobs/latest`：`job:null` → 「还没生成」第一屏；有任务 → 按任务状态显示。读取失败 → 提醒块「读不到这件作品的直出任务」+「重试」，**不许显示成第一屏**。
3. 第一屏：口播稿文本框；按行切分（去掉空行和首尾空白），下面列出每镜编号、口播、估算秒数；合计「N 镜 · 按字数估约 m:ss · 每秒按 5.1 字算」。没内容时「生成」灰掉。「导入分镜文件」读本地 `storyboard.json`（`shots[].dialogue`）填进文本框。风格说明一行输入。配音「上传配音…」在没有任务时先记在页面上，建好任务后再传（或在任务生成后传，二选一，写进汇报）。
4. 「生成」→ `POST …/direct/jobs` `{script, style}`；成功后进入任务显示。
5. 顶栏右侧「Opus 5.5 · 本机 Claude」：任务 `failureCode = claude_cli_unavailable` 或建任务返回这个错误时显示黄点「调不通」，页面出 `DV-UNAVAILABLE` 提醒块，「生成」「重写」灰掉。
6. 任务显示：步骤条三步（照稿文字）；全片设计一行（`design.status` 不是 done 时是虚线框一句话）；进度行（x / N 镜写好、进度条、已用时间、三镜同时写）；七镜胶片；选中一镜的详情（第 3 节）；配音和合成按钮；成片块。
7. 镜卡：关键帧用 `poster.jpg?v=<posterRevision>`；还没有关键帧时按状态显示「等着写」虚线框 / 「Opus 正在写 · 已写 m:ss」流光 / 「自查没过，正在重写」/「没写成」。状态文字和颜色照稿：等着写（灰）、正在写（主色）、自查没过正在重写（黄）、写好 · m:ss（绿）、写了两次都没过（红）、按你的意见重写（主色）、中断了（灰，带「重试」）。
8. 轮询：任务没结束时每 2 秒 `GET …/jobs/{jobId}`；结束的定义：`status` 是 `ready`、`done` 或 `failed`，且没有镜在 `writing / rendering`，且 `output.status` 不是 `composing`。结束就停，离开页面（路由变了）也停。
9. 配音：「上传配音…」选 WAV → `POST …/narration`（请求体就是文件，`Content-Type: audio/wav`）。按钮文字：没有配音「先合成无声预览」，有配音「合成成片」→ `POST …/compose`。
10. 成片：真的 `<video src="…/output.mp4?v=<revision>">`，按稿的样子：竖屏 288×512、居中大播放钮、进度条和「m:ss / m:ss」；右边标题、一行信息（竖屏 1080×1920 · N 镜 · 带配音或无声预览 · m:ss）、四项检查（读 `output.checks`）、N 镜缩略条（点哪镜 `video.currentTime` 跳到那镜开始秒数）。「在访达中显示」没有后端接口就**不放**（不许放只弹提示的按钮），写进汇报「需要的接口」。
11. 失败代码一律按设计稿第 5 节翻成中文；没登记的代码写「读不到这一镜的状态，点重试」。页面上不许出现英文失败代码、本机绝对路径、`undefined`、`NaN`。
12. **不写内联 `style=`**：Studio 的内容安全策略会拦。宽度、缩放、颜色块用 CSS 类，或在脚本里 `el.style.setProperty(…)`。
13. 减少动态效果时，「正在写」的流光不动。
14. 七镜一排的版式：1440 宽一排七张（每张约 160 宽）；≤1180 四列；≤960 四列；≤620 三列。卡片口播两行省略，不许撑高卡片。

## 3. 单镜详情模块（R277 会整块替换）

`direct-shot-detail.js` 只导出一个函数：

```js
export function renderShotDetail(container, { job, shot, projectId, api, onRewrite }) { … }
```

- `container`：详情要画进去的空元素；`job`：整个任务投影；`shot`：选中的那一镜（`job.shots` 里的对象）；`api`：`review-view.js` 里现有的请求函数；`onRewrite(shotId)`：重写请求发出后通知外层立即刷新一次。
- 画：大关键帧（`poster.jpg`，252×448，下面一行「关键帧 · 这一镜 x.x 秒处的 80%」）；没写成时画「这一镜还没有画面」。右边：第 NN 镜、写好于 m:ss；口播原文；四格（时长、写了几次、主动作、代码字数）；检查结果（`checks.errors` 红叉、`warnings` 黄叹号，再列能渲染的五条硬规则）；修改意见输入（1–200 字）+「让 Opus 重写这一镜」→ `POST …/shots/{shotId}/rewrite {instruction}`；「看代码」折叠，展开时才 `GET …/shots/{shotId}/code`，等宽显示。
- **轮询重画不许清掉用户正在输入的修改意见、不许抢走焦点**：只有这一镜的 `status`、`posterRevision`、`checks`、`attempts` 变了才重画，重画时保留输入框的值和焦点。
- 默认选中：失败的镜 → 正在重写的镜 → 第一镜；用户点过的镜一直保持选中，直到换任务。

## 4. 数字公式（每条写成测试）

| 数字 | 公式 |
|---|---|
| 每镜估算秒数 | 口播字数（含标点，按字符计）÷ 5.1，四舍五入一位小数；有 `measuredSeconds` 时用实测 |
| 合计 m:ss | 各镜秒数相加，四舍五入到整秒 |
| x / N 镜写好 | 状态是 `written`、`rendering`、`rendered` 的镜数 / 总镜数 |
| 已用 m:ss | 现在 − `createdAt` |
| 写好 · m:ss | `writtenAt − createdAt`；重写后只有那一镜变 |
| 正在写 · 已写 m:ss | 现在 − 这一镜最近一次开始写的时间（投影里没有这个字段就写进汇报「需要的接口」，先不显示秒数） |
| 合成进度 | 投影里有帧数就用帧数，没有就只显示「合成中」，不编数字 |

## 5. 门禁和截图

- `tests/test_r276_direct_frontend.mjs`：上面的公式；按行切分；轮询结束条件；失败代码翻译（含未登记代码）；详情模块轮询重画保留输入值。
- `tests/test_r276_direct_frontend.py`：新文件里没有 `style=` 内联样式、没有英文失败代码字面量出现在页面文字里、`review-view.js` 有 `direct` 分页、`index.html` 引了两个样式表。
- 状态夹具：照十个设计状态各写一份任务投影 JSON（形状照后端真实投影；「还没生成」是 `job:null`，「调不通」是建任务返回 `claude_cli_unavailable`），放 `tests/fixtures/r276-direct/`。截图脚本用 Playwright 拦截这几个接口返回夹具，打开真实 Studio 页面（8767，临时状态目录），逐状态截图 1440 和 960 两个宽度，放仓库外 `~/.photo-content-os/evidence/R276-direct-video-opus/frontend/`；同时用 `collect_design_inventory.js` 清点、`check_design_contract.py check --contract <主目录>/docs/tasks/R276-direct-video-opus/design/contract.json` 比对，十个状态都要通过。稿外文字或元素：写进汇报「需要新文案」「稿外元素」后停下，不要自己加。
- 最差首屏：「读不到任务」和「调不通」两个状态必须截图。
- **你自己逐张看截图**，再交给总控；总控也会逐张看。

## 6. 分段

- **第一段（F1）**：第 2–5 节全部做完，夹具截图和合同检查通过，相关现有前端测试（`test_p2_frontend_contract.py`、`test_r220_number_formulas.*`、`test_checklist_remediation_static.py`）不被你弄红。汇报写 worktree 里 `docs/tasks/R276-direct-video-opus/REPORT-F1.md`：改了哪些文件、截图目录、合同检查结果、测试结果、需要的接口、需要新文案、稿外元素。**然后停下。**
- **第二段（F2，总控开）**：等后端真跑完，用真实任务数据在真实 Studio 上截「写到一半 / 七镜写好 / 成片出来」三屏，按总控看图意见改。
