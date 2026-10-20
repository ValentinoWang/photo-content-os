# 问题卡：音乐库的标签现状，以及怎样和开源项目配合

- 模式：讨论；质询最多 1 轮
- 要回答的问题：Studio 音乐页（`http://127.0.0.1:8765/#view=music`）里的歌，现在有没有打标签？如果要打或补打，怎样和现有的开源项目配合？
- 要做的决定：用户据此决定要不要做音乐标签和分析，选哪些开源项目、以什么方式接入（装成依赖调用、子进程调用、只借思路），以及先做哪一步。
- 背景（只写事实，不写倾向）：
  - 音乐页由 `studio/static/review-music.js` 渲染，数据来自 `GET /api/review/music`，服务端在 `studio/server.py`、`studio/media_review.py`。本机服务正在 `127.0.0.1:8765` 运行（`scripts/launch_studio.py`），可以对这个接口发只读 GET 看真实数据，目前库里 3 首。
  - 用户没有限定「标签」指什么：可能是页面上已经显示的标注（来源、授权等），也可能是选曲用的描述性信息（风格、情绪、BPM、能量、段落、乐器、人声有无等）。两种都要回答。
  - 入库代码：`scripts/music_library/`、`scripts/import_music.py`。导入需求和历次汇报：`docs/tasks/R210-music-link-import/`。
  - 音乐分析、推荐、卡点的规划：`docs/tasks/R208-vlog-aesthetic-layer/PRD.md`（§3 参考项目、§4.3 背景音乐、§4.4 节奏编排、§5 分阶段、§6 待确认、§7 依赖与许可）。阶段 A 的任务单：`docs/tasks/R208-vlog-aesthetic-layer/TASK-A.md`。
  - 已接入或放在本机的第三方：musicdl（见 R210 TASK.md）、`third_party/`（openfilm、browser-runtime，版本钉在 `third_party/edit-tools.lock.json`）、`reference/hypit`（本机参考，不进 git）。剪辑交接合同：`scripts/edl_contract.py`、`docs/studio-contract-and-privacy.md`。
  - 许可前提：R210 TASK.md 写明本项目是课程项目、自己用、不商用，在这个前提下 PolyForm Noncommercial、AGPL 等都可以直接安装和复用代码，须保留许可证全文、记来源。
  - 机器：macOS，Apple Silicon，本地 Python。
- 约束：
  - 本地与云端的边界、哪些东西不能发出本机：`docs/studio-contract-and-privacy.md` §2；产品里的 AI 调用须走运行时声明的 AI 网关：`/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/harnesses/ai-egress-ownership-guard-card.md`。
  - 只读：不改文件、不装依赖、不起服务，对 8765 只发 GET。
- 证据在哪：
  - 仓库：上面列的路径；测试在 `tests/`（可 `rg music` 找）。
  - 资料：R208 PRD §3、§7 里列的开源项目链接；需要时自己查项目主页核实许可、维护状态、Mac 上能不能跑。
  - 附图：无。
- 不讨论：导入和下载链路本身的修复（R210）、镜头挑选（R208 阶段 A）、页面视觉。
- 输出格式：
  1. 先用 1–3 句直接回答「现在有没有打标签」，写明相关字段在真实数据里的取值。
  2. 论点表：编号 | 结论 | 证据（文件:行号 / URL）| 把握（已核实/推断/猜测）| 建议
  3. 配合方案表：开源项目 | 负责哪类标签或分析 | 接入方式（依赖调用 / 子进程 / 只借思路）| 许可 | Mac 上能不能跑、要多少资源 | 把握
  4. 建议的第一步：做什么、产出什么、怎么验收。
  5. 不建议做的：每条一句理由。
  6. 按价值从高到低排；总长不超过 3000 字。
