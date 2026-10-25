# R276 脚本直出 · REPORT-F1

## 1. 和设计稿哪里不一样

本轮只实施 F1，未进入 F2。十状态 × 两宽的设计合同全部通过；F1 自动交互与指定回归通过。**不报告为 READY**：Core 文案门禁仍被原稿占位文案拦住，另有接口缺口、无声分支文案待总控决定，以及全仓环境/同步失败。没有修改设计稿或批准表来绕过检查。

下面的对照图左侧是获批稿，右侧是真实 Studio 的夹具页面；只是并排比较图，独立原图和完整尺寸在画廊及清单中。

[完整截图画廊](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/index.html) · [27 张截图的尺寸、时间、覆盖范围与 SHA-256](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/screenshot-manifest.json)

| 状态 | 差异与处理 | 1440 对照 | 960 对照 |
| --- | --- | --- | --- |
| empty | 输入首屏按稿实现；保留获批占位文案，存在 Core 空格检查冲突（见第 6 节）。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-empty-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-empty-960.png) |
| filled | 镜数、逐镜时长与合计来自当前口播；截图使用真实设计稿的七段口播，文本框恢复到顶部。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-filled-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-filled-960.png) |
| unavailable | 通过建任务返回 claude_cli_unavailable 复现；黄色提醒、模型黄点、生成禁用。390 宽模型另起一行，避免挤碎作品标题。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-unavailable-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-unavailable-960.png) |
| designing | 未放无接口的「停下来」；零进度按公式为 0%，未照稿编造 2%。耗时由夹具 createdAt 实算。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-designing-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-designing-960.png) |
| writing | 按任务单的默认选中优先级选自动重写的第 06 镜，稿中选的是第 01 镜。投影无开始写时间，未显示「已写 m:ss」。标题据实际 writing 三镜生成。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-writing-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-writing-960.png) |
| failed-shot | 红色提醒直接显示 checks.errors 的中文原因；失败详情没有画面，不声明动画时长检查通过。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-failed-shot-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-failed-shot-960.png) |
| ready | 七镜、详情、上传与无声合成入口按稿；修改意见为空时重写按钮禁用。耗时和提醒数实时计算。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-ready-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-ready-960.png) |
| rewriting | 保留第 03 镜旧关键帧；状态、选中、禁用输入按投影；attempts 直接显示已发生次数，不提前加一。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-rewriting-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-rewriting-960.png) |
| composing | 顺序为合成状态→全片设计→胶片；无实时已拼帧数或 ETA，只显示「合成中」。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-composing-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-composing-960.png) |
| done | 顺序为播放器→全片设计→胶片；真实 video 从 0:00 开始；省略无接口的访达按钮与无字段的烧录字幕断言。测试视频是合成的静态测试片，不是后端真出片。 | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-done-1440.png) | [对照](~/.photo-content-os/evidence/R276-direct-video-opus/frontend/compare-done-960.png) |

全片设计里的字号和动作说明目前继承 Studio 正文字色，相比稿的 muted 文字略重；未声明像素级一致，由总控审图裁定。关键帧夹具来自获批稿的七镜渲染截图，详情里放大后的清晰度不代表真实后端 JPEG 质量。

## 2. 改了哪些文件

仅改任务单第 0 节白名单及用户明确要求的本汇报：

| 文件 | 内容 |
| --- | --- |
| `studio/static/direct-view.js` | 页面、中文失败映射、公式、按行预览、分镜导入、建任务、WAV 上传、合成、播放器、轮询与离页失效。 |
| `studio/static/direct.css` | 照稿布局和 Studio 语义令牌；七/四/三列；减少动态效果；手机标题/模型分行；常见类只作用在直出页。 |
| `studio/static/direct-shot-detail.js` | 唯一导出 renderShotDetail；关键帧、事实、检查、修改意见、重写、延迟读代码；按指定字段判断重画，保留意见、焦点与光标选区。 |
| `studio/static/direct-shot-detail.css` | 独立详情布局；其检查样式不会覆盖成片检查，成片样式归 direct.css。 |
| `studio/static/review-view.js` | 最小改动：导入/初始化、第三分页与 localStorage 允许值、ptab=direct 分支、离页 stop。 |
| `studio/static/index.html` | 仅增加两个 CSS 链接。 |
| `tests/test_r276_direct_frontend.py` | 5 项静态/模块边界/公式入口检查。 |
| `tests/test_r276_direct_frontend.mjs` | 公式与失败翻译的正/负例、十状态夹具定义、浏览器详情重画检查。 |
| `scripts/direct_video/frontend_gate.mjs` | 真实 Studio 8767 + 临时状态/素材目录，Playwright 接口拦截、整页截图、Core 清点及合同检查、交互验证。 |
| `docs/tasks/R276-direct-video-opus/REPORT-F1.md` | 本汇报。 |

没有编辑后端、schema、已有测试、主目录、Harness SSOT 或真实媒体；没有提交、推送、创建 worktree、操作 8765/8766、终止他人进程。

**夹具目录边界冲突：** 第 5 节要求新增 `tests/fixtures/r276-direct/`，但第 0 节没有授权该目录，用户又强调只许改第 0 节文件。因此未创建该目录；夹具定义放在获准的新测试 `.mjs` 中，运行后输出到仓库外 `frontend/fixtures/`。其中 unavailable 的 latest 为 job:null，通过建任务错误复现；额外保存 `unavailable-create-error.json`。读取失败另有 read-error 响应分支。

## 3. 截图与亲自复核

- 目录：`~/.photo-content-os/evidence/R276-direct-video-opus/frontend/`。
- 真实路由：`http://127.0.0.1:8767/#view=piece&piece=fixture-piece&ptab=direct`；仅 F1 接口拦截夹具，不冒充真实后端任务。
- 1440×900、960×900：十设计状态 + 读不到任务，共 22 张整页截图。
- 390×900：还没生成、写到一半、成片、调不通、读不到任务，再加 5 张，共 27 张。
- 实测 viewport；遍历页面滚动到底后 fullPage 截图，核对 PNG 输出尺寸覆盖 document.scrollHeight。该页面采用文档滚动；七行清单完整展示，长口播仍保留文本框本来的编辑滚动。
- 最后一轮视觉改动后重新运行门禁，逐张打开 27 张最终图，查看主体和底部；修复了详情响应式被加载顺序覆盖、手机成片检查数字竖排、播放器右边距不足和长模型名挤压作品标题。
- 已保存个人整页判断到 `visual-review-notes.json`，并将姓名/范围/时间/逐图 SHA-256 绑定到 screenshot-manifest；不是用户验收或总控放行。
- 图片字体模式为 fallback-local；不依赖字体 CDN 成功与否。旧的 *.overflow.* 是失败轮次调试证据，不在最终画廊/通过截图清单里。
- 画廊 27 个原图入口和 20 个对照入口均已做文件存在检查，清单原图哈希全部复核。

## 4. 合同检查与测试结果

| 检查/命令 | 结果 |
| --- | --- |
| `node scripts/direct_video/frontend_gate.mjs` | PASS：20 次 Core 设计合同检查、27 张整页截图、公式和浏览器交互；浏览器 pageerror 为 0。 |
| Core `collect_design_inventory.js` + `check_design_contract.py check --contract <设计稿>/contract.json --inventory ...` | 十状态 × 1440/960 全部 PASS；未使用 approved-extras，未修改合同。read-error 不在原十状态合同中，不虚报为合同通过。 |
| `node tests/test_r276_direct_frontend.mjs` | PASS：Unicode 字符计数、按行切分、实测优先、合计取整、完成数、耗时、单镜写好时间、轮询边界、六个失败码及未知码、选中优先级、累计跳镜秒数、关键帧版本。 |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_frontend.py tests/test_p2_frontend_contract.py tests/test_r220_number_formulas.py tests/test_checklist_remediation_static.py` | 12 passed（含本轮新增 5 项），指定现有前端回归未红。 |
| `node tests/test_r220_number_formulas.mjs` | PASS。 |
| `node --check` 三个 JS 模块 + `git diff --check` | PASS。 |
| `bash scripts/check_runtime_contract.sh` | PASS。 |
| `validate_music_analysis_registry.py`（设置 Core checker） | PASS：126 ids；121 copy entries。 |
| `check_repository_safety.py --base origin/main` | PASS。 |
| `check_obsidian_doc_sync.py`、`check_outline_contract.py .` | FAIL：三个配对文档报 source-newer-than-target；相关 README/执行文档本轮均未改，未越界同步。 |
| `.venv/bin/python -m pytest -q tests` | 898 passed、34 skipped、9 failed、6 errors、2003 subtests passed。详见下文。 |
| `validate_content_os_task.py --help`、`validate_jianying_draft.py --help` | PASS。 |
| Core `check_ui_copy_quality.py` 扫两个新增 JS | FAIL：1 条原稿占位文案的 mixed-script-spacing，详见第 6 节。 |

浏览器交互覆盖：空稿不能生成、创建失败变调不通、分镜文件导入、风格提交、建任务前暂存 WAV 并在建好后原样上传（audio/wav + CSRF）、展开时才读取代码、详情重画保留输入及焦点/光标、重写后其他六镜的 DOM 关键帧地址和写好时间不变、用户选中镜跨轮询保持、2 秒轮询、ready 后推进 61 秒无新增轮询、离页后推进 61 秒无新增轮询、成片真实 video 的 currentTime 跳镜和重新合成。媒体验证夹具支持 Range；不以假时钟或界面假数字代替播放器定位。

全仓测试在实现过程中执行；最后一次视觉修正后重跑了定向测试和浏览器门禁，没有重复全仓。全仓失败：1 项是 Obsidian 同步；8 项失败和 6 项 setup error 均在既有字幕/视频 FFmpeg 调用退出码 8 处失败。当前 FFmpeg 滤镜清单确认没有 drawtext、subtitles、ass（`ffmpeg-filters.log`）。未改这些文件或削弱断言；未在基线 checkout 重跑全套，因此不把全仓说成通过，也不把所有失败都认定为已完成的回归归因。日志为 `pytest-full.log`。

运行同步与全仓命令时显式使用自媒体 Obsidian 根；音乐门禁和全仓测试设置了 Core `UI_COPY_QUALITY_CHECKER`。第一次未设 checker 的音乐检查失败后，按要求补齐环境再运行并通过，保留的是有效重跑日志。

## 5. 需要的接口

| 缺口 | 当前处理 |
| --- | --- |
| 单镜最近开始写的时间，例如 writingStartedAt | 真实 SHOT_FIELDS 没有这个字段；仅显示正在写/重写状态，不编造「已写 m:ss」。 |
| 合成实时已拼帧数、总帧数、预计剩余时间 | 当前 output.frames 是结果字段，没有进度语义；只显示「合成中」。 |
| 在访达中显示成片目录 | 没有接口；按钮不放，不弹假提示。 |
| 停止任务 | 没有 cancel/stop 接口；未放「停下来」。 |
| 中断镜的一键重试语义 | 目前只有要求 1–200 字 instruction 的 rewrite 接口；卡片显示「中断了 / 重试」，点击选择这一镜后可在详情填意见重写。没有擅造恢复接口或自动重跑；若要求一键恢复原尝试，需要后端明确契约。 |

按实际 `studio/direct_video.py` 字段实现；未新增任何后端字段。代码 text/plain 和 WAV 二进制请求没有使用会 JSON 化文件的现有 api()；在新增模块内用同源 fetch，写请求仍从 bootstrap 获取 CSRF。

## 6. 需要新文案

1. **阻塞 Core 文案门禁：** 原稿口播 placeholder 是「清华AI体育博主」。Core 判定「华A」缺少中英文空格，建议改为「清华 AI 体育博主」。当前严格保留获批稿，未自行加空格、未放宽 checker、未改合同。需总控先改设计与合同，再同步实现。具体诊断见 `copy-quality/ui-copy-quality.json`。
2. **无声分支缺稿：** 无声预览合成时，获批 composing 文案仍是「七镜画面按配音逐帧拼起来，再检查一遍。」建议批准无声分支为「七镜画面逐帧拼起来，再检查一遍。」当前没有自行替换。
3. **无声成片检查缺稿：** 没有声音时，声音/配音检查读不到数值，当前显示批准的未知状态说明及黄色提示，不声明通过。建议补充无声场景的「无声预览，不检查声音」等不适用文案与规则后再实现。
4. 「读不到这件作品的直出任务 / 重试」来自前端任务单第 2.2 条，已经实现并截图；原 contract.json 没有 read-error 状态。请总控将这个已明确要求的状态补进设计合同；本轮未私改权威合同。

## 7. 稿外元素

- 十个现有状态没有新增设计编号，20 次编号/文案检查均通过；没有 iframe 执行模型代码、无效访达按钮、虚构 ETA 或隐藏审批外新文案。
- read-error 是任务单明确要求的额外错误分支，复用现有 attention 组件；原十状态合同不含此分支，单独截图并验证不显示输入首屏。
- 390 宽对顶栏和三步标签做必要响应式排布；1440/960 保持稿的布局，未修改共享 token 或其他页面主题。

## 8. 交接与停止状态

机器证据只覆盖本地夹具前端。F2 的真实任务「写到一半 / 七镜写好 / 成片」三屏未做；H-01–H-03 未代签，未宣布整体验收通过。
开场读取 human-acceptance-log.json；R220 的 studio.navigation / studio.shot-review PENDING 与本轮入口相交，仍保持原状。由于文案门禁及接口缺口未绿，也受文件白名单限制，未生成或修改人工 handoff、清单和签署记录。本汇报不是 SSOT 开发包，未创建 ssot-archive 声明或第二份 Obsidian 权威。
业务项目 git：本轮 9 个实现/测试文件及本汇报未提交；开场已有后端线程的 server/api/schema/direct_video 等改动继续保留。完整状态见外部 `business-git-status.txt`。
Harness SSOT git：本轮没有修改；仓库原先存在 acceptance/requests、tools/console 等未提交改动，未操作它们。完整状态见外部 `harness-git-status.txt`。
本线程只停止自己启动的 8767 临时 Studio，临时状态/素材目录已删除；8765 和 8766 未动。到此停止，不开始 F2。
