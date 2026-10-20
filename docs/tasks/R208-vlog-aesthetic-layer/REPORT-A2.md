# R208 A2 汇报

日期：2026-10-20（Asia/Taipei）。本报告记录真实全量运行、视觉复核和交付停止边界。

## 实现范围

在原 worktree `/private/tmp/task-worktrees/photo-content-os-r208-a1` 继续，只做挑镜头；不做音乐、节奏、粗剪工程或产品审阅页。

- 清晰度统一到长边 640 px，4×4 分块，取方差最高两块的均值。保存 16 块原始值和整帧对照值。候选三帧的均值用于软标记，最清晰帧用于硬淘汰判断；项目中位数和比值只作诊断。
- 硬淘汰仅保留：各采样帧都近乎全黑/全白（≥98%）、各帧最清晰两块仍低于 40、极端抖动 >0.024、时长 <0.8 秒。软清晰度阈值 200；曝光偏 >25%、抖动 >0.008、跟踪不足只标记和扣分，每项扣 0.25。曝光只有一帧全白不会硬淘汰整个候选。
- 所有有图且没有硬淘汰理由的候选都按场景分页送多模态模型，每页最多 8 条，不再截取前三名。拼图标出软问题。重复组仍复用原有感知哈希实现，重复备选同样送审，最终不进精选或钩子。
- 模型必须返回三个严格布尔字段：`has_title_or_sticker`、`has_watermark`、`has_occlusion`。每张常规拼图附三帧各自的四角放大图，避免小水印/手指在缩略图中漏检；任一为真不能进入精选；保存原始模型结论和最终状态，理由追加可核对的视觉标记。真实标牌、号码布不当作后贴标题。
- 提示词限制可见事实，禁止猜场所功能、行程方向、人物身份；使用文件名必须写“据文件名”。复用 `load_creator_context`，缺省使用任务指定账号定位，运动/身体类镜头优先。
- `llm_common` 只为 Codex 子进程复制环境并前置当前 Python 所在 bin。未改全局 PATH、账号或配置；已删除 `.tools/bin/codex-r208`。
- 取消第二模型对比与 L/14 CLI 入口，B/32 只作本地初筛，多模态看图决定取舍。没有下载 L/14。

实现文件：`scripts/select_shots.py`、`scripts/shot_quality.py`、`scripts/shot_aesthetics.py`、`scripts/shot_selection_config.json`、`schemas/shots.schema.json`、两份 R208 测试；追加 `requirements-dev.txt`，`.gitignore` 只追加 `.tools/`。A2 另修改 `scripts/llm_common.py`。既有 `scripts/edit_backends/`、doctor、安全检查脚本和 README 未修改。

## 素材盘点

本次实际发现 36 段 primary 视频、1 段 `travel/raw-pending` 待选视频、5 个 primary 图像文件（含标题参考图），全部纳入体检；待选文件没有被改成正式来源。A1 报告写的“41 段正式视频”不准确，以本次完整清单为准。未改动 PRD 的历史素材数字。

| 目录 | 视频 | 图像 | 处理 |
|---|---:|---:|---|
| selfie-moments | 11 | 2 | 全部分析 |
| sports-meet | 6 | 2 | 全部分析 |
| travel（含 raw-pending） | 20 | 1 | 全部分析；待选单列来源 |
| icloud-selected | 4 | 1 | 精选副本，排除；逐一 SHA-256 与以上正式来源完全一致 |
| raw-vault | 2 | 0 | 原始归档，按任务排除 |
| draft-project / output / ai-analysis | 派生文件 | 派生文件 | 排除 |

全扩展名审计另确认没有 DNG/RAW/JFIF 等未支持格式被漏掉，剩余仅项目 Markdown/JSON。素材整理记录还注明旧 `IMG_6189.MOV`、`IMG_6192.MOV` 源缺失；本次只承诺扫描当前项目内可读文件，没有把历史缺源算作完成，也未回查原始导入盘。

正式目录中的五个图像文件是标题截图参考、成绩表 HEIC、跑道自拍 HEIC、AI 超清冲刺 JPEG、机舱办公 HEIC，没有漏掉独立的照片目录。父目录另外两个项目分别有 224 和 8 张非派生照片，属于 `2026-lzu-group-and-honors`、`2026-lzu-400m-pov`，本次不混入它们。证据见 `source-before.json`、`photo-discovery.json`、`photo-parent-counts.json`。

## 测试与真实运行

先写负例：新增 A2 用例首次为 10 个失败，日志 `negative-first.log`；另补“只有一帧全白不能硬淘汰”负例，首次失败保存在 `negative-partial-white.log`。修复后相关测试 33 项全部通过，包括合成前景清晰/平面背景、高斯模糊、随机抖动/平滑横移、全部分页、三项严格布尔、缺失/幻觉编号、上下文与 Python PATH。原 A1 关于“过曝一律硬淘汰”和“重复项硬淘汰”的断言按 A2 改为全白淘汰、重复备选单列；未知项及引用完整性保护保留。

| 检查 | 结果 |
|---|---|
| 相关测试 | 33 passed |
| 全库 pytest | 603 passed、32 skipped、9 failed、6 errors、1982 subtests passed |
| 与 A1 原基线对照 | 15 个失败/错误测试编号完全相同，无新增失败 |
| runtime contract | 通过 |
| Obsidian doc sync / outline | 失败：已有脚本文档 mtime 比 Obsidian 页面新；与 A1 相同，未改这些文件 |
| 两个协议校验器 --help | 通过 |
| pip check / selector --help / 源码 git diff --check | 通过；CLI 已无 L/14 和双模型对比入口 |

Python 根因：原环境的 `python3` 是 `/usr/bin/python3` 3.9.6，Switch Codex 包装器采用 `#!/usr/bin/env python3`，因此缺 `tomllib`。当前固定虚拟环境为 3.13.16，修复后子进程首先解析其 `bin/python3`。负例把 PATH 前端伪装成退出码 99 的旧 Python，仍能通过实际 env-python 包装器导入 `tomllib`；真跑另行验证。细节见 `python-runtime.json`。

全量首次执行随外层会话退出中断；不是代码异常。该次 A2 数值尚未从内存保存，盘上的 shots.json 仍是 A1，323 张帧图不具备完整区间/运动记录，未冒充已完成体检。恢复脚本 `evidence/2026-10-20/R208-A2/resume-full.py` 对源文件逐一核对 SHA-256/大小/mtime，并确认切分和运动参数与 A1 相同后，复用 10 段视频的区间和运动测量；所有清晰度帧重新从原素材抽取，B/32 分和多模态全部重跑。其余 27 段视频重新体检。每个完整源文件在 ai-analysis/shots/cache/checkpoints 原子保存原始测量，续跑只认完整记录，不凭帧图数量判完成。

补了重复备选负例（`negative-duplicate-alternative.log`）：模型审过的清晰备选可以是可用，只有组内代表可以精选；避免把四个重点镜头中的重复备选再次直接改成不用。提示词明确这一点，原始分组和代表编号不被模型改写。

本地总量为 123 段视频候选 + 5 张照片 = 128 条、374 帧；125 条非硬淘汰候选全部送审，18 张常规拼图。体检软标记（可重叠）：跟踪不足 37、抖动 25、轻度糊 4；另有重复备选 21 条。硬淘汰仅 3 条 too_short；没有全黑/全白、极糊或极端抖动触线的真实例子。必需帧/美感测量 unknown 为 0；跟踪不足仍保存 null 和标记，没有冒充已量出可靠抖动。

B/32 使用 MPS，374 帧实测均值 0.061 s/帧、中位数 0.050 s/帧，首帧 0.881 s；总评分时间 22.80 s。候选美感分 min/median/max = 2.966 / 4.482 / 5.858。无第二模型对比，理由不是许可证排除。详细数值分布见 `quantitative-stats.json`。

首轮真实看图出现 4 个指定回归失败（号码布近景、比赛跟拍备选被丢，水印与手指漏检），保存在 `first-pass-result-verification.json`、`first-pass-shots.json` 和原始回答目录，未覆盖。先写失败用例，再加入四角放大证据、身体主体和重复备选规则；逐张看完全部常规图与四角对照后，只复核 9 个受影响页，其余 9 页复用已检查的真实回答。开场钩子重新选。镜前早期两段理由借用了后面镜头的号码布，增加禁止跨镜头补物件的提示；“完整身体”也用原帧检查取景边界后再调模型纠正。缺陷布尔值以中文说明追加到理由，不修改原始回答。

最终：**精选 27、可用 71、不用 27、太短淘汰 3、unknown 0**。指定回归全部通过，42 个源文件的 SHA-256/大小/mtime 全部不变。共 33 次真实调用（18 页初审 + 初次钩子 1 + 局部复核 9 + 钩子重选 1 + 理由原帧复核 4），均为原 `codex_cli` / `gpt-5.6-terra` / medium，没有临时 Codex 包装器或替换模型。模型调用合计 1400.1 秒；恢复全量与复核累计程序计时 2906.4 秒。其中 32 次为有效结构回答，1 次把帧后缀当候选编号，被严格校验拒绝；原答与失败日志保留，重新请求时没有静默改号。逐次时间保留在 `call-timing-summary.json`、`final-model-calls.json`，失败初判仍可追溯。

## 看图复核与截图

常规拼图 18 张全部逐张查看；另逐页查看 18 张三帧四角对照（对应 54 张细节图），以及包含三个硬淘汰尾段的 audit-008/010/013，实际覆盖 128 条。没有把全部 16 张重复审计拼图都说成亲看。镜前/身体画面清楚，两条坏尾段没有稳定可辨主体；标题、水印与右上手指可见，最终状态符合要求。初判错误、逐页记录和模型复核均保留。

| 候选 | 最终状态 | 主体清晰度 | 软标记 / 视觉问题 |
|---|---|---:|---|
| S1d6f53e6f8-001 | 精选 | 483.17 | 无 |
| S3a7e697f5f-001 | 可用 | 413.58 | 无 |
| S3a7e697f5f-002 | 可用 | 238.10 | duplicate |
| S3a7e697f5f-003 | 精选 | 418.11 | shake |
| S4f8f2673dd-002 | 精选 | 1754.50 | shake |
| S4f8f2673dd-003 | 可用 | 1032.31 | shake, duplicate |
| S6e1e372b05-004 | 不用 | 641.30 | tracking_insufficient |
| S1c053bd1b6-002 | 不用 | 234.49 | tracking_insufficient |
| S5667c565f4 | 不用 | 2473.03 | has_title_or_sticker |
| Sd743287b07 | 可用 | 3856.50 | has_watermark |
| S4f8f2673dd-005 | 可用 | 3964.50 | duplicate, has_occlusion |

`S4f8f2673dd-002/-003` 抖动值分别为 0.011917、0.012262，只作软标记。镜前 003/004 的“完整身体/全身”及不确定衣物已通过原帧真实模型复核纠正；没有直接手改为预设理由。前两段不再借用后面可见的号码布。重复备选保留可用，但不进精选/钩子；相似扶梯/电脑画面跨哈希组的情况仍存在，不宣称完整语义去重。

最后一次理由变更后重新完整截图：实际桌面视口 1280×900，整页 1280×80703，101 张滚动帧、37 个连续部分；实际手机视口 390×844，整页 390×267728，360 帧、122 部分。逐一校验 459 处重叠像素零差异，均覆盖最后候选及底部 unknown 0。本人再看最终桌面 01/03/11/28/37、手机 01/09/33/93/122，核查首屏、最终理由、水印/手指及底部；未把抽看说成亲看所有部分。两种视口 374 张图完整，128 个来源链接均存在，无横向溢出；键盘跳转钩子有效。详情 `visual-verification.md`、`overview-qa.json`、`screenshots/seam-verification.json`。

最终绝对路径：

- 数据、常规/四角拼图、实际证据页：`media-root:projects/2026-lzu-revisit/2026-lzu-travel-and-sports/ai-analysis/shots/{shots.json,sheets/,overview.html}`。
- 便于打开的截图/拼图索引：[gallery.html](../../../evidence/2026-10-20/R208-A2/gallery.html)，主目录绝对路径 `evidence/2026-10-20/R208-A2/gallery.html`。
- 完整图：主目录 `evidence/2026-10-20/R208-A2/screenshots/overview-desktop-full.png`、`overview-phone-full.png`；连续部分见同目录 `overview-{desktop,phone}-part-*.png`。副本在原 worktree 同相对目录。
- `capture-manifest.json` 保存实际 file 路由、捕获时间、每帧坐标、各部分覆盖、尺寸、SHA-256；`artifact-hashes.json` 记录最终图/HTML 摘要。索引全部链接与哈希已经检查，交付副本再复核。

这是本地机器证据页，不是线上发布或 H-01 待设计的产品审阅页。原始 pytest 日志与许可证原文包含尾空格/末尾空行，完整 evidence 的 diff --check 会指出它们；未为消除警告改写原始证据。源码/任务文档检查通过。


## 依赖与许可证

只保留 LAION v1 B/32 评分头 + OpenAI CLIP B/32 骨干，由 OpenCLIP 实现；许可证不作排除条件，第二模型对比按 A2 取消。LAION 仓库、OpenAI CLIP 仓库与 OpenCLIP 的 MIT 原文和来源、SHA-256 已保存在 `.tools/models/licenses/` 和 `evidence/2026-10-20/R208-A2/licenses/`。评分头按仓库 MIT 分发，CLIP 仓库 MIT 原文不能冒充另行明确的骨干权重条款；保留这一区分但不阻止本次课程自用。骨干使用官方 URL 的 SHA-256 校验，不替换骨干。

## 提交与停止状态

交付状态：**实现与全量验证完成；推送被交付门禁阻塞，未推送。H-01 未递交人工验收，不能称 READY。**

1. 提交前 `git fetch origin` 成功，确认 `origin/main` 为 `6fe9533340fd1e8c2d2fc24b7939eba2cde950f0`。其祖先 R207 提交 `cd7a30eb35788e83ae5603720d5d3b3f24659d4a` 已将 `evidence/**` 明确登记为 `artifact: true`；本次同时合入 R207 后续安装与验收证据提交。前置证据 `precommit-r207.json`。
2. 本次实现/证据提交 `08cf232cf94af319d9764a82feb90350d20ca372`；合并提交 `aafbd2490c51886e648dc544c4f1444be632c8b8`，父提交分别为本次实现和上述 origin/main。两个提交均带指定 `Request` 与仅 H-01 的 `Verify` 尾行。没有 rebase、force 或更改他人历史。合并无冲突；十个源码/配置/测试文件哈希与已测版本完全一致，tracked 工作区与暂存区均无差异，见 `postmerge-source-identity.json`。全库与相关测试为合并前执行，没有把 R207 新增检查说成本轮全库已重跑。
3. 提交合并后 **仅运行一次** check-delivery：`--project-root /private/tmp/task-worktrees/photo-content-os-r208-a1 --range origin/main..HEAD --json --read-only`。退出码 **1**，检查 HEAD `aafbd2490c51886e648dc544c4f1444be632c8b8`、base `6fe9533340fd1e8c2d2fc24b7939eba2cde950f0`。G1：非豁免实现和合并提交均无验收卡覆盖。G12：本阶段只覆盖 H-01，H-02/H-03 没有本批 Verify，也无同编号验收卡的 `claims.request_changes` 解释。其余 G2–G11、G13–G16 为 pass；这些门禁 pass 不等于全库测试全绿或 H-01 人工通过。原文见 `check-delivery.json` 与命令/退出码 `check-delivery-command.json`。
4. 任务明确要求本轮不递交卡；H-01 产品审阅页还须 Claude 先设计。因此没有创建卡、伪造人工 PASS、改需求标准或再跑门禁。**没有执行 push，也没有运行要求已推送的 finish**。原 worktree 与两个本地提交保留；相对于本次 fetched origin/main，behind 0、ahead 2，尚未进入远端 main。无 PR 或远程功能分支操作。
5. 自己启动的全量体检、模型调用、截图和 QA 均已退出，截图浏览器在 finally 中关闭；未关闭其他会话的浏览器或进程。收工 `task_worktree.py check` 返回 1：本任务因按指定缺卡停止而保留未推送提交、报告与门禁证据；另列出既有 R207/R210 工作树问题，未操作它们。

Git 状态快照（`git-status-summary.json` 和三个 `*-status.txt`）：业务主目录 `c1b4db387e3c0c0aa6cabdb1af283a8e1d0f0594`，已有 60 个状态条目、16 个暂存路径；本任务没有触碰其 index、其他会话改动或主目录 HEAD，只回写本报告和自己的 A2 证据。任务 worktree 在上述合并提交，源码/暂存区干净；后生成的报告、门禁、状态与副本核验记录保留未提交，另有 `.venv` 测试软链接和需求锁文件，未暂存。Harness SSOT `581e43e5f4146a4e663b46c79bd259dbbe409160`，快照有 4993 个既有状态条目，暂存 0；**本任务未编辑 Harness SSOT**。共享目录其他会话仍在活动，数字为快照而非静止保证。

最终图索引已同步回主目录，只复制自己的 `evidence/2026-10-20/R208-A2/`；233 个索引链接、729 个图/HTML 哈希全部核验一致，见 `main-delivery-copy-verification.json`。A1/A2 实现和先前证据已进上述本地实现提交；报告、门禁与收尾证据产生于提交之后，不冒充提交内内容。本报告属于普通任务报告，不是 SSOT 开发包，无需另建 Obsidian 权威副本。

按本阶段指令在此停止。后续应先由 Claude 设计产品审阅页，再按当前需求卡完成验收递交和后续阶段；本轮不将推送或人工验收算作完成。

