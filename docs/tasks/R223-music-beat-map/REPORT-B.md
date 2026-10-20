# R223 阶段 B 汇报

## 和设计稿哪里不一样

B1–B4 已实现并在 worktree 提交，未推送。后端接口未改。以下是逐状态、逐宽度的实际差异，不将截图相似等同于人工验收通过。

并排图统一位于 `~/.photo-content-os/evidence/R223-music-beat-map/phase-b/comparisons/`，表内是该目录下的完整文件名，**左设计稿、右实现**。图库入口为同级上层 `index.html`。63 张并排图、151 个图库引用均检查可达及哈希；原始截图的尺寸、时间、哈希见机器证据。设计侧由批准的 HTML 重新全页渲染；原有 `mockshots/` 保持原样，避免原有视口截图截掉右栏底部。

差异说明：

- D0：现有外壳的工作台数字为 1，稿中为 2；桌面页脚保留现有「上游平台未连接」。来自隔离环境中的项目与连接状态，未改共享外壳。
- D1：波形使用共享模块按时间定位，柱间距比稿的 flex 排列略密；峰值和高度公式一致。真实音频波形本身也不同于稿的示例。
- D2：分面标签先按数量降序，同数按 taxonomy 顺序；稿中同数按样本首次出现顺序。实现遵守接口作为顺序权威。
- D3：播放动效相位可能不同；响度柱用精确的 `10 + 40 × E`，稿中部分柱高取整，差不超过 0.5px。1:28 截图固定在真实播放器的 88.4 秒采样帧；另有连续播放和 rAF 检查。
- D4：真实模型的拍点、段落和 BPM 与设计样本不同。Turn Back Time 为 115 BPM，稿为 117；CRUSH VIBE 为 143，稿为 144；Fever Pitch 为 125，稿为 123。真实数据没有改成稿里的数。

| 状态 / 场景 | 实际视口 | 并排图文件名 | 差异与原因 |
|---|---|---|---|
| music | 1440×960 | `compare-music-1440.png` | D0、D1、D2、D3 |
| music | 1180×860 | `compare-music-1180.png` | D0、D1、D2、D3 |
| music | 430×932 | `compare-music-430.png`；`compare-music-430-open.png`（展开） | D0、D1、D2、D3 |
| music-playing | 1440×960 | `compare-music-playing-1440.png` | D0、D1、D2、D3 |
| music-playing | 1180×860 | `compare-music-playing-1180.png` | D0、D1、D2、D3 |
| music-playing | 430×932 | `compare-music-playing-430.png`；`compare-music-playing-430-open.png`（展开） | D0、D1、D2、D3 |
| music-intro | 1440×960 | `compare-music-intro-1440.png` | D0、D1、D2、D3 |
| music-intro | 1180×860 | `compare-music-intro-1180.png` | D0、D1、D2、D3 |
| music-intro | 430×932 | `compare-music-intro-430.png`；`compare-music-intro-430-open.png`（展开） | D0、D1、D2、D3 |
| music-end | 1440×960 | `compare-music-end-1440.png` | D0、D1、D2、D3 |
| music-end | 1180×860 | `compare-music-end-1180.png` | D0、D1、D2、D3 |
| music-end | 430×932 | `compare-music-end-430.png`；`compare-music-end-430-open.png`（展开） | D0、D1、D2、D3 |
| music-beats-queued | 1440×960 | `compare-music-beats-queued-1440.png` | D0、D1 |
| music-beats-queued | 1180×860 | `compare-music-beats-queued-1180.png` | D0、D1 |
| music-beats-queued | 430×932 | `compare-music-beats-queued-430.png`；`compare-music-beats-queued-430-open.png`（展开） | D0、D1 |
| music-beats-analyzing | 1440×960 | `compare-music-beats-analyzing-1440.png` | D0、D1 |
| music-beats-analyzing | 1180×860 | `compare-music-beats-analyzing-1180.png` | D0、D1 |
| music-beats-analyzing | 430×932 | `compare-music-beats-analyzing-430.png`；`compare-music-beats-analyzing-430-open.png`（展开） | D0、D1 |
| music-beats-failed | 1440×960 | `compare-music-beats-failed-1440.png` | D0、D1、D2 |
| music-beats-failed | 1180×860 | `compare-music-beats-failed-1180.png` | D0、D1、D2 |
| music-beats-failed | 430×932 | `compare-music-beats-failed-430.png`；`compare-music-beats-failed-430-open.png`（展开） | D0、D1、D2 |
| music-beats-failed-unreadable | 1440×960 | `compare-music-beats-failed-unreadable-1440.png` | D0、D1、D2 |
| music-beats-failed-unreadable | 1180×860 | `compare-music-beats-failed-unreadable-1180.png` | D0、D1、D2 |
| music-beats-failed-unreadable | 430×932 | `compare-music-beats-failed-unreadable-430.png`；`compare-music-beats-failed-unreadable-430-open.png`（展开） | D0、D1、D2 |
| music-beats-failed-unknown | 1440×960 | `compare-music-beats-failed-unknown-1440.png` | D0、D1、D2 |
| music-beats-failed-unknown | 1180×860 | `compare-music-beats-failed-unknown-1180.png` | D0、D1、D2 |
| music-beats-failed-unknown | 430×932 | `compare-music-beats-failed-unknown-430.png`；`compare-music-beats-failed-unknown-430-open.png`（展开） | D0、D1、D2 |
| music-tags-failed | 1440×960 | `compare-music-tags-failed-1440.png` | D0、D1、D2 |
| music-tags-failed | 1180×860 | `compare-music-tags-failed-1180.png` | D0、D1、D2 |
| music-tags-failed | 430×932 | `compare-music-tags-failed-430.png`；`compare-music-tags-failed-430-open.png`（展开） | D0、D1、D2 |
| music-filtered | 1440×960 | `compare-music-filtered-1440.png` | D0、D1、D2、D3 |
| music-filtered | 1180×860 | `compare-music-filtered-1180.png` | D0、D1、D2、D3 |
| music-filtered | 430×932 | `compare-music-filtered-430.png`；`compare-music-filtered-430-open.png`（展开） | D0、D1、D2、D3 |
| music-filter-empty | 1440×960 | `compare-music-filter-empty-1440.png` | D0；空结果不显示右栏，故没有展开图 |
| music-filter-empty | 1180×860 | `compare-music-filter-empty-1180.png` | D0；空结果不显示右栏，故没有展开图 |
| music-filter-empty | 430×932 | `compare-music-filter-empty-430.png` | D0；空结果不显示右栏，故没有展开图 |
| real-queued-projection | 1440×960 | `compare-real-queued-projection-1440.png` | D0、D1 |
| real-queued-projection | 1180×860 | `compare-real-queued-projection-1180.png` | D0、D1 |
| real-queued-projection | 430×932 | `compare-real-queued-projection-430.png`；`compare-real-queued-projection-430-open.png`（展开） | D0、D1 |
| real-normal-projection | 1440×960 | `compare-real-normal-projection-1440.png` | D0、D1、D2、D4 |
| real-normal-projection | 1180×860 | `compare-real-normal-projection-1180.png` | D0、D1、D2、D4 |
| real-normal-projection | 430×932 | `compare-real-normal-projection-430.png`；`compare-real-normal-projection-430-open.png`（展开） | D0、D1、D2、D4 |
| live-final-queued | 1440×960 | `compare-live-final-queued-1440.png` | D0、D1 |
| live-final-queued | 1180×860 | `compare-live-final-queued-1180.png` | D0、D1 |
| live-final-queued | 430×932 | `compare-live-final-queued-430.png`；`compare-live-final-queued-430-open.png`（展开） | D0、D1 |
| live-final-normal | 1440×960 | `compare-live-final-normal-1440.png` | D0、D1、D2、D4 |
| live-final-normal | 1180×860 | `compare-live-final-normal-1180.png` | D0、D1、D2、D4 |
| live-final-normal | 430×932 | `compare-live-final-normal-430.png`；`compare-live-final-normal-430-open.png`（展开） | D0、D1、D2、D4 |

`real-*-projection` 是曲库复制品的真实接口投影；`live-final-*` 是未拦截音乐 API 的最终服务截图。最差首屏观察到第一首分析中、另外两首排队，随后不刷新页面依次进入分析和完成。正常图在三首 beat、tags 全部 done 且页面完成更新后拍摄。早期 8 张 `implementation-real-queued/normal-*` 已标为 SUPERSEDED，不计入最终通过。

右栏 2 倍图在 `~/.photo-content-os/evidence/R223-music-beat-map/phase-b/`：

| 场景 | 设计数据的实现截图 | 真实复制品截图 | 真实结果差异 |
|---|---|---|---|
| 开头 | `implementation-music-rail-2x.png` | `real-start-rail-2x.png` | Turn 从第 1 小节开始；稿的第一重拍稍后出现 |
| 播放到 1:28 | `implementation-music-playing-rail-2x.png` | `real-playing-rail-2x.png` | 实测第 43 小节、推进；稿第 40 小节、高潮 |
| CRUSH VIBE 前奏 2 秒 | `implementation-music-intro-rail-2x.png` | `real-intro-rail-2x.png` | 实测已有拍点、第 2 小节；稿这一窗口没有拍子 |
| Fever Pitch 结尾 133 秒 | `implementation-music-end-rail-2x.png` | `real-end-rail-2x.png` | 实测第 69 小节；稿第 68 小节 |

已亲自查看三档对照板、桌面全页、手机展开页、四种右栏放大图及 `r226-module.png`，包括底部导入时间。手机多余速度列和多首换歌按钮裁切已修复。没有水平溢出；可见状态的层次、失败恢复入口、标签换行及底部信息正常。本次为 Codex 代理视觉复核，未代替 Claude 复核或用户真人验收。

## 四道检查的命令和结果原样

环境：`STUDIO_URL` 指向本任务曲库复制品的独立 Studio（62738）；最终真实补分析服务为 64306。均不使用 8765。`PW_REQ` 指向临时 Playwright 解析入口；`HARNESS_CORE_ROOT` 指向当前 Harness Core；`DESIGN_CONTRACT_CHECKER=$HARNESS_CORE_ROOT/skills/ui-copy-quality/scripts/check_design_contract.py`。以下命令从 worktree 根运行。

### 1. 文案表、2. 设计编号

批准文案从清单生成，另读取 TASK B1 已批准的即时反馈「分析中」，没有手抄 taxonomy。

```text
.venv/bin/python scripts/music_analysis/approved_frontend_copy.py --out tests/fixtures/r223/frontend/approved-copy.json
Approved taxonomy and TASK B1 immediate progress copy generated

.venv/bin/python scripts/check_r223_design.py
Inventories: 58 failing: 0
[]
exit 0
```

包装脚本逐份调用现有 `check_design_contract.py check --contract ... --inventory ... --approved-extras ... --json`。58 份包括 47 份设计状态场景、8 份真实投影、3 份即时重试状态；同时核对可见文案和设计编号。负例原样结果：

```text
copy: exit 1, copy.unapproved-text
unapproved-id: exit 1, design.unapproved-element
missing-id: exit 1, design.missing-element
zero-inventory: exit 1, design.matrix.incomplete: expected 47 mock, 8 copied-library and 3 optimistic inventories
```

### 3. 数字公式

```text
node scripts/capture_r223.mjs
PASS capture matrix and all 12 numeric formula rows
exit 0

node tests/test_r220_number_formulas.mjs
PASS numeric formulas: positive and negative assertions
PASS R220 music numeric regression: median BPM, meter, bar counts, clamped window
exit 0
```

截图脚本需设置 `R223_SCREENSHOTS`、`R223_EVIDENCE`，真实投影补拍使用 `ONLY_STATES=real-queued-projection,real-normal-projection` 与 `R223_REAL_FIXTURES`。`number-formulas.json` 的 28 次实际页面核对覆盖第 6 节全部 12 行：BPM、每小节拍数、当前小节、小节序号、段名、前面 N 首、8 秒窗口、柱高、段宽、来源计数、分面计数、派生标签。原始观测保存在 `number-formulas.json`，不是只对辅助函数自测。

### 4. 人话与观感

```text
python3 "$HARNESS_CORE_ROOT/skills/ui-copy-quality/scripts/check_ui_copy_quality.py" studio/static/review-music.js studio/static/beat-map.js --project-root . --evidence-dir evidence/2026-10-21/R223-music-beat-map/phase-b/copy
ui-copy-quality: PASS (2 file(s), 0 warning(s); lexical checks only, not a review of meaning)
exit 0
```

截图查看范围、差异、尺寸与完整覆盖证据见上节及 `visual-review.md`；词法通过不冒充语义或观感通过。

## 其他检查及运行结果

```text
node tests/test_r223_beat_map.mjs
PASS beat map: signature lifecycle, cuts, fade, offsets, multi-song swap, lane:false, seek, stable overview, formulas, visible swap, no overflow
exit 0

node scripts/verify_r223_interactions.mjs
PASS 6 music interaction checks
exit 0

R220_MUSIC_ONLY=1 node scripts/verify_r220_browser.mjs
PASS R220 music browser regression: real playback, seek, four title widths, metadata font, no JS errors
exit 0

node --check <8 changed JS/MJS files>
8/8 syntax checks passed
exit 0
```

模块测试覆盖约定签名和三个返回方法、更新与销毁、cuts、fadeOut、offset、多首歌、lane:false、小节各自编号、onSeek、onSwapClick、button.bm-swap、aria-pressed 和点击隔离。交互检查覆盖两种即时重试与失败回滚、同时重试互不覆盖、真实音频播放与跳转、白拍和 overview 节点稳定、约 1 秒轮询直到完成后停止、taxonomy 改名和顺序立即生效。旧 R220 的原有数字断言保留；浏览器仅运行音乐分支，未运行依赖旧项目素材的其他页面流程，默认全流程入口保持原样。

阶段 A 全套检查重新执行，原样命令、退出码与结果如下（`OBSIDIAN_ROOT` 显式设置为现有自媒体 vault；测试媒体根为临时目录）：

| 命令 | 退出码 | 原样结果 / 完整日志 |
|---|---:|---|
| `.venv/bin/python -m pytest -q tests/test_r223_sections.py` | 0 | `28 passed in 0.99s` |
| `.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_p1_openclaw_bridge.py tests/test_desktop_openapi_route_sync.py` | 0 | `63 passed, 4 subtests passed in 11.64s` |
| `R223_RUNTIME_TESTS=1 .venv/bin/python -m pytest -q tests/test_r223_music_analysis_runtime.py` | 0 | `1 passed in 133.96s (0:02:13)` |
| `bash scripts/check_runtime_contract.sh` | 0 | `Runtime contract check passed.` |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 0 | `music-analysis-registry OK: 126 ids; 121 copy entries` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 0 | `Repository safety check passed.` |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 1 | `Obsidian 文档同步检查失败：`；完整 `doc-sync.log` |
| `.venv/bin/python scripts/check_outline_contract.py .` | 1 | 同步检查失败后 `subprocess.CalledProcessError`；完整 `outline.log` |
| `.venv/bin/python -m pytest -q tests` | 1 | `10 failed, 828 passed, 33 skipped, 6 errors, 2003 subtests passed in 240.27s (0:04:00)` |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 0 | help 正常输出，完整 `task-help.log` |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 0 | help 正常输出，完整 `draft-help.log` |

全量失败与 A4 基线相同：本机 ffmpeg 无 drawtext 导致 8 failed、6 errors；worktree 的共享工具软链接路径断言 1 failed；既有 Obsidian 同步问题 1 failed。同步与 outline 同为既有 3 组文档源更新于 vault 目标，未修改 vault 或放宽检查。本次没有新的 Python 失败，未将全量结果写成全绿。

```text
.venv/bin/python scripts/music_analysis/verify_runtime.py --evidence-dir evidence/2026-10-21/R223-music-beat-map/phase-b/http-runtime
HTTP folder import started
Three real analyses complete
Unreadable failure and tags-only retry verified
Startup backfill verified
exit 0
```

此 HTTP 检查用 3 首合成音频，完成导入→排队→模型→接口，验证不可读失败、仅标签重试和启动补队列。每首原始分数数量为 genre 400、moodtheme 56、instrument 40、voice 2；worker 禁止网络连接。原样完整日志与结果在 `http-runtime.log`、`http-runtime/runtime.json`。

真实曲库整份复制后，只在复制品迁移并删除其 3 份 analysis.json，再启动补分析；最终三首 beat、tags 都为 done：

| 歌曲 | BPM | 每小节拍数 | 段落数 |
|---|---:|---:|---:|
| Turn Back Time | 115 | 4 | 10 |
| CRUSH VIBE | 143 | 4 | 9 |
| Fever Pitch | 125 | 4 | 10 |

原件全部 86 个文件的相对路径、SHA-256、mtime_ns 前后完全相同，无新增或删除；完整快照只放仓库外。原有 beat-maps 导出未改。仅关闭本任务自己启动的隔离服务，未访问、启动、停止或重启 8765。

## 改了哪些文件

- `studio/static/review-music.js`：音乐列表、分面筛选、8 种状态、AI 标注、节拍图接入、rAF 播放、轮询和分部重试。保留现有导入流程。
- `studio/static/beat-map.js`：新增共享节拍模块及 R226 约定入口，适配 Studio 的严格 CSP。
- `studio/static/review.css`：只改音乐行及新增 bm/tag/tg 规则，使用现有语义令牌；没有新增 !important。手机来源与速度放入元信息，桌面保留速度列。
- `scripts/music_analysis/approved_frontend_copy.py`、`build_frontend_fixtures.py` 与 `tests/fixtures/r223/frontend/`：从清单生成批准文案，通过阶段 A 原接口投影生成全部状态，夹具不带音频或私人路径。
- `scripts/capture_r223.mjs`、`check_r223_design.py`、`verify_r223_interactions.mjs`、`verify_r223_music_browser.mjs`、`tests/test_r223_beat_map.mjs`：截图、页面文案/编号清单、实际数字公式和模块/交互检查。
- `scripts/verify_r220_browser.mjs`、`tests/test_r220_number_formulas.mjs`、R220 `design-contract.json`：音乐部分对齐 R223，保留其他页面入口与既有断言。
- `TASK.md`、`DESIGN.md`：纳入 Claude 已补全的阶段 B 细则及接口说明，作为本轮输入一起保存；未改后端实现。
- `REPORT-B.md` 和 `evidence/2026-10-21/R223-music-beat-map/phase-b/`：本轮报告和文本证据。图片、音频、复制品与完整原件快照均在仓库外。

机器证据根目录：`evidence/2026-10-21/R223-music-beat-map/phase-b/`。主要入口为 `frontend-checks.json`、`checks-summary.json`、`design-checks.json`、`number-formulas.json`、`interactions.json`、`source-bindings.json`、`reviewed-screenshot-manifest.json`、`comparisons.json`、`gallery-verification.json`、`live-final-runtime.json`、`original-library-preserved.json`。旧截图在 `superseded-screenshots.json` 明确排除。

## 越界需求

无。

## 需要新文案

无。即时「分析中」直接来自 TASK B1，其余 taxonomy 文案来自接口。

## 稿外元素

无新增产品块。独立标签重试时，同一既有 AI 标注区显示 TASK 已规定的「分析中」；没有新建状态名或新面板。共享模块的换歌/切点/淡出属于 DESIGN 10.1 明确要求。

## 需要拍板

无新增决定。Claude 截图复核和需求卡真人验收仍由原流程负责，没有把既有 R210/R220 PENDING 记录改为通过。

## 提交与工作区状态

本阶段在 `/private/tmp/task-worktrees/photo-content-os-r223-music-beat-map` 提交，未推送，未运行 finish、合并或删除 worktree。提交尾行：

```text
Request: 2026-10-20-R223-photo-music-beat-map
Verify: 2026-10-20-R223-photo-music-beat-map/H-01, 2026-10-20-R223-photo-music-beat-map/H-02, 2026-10-20-R223-photo-music-beat-map/H-03
```

业务 worktree 提交后仅保留未跟踪的 `.tools`、`.venv` 共享软链接；主目录未写入。本轮未编辑 Harness SSOT；其工作区已有其他改动，收尾只读状态见 `harness-status.txt`，未提交或回退这些改动。当前任务证据不是声明的 SSOT 开发包，不创建第二份 Obsidian 权威。
