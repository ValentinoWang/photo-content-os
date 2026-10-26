# R278 前端第一段 F1 汇报

日期：2026-10-26。任务：`FRONTEND-TASK.md` 第二段前端。业务 HEAD：`107b56eb0ab66881d706e8bdecae30f945619da2`。

## 1. 和设计稿哪里不一样

R278 的目标状态和交互已实现。页面沿用当前 Studio 深色语义令牌；设计说明明确浅色属于 R280，本段没有落地浅色主题。模型生成的色板、字号、动作短文案属于接口数据，截图使用夹具数据；未宣称这些是本轮真实模型输出。R282、R283 标记内容全部未实现。

| 状态 | 对照结果（1440、960 均已逐图查看） |
| --- | --- |
| `entry` | 整格可点，右侧「改分镜脚本」；入口夹具帧数已按时长重算。 |
| `writing` | 入口不可点，灰字「写完才能改」。 |
| `composing` | 入口不可点，灰字「合成完才能改」。 |
| `rescript` | 预填七镜、当前风格；四块整行从上到下。 |
| `rescript-zoom` | 第 02 镜浮层、时间、关闭按钮及减少动态效果下的播放控件。 |
| `rescript-adjust` | 改哪里、生成后的第一步、生成条同步显示调整意见。 |
| `rescript-other` | 改选另一条风格后，卡片、大预览及生成条同步。 |
| `first-empty` | 220px 粘贴空态；导入在框底部，生成在页底并禁用。 |
| `first` | 六列表、每镜文字只出现一次、估算时间与风格选择。 |
| `first-new` | 六项提示、未写说明、样张空态；两个生成相关按钮禁用。 |
| `first-new-text` | 说明保留，先定风格可点，生成仍禁用。 |
| `first-new-drafting` | 说明只读；正在定风格、已用 0:42；生成禁用。 |
| `first-new-ready` | 样张、色板、字号、短文案、再改一句、就用这个；生成禁用。 |
| `first-new-revising` | 保留说明和修改意见；正在改样张与计时；相关按钮禁用。 |
| `first-new-accepted` | 已选用、重新定、样张来源；生成可点。 |
| `first-new-failed` | 失败原因和重试；说明与分镜保留。 |
| `first-none-r278` | 没有可沿用成片；默认从头定，现成风格分段禁用。 |
| `designing` | 正在按意见改全片设计；虚线框写明来源及意见。 |
| `inherited` | 来源为沿用；动作规矩和不用使用短文案，无删除线。 |
| `adjusted` | 来源为改过；两个标题、短标签、换行均正确。 |

另看了复制的真实旧任务 `real-worst-rescript-1440`：长台词到第 07 镜及页底都完整；没有短文案时，动作原话限制两行，长「不用」标签省略并保留悬停全文。没有用原始生产目录运行或写入任务。

## 2. 本段改动文件

| 文件 | 改动 |
| --- | --- |
| `studio/static/direct-view.js` | 改分镜入口、锁定原因、表单状态、逐作品输入保留、风格及样张请求、生成请求、来源和设计行。 |
| `studio/static/direct-storyboard.js`（新） | 六列表、时间与数量公式、拆镜/并镜/粘贴/导入、片段可见性播放、减少动态效果、关键帧回退、放大浮层。 |
| `studio/static/direct-style.js`（新） | 风格卡片及大预览、分段输入保留、六项提示、样张状态、选用及重定、生成可用条件与载荷。 |
| `studio/static/direct-rescript.css`（新） | 按稿移植 R278 新块，复用现行令牌；960 分界、表格横滚、旧文案两行限制。 |
| `studio/static/direct.css` | 删除已取消的逐镜重复列表样式和旧「不用」删除线样式。 |
| `studio/static/index.html` | 只增加 `direct-rescript.css` 链接。新 JS 由 `direct-view.js` 通过模块导入。 |
| `tests/test_r278_direct_rescript.mjs`（新） | 公式、编辑操作、请求与入口条件；导出在真实 Studio 上执行的浏览器交互断言。 |
| `tests/test_r278_direct_frontend.py`（新） | 模块边界、名称、CSP、颜色、样式链接、表格和生成条静态检查。 |
| `tests/fixtures/r278-direct/*.json`（20 份新夹具） | 每个指定状态的 latest、styles、draft 接口返回，以及用于真实 UI 导入的分镜。任务字段经后端投影形状组织。 |
| `scripts/direct_video/rescript_frontend_gate.mjs`（新） | 8768 临时 Studio、逐状态 API 拦截与交互、完整截图、公式/布局断言、逐块合同采集、外部证据保存。 |
| `scripts/direct_video/frontend_gate.mjs` | R276 门禁的端口、风格接口、表单操作、请求体和新合同接入，逐条见第 6 节。 |
| `scripts/direct_video/revision_frontend_gate.mjs` | R277 门禁接入 R278 已批准的步骤条/设计行变更；端口参数化，逐条见第 6 节。 |
| `docs/tasks/R278-direct-rescript/REPORT-F1.md` | 本汇报。 |

后端文件、schemas、R277 的 `direct-shot-detail.js/.css` 和 `direct-revision-log.js` 均未修改。第一段 A 的 14 个源码/测试文件逐一核对原记录 SHA-256，全相同，见仓库外 `backend-preservation.json`。已有后端未提交改动完整保留。

## 3. 任务单第 2 节逐条结果

1. **入口：完成。** 任务停止、无读取错误且 R277 看图/核改未运行时，第一格是键盘可聚焦按钮；写镜/合成各自显示锁定原因。进入表格时滚到顶部，聚焦第 01 镜开头。返回按钮只切本地视图，浏览器测试核对请求数量不增加。
2. **版式：完成。** 分镜脚本 → 视频风格 → 说明与配音两卡 → 生成条。1440 两卡并排，960 上下排。门禁断言四块等宽、上下顺序、选项列数和表格宽度公式。
3. **分镜表：完成。** 六列名与稿一致；五个文本字段预填并可改，台词按 Unicode 字符数除以 5.1 累计时间。空镜不占时间、生成不发送。回车拆镜、IME 回车不拆、开头退格并镜、多行粘贴丢空行、其他列回车换行均保留；拆镜时其他列及画面留在前一镜，并镜遵循演示稿台词接续、其他四列用「；」连接。导入把四个可选字段放到对应列。发送 `storyboard`，不再发送 `script`。
   - 片段是同版本 `clip.mp4?v=posterRevision`，静音、循环、playsinline，无缩略图控件；IntersectionObserver 进屏播放、出屏暂停，减少动态效果时暂停，片段 error 回退关键帧。
   - 静图和动画均可放大；Esc、关闭、外部点击、滚动关闭并恢复原按钮焦点；换镜直接替换浮层。减少动态效果时浮层提供控件且不自动播放。
4. **视频风格：完成。** GET 风格列表、当前风格默认值、卡片单选、大预览和可选调整意见；两种分段保留输入。列表去重掉当前任务时仍保留当前任务的合法风格来源，不把它清空。无可用成片默认从头定。六项提示在说明末尾添加「项名：」。样张创建/读取/revise 三类接口已接，2 秒轮询、计时、失败重试、再改一句、选用、重新定完整。离页停轮询，回到本作品保留文本和样张；刷新按稿丢页面状态。
5. **生成条：完成。** 位于页底，显示所选风格及意见，或未定好的原因。台词非空、Claude 未报不可用、不在提交、风格来源满足条件才可生成；沿用发送 job `styleBase` 和可选 `style`，从头定发送已选用的 ready draft 来源。生成请求失败留在表单，文本不丢，已用浏览器断言验证。
6. **全片设计：完成。** 显示 `design.source`；「动作规矩」「不用」使用 `motionSummary`/`bannedShort`。老任务 null 时保留原话，动作两行限制、标签省略并保留 title，去掉删除线。
7. **改名：完成。** `direct-view.js` 不再出现「口播稿」，新编辑列叫「台词」。R277 详情中的「口播」未改。
8. **CSP 与颜色：完成。** 没有内联 `style=`；色块通过 CSSOM `setProperty('--swatch', …)` 赋接口色板，界面新颜色只引用现有令牌。3 个 JS 的文案词法检查 0 错误、0 警告。

R282 的中台交接、配音时间接入和 R283 风格库不在本段范围。按配音使用起止时间的纯公式有测试，但本段不接中台交接接口。

## 4. 先红后绿及最终检查

实现前已写两份 R278 新测试并运行：

- Node：因新增分镜模块不存在而失败，日志 `red-node.log`。
- Python：**3 failed**，分别拦到模块缺失、旧名称及旧表单结构，日志 `red-python.log`。

实现及浏览器修复后结果：

| 检查 | 最终结果 | 外部证据文件 |
| --- | --- | --- |
| `node tests/test_r278_direct_rescript.mjs` | PASS：公式、字段、编辑运算、风格条件、请求体与入口锁定 | `node-final.log` |
| 指定三份前端 Python 测试 | **13 passed**，0.17s | `python-final.log` |
| `node tests/test_r276_direct_frontend.mjs` | PASS | `r276-node-final.log` |
| `node tests/test_r277_frontend.mjs` | PASS，既有 17 状态夹具与数值检查 | `r277-node-final.log` |
| R278 `--checks-only` | PASS：真实 Studio 挂载、点击/键盘/导入/请求/媒体/轮询交互，40 次逐状态合同检查 | `browser-checks-final.log` |
| R278 最终 `--capture-only` | PASS：41 张完整页截图、41 次合同检查、**204 个分块比对** | `final-capture.log`、`contracts.json`、各 inventory/contract JSON |
| `check_ui_copy_quality.py` | PASS：3 文件，0 警告；仅词法检查 | `copy-quality.log`、`copy-quality/` |
| `check_repository_safety.py --base origin/main` | PASS | `repository-safety.log` |
| `git diff --check` | PASS | `diff-check.log` |
| 旧门禁合同组合及 JS 语法 | R276 13 状态、R277 9 个合同状态可组合；原支持的设计编号保留，日志页不误加步骤条；两脚本语法通过 | 见本轮工具记录 |

浏览器实际断言还包括：返回不发请求、六列列名、没有 `.dv-lines`、生成不在分镜框里、输入法不拆镜、导入四列、生成失败保留文本、样张未选用时不能生成、revise 载荷、选用后 draft 建任务、风格列表去重后当前来源仍可生成、样张计时随轮询更新、离页停止样张轮询、片段进出屏播放/暂停、减少动态效果、片段错误回退、静图放大及四种关闭方式恢复焦点。

没有运行全量 pytest，也没有重跑旧 R276/R277 的完整截图或真实模型生成路径；本段只拍任务指定 20 状态和真实旧任务投影。旧门禁全量验证及受保护基线处理留给总控，不能由本段的专项 PASS 代替。

合同采集使用 Core 原版 `collect_design_inventory.js` 的 `options.states`，逐一指向真实 DOM 的 steps/head/script/style/opts/gen/design 包裹层；未改 R278 `contract.json`，未增加 approved-extras，未过滤稿外文字或缺失编号。分块根缺失会直接失败。生成条包裹层仅用于采集根编号，没有可见元素或文字。

## 5. 截图与个人看图记录

最终截图根：`~/.photo-content-os/evidence/R278-direct-rescript/frontend/`。

本地截图索引：
[gallery.html](~/.photo-content-os/evidence/R278-direct-rescript/frontend/gallery.html)。每个图片链接均已核验指向当前最终 PNG，SHA-256 与 `screenshot-manifest.json` 一致。

实际视口为 **1440×900、960×900**，960 是本次指定窄屏，未声称额外做手机宽度验收。路线为 `http://127.0.0.1:8768/#view=piece&piece=fixture-piece&ptab=direct`；真实旧任务使用其原 projectId。均从页顶覆盖到页底；表格按稿在自身容器横滚，没有把表格横向宽度伪装成整页宽度。清单记录浏览器版本、视口、时间、滚动覆盖、PNG 尺寸、哈希、fallback-local 字体模式和逐图结论。

| 状态 | 1440 图片路径 | 960 图片路径 |
| --- | --- | --- |
| `entry` | [entry-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/entry-1440.png) | [entry-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/entry-960.png) |
| `writing` | [writing-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/writing-1440.png) | [writing-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/writing-960.png) |
| `composing` | [composing-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/composing-1440.png) | [composing-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/composing-960.png) |
| `rescript` | [rescript-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-1440.png) | [rescript-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-960.png) |
| `rescript-zoom` | [rescript-zoom-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-zoom-1440.png) | [rescript-zoom-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-zoom-960.png) |
| `rescript-adjust` | [rescript-adjust-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-1440.png) | [rescript-adjust-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-960.png) |
| `rescript-other` | [rescript-other-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-1440.png) | [rescript-other-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-960.png) |
| `first-empty` | [first-empty-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-empty-1440.png) | [first-empty-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-empty-960.png) |
| `first` | [first-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-1440.png) | [first-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-960.png) |
| `first-new` | [first-new-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-1440.png) | [first-new-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-960.png) |
| `first-new-text` | [first-new-text-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-text-1440.png) | [first-new-text-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-text-960.png) |
| `first-new-drafting` | [first-new-drafting-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-drafting-1440.png) | [first-new-drafting-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-drafting-960.png) |
| `first-new-ready` | [first-new-ready-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-ready-1440.png) | [first-new-ready-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-ready-960.png) |
| `first-new-revising` | [first-new-revising-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-revising-1440.png) | [first-new-revising-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-revising-960.png) |
| `first-new-accepted` | [first-new-accepted-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-accepted-1440.png) | [first-new-accepted-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-accepted-960.png) |
| `first-new-failed` | [first-new-failed-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-failed-1440.png) | [first-new-failed-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-new-failed-960.png) |
| `first-none-r278` | [first-none-r278-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-none-r278-1440.png) | [first-none-r278-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-none-r278-960.png) |
| `designing` | [designing-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/designing-1440.png) | [designing-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/designing-960.png) |
| `inherited` | [inherited-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/inherited-1440.png) | [inherited-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/inherited-960.png) |
| `adjusted` | [adjusted-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/adjusted-1440.png) | [adjusted-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/adjusted-960.png) |
| 真实旧任务最差首屏（完整页） | [real-worst-rescript-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/real-worst-rescript-1440.png) | 按任务单只加一张 |

我逐张打开过全部 41 个 PNG，检查页头、目标区域、邻接区与页底；最终刷新后，38 张与已看版本哈希相同，另 3 张（两个 zoom、designing 1440）再次逐张打开。全部最终文件有逐图 review note。入口修复后的两张也已重新打开检查。

本轮发现并已修复的问题：

- DOM 包裹层使用 display:contents 时，稿中的「直接子元素占整行」选择器未覆盖新包裹层，造成风格区挤入旧网格，提示按钮被预览遮挡；改为匹配实际网格内容，补整行顺序/宽度断言。
- 点浮层外部关闭时，pointerdown 后浏览器默认焦点行为覆盖了返回焦点；移到 click 阶段关闭，四种关闭方式的焦点断言通过。
- 视频失败回退成静图后，放大仍尝试原片段；改为按实际缩略图媒体类型选择浮层媒体，静图放大断言通过。
- 入口夹具把 142.8 秒写成 143 秒，导致现有帧数检查出现红叉；重算为 4284 帧后重拍并确认绿色，未修改检查判据。
- “无成片”状态的准备步骤误用了空脚本；按原稿准备已有台词后，40/40 指定合同检查通过。

截图和视频/图片素材均在仓库外。原真实 job.json 先复制再投影，前后与副本哈希一致，见 `source-preservation.json`。样张和片段媒体来自设计稿引用的本机样例；这些截图证明当前前端在夹具下的渲染与交互，不代表本段真实模型生成、真实后端写入或生产部署验收。

## 6. R276 / R277 门禁变更逐条

本段没有改 R276/R277 的 `.py`/`.mjs` 测试文件、旧 JSON 夹具、approved-extras 或人工验收材料；工作区已有的后端测试差异属于第一段 A，已按其哈希核对保留。

`frontend_gate.mjs`：

1. 8767 硬编码改成 `DIRECT_GATE_PORT`，默认仍 8767；主/真实/临时服务启动均传所选端口。本段实际只启动新门禁的 8768。
2. 支持任务指定 Playwright 模块与 headless-shell 可执行路径，保持 headless。
3. 风格列表通过现有 R278 `first.json` 的接口夹具返回；表单的「口播稿」选择器改为「台词」，旧风格输入选择器改成调整意见。
4. 创建请求断言改为带镜号的 `storyboard.shots`、job `styleBase` 和调整文字，继续核对台词和请求次数。
5. 导入等待/断言改成读取台词列数组，覆盖新六列表；保留原配音上传、请求次数、写镜与成片相关断言。
6. 真实生成辅助分支补必需 style，避免新契约拒绝空风格；本段没有执行这个真实生成分支。
7. 新增合同组合入口：仅将 R278 批准的首屏各块、步骤条改名/入口/锁定和设计行两个标题叠入对应旧状态；移除已取消的 `DV-LINES`，要求新表格/风格/生成条编号。原支持编号及其他断言保留，没写新白名单。

`revision_frontend_gate.mjs`：

1. 端口和占用探测统一读取 `DIRECT_GATE_PORT`，默认保持原来的 8768。
2. 支持任务指定的无头浏览器与 Playwright 路径。
3. 原合同组合 R278 的步骤条及全片设计行变更；有步骤条的任务状态要求相应入口/锁定编号，日志页不增加步骤条。镜详情、标记、对比、版本和问题记录的原检查保留。

这些是受保护门禁相关变更。R276/R277 开工时均为 PENDING，本段没有处理 G16 rebaseline、改 binding/handoff 或签署人工结果。总控需按本节逐处审阅后运行旧卡完整机器范围并处理基线，不能把本汇报当作发布 READY。

## 7. 复跑方式

在任务 worktree 软件根执行，设置任务单的环境：

```sh
export HARNESS_CORE="$HOME/Desktop/Opensource_Tool/Harness_Engineering/Core"
export R278_DESIGN_ROOT="$HOME/Desktop/创业项目/photo-content-os/docs/tasks/R278-direct-rescript/design"
export VIDEO_RENDER_PLAYWRIGHT_MODULE="$HOME/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js"
export VIDEO_RENDER_BROWSER="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"
export DIRECT_GATE_PORT=8768
export UI_COPY_QUALITY_CHECKER="$HARNESS_CORE/skills/ui-copy-quality/scripts/check_ui_copy_quality.py"
node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
node scripts/direct_video/rescript_frontend_gate.mjs --capture-only
```

默认运行不带参数会依次执行浏览器交互、全部合同和截图。每次只开一个无头浏览器、一个页面，页面截完关闭，整轮 finally 关闭浏览器及自有临时服务、删除临时状态目录。端口占用会拒绝运行，不复用或结束他人进程。每次开页/截屏检查剩余磁盘，不足 3 GiB 即失败停止。`--states=entry` 可仅重拍指定状态并保留其余有哈希的截图记录；刷新后的截图必须重新看图，采集脚本不会自动写视觉 PASS。

## 8. 需要的接口、新文案、稿外元素与未完成范围

- **需要的接口：无。** 本段目标已有接口可满足，未自行修改后端。
- **需要新文案：无。** 使用批准稿文字、既有失败翻译及接口动态数据；未加 approved-extras。
- **稿外元素：无新增可见元素。** 包裹节点、输入上限和 CSSOM 赋值仅用于实现及采集。
- **R278 本段目标未完成项：无。** 本地专项、20 状态合同、截图和个人逐图检查已完成。
- **未在本段执行：** 旧卡全量截图/真实生成门禁、G16 基线处理、人工验收、生产部署；以及任务明确排除的 R280/R282/R283。这里的完成仅指前端 F1 执行段。

## 9. Git 与 Harness SSOT 状态

- 业务项目仍在指定 worktree，HEAD 未变；本段前端及门禁修改全部未提交、未推送，未新建 worktree。已有后端改动、`.venv` 软链等保留。
- 未改 Harness SSOT。收尾读取该仓库有 **64 条既有/并行状态项**；没有清理、回退、暂存或提交。完整两仓库状态在仓库外 `verification-summary.json`。
- 本段只产生代码、测试、普通证据与本汇报，没有创建或更新声明的 SSOT 开发包，因此没有生成新的 Obsidian SSOT 快照或提醒。
- 临时 8768 Studio 和本段无头浏览器已退出；未操作 8765、8766、8767 服务。磁盘始终高于 3 GiB，收尾约 7 GB 可用。

按任务单，写完本汇报后停止。


## 10. 去掉「这一版」

日期：2026-10-27。按用户决定和 worktree 内已更新的设计说明，仅调整改分镜脚本画面旁的来源标签。

**改动：**

- `studio/static/direct-storyboard.js`：从“有图片就固定输出「这一版」”改为“只有 `image.tag` 有值才输出标签，并转义标签内容”。当前任务的画面没有 tag，因此不再显示来源标签；标签元素和样式机制保留，供以后 R282 的带来源图片使用。没有增加中台接口或其他功能。
- `tests/test_r278_direct_rescript.mjs`：新增真实改分镜页 `.dv-sb .sb-tag` 数量为 0 的断言；用组件内图片夹具验证 `tag: '代码渲染'` 仍显示，并验证标签中的 HTML 字符按原文转义。现有样张计时测试的固定「0:44」在本轮加载耗时下发生超时，已改成冻结测试时钟、等待真实轮询响应，再按当前模拟时间严格计算应显示的 m:ss，保留轮询与离页停止断言。
- `scripts/direct_video/rescript_frontend_gate.mjs`：四个改分镜状态及真实旧任务均断言无来源标签；`--states` 支持 `real-worst-rescript`（只拍 1440），并按截图名称替换对应合同记录。增加可选 `R278_DESIGN_MEDIA_ROOT`，从仓库外已有样例读取媒体，合同仍使用 worktree 内原 `contract.json`。
- 已搜索测试、门禁和 JSON 夹具；原接口夹具没有写死「这一版」，因此没有无关的夹具改动。设计稿现有修改由上游提供，本段未再编辑 spec/draft；`contract.json` 未改。

**测试及合同：**

| 检查 | 结果 | 仓库外日志 |
| --- | --- | --- |
| 实现前新增浏览器断言 | 预期失败：发现 7 个来源标签，要求 0 个 | `no-source-label-red.log` |
| `node tests/test_r278_direct_rescript.mjs` | PASS | `no-source-label-node.log` |
| 三份前端 pytest：R278、R276、R277 | **13 passed** | `no-source-label-pytest.log` |
| `rescript_frontend_gate.mjs --checks-only` | PASS：交互检查及 20 状态 × 两宽度，共 40 次合同检查 | `no-source-label-checks.log` |
| 受影响状态重拍与合同 | **9 张新截图、9 次新合同检查、54 个分块比对，全部通过** | `no-source-label-captures.log`、`no-source-label-review.json` |
| `git diff --check` | PASS | 本轮工具记录 |

截图清单仍包含 41 张，其中本轮仅刷新以下 9 张，其余 32 张保留；门禁输出中的 41 是合并后的清单数量，不代表本轮重拍了全部状态。没有修改合同或增加 approved-extras 来绕过检查。

复跑截图时使用工作区合同和仓库外媒体：

```sh
export HARNESS_CORE="$HOME/Desktop/Opensource_Tool/Harness_Engineering/Core"
export R278_DESIGN_MEDIA_ROOT="$HOME/Desktop/创业项目/photo-content-os/docs/tasks/R278-direct-rescript/design/img"
export VIDEO_RENDER_PLAYWRIGHT_MODULE="$HOME/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js"
export VIDEO_RENDER_BROWSER="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"
export DIRECT_GATE_PORT=8768
node scripts/direct_video/rescript_frontend_gate.mjs --capture-only --states=rescript,rescript-zoom,rescript-adjust,rescript-other,real-worst-rescript
```

**重拍路径与逐图结论：** 所有路径根仍为 `~/.photo-content-os/evidence/R278-direct-rescript/frontend/`；每张实际视口为 1440×900 或 960×900，均是覆盖到页底的完整截图。

| 状态 | 1440 | 960 | 看图结论 |
| --- | --- | --- | --- |
| `rescript` | [rescript-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-1440.png) | [rescript-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-960.png) | 两张均无来源标签，画面说明从单元格顶部开始；七镜表格、下方风格和生成条完整。 |
| `rescript-zoom` | [rescript-zoom-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-zoom-1440.png) | [rescript-zoom-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-zoom-960.png) | 两张背景表格均无标签；第 02 镜浮层、关闭按钮和播放控件完整，未出现新裁切。 |
| `rescript-adjust` | [rescript-adjust-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-1440.png) | [rescript-adjust-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-960.png) | 两张均无标签，调整意见与生成条保持同步；960 维持上下排列。 |
| `rescript-other` | [rescript-other-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-1440.png) | [rescript-other-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-960.png) | 两张均无标签，另一风格的选中、大预览及生成条保持一致。 |
| 真实旧任务最差首屏 | [real-worst-rescript-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/real-worst-rescript-1440.png) | 按要求仅一张 | 七镜画面均无标签；长台词、旧风格原话和页底生成条完整。 |

以上 9 张最终 PNG 已分别用 view_image 打开查看，包括表格、邻接区域和页底；每张 SHA-256 已与清单核对，更新了 review note 和截图索引 `gallery.html`，索引链接指向当前最终文件。完整记录见 `no-source-label-review.json`、`screenshot-manifest.json`。这是本地 Studio 与接口夹具验证，没有把它表述为生产或真实模型生成验收。

**边界及状态：**

- 本段只改上述三个前端/测试/门禁文件，并在本报告末尾追加本节；没有写后端、schemas、acceptance/ 或 agents-results/。后端及设计合同的开工/收尾哈希相同。
- 排除目录在本轮期间有并行变动，读取比对发现 13 个既有文件变化；本段未写入、覆盖或回滚它们，记录在仓库外 `no-source-label-preservation.json`。共享 worktree 的 HEAD 被并行工作从 `4fd1243` 推进到 `ffc8c00`（验收交接回执提交）；该提交不是本段执行的，本段没有提交或推送。
- 8768 临时 Studio 及本段无头浏览器已经关闭。8769 始终保留原监听进程 PID 58162，没有停止或重启。未启动有头浏览器；本轮每次只有一个自有无头浏览器。
- 没有修改 Harness SSOT；收尾只读看到其有 77 条既有/并行状态项，完整状态存于 `no-source-label-summary.json`。

本节写完后停止。


## 11. 交付前修一轮

2026-10-27，总控本轮要求已完成。只改任务 worktree，未提交、未推送。下面是本轮增量；设计稿三份文件的用户更新和上一轮未提交改动继续保留。

### 改动与根因

1. `studio/static/direct-storyboard.js`：只将画面格的空占位改成「写这一镜画什么（可不填）」。字幕 / 花字、景别 · 运镜、音乐 / 音效仍为「—」，沿用原有 `--ink-5` 占位色。`tests/test_r278_direct_rescript.mjs` 增加实际挂载后的占位和四列占位同色断言；已有内容、来源标签机制、请求字段均保留。JSON 夹具无需改动，空画面值仍为空字符串。
2. **R276 的 pageerror 是前端生命周期 bug**：`direct-view.js` 的成片视频 `ontimeupdate` 在旧视频被移除后仍执行，通过 `find('[data-readout]')` 查找当前画面，查到 `null` 后写 `textContent`。重新合成、进入改分镜脚本都可能触发。现在先检查旧视频 `isConnected`，已移除就返回。R278 浏览器测试保留旧视频，进入改分镜脚本后主动调用回调；R276 门禁在重新合成后也调用旧视频回调，确保两条路径都不报错。正常成片跳转、进度和轮询检查保留。
3. **R276 合同漏合批准的 R278 分支**：`composeLegacyContract` 以前只合 `first` 的五块，缺少调整风格时的第一步解释和从头定风格的示例文案。现在在 `filled`、`unavailable` 合入 `rescript-adjust-opts`、`first-new-text-style`。独立的「浅米色底」来自后者已批准示例的首分句，按明确边界提取进这两个状态的组合合同；没有放行任意子串。未修改 `approved-extras`、设计判据或 Core 检查器。Node 增加两个旧状态的合同回归断言；最终四次原失败比较全部通过。
4. **R277 状态来源**：`revision_frontend_gate.mjs` 新增 `R277_SOURCE_STATE`，默认仍为 `~/.photo-content-os/studio-r276`；本轮设为 `~/.photo-content-os/studio-r278`。保留 `/bin/cp -cR` APFS 克隆到临时目录，运行结束删除。源目录只读，前后 8,670 个文件哈希一致。
5. R277 能继续执行后又查出两处：
   - 真实旧任务在 390 宽度溢出到 419。根因是 R278 全片设计的「不用」标签按 260 像素最小内容宽度撑开 flex 行。`direct-rescript.css` 给该行 `min-width:0`，标签最大宽度限制为 `min(260px,100%)`，保留省略号和悬停全文。原有溢出断言保持不变，最终页面宽、滚动宽均为 390。
   - `review`、`compare` 等详情状态被多个运行中场景复用，旧组合合同按基础夹具生成，`rewriting2` 还在点击修改前取值，因此 8 次比较误要求可点的「改分镜脚本」。现在按每次操作后的当前投影单独组合该详情状态的外层 R278 合同。增加普通 / 看图中 / 检查中 / 重写中的步骤锁回归断言，未改详情产品文件或放宽编号判据。最终 42 次比较全部通过。
6. **路径清理**：扫描本任务下所有 Markdown 和整个 `design/`。仅 `TASK.md`、`FRONTEND-TASK.md`、本报告有命中，已按要求改成 `~/…`、「任务 worktree」、「总控 scratchpad」；设计文件无本机绝对路径命中。为检查暂存区，只暂存这三份清理后的 Markdown；本节追加内容留在工作区。没有提交或重写历史。
7. R276、R277 门禁增加 `--checks-only`：保留状态遍历、合同、布局、公式和交互断言，跳过整页与参考页截图；用于遵守本轮只重拍指定 8 张的要求。生成测试用缩略图的原流程保留。R277 的日志在此模式写 `checked`。

### 检查结果

先补测试再实现：`node-red.log` 证明旧组合合同缺少批准解释；`browser-red.log` 稳定复现旧视频回调的 `textContent` 报错；`placeholder-red.log` 证明旧画面占位还是「—」。继续跑出的 R277 运行状态合同失败另存 `r277-variant-red.log`。最终检查如下，所有日志在 `~/.photo-content-os/evidence/R278-direct-rescript/frontend/repair-11/`。

| 检查 | 结果 | 日志 |
| --- | --- | --- |
| `node tests/test_r278_direct_rescript.mjs` | PASS，含批准文案组合和运行状态步骤锁 | `node.log` |
| 三份前端 pytest：R278 / R276 / R277 | 13 passed | `frontend-pytest.log` |
| R278 Python：`test_r278_style_base.py`、`test_r278_clips.py` | 64 passed | `r278-pytest.log` |
| `rescript_frontend_gate.mjs --checks-only` | PASS，20 状态 × 两宽度，40 次 / 198 块；真实 Studio 挂载交互通过 | `r278-checks.log`、`r278-final-contracts.json` |
| `frontend_gate.mjs --checks-only` | PASS，26 次合同及全部既有交互，含旧视频重新合成回归 | `r276-checks.log` |
| `revision_frontend_gate.mjs --checks-only`，使用上述 R277 状态源 | PASS，42/42 合同；真实旧任务、标记、详情、版本、日志和轮询检查通过 | `r277-checks.log` |
| `check_repository_safety.py --base origin/main` | 工作区、暂存区命中均为 0；整体退出 1，只余 9 条历史提交路径记录，按总控安排处理 | `repository-safety.log` |
| `check_repository_safety.py --base HEAD` | PASS，当前文件、工作区和暂存区检查通过；不代表历史提交已清理 | `repository-safety-current.log` |
| 工作区和暂存区 `git diff --check` | PASS | 收尾终端记录 |

三个浏览器门禁串行执行，均只开一个无头浏览器，端口 8768；运行完关闭浏览器和本轮临时服务。没有跑全量 pytest，没有生产部署或真实模型生成声明。

### 本轮重拍与逐张目检

命令为 `rescript_frontend_gate.mjs --capture-only --states=rescript,rescript-adjust,rescript-other,first`。实际视口分别为 1440×900、960×900；每张覆盖页面顶部至底部生成条，输出分别为 1440×2310、960×2800。采集时间为 2026-10-27 00:56:44–00:56:49（台北）。每张均已本人查看，并核验最终 PNG 的 SHA-256。

截图根目录：`~/.photo-content-os/evidence/R278-direct-rescript/frontend/`。

| 状态 | 1440 | 960 | 逐张看图结论 |
| --- | --- | --- | --- |
| `rescript` | [rescript-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-1440.png) | [rescript-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-960.png) | 两张七镜画面旁均为浅灰新占位，没有来源标签；1440 六列对齐，960 表内横向滚动；风格、选项、页底生成条完整。 |
| `rescript-adjust` | [rescript-adjust-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-1440.png) | [rescript-adjust-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-adjust-960.png) | 两张新占位正确；调整说明、第一步解释及生成条对应，960 上下排后内容完整，未发现新裁切。 |
| `rescript-other` | [rescript-other-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-1440.png) | [rescript-other-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/rescript-other-960.png) | 两张新占位正确，第三张风格高亮、大预览和生成条同步；窄屏预览和页底完整。 |
| `first` | [first-1440.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-1440.png) | [first-960.png](~/.photo-content-os/evidence/R278-direct-rescript/frontend/first-960.png) | 两张无图虚线框与画面新占位可辨；其他空列保留「—」；台词、风格与生成操作层级正常，均看到页面底部。 |

本轮 8 次逐块合同（48 块）全部通过。`screenshot-manifest.json` 和 `gallery.html` 已刷新并核验链接：总共 41 张中，只有上述 8 张本轮重拍，另外 33 张明确标为此前保留证据。门禁输出的 41 是合并后的总数。逐张结论、视口、输出尺寸、覆盖范围、时间及哈希见 `repair-11/screenshot-review.json`。

390 宽度额外做了真实旧任务的临时整页和相邻区域诊断目检：全片设计的长「不用」标签限制在卡片里，动作规矩两行、相邻成片检查和镜头列表完整，没有再横向溢出。临时诊断图看过后已删除，不加入交付图库；看图记录留在工具转录，度量和哈希留在 `repair-11/phone-layout.json`。

### 边界与收尾

本轮代码涉及 `direct-storyboard.js`、`direct-view.js`、`direct-rescript.css`、三个前端门禁和 `test_r278_direct_rescript.mjs`；文档只做上述路径清理和本节追加。用户更新的设计稿没有被本轮重写。未改后端 `.py`，未改 `acceptance/`、`agents-results/`；覆盖这些目录及后端源文件的 445 个文件前后哈希一致，见 `protected-preservation.json`。

业务项目 HEAD 仍为 `ffc8c00401dc235c006296ef3f0800c1779846ae`，有本轮前端与文档改动、原有设计稿改动及原有未跟踪 `.venv`；三份清理文档已暂存，其余代码未暂存，本节追加后报告同时有工作区增量。Harness SSOT 未改；其仓库状态现有 79 条记录，原样保留，见 `harness-status.log`。本轮临时目录已删除、8768 已关闭，8769 仍为原 PID 58162，未停止或重启。没有需要补的新接口或稿外文案；历史提交路径清理由总控处理。写完本节即停止。
