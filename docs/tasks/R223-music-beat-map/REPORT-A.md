# R223 阶段 A 汇报

阶段 A（A1–A8）已实现，专项和真实模型链路通过；全局检查仍有范围外失败，不能标为发布 READY。未进入阶段 B，未迁移或补分析真实曲库，未访问、重启或终止 8765 Studio。

工作区：`/private/tmp/task-worktrees/photo-content-os-r223-music-beat-map`，由指定脚本基于 `origin/main` 创建；代码、任务资料、证据和本报告在该 worktree 提交，不推送，不执行 `finish`。`.venv`、`.tools` 保留为指向主目录的本地软链接，不纳入提交。

## A1 删除曲目授权

- 修改 `scripts/music_library/{library,platforms,client_files,musicdl_engine}.py`、`scripts/import_music.py`，删除字段、赋值、显示映射和命令行输出。
- 修改 `studio/static/review-music.js`、`review.css`：删除授权列、小标签和右侧说明，调整五列桌面、四列窄桌面及手机栅格。
- 更新 `tests/test_music_library.py`、`scripts/verify_r220_browser.mjs`；保留测量、去重、完整性和错误处理测试。`tests/test_r220_number_formulas.mjs` 当前基底没有授权断言，无需修改，实际运行通过。
- 更新音乐库 README、R210 TASK、R208 PRD、R220 TASK / design-contract / resolved-surface-contract。R220 音乐设计由 R223 接管，删除相冲突的旧占位文案。主目录未跟踪的 R210 TASK 复制后仅修改本次要求；两份任务单中的用户绝对路径改为路径变量，未改验收标准。
- 已保留并验证：导入、去重、测量、试听、波形跳转接口及错误处理；旧字段、授权入口、别名和回退没有保留；v1 索引及曲目被明确拒绝并提示“先运行迁移”。

删除扫描命令：

```bash
rg -n "license_status|LICENSE_LABELS|平台版权曲|来源不明|licenseTag|license--unknown|attribution|授权未知|版权曲" scripts studio schemas tests docs README.md
```

扫描剩余命中逐项核对如下（行号为写本报告前的扫描，清单见 `deletion-scan.json`）：

| 位置 | 保留理由 |
| --- | --- |
| `scripts/migrate_music_library_v2.py:14` | 迁移必须识别并删除旧字段，不是运行时兼容读取。 |
| `tests/test_r223_music_analysis.py:36,56` | 构造 v1 负例及断言迁移后旧字段消失。 |
| `scripts/shot_aesthetics.py:22` | 模型权重许可证，任务明确排除。 |
| `scripts/music_library/f2-Apache.LICENSE:102,108,117,120` | 第三方软件许可证原文。 |
| `scripts/music_library/MTG-CC-BY-NC-SA-4.0.LICENSE:211,252` | 模型许可证原文。 |
| `scripts/music_library/essentia-AGPL-3.0.LICENSE:357` | 分析软件许可证原文。 |
| `docs/discussions/2026-10-20-music-tagging/opus-x1.md:7,12` | 历史讨论和纠错记录。 |
| 同目录 `gpt-r1.md:1`、`synthesis.md:51`、`opus-r1.md:5,45` | 历史事实快照、被纠正的旧结论，按要求整份保留。 |
| `docs/tasks/R220-studio-ia-preview/REPORT-2.md:26` | 历史汇报，明确不改。 |
| `docs/tasks/R223-music-beat-map/DESIGN.md:66,68` | 权威设计对删除对象的说明。 |
| 同目录 `TASK.md:69,70,72,77,83,85,89,90,105` | 原任务的删除范围、扫描命令和迁移要求。 |
| 本 `REPORT-A.md` | 删除审计说明和扫描命令自身。 |

另外保留：R210 TASK 中既有执行历史、剪辑交接的软件许可证、账号/同步授权、成片检查素材来源与第三方声明；未把它们误删为曲目字段。

已亲自打开并检查最后一次视觉修改后的真实应用截图：`/#view=music`，实际视口 1440×960、430×960，三首合成音频，详情展开，播放已推进再暂停。列表、相邻导入区和详情底部完整可见，无横向溢出。文件在仓库外 `~/.photo-content-os/evidence/R223-music-beat-map/phase-a/`，尺寸、时间、哈希和检查结论见 `visual.json`。这是本地 A1 删除验证；旧节拍占位按本阶段边界保留，新节拍图及标签界面留到阶段 B。

## A2 v2 规范和迁移

修改 `schemas/music-track.schema.json`、`library.py`：曲目和索引只认 v2，删除授权及三个空分析字段，无 v1 兼容分支。

新增 `scripts/migrate_music_library_v2.py`：默认预演；`--apply` 前将索引和全部曲目元数据备份至仓库外，逐文件核验备份字节后再写。写完验证全库，重复执行不改文件、不新增备份；写入异常尝试还原原元数据。音频、`peaks.json`、`.attempts/` 不动。

临时曲库测试覆盖：预演、备份、应用、幂等、备份失败拒写、写失败回滚、旁挂和音频保留、v1 明确拒绝。真实曲库没有执行迁移。

## A3 清单规范与门禁

新增 `schemas/music-analysis-registry.schema.json`、`scripts/validate_music_analysis_registry.py`、`docs/music-analysis-registry-guard.md`；接入 `AGENTS.md` Required checks 和 `.harness/overlays/project-harness-adapter.yaml` 的 `static_guards`。

失败类为 `music-analysis-registry`，失败输出给出修法。拦截重复编号、启用标签无中文名、未知类别/模型、越界阈值、模型缺哈希/许可、删除或复用已发布编号、版本未恰好加一、未追加或改写历史记录及文案失败。文件不可读、解析失败、零输入和 Git 基底不可读均非零退出。

使用 Core 同一文案检查器，实际通过：`126 ids; 121 copy entries`。对 `origin/main` 成功读取 Git 树后确认这是首次发布；历史版本红绿用例另行覆盖。运行前需设置 `UI_COPY_QUALITY_CHECKER` 指向 Core 的检查脚本。

## A4 独立分析环境

新增 `scripts/music_analysis/install.py`、`third_party/music-analysis.requirements.lock.txt`，扩展 `third_party/edit-tools.lock.json` 和 `scripts/setup_edit_tools.py --music-analysis`；现有 Shell / PowerShell 包装入口透传参数。

实际环境为 Python 3.12.14（macOS arm64），选择理由是指定 Essentia、torch/torchaudio 配对和 librosa 均有可用轮子，已实际加载运行。包版本：beat-this 1.1.0、librosa 1.0.0、essentia-tensorflow 2.1b6.dev1389、torch/torchaudio 2.8.0。未安装进 Studio `.venv`。

五个 MTG 模型按清单地址下载并逐个核对 SHA-256；另锁定 beat-this final0 权重及四份类别元数据的哈希。10 个文件校验全部一致，见 `models.json`。安装脚本重复执行通过。

在 `scripts/music_library/` 增加 MIT、ISC、AGPL-3.0、CC BY-NC-SA 4.0 全文，在 `THIRD_PARTY_NOTICES.md` 记录来源。分析只加载本地模型，worker 禁止 socket 连接，不调用大模型。未验证 Windows/Linux 安装。

## A5 分析程序与结果

新增 `scripts/music_analysis/worker.py`、README 和 `schemas/music-analysis.schema.json`。专用解释器以子进程收发 JSON，整首超时 180 秒，诊断走 stderr；结果原子写入每首的 `analysis.json`。

输出实测拍点、重拍、逐拍 RMS 归一能量、三档小节能量段落，以及四个分类头全部原始分数（400 / 56 / 40 / 2），并记录包版本、模型编号、清单版本。短段按清单 `min_bars` 合并。节拍与标签独立成败，保留 `audio_unreadable`、`worker_error`、`timeout` 和未知代号。

真实点击音轨：120 BPM 误差 0；裁去开头 0.5 秒，排除头尾 4 秒后内部拍点平移最大误差 0 秒，容差 0.04 秒。时间戳、重拍子集、能量长度、完整分数数量及规范校验通过。已修复模型返回曲终拍点导致空 RMS 片段的问题，回归断言保留。

## A6 共享标签推导与读取

新增 `studio/music_analysis.py` 和 `tests/fixtures/r223/scores.json`。`derive()` 从当前清单现算；三首设计数据的风格、细分、情绪、场景、人声和乐器均符合任务期望，包含 Fever Pitch 的人声拿不准和 CRUSH VIBE 的空场景。

测试证明改中文名、阈值或标签状态后，重新读取立即生效，不重跑模型。R226 可用 `read_rhythm(library, track_id)` 只读拍点、重拍/小节、段落、BPM 和拍号；不会启动分析。调用方式及返回结构已写进分析 README。

## A7 串行分析队列

`AnalysisQueue` 在 Studio 进程内一次处理一首。导入成功自动排队，启动补排缺少结果的曲目，返回排队位置，重复请求合并；部分重分析保留另一部分的结果。worker 异常隔离并持久化失败，结果不可读明确报错。

最后一轮全量测试抓到启动补排与 worker 完成之间的竞态，已改为先补排再启动 worker，并将缺失检查和入队置于同一锁内。保留原断言，另用快速合成 worker 压测 50 次，50/50 均只执行一次。红例保留在 `pre-startup-race-full.log`。

## A8 接口与契约

修改 `studio/media_review.py` 的音乐部分、`studio/server.py` 的音乐路由及队列启动行；`studio/api_contract.py` 只增加重新分析路由，并由 `build_openapi()` 重生成 `schemas/studio-openapi.json`。

`GET /api/review/music` 返回当前 `registry_version`、`taxonomy` 以及每首独立的 `beat` / `tags`，不返回原始分数。新增 `POST /api/review/music/<编号>/reanalyze`，JSON 参数 `part=beat|tags`，沿用 Origin/CSRF 检查。

HTTP/投影测试覆盖完成、排队、分析中、节拍失败、标签失败、音频不可读和未知代号；路由同步通过。按任务一次加入五个共享色彩令牌，未实现阶段 B 的图表和标签组件。

临时 Studio 使用自动分配的非 8765 端口，走真实 HTTP 文件夹导入三首自行合成音频 → 自动队列 → 真实模型 → 接口结果；注入音频损坏后得到不可重试的 `audio_unreadable`，恢复文件后仅重跑标签，节拍结果逐字段不变；重启后补齐缺失结果。最后一轮端口及状态记录见 `runtime.json`，测试服务已关闭。

## 测试与检查结果

命令均在 worktree 执行。Required checks 使用临时 `LOCAL_MEDIA_ROOT`，显式设置 `OBSIDIAN_ROOT` 和 `UI_COPY_QUALITY_CHECKER`。日志仅将本机路径替换为变量，保留结果、退出码和断言内容；完整日志位于 `evidence/2026-10-21/R223-music-beat-map/`。

| 命令 | 退出码 | 最终结果 |
| --- | --- | --- |
| `bash scripts/check_runtime_contract.sh` | 0 | `Runtime contract check passed.` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 0 | `Repository safety check passed.` |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 1 | `3 组 source doc is newer than Obsidian target` |
| `.venv/bin/python scripts/check_outline_contract.py .` | 1 | `因 Obsidian 同步检查非零退出` |
| `.venv/bin/python -m pytest -q tests` | 1 | `10 failed, 771 passed, 33 skipped, 6 errors, 2003 subtests passed in 126.44s (0:02:06)` |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 0 | `help 正常` |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 0 | `help 正常` |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 0 | `music-analysis-registry OK: 126 ids; 121 copy entries` |

专项结果原样：

```text
.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_music_library.py tests/test_desktop_openapi_route_sync.py
exit 0
71 passed in 3.90s

R223_RUNTIME_TESTS=1 R223_EVIDENCE=evidence/2026-10-21/R223-music-beat-map .venv/bin/python -m pytest -q tests/test_r223_music_analysis_runtime.py
exit 0
1 passed in 14.22s

.venv/bin/python scripts/setup_edit_tools.py --music-analysis
exit 0
Music analysis runtime and model hashes OK

.venv/bin/python scripts/music_analysis/verify_runtime.py --evidence-dir evidence/2026-10-21/R223-music-beat-map
exit 0
HTTP folder import started
Three real analyses complete
Unreadable failure and tags-only retry verified
Startup backfill verified

node tests/test_r220_number_formulas.mjs
exit 0
PASS numeric formulas: positive and negative assertions

node --check studio/static/review-music.js
exit 0
```

全量失败范围：

- 8 个失败及 6 个 setup errors：`test_bilingual_subtitles_r6.py`、`test_direct_video_subtitles.py`、`test_pf_video_pipeline.py` 的字幕/视频合成路径。本机 `ffmpeg -filters` 确认没有 `drawtext`，调用返回 exit 8。
- 1 个失败：`test_edit_tools_runtime.py::test_default_paths_do_not_depend_on_home`。既有适配器解析 `.tools` 软链接得到主目录路径，而断言要求 worktree 字面路径。
- 1 个失败：`test_obsidian_doc_sync.py` 的真实文档命令用例；和两项独立检查相同，是三组源文件时间晚于 Obsidian 目标。

上述代码和测试相对 `origin/main` 均未改动；未修改 FFmpeg、剪辑后端、这些测试或 Obsidian 文件，也没有降低门禁。早期绝对路径失败已修复，启动竞态的 1 个失败已修复，最终全量中没有 R223 失败。全部失败名称与原始断言见 `final-check-5.log`。

未执行：真实曲库迁移/补分析、阶段 B 页面实现及其状态截图/完整体验验收、Windows/Linux 安装；没有声称 H-01–H-03 已获人工通过。既有 R210、R220 人工记录仍为 PENDING。

## 真实曲库迁移和补分析步骤（仅说明，未执行）

由 Claude 在代码整合、允许停用旧 Studio 后安排：

1. 暂停导入及旧 Studio，确认使用待发布代码；`LOCAL_MEDIA_ROOT` 由操作人显式设为真实素材根。
2. 安装并核验独立环境：`python3 scripts/setup_edit_tools.py --music-analysis`。
3. 预演：`.venv/bin/python scripts/migrate_music_library_v2.py`。确认曲目数与预期一致。
4. 应用：`.venv/bin/python scripts/migrate_music_library_v2.py --apply`。备份固定在 `~/.photo-content-os/backups/music-library-v1-<UTC时间戳>/`，包含索引及全部曲目元数据；备份失败不会写曲库。
5. 再执行同一命令，应返回 `unchanged`；用 v2 代码读取索引及曲目，随后启动新版 Studio。缺少 `analysis.json` 的曲目自动串行补分析，从接口核对每首两部分状态。
6. 回退：保持 Studio 和导入停止，恢复迁移前代码，再将该批备份的 `index.json`、各曲目 `track.json` 按原相对位置恢复。音频、波形和尝试缓存不用恢复；新旁挂可保留供排查，旧代码不读取。该回退以备份后未新增导入为前提；有新增记录时先核对差异，不直接覆盖索引。

## 越界需求

处理下列全局失败需要修改本任务文件边界之外的内容：具备 `drawtext` 的视频运行环境、现有剪辑后端的软链接路径断言、Obsidian 三份协议页的同步/时间问题。此次只记录，不改这些实现、测试、协议或门禁。

## 需要新文案

无。展示名字和空/不确定文案沿用清单；新增错误只供接口诊断，阶段 B 按批准设计映射展示。

## 需要拍板

无新增产品决策。全局失败、阶段 A 审阅、真实迁移时机及阶段 B 是否开启交由 Claude 按原任务安排。

## Git 与边界状态

- 业务项目：阶段 A 代码、输入资料、文字证据和本报告已在上述 detached worktree 提交；未推送，未改主目录源码、文档或真实曲库。独立环境按约定经共享 `.tools` 链接安装；运行环境链接为本地未跟踪文件。
- 收尾 `task_worktree.py check` 返回 1：worktree 按本次明确要求保留，含本地运行环境链接，且没有推送/整合；因此未执行 `finish`。
- Harness SSOT：本次没有修改或提交；检查时工作区有 11 项既存改动/未跟踪项，状态记录在 `harness-status.txt`。
- 未创建声明式 SSOT 开发包，本次任务文档及机器证据不属于 Obsidian SSOT 快照范围。

阶段 A 汇报至此，停止，等待 Claude 复核。
