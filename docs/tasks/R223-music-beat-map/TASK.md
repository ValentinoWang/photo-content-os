# R223 任务单：音乐库 AI 标签、节拍图，删除授权

- 需求卡：音乐库：AI 给每首歌打标签，并显示节拍图 · 待办（2026-10-20-R223-photo-music-beat-map）。验收项 H-01、H-02、H-03 以需求卡为准，不许自行改标准。
- 同时改到的两张卡（只改其中「授权」相关的标准，已由 Claude 改好卡面）：
  - 汽水音乐、网易云音乐链接导入并入库 · 进行中（2026-10-19-R210-photo-music-link-import）；
  - Photo Studio 导航整理、挑镜头页和音乐库页 · 待确认（2026-10-20-R220-photo-studio-ia-preview）。
- 执行：Codex 账号 1。总控：Claude（photo-content-os，账号 3）。
- 分段做，每段做完写汇报后**停下**，等 Claude 看过再开下一段。本单现在只开**阶段 A**。

## 0. 先读

1. 本目录 `DESIGN.md`（设计说明，权威），`mock/beat-map.html`（可交互设计稿，左下角切状态）。
2. 仓库根目录 `music-analysis.registry.json`：段落、标签、阈值、模型、改动规则的唯一来源。
3. `docs/discussions/2026-10-20-music-tagging/synthesis.md` 和 `record.md` 的「最终结论」「用户拍板」。
4. 项目 `AGENTS.md`、`develop/harness/fullstack-ai-harness.md`。
5. Harness Core（绝对路径 `$HARNESS_ROOT/Core/harnesses/`）：
   - `quality-ai-harness.md` 的「删除与精简」；
   - `ai-coding-error-lessons.md`；
   - `unreadable-is-not-absent-guard-card.md`；
   - `backend-ai-harness.md`；
   - `api-contract-ai-harness.md`；
   - `agent-collaboration-harness.md` 第 2–5 节（阶段 B 用）；
   - `task-worktree-harness.md`。

## 1. 工作区和边界

- **只用脚本建 worktree**，一个任务一个，不许自己 `git worktree add`：
  ```bash
  cd $SOFTWARE_ROOT
  python3 $HARNESS_ROOT/Core/skills/task-worktree/scripts/task_worktree.py create r223-music-beat-map --base origin/main
  ```
  - `.venv`、`.tools` 用软链接指向主目录，不复制。
  - 主目录里这些文件还没提交，开工时整份复制进 worktree，一起提交：
    - `docs/tasks/R223-music-beat-map/` 整个目录；
    - `music-analysis.registry.json`；
    - `docs/discussions/2026-10-20-music-tagging/` 整个目录；
    - `acceptance/requests/2026-W43/2026-10-20-R223-photo-music-beat-map/request.json`、`request.md`。
- **提交但不推送**：在 worktree 里提交。提交信息末尾两行：
  ```
  Request: 2026-10-20-R223-photo-music-beat-map
  Verify: 2026-10-20-R223-photo-music-beat-map/H-01, 2026-10-20-R223-photo-music-beat-map/H-02, 2026-10-20-R223-photo-music-beat-map/H-03
  ```
  推送和 `task_worktree.py finish` 由 Claude 问过用户后再做。
- **主目录的真实曲库不许动**：`~/Desktop/照片筛选/library/music/`。
  - 那里的 Studio（8765 端口，主目录老代码）正在用。
  - 迁移和补分析只在测试用的临时目录跑；真实曲库等代码合进主目录、Studio 重启后，由 Claude 安排一次性执行。
  - 不许重启或杀 8765 上的进程。自己起服务用别的端口，`LOCAL_MEDIA_ROOT` 指向临时目录。
- **和「剪辑手法」实现会话（R226，另一个会话也在用 cdx 1）的文件边界**：
  - 只归 R223：
    - `music-analysis.registry.json` 和它的规范、校验脚本；
    - `schemas/music-track.schema.json`；
    - `scripts/music_library/`；
    - 新的 `scripts/music_analysis/`、`studio/music_analysis.py`；
    - `studio/media_review.py` 的音乐部分；
    - `studio/static/review-music.js`；
    - 新的 `studio/static/beat-map.js`。
  - `studio/server.py`：只改 `/api/review/music…` 路由分发，加重新分析的 POST，再加启动分析队列的一行。`studio/api_contract.py` 的 `ROUTE_SPECS` 只加 R223 的路由；`schemas/studio-openapi.json` 用现有流程重生成，不手改。
  - `studio/static/review.css`：只改音乐页、`.bm-*`、`.tag`、`.tagfilters`、`.tg*`、`.trow` 相关规则。
  - `studio/static/styles.css`：由 R223 一次加四个令牌，`--sec-quiet:#33464A`、`--sec-build:#2E6E75`、`--sec-peak:#4FB3BD`，以及 R226 的 `--fam-cut:#3987e5`、`--fam-snd:#d55181`；R226 不碰这个文件。
  - 别的文件发现要改，先写进汇报的「越界需求」，不动手。
  - 遇到 R226 或别的会话造成的失败，只列出、不修。
- 不回退别人的改动，不杀别人的进程，不提交 worktree 以外的东西。

## 2. 阶段 A：删除授权 + 数据和后端（现在做）

### A1 删除「授权」（曲目版权标注）——做彻底

删除对象：曲目授权的数据、显示和说明。也就是：
- `license_status`、`attribution` 字段，`LICENSE_LABELS`；
- 「授权」列、「平台版权曲」「来源不明」「CC0」「CC BY」字样，`.license` 小标签；
- 「只用来定切点和在本机预览…」那段说明；
- 「授权未知不许当成可以发布」这类规则。

至少覆盖下面这些位置。开工时用下面的命令再扫一遍，逐条审阅剩余命中：

```bash
rg -n "license_status|LICENSE_LABELS|平台版权曲|来源不明|licenseTag|license--unknown|attribution|授权未知|版权曲" scripts studio schemas tests docs README.md
```

| 位置 | 做什么 |
|---|---|
| `schemas/music-track.schema.json` | 见 A2 |
| `scripts/music_library/library.py`、`platforms.py`、`client_files.py`、`musicdl_engine.py` | 删字段、删 `LICENSE_LABELS` 和所有赋值 |
| `scripts/import_music.py` | 命令行输出里删授权 |
| `studio/static/review-music.js`、`studio/static/review.css` | 删授权映射、`licenseTag`、授权列、右侧授权说明、`.license` / `.license--unknown`。阶段 A 只删，新设计在阶段 B 做 |
| `tests/test_music_library.py` 及其他断言授权的测试 | 只验证授权的断言删掉；仍有效的完整性和错误处理测试保留 |
| `scripts/verify_r220_browser.mjs`、`tests/test_r220_number_formulas.mjs` | 删授权相关检查 |
| `scripts/music_library/README.md` 第 22 行附近 | 删授权说法 |
| `docs/tasks/R210-music-link-import/TASK.md` | 当前规范里的授权取值表、规则、H-01 里的「平台版权曲」改成当前状态（需求卡已改，见卡） |
| `docs/tasks/R208-vlog-aesthetic-layer/PRD.md` 第 78、80、131 行 | 删掉「标成平台版权曲」、「逐首记下授权、存授权页、CC0/CC-BY/CC-BY-NC」规则和「逐首存授权」；补充来源只保留候选来源和「不批量抓站」 |
| `docs/tasks/R220-studio-ia-preview/design-contract.json`、`resolved-surface-contract.json`、`TASK.md` 第 266 行 | 去掉音乐页的授权文案和「写着来源平台和授权」；音乐页的设计以 R223 为准，R220 合同里的音乐状态要和 R223 不矛盾 |

**不要动**（不是曲目授权）：
- 第三方软件许可证和声明：`scripts/music_library/*.LICENSE`、`THIRD_PARTY_NOTICES.md`、`edit-tools.lock.json`、清单里模型和包的 `license`；
- 剪辑交接里的软件许可证：`workflow.css`、`handoff.js` 的 `.license`，`edit_backends/*`；
- 账号或同步「授权」的说法：`README.md`、`scripts/music_library/README.md` 第 52 行；
- 成片检查素材来源的 `license`：`scripts/review_output_video.py`；
- 模型许可证：`scripts/shot_aesthetics.py`；
- 署名称呼：`scripts/llm_common.py`；
- 历史汇报、证据、`repository-safety-path-baseline.json`；
- 别的会话的目录：`docs/tasks/R226-*`、`R225-*`、`R228-*`。

### A2 曲目规范升 v2，迁移脚本

- `schemas/music-track.schema.json` 升 `schema_version: 2`，删掉 `license_status`、`attribution`，以及 `bpm`、`beats`、`sections` 三个永远为空的占位字段。分析结果改放旁挂文件（A5）。
- 索引 `index.json` 同步升 v2；`library.py` 的读写和一致性检查只认 v2，**不留读 v1 的兼容分支**。
- 新写 `scripts/migrate_music_library_v2.py`：
  - 默认只预演，`--apply` 才写；
  - 写之前把 `index.json` 和全部 `track.json` 备份到仓库外 `~/.photo-content-os/backups/music-library-v1-<时间戳>/`，备份失败就不写；
  - 写完逐首校验 v2 规范，再跑一遍等于什么都不改（幂等）；
  - 音频、`peaks.json`、`.attempts/` 都不动。
- 测试：用临时目录造 v1 曲库，覆盖预演、备份、应用、幂等、备份失败拒写，以及 v1 数据在新代码下被明确拒绝（报「先运行迁移」，不是悄悄当空）。
- **阶段 A 不对真实曲库执行迁移。**

### A3 清单的规范和校验门禁

- `schemas/music-analysis-registry.schema.json`、`scripts/validate_music_analysis_registry.py`。现有 `scripts/validate_review_capability_registry.py` 是同类做法，可以参考。
- 规则来自清单 `governance.rules`，校验至少要拦住这些情况：
  - 编号重复；
  - 启用的标签没有中文名；
  - `display` 引用了不存在的类别；
  - 阈值不在 0–1；
  - 模型缺 `sha256` 或 `license`；
  - 和 `origin/main` 上的版本比：删掉了已发布的编号（只许改成 `deprecated`）；内容变了但 `registry_version` 没加 1，或者 `changelog` 没追加；
  - 清单里的中文过不了文案检查。文案检查用 `$HARNESS_ROOT/Core/skills/ui-copy-quality/scripts/check_ui_copy_quality.py`，和设计稿用的同一个。
- 读不到清单、读不懂、输入为零时返回非零，不许报通过。
- 红绿测试逐条覆盖上面的情况。
- 把校验加进项目检查：`.harness/overlays/project-harness-adapter.yaml` 的 `static_guards`，以及 `AGENTS.md` 的 Required checks；写明失败类和修法。

### A4 分析工具环境

- 独立环境：放在 `.tools/music-analysis/`，不进 Studio 主环境。
  - 包：`beat-this==1.1.0`（另需配套的 torch / torchaudio）、`librosa==1.0.0`、`essentia-tensorflow==2.1b6.dev1389`。
  - Python 版本自己按轮子选，在汇报里写明理由。2026-10-21 实测，3.12 下 essentia 能跑；cp313 的 macOS arm64 轮子也有。
- 按 R207 的做法写进锁定清单和安装脚本：`third_party/edit-tools.lock.json`、`scripts/setup_edit_tools.*`，参照 `docs/edit-tools-runtime-guard.md`。源码里不许出现用户绝对路径。
- 模型文件按清单 `analyzers.tags.models` 的地址下载，逐个校验 `sha256`，不一致就报错停下；放 `.tools/music-analysis/models/`。
- 许可证：beat-this（MIT）、librosa（ISC）、essentia（AGPL-3.0-only）、MTG 模型（CC BY-NC-SA 4.0）的全文和来源，写进 `scripts/music_library/THIRD_PARTY_NOTICES.md` 或同级新文件。
- 分析过程不联网（只有安装时下载一次），也不调用任何大模型。
- 分析环境放在 `.tools/` 后，`tests/test_p1_openclaw_bridge.py::test_core_has_no_mandatory_openclaw_media_dependency` 会扫到 essentia 里一个 Python 2 写法的文件而报错（2026-10-21 另一个会话报告）。把这条测试改成只扫 Git 跟踪的 `.py` 文件，它要查的本来就是我们自己的代码；不许把分析环境挪出 `.tools/` 来躲开这条测试。

### A5 分析程序和结果文件

- `scripts/music_analysis/`：在 A4 的环境里以子进程运行，JSON 进 JSON 出，有超时。一首歌产出：
  - 拍点 `beats`、重拍 `downbeats`（beat_this）；
  - 每拍响度 `beat_energy`：librosa 按拍算 RMS，按整首 5%–95% 分位归一到 0–1；
  - 段落 `sections`：按清单 `sections.rules`，小节能量分三档，短于 `min_bars` 的段并进相邻段；
  - 四个分类头的**全部**原始分数：genre 400、moodtheme 56、instrument 40、voice 2；
  - 所用包版本、模型编号、`registry_version`。
- 失败码：`audio_unreadable`、`worker_error`、`timeout`。拍点和标签成败分开记。没认出的失败原样记代号，不归并成已知原因。
- 结果放每首歌目录下的 `analysis.json`，写 `schemas/music-analysis.schema.json`，原子写。
- 拍点和段落的质量要求（需求卡 H-02）：
  - 时间戳递增、不超出曲长；`downbeats` 是 `beats` 的子集；`beat_energy` 和 `beats` 一样长。
  - 用合成的点击音轨做测试：已知 120 BPM，测出 BPM 误差不超过 1；裁掉开头 0.5 秒重跑，内部拍点约提前 0.5 秒（排除边界，容差写进测试）。

### A6 显示用标签的取舍（共享实现）

- `studio/music_analysis.py` 里写一个函数：按清单规则，从原始分数算出要显示的标签。必须和设计稿 `mock/beat-map.html` 里的 `derive()` 结果一致。
- 用设计稿的数据做测试夹具：`mock/beat-data.js` 里的 `scores`，复制到 `tests/fixtures/r223/`，不含路径。期望结果：
  - Turn Back Time：风格「电子」，细分 Tropical House；情绪「深沉」「欢快」；场景「夏日」；有人声；乐器贝斯、合成器、键盘。
  - Fever Pitch：「电子」，细分 House；情绪「深沉」；场景「夏日」；人声**拿不准**；乐器贝斯、合成器、键盘。
  - CRUSH VIBE：「电子」，没有细分；情绪「旋律优美」「太空感」「暗黑」；场景为空；纯音乐；乐器合成器、采样器。
- 改清单的名字、阈值、状态后再读，结果立刻变，不重跑模型。这一点要有测试。
- 同一个模块提供给 R226 的读取函数 `load_beat_map` 和异常 `BeatMapUnavailable`。签名、返回形状和失败码**照 `DESIGN.md` 第 10.1 节，一个字不改**，因为 R226 已经按这个形状在写。每个失败码都要有测试，包括读不懂结果文件和不返回半成品。

### A7 分析队列

- Studio 进程内一个分析队列，一次处理一首：
  - 导入成功后自动排队；
  - 启动时把缺 `analysis.json` 的歌补进队列；
  - 记录排队位置。
- 重新分析接口：`POST /api/review/music/<编号>/reanalyze`，参数 `part=beat|tags`，只重跑这一部分。重复点击不能排两份。
- 队列里出错不能拖垮 Studio，读不到结果要明确报错。

### A8 接口

- `GET /api/review/music` 按 `DESIGN.md` 第 9 节：
  - 顶层加 `registry_version` 和 `taxonomy`（清单里的段落、类别、标签名、`empty_text`、`uncertain_text`、`display`）；
  - 每首加 `beat`、`tags` 两个对象，带状态、排队位置、失败码；
  - 原始分数不随列表下发。
- `ROUTE_SPECS` 加新路由，按现有流程重生成 `schemas/studio-openapi.json`。`tests/test_desktop_openapi_route_sync.py` 要绿。
- 契约测试覆盖每种状态：已完成、排队、分析中、节拍失败、标签失败、音频读不出、未知代号。

### A 阶段要跑的

- `AGENTS.md` 的 Required checks 全部跑（`check_runtime_contract.sh`、`check_repository_safety.py --base origin/main`、`check_obsidian_doc_sync.py`、`check_outline_contract.py`、`pytest -q tests` 等），加上 A3 的新校验。
- 在 worktree 里起一个 Studio：
  - 端口不是 8765，媒体根指向一个临时曲库；
  - 临时曲库里放 3 首**你自己合成**的测试音频，不用用户的歌；
  - 跑完整条路径：导入 → 自动排队 → 分析 → 接口返回节拍和标签；再触发一次失败和一次重新分析。
- 机器证据：文字放 `evidence/2026-10-21/R223-music-beat-map/`；图片、音频放仓库外 `~/.photo-content-os/evidence/R223-music-beat-map/`。证据里不许有用户的歌、私人路径。

### A 阶段汇报（写完停下）

汇报写进本目录 `REPORT-A.md`，同时作为最后一条消息输出：

1. 做了什么，按 A1–A8 分节，每节写改了哪些文件、怎么验证的。
2. A1 的删除：扫描命令、剩余命中逐条说明保留理由；以及验证过的三件事：
   - 应保留的行为正常；
   - 旧字段、入口、别名、回退都没了；
   - v1 数据被明确拒绝。
3. 测试和检查结果原样附上（命令、退出码、通过数）；没跑的写明。
4. 真实曲库迁移和补分析的执行步骤：备份位置、命令、怎么回退。等 Claude 安排，不要执行。
5. 「越界需求」「需要新文案」「需要拍板」三节，没有写「无」。

## 3. 阶段 B：前端照稿实现（等 Claude 开）

阶段 A 汇报通过后，Claude 会补上阶段 B 的细则。范围先写在这里，让你知道 A 要给 B 留什么：

- 照 `mock/beat-map.html` 实现：右侧节拍图、AI 标注区、速度行、列表的速度列和标签行、分面筛选、筛选后没有歌、全部失败和排队状态。
- 名字和顺序全部从接口的 `taxonomy` 读，前端不写死。
- 共用节拍图模块 `studio/static/beat-map.js`：`mountBeatMap` 的签名照 `DESIGN.md` 第 10.1 节，不改；R226 的入口（切点、淡出、多首歌、关掉放大区、`onSeek`、`onSwapClick`、`selectedSwap`）都要实现并有测试；「换歌」标签用 `button.bm-swap`，选中态用 `aria-pressed="true"`。
- 四道检查都要跑：文案表比对、设计编号比对、数字公式（`DESIGN.md` 第 6 节）、人话与观感。
  - 文案表：`mock/design-contract.json`，加上清单里的全部中文。
  - 状态：设计稿每个状态都有夹具，再加真实数据的最差首屏。
- 截图：1440、1180、430 三种宽度。汇报第一节是「和设计稿哪里不一样」，逐个状态并排对照。
