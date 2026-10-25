# R276 脚本直出 · REPORT-F2

F2 已完成，停在本段。13 状态 × 两宽合同检查通过；真实任务的四个阶段及播放状态已截图、清点并逐张看完。定向测试 80 项通过。全仓仍有下述环境/同步失败，因此不报告整项目 READY，不代签 H-01–H-03。

[最终截图画廊](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/index.html) · [最终清单：43 张截图、38 次合同检查、尺寸/时间/覆盖范围/SHA-256](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/final-manifest.json) · [逐图复核记录](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/visual-review-notes.json)

## 1. 实现与边界

本轮在 worktree 内改动以下文件，未编辑主目录、后端、schema 或已有测试：

| 文件 | F2 变化 |
| --- | --- |
| `studio/static/direct-view.js` | 占位例句改为「清华 AI 体育博主」；接入 read-error、composing-silent、done-silent；合成摘要按新稿；接入 writingStartedAt；中断卡直接空意见重试；适配真实黑帧检查的 pass/fail 和初次 attempts=1。 |
| `studio/static/direct-shot-detail.js` | failed/interrupted 允许空意见，显示「重试这一镜」；填写意见时显示通常重写按钮；其他状态仍要求 1–200 字。保留意见、焦点、选区与延迟读代码行为。 |
| `studio/static/direct.css` | 无声声音检查使用中性的「–」；镜卡支持内部独立重试按钮，并保留键盘选镜。 |
| `tests/test_r276_direct_frontend.mjs` | 13 状态夹具构造、写镜耗时与空意见边界、真实 attempts/blackFrames 形状、详情重画和提醒显示检查。 |
| `tests/test_r276_direct_frontend.py` | 增加夹具字段、无声分支与构图提醒回归检查，合计 6 项。 |
| `tests/fixtures/r276-direct/` | 按本轮批准建立 13 份 JSON 夹具，以及仅包含两条已批准重试文字的 approved-extras.json。 |
| `scripts/direct_video/frontend_gate.mjs` | 使用文件夹具；13 状态合同与交互检查；真实状态复制、真任务生成、实际视频播放、清点、整页截图、原状态哈希核验和临时服务清理。 |
| `docs/tasks/R276-direct-video-opus/REPORT-F2.md` | 本汇报。 |

F1 的 `direct-shot-detail.css`、分页路由和两个样式表链接保留，本轮未继续改动。`layout_bottom_gap` 没有增加特例，按 warnings 中的中文 message 显示普通提醒；夹具 ready 状态覆盖该代码。

写镜耗时按「现在 − writingStartedAt」计算，随 2 秒轮询更新；缺失时间时不编造秒数。真实后端初次写作 attempts 已是 1，只有大于 1 才按自动重写展示。真实 output.checks.blackFrames 是 pass/fail，现按真实字段显示绿色「0 处」，不再误报未知。

无声合成显示「七镜画面逐帧拼起来，再检查一遍。」和「N 镜 · 无声预览 · 约 m:ss」；带声合成只显示「N 镜 · 配音 m:ss」。无声完成显示「无声预览出来了」、信息行「无声预览 m:ss」、中性的「无声预览，不检查声音」，标题旁有「上传配音…」「重新合成」。无帧数/剩余时间的合成进度，无「停下来」「在访达中显示」。

## 2. 真实任务与截图

真实路由为 `http://127.0.0.1:8767/#view=piece&piece=project-fc6baa3294&ptab=direct`，作品「断更一年，我拆了四句话」。从 worktree 启动 Studio，真实 API 未拦截；只拦字体 CDN，字体模式为 fallback-local。

使用 `~/.photo-content-os/studio-r276/` 的独立临时复制：第一份保留最新七镜任务，另一份只在复制品里去掉该七镜目录，以读取十镜带声任务。使用后端相同环境变量：

```text
VIDEO_RENDER_PLAYWRIGHT_MODULE=~/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js
VIDEO_RENDER_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell
```

| 真实状态 | 任务与观察 | 1440 × 900 viewport | 960 × 900 viewport |
| --- | --- | --- | --- |
| 无声预览出来了 | `dv_0e184e961bd14ac084c67411`，7 镜，4284 帧，142.8 秒，revision 2；声音检查为中性。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-silent-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-silent-960.png) |
| 成片出来了 | `dv_0d6e5d7cd39741d6abeadb19`，10 镜，1855 帧，61.833 秒，revision 1；四项检查通过。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-960.png) |
| 写到一半 | 真新任务 `dv_f3f85eaec4ee431587229614`；前三镜已渲染，第 04–06 镜正在写，第 07 镜等待。卡上显示真实已写耗时。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/real-writing-final-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/real-writing-final-960.png) |
| 七镜都写好 | 同一新任务，全部 rendered、attempts=1、posterRevision=1，五条提醒；从创建到 ready 约 8:26，没有调用失败重试。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/real-ready-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/real-ready-960.png) |
| 无声预览播放中 | 真的点击播放，currentTime 超过 2 秒、paused=false，实际视频 1080×1920。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-silent-playing-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-silent-playing-960.png) |
| 带声成片播放中 | 真的点击播放，currentTime 超过 2 秒、paused=false，实际视频 1080×1920。 | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-playing-1440.png) | [整页](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/output-final/real-done-playing-960.png) |

新任务通过实际 POST 创建，口播是批准稿 shots-data.js 的七句，style 为空；使用真实本机 Claude，不是回放或假数据。创建、轮询时间线和 ready 投影保存在外部证据目录 `real/`。新任务只存在临时状态中，按要求随临时目录删除，不改原任务目录。

初次整批真实截图过早截到 writing：当时首镜尚无关键帧，合同的详情区域检查有 2 次失败。因此那一轮命令最终非零退出，不能说整批通过。随后在同一真实任务 3/7 时重新截取 writing，两宽均通过；输出页也在最终前端修改后重拍。最终清单仅采用 writing-final 两张、ready 两张、output-final 八张，12 次清点全部通过；过早截图与失败结果保留作调试证据，不进入最终画廊。

## 3. 夹具、合同与逐图复核

13 个状态是 empty、read-error、filled、unavailable、designing、writing、failed-shot、ready、rewriting、composing、composing-silent、done、done-silent。每个状态使用实际 1440×900、960×900 viewport，合计 26 张；另有 empty、writing、done、unavailable、read-error 的 390×900 手机检查 5 张。夹具截图不冒充后端真任务。

Core collect_design_inventory.js + check_design_contract.py 使用主目录新 contract.json：夹具 26 次通过，真实页面含播放态 12 次通过，合计 38 次。动态任务标题、口播、镜数、时间和检查 message 按数据区域清点，不当作稿外固定文案。没有修改设计稿、contract.json 或 Core checker。

**明确的文案补充：** 新导出的 failed-shot 合同仍没收录本轮第 5 条要求的「重试这一镜」「中断了 · 重试」。因此 approved-extras.json 只给 failed-shot 增补这两条用户已明确批准的文字，来源就是本轮指令；没有新增设计编号、可选化缺失块或放宽其他状态。除此之外没有新文案、稿外元素或待补接口。占位例句修正后 Core 文案检查通过。

最后一次产品视觉修改后重跑夹具及输出页截图。逐张打开并看完 43 张最终整页图，检查主体、相邻区域及底部：

- 真实四屏：两宽的标题、全片设计、胶片、详情、上传合成入口层次清楚；七镜和十镜没有串任务；960 宽四列，长口播未撑破卡片。播放时中央按钮消失，画面和时间发生变化。
- read-error：提示文字照新稿，步骤条显示读不到，没有误变成空白生成表单。unavailable：黄点、中文错误、生成禁用正确。
- composing / composing-silent：只展示批准的摘要，未展示伪造帧数或剩余时间。done-silent：中性横线、无声说明和两个按钮可读。
- writing / rewriting / failed-shot：已写时间、重写状态、失败空画面和可空意见的重试入口清楚。ready：构图 message 为普通黄色提醒。
- 手机五屏：作品标题和模型分行，三列胶片、单列详情、播放器检查数字不挤成竖排；没有横向溢出或底部裁切。

所有截图都是原始页面输出，没有修改图片像素。页面使用文档滚动，截图前实际滚到底再回顶部，PNG 高度覆盖 document.scrollHeight；时间、路由、真实 viewport、输出尺寸、覆盖范围和逐图哈希均在最终清单。真实视频内的密集字幕/构图属于 Opus 生成内容，本轮没有修改镜头代码，不将前端审图说成视频内容验收。画廊的 139 个 src/href 文件入口均已核验可达，最终截图哈希逐一复核。

## 4. 测试与限制

| 检查 | 结果 |
| --- | --- |
| `node scripts/direct_video/frontend_gate.mjs` | PASS：26 次合同、31 张夹具整页截图、公式与浏览器交互；pageerror 为 0。 |
| 真实四屏及播放态 Core 清点 | 最终 12/12 PASS；依据见最终清单。初次过早 writing 失败单独保留，不计入通过数。 |
| `node tests/test_r276_direct_frontend.mjs` | PASS：新增 writingStartedAt 空值/时间公式、空意见重试状态与 200 字边界；原有公式和失败映射继续通过。 |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_frontend.py tests/test_r276_direct_c.py tests/test_r276_direct_api.py tests/test_p2_frontend_contract.py tests/test_r220_number_formulas.py tests/test_checklist_remediation_static.py` | **80 passed**；指定现有前端回归未红，未编辑后端测试。 |
| `node tests/test_r220_number_formulas.mjs` | PASS。 |
| JS 语法、`git diff --check` | PASS；截图脚本最后补齐自己创建的空临时目录清理后再做语法检查。 |
| Core 文案检查，两个前端 JS | PASS，0 warnings；原占位文案问题已解决。 |
| runtime contract、music registry、repository safety、两个 validate 脚本 `--help` | PASS。音乐及测试使用 Core UI_COPY_QUALITY_CHECKER。 |
| Obsidian doc sync、outline contract | FAIL：与 F1 相同的三组 source-newer-than-target；显式使用自媒体 Obsidian 根，未越界修改相关执行文档或 Obsidian 页面。 |
| `.venv/bin/python -m pytest -q tests` | **970 passed、25 skipped、9 failed、6 errors、2003 subtests passed**。 |

全仓失败明细见外部 `pytest-full.log`：1 项文档同步；8 项失败和 6 项 setup error 在既有 FFmpeg 字幕/视频调用退出码 8 处失败，与 F1 所记录的缺少 drawtext/subtitles/ass 的失败类别一致。没有削弱测试或改 FFmpeg 相关代码；未另建基线 checkout 重跑全套，故不宣称已完成全部失败的回归归因。

浏览器交互实际覆盖：failed/interrupted 空意见提交成功、普通 rendered 空意见不能提交、填写意见恢复普通按钮、200 字边界、卡上中断重试、CSRF、WAV 原样上传、其他六镜 poster/time 不变、详情输入/焦点保留、代码展开才读取、ready/离页停止轮询、真实 video 定位、无声中性检查及构图提醒。真实新任务没有制造失败或重写；空意见重试由夹具浏览器交互和后端 C/API 测试验证。

## 5. 清理、状态与停止

已停止本线程启动的 8767，lsof 核验无监听；没有操作 8765/8766 或终止他人进程。两轮真实复制状态目录、夹具临时状态目录及脚本空临时目录已删除，临时 `.venv` 符号链接已移除。原 `~/.photo-content-os/studio-r276/` 的 8,594 个文件最后再次比对，与真跑前 SHA-256 完全一致。[清理核验](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/cleanup.json)

业务项目 git：本轮上述前端/夹具/测试/脚本及汇报均未提交；后端线程已有的 server/api/schema/direct_video 等改动保留。无提交、推送、新 worktree 或主目录修改。[完整状态](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/business-git-status.txt)

Harness SSOT git：本轮未修改；仓库仍有其他会话的 acceptance/requests、tools/console 等未提交改动。[完整状态](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f2/harness-git-status.txt)

开场读取的人验日志里，R220 的 studio.navigation / studio.shot-review PENDING 仍与入口相交，未代改其状态；R276 H-01–H-03 留给总控/用户验收。按文件白名单未写额外 handoff 或签署文件。本汇报和截图是普通报告/证据，不创建 SSOT 包或 Obsidian 快照。到此停止，不开始下一段。

## F3

已修正镜卡和单镜详情的计时含义。两处共用「写好 · 用时 m:ss」，用时为该镜 `writtenAt − writingStartedAt`；任一字段缺失、不可解析或时间倒置时只显示「写好」，不回退到任务创建时间。详情重画判据同时包含这两个时间字段，避免仅时间变化时仍显示旧值；输入意见、焦点和选区保留逻辑不变。

仅修改 `studio/static/direct-view.js`、`studio/static/direct-shot-detail.js`、`tests/test_r276_direct_frontend.mjs`，以及按要求追加本节。没有修改夹具、合同、截图脚本或后端。

回归覆盖正常写镜（3:41）、缺少 writingStartedAt / writtenAt、隔数小时重写（03:40:00 到 03:44:19，仅显示本次 4:19）。浏览器测试挂载实际页面模块，检查镜卡和详情两处文字；只更新一镜的两个时间字段，不改 posterRevision，也能刷新详情；其余六镜的卡片文字逐项保持不变。原有单镜重写后其他六镜 poster/time 不变、输入保留等交互检查继续通过。

| 指定检查 | F3 结果 |
| --- | --- |
| `node tests/test_r276_direct_frontend.mjs` | PASS。 |
| `HARNESS_CORE=~/Desktop/Opensource_Tool/Harness_Engineering/Core R276_FRONTEND_EVIDENCE=~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3 node scripts/direct_video/frontend_gate.mjs` | PASS：26 次设计合同比对、31 张完整页面截图、公式和浏览器交互；pageerror 为 0。仅使用 8767 临时 Studio 和接口夹具，没有运行真实生成任务。 |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_frontend.py` | 6 passed。 |
| `git diff --check` | PASS。 |

**合同文案结果：** 本次「写好 · 用时」未被判为稿外文字，两处沿用既有 data-design-data 数据区。没有修改 contract.json、approved-extras 或清点规则；合同通过不代表设计稿已同步改成新公式，文案与公式依据本轮明确指令。

F3 证据独立放在 [frontend-f3 清单](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3/screenshot-manifest.json)，未覆盖 F2 证据。亲自看了最终 [ready 1440](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3/ready-1440.png)、[ready 960](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3/ready-960.png)、[writing 390](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3/writing-390.png)、[done 390](~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3/done-390.png) 的完整页面及底部：镜卡新文字可读，详情右上角与镜卡用时一致；手机状态自然换行，没有溢出、裁切或遮挡。其余截图为本次矩阵机器检查，不宣称全部重新人工审图。实际 viewport 为 1440×900、960×900、390×900，路由是本地 fixture-piece 的脚本直出页；逐图时间、完整滚动覆盖、尺寸与哈希见清单。日志为同目录 formulas.log、frontend-gate.log、pytest.log。

业务 git HEAD 仍为 `b04e0387ea81fe629116073cb74a68b7c06d7a42`，没有提交、暂存、重写历史或修改前面的 90875ba / d095d10 / 9637bd9。工作区仅有上述四个已授权文件的改动，开场已有的未跟踪 `.venv` 链接保持原样。Harness SSOT 本轮未修改，其他会话已有改动保留。R276 人验 PENDING 保持原状，不代签或改验收文件。

8767 已由截图脚本停止，临时状态目录已清理，lsof 确认无监听。未操作 8765、8766、8768，未停止总控给用户开的 Studio。到此停止，交由总控提交。

F3 补充：为配合 R277 整块替换详情，已移除 R276 测试中全部详情「写好」文案断言（含 normal、missingStart、missingEnd、refreshedDetail、rewrittenDetail），镜卡断言全部保留，详情实现未回退；`node tests/test_r276_direct_frontend.mjs` 和设置 HARNESS_CORE 指向 Core 的 `node scripts/direct_video/frontend_gate.mjs` 重跑均通过（26 次合同检查、31 张完整截图及浏览器交互），新日志位于 `~/.photo-content-os/evidence/R276-direct-video-opus/frontend-f3-card-only/`，8767 已停止并清理临时状态，未提交、未操作 8766，本次仅修改测试和追加本句，业务项目保留既有 F3 未提交改动，Harness SSOT 未修改。
