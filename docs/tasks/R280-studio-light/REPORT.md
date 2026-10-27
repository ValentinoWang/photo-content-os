# R280 Studio 浅色界面实施报告

日期：2026-10-27。业务 HEAD：`a28a991210b72f0be38aca786ec32c3e93208c3e`。只在任务 worktree 修改，未提交、未推送。

颜色修改、指定前端测试与三个串行门禁已通过；18 张最终截图已逐张打开查看。真实旧任务的「改分镜脚本」及其放大状态保留原有横向溢出，视觉总体验收不能写成全绿；详见第 5 节。H-01、H-02 原文未改，也未代签人工通过。

## 1. 改动文件及边界

| 文件 | 处理 |
| --- | --- |
| `studio/static/styles.css` | 26 个浅色令牌、公共界面字面量、共享前景/侧栏/悬停/媒体令牌、原生浅色控件、提示框阴影 |
| `studio/static/workflow.css` | 交接页字面量、选中状态、轨道、SVG 图标和视频区前景 |
| `studio/static/review.css` | 文字层级、主色控件前景、播放器画布与页面主题隔离 |
| `studio/static/direct.css` | 关键帧/成片底色隔离、主操作白字、错误区说明色 |
| `studio/static/direct-shot-detail.css` | 详情画布与忙碌遮罩保留深色，正文/说明/标记前景使用相应令牌 |
| `studio/static/direct-rescript.css` | 放大画面深色底，锁定状态和小字/占位颜色层级 |
| `studio/static/index.html` | 唯一改动是 `color-scheme: dark → light` 的 meta 值 |
| `tests/test_r280_light.py` | 新增 9 项轻量检查，保护获批令牌、深色字面量、对比度、小字用途及媒体画布隔离 |
| `docs/tasks/R280-studio-light/REPORT.md` | 本报告 |

六份 CSS 的选择器、非颜色声明保持一致，自动比对见仓库外 `color-only.json`。HTML 文案、节点、字号、间距、脚本、后端、旧测试、设计合同、只读需求卡均未改；未新增 `style=`。没有修改主检出、原素材、视频、剪映草稿或 Obsidian 创作内容。

`develop/harness/fullstack-ai-harness.md` 在本稀疏 worktree 中缺失，已读取 Core 同名权威文件及项目适配文件；未编辑 Harness SSOT。任务单没有「规则卡短表」，本轮落实了先红后绿、按前端模块选测、串行单个无头浏览器、真实全页截图及结论范围约束。

## 2. 每个颜色令牌

以下 26 项全部与获批 `design/light.css` 一致，`--fam-cut`、`--fam-snd` 与字体令牌保留。

| 令牌 | 浅色值 |
| --- | --- |
| `--sec-quiet` | `#C9D6D7` |
| `--sec-build` | `#7FB7BD` |
| `--sec-peak` | `#1F8D96` |
| `--bg` | `#F5F6F4` |
| `--panel` | `#FFFFFF` |
| `--panel-2` | `#F7F8F7` |
| `--raise` | `#EEF2F1` |
| `--rule` | `#E4E8E7` |
| `--rule-2` | `#D2D9D8` |
| `--ink` | `#152021` |
| `--ink-2` | `#3A4849` |
| `--ink-3` | `#5F6E6F` |
| `--ink-4` | `#7F8C8D` |
| `--ink-5` | `#A5AFB0` |
| `--ac` | `#1F8D96` |
| `--ac-2` | `#A9D5D9` |
| `--ac-bg` | `#E6F3F4` |
| `--ac-soft` | `#18727A` |
| `--ok` | `#2E7D4B` |
| `--ok-bg` | `#E7F4EC` |
| `--ok-line` | `#BFE0CB` |
| `--warn` | `#9A6B10` |
| `--warn-bg` | `#FBF2DE` |
| `--warn-line` | `#E8CB8C` |
| `--cut` | `#B5412F` |
| `--cut-bg` | `#FCE9E5` |

补充的共享实现令牌均在 `styles.css :root`：`--on-ac:#FFFFFF`（主色上的白字）、`--side-bg:#FBFCFB`、`--ac-hover:#18767E`、`--media-bg:#0D1314`、`--media-ink:#E4EBEB`、`--media-muted:#7D8C8E`。视频画布不再跟随页面底色；媒体文件与画面内容未改。

普通正文、正文次层、次要文字在八种浅色表面的最小对比度分别为 **14.222、8.137、4.542**。`--ink-4` 仅用于占位和 `small` 说明，普通文字与控件原有的 `--ink-4` 改用 `--ink-3`；最弱的有效组合为 **3.062**。这些数字来自 WCAG 相对亮度公式，不代表所有按钮和图标的对比度。

固定设计值 `--ink-4` 对 `--cut-bg` 为 **2.969**，不能同时满足 3。保留获批根令牌，在所有使用错误底色的规则中局部声明 `--ink-4:var(--ink-3)`，将错误区后代说明提升到可读层级；测试逐条验证该保护。没有降低阈值。分镜表格的空占位由 `--ink-5` 改为 `--ink-4`，步骤锁提示由 `--ink-5` 改为 `--ink-3`。

## 3. 每处写死颜色

下表完整列出本次 38 处含旧字面量的声明变化；同一规则的背景、前景分别计数。SVG 行仅列编码颜色，SVG 路径和几何未改。

| 文件 / 选择器 | 属性 | 原值 → 新值 |
| --- | --- | --- |
| `styles.css` · `body` | `background` | `#070C0D` → `var(--bg)` |
| `styles.css` · `.side` | `background` | `#101718` → `var(--side-bg)` |
| `styles.css` · `.brand-mark` | `color` | `#071719` → `var(--on-ac)` |
| `styles.css` · `.nav button:hover,.side-sec button:hover` | `background` | `#141D1E` → `var(--raise)` |
| `styles.css` · `.btn--pri` | `color` | `#08191B` → `var(--on-ac)` |
| `styles.css` · `.btn--pri:hover` | `background` | `#63C3CC` → `var(--ac-hover)` |
| `styles.css` · `.btn--pri:hover` | `color` | `#071719` → `var(--on-ac)` |
| `styles.css` · `.chip` | `background` | `#1A2425` → `var(--raise)` |
| `styles.css` · `.chip--warn` | `background` | `#2A2018` → `var(--warn-bg)` |
| `styles.css` · `.thumb,.media` | `background` | `#1B2627` → `var(--raise)` |
| `styles.css` · `.delete-row` | `border-top` | `1px solid #372b17` → `1px solid var(--warn-line)` |
| `styles.css` · `.tree button[aria-current="true"],.tree button:hover` | `background` | `#16201F` → `var(--raise)` |
| `styles.css` · `.tracks` | `background` | `#0A1112` → `var(--panel-2)` |
| `styles.css` · `.tracks div:nth-child(2) i` | `background` | `#35544A` → `#9FC7C0` |
| `styles.css` · `:where(.settings-layout) .set-nav button:hover,:where(.settings-layout) .set-nav button[aria-current="true"]` | `background` | `#16201F` → `var(--raise)` |
| `styles.css` · `.surface` | `background` | `#070C0D` → `var(--bg)` |
| `styles.css` · `.login-brand` | `background` | `#090F10` → `var(--panel)` |
| `styles.css` · `.wizard-steps li.active b` | `color` | `#071719` → `var(--on-ac)` |
| `styles.css` · `.toast` | `background` | `#172224` → `var(--panel)` |
| `workflow.css` · `.handoff .w-bar` | `fill` | `#3f6e73` → `var(--sec-build)` |
| `workflow.css` · `.handoff .ruler` | `color` | `#46585A` → `var(--ink-5)` |
| `workflow.css` · `.handoff .proto` | `background` | `#000c` → `#ffffffee` |
| `workflow.css` · `.handoff .proto a[aria-current]` | `color` | `#071719` → `var(--on-ac)` |
| `workflow.css` · `.handoff .attn b` | `color` | `#F0C46E` → `var(--warn)` |
| `workflow.css` · `.handoff .done` | `border` | `1px solid #2b4733` → `1px solid var(--ok-line)` |
| `workflow.css` · `.handoff .cs-dot` | `box-shadow` | `0 0 0 3px #7fbb9226` → `0 0 0 3px #2E7D4B26` |
| `workflow.css` · `.handoff .method-cards a[aria-current]` | `background` | `#12343A` → `var(--ac-bg)` |
| `workflow.css` · `.handoff .method-cards a[aria-current] .mc-ico svg` | `stroke` | `#071719` → `var(--on-ac)` |
| `workflow.css` · `.handoff .method-cards a[aria-current] .mc-text b` | `color` | `#CDEEF1` → `var(--ac-soft)` |
| `workflow.css` · `.handoff .method-cards a[aria-current]::after` | `background` | `SVG %23071719` → `SVG %23FFFFFF` |
| `workflow.css` · `.handoff .return-zone::before` | `background` | `SVG %238FC7CD` → `SVG %2318727A` |
| `workflow.css` · `.handoff .software-option:has([aria-pressed=true])` | `background` | `#12343A` → `var(--ac-bg)` |
| `workflow.css` · `.handoff .lg.done` | `background` | `#000` → `var(--rule-2)` |
| `workflow.css` · `.handoff .cue` | `background` | `#1E2A2C` → `var(--panel-2)` |
| `workflow.css` · `.handoff .clips .edit-clip` | `border` | `1px solid #2E5F65aa` → `1px solid var(--ac-2)` |
| `workflow.css` · `.handoff .clips .edit-clip[aria-pressed=true]` | `background` | `#4fb3bd14` → `#1F8D9614` |
| `workflow.css` · `.handoff .applied-cut` | `background` | `repeating-linear-gradient(135deg,#000 0 4px,#0d1314 4px 8px)` → `repeating-linear-gradient(135deg,#D9DFDE 0 4px,#EEF2F1 4px 8px)` |
| `workflow.css` · `.handoff .clips .edit-clip::after` | `box-shadow` | `inset 0 0 0 1px #ffffff22` → `inset 0 0 0 1px #15202122` |

`.toast` 同时按设计稿增加 `0 6px 20px rgba(21,32,33,.12)` 阴影。`.handoff .lg.done` 的黑色图例改用 `--rule-2`，不是视频画面。透明删除/间隙波形色及删除标签描边等未被稿子要求替换的浅色叠加值保留；字面量检查按其在浅底上的合成亮度计算，不把带透明度的浅叠加误判为整块深色。

保留深色的范围：`.handoff .stage` 的 `#05090A`、其播放钮的 `#000a`/`#ffffff33` 保留；相关播放 SVG 使用 `--media-ink`。作品画布、成片播放器、详情画布、关键帧容器、放大浮层中的图片/视频用媒体专用令牌，周边表单和面板使用浅色令牌。`review.css`、`direct*.css` 仍无新增颜色字面量。

## 4. 测试与门禁

证据根目录：`~/.photo-content-os/evidence/R280-studio-light/`。日志位于其 `logs/`。

| 检查 | 结果 | 日志 |
| --- | --- | --- |
| 先新增 R280 测试，在改产品代码前执行 | **6 failed / 3 passed**：令牌、两份样式的字面量、次要文字对比度、小字用途、媒体隔离失败 | `red.log` |
| 最终版 R280 测试对原 HEAD 的独立临时副本复验 | **7 failed / 2 passed**：包含错误底说明色的新增检查，证明最终测试仍能拦住旧实现 | `final-tests-on-head-red.log` |
| R280 测试，修改后 | **9 passed** | `green.log` |
| R276/R277/R278/R282/R283 五份 `.mjs` | **全部 PASS** | `node-r276.log` 至 `node-r283.log`（R278 为 `node-r278.log`） |
| 五份前端 pytest + R280 | **25 passed** | `frontend-pytest.log` |
| R276 `frontend_gate.mjs --checks-only` | **PASS，26 次合同比较**，公式与真实挂载交互通过 | `r276-gate.log` |
| R277 `revision_frontend_gate.mjs --checks-only` | **PASS，42/42 合同**，详情/版本/日志/轮询/标记避让通过 | `r277-gate.log` |
| R278/R282/R283 `rescript_frontend_gate.mjs --checks-only` | **PASS，52 次合同比较**，三代挂载交互通过 | `r278-r282-r283-gate-rerun.log` |
| `scripts/check_repository_safety.py --base HEAD` | **PASS** | `repository-safety.log` |
| `git diff --check` | **PASS** | 终端工具记录 |

共用门禁首次失败在原有 `testZoomAndClips` 的视频错误回退即时计数断言（`0 !== 1`，`rescript_frontend_gate.mjs:159`）。未改产品 JS、门禁或原断言，原样串行重跑后完整通过；首轮失败日志保留为 `r278-r282-r283-gate.log`。本轮仅确认该失败为单次出现，未把它表述为已定位或已修复的不稳定性。

实际测试命令：

```sh
node tests/test_r276_direct_frontend.mjs
node tests/test_r277_frontend.mjs
node tests/test_r278_direct_rescript.mjs
node tests/test_r282_frontend.mjs
node tests/test_r283_frontend.mjs
.venv/bin/python -m pytest -q tests/test_r280_light.py tests/test_r276_direct_frontend.py tests/test_r277_frontend.py tests/test_r278_direct_frontend.py tests/test_r282_frontend.py tests/test_r283_frontend.py
node scripts/direct_video/frontend_gate.mjs --checks-only
node scripts/direct_video/revision_frontend_gate.mjs --checks-only
node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
.venv/bin/python scripts/check_repository_safety.py --base HEAD
```

环境沿用 R278 报告第 7 节：`HARNESS_CORE`、`UI_COPY_QUALITY_CHECKER` 指向 Core；Playwright 模块沿用指定模块；`VIDEO_RENDER_BROWSER` 固定为 `chromium_headless_shell-1228` 下的可执行文件；`DIRECT_GATE_PORT=8768`；`R277_SOURCE_STATE=~/.photo-content-os/studio-r278`。`R278_DESIGN_ROOT` 使用本 worktree 合同，`R278_DESIGN_MEDIA_ROOT` 只读主检出的设计图片。三个证据输出变量均改到 R280 子目录，未覆盖旧任务证据。未跑全量 pytest。

## 5. 最终截图与逐张看图结论

截图在仓库外 `~/.photo-content-os/evidence/R280-studio-light/screenshots/`。索引为该证据根目录的 `gallery.html`，全部 36 个图片/链接引用解析到这 18 张最终文件，18/18 SHA-256 核验一致；详见 `gallery-verification.json`。每张 PNG 均经 `view_image` 逐张打开，包括底部；说明、小字、相邻区域、长文案、展开规则列表及视频浮层均已查看。

实际视口均高 900，宽度为下表值，使用 `zh-CN`、`Asia/Taipei`、本地回退字体和减少动态效果。截图通过滚动文档到页底后采集完整渲染页；详情展开图只展开口播和规则检查，代码保持折叠，没有将代码面板的一屏冒充完整代码截图。

截图时间为 **2026-10-27 15:17:25–15:21:33（台北）**。每图精确时间、真实 route、浏览器版本、覆盖范围、输出尺寸和完整哈希记录于 `screenshot-manifest.json`。

| 截图 | 实际视口 | 输出尺寸 | 本人看图结论 |
| --- | --- | --- | --- |
| `screenshots/home-1440.png` | 1440×900 | 1440×900 | 浅灰画布、白卡、选中导航和青底白字主操作清楚；顶部待办和页底本机能力完整。 |
| `screenshots/inbox-1440.png` | 1440×900 | 1440×900 | 真实无待整理素材状态；说明、计数、主次按钮完整，无深色残块。 |
| `screenshots/projects-1440.png` | 1440×900 | 1440×900 | 三个项目分组、作品计数和相邻缩略图完整；照片保持原样。 |
| `screenshots/project-1440.png` | 1440×900 | 1440×900 | 其他作品的八张文字卡与页底完整；浅色层级清楚。 |
| `screenshots/piece-vlog-1440.png` | 1440×900 | 1440×900 | 五步流程、真实无素材状态和开始按钮为浅色；未触发生成。 |
| `screenshots/piece-script-1440.png` | 1440×900 | 1440×900 | 六步流程、文档卡、右栏和页底双轨时间线均浅色；文字与轨道区分清楚。 |
| `screenshots/piece-direct-1440.png` | 1440×900 | 1440×1500 | 步骤、成片检查、全片设计和七镜卡片清楚；视频和缩略图保持深色；页底完整。 |
| `screenshots/library-1440.png` | 1440×900 | 1440×900 | 真实空库状态；说明和主次操作清楚，未注入演示数据。 |
| `screenshots/music-1440.png` | 1440×900 | 1440×1066 | 三首歌曲、波形、筛选、标签及右栏至导入时间完整；无深色界面残块。 |
| `screenshots/settings-1440.png` | 1440×900 | 1440×900 | 剪辑软件未连接与可用状态均可读；设置导航、列表及重新检查按钮完整。 |
| `screenshots/shot02-1440.png` | 1440×900 | 1440×2228 | 第02镜选中、详情输入框、禁用按钮和折叠项清楚；关键帧保持原样；详情底部完整。 |
| `screenshots/shot02-expanded-1440.png` | 1440×900 | 1440×2330 | 口播和规则检查展开，层级与嵌套列表可读；代码保持折叠；详情页底完整。 |
| `screenshots/rescript-1440.png` | 1440×900 | 1554×2575 | 七镜表格、视频风格、样例、选项和生成条为浅色，七张画面保持原样；旧任务信息列存在原有横向溢出。 |
| `screenshots/rescript-zoom-1440.png` | 1440×900 | 1554×2575 | 第02镜放大浮层为浅色边框与标题，媒体和原生播放区仍为深色；相邻表格、风格区及页底完整；同一原有横向溢出。 |
| `screenshots/piece-direct-960.png` | 960×900 | 960×2317 | 步骤、成片检查、全片设计和七镜卡片清楚；视频和缩略图保持深色；页底完整。 实际960宽度，页面无横向溢出，七镜换行和详情两栏完整。 |
| `screenshots/shot02-960.png` | 960×900 | 960×3046 | 第02镜选中、详情输入框、禁用按钮和折叠项清楚；关键帧保持原样；详情底部完整。 实际960宽度，页面无横向溢出，七镜换行和详情两栏完整。 |
| `screenshots/piece-direct-390.png` | 390×900 | 390×2491 | 步骤、成片检查、全片设计和七镜卡片清楚；视频和缩略图保持深色；页底完整。 实际390宽度，页面无横向溢出，详情上下排列；沿用既有字号与截断。 |
| `screenshots/shot02-390.png` | 390×900 | 390×3645 | 第02镜选中、详情输入框、禁用按钮和折叠项清楚；关键帧保持原样；详情底部完整。 实际390宽度，页面无横向溢出，详情上下排列；沿用既有字号与截断。 |

**保留的原有布局问题：** 真实旧任务在 1440 视口进入「改分镜脚本」后，右侧 `.dv-sw-meta` 的旧设计信息列扩展到 x=1554。通过同一浏览器临时拦截 CSS 为原 HEAD 样式测量，原版和浅色版 `documentElement.scrollWidth` 都是 **1554**。因此两张 `rescript` 图真实输出宽度为 1554，没有缩放、裁掉溢出或假报 1440。两张记录为 `color_review_result=PASS`、`layout_review_result=KNOWN_BASELINE_OVERFLOW`、总体 `PARTIAL`；其他 16 张为 PASS。本任务限定只改颜色，未擅自修改该布局；是否另开布局修复交总控决定。

截图来自本 worktree 的真实 Studio、临时 APFS 克隆状态，接口未 mock；唯一 CSS 拦截仅用于上述原版宽度诊断，不用于交付图片。素材根通过 `runtime_paths.local_media_root()` 解析，未从软件根推导。整理台和素材库为空是源状态的真实空态；没有为了截图注入内容。未调用收费模型、未生成新成片，不代表生产部署或真人验收。

## 6. 稿外内容、状态与停止点

稿外新增的可见文字/元素：**无**。实现中补充了媒体专用令牌、错误底说明色保护、两处编码 SVG 颜色及黑色图例，均为落实浅色和视频保色要求，没有改动结构。额外拍了两张 390 手机视口、项目详情、详情展开和画面放大状态，用于共享主题的影响检查。原有布局溢出和首轮门禁失败如实列出，未放宽合同、断言或阈值。

开场人工日志中，与本轮采样表面交叉的 R276、R277、R278、R282、R283、R220、R223、R210 均仍为 PENDING；本轮不作人工 PASS、READY 或发布结论，未改验收卡和日志。没有创建或实质更新声明的 SSOT 开发包，本报告是任务实施记录，不触发 SSOT 快照。

临时状态目录与自有无头浏览器均已关闭清理，8768 已无监听。原有 8766/8767/8769 的监听 PID 分别为 41998/18772/45249，前后完全一致；未触碰这些服务，8765 前后均无监听。磁盘开工约 8.3 GiB，收尾约 8.0 GiB，全程高于 3 GiB。源状态 167 份 JSON 前后哈希完全一致，见 `source-preservation.json`；未声称这是全部原始媒体的逐字节审计。

业务 Git：HEAD 未变；7 个产品文件有工作区修改，新增 R280 测试和本报告；开场已有未跟踪的 `.venv`、只读需求卡和设计任务目录继续保留，未暂存、未提交、未推送。详见 `logs/business-before.log`、`logs/business-final.log`（最终记录采于写报告之前）。

Harness SSOT Git：本轮未修改，开工与收尾 `git status --porcelain` 完全相同，均为 99 条已有状态记录，见 `logs/harness-before.log`、`logs/harness-final.log`。

本报告写完即停止。

## 修横向溢出

2026-10-27，根据总控看图后的追加要求修复。本节取代前文「保留原有布局溢出」的结论；前文是上轮历史记录，旧的两张溢出图及其清单已备份至证据根目录下 `overflow-repair/before/`。当前两宽均无整页横向溢出。

### 样式与断言

本轮产品修改仅在 `studio/static/direct-rescript.css`：
.dv-sw-meta 的 `min-width:0` 本来已经存在，真正撑宽的是内部 `dl` 的自动最小网格列。现将它明确为 `grid-template-columns:minmax(0,1fr)` 并加 `min-width:0`，同时给网格子项和 `dd` 加 `min-width:0`，使旧设计文字受说明列宽度约束。

仅对 `.dv-sw-meta dd.dv-legacy-motion` 将行数上限设为 3，并允许超长词断行。继续使用已有的 `-webkit-box` / `overflow:hidden` 省略机制；作品全片设计行原有的两行限制保留。原有 `.dv-nots span` 的 `max-width:min(260px,100%)`、单行与省略号规则无需改写，说明列变为有界后即正确生效。新任务短白话不带 `dv-legacy-motion`，未施加三行截断；R283 九风格、短文案与390宽度的既有检查通过。

未改产品 JS、文案、DOM 结构、颜色、字号或间距。说明列中的老原话和标签原本没有 `title`，按本轮限制未增加；其他地方已有的 `title` 保留，完整原话仍在 DOM 和来源记录中。

在 `scripts/direct_video/rescript_frontend_gate.mjs` 的真实旧任务最差首屏检查中增加实际视口与 `documentElement.scrollWidth` 断言，1440、960 都执行。此前 `--checks-only` 会跳过真实旧任务，现在默认也覆盖它，合同比较从52次增加到54次。两宽度量落在每次运行的 `real-worst-layout.json`；失败会指出实际宽度、目标视口和约束说明列的修复方向。原合同、原断言和测试阈值未放宽。

### 先红后绿与复验

本轮证据目录：`~/.photo-content-os/evidence/R280-studio-light/overflow-repair/`。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 先加断言，保持修复前样式执行真实旧任务检查 | **预期失败**：1440视口为1554；960视口为960。失败明确为 `1554 > viewport 1440` | `red.log`、`red/real-worst-layout.json` |
| 样式修改后，同一真实旧任务检查 | **PASS**：1440→1440，960→960，两次合同通过，无截图 | `green-targeted.log`、`green/real-worst-layout.json` |
| 完整 `rescript_frontend_gate.mjs --checks-only` | **PASS，54/54合同比较**；R278/R282/R283挂载交互、既有390检查和新增两宽旧任务检查全部通过，无截图 | `full-gate.log`、`full-gate/real-worst-layout.json` |
| R278/R282/R283三份前端 `.mjs` | **全部PASS** | `node-r278.log`、`node-r282.log`、`node-r283.log` |
| R278/R282/R283前端 pytest，加上R280颜色回归 | **15 passed** | `frontend-pytest.log` |
| 仓库安全 `--base HEAD` | **PASS** | `repository-safety.log` |
| `git diff --check` | **PASS** | 本轮终端工具记录 |

红/绿的聚焦命令均为 `node scripts/direct_video/rescript_frontend_gate.mjs --checks-only --capture-only --states=real-worst-rescript`，用于只跑这两个真实旧任务状态，跳过其他交互及截图；之后另行完整执行了 `--checks-only`。前端 pytest 实际选中 `test_r278_direct_frontend.py`、`test_r282_frontend.py`、`test_r283_frontend.py`、`test_r280_light.py`。未跑全量 pytest，也未重复拍摄其他页面。

### 三张最终截图

本轮只拍以下三张，均使用本地真实 Studio、APFS克隆状态、原媒体只读、固定1228无头浏览器；接口与CSS没有mock。依次在8768串行执行，实际视口高900，完整滚动至页底后捕获。字体为本地回退，区域设置 `zh-CN`，时区 `Asia/Taipei`。

| 文件（证据根目录下） | 实际视口 | 输出尺寸 | 看图与实测结论 |
| --- | --- | --- | --- |
| `screenshots/rescript-1440.png` | 1440×900 | 1440×2575 | 逐张查看整页：七镜、视频风格右半列、相邻选项及生成条完整；老原话三行省略，标签单行省略且不超说明列，页面宽1440，无横向溢出。 |
| `screenshots/rescript-zoom-1440.png` | 1440×900 | 1440×2575 | 逐张查看整页：第02镜放大浮层标题和关闭按钮完整，画面/播放区保持深色；说明列、相邻表格与页底完整，页面宽1440，无横向溢出。 |
| `screenshots/rescript-960.png` | 960×900 | 960×3173 | 逐张查看整页：视频风格上下排，说明列老原话两行，标签单行省略；七镜和页底生成条完整，页面宽960，无横向溢出。分镜表格保留已有内部横向滚动，未把它变成整页滚动。 |

三张均已本人用 `view_image` 逐张查看，覆盖页面顶部、说明列、相邻区域及页底。1440下说明列宽 **252px**，老原话高度约 **3行**，最长标签 **252px**；960下说明列宽 **488px**，老原话约 **2行**，最长标签 **260px**。标签均为 `nowrap`、`overflow:hidden`、`text-overflow:ellipsis`，不超过各自说明列。960表格本身既有的内部横向滚动保留，整页宽度仍为960。

采集时间为 **2026-10-27 15:34:20–15:34:24（台北）**；完整路由、浏览器版本、覆盖范围、度量、逐图结论和SHA-256见 `overflow-repair/screenshot-manifest.json`。全图索引 `gallery.html` 和根 `screenshot-manifest.json` 已同步为 **19张=16张上轮原样保留+3张本轮采集**，不是19张重拍；19份文件哈希与38个图库引用全部核验成功。原来两张1554宽图的活动链接已换成最终1440宽图，旧图仅留在前述备份目录。

### 边界与收尾

本轮增量只有样式文件、既有门禁脚本和本报告追加段。未增加可见文字/元素，未编辑需求卡、人工验收记录、设计合同或素材；源状态167份JSON前后哈希一致，见 `source-preservation.json`。本轮机器与截图检查通过不代替人工签署，也不代表生产部署。

固定1228无头浏览器每次只有一个，门禁、截图串行完成；浏览器、临时状态与8768服务均已关闭清理。8766/8767/8769仍为开场原PID，其他Studio服务未动。磁盘收尾约7.0 GiB，高于3 GiB停止线。

业务Git：HEAD仍为 `a28a991210b72f0be38aca786ec32c3e93208c3e`，保留上轮未提交改动并增加本节所列修复，未暂存、未提交、未推送。Harness SSOT：本轮未改，开工与收尾状态完全一致，均为99条已有记录，见 `overflow-repair/harness-before.log`、`overflow-repair/harness-final.log`。

本节写完即停止。
