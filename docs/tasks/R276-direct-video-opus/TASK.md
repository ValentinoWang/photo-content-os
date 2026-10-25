# R276 一键直出：Opus 按口播稿写每一镜动画，本机渲染出成片 · 后端任务单

需求卡：「Studio 里一键直出：Opus 按口播稿写每一镜动画，本机渲染出成片 · 待确认（2026-10-26-R276-photo-direct-video-opus）」，在 `acceptance/requests/2026-W44/2026-10-26-R276-photo-direct-video-opus/`。验收项 H-01–H-03 原样照卡，不许自行改。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（会话名 photo-content-os-f8，账号 3）。本单只做**后端**；前端等用户认可设计稿后另派。

目标：**2026-10-26 上午**能在 Studio 里从「粘贴口播稿 → 点生成」跑到「播放成片」。

## 0. 工作位置和边界（必须遵守）

- 只在任务 worktree 里改：`/private/tmp/task-worktrees/photo-content-os-r276-direct-video`（总控已用 `task_worktree.py create` 建好，基于 origin/main `2263a04`）。**不许**自己 `git worktree add`，不许改主目录 `~/Desktop/创业项目/photo-content-os`（主目录里有别的会话没提交的 R226/R227/R228 改动，`studio/server.py`、`studio/api_contract.py`、`schemas/studio-openapi.json` 都在其中）。本任务单放在主目录 `docs/tasks/R276-direct-video-opus/`，只读；收尾时由总控把它和设计稿一起放进提交。
- 不提交、不推送、不回退别人的改动、不杀别人的进程。端口 8765 上的 Studio 是用户正在用的，不许动它。
- 遇到要拍板的事：先做不受影响的部分，把问题写进汇报后停下。
- 证据（日志、JSON）放 worktree 里的 `evidence/2026-10-26/R276-direct-video-opus/`；渲染出的帧、MP4、截图一律放仓库外 `~/.photo-content-os/evidence/R276-direct-video-opus/`。

## 1. 先读

- `AGENTS.md`、`CONTRIBUTING.md`、`docs/execution-rules.md`（worktree 里）。
- `scripts/video_render/README.md` 和 `multi_shot.py`、`compose.py`、`animation_duration.py`：渲染器已有，本任务**复用，不重写**。
- `scripts/llm_common.py`：产品里的模型调用统一走 `generate_text`。Core 规则 `~/Desktop/Opensource_Tool/Harness_Engineering/Core/harnesses/ai-egress-ownership-guard-card.md`：新的 AI 调用必须走这个统一入口，不许在别处直接起模型进程。
- `studio/server.py`、`studio/api_contract.py`、`studio/video_workflow.py`：路由登记、CSRF、隐私投影、媒体 Range 返回的现有写法，照着写。
- 镜头代码规则来源（用户自己的技能，只读）：`~/.claude/skills/direct-video-shots/SKILL.md` 和同目录 `scripts/lint_shots.py`、`scripts/preview_frames.py`。
- 实跑参考（上游仓库，只读）：`~/Desktop/创业项目/自媒体创作Agent/docs/development/video-practice-hiatus/`（`storyboard.json`、`shots/01–07.html`、`AUTHOR-NOTES.md`）和 `~/Desktop/创业项目/自媒体创作Agent/agents-results/2026-10-15/R131-hiatus-video/v4-form/run23/`（`narration.wav`、`final-video.json` 里的十镜口播和句级时序）。

## 2. 要做什么

### 2.1 模型入口：`llm_common.generate_text` 加 `claude_cli`

- 照 `generate_text_with_codex_cli` 的写法加 `generate_text_with_claude_cli`，provider 名 `claude_cli`（别名 `claude`、`claude-cli`）。默认模型 `claude-opus-5-5`。
- 命令行先用 `claude --help` 核实参数，再定写法。要求：
  - 非交互（`-p`），输出可解析；
  - **不给工具、不连 MCP、不读用户和项目的 CLAUDE.md/设置/钩子**（产品调用要和用户自己的 Claude Code 会话隔离），在一个空的临时目录里运行；
  - 提示从标准输入或临时文件传，不拼进命令行；
  - 超时可配（默认 300 秒），超时、非零退出、空输出都抛 `LLMError`，错误信息不带提示原文；
  - 可执行文件用 `OPENCLAW_CLAUDE_BIN` 覆盖，否则 `shutil.which('claude')`（本机 shell 里 `claude` 是个函数，子进程里要找到真实路径 `npm-global/bin/claude`）；登录目录用 `OPENCLAW_CLAUDE_CONFIG_DIR` 覆盖，不设就继承环境。
- **第一件事**：从一个和 Studio 一样的后台子进程里实测一次 `generate_text(provider='claude_cli', model='claude-opus-5-5', …)`，返回「ok」即通过。把实测用的账号目录、耗时、成败写进汇报。调不通就停下汇报，不要往下做。
- 测试用假的可执行文件（写一个脚本冒充 claude），不在测试里真调模型。

### 2.2 生成器：`scripts/direct_video/`

把技能里的规则和检查搬进仓库（文件头写来源：用户技能 `direct-video-shots`，规则部分借自 HeyGen HyperFrames，Apache-2.0）：

- `rules/shots.md`：从 SKILL.md 摘出写代码要遵守的部分（渲染器硬规则、每一镜怎么动、默认禁用、观感）。只摘规则，不搬「交付」「审片」里给人看的流程。
- `lint.py`：移植 `lint_shots.py`，改成函数调用（输入代码文本和这一镜的口播、时长，返回 `errors[]`、`warnings[]`，每条带 `code`、中文 `message`、可选 `atSeconds`），命令行入口保留。
- `generate.py`：
  1. **全片设计**：一次调用。输入每镜口播（和可选的风格说明），输出 JSON：`palette`（background、primary、accent、neutral 四个颜色）、`typeScale`（三档字号）、`motionRules`（一句话）、`banned`（不用的套路，3–6 条）、`perShot[]`（`shotId`、`mainAction` 唯一主动作、`takeaway` 观众读到什么）。
  2. **逐镜写代码**：每镜一次调用，**最多 3 镜同时写**（可配）。输入全片设计、这一镜口播、前后镜口播、时长 `D`、镜号/总镜数。输出 JSON `{"code": 完整 HTML}`。校验：以 `<!doctype html>` 开头、含 `window.seekFrame`、有 `data-role="header"`、不超过 100,000 字。
  3. **自查**：每镜写完立刻 `lint`。有 error 时把错误原文附上，自动让 Opus 重写这一镜**一次**；还有 error 就标失败，不再重试。warning 只记录。
  4. **渲染**：每镜写好（或重写好）立刻单独渲染，不等其他镜。用 `video_render/multi_shot.py` 的现有函数和帧缓存；每镜存一张关键帧 JPEG（取 0.8·D 那一帧，短边 ≤ 360），作为页面上的海报。
  5. **时长**：没有配音时 `D = 口播字数（含标点）÷ 5.1`，保留一位小数。上传配音后，先用本机转写（`transcribe_audio.py` 的本地 FunASR，逐字时间）把每镜口播对到配音上，得到每镜实测时长；对不上就按字数比例分配整段配音时长，并在结果里标 `timingSource: 'proportional'`。实测时长比代码里的 `D` 短的镜，按实测 `D` 自动让 Opus 重写一次（这就是 R131 第 04 镜踩过的坑：动画比配音长会被切掉）。
  6. **合成**：没有配音 → 用逐镜帧出**无声预览** MP4；有配音 → `video_render/compose.py` 出带声成片。合成后跑 `video_candidate.py` 现有的检查（能播放、音画差、帧数、黑帧），结果写进任务。
  7. **重写一镜**：输入一句修改意见，只重写、只重渲这一镜；其他镜的代码、关键帧、写好时间都不变（验收 H-03 要看这个）。
- 任务状态落盘：Studio 状态目录下 `direct-jobs/<作品编号>/<任务编号>/`（`job.json`、`design.json`、`shots/NN.html`、`checks/NN.json`、`posters/NN.jpg`、帧缓存、`output.mp4`）。所有写入原子化；进程重启后能从 `job.json` 读回当前状态，正在写的镜标「中断」，可重试。

### 2.3 Studio 接口（`studio/direct_video.py` + `server.py` 登记路由 + `api_contract.py` + `schemas/studio-openapi.json`）

照现有路由写法登记，写请求照旧要 loopback、同源、`X-Content-OS-CSRF`。**投影里不出现任何本机绝对路径**。

| 方法 | 路径 | 做什么 |
|---|---|---|
| POST | `/api/projects/{id}/direct/jobs` | body `{script: 一行一镜的文字}` 或 `{storyboard: {shots:[{shotId, dialogue}]}}`，可选 `style`、`model`（只收 `claude-opus-5-5`）。建任务并在后台开始；返回任务投影 |
| GET | `/api/projects/{id}/direct/jobs/latest` | 这件作品最近一个任务的投影；没有返回 `{job: null}` |
| GET | `/api/projects/{id}/direct/jobs/{jobId}` | 任务投影 |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/rewrite` | body `{instruction}`（1–200 字），只重写这一镜 |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/narration` | 请求体直接是 WAV（`Content-Type: audio/wav`，≤ 100 MB），校验能解码；之后自动重算时长、必要时重写、重渲 |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/compose` | 合成成片（有配音带声，没有就无声预览） |
| GET | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/poster.jpg` | 关键帧 |
| GET | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/code` | 这一镜的代码，`text/plain; charset=utf-8` |
| GET | `/api/projects/{id}/direct/jobs/{jobId}/output.mp4` | 成片，支持单段 Range（照现有媒体接口） |

任务投影（前端照这个画，字段名定了不要改）：

```json
{"ok": true, "job": {
  "jobId": "dv_…", "projectId": "…", "model": "claude-opus-5-5",
  "status": "designing | writing | rendering | ready | composing | done | failed",
  "createdAt": "…", "updatedAt": "…", "failureCode": null,
  "design": {"status": "pending | writing | done | failed",
             "palette": {"background": "#…", "primary": "#…", "accent": "#…", "neutral": "#…"},
             "typeScale": [132, 72, 44], "motionRules": "…", "banned": ["…"]},
  "shots": [{"shotId": "01", "dialogue": "…", "mainAction": "…",
             "estimatedSeconds": 2.4, "measuredSeconds": null, "timingSource": "estimate | narration | proportional",
             "status": "queued | writing | written | rendering | rendered | failed | interrupted",
             "failureCode": null, "attempts": 1, "lastInstruction": null,
             "writtenAt": "…", "renderedAt": "…", "codeChars": 1771, "posterRevision": 2,
             "checks": {"errors": [{"code": "…", "message": "中文一句", "atSeconds": 1.6}], "warnings": []}}],
  "narration": {"status": "none | aligning | ready | invalid", "durationSeconds": null},
  "output": {"status": "none | composing | ready | failed", "kind": "silent | narrated",
             "durationSeconds": null, "frames": null, "revision": 0,
             "checks": {"playable": "pass | fail | unknown", "avOffsetSeconds": null, "blackFrames": null}}
}}
```

`failureCode` 用受控的英文代码（如 `claude_cli_unavailable`、`model_timeout`、`code_invalid`、`lint_failed_after_retry`、`render_failed`、`narration_invalid`），前端负责翻成中文；投影里不放原始报错正文。

### 2.4 测试

- 新增 `tests/test_r276_*.py`：假 claude 可执行文件；全片设计和逐镜代码的 JSON 校验；lint 的 error/warning；自动重写只一次；重写一镜不动其他镜（代码、关键帧、写好时间）；配音对齐失败时按比例分配并标记；任务重启后读回、写到一半的镜标中断；接口投影无绝对路径；未登记路由 404；CSRF。
- 渲染相关的测试在本机没有 Playwright/浏览器时跳过，并在汇报里写明跳过原因。
- 跑：新测试；`tests/` 里和 `llm_common`、`api_contract`、`server`、`video_render` 相关的现有测试；`bash scripts/check_runtime_contract.sh`；`.venv/bin/python scripts/check_repository_safety.py --base origin/main`。全量 pytest 跑一次，失败逐条判断是不是本任务造成的（不是的只列出）。

## 3. 分段

- **第一段（A）**：2.1 实测打通 → 2.2 生成器（可先用假模型）→ 2.3 接口 → 2.4 测试。做完写汇报 `docs/tasks/R276-direct-video-opus/REPORT-A.md`（写在 worktree 里），列：改了哪些文件、实测 claude 调用结果、测试命令和结果、没做完的、要拍板的。**然后停下。**
- **第二段（B，总控看过 A 再开）**：真跑。用 R131 第四版十镜口播 + `narration.wav`：从 worktree 起一个独立的 Studio（端口 8766，状态目录 `~/.photo-content-os/studio-r276/`，先复制一份 `creative-projects.json` 进去），按接口建任务、等写完、上传配音、合成，拿到带声成片；记录每镜写代码耗时、自动重写次数、总耗时。

## 交接

### 交接 1（2026-10-26，总控）

- 第一段 A 完成，Codex 线程 `01a173fd-b053-7130-bde1-b8c270f85596`（账号 cdx 1），汇报在 worktree 的 `docs/tasks/R276-direct-video-opus/REPORT-A.md`。后台调 Opus 实测 7.0 秒返回；新测试 47 项。
- 总控复核：本机 Playwright 用上游的 `apps/media/web/node_modules/playwright`（1.61.1），浏览器要指到 `chromium_headless_shell-1228`；这样真实 HTML 渲染测试通过。本机 ffmpeg 没有 drawtext，本任务不烧字幕，设计稿已去掉「字幕已烧录」。
- 全量 pytest 的 9 失败 6 错误都是既有问题（drawtext 缺失、Obsidian 文档时间戳），与本任务无关。
- 第二段 B（真跑十镜带配音、七镜无配音、单镜重写）已在同一线程续跑，汇报写 `REPORT-B.md`。
- 前端：设计稿 `design/index.html`、`design/direct.html`，等用户认可后派 cdx 2。

### 交接 2（2026-10-26，总控）

- 第二段 B 通过（REPORT-B.md）：七镜从建任务到全部写好渲染 8 分 16 秒；十镜带声成片音画差 0；第 03 镜按意见重写 71 秒，只这一镜变。联系表和成片在仓库外 `~/.photo-content-os/evidence/R276-direct-video-opus/`，总控已逐张看过。配音对齐这次走的是按字数比例（`proportional`），内部切镜最大偏差约 1 秒，逐字对齐没做到，留作后续。
- 第三段 C 通过（REPORT-C.md）：加了 `writingStartedAt`、中断或失败的镜可空意见重试、构图提醒 `layout_bottom_gap`（只提醒不重写）。总控原以为 B 的关键帧主画面挤在上 60%，亲自量过 7 张关键帧，内容下沿都在 y≈1400–1500，紧贴字幕带，是总控看错了；构图检查保留，取消「至少 10 张要报」那条要求。
- 前端 F1 通过（REPORT-F1.md），和稿基本一致。总控据 F1 的问题更新了设计稿和合同（13 个状态，见 design/index.html 第 1 节「F1 后的改动」）。F2（接新字段、真实环境截图）在前端线程 `01a1742b-35f5-75a3-bb11-7897ecfb9137`（账号 2）续跑，汇报写 REPORT-F2.md。
- 还没做：提交（等 F2 验收）、推送（要过交付检查）；R277（会话 photo-content-os-b5）等 R276 的提交号开工。
