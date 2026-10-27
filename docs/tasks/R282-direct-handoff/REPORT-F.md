# R282 前端 F 段汇报

2026-10-27。只执行任务单第 0、1 节和 F 段；未提交、未推送。前端实现和本地夹具机器检查通过，真实中台交接及成片生成没有在本段验收。**交接时间仍有 B 段接口缺口，见末节；不能据本报告宣称整张 R282 已完成或 READY。**

## 改动范围

- `studio/static/direct-view.js`：首次进入读取 `GET …/direct/handoff`，没有任务且没有本机编辑内容时，预填交接分镜；显示来源横条和带入配音卡。建任务带 `handoff: {jobId, revision}`。进入改分镜时重新读取当前任务和交接，使用 B 的 `handoffNewer`；点击「换成中台这版」才替换整表、图片和配音，未点击继续用当前任务分镜。
- `studio/static/direct-storyboard.js`：映射四种图片来源标签与版权待确认警示；没有本机图片时保留空图占位。交接起止时间同时用于镜头列、合计、步骤条与放大图；改画面等字段保留交接计时，改台词、拆镜、并镜或多行粘贴后改按每秒 5.1 字估时。六列文字按交接投影原样显示。
- `studio/static/direct-rescript.css`：仅给生成条操作区加 `flex:none`，防止手机上「生成」被挤成两行。来源横条、标签和版权警示直接复用已有令牌和样式。没有新增颜色、内联 `style=` 或替换控件。
- `scripts/direct_video/rescript_frontend_gate.mjs`：增加两个 R282 状态、交接接口/图片夹具和交互测试，两个状态六个分块全部收集到真实页面；不再排除它们的批准合同检查。保留 R278/R283 所有既有交互与合同断言。
- 新增 `tests/test_r282_frontend.mjs`、`tests/test_r282_frontend.py`、`tests/fixtures/r282-direct/{first-handoff,rescript-newer}.json`。
- `direct-style.js` 无需改动。未修改 B 段的 Python、OpenAPI、后端测试，也未写中台仓库、设计稿、验收卡或现有本机状态目录。

## 先红后绿与最终检查

证据根目录：`~/.photo-content-os/evidence/R282-direct-handoff/frontend/`。测试保护交接的可见内容、计时、显式换版、来源身份和手机按钮；复用原浏览器门禁，未另起浏览器运行框架。

| 检查 | 结果 / 日志 |
| --- | --- |
| 现有产品代码上的新增 Node 测试 | 预期失败，缺少交接来源映射；`red-node.log` |
| 现有门禁上的新增 pytest | 预期失败，未收集 R282 状态；`red-pytest.log` |
| 现有产品代码上的挂载页面断言 | 预期失败，实际 0 行，要求交接七镜；`red-browser.log` |
| null 时间回归 | 修改前显示 1 月 1 日，断言失败；修复为缺失时间不显示虚构日期；`null-time-red.log` |
| 390 手机生成按钮 | 修改前 Range 检出两行，要求一行，断言失败；`phone-button-red.log` |
| `node tests/test_r282_frontend.mjs` | PASS；`node-r282.log` |
| `node tests/test_r278_direct_rescript.mjs` | PASS；`node-r278.log` |
| `node tests/test_r283_frontend.mjs` | PASS；`node-r283.log` |
| 五份前端 pytest：R282 / R278 / R283 / R276 / R277 | **16 passed**；`frontend-pytest.log` |
| `rescript_frontend_gate.mjs --checks-only` | **48 次 / 240 块合同 PASS**，含挂载交互；`checks.log`、`checks-contracts.json` |
| 最终截图合同 | **6 次 / 36 块 PASS**；`captures.log`、`contracts.json` |
| `check_repository_safety.py --base HEAD` | PASS；`repository-safety.log` |
| `git diff --check` | PASS |

挂载页面还验证了：五个文字字段逐字一致；七张交接图片；四类来源标签及警示色；静图放大和交接时间；仅改画面不改计时；改台词切换估时；显式换版后全部列和图替换；不换版不发送 handoff；缺图、无配音、时间为 null；「换一个配音…」文件选择与生成后上传至新任务。上传音频、建任务、样张及生成结果均使用接口替身，没有真调模型或进行真实声音/成片验证。

全部浏览器门禁串行，只开一个自有无头 Chromium，端口 8768，临时状态和素材目录位于系统临时目录。固定测试日期没有冻结动画计时器。没有运行全量 pytest。磁盘始终高于 3 GiB，收尾约 4.2 GiB。浏览器、临时服务与临时状态已清理，8768 无监听；未停止或重启其他端口的现有 Studio。

## 最终截图逐张审看

最后一次视觉修改之后重新加载应用，重拍并分别用 `view_image` 打开以下六张最终完整页面。手机先用 high 看全页，再对目标区域及最终手机文件做原尺寸复看。截图覆盖页顶至生成条，捕获期间遍历了文档滚动范围，PNG 高度与实际完整页面高度一致。960、390 的表格按批准稿在自身容器横滚，未扩大整页模拟完整表宽。

路由：`http://127.0.0.1:8768/#view=piece&piece=fixture-piece&ptab=direct`。每张实际视口高度为 900，宽度如下；最终采集时间为台北时间 **2026-10-27 13:27:26–13:27:30**。字体模式为 `fallback-local`。

| 状态 / 文件 | 实际视口 | PNG 尺寸 | 本人逐图结论 |
| --- | --- | --- | --- |
| `first-handoff-1440.png` | 1440×900 | 1440×2637 | 来源、版本、时间在表头下；六列对齐，03 镜警示可辨；配音卡、相邻风格段及页底完整。 |
| `first-handoff-960.png` | 960×900 | 960×3240 | 来源与本机修改说明自然换行；表格自身横滚；风格、配音、生成条上下排列，无页级溢出。 |
| `rescript-newer-1440.png` | 1440×900 | 1440×2612 | 新版横条和换版按钮可见；接受前保留当前七镜，无来源标签；风格和页底完整。 |
| `rescript-newer-960.png` | 960×900 | 960×3186 | 新版入口、返回按钮清楚；表格、相邻风格段及下方说明层级正常，页底完整。 |
| `first-handoff-390.png` | 390×900 | 390×4632 | 来源、本机修改说明和配音信息可读；单列风格卡完整，生成标签一行，未见页级溢出。 |
| `rescript-newer-390.png` | 390×900 | 390×4628 | 第 4 版与时间自然折行，换版按钮完整；七镜及相邻风格段完整，生成按钮一行。 |

这些文件均位于证据根目录。`gallery.html` 的六个链接已逐一验证指向上述最终文件；`screenshot-manifest.json`、`screenshot-review.json` 记录各图 SHA-256、浏览器、视口、时间、滚动覆盖、输出尺寸和本人 review note。最终哈希已复算一致，没有交付旧图。首次截图发现的手机按钮问题已经修复，最终六张均为修复后重拍。

这里完成的是设计合同、单页启发式与夹具任务流检查；不是用户 5 秒测试、真人验收或真实交接任务成功率。来源类别/版权状态为专门覆盖四类标签的合成夹具，图片为批准设计样例，不作为素材来源事实证据。未新增模型信息、长标识披露、嵌套列表或引用组件。

## 复跑

沿用 R278 `REPORT-F1.md` 第 7 节环境，合同固定用本 worktree，媒体从原项目只读取：

```sh
export HARNESS_CORE="$HOME/Desktop/Opensource_Tool/Harness_Engineering/Core"
export UI_COPY_QUALITY_CHECKER="$HARNESS_CORE/skills/ui-copy-quality/scripts/check_ui_copy_quality.py"
export R278_DESIGN_MEDIA_ROOT="$HOME/Desktop/创业项目/photo-content-os/docs/tasks/R278-direct-rescript/design/img"
export R278_FRONTEND_EVIDENCE="$HOME/.photo-content-os/evidence/R282-direct-handoff/frontend"
export VIDEO_RENDER_PLAYWRIGHT_MODULE="$HOME/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js"
export VIDEO_RENDER_BROWSER="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"
export DIRECT_GATE_PORT=8768
node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
node scripts/direct_video/rescript_frontend_gate.mjs --capture-only --states=first-handoff,rescript-newer --widths=1440,960,390
```

不得把 `R278_DESIGN_ROOT` 指到另一份合同；默认就是本 worktree 的批准合同。重拍之后必须重新逐图审看，采集程序不会代写视觉 PASS。

## B 接口对齐、边界及状态

- 已只读对齐 B 当前源码：新版字段为 `job.handoffNewer`；交接 `revision` 来源为 `identity.workRevision`。前端字段一致，没有后端文件写入。
- **未完成的接口事实：** B 当前投影 `handedAt: null`，注释/OpenAPI 表示 producer 尚未传输交接创建时间。因而真实交接不能显示设计要求的时间；对于不是从交接创建的旧任务，也无法依靠交接时间判断更新。前端对 null 省略时间，未冒用文件时间或造日期；测试用合法时间只证明前端渲染。需要总控/B 确定可用的交接时间来源。本段不越界修后端或中台。写报告时 `REPORT-B.md` 尚未出现，以上按其当前源码说明，不代表 B 最终结论。
- 无配音时不写「配音都已带上」，不显示带配音来源片段；保留交接起止时间，省略「按中台的配音」说明。没有新增稿外文案。
- 人工日志中与本段相交的 R276、R277、R278、R283 仍为 PENDING；本段未编辑、代签或重基线任何人工记录。真实 H-01–H-03 留给总控整体验收。
- 本 worktree 开工/收尾 HEAD 为 `614c55060554de74beb547e7213877c369fa69cb`。业务 Git 有本段前端、门禁、测试、夹具及报告未提交改动；同时存在 B 线程的后端/OpenAPI/测试改动，以及开工已有的 `.venv`、需求卡和任务单未跟踪项。本段没有暂存、提交、推送、清理或回退它们。完整状态见证据中的 `business-status.log`。
- 没有改 Harness SSOT；收尾只读状态有 **94 条**既有/并行记录，见 `harness-status.log`。项目入口 `develop/harness/fullstack-ai-harness.md` 在该稀疏 worktree 不存在，已读取 Core 原文及项目 adapter；没有补建或改链接。
- 没有创建或更新声明的 SSOT 开发包；本报告及仓库外机器证据不属于 SSOT 快照对象，因此没有新建 Obsidian 快照或提醒。

按任务单，报告写完后停止。

## 补充 1

2026-10-27。仅完成任务单「补充 1」的 F 部分，未提交、未推送。**本节替代首轮关于版本来源和交接时间接口缺口的现行结论**：已只读核对 B 的补充报告，`revision` 现在来自可选的 `storyboardRevision`，`handedAt` 来自同名可选字段，前端按其投影的 `null` 处理。真实中台新包及 H-01–H-03 仍未在 F 段验收。

### 本轮改动

- `direct-view.js`：`revision` 为 null 时不显示版本片段，时间缺失时不显示时间及其分隔点；剩余作品名、配音、本机修改说明保留。新版横条没有版本号时准确写「中台又交过来新的分镜。」，再接「换成中台这版」。有版本号、无时间时保留版本，反向缺失时保留可用时间；无版本号的新版横条遵照补充要求使用上述固定句子。
- `tests/fixtures/r282-direct/first-handoff-legacy.json`：新增一份旧包的 API 投影，`revision`、`handedAt` 均为 null，其余七镜内容、图片及配音与原交接夹具完全相同。这里是后端对旧包的投影形状，不是伪造中台已存在的字段。
- 扩展既有 `test_r282_frontend.mjs`：版本/时间分别存在、分别缺失和同时缺失的四种组合，首次横条和新版横条都做全文断言；验证七镜与图片仍可用，接受新版后可替换台词，空版本建任务仍准确发送 `{jobId, revision: null}`。另外验证无配音、无元数据时只保留作品名，不留下分隔点。没有新增测试框架。
- `test_r282_frontend.py` 验证新夹具仅将两个元数据改为空，其余内容完整保留。
- 门禁新增 `first-handoff-legacy`、`rescript-newer-unversioned` 两个场景，分别绑定既有 `first-handoff`、`rescript-newer` 的六块批准合同。后者保留有效交接时间、仅去掉版本号，代表后端有依据判断为更新的情形。没有修改设计合同、approved-extras 或 Core 检查器。
- 本次完整门禁暴露既有 `first-new-drafting` 只等待字面「0:42」的计时断言超时，记录在 `checks.log`。同一 F 门禁内改为严格按夹具 `startedAt` 和当前测试时间计算完整 m:ss；保留计时公式断言，不固定成某一秒，不改产品时钟。最终完整复跑通过。
- 本轮未改 `direct-storyboard.js`、`direct-style.js`、CSS、任何 B 文件或中台文件；没有增加颜色、内联样式或组件。

### 测试结果

本轮全部证据位于 `~/.photo-content-os/evidence/R282-direct-handoff/frontend/supplement-1/`。

| 检查 | 结果 / 证据 |
| --- | --- |
| 先补浏览器断言，在未改产品代码时运行 | 预期失败：实际含「第 null 版」，要求省略；`red-browser.log` |
| 三项 Node：R282 / R278 / R283 | 均 PASS；`node-r282.log`、`node-r278.log`、`node-r283.log` |
| 五份前端 pytest：R282 / R278 / R283 / R276 / R277 | **16 passed**；`frontend-pytest.log` |
| `rescript_frontend_gate.mjs --checks-only` | **52 次 / 264 块合同 PASS**，含所有原交互及新增元数据组合；`checks-final.log`、`checks-contracts.json` |
| 最终新截图的合同检查 | **4 次 / 24 块 PASS**；`captures.log`、`contracts.json` |
| `check_repository_safety.py --base HEAD` | PASS；`repository-safety.log` |
| `git diff --check` | PASS |

以上为真实挂载的本地 Studio 与合成 API 夹具验证，不涉及真实模型调用、声音处理或成片生成。未跑全量 pytest。门禁全部串行，仅一个无头 Chromium，端口 8768，使用独立临时状态/素材目录。

### 新截图与逐图审看

最后产品改动之后重新加载真实应用，再拍以下四张完整页面。实际视口高度均为 900，捕获从页顶覆盖到页底生成条；PNG 高度与文档滚动覆盖高度一致。每张均用 `view_image` 单独打开，手机新版页另用原尺寸复看。表格仍在自身容器内横滚，没有整页横向溢出。

路由：`http://127.0.0.1:8768/#view=piece&piece=fixture-piece&ptab=direct`。采集时间为台北时间 **13:38:54–13:38:57**，字体模式为 `fallback-local`。

| 新截图文件（相对本轮证据目录） | 实际视口 | PNG 尺寸 | 本人看图结果 |
| --- | --- | --- | --- |
| `first-handoff-legacy-1440.png` | 1440×900 | 1440×2637 | 来源条没有版本号或时间，作品名、配音及本机说明保留；七镜六列、相邻风格与页底完整。 |
| `first-handoff-legacy-390.png` | 390×900 | 390×4612 | 缺失字段无占位，来源说明自然换行；表格横滚边界、配音卡及生成按钮完整。 |
| `rescript-newer-unversioned-1440.png` | 1440×900 | 1440×2612 | 横条准确为「中台又交过来新的分镜。」并接按钮，没有虚构版本；原分镜和相邻区域完整。 |
| `rescript-newer-unversioned-390.png` | 390×900 | 390×4576 | 新版句子与按钮同一行可读；原七镜、风格段、配音卡和页底生成按钮完整。 |

本轮 `gallery.html` 的四个链接已核实指向以上最终文件。`screenshot-manifest.json`、`screenshot-review.json` 保存 SHA-256、实际视口、浏览器、采集时间、覆盖范围和逐图 review note，最终哈希复算一致。原首轮六张截图及其哈希保持不变，不冒充本轮重拍。

复跑沿用上文环境，仅将 `R278_FRONTEND_EVIDENCE` 改为本轮证据目录，再串行执行：

```sh
node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
node scripts/direct_video/rescript_frontend_gate.mjs --capture-only --states=first-handoff-legacy,rescript-newer-unversioned --widths=1440,390
```

### 边界和收尾

- B 的补充报告与本轮前端字段一致；未重新实现版本比较或读取原始交接包，也未修改 B 的文件。受保护文件前后哈希比对中，仅 `tests/test_r282_handoff.py` 在 B 并行工作期间变化；本段未覆盖或回退，记录在 `protected-after.json`。
- 业务项目 HEAD 仍为 `614c55060554de74beb547e7213877c369fa69cb`，原 B/F 未提交改动继续保留。本补充仅新增上述前端处理、测试、夹具、门禁及报告追加内容，没有暂存、提交、推送。
- Harness SSOT 未改；只读状态仍为 **94 条**既有/并行记录。两仓库状态、校验计数与截图信息见本轮 `business-status.log`、`harness-status.log`、`verification-summary.json`。
- 临时浏览器、8768 服务及临时状态已关闭/移除，8768 无监听；没有操作其他端口的 Studio。收尾磁盘约 **5.1 GiB**。相交的人工作品验收仍为 PENDING，未代签；没有创建 SSOT 开发包或 Obsidian 快照。

补充 1 写完后停止。

## 修一轮（交付前）

2026-10-27，总控指定的修复轮。以当前 `2430f0d2ee490c317e38ab9eb1cb99e49349da6e` 为基准，先按原样串行复跑四项，再修仍然失败的门禁。**指定检查最终全部 PASS**；未提交、未推送，未应用交付线程的受阻补丁，未改产品前端、后端 `.py`、渲染器、设计合同、判据或 approved-extras。

### 逐条根因与处理

| 原失败 | 在恢复的 headless-shell 下复跑 | 根因与处理 |
| --- | --- | --- |
| R278 点浮层外面关闭后焦点返回失败 | 原码直接 PASS；R282/R278/R283 全门禁 52 次合同比较通过 | 本轮未复现。使用恢复的 1228 构建，保留原来的关闭和焦点返回断言，没有改交互或断言。先前环境使用了另一浏览器，本轮证据只支持「原固定浏览器下通过」，不能独立证明系统 Chrome 是唯一原因。 |
| R276 缺 handoff 接口夹具 | 原码稳定报 `Unmocked API: GET …/direct/handoff` | R282 进入页面会读取交接投影，旧 R276 夹具未登记此 GET。只在 `frontend_gate.mjs` 补该作品精确路由的 `{ok:true,handoff:null}`，表示本场景没有交接包；未知路由仍失败。 |
| R277 等 `DV-DETAIL` 15000ms 超时 | 原码稳定复现；错误清单明确记录同一 handoff GET 未处理 | 旧 R277 夹具把该请求变成 500，应用进入读取错误态，因此没有详情元素。只在 `revision_frontend_gate.mjs` 补同一空交接投影；没有增加等待时间或改产品错误处理。 |
| R277 DOM 子进程 45 秒 / `shot_timeout` | 两条真实浏览器用例直接 **2 passed in 27.31s** | 恢复原浏览器后未复现；保留原 30 秒镜头预算、45 秒子进程预算及所有几何断言。不改渲染器、后端或测试 Python。与焦点问题一样，不将一次环境恢复后的通过当成系统 Chrome 唯一根因的证明。 |

两个门禁同时加强了回归检查：统计真实挂载页面对 handoff 的读取次数，正常初次进入必须恰好一次；R276 的原读取失败场景必须为零，因为 latest 已失败。原场景、空态、读取错误、交互、来源隔离、合同和布局断言全部保留。修复前的两份失败日志就是缺夹具的红证据；没有把接口请求屏蔽、绕开或当作读取成功。

实际源码改动只有：

- `scripts/direct_video/frontend_gate.mjs`：精确 GET 夹具、读取计数和页面级断言。
- `scripts/direct_video/revision_frontend_gate.mjs`：同上。
- 本报告末尾追加本节，之前的报告正文保持逐字不变。

### 固定环境与重跑结果

本轮使用 **Playwright 1.61.1 / chromium-headless-shell revision 1228 / 149.0.7827.55**。可执行文件是恢复后的 `~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`，不是系统应用目录里的 Google Chrome。`--version` 显示的品牌文字为 `Google Chrome for Testing`；包元数据、具体可执行文件路径和 SHA-256 已记录到证据，不能仅凭品牌文字判断是否换了浏览器。

环境沿用 R278 `REPORT-F1.md` 第 7 节，另将 `R278_DESIGN_ROOT` 固定为本 worktree 的批准合同，设置 `R278_DESIGN_MEDIA_ROOT` 为原项目只读样例目录，`DIRECT_GATE_PORT=8768`，`R277_SOURCE_STATE=~/.photo-content-os/studio-r278`。三份门禁使用独立的本轮证据子目录，全部串行执行，一次只有一个自有无头浏览器。

证据根：`~/.photo-content-os/evidence/R282-direct-handoff/frontend/pre-delivery-repair/`。

| 检查 | 最终结果 | 日志 / 结构化证据 |
| --- | --- | --- |
| `rescript_frontend_gate.mjs --checks-only` | **52/52 次、264 块合同 PASS**；含原关闭/焦点、视频生命周期、R282、R278、R283 交互 | `rescript-baseline.log`、`rescript/contracts.json` |
| `frontend_gate.mjs --checks-only` | **26/26 次合同 PASS**；原公式、交互及新增 handoff 读取断言通过 | `r276-final.log`、`r276/contracts.json` |
| `revision_frontend_gate.mjs --checks-only` | **42/42 次合同 PASS**；原真实旧任务、图形标记、详情、版本、日志、轮询和布局检查通过 | `r277-final.log`、`r277/contracts.json` |
| `tests/test_r277_boxes.py` 全文件 | **2 passed in 27.31s**，未跳过、未用渲染替身 | `r277-render-baseline.log` |
| 五份前端 pytest：R276 / R277 / R278 / R282 / R283 | **16 passed in 0.31s** | `frontend-pytest.log` |
| `check_repository_safety.py --base HEAD` | PASS | `repository-safety.log` |
| `git diff --check` | PASS | 收尾终端记录 |

两条真实用例分别是：

- `test_r276_shot02_boxes_at_poster_frame_and_chinese_names`：真实帧渲染与 DOM 测量，保持隐藏元素剔除、中文名称、坐标、柱宽和两倍柱高关系等全部断言。
- `test_local_render_stores_boxes_and_three_review_frames`：真实 `LocalMedia.render`，保持 poster 时刻坐标和三张 review frame 文件/尺寸断言。

本轮没有跑全量 pytest，没有真实 Claude 生成、中台新包或人工 H-01–H-03 验收。R276/R277 的页面交互仍包含合成 API 夹具；R277 同时运行真实旧任务副本和已有真实投影的只读重放。两条 Python 用例是真实浏览器渲染/DOM 检查，与这些页面夹具的验证范围分开记录。

### 证据和收尾状态

- 失败证据保留在 `r276-baseline.log`、`r277-baseline.log`、`r277-baseline-manifest.json`；后者的错误清单可直接追到未处理的 handoff GET。没有覆盖成成功记录。
- `verification-summary.json` 汇总固定浏览器、包版本、文件哈希、各门禁计数和测试输出。R276/R277 最终浏览器错误清单均为空。
- R277 使用原状态的 APFS 临时副本；原目录 **8,670 个文件**前后哈希一致。30 个产品 Python 源文件前后哈希一致，见 `protected-python-after.json`。未编辑任一 `.py`。
- 本轮只改门禁，没有视觉修改，因此按指定的 `--checks-only` 运行，**未新增整页截图，也未宣称完成一轮新的视觉审图**。原设计及截图没有被重写或加入新的批准例外。
- 业务 Git HEAD 仍是 `2430f0d`；工作区只有两个门禁、本报告的未提交修改，以及开工已有的 `.venv`。没有暂存、提交、推送或改写历史。完整状态见本轮 `business-status.log`。
- Harness SSOT 零修改；只读状态仍有 **94 条**既有/并行记录，见 `harness-status.log`。没有改验收记录或代签，关联人工项仍为 PENDING。本轮没有创建声明的 SSOT 开发包，不产生 Obsidian 快照。
- 磁盘始终高于 3 GiB，收尾约 **7.9 GiB**。本轮临时服务、浏览器和临时目录已退出/清理，8768 无监听。**8769 仍是原监听 PID 45249**，没有停止或重启。

本节写完后停止。
