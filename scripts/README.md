# AI 素材分析脚本

本目录是 `docs/media-workflow.md` 和本地 SOP 子文档的执行层。

```text
docs/media-workflow.md = 制度层总纲：定义术语、总口径、素材决策表和子文档索引
docs/01-06 = 制度层 SOP：承载素材进入、整理、精选、同步、归档等详细规则
docs/decision-tables/ = 制度层素材决策表：承载 07.xx 素材去向 / 入库 / 复用 / 归档高频情形
docs/usage-guides/ = 具体情形使用指南：承载 08.xx 情形号，例如 08.01 已有 tags / 灵感 / 拍摄素材时如何启动内容并落盘
scripts/ = 执行层：把规则变成可重复运行的扫描、抽帧、prompt、summary 流程
ai-analysis/ = 反馈层：把 AI 分析结果回填到筛选、命名、精选入库、Wink 修复和同步记录
```

文档层级固定为：`docs/media-workflow.md` 是本地执行总纲，`docs/01-06` 是本地执行 SOP，`docs/decision-tables/` 是素材决策表目录，`docs/usage-guides/` 是日常使用指南目录，`scripts/README.md` 只说明脚本如何执行这套规则；Obsidian 中的流转规范、状态机、剪映流水线和审核链路都是协议入口或局部子文档，不能覆盖本地执行总纲。

本地执行文档和 Obsidian 协议页之间由 `doc-sync-contract.json` 维护关键口径同步。修改本地执行总纲、剪辑/HyperFrames 子文档、脚本说明，或修改 Obsidian 的 `腾讯云OpenClaw与MAC_OpenClaw本地素材协同流转规范.md`、`剪辑交接与可编辑时间线.md` 时，必须运行：

```bash
python3 scripts/check_obsidian_doc_sync.py
python3 scripts/check_outline_contract.py .
```

如果检查失败，优先同步对应文档，不要删除 marker 或放宽契约。

## Content OS v0.2 剪辑交接

正式路线先由项目总览选择剪辑方式，再派发 Mac 任务。每个项目版本只选择一种剪辑交接方式，失败时不自动换另一种：

| 剪辑方式 | Runner 任务 | 版本目录 | 交给谁 |
| --- | --- | --- | --- |
| 标准剪辑交接（默认） | `generate_edit_handoff_pack` | `draft-project/edit-handoff/{project_revision}/` | 人使用合适的软件精剪 |
| 自动生成可编辑时间线（可选） | `generate_otio_kdenlive_timeline` | 同一版本目录 | 人在可编辑时间线中精剪 |

标准剪辑交接输出 manifest、片段表、字幕和说明。可编辑时间线输出 OTIO、Kdenlive
工程和校验记录，并且只由
`.venv/bin/python` 运行；缺少该环境、Kdenlive 或媒体
重连证据时，Runner 写 blocked 结果，不调用其他解释器、编辑器或交接方式。

旧 native import pack、旧 `06b`/`06d` 文件和真实剪映草稿只保留为历史证据。新任务不
生成或修改生产用剪映草稿；人仍可在本机使用剪映完成精剪，但真实草稿不在同步范围。

需要剪到一半修改时，协作者只能从 Media Bot 对话提交。Bot 先记录并复述，再让人选
“先记下”“只改一小处”或“现在修改”；后两者只有在人确认影响后才创建新版本工作。

项目素材库以最大信息保留为主，不由 AI 做高光筛选或删除候选；iCloud 照片才是高度精选的长期回看库。

`98_Agent任务队列` 和 `openclaw-queue` 是上下两层，不互相替代：

```text
98_Agent任务队列 = 任务层 / 协议层 / 文档层
openclaw-queue = 执行层 / 素材层 / 控制层
```

腾讯云 OpenClaw 需要给 Mac 派发任务说明、brief、执行要求或结果沉淀时，走 Obsidian vault 里的 `98_Agent任务队列`。当任务进入真实素材批次处理时，Mac Agent 再把任务层信息桥接成本机 `openclaw-queue` 的 JSON 控制文件；云端不直接写 Mac 本地 `openclaw-queue`，也不同步整个 `inbox`。

Mac 本机的轻量执行队列结构固定为：

```text
openclaw-queue/
├── cloud_to_mac/
│   └── run_YYYYMMDD_HHMMSS_xxxx.json
├── mac_to_cloud/
│   └── run_YYYYMMDD_HHMMSS_xxxx.result.json
├── processed/
└── failed/
```

Syncthing 正式常驻同步的是 Obsidian vault 中的 `98_Agent任务队列`，不是 `openclaw-queue`。原始照片、视频、Live Photo 组、DJI/Insta 原始文件仍然留在 Mac 本地；Mac OpenClaw 读取本地批次后，只回写 `link.json`、`status.json` 和轻量 result 摘要到任务层。

作品审核能力统一由 GitHub 管理，机器可读单一事实源是 `review-capabilities.registry.json`。这一版优先收敛的是视频评分、判断和版本排序算法本身：技术门禁、策略评分、VLM 语义融合、节奏同步评分、推荐值和人工判断边界。本机 Mac 和远端服务器新增或修改成片质检、VLM 复核、节奏同步、版本排序、远端任务编排时，必须先更新 registry 的 `algorithm_contract`，再改脚本、Runner、文档和测试，并运行：

```bash
python3 scripts/validate_review_capability_registry.py
```

原则固定为：Mac 侧 `review_output_video.py` 承担视频探测、抽帧、音画同步、策略评分和 VLM 语义复核；远端服务器这一版只派发任务、推进状态、消费 Mac 回写结果，不另造第二套评分/判断算法。

这些脚本不替代 `docs/media-workflow.md` 和本地 SOP 子文档，只服务这套规则。如果执行总纲或子文档修改了目录、命名、Live Photo、iCloud 照片或阿里云盘规则，脚本说明和契约检查也必须同步更新。

## 归档候选清单

`archive_project.py` 是本地、无破坏性的归档准入和清单生成工具。它检查 Final、同步清单和 `additions/`，并在显式 `--write` 时生成带 SHA-256 的 `archive_manifest.json` 与归档索引卡；不会上传、删除或修改真实剪映草稿。外部镜像回读、恢复演练和 Mac 瘦身仍需独立证据。

## 目录唯一事实来源

正式项目目录必须位于：

```text
本地素材根/projects/主题集合/YYYYMM_主题_叙事关键词
```

示例：

```text
/Users/vsiyo/Desktop/照片筛选/projects/2026-lzu-revisit/2026-lzu-travel-and-sports
```

`/Users/vsiyo/Desktop/照片筛选` 是当前本地素材根；`docs/`、`scripts/`、`projects`、`library` 共同构成唯一事实来源。根目录只保留 `00_START_HERE_今天看这里.md` 作为日常入口，不再放制度文件。主题集合统一放进 `projects`，不要裸放在本地素材根顶层；临时加工缓存放在具体项目根的 `work-cache` 下。iCloud 云盘不承载全量素材库，只做按需中转；项目源文件仍留在项目 L3 目录，不搬进资产库。

剪映真实草稿和项目工程记录分开：活动草稿优先留在 `/Users/vsiyo/Desktop/照片筛选/jianying-drafts` 或剪映官方本机目录；当前版本交接物放 `draft-project/edit-handoff/{project_revision}`，官方备份包可留在 `draft-project/jianying/official-backups`。旧 native import pack 仅作历史证据。HyperFrames 只作为 AI 动态包装素材生产器，源工程放 `draft-project/HyperFrames`，导出素材放 `output/HyperFrames` 或回填 L3。

## 闭环流程

```text
docs/00 总纲和 SOP 子文档定义项目结构和筛选标准
↓
scripts/ 扫描项目并生成 AI 分析材料
↓
ai-analysis/ 输出 manifest、keyframes、prompts、summaries
↓
AI 提供分析、归类、命名、Raw 判别和 Wink / 80 建议；人工决定发布、删除和最终精选
↓
回填 readme.md、aliyun-sync-manifest.md、icloud-selected、draft-project/project-notes.md
↓
每日检查清单和阿里云盘同步记录再次验证项目是否符合大纲
```

## 执行流程

脚本会把项目素材变成 AI 更容易分析的结构化材料：

```text
项目文件夹
↓
扫描素材清单
↓
校验 Raw / 低清 / 低质等命名判断
↓
均匀抽取关键帧
↓
可选提取音频
↓
生成 AI 分析 prompt
↓
通过本机 Codex CLI/OAuth 调用 gpt-5.5 / xhigh 生成 summary 和项目总览
```

二次筛选后如果还有增量素材进入 `additions`，不要手工直接并入正式项目，先生成合并计划：

```text
additions
↓
run_additions_merge.sh 调用 08 生成分类、命名和目标目录建议
↓
run_additions_merge.sh 调用 09 执行已确认计划
↓
正式项目重新跑 run_analyze_project.sh
```

## 快速运行

```bash
chmod +x scripts/*.sh
./scripts/run_analyze_project.sh "/Users/vsiyo/Desktop/照片筛选/projects/2026-lzu-revisit/2026-lzu-travel-and-sports"
```

如果需要同时提取音频：

```bash
./scripts/run_analyze_project.sh "/Users/vsiyo/Desktop/照片筛选/projects/2026-lzu-revisit/2026-lzu-travel-and-sports" --audio
```

## 输出结构

```text
ai-analysis/
├── media-manifest.json
├── media-decision-warnings.md
├── keyframes/
├── audio/
├── prompts/
├── summaries/
├── additions-merge-plan.md
├── additions-merge-plan.json
└── project-overview.md
```

这些输出是项目内部分析资产，不是剪辑工程文件，也不是 iCloud 照片精选库本身。默认同步清单、summary、plan、project_overview；keyframes 和 audio 是可重建分析缓存，可按空间情况排除。最终是否进入 `icloud-selected`，仍以 `docs/media-workflow.md` 的 iCloudReady 规则为准。

`icloud-selected` 不是平铺目录，主流程会补齐：

```text
project-selected/
cover-candidates/
memorial/
phone-reusable/
live-photo-groups/
final-output/
pending-review/
```

连拍、重复照片和细微动作差异素材按执行总纲处理：出彩代表进 80 对应子目录，动作略有区别的补充素材留项目 L3，近重复但想保存的原始组进入 `raw-vault/连拍原始组_保留/`。

## 脚本说明

- `scan_media_manifest.py`：扫描视频、图片、XMP，检测 Live Photo 同名组，提取 QuickTime GPS，标记 80 精选副本等派生目录。
- `extract_keyframes.py`：按时长均匀抽帧，比赛/校运会素材默认更密。
- `extract_audio.sh`：从有音频的视频提取 16kHz 单声道 WAV。
- `generate_ai_prompt.py`：为每个素材生成标准 AI 分析 prompt，并生成项目级 L3 内容结构判读 prompt 和命名 workflow prompts。
- `write_content_summary.py`：默认通过本机已登录的 Codex CLI/OAuth 调用 gpt-5.5 / xhigh 生成素材 summary 和项目总览；也可显式设置 `OPENCLAW_CREATIVE_PROVIDER=openai_api` 改走 OpenAI API key。无可用 LLM provider 时失败，不生成规则模板。
- `check_outline_contract.py`：检查 `docs/media-workflow.md`、本地 SOP 子文档、`scripts/README.md` 与 Obsidian 协议页是否仍然描述同一套闭环契约。
- `validate_media_decisions.py`：校验 `raw-pending`、`低清`、`低质` 等命名判断是否有可复核依据，并输出 `media-decision-warnings.md`。
- `plan_additions_merge.py`：扫描二筛 `additions` 大杂烩目录，生成合并到正式项目的证据包和机械计划；文件名缺少线索的视频会先抽关键帧，图片会生成预览图，同时输出 LLM 判读 prompt，不用视觉启发式硬判语义，也不自动创建固定内容目录。
- `apply_additions_merge.py`：读取已确认的合并计划，移动/改名素材，追加素材整理记录，并可自动重跑正式项目分析。
- `run_additions_merge.sh`：日常一键入口；默认直接执行合并、重跑分析并清空 `additions`，加 `--plan` 时只生成计划。
- `rename_media_file.py`：项目内单独重命名执行入口；先抽帧/生成图片预览并写入重命名计划，语义基名由 LLM/人工通过 `--override-stem` 给出，脚本负责 Live Photo / 原始关联组整组改名、同名冲突避让、整理记录和重跑分析。
- `select_repeat_photo_groups.py`：重复照片/合照补充包专用入口；先生成联系表和合并计划，按计划把照片并入 L3 主题目录，待确认或待修复的照片放 Raw。
- `ensure_project_structure.py`：补齐正式项目标准工作流目录，并按项目名创建项目级 WorkCache；只允许作用于 `projects` 下的正式项目，直接指向 `inbox` 会拒绝并提示先运行 `ensure_project_from_inbox_batch.py`。项目根内只创建 80、90、91、92、additions等常驻目录和基础记录文件。内容 L3 目录只能来自 LLM/人工确认的结构计划，可用 `--apply-l3-plan` 执行。
- `distribute_group_photos_by_name.py`：按需创建合照发放区，读取合照发放 CSV，把同一张合照复制到多个人的姓名目录，生成可交付的按人发放副本。
- `register_reusable_asset.py`：把具有多重价值的项目素材登记到 `library` 通用资产索引；只写索引和资产卡片，不复制源文件。
- `match_materials_to_brief.py`：默认通过本机 Codex CLI/OAuth 调用 gpt-5.5 / xhigh，基于 brief、04_script、manifest 和 summary 做宏观素材适配判断；脚本不做关键词匹配、不做规则分组，只负责打包输入、调用 LLM、校验 frontmatter 和落盘。
- `generate_storyboard_edl.py`：默认通过本机 Codex CLI/OAuth 调用 gpt-5.5 / xhigh，基于 brief、04_script、素材匹配报告和 manifest 生成 storyboard / EDL；脚本只校验 JSON 合同和写文件。
- `review_output_video.py`：本地成片验收入口；用 ffprobe/ffmpeg/Pillow 生成 metrics、抽帧总览、场景变化图和 `_output_review.md`。可通过 `--bgm-review-dir` 接入外部 BGM/步点/切点审阅 JSON，通过 `--project-root` 读取项目平台目标，并生成作品策略审阅表，覆盖节奏、平台画幅、开头钩子、构图技术和选题命名。也可用 `--rhythm-sync --profile <profile>` 启用内建节奏同步评估，输出 `ai-analysis/output-review/rhythm_sync/rhythm_sync_metrics.json`、`rhythm_sync_result.yaml`、`rhythm_sync_report.md`，并为每个版本生成 `audio_events.json`、`visual_events.json`、`matches.json` 和审看帧。内建 V1 使用 RMS/onset/beat-grid 音频事件、ffmpeg scene select、帧差运动峰、顶部/底部字幕变化代理、下中部 ROI 步点代理和强运动 `pose_keyframe` 代理，按 `general_bgm_edit`、`single_person_stage_walk`、`split_screen_comparison` 等 profile 加权排序，并输出 `edit_suggestions` 与动态路径候选，供剪映人工微调切点、整体偏移、裁黑场或局部变速参考。加 `--run-vlm-review` 时会把各版本 contact sheet 作为图片交给 Codex VLM，补充人物状态、真实构图美感、开头钩子、选题表达和平台观感语义分，并与规则分合并；脚本仍只能给版本倾向和人工审看点，最终发布由人确认。
- `check_obsidian_doc_sync.py`：读取 `doc-sync-contract.json`，检查本地执行文档和 Obsidian 协议页的关键口径、目标 marker 和修改时间，防止一边改了另一边没同步。
- `link_batch_to_content_project.py`：无云端 task 时的本地桥接入口；读取 `inbox/事件批次/batch-notes.md` 的 Obsidian 项目ID，校验 `08_内容项目/{project_id}/01_idea_card.md`、`02_project_brief.md`、`04_script.md` 和可选 task，生成 `事件批次/ai-analysis/content_os_link.yaml`。状态只允许 `pending_cloud_brief` 或 `brief_ready`。
- `process_openclaw_queue.py`：Mac 本机轻量 JSON 执行队列入口；读取 `openclaw-queue/cloud_to_mac/*.json`，把 `creation_run_id` / 飞书文档 / 本地 Inbox 批次绑定到 `事件批次/openclaw/link.json` 和 `status.json`，再回写 `openclaw-queue/mac_to_cloud/*.result.json`。如果任务指向的 Inbox 批次目录或 `batch-notes.md` 不存在，会在 `inbox` 内自动创建，并在批次说明里预填云端自动填充区；如果说明文件已存在，只插入缺失的云端区块，不覆盖人工内容。批次目录支持人工改名，只要保留 `openclaw/link.json`，后续任务会按 `creation_run_id` 或 `batch_id` 找回改名后的目录。默认 `--once` 跑一次，也可 `--watch` 常驻监听；不复制、不同步、不列出原素材文件名。
- `enqueue_openclaw_queue_job.py`：任务层到执行层的桥接入口；读取 `98_Agent任务队列/01_cloud_to_mac_ready/task_*.yaml` 或其 `content_os_link_path`，生成 `openclaw-queue/cloud_to_mac/*.json`。它只写本机 JSON 控制任务，不复制素材；可加 `--process` 立刻调用 `process_openclaw_queue.py --once`，也可用 `--all-ready --process` 扫描所有云端 ready 任务，或用 `--watch --process` 常驻监听云端任务层。
- `ensure_project_from_inbox_batch.py`：手动把 `inbox/事件批次` 升级为正式项目壳；如果批次说明已有有效 `目标项目` 就复用，否则按时间、batch_id、事件/topic 在 `projects/主题集合/项目名` 下创建正式目录、补齐 80/90/91/92/additions 和项目级 WorkCache，并回写 `batch-notes.md` 与 `openclaw/project.json`。`process_openclaw_queue.py` 也会自动调用同一套能力。
- `promote_inbox_batch_to_project.py`：把已经有正式项目壳的 Inbox 批次真正迁入 `projects`。真实素材移动到项目 `unclassified/`，批次说明一起移动，旧 `ai-analysis` 和 `openclaw` 作为迁移证据移到项目内，随后删除/清空原 `inbox/事件批次`；这是移动，不是复制。误在 Inbox 里生成的 80/90/91/92/additions 脚手架会移到项目 `ai-analysis/promoted-inbox-batches/批次名/generated-scaffold-from-inbox/` 作为证据，不进入长期项目结构。
- `validate_review_capability_registry.py`：校验 `review-capabilities.registry.json`，保证每个作品审核能力只有一个 canonical owner、一个可追溯实现入口和明确 GitHub 变更门禁；防止本机与远端各写一套成片质检、节奏同步或 VLM 复核。
- `run_analyze_project.sh`：一键跑完整准备流程。

`local_material_match` task 可以带：

```yaml
inputs:
  content_os_link_path: /Users/vsiyo/Desktop/照片筛选/inbox/事件批次/ai-analysis/content_os_link.yaml
```

Runner 会校验该 link 为 `brief_ready`、`project_id` 一致、没有缺失项目包文件，并在 result YAML 的 `local_outputs.content_os_link` 中回写。Mac 回写才是腾讯云可继续使用的“本地事实”；腾讯云后续只能基于 Mac 回写的 `03_material_match_report.md`、`05_storyboard.md`、`06_edit_decision_list.json`、`08_local_assets.md` 和 `result_*.yaml` 继续修订脚本或发布包，不能直接推断 Mac 目录。

新的 Syncthing 队列只处理“云端创作运行绑定到本地 Inbox 批次”这一类轻量任务：

```json
{
  "task_type": "bind_creation_run_to_local_batch",
  "creation_run_id": "run_20260627_115051_382a",
  "feishu_doc_link": "https://tcnwueberajc.feishu.cn/wiki/...",
  "batch_id": "2026-tsinghua-graduation",
  "topic": "第一视角体验清华毕业典礼",
  "platform": "抖音",
  "content_type": "视频",
  "requested_outputs": ["剪辑说明", "素材匹配", "Storyboard", "EDL"]
}
```

正式 JSON contract 优先使用顶层 `batch_id`。云端默认不需要知道完整 Mac 路径；Mac 会把 `batch_id` 解析为 `inbox/{batch_id}`。`local_batch_path` 只作为人明确提供完整 Mac 路径时的可选 hint；`process_openclaw_queue.py` 仍兼容旧的 `local_batch.path` 嵌套写法。

处理本机 `openclaw-queue` 手动跑一次：

```bash
python3 scripts/process_openclaw_queue.py --once
```

Mac OpenClaw 常驻监听：

```bash
python3 scripts/process_openclaw_queue.py --watch --interval 10
```

云端 ready 队列自动开工：从云端任务层扫描所有 ready 任务并立即处理：

```bash
python3 scripts/enqueue_openclaw_queue_job.py --all-ready --process
```

让 Mac OpenClaw 常驻等待云端任务单：

```bash
python3 scripts/enqueue_openclaw_queue_job.py --watch --process --interval 10
```

成功后，本地批次会得到：

```text
inbox/事件批次/
├── batch-notes.md
├── 原始素材...
└── openclaw/
    ├── link.json
    └── status.json
```

`openclaw-queue/mac_to_cloud/*.result.json` 只写 `creation_run_id`、飞书链接、本地批次路径、批次说明路径、媒体数量和下一步动作，不写原素材文件名清单。

如果任务先进入旧链路：

```bash
python3 scripts/enqueue_openclaw_queue_job.py task_YYYYMMDD_NNN
```

或者生成后立即处理：

```bash
python3 scripts/enqueue_openclaw_queue_job.py task_YYYYMMDD_NNN --process
```

如果该 task 只提供 `batch_id`，Mac OpenClaw 会自动映射到 `inbox/{batch_id}`。如果批次目录或 `batch-notes.md` 不存在，会自动创建事件批次目录和说明文件。自动创建只允许发生在 `inbox` 内；路径越界、字段缺失或文件占用批次目录仍然会 blocked。

`batch-notes.md` 的云端信息采用“预填但可编辑”原则：脚本会写入 `creation_run_id`、`batch_id`、topic、平台、飞书链接、来源 task 和 requested_outputs；人可以继续修改这份 Markdown。脚本不会覆盖已有的人工字段，目录被你改名后也会通过 `openclaw/link.json` 继续追踪。

这条链路固定为：

```text
98_Agent任务队列/task_*.yaml
↓
enqueue_openclaw_queue_job.py
↓
openclaw-queue/cloud_to_mac/*.json
↓
process_openclaw_queue.py
↓
openclaw-queue/mac_to_cloud/*.result.json
↓
必要时摘要回写 98_Agent任务队列/02_mac_to_cloud_results
```

## 与大纲的职责对应

| 总纲规则 | 脚本执行 | 回填位置 |
| --- | --- | --- |
| L3 根部是项目可用素材区，raw-pending只放原因明确的场景级待处理素材 | `scan_media_manifest.py` 标记 `primary` / `raw_or_pending`，`validate_media_decisions.py` 校验原因 | `readme.md`、`material-organization.md` |
| iCloud 照片只收 iCloudReady 精选 | manifest 标记 `selected_copy`，默认不重复分析 80 副本 | `icloud-selected` |
| 80 精选必须有下一级归类 | `ensure_project_structure.py` 自动创建 01-06 和 99 复核目录 | `icloud-selected/project-selected` 等 |
| Live Photo 必须 HEIC/MOV/XMP 同名组 | 扫描时检测 `live_photo_status`，additions合并时按组继承分类并保持同名不同后缀 | Live Photo 整理记录 |
| 文件命名尽量说清画面内容 | manifest/prompt 提供 GPS、关键帧、地点提取要求和命名判别结果 | L3 文件名、`material-organization.md` |
| 素材价值不只看画面类别 | prompt 强制拆分画面事实、隐含叙事意图、可表达观点；设备/幕后/不便捷性不能被泛化为普通候场 | `ai-analysis/summaries`、`project-overview.md`、资产卡片 |
| 视觉相似素材先成组复核 | `generate_ai_prompt.py` 基于关键帧生成视觉相似候选组，并写入 L3 结构 prompt | `ai-analysis/visual-similarity-groups.md`、`ai-analysis/prompts/project-l3-structure-prompt.md` |
| 重复合照先成组再归类 | `select_repeat_photo_groups.py` 生成合并计划并执行，不做高光筛选，不生成删除候选 | L3 根部、Raw、整理记录 |
| 合照by-name发放 | `distribute_group_photos_by_name.py` 读取 `合照发放清单.csv` 并by-name复制副本 | `group-photo-distribution` |
| 多重价值素材复用 | `register_reusable_asset.py` 写入通用素材索引和资产卡片 | `library/Reusable_通用素材索引.md` |
| 超脱项目的纪念素材 | 源文件留项目 L3，精选副本进 80 纪念目录，长期索引进纪念资产库 | `icloud-selected/memorial`、`library/memorial` |
| Wink 修复只处理副本 | prompt 要求判断是否需要 Wink | `项目根/work-cache/wink-exports`、L3 根部 |
| 拼图只处理副本 | 从 L3 复制选中图片到项目级collage-assets，拼图成品先进输出暂存 | `项目根/work-cache/collage-assets`、`项目根/work-cache/collage-exports` |
| 阿里云盘只做单向远程镜像 | summary 和 manifest 支持同步前检查 | `aliyun-sync-manifest.md`、`sync-ready` |
| 人工精剪读取当前版本交接物、L3 素材和导出包装素材 | prompt 判断素材用途和剪辑价值 | `draft-project/edit-handoff/{project_revision}`、`draft-project/project-notes.md` |
| 真实剪映草稿留在本机活动区 | 脚本只创建记录目录，不移动真实草稿 | `jianying-drafts`、`draft-project/jianying/official-backups` |
| 批次说明连接云端初稿和本地素材 | `link_batch_to_content_project.py` 读取 `batch-notes.md`，反查 Obsidian 项目包 | `inbox/事件批次/ai-analysis/content_os_link.yaml` |
| HyperFrames 只生产包装素材 | 脚本创建源工程和导出位置，不把它当剪映草稿 | `draft-project/HyperFrames`、`output/HyperFrames`、`library/hyperframes-components` |
| additions是二筛增量入口，不是正式目录 | `run_additions_merge.sh` 默认一键执行，底层调用 `08` / `09` | 正式项目 L3、`material-organization.md`、`ai-analysis` |
| 单独改名不改变素材分类 | `rename_media_file.py` 拆解内容后原地自动重命名，Live Photo 默认整组改名 | L3 文件名、`material-organization.md`、`ai-analysis` |
| 主工作流自动补齐空目录 | `run_analyze_project.sh` 先调用 `ensure_project_structure.py` | 项目根内 `work-cache`、`80`、`90`、`91`、`92`、`additions` |

## L3 内容结构

项目的 L3 内容目录不使用固定模板。任何内容目录名都只能作为某个项目经全局分析后确认的结果，不能作为脚本默认结构。

一键分析会生成：

```text
ai-analysis/prompts/project-l3-structure-prompt.md
```

LLM/人工根据该 prompt 输出结构计划后，再执行：

```bash
python3 scripts/ensure_project_structure.py "正式项目目录" \
  --apply-l3-plan "ai-analysis/l3-structure-plan.json"
```

结构计划负责创建内容目录和移动现有素材；脚本只做路径校验、同名保护、移动执行和整理记录，不替用户决定叙事结构。

## 命名 Prompt

命名规则以 `docs/media-workflow.md` 和 `scripts/prompt-templates/` 为唯一事实来源。运行 `generate_ai_prompt.py` 后，每个项目都会得到：

```text
ai-analysis/prompts/workflows/
├── l3-structure-prompt.md
├── file-rename-prompt.md
├── clip-content-prompts.md
├── batch-rename-plan-prompt.md
└── icloud-asset-delivery-prompt.md
```

这些 prompt 分别处理：L3 结构、单文件重命名、剪辑内容类型判读、批量重命名计划、80/资产库/交付命名。脚本不把“比赛、自拍、成绩表”等词硬编码成目录或文件名。

命名时区分素材层和作品层：L3 原素材文件名只写画面事实和素材特质，不被 `第一视角全景跑400米`、`400米比赛记录`、`全景相机幕后感` 等单一作品风格锁死；作品风格写进 summary、资产卡片、`draft-project` 剪辑方案和 `output` 成片名。只有风格化衍生物、发布成片、封面候选或交付副本，才在文件名里写作品风格。

## 注意

默认只分析 L3 根部的主素材；`icloud-selected`、`output` 等目录会进入清单，但不会重复生成 prompt，避免精选副本重复计数。

主流程会先自动补齐标准空目录：

```bash
python3 scripts/ensure_project_structure.py "正式项目目录"
```

它只创建项目正式目录、项目级 WorkCache 和基础记录文件，不移动、不复制、不改名素材。

补齐内容包括：

```text
draft-project/edit-handoff/{project_revision}/
draft-project/jianying/official-backups/
draft-project/jianying/历史 native-import-packs（仅旧项目证据）/
draft-project/hyperframes/src/
draft-project/hyperframes/render-logs/
output/hyperframes/
项目根/work-cache/hyperframes-render-cache/
```

`低清` 只能在脚本读到短边低于 720p 时使用。短边达到 720p 或以上的素材不能因为画面有抖动、开头拍到地面、结尾不可用而命名为低清；这类素材应改成 `_待截取`、`_待防抖`、`_模糊待选` 等可复核状态。普通照片 / 普通视频进入 `raw-pending` 时，文件名必须写明不可直用原因；DJI / Insta360 / Live Photo 原始关联组可保持原名，原因写入文件夹名或 readme。

## additions合并

日常直接合并：

```bash
./scripts/run_additions_merge.sh "目标正式项目目录"
```

只想先看计划时才加 `--plan`：

```bash
./scripts/run_additions_merge.sh "目标正式项目目录" --plan
```

`additions` 固定放在正式项目内，也就是 `目标正式项目目录/additions`。默认模式会按当前计划执行全部 pending 条目，允许 needs_review 条目，合并后自动重跑正式项目分析，并清空 `additions`。

`additions` 是增量入口，不参与剪辑、不进入 iCloud 照片、不进入阿里云盘镜像；合并后才进入正式项目素材判断。

文件名和元数据不够判断时，视频会自动抽帧、图片会生成预览图，结果保存到 `additions/ai-analysis/addition-keyframes/`，并额外生成 `additions/ai-analysis/additions-llm-review-prompt.md`。脚本不再根据颜色、画面比例或少量关键词直接判断“跑道/成绩表/自拍”等宏观语义；泛名素材保持 `blocked`，等 LLM/人工确认目录、命名和 `status=approved` 后再执行合并，避免把可用素材误丢进 `raw-pending`。

需要更细控制时，也可以直接使用底层脚本：

```bash
python3 scripts/plan_additions_merge.py "additions目录" "目标正式项目目录"
python3 scripts/apply_additions_merge.py "additions目录" "目标正式项目目录"
```

底层脚本也会校验：`additions目录` 必须等于 `目标正式项目目录/additions`，避免误把上一级 `兰州大学/additions` 之类的临时目录当成项目入口。

底层 `apply_additions_merge.py` 单独运行时，含 `needs_review=true` 的条目默认不会被执行。日常入口 `run_additions_merge.sh` 默认按整批additions素材执行，会自动加上 `--allow-review-items`。

Live Photo 增量组会被识别为 HEIC/MOV/XMP 同名组；计划脚本会使用同一个 `LIVE` 基名生成建议，避免把静态图和动态视频拆成两个不同名字。

## 重复照片additions

当 `additions` 里是一批合照、领奖照、人像连拍或 JPG 照片补充包时，不使用 `run_additions_merge.sh`，改用重复照片角色筛选脚本：

```bash
python3 scripts/select_repeat_photo_groups.py "正式项目目录" --plan
```

脚本会生成：

```text
ai-analysis/repeat_photo_additions/current/contact-sheets/
ai-analysis/repeat_photo_additions/current/repeat_photo_selection_plan.json
```

看联系表后，在 JSON 里把每张照片分配为：

```text
merge            合并到 L3 主题目录
raw              待修 / 待确认，进入 raw-pending
```

原则：不再设置备用目录，也不建立 `99_To_Delete_7days`。AI 不负责高光筛选；可归类照片全部并入对应 L3 主题目录，无法确认人物、需要修复或暂不可直用的照片进入 Raw。

L3 项目归档层使用 `补充01`、`补充02` 和 `_未修` / `_待修复` 等状态；`代表`、`情绪`、`封面候选` 只用于 80 或发布层。普通 JPG 合照不要用 `_原片` 后缀，避免和 Live Photo 原始组或相机 Raw 混淆。

计划填好后执行：

```bash
python3 scripts/select_repeat_photo_groups.py "正式项目目录" --apply
```

执行后会追加 `重复组合照筛选记录.md`、清空 `additions`，并默认重跑项目分析。

## 合照by-name发放

需要按人发合照时再运行本脚本；它会按需创建：

```text
group-photo-distribution/合照发放清单.csv
```

主分析流程不会自动创建 93。它不是素材分流目录，只是交付发放副本区。

CSV 字段：

```text
photo_path,names,note
LLM确认的合照目录/红墙团队领奖合影_G01_代表01_Wink已修.JPG,张三、李四,领奖合照
```

执行：

```bash
python3 scripts/distribute_group_photos_by_name.py "正式项目目录"
```

脚本会复制副本到 `group-photo-distribution/by-name/姓名/`；一张合照写多个姓名时，每个人目录都会获得一份。姓名为空或写“待确认”的条目进入 `pending-names/`。

## 多重价值素材登记

当一个素材既属于某个项目，又有长期通用价值时，源文件仍留在项目 L3 目录，只在资产库登记索引：

```bash
python3 scripts/register_reusable_asset.py \
  "正式项目目录" \
  "LLM确认的人物状态目录/兰州大学榆中校区宿舍镜前自拍视频.mp4" \
  --category "reusable-portraits" \
  --title "兰州大学榆中宿舍镜前自拍_颜值类通用素材" \
  --tags "颜值类、镜前自拍、宿舍、校园、人设、自拍视频" \
  --uses "小红书封面、短视频开头、人物状态转场、校园人设素材" \
  --cuts "00:00-00:05 全段可用" \
  --public-status "待确认"
```

脚本会更新：

```text
library/Reusable_通用素材索引.md
library/reusable-portraits/*.asset.md
```

资产库默认不复制源文件。若以后做了调色、裁切、Wink 修复后的通用成品，再把成品副本作为新的资产卡片登记。

## 单独重命名

只需要在项目内原地改一个文件名时，用 `rename_media_file.py`。它不做分类移动，也不在脚本里硬编码“看起来像跑道/成绩表/自拍”这类宏观判断；它先拆解当前素材内容，生成关键帧、联系表和 rename plan：

```bash
python3 scripts/rename_media_file.py "正式项目目录" "项目内相对路径或绝对路径"
```

只想先看自动命名计划时：

```bash
python3 scripts/rename_media_file.py "正式项目目录" "项目内相对路径或绝对路径" --plan
```

LLM/人工看完关键帧和项目 prompt 后，用明确基名执行改名：

```bash
python3 scripts/rename_media_file.py "正式项目目录" "项目内相对路径或绝对路径" \
  --override-stem "兰州大学校运会400米比赛全程_看台视角"
```

Live Photo 默认整组同名改：

```bash
python3 scripts/rename_media_file.py "正式项目目录" "LLM确认的人物状态目录/IMG_6278.MOV"
```

这会先抽取 MOV 关键帧或 HEIC 预览图，生成 `ai-analysis/rename-keyframes/` 和 `ai-analysis/rename-plans/`，再把同名 `.HEIC` / `.MOV` / `.XMP` 改成同一个内容化基名。`.OSV` / `.LRF` / `.INSV` 原始关联组同理按同 stem 整组改名，不单独拆开。只想改当前文件时才加 `--single`；没有 `--override-stem` 且文件名仍是相机泛名时会停止，不想重跑分析时加 `--skip-analysis`。

## 契约检查

```bash
python3 scripts/check_outline_contract.py "/Users/vsiyo/Desktop/照片筛选"
```

一键脚本会在检测到 `docs/media-workflow.md` 时自动执行这个检查。检查失败代表脚本说明、执行总纲或本地 SOP 子文档规则已经脱节，需要先修文档或脚本再继续跑项目分析。
