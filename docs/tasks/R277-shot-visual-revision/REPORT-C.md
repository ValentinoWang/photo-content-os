# R277 C 段真跑报告

本段**部分完成，因 C-01 状态显示问题停止**。H-01 已完成真实看图、选改法、单镜重写、两版对比和核对；H-02 已完成退回及样例复制。准备 H-03 时再次确认 C-01，按 TASK.md 第 5 节「发现问题写进汇报后停下」停止，没有发第 05 镜 revise，没有凑第三次，没有点「采用」。不能把本报告当作 H-01–H-03 全部通过或真人验收签字。

## 起点与运行边界

- HEAD：`ae80df4`，父提交 `d095d10`。使用本 worktree 的实际代码，未改任何代码、测试、夹具、批准文件或验收记录。
- 开场 `git status --short` 实际已有 `M docs/tasks/R277-shot-visual-revision/TASK.md` 和 `?? .venv`，与口头「干净」存在差异；两者原样保留。证据：[开场状态](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/git-status-before.txt)。本段唯一新增仓库文件为本报告。
- 作品「断更一年，我拆了四句话」，`project-fc6baa3294`；实际选用指定七镜任务 `dv_0e184e961bd14ac084c67411`（也是副本中最新任务）。未新造作品、任务或替换输入。
- 将 `~/.photo-content-os/studio-r276/` 全量复制到系统临时目录后启动 Studio，仅用 8768。原件 8599 文件前后 SHA-256 一致：[原件核验](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/source-preservation.json)。临时目录、浏览器 profile 已删除；仅停止自己启动的服务，8768 无监听；8765/8766 未访问或操作。[清理结果](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/cleanup.json)。
- 真模型走产品 `llm_common.generate_text` → 本机 Claude CLI，`claude_cli / claude-opus-5-5`，使用 R276 真跑相同的 `OPENCLAW_CLAUDE_CONFIG_DIR=~/.claude-account3`。固定 `.venv/bin/python` 启动；未替换模型、模型响应、渲染器或 API。仅拦截字体 CDN，字体为 fallback-local。
- 渲染变量沿用交接 3：`VIDEO_RENDER_PLAYWRIGHT_MODULE=~/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js`；`VIDEO_RENDER_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`。
- 所有截图实际视口 1440×900；每步均有完整页面和详情视口图，22 张均已逐张打开查看，完整页看到底部。原图尺寸、路由、时间、覆盖范围、哈希与意见见 [截图清单](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/screenshot-manifest.json)。其中 C-01 的 4 张图标记 FAIL，其余 18 张图复核 PASS；这些是机器证据的看图结论，不代表真人验收。

## C-01：首次补块时遮住看图进行状态（停止原因）

复现：打开旧镜（`boxes=[]`），点「让 Opus 看一遍」。POST 已接受并返回 `look.status=running`、`boxes=[]`，页面仍然显示「这一镜还没有可以点的块」和「让 Opus 看一遍」，没有第 3.3 节要求的「Opus 正在看这一镜的画面」。第 02 镜与第 05 镜均记录到。截图中没有橙点是正常的，缺的是进行状态说明。

源码只读定位：[direct-shot-detail.js](/private/tmp/task-worktrees/photo-content-os-r277-shot-visual-revision/studio/static/direct-shot-detail.js:57) 的 `lead` 先判断 `!boxes.length`，进入无块按钮分支后不会检查 `look.status==='running'`；因此旧镜正在补渲染和看图时，running 文案被遮住。本段没有修复。

| 镜头 | POST 接受时间 UTC | 证据图（均在接受之后捕获） | 接受响应 |
| --- | --- | --- | --- |
| 02 | 2026-10-25T21:06:47.958000+00:00 | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running-detail.png) · [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running-full.png) | [look=running、boxes=[]](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running.accepted-response.json) |
| 05 | 2026-10-25T21:12:54.582000+00:00 | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running-detail.png) · [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running-full.png) | [look=running、boxes=[]](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running.accepted-response.json) |

关联时间校验：[C-01-evidence.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/C-01-evidence.json)。捕获 helper 在点击后立即 GET 的两个 `.job.json` 恰好抢在 POST 处理前，仍记为 `look=none`；保留原始记录，不改造证据。本问题使用已接受的 POST 响应及其之后的截图、后续 running 轮询确认，不把这两个先返回的 GET 当作 running 投影。第 05 镜开始后核对时间线与相同源码分支，确认问题，随即停止后续写操作；只等已经启动的看图正常结束以便安全清理。

## H-01：选择改法，只重写第 02 镜

实际步骤：

1. 打开指定作品的「脚本直出」，点第 02 镜。旧任务没有块，先点「让 Opus 看一遍」；这是第 5 节明确补充的旧任务准备步骤。真实看图完成后得到 10 个块、4 条发现，其中 3 条落在块上，1 条为整镜问题。
2. **真实输入与卡的差异**：该任务第 1 版实际是点阵图，含「25%」和「估计 50%」两个文字块，卡写的两根「约 25%／约 50%」柱子不存在。没有把设计夹具灌入真实任务。按同一数值对象，实际点 `num`「25%」选「缩小变灰」，点 `gh`「估计 50%」选「做主角」。两者本次都被 Opus 标了橙色「!」；后者的模型建议是「字改短」，仍按卡选择「做主角」。
3. 输入「底色不动」，实际页面显示 `71 / 200 字`。画面编号 1、2 与右边两条改法对应。点击「重写这一镜」，POST revise 接受 3 条要求（补的一句也作为一条 own 要求）。
4. 等真实写代码、渲染、看图与核对结束。当前第 2 版，`baseVersion=1`；两版并排，3 条逐项核对均为 `done`。此处是模型返回的核对结论，不将其扩大为独立内容质量认证。

Opus 首次看图原话如下（来自实际任务投影，不改措辞）：

| 块 | kind | text 原文 | suggest |
| --- | --- | --- | --- |
| num · 「25%」 | 口播同步 | 0.6 处口播还在讲“估计大约一半”，画面已停在 25%，跳过了先铺满一半的阶段，数字比口播早出现 | dim |
| con · 「只有你以为的一半」 | 口播同步 | 橙色结论在 0.6 就已落定，早于“实际只有四分之一左右”这句，结论色在口播之前出现 | dim |
| null · 整镜（boxId=null） | 颜色 | 表示估计值与实际值差值的灰格，与未点亮的暗格对比太弱，观众看不出“一半”的范围，收缩的对比因此不成立 | main |
| gh · 「估计 50%」 | 字量 | 25%、实际注意到、估计 50%、只有你以为的一半四段文字叠在一起，点阵已经表达了 50% 这个估计值，这行可以缩短或并入 | short |

实际提交与核对：

| index | 要求原文 | result | reason 原文 |
| --- | --- | --- | --- |
| 0 | 「25%」缩小一档、改成灰色，不和主角抢。 | done | 空字符串 `""` |
| 1 | 「估计 50%」做成这一镜唯一的主角：数字 150px 以上，柱子至少占画面高度的四分之一。 | done | 空字符串 `""` |
| 2 | 底色不动 | done | 空字符串 `""` |

[完整看图投影](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c02-look-02-finished.job.json) · [选中状态 DOM／字数／编号](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/selected-02.dom.json) · [服务端保存的 revise 要求](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/revise-02-server-received.json) · [最终版本及 verify](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c05-compare-02.job.json)。

逐句对照：

| 预期 | 本轮结论与原因 |
| --- | --- |
| 画面上有几处橙色「!」，点开可看到这一块的问题 | 成立：num、con、gh 共 3 个块有标记；已点开 gh，右栏显示原文与建议。整镜颜色问题另列。 |
| 选了改法的两根柱子出现编号 1、2 | 字面不成立：旧任务没有这两根柱子。实际对应的两个文字块出现编号 1、2；没有将差异记为通过。 |
| 右边「要改的」有同号的两条具体要求，字数≤200 | 成立：两条对应块的要求，含「底色不动」总计 71 字。 |
| 重写后第 1／2 版并排、每条有做到／没做到 | 成立：第 1 与第 2 版并排，3 条均显示「做到了」，verify.reason 均为空。 |
| 其他六镜的画面和写好时间不变 | 成立：下表的 posterRevision、writtenAt、关键帧 SHA-256 均不变；代码 SHA-256 也一致。 |

**重写前后七镜对照**（前 = 第 02 镜准备看图完成后、提交 revise 前；后 = 第 02 镜 verify 完成后、H-02 退回前）：

| 镜 | posterRevision 前→后 | writtenAt 前→后（UTC） | 关键帧 SHA-256 前 | 关键帧 SHA-256 后 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 01 | 1 → 1 | 2026-10-25T17:53:48.147448Z → 2026-10-25T17:53:48.147448Z | `5e3f917c3220778da90ede01f6c6dde8264d269c071aef0dd376d982b46b0917` | `5e3f917c3220778da90ede01f6c6dde8264d269c071aef0dd376d982b46b0917` | 完全不变 |
| 02 | 1 → 2 | 2026-10-25T17:54:09.288910Z → 2026-10-25T21:10:15.299089Z | `8717c6930e21da7c24a5fe72895279523acb7433495ca1b8cb6447089bbc4af9` | `06e99699b63eeb3eaffaf12d6ebfb0f0b0f97ac18fa745d45261f9db778cd753` | 仅此镜改变 |
| 03 | 2 → 2 | 2026-10-25T18:02:28.760644Z → 2026-10-25T18:02:28.760644Z | `3f370f9fce8e61c6b1ab56ff60ce7e7bbd23545c9baceecca9e2c20c2df6e986` | `3f370f9fce8e61c6b1ab56ff60ce7e7bbd23545c9baceecca9e2c20c2df6e986` | 完全不变 |
| 04 | 1 → 1 | 2026-10-25T17:56:49.301081Z → 2026-10-25T17:56:49.301081Z | `9885f5d4cd5da85e8f24c6c5011a9fb3f077702856d6b0ac8fa9ec88b8a9d8a2` | `9885f5d4cd5da85e8f24c6c5011a9fb3f077702856d6b0ac8fa9ec88b8a9d8a2` | 完全不变 |
| 05 | 1 → 1 | 2026-10-25T17:57:31.935371Z → 2026-10-25T17:57:31.935371Z | `f5795d2e64c07dd89beb6e4fcf3018517ae51f7d0d85f0b73d16bb39da14967b` | `f5795d2e64c07dd89beb6e4fcf3018517ae51f7d0d85f0b73d16bb39da14967b` | 完全不变 |
| 06 | 1 → 1 | 2026-10-25T17:57:34.811383Z → 2026-10-25T17:57:34.811383Z | `540a1d9340c6dfdcd25079c08a6147d0c4b4e32d18b60a28bcb2edbb5c09efdb` | `540a1d9340c6dfdcd25079c08a6147d0c4b4e32d18b60a28bcb2edbb5c09efdb` | 完全不变 |
| 07 | 1 → 1 | 2026-10-25T17:59:24.922651Z → 2026-10-25T17:59:24.922651Z | `2c9c9201f1a1c43860fbbeaae02fe1de2a25c5f10b240f9c5455a5aef70fbcb7` | `2c9c9201f1a1c43860fbbeaae02fe1de2a25c5f10b240f9c5455a5aef70fbcb7` | 完全不变 |

机器对照：[h01-shots-comparison.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/h01-shots-comparison.json)，其余六镜 `unchanged=true`。对比版本的代码、关键帧、检查和 review 文件保存在 ~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/artifacts/versions/02/。

## H-02：退回第 1 版，存第 01 镜样例

实际点「退回第 1 版」，POST current 的 body 为 `{"version":1}`。第 02 镜关键帧与代码 SHA-256 均恢复到重写前值，版本列表仍保留 `[1,2]`：[退回哈希证明](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/h02-revert-proof.json)。

标题下那行原样为：**「按字数估 20.8 秒 · 用第 1 版 · 共 2 版」**。卡中「用第 1 版 · 共 2 版」在其中成立；完整一行另外带有时长与来源前缀，已如实抄出，没有改代码让其贴合卡。

随后点第 01 镜的「♡ 这镜好」，真实 PUT sample 返回成功，页面变为「♥ 已存为样例」。样例库实际生成独立文件 `direct-samples/<sampleId>/code.html` 和 `poster.jpg`，与第 01 镜原文件字节相同、inode 不同，确为复制：[样例 API](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/samples-after.json) · [复制证明](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/sample-copy-proof.json)。临时状态清理前把这两份文件再保存在 ~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/sample-copy/，供复核。

| 预期 | 本轮结论 |
| --- | --- |
| 第 02 镜回到重写前样子 | 成立：关键帧及代码 SHA-256 恢复。 |
| 标题下写着「用第 1 版 · 共 2 版」 | 成立：实际完整行如上。 |
| 第 01 镜显示「已存为样例」 | 成立：页面实际为「♥ 已存为样例」，并有真实复制文件。 |

## H-03：问题记录与三次阈值（停止，未完成）

H-01 的两个 action 只为「主次不清」记录 2 次，own「底色不动」不计类；退回没有删这两次。为了按第 5 节凑到 3 次，已开始第 05 镜「让 Opus 看一遍」。本次正常完成，19 个块、5 条发现；确认 C-01 后没有再点改法、没有提交第 05 镜 revise，因此没有生成第 3 次记录和规则草稿。这一步没有替换成 API 伪造计数。

最终只读 GET `/api/direct/revision-log` 返回：`rulesRevision=0`，主次不清 `count=2`，`proposals=[]`，其余类别 count=0。开始前 `rulesRevision` 同为 0，确未采用任何规则：[开始前](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/revision-log-before.json) · [两次后](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/revision-log-after-two.json) · [停止时最终值](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/revision-log-final.json)。接口时间线没有任何 adopt 请求。

| 预期 | 本轮结论与原因 |
| --- | --- |
| 记录页每种问题有次数、出处 | 不成立（本轮未完成界面验证）：只读 API 已见主次不清 2 次、出处均为本作品第 02 镜；停止后未继续操作记录页。 |
| 到 3 次显示「建议写进规则」和起草条文 | 不成立（未触发／未验证）：第 05 镜只看图，未提交第三条 action；不能据此断言产品三次阈值有缺陷。 |
| 没点「采用」前规则不变 | 部分证据成立：从开始到停止 rulesRevision 均为 0，未发 adopt；但没有取得「三次已有草稿仍未采用」这一完整场景证据。 |

需要继续的范围：总控处理 C-01 后，在隔离的真实副本中完成第 05 镜一次 main/dim 修改及真实重写，再打开记录页等待 pending 草稿，核对 count=3 与 rulesRevision 不变；本段未擅自续做或修复。

## 接口时间线与耗时

全部业务写操作均由实际 Studio 按钮发出，5 个写请求均 HTTP 200。每步任务投影保存为对应 `.job.json`；写请求、GET 轮询、响应和阶段变化见 [api-timeline.ndjson](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/api-timeline.ndjson)；[action-durations.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/action-durations.json) 汇总真实观察值。最早两个写请求的原始日志因 helper 字段同名覆盖只保留响应 body：look 请求 body 为实际空对象，revise 的已接收要求另从实际版本 request 落盘（上文链接），没有将其冒充原始浏览器 requestBody；后续请求记录保留 requestBody。

| 操作 | HTTP 返回 | 总观察耗时 | 说明 |
| --- | --- | --- | --- |
| 第 02 镜首次 look | 36ms | 89.616s | 含旧镜补渲染、抽帧、真实 Opus 看图；不是纯模型调用耗时。 |
| 第 02 镜 revise | 18ms | 160.622s | 到第 2 版渲染、看图、逐条 verify 都完成。 |
| 第 02 镜 current=1 | 18ms | 同步完成 | 已比对回退字节。 |
| 第 01 镜 PUT sample | 15ms | 同步完成 | 已核验两份复制文件。 |
| 第 05 镜首次 look | 15ms | 100.307s | 已启动后正常等到结束；没有接着 revise。 |

第 02 镜 revise 的轮询观察阶段：写代码约 66.112s；渲染区间约 62.035s；渲染后看图加逐条核对约 32.475s。轮询间隔约 1s，属于观察边界，非后端高精度埋点。从自己启动的 Studio 子进程树只读观察 Claude 生命周期（约 0.5s 采样），对应本次重写模型约 65.879s、新画面看图约 22.745s、verify 约 9.648s；第 05 镜看图模型约 23.139s。第 02 镜首次 look 在观察器开始前，未另称其纯模型秒数。[进程时间线](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/process-timeline.ndjson) · [模型进程耗时](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/model-call-durations.json)。

## 每步截图与任务投影

下表每一张图都已打开查看；「完整页」覆盖到页面底部，「详情」是同一次操作后的 1440×900 实际视口。C-01 失败图保留，不列为通过样例。

| 步骤 | 完整页 | 详情 | 任务投影 |
| --- | --- | --- | --- |
| c00-initial-02 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c00-initial-02-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c00-initial-02-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c00-initial-02.job.json) |
| c01-look-02-running | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c01-look-02-running.job.json) |
| c02-look-02-finished | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c02-look-02-finished-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c02-look-02-finished-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c02-look-02-finished.job.json) |
| c03-selected-02 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03-selected-02-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03-selected-02-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03-selected-02.job.json) |
| c03b-before-rewrite-02 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03b-before-rewrite-02-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03b-before-rewrite-02-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c03b-before-rewrite-02.job.json) |
| c04-rewrite-02-running | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c04-rewrite-02-running-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c04-rewrite-02-running-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c04-rewrite-02-running.job.json) |
| c05-compare-02 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c05-compare-02-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c05-compare-02-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c05-compare-02.job.json) |
| c06-reverted-02 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c06-reverted-02-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c06-reverted-02-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c06-reverted-02.job.json) |
| c07-sample-01 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c07-sample-01-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c07-sample-01-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c07-sample-01.job.json) |
| c08-look-05-running | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c08-look-05-running.job.json) |
| c09-look-05-finished | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c09-look-05-finished-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c09-look-05-finished-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/c09-look-05-finished.job.json) |

## 本段校验与停止点

本段未改实现或测试，也未重跑全量 pytest／两份夹具门禁；交接 6 的 204 项与合同结果属于总控 rebase 验证，不能记作本段测试。C 段实际执行的是上述真实业务流程：5 个业务写请求成功、浏览器 pageerror=0、H-01 六镜不变性校验通过、H-02 退回哈希与独立样例复制校验通过；C-01 未通过，H-03 未完成。没有代签人工验收；既有 R220 的 studio.navigation／studio.shot-review PENDING 仍保留。

最终业务状态见 [git-status-final.txt](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/git-status-final.txt)：除开场已有 TASK.md 与 `.venv` 状态，只新增本报告。TASK.md 字节哈希与开场一致；`git diff --check` 通过。Harness SSOT 仓库已有其他未提交改动，本线程未写入其文件，见 [Harness 状态](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/harness-git-status-final.txt)。本报告属于普通运行交接证据，不创建 SSOT 开发包。

按要求停止，不修复 C-01、不继续 H-03、不提交、不推送。


## 第 2 轮

按 TASK.md「交接 7」完成 C2-1 和 C2-2。C-01 已修复，H-03 已在重新复制的真实状态中补跑到 pending 草稿；未点「采用」。本节替代前文 C-01 未修与 H-03 未完成的停止结论，前文证据原样保留。H-01／H-02 沿用上轮真跑与交接 7 的结论，本轮未改需求卡措辞。

### C2-1：看图进行状态优先

产品代码只改 `studio/static/direct-shot-detail.js`：inspector 先判断 `look.status==='running'`，直接显示「Opus 正在看这一镜的画面」，再处理选中的块和无块状态；移除后面已不可达的 running 分支。无块且正在看图时不再显示无块标题、重看按钮，也不出橙点。沿用现有 RV-INSPECT 结构、样式和已批准文案，没有改 CSS、其他产品文件或后端。

本轮共改 5 个文件：

| 文件 | 改动 |
| --- | --- |
| `studio/static/direct-shot-detail.js` | 上述优先级修复，共 2 行增加、1 行替换删除。 |
| `tests/fixtures/r277-revise/no-boxes-look-running.json` | 新增独立夹具，第 02 镜 `boxes=[]`、`look.status=running`；保留 baseVersion 字段；按 review 状态检查合同。 |
| `tests/test_r277_frontend.mjs` | 夹具清单增加至 17；断言新夹具组合；新增无块 running、有块 running、结束后恢复无块入口的状态切换检查；新增 `testLookRunningState` 检查进行文案、无重看按钮、无橙点。 |
| `scripts/direct_video/revision_frontend_gate.mjs` | 新状态加入 1440／960 矩阵，映射 review；捕获 look-running／no-boxes-look-running 前执行上述断言。原状态和断言保留。 |
| `docs/tasks/R277-shot-visual-revision/REPORT-C.md` | 仅追加本节，前文字节哈希不变。 |

先运行新增浏览器断言验证原问题，原实现退出 1，实际为「这一镜还没有可以点的块让 Opus 看一遍」，预期为进行文案；修复后同一探针退出 0。[修复前失败](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/regression-red.log) · [修复后通过](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/regression-green.log)。探针从 8768 加载真实模块、挂载新夹具，不是真跑模型证据；下面另有真实 Studio 验证。

新增夹具最终完整页：[1440](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/no-boxes-look-running-1440.png) · [960](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/no-boxes-look-running-960.png)。两张均亲自打开查看：画面是主角，进行文案清楚，空态标题和重看按钮均不在。原有 look-running 两宽也已重看，仍无橙点。

### C2-2：从 0 次补完真实 H-03

重新全量复制 `~/.photo-content-os/studio-r276/` 到独立临时目录，从本 worktree 起真实 Studio 8768。作品仍为「断更一年，我拆了四句话」，任务仍为 `dv_0e184e961bd14ac084c67411`。沿用前文 account3 本机 Claude、`claude_cli / claude-opus-5-5` 和两项 VIDEO_RENDER 环境变量，没有替换模型、API 或渲染结果。开始 GET revision-log 为主次不清 0 次、rulesRevision=0，副本不含前轮 H-01 的 2 次或样例。

1. 点第 05 镜「让 Opus 看一遍」。等待真实 POST 返回 `running`、`boxes=[]`，并等页面出现进行文案后才截取：[1440 详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01-look-05-running-detail.png) · [1440 完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01-look-05-running-full.png)。[接受响应](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/look-accepted.json) 与 [DOM 断言结果](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/running-state.json) 同时记录：文字准确、重看按钮为 0、无橙点。另补真实 390 视口检查：[手机详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01b-look-05-phone-detail.png) · [手机完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01b-look-05-phone-full.png)；实际 look 仍为 running，文字可读，没有溢出。
2. 看图完成后得到 19 个块，4 个有对应问题标记，另有 1 个整镜同步问题；原始结果保存在 [看图完成投影](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r02-look-05-done.job.json)。为验证「同类到 3 次」阈值，特意点三块，每块都选「缩小变灰」，没有补 own 文字。这是交接 7 授权的阈值验证步骤，不声称三次来自三次独立用户会话。
3. 三块分别是 `num`「66」、`nl2`「快 18 天，慢 254」、`c2`「只要不连着断两次」。页面出现编号 1／2／3，总字数 **76 / 200 字**；三条 action 均为 dim，归「主次不清」。[三块选中截图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r03-three-selected-detail.png) · [三项文字及编号](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/selected-three.json)。
4. 点「重写这一镜」。真实 revise 发 3 条 lines，等第 2 版渲染、看图与 verify 结束，再打开「画面问题记录」。真实草稿已起草完，页面与 API 都为 pending。[重写中](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r04-rewrite-05-running-detail.png) · [重写后与核对](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r05-compare-05-detail.png) · [记录及草稿整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r07-log-pending-full.png)。
5. 不点「采用」或「不用」。停止前再次 GET revision-log，rulesRevision 仍为 0；实际规则层 `rules=[]`，草稿未进入生效规则。完整接口时间线只有两项业务写操作：第 05 镜 look、revise，没有 adopt/reject。[开始前 GET](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/rules-before.json) · [草稿 pending GET](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/rules-after-pending.json) · [最终 GET](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/rules-final.json) · [H-03 机器证明](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/h03-proof.json)。

H-03 逐句对照：

| 预期 | 结果与依据 |
| --- | --- |
| 每种问题写着改过几次、出在哪几镜 | 成立：页面仅列 count>0 的「主次不清」，3 次；出处为本作品第 05 镜。API 的三个 sources 全是 05，没有 02。 |
| 同类到 3 次，写着「建议写进规则」并附草稿 | 成立：count=3，throughCount=3，proposal.status=pending；页面显示「建议写进规则」及草稿块。 |
| 没点采用之前规则不变 | 成立：开始、pending、停止时 rulesRevision 都为 0，规则数组为空，无 adopt 请求。标题中的「第 0 版 → 第 1 版」是待采用提案，不是已生效。 |

真实起草条文原文：

> 画面中的辅助数字、对比数据和补充说明文字（如次要统计数、对比天数、条件性提示语），字号比主角信息小一档，并统一改用灰色，不与主角争夺视觉焦点。

本次逐条核对原样保留（verify.status=done，不等于每条 result 都是 done）：

| index | 要求原文 | result | reason 原文 |
| --- | --- | --- | --- |
| 0 | 「66」缩小一档、改成灰色，不和主角抢。 | done | 空字符串 `""` |
| 1 | 「快 18 天，慢 254」缩小一档、改成灰色，不和主角抢。 | done | 空字符串 `""` |
| 2 | 「只要不连着断两次」缩小一档、改成灰色，不和主角抢。 | missed | 「只要不连着断两次」在画面中字号与上一行「断一次，不影响养成」相同，颜色仍接近白色，没有缩小，也没有变灰。 |

即 2 条 done、1 条 missed。页面确实显示了「没做到」及原因；没有重试模型来换取全 done，也没有把 H-03 阈值通过扩大成画面三条要求全部满足。[完整版本及 verify](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r05-compare-05.job.json)。

### 门禁与测试

| 检查 | 本轮结果 | 证据 |
| --- | --- | --- |
| 原问题负向复现／修复后同一浏览器断言 | 原实现按预期 FAIL；修复后 PASS | [red](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/regression-red.log) · [green](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/regression-green.log) |
| R277 门禁 | 功能 PASS，40/40 合同 PASS，46 张主捕获 | [运行日志](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/r277-gate.log) · [合同逐项结果](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/contracts.json) |
| R276 门禁 | 功能 PASS，26/26 合同 PASS，31 张机器回归捕获 | [运行日志](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/r276-gate.log) · [合同逐项结果](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r276/contracts.json) |
| 定向 pytest | 17 passed in 0.59s | [pytest.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/pytest.log) |
| runtime contract | PASS，含 safety／compileall／packages／encoding | [runtime.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/runtime.log) |
| Core UI 文案词法检查 | PASS，1 文件，0 warning；文案沿用批准内容 | [copy-quality.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/copy-quality.log) |
| git diff --check／JS 语法 | PASS | 最终检查退出 0 |

pytest 范围为 `tests/test_r277_frontend.py`、`tests/test_r276_direct_frontend.py`、`tests/test_p2_frontend_contract.py`、`tests/test_r220_number_formulas.py`、`tests/test_checklist_remediation_static.py`。未重跑全量 pytest 或后端测试，不把交接 6 的 204 项记成本轮结果。

R276 源门禁及测试本轮未改。与 B2 相同，因其端口硬编码为 8767，在仓库外生成执行副本，只将端口换成 8768，并适配 ROOT／测试 import 绝对路径；所有状态、断言、夹具、合同一致。[实际执行副本](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/r276-gate-8768.mjs)。

需求卡 JSON／Markdown、两份 approved-extras.json 均保持本轮开场 SHA-256；TASK.md 的总控改动原样保留。[保护文件哈希](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/protected-preservation.json)。没有修改后端，没有新增接口、文案申请或稿外元素。

### 真跑接口耗时与每步截图

接口时间线及逐步任务 JSON 位于 ~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/：[api-timeline.ndjson](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/api-timeline.ndjson)，包含实际 requestBody、HTTP 状态、返回毫秒、GET 轮询与阶段变化。两个写请求均为 HTTP 200，浏览器 pageerror=0。

| 操作 | 接口返回 | 总观察用时 |
| --- | --- | --- |
| 第 05 镜 look | 16ms | 95.763s |
| 第 05 镜 revise | 18ms | 132.59s |

look 总用时包括旧镜补渲染及真实看图；revise 总用时包括写代码、渲染、新画面看图和逐条核对。独立观察 Studio 子进程树，五次真实 Claude 进程依次约为：旧镜首次看图 23.715s、重写代码 38.496s、新画面看图 18.126s、逐条核对 10.633s、起草规则 7.286s。轮询约 1s、进程采样约 0.5s，均为墙钟观察值，没有加后端埋点或替换模型网关。[耗时汇总](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/timings.json) · [进程时间线](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/process-timeline.ndjson)。

| 步骤 | 完整页 | 详情 | 任务投影 |
| --- | --- | --- | --- |
| r00-initial-05 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r00-initial-05-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r00-initial-05-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r00-initial-05.job.json) |
| r01-look-05-running | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01-look-05-running-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01-look-05-running-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01-look-05-running.job.json) |
| r01b-look-05-phone | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01b-look-05-phone-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01b-look-05-phone-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r01b-look-05-phone.job.json) |
| r02-look-05-done | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r02-look-05-done-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r02-look-05-done-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r02-look-05-done.job.json) |
| r03-three-selected | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r03-three-selected-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r03-three-selected-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r03-three-selected.job.json) |
| r04-rewrite-05-running | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r04-rewrite-05-running-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r04-rewrite-05-running-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r04-rewrite-05-running.job.json) |
| r05-compare-05 | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r05-compare-05-full.png) | [详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r05-compare-05-detail.png) | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r05-compare-05.job.json) |
| r06-log-open | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r06-log-open-full.png) | — | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r06-log-open.job.json) |
| r07-log-pending | [完整页](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r07-log-pending-full.png) | — | [JSON](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/r07-log-pending.job.json) |

真实 16 张最终图均本轮逐张打开看过，完整页查看至底部，含 1440 桌面及 390 手机。记录页只有一行有数据，整页已覆盖草稿和样例空态。[真实截图清单](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/screenshot-manifest.json) 记录实际视口、路由、时间、覆盖范围、尺寸与 SHA-256。

R277 门禁另交付 48 张：46 张主捕获 + 390 记录表的 2 张补充横向分段。26 张新字节图本轮逐张打开；另 22 张逐文件 SHA-256 与此前本人已看过的 B2 图完全相同，复用原结论并在 manifest 中列出来源，没有把未查看过的新图标 PASS。[逐图清单](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/screenshot-manifest.json) · [22 张精确复用对应关系](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-exact-review-reuse.json) · [新图复核意见](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-fresh-review.json)。390 记录表的 [第 1 段](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/log-390.png)、[第 2 段](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/log-panel-part-2-390.png)、[第 3 段](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/log-panel-part-3-390.png) 重叠覆盖 0–620px 表宽，均含样例底部；这三张是夹具回归图，与真实 H-03 图分开。R276 的 31 张仅列为机器回归捕获，不冒充本轮逐张人工看图。

### 边界、清理与停止

真实副本、R277 门禁均核对原 `~/.photo-content-os/studio-r276/` 的 8599 文件哈希不变。[真实原件核验](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/source-preservation.json) · [门禁原件核验](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/gate-r277/source-preservation.json)。已保留实际第 05 镜两版代码／关键帧／review 及 pending 规则状态在 ~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/artifacts/；真实临时状态与浏览器 profile 已删，所有本线程 8768 服务已退出，8765／8766 未访问或操作。[真实环境清理](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/real/cleanup.json)。

业务 worktree 的本轮改动仅为上表 5 个文件，开场已有 TASK.md、`.venv` 与前轮 REPORT-C.md 均保留；[最终业务状态](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/business-git-status-final.txt)。Harness SSOT 仓库有原有其他工作区改动，本线程未修改 Harness 文件；[Harness 状态](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c2/harness-git-status-final.txt)。本节是本地机器验证证据，不代签人工验收、不宣告生产发布，也不创建 SSOT 开发包。

按要求在此停止，不提交、不推送。


## 第 3 轮

本轮只做交接 8 的 C3-1。按指定候选顺序实现完成，两份合同门禁与徽标矩形断言通过；本人看图后发现**相邻文字遮挡仍存在，不能报整体视觉通过**。保留交接规定的顺序、2px 间距、20px 徽标，不自行改坐标、缩字号或改变候选规则；问题见下文。未调用模型，未提交、未推送，未代签人工验收。

### C3-1 实现与边界

本轮相对开工快照只改以下四个实现／测试文件，并在本报告末尾追加本节：

| 文件 | 本轮改动 |
|---|---|
| `studio/static/direct-shot-detail.js` | 根据真实画面和块的 `getBoundingClientRect()` 放徽标。编号按左→上→下→右、橙点按右→上→下→左，取第一个整个在画面内的位置；外侧间距 2px。扣除热区边框以保证定位准确。四处均放不下时保留原角上位置；同块先放编号，另一枚须避开已放的徽标。用 ResizeObserver 在画面宽度改变后重算，重绘／切任务断开旧观察器。 |
| `studio/static/direct-shot-detail.css` | 热区允许徽标溢出；徽标不单独截获指针。沿用原有颜色、字号、20px 尺寸和角上回退样式。 |
| `tests/test_r277_frontend.mjs` | 增加逐枚徽标的所属块不相交、画面内、同块双徽标不相交断言；增加八个有序方向、2px 间距、四边均不够的角上回退、双徽标及 300px resize 共 10 个用例。边界数据在测试内构造，没有新改 JSON 夹具。 |
| `scripts/direct_video/revision_frontend_gate.mjs` | 每次截图都测徽标；review／picked／compare／kept-prev 及真实有块重放要求徽标非空，避免空断言。重放 C/C2 已留存真实投影和原关键帧，补 02／05 看图后、05 已选三块、05 对比的整页和详情图，1440／960，并对已选和对比加 390。保存原输入哈希与重放无业务写入证明。 |

当前页面本来用编号替换已选块的橙点，此规则没有改；同块双徽标通过测试内临时加入第二枚再 resize 验证。角上回退本身可能与块相交，这是交接明确保留的例外，独立边界用例验证了这一点；本轮夹具和真实截图中的 146 个测量没有使用该例外来跳过断言。

没有改 R276 测试或门禁。R276 为遵守端口限制，执行仓库外副本，唯一替换为 ROOT／测试 import 的绝对路径及端口 8767→8768，业务断言不变。

### 测试与合同结果

| 检查 | 本轮结果 | 证据 |
|---|---|---|
| 红／绿回归 | 改前真实 05 断言失败 `pin/refT covers its block`；改后通过 | [red](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/regression-red.log) / [green](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/regression-green.log) |
| R277 门禁 | PASS，原交互／公式检查保留；40/40 合同，0 浏览器异常；66 次截图时检查，146 枚徽标测量，10 个边界用例 | [gate log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/r277-gate.log) / [manifest](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/screenshot-manifest.json) |
| R276 门禁 | PASS，26/26 合同，31 张完整页截图；split、Unicode、时长、计数、轮询、失败与选择等原断言通过 | [gate log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/r276-gate.log) / [manifest](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r276/screenshot-manifest.json) |
| 定向 pytest | 17 passed in 0.54s | [pytest.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/pytest.log) |
| runtime contract | PASS，含 safety／compileall／packages／encoding | [runtime.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/runtime.log) |
| Core 文案词法检查 | PASS，0 error／0 warning；未加产品文案 | [copy-quality.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/copy-quality.log) |
| 语法与补丁 | 三份 JS/MJS `node --check`、`git diff --check` 通过 | 本轮终端记录 |

pytest 范围：`tests/test_r277_frontend.py`、`tests/test_r276_direct_frontend.py`、`tests/test_p2_frontend_contract.py`、`tests/test_r220_number_formulas.py`、`tests/test_checklist_remediation_static.py`。未重跑全量和后端测试。两份门禁仍用原合同及原批准文件，没有扩大批准范围、降低现有断言或重写基线。

### 截图、逐张看图与残留问题

最终 R277 图片目录：[gate-r277](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/)。共 68 张（66 张门禁输出，加手机记录页横向滚动第 2／3 部分）；本人本轮逐张打开看过，包括与 C2 哈希相同的 8 张，未仅靠旧结论复用。逐图结论和哈希在 [review-notes.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/review-notes.json) 与上述 manifest。

真实数据来自任务 `dv_0e184e961bd14ac084c67411` 的 C/C2 留存投影与原 poster；重放在当前代码的真实 Studio 页面，GET 投影／poster 由已保存数据响应，没有新模型调用、没有业务写请求。它证明当前前端如何显示真实数据，不能算新一轮真 Opus 运行。旧任务无块原始首屏也保留；有块后的 02／05 重放用于本轮非空徽标断言。真实重放沿用真实外层状态，不强套夹具外层文案合同（与原 real-worst 一致），40 次夹具合同不减。

实际 viewport 为 1440×900、960×900、390×900。完整页覆盖至 document 底部；`*-detail-*`／`real-worst-first-screen-*` 是滚到详情起点后的 900px 视窗补图，不能当整页。每张的路由、捕获时间、scroll coverage、输出尺寸、SHA-256 都在 manifest。手机记录页三部分覆盖实际 620px 横向内容：0–300、160–460、320–620，有重叠且到末列；本人看过末列草稿和页底样例。

**矩形要求成立的范围**：真实大图的“66”“快”“只”及橙点对应的“接近自动”完整露出；review／picked／kept-prev 夹具的所属块也不再被徽标压住。1440 详情双栏及 960 对比标题在图片上方的顺序保持。

**视觉残留 C3-V01（未解决）**：真实 05 对比图宽 300px，“66”和“只要不连着断两次”的块左边只有约 20px，容不下 20px 徽标加 2px 间距，按交接顺序取“上方”。1 号于是盖到上一行来源“Lally 等，2010”的部分字，3 号盖到上一行“断一次，不影响养成”。1440、960 都能看见；390 已选／对比更挤，也有相邻块遮挡。所属块不相交及画面内的断言全部成立，但这不足以证明整张图无遮挡。

典型截图：[真实对比1440详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-detail-1440.png)、[真实对比960详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-detail-960.png)、[真实已选390详情](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-detail-390.png)。相邻块测量另存 [adjacent-overlap-observations.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/adjacent-overlap-observations.json)：1440／960 的 num→src 相交约151.258px²，c2→c1 约244.442px²。

**视觉残留 C3-V02（未解决）**：夹具 compare／verify-* 新图的 1 号在所属块左边，但仍盖到海报上更靠左的“约”字；3 号也靠在标题上。这是所属块坐标未覆盖海报中文字的情形，不能用矩形门禁宣布字完整。没有改夹具坐标或海报来使图通过。

C3-V01 若要继续处理，需确定是否允许跳过会覆盖其他块的候选位置；这会增加交接 8 未写的候选条件。C3-V02 还涉及块坐标与关键帧文字的一致性。本轮保留原要求并如实停在此处，不把问题转成通过。已异步提出这一候选规则问题，写报告时尚无新答复。需要接口：无；新文案：无；新增稿外可见元素：无。

逐张截图链接如下；“有问题”表示上述整图文字遮挡，并非合同或所属块矩形断言失败。

| 图片 | 实际 viewport | 覆盖 | 本人看图 |
|---|---|---|---|
| [real-worst-complete-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-complete-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [real-worst-first-screen-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-first-screen-1440.png) | 1440×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-worst-complete-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-complete-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [real-worst-first-screen-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-first-screen-960.png) | 960×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-worst-complete-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-complete-390.png) | 390×900 | 完整页 | 已看，未见本轮问题 |
| [real-worst-first-screen-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-worst-first-screen-390.png) | 390×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-review-02-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-02-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-review-02-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-02-detail-1440.png) | 1440×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-review-02-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-02-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-review-02-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-02-detail-960.png) | 960×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-review-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-05-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-review-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-05-detail-1440.png) | 1440×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-review-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-05-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-review-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-review-05-detail-960.png) | 960×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-picked-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-picked-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-detail-1440.png) | 1440×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-picked-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [real-boxes-picked-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-detail-960.png) | 960×900 | 详情视窗 | 已看，未见本轮问题 |
| [real-boxes-picked-05-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-390.png) | 390×900 | 完整页 | 有问题 |
| [real-boxes-picked-05-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-picked-05-detail-390.png) | 390×900 | 详情视窗 | 有问题 |
| [real-boxes-compare-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-1440.png) | 1440×900 | 完整页 | 有问题 |
| [real-boxes-compare-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-detail-1440.png) | 1440×900 | 详情视窗 | 有问题 |
| [real-boxes-compare-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-960.png) | 960×900 | 完整页 | 有问题 |
| [real-boxes-compare-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-detail-960.png) | 960×900 | 详情视窗 | 有问题 |
| [real-boxes-compare-05-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-390.png) | 390×900 | 完整页 | 有问题 |
| [real-boxes-compare-05-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-boxes-compare-05-detail-390.png) | 390×900 | 详情视窗 | 有问题 |
| [review-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [review-expanded-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-expanded-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [review-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [review-expanded-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-expanded-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [select-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/select-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [select-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/select-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [picked-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/picked-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [picked-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/picked-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [rewriting2-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/rewriting2-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [rewriting2-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/rewriting2-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [compare-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/compare-1440.png) | 1440×900 | 完整页 | 有问题 |
| [compare-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/compare-960.png) | 960×900 | 完整页 | 有问题 |
| [kept-prev-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/kept-prev-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [kept-prev-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/kept-prev-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [saved-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/saved-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [saved-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/saved-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [review-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-failed-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [review-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-failed-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [log-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [log-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [look-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/look-running-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [look-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/look-running-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [no-boxes-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/no-boxes-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [no-boxes-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/no-boxes-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [no-boxes-look-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/no-boxes-look-running-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [no-boxes-look-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/no-boxes-look-running-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [verify-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-running-1440.png) | 1440×900 | 完整页 | 有问题 |
| [verify-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-running-960.png) | 960×900 | 完整页 | 有问题 |
| [verify-missed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-missed-1440.png) | 1440×900 | 完整页 | 有问题 |
| [verify-missed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-missed-960.png) | 960×900 | 完整页 | 有问题 |
| [verify-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-failed-1440.png) | 1440×900 | 完整页 | 有问题 |
| [verify-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/verify-failed-960.png) | 960×900 | 完整页 | 有问题 |
| [log-empty-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-empty-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [log-empty-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-empty-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [proposal-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/proposal-running-1440.png) | 1440×900 | 完整页 | 已看，未见本轮问题 |
| [proposal-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/proposal-running-960.png) | 960×900 | 完整页 | 已看，未见本轮问题 |
| [review-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/review-390.png) | 390×900 | 完整页 | 已看，未见本轮问题 |
| [compare-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/compare-390.png) | 390×900 | 完整页 | 有问题 |
| [no-boxes-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/no-boxes-390.png) | 390×900 | 完整页 | 已看，未见本轮问题 |
| [log-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-390.png) | 390×900 | 完整页／横向第1部分 | 已看，未见本轮问题 |
| [log-panel-part-2-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-panel-part-2-390.png) | 390×900 | 完整页／横向第2部分 | 已看，未见本轮问题 |
| [log-panel-part-3-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/log-panel-part-3-390.png) | 390×900 | 完整页／横向第3部分 | 已看，未见本轮问题 |

### 保全与工作区

`~/.photo-content-os/studio-r276/` 原件 8599 文件前后哈希相同：[source-preservation.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/source-preservation.json)；C/C2 真实输入与关键帧前后哈希相同，业务写请求为空：[real-marker-replay.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/gate-r277/real-marker-replay.json)。

相对本轮开工快照，TASK、两份 approved-extras、需求卡 JSON/MD、C2 no-boxes-look-running 夹具均未变，见 [boundary-check.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c3/boundary-check.json)。报告原有前 41036 字节 SHA-256 `c031cb47b3cbef5e5ff99b2ddf0c78cb11bd743324a715c5919871ea7c53cf37` 保持，仅末尾追加。

业务仓库 HEAD 仍为 `ae80df4`。开工已有的 TASK 修改、C2 JS／门禁／测试、未跟踪 REPORT-C／C2 夹具／.venv 均保留；本轮新增差异仅上列四文件及报告追加。Harness SSOT 仍有既有未提交／未跟踪改动，本轮没有写入。普通报告与仓库外截图不属于声明的 SSOT bundle。8768 已关闭；未访问或干预 8765、8766，未杀其他进程。机器检查绿色不等于人工验收通过，既有 R220 PENDING 未改。本轮到此停止。


## 第 4 轮

本轮按交接 9 完成 C4-1～C4-3。R277 合同 42/42、R276 合同 26/26、定向 pytest 17 项通过。74 张最终 R277 截图本人逐张看过，C3 的 Lally／“断一次”及夹具“约”字遮挡已消除。最小相交面积例外全部单列，**390 真实对比的 1 号仍与 `unit`（“天”）块相交约 28.807px²**，交总控按交接逐枚判断，不宣称整图零遮挡。没有调用模型，没有提交或推送。

### C4-1：避让所有块和已放徽标

`studio/static/direct-shot-detail.js` 的定位现按画面内的全部块计算，包括无徽标的块和包住整图／图表的容器；对比只读图也保留全部不可点击透明块供测量。编号左→上→下→右，橙点右→上→下→左，2px 间距不变。

每枚先排除出画面、压自己或压已经放下的任何徽标的位置，再取第一个与其他块也不相交的位置。没有完全无交点的位置时，按其他块相交面积之和选最小值，同分沿用候选顺序；仍不压自己或前面的徽标。连这样可用的候选也没有才使用角上回退。原有 ResizeObserver 在切镜、重绘及尺寸变化时重新计算。

门禁独立重算候选及相交面积，验证所属块不相交、画面内、全画面徽标互不相交、顺序、2px 间距；发生其他块相交时必须证明四候选没有清晰位置且当前是最小面积，并写入清单。没有按 `cv`、`3` 或其他块名排除祖先容器。真实／夹具的截图中没有角上回退；独立满画面边界用例仍覆盖该明确例外。

### C4-2：尺寸随实际画面宽度变化

`studio/static/direct-shot-detail.js` / `.css`：实际画面宽度 ≤300px 时徽标 16×16px、字号 9.2px；大画面 360px 时 20×20px、字号 11.5px。读取实际画面宽度，不按窗口宽度猜测；同一个 960 viewport 的 360px 大图仍是 20px，300px 对比图是 16px。列表编号、说明里的行内橙点沿用其现有样式。门禁测尺寸与字号；300px resize 用例同时证明两枚同块徽标不重叠。

### C4-3：用镜头真实元素替换手写夹具坐标

门禁在 1080×1920、30fps、`floor(0.8 * D * 30)` 帧调用镜头 `seekFrame`，等待字体完成后取位置；R277 测试辅助函数直接执行 `scripts/video_render/render-frames.mjs` 的可见 `[id],[data-s]` 收集函数，包括其名称规则。没有修改 renderer、设计稿或后端。每次门禁重新测量并与有块夹具的完整 `boxes`（id、name、x、y、w、h）严格相等；有漂移就报出具体夹具和镜号，不能靠保留手填框通过。

测量来源、renderer SHA-256 和 16 份非空 shot 几何对照见 [fixture-geometry.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/fixture-geometry.json)；逐份前后坐标及名称见 [fixture-changes.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/fixture-changes.json)，初始测量见 [measured-boxes.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/measured-boxes.json)。原第 02 镜 D=19s，取第 456 帧；新图删除了小字，其元素在 collector 中自然消失。

对应关系：

| 原手写 id／名称 | 真实元素 id／名称 | 处理 |
|---|---|---|
| `big`／「约 50%」柱子 | `b1`／「约 50%」柱子 | 请求行 boxId 改为 b1，坐标量实际柱形矩形；标签 v1 作为独立块参与避让。 |
| `small`／「约 25%」柱子 | `b2`／「约 25%」柱子 | findings 与请求行 boxId 改为 b2；名称保持测量结果；标签 v2 独立参与避让。 |
| `sub`／标题下的小字 | `2`／「断了这么久，大家肯定都注」 | 名称沿用后端截取前 12 字的规则，findings 与历史请求 boxId 对应到 2。新图 display:none，因此新 boxes 没有 2，图上不画“已删除文字”的 3 号；右边历史修改要求仍保留。 |
| `ref`／100% 刻度那一块 | `3`／「经典实验：穿件尴尬的衣服」 | 原刻度自身没有 id/data-s，实际可取的对应范围是包含它的图表容器 3；findings.boxId 改为 3，没有伪造刻度 id 或手写坐标。 |
| saved 第 01 镜 `title`／标题 | renderer 收集的 9 个真实块 | 去掉手写标题框，替换为真实 ul、data-s 卡片等完整结果；该镜没有 findings 需映射。 |

第 02 镜原图收集 9 块（2、3、b1、b2、v1、v2、l1、l2、8），新图 8 块（少了 2）。所有空 boxes 状态保持空；没有向旧真实任务或原始状态目录写入坐标。

修改的 15 份 R277 JSON 夹具：`review`、`select`、`picked`、`rewriting2`、`compare`、`kept-prev`、`saved`、`review-failed`、`log`、`look-running`、`verify-running`、`verify-missed`、`verify-failed`、`log-empty`、`proposal-running`。`saved` 同时更新 01 和 02，合计 16 个 shot 几何。`no-boxes`、`no-boxes-look-running` 没改。除了 boxes 的真实 id／名称／坐标及对应 boxId，业务状态、时间、baseVersion、核对 done/missed、规则版本、既有请求文字均未改。

实时点选“删除”改用后端生成的块名，现场三条要求加补充从 85 字变成 **93 字**（17 字删除句替代 9 字旧句，多 8 字）；门禁仍严格核对 93 / 200。compare 夹具保存的是原有 85 字历史请求，仍严格核对 85 字，不把历史文字改成新点选结果。DOM 坐标测试同步改为实测的 b2 x=590、w=280；该用例自身轮询使 y 从 987 加到 988，仍按 1080→360 的三分之一比例严格核对。

### 测试、门禁及改动文件

实现只改 `studio/static/direct-shot-detail.js`、`studio/static/direct-shot-detail.css`；除上述 15 份夹具，再改 `tests/test_r277_frontend.mjs`、`scripts/direct_video/revision_frontend_gate.mjs`，以及本报告追加。R276 的测试、门禁文件均未改。R276 使用仓库外已有执行副本，只把 ROOT／import 定位至本 worktree、8767 改成 8768，其原有断言照跑。

| 检查 | 结果 | 本轮证据 |
|---|---|---|
| R277 门禁 | PASS；42/42 合同、72 张门禁截图，158 枚徽标测量；14 个边界／避让记录（含反例拒绝）；原有行为测试保留 | [log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/r277-gate.log) / [manifest](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/screenshot-manifest.json) |
| R276 门禁 | PASS；26/26 合同、31 张完整页；原交互、公式、时长等检查通过 | [log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/r276-gate.log) / [manifest](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r276/screenshot-manifest.json) |
| 定向 pytest | 17 passed in 0.72s | [pytest.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/pytest.log) |
| runtime contract | PASS | [runtime.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/runtime.log) |
| Core UI 文案词法检查 | PASS，1 文件，0 warning | [copy-quality.log](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/copy-quality.log) |
| JS/MJS 语法及补丁 | 三份 node --check、git diff --check 通过 | 本轮终端记录 |

pytest 范围仍是 `tests/test_r277_frontend.py`、`tests/test_r276_direct_frontend.py`、`tests/test_p2_frontend_contract.py`、`tests/test_r220_number_formulas.py`、`tests/test_checklist_remediation_static.py`；未跑全量／后端测试。没有改两份合同或 approved-extras。

新增验证覆盖：①有其他块挡在首选左侧时转到上方；②整个画面容器包住目标、四处都相交时选择面积最小；③不同块的徽标碰撞时避开已经放下的徽标；④把已通过的徽标强制移回被其他块挡住的位置，新门禁必须拒绝。另保留八方向、2px 间距、角上回退、同块两徽标与 resize 用例。夹具实测相等检查也实际拦住了 saved/01 的手写框，修完数据后通过。

### 逐枚最小相交例外（交总控看图判断）

完整清单 [marker-overlap-exceptions.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/marker-overlap-exceptions.json) 含 110 次测量（整页与配套详情重复计入），按状态／viewport／块去重为 74 枚。以下没有省略任何一枚；面积单位是当前屏幕 CSS px²，多个块的面积按和计算。`cv` 是真实 05 的整体容器，`3` 是夹具图表容器，它们也严格算作“其他块”。

唯一同时碰到非容器文字块的例外：`real-boxes-compare-05` / 390 / `num`，总面积 284.807 = cv 256 + unit 28.807。实际画面只有约 132px 宽，16px 编号在四候选里该位置相交最少；没有缩成更小或增加第五个位置。本轮保留并明确标 ISSUE，请总控逐图判断，不能把机器条件通过当成这一枚的人工认可。

| 状态／viewport | 块 id（徽标） | 位置 | 面积 | 相交块及面积 | 截图 |
|---|---|---|---|---|---|
| real-boxes-review-05 / 1440 | refT（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-1440.png) |
| real-boxes-review-05 / 1440 | nl2（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-1440.png) |
| real-boxes-review-05 / 1440 | c1（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-1440.png) |
| real-boxes-review-05 / 1440 | c2（pin） | bottom | 120.000 | cv: 120.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-1440.png) |
| real-boxes-review-05 / 960 | refT（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-960.png) |
| real-boxes-review-05 / 960 | nl2（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-960.png) |
| real-boxes-review-05 / 960 | c1（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-960.png) |
| real-boxes-review-05 / 960 | c2（pin） | bottom | 120.000 | cv: 120.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-960.png) |
| real-boxes-review-05 / 390 | refT（pin） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-390.png) |
| real-boxes-review-05 / 390 | nl2（pin） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-390.png) |
| real-boxes-review-05 / 390 | c1（pin） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-390.png) |
| real-boxes-review-05 / 390 | c2（pin） | bottom | 65.500 | cv: 65.500 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-390.png) |
| real-boxes-picked-05 / 1440 | refT（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) |
| real-boxes-picked-05 / 1440 | num（number） | left | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) |
| real-boxes-picked-05 / 1440 | nl2（number） | left | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) |
| real-boxes-picked-05 / 1440 | c1（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) |
| real-boxes-picked-05 / 1440 | c2（number） | bottom | 120.000 | cv: 120.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) |
| real-boxes-picked-05 / 960 | refT（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) |
| real-boxes-picked-05 / 960 | num（number） | left | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) |
| real-boxes-picked-05 / 960 | nl2（number） | left | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) |
| real-boxes-picked-05 / 960 | c1（pin） | right | 400.000 | cv: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) |
| real-boxes-picked-05 / 960 | c2（number） | bottom | 120.000 | cv: 120.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) |
| real-boxes-picked-05 / 390 | refT（pin） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) |
| real-boxes-picked-05 / 390 | num（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) |
| real-boxes-picked-05 / 390 | nl2（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) |
| real-boxes-picked-05 / 390 | c1（pin） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) |
| real-boxes-picked-05 / 390 | c2（number） | bottom | 65.500 | cv: 65.500 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) |
| real-boxes-compare-05 / 1440 | num（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-1440.png) |
| real-boxes-compare-05 / 1440 | nl2（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-1440.png) |
| real-boxes-compare-05 / 1440 | c2（number） | bottom | 199.250 | cv: 199.250 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-1440.png) |
| real-boxes-compare-05 / 960 | num（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-960.png) |
| real-boxes-compare-05 / 960 | nl2（number） | left | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-960.png) |
| real-boxes-compare-05 / 960 | c2（number） | bottom | 199.250 | cv: 199.250 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-960.png) |
| real-boxes-compare-05 / 390 | num（number） | right | 284.807 | cv: 256.000, unit: 28.807 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-390.png) |
| real-boxes-compare-05 / 390 | nl2（number） | right | 256.000 | cv: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-390.png) |
| real-boxes-compare-05 / 390 | c2（number） | bottom | 69.750 | cv: 69.750 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-390.png) |
| review / 1440 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-1440.png) |
| review-expanded / 1440 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-expanded-1440.png) |
| review / 960 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-960.png) |
| review-expanded / 960 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-expanded-960.png) |
| select / 1440 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/select-1440.png) |
| select / 960 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/select-960.png) |
| picked / 1440 | b1（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-1440.png) |
| picked / 1440 | b2（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-1440.png) |
| picked / 960 | b1（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-960.png) |
| picked / 960 | b2（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-960.png) |
| rewriting2 / 1440 | b1（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-1440.png) |
| rewriting2 / 1440 | b2（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-1440.png) |
| rewriting2 / 960 | b1（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-960.png) |
| rewriting2 / 960 | b2（number） | left | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-960.png) |
| compare / 1440 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-1440.png) |
| compare / 1440 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-1440.png) |
| compare / 960 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-960.png) |
| compare / 960 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-960.png) |
| kept-prev / 1440 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-1440.png) |
| kept-prev / 960 | b2（pin） | right | 400.000 | 3: 400.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-960.png) |
| verify-running / 1440 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-1440.png) |
| verify-running / 1440 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-1440.png) |
| verify-running / 960 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-960.png) |
| verify-running / 960 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-960.png) |
| verify-missed / 1440 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-1440.png) |
| verify-missed / 1440 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-1440.png) |
| verify-missed / 960 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-960.png) |
| verify-missed / 960 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-960.png) |
| verify-failed / 1440 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-1440.png) |
| verify-failed / 1440 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-1440.png) |
| verify-failed / 960 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-960.png) |
| verify-failed / 960 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-960.png) |
| review / 390 | b2（pin） | right | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-390.png) |
| picked / 390 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-390.png) |
| picked / 390 | b2（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-390.png) |
| compare / 390 | b1（number） | left | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-390.png) |
| compare / 390 | b2（number） | right | 237.750 | 3: 237.750 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-390.png) |
| kept-prev / 390 | b2（pin） | right | 256.000 | 3: 256.000 | [看图](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-390.png) |

### 最终截图与本人看图结论

目录：[gate-r277](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/)。72 张门禁输出加手机记录页横向第 2／3 部分，共 **74 张**，本人本轮逐张打开看过；每张 SHA-256、route、viewport、capture time、scroll coverage、输出尺寸及结论见 [manifest](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/screenshot-manifest.json) / [review-notes.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/review-notes.json)。

真实重放使用 C/C2 原投影与原 poster，在当前 Studio 页面显示，没有重新跑 Opus或重写镜头。真实 02／05 看图后、05 选三块、05 对比均截 1440×900／960×900／390×900 的整页与详情；review／picked／compare／kept-prev 夹具也覆盖三宽。完整页走至文档底部，详情补图只覆盖当前 900px，不冒充整页。手机记录页横向三部分为 0–300、160–460、320–620，末列及页底样例已看。

本人结论：C3-V01 的来源 Lally 与“断一次”现在露出，原主数字 66、快、只、接近自动保持可读。C3-V02 的“约”字及标题上方假 3 号问题随真实 boxes 修正消除。1440 双栏、960 对比标题在两图上方、390 纵向顺序及展开内容完整；图表容器导致的最小相交已逐枚列出。390 真实对比的 unit 例外保留为 ISSUE，等待总控作视觉判断。未代签人工验收。

| 图片 | viewport | 覆盖 | 本人结论 |
|---|---|---|---|
| [real-worst-complete-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-complete-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-worst-first-screen-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-first-screen-1440.png) | 1440×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-worst-complete-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-complete-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-worst-first-screen-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-first-screen-960.png) | 960×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-worst-complete-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-complete-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-worst-first-screen-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-worst-first-screen-390.png) | 390×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-detail-1440.png) | 1440×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-detail-960.png) | 960×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-02-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-02-detail-390.png) | 390×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-1440.png) | 1440×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-960.png) | 960×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-review-05-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-review-05-detail-390.png) | 390×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-1440.png) | 1440×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-960.png) | 960×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-picked-05-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-picked-05-detail-390.png) | 390×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-compare-05-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-compare-05-detail-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-1440.png) | 1440×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-compare-05-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [real-boxes-compare-05-detail-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-960.png) | 960×900 | 详情视窗 | 已看；最小相交例外见上表 |
| [real-boxes-compare-05-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-390.png) | 390×900 | 完整页 | unit 最小相交，待总控判断 |
| [real-boxes-compare-05-detail-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-boxes-compare-05-detail-390.png) | 390×900 | 详情视窗 | unit 最小相交，待总控判断 |
| [review-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-expanded-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-expanded-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-expanded-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-expanded-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [select-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/select-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [select-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/select-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [picked-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [picked-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [rewriting2-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [rewriting2-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/rewriting2-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [compare-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [compare-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [kept-prev-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [kept-prev-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [saved-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/saved-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [saved-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/saved-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-failed-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-failed-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [log-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [log-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [look-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/look-running-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [look-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/look-running-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [no-boxes-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/no-boxes-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [no-boxes-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/no-boxes-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [no-boxes-look-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/no-boxes-look-running-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [no-boxes-look-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/no-boxes-look-running-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-running-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-missed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-missed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-missed-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [verify-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/verify-failed-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [log-empty-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-empty-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [log-empty-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-empty-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [proposal-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/proposal-running-1440.png) | 1440×900 | 完整页 | 已看；最小相交例外见上表 |
| [proposal-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/proposal-running-960.png) | 960×900 | 完整页 | 已看；最小相交例外见上表 |
| [review-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/review-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [picked-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/picked-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [compare-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/compare-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [kept-prev-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/kept-prev-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [no-boxes-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/no-boxes-390.png) | 390×900 | 完整页 | 已看；最小相交例外见上表 |
| [log-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-390.png) | 390×900 | 完整页／横向第1部分 | 已看；最小相交例外见上表 |
| [log-panel-part-2-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-panel-part-2-390.png) | 390×900 | 完整页／横向第2部分 | 已看；最小相交例外见上表 |
| [log-panel-part-3-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/log-panel-part-3-390.png) | 390×900 | 完整页／横向第3部分 | 已看；最小相交例外见上表 |

### 保全、接口与工作区

原始 `~/.photo-content-os/studio-r276/` 8599 文件前后哈希一致，[source-preservation.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/source-preservation.json)；真实重放输入未变、没有业务写请求，[real-marker-replay.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/gate-r277/real-marker-replay.json)。需求卡、TASK、两份 approved-extras、后端、R276 文件均与本轮开工哈希一致，[boundary-check.json](~/.photo-content-os/evidence/R277-shot-visual-revision/real-c4/boundary-check.json)。

报告原前 63820 字节 SHA-256 `fadd7763e3066929e2c9b5f525050f572eb1f5cfca93fc5f0dc735cf618d2f1f` 不变，仅追加本节。业务 HEAD 仍 `ae80df4`，工作区保留本轮及既有未提交差异；Harness SSOT 有既有未提交／未跟踪差异，本轮未写入。没有新接口、新固定文案或稿外可见元素；生成的块名来自规定 collector。既有 R220 PENDING 不变。8768 已关闭，未访问／干预 8765、8766，未杀其他进程。普通报告及截图不属于声明的 SSOT bundle。本轮到此停止，不提交、不推送。
