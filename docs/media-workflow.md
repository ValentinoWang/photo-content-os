# 本地素材与剪映 HyperFrames 流转总纲

## 文档定位

**文档版本**：V4.5 Content OS v0.2 剪辑交接版  
**适用对象**：主剪辑师、外包团队、合作摄影师、运营人员  
**核心设备与工具**：MacBook、iCloud 云盘、iCloud 照片、Wink Mac 版、DJI Studio、DJI Reframe 插件、Insta360 Studio、剪映 Mac 版、HyperFrames、阿里云盘 Mac 客户端、移动硬盘

本文件是本地素材、剪映草稿、HyperFrames、iCloud、阿里云盘和移动硬盘流转的本地执行总纲。它放在 `docs/` 内，不再放在素材根目录；根目录只保留 `00_START_HERE_今天看这里.md` 作为日常入口。本文件只保留术语、总口径、素材高频决策表入口和子文档索引；详细 SOP 由同目录子文档承载。若子文档、子子文档、Obsidian 协议层或脚本说明发生冲突，以本文件和脚本契约检查为准。

Obsidian 协议文档仍在 `06_技术栈与自动化/`。本地 docs 只保存 Mac 执行规则，不复制 Obsidian 协议层全文。原始素材不进 Obsidian；Obsidian 只放项目包、路径、摘要、task 和 result。

## 术语解释

| 术语 | 定义 | 例子 |
| --- | --- | --- |
| L1 本地素材根 | 整套本地素材系统的根目录 | `/Users/vsiyo/Desktop/照片筛选` |
| L2 主题集合 | 一组相关项目的集合 | `projects/2026-lzu-revisit` |
| L3 项目根 | 单条内容或一个可独立归档项目的正式目录 | `2026-lzu-travel-and-sports` |
| L4 内容目录 | 项目内按叙事场景、素材功能或内容主题划分的目录 | `项目根/post-race-group` |
| L3 内容目录 / L3 根部 | 旧口语说法，指项目根下面的内容目录及其直接可见素材 | `post-race-group/红墙合影.jpg` |
| 项目 L3 源文件 | 位于项目内容目录里的事实原件或工作源 | `项目根/post-race-group/红墙团队领奖合影_G01_补充01_未修.jpg` |
| 80 精选副本 | 从项目 L3 源文件复制或导出的 iCloudReady 内容 | `icloud-selected/memorial/...` |
| raw-vault | 项目级技术源素材区，放原始全景、Log、Raw、Live Photo 半组、连拍原始组保留等 | `项目根/raw-vault/连拍原始组_保留/` |
| raw-pending | 场景级待处理区，放已归场景但需修复、转码、补齐或人工确认的素材 | `post-race-group/raw-pending/` |
| library | 跨项目复用索引和成品资产库，默认登记资产卡片，不复制项目源文件 | `library/Reusable_通用素材索引.md` |
| 归档索引卡 | 发布稳定后留在 Mac 上的轻量检索卡，记录旧项目的关键词、iCloud 相册、阿里云盘路径、移动硬盘路径和恢复方式 | `library/project-archive-index/20260514_项目名.archive.md` |
| iCloudReady | 已整理、已修复或确认无需修复、已去重、可长期回看、可导入 iCloud 照片 | `icloud-selected/project-selected/` |
| 标准剪辑交接包 | 当前默认剪辑交接方式；包含清单、字幕和交接说明，由人选择工具精剪 | `draft-project/edit-handoff/{project_revision}/` |
| 可编辑时间线 | 当前可选剪辑交接方式；生成并校验 OTIO/Kdenlive 时间线 | `draft-project/edit-handoff/{project_revision}/timeline.otio` |
| native import pack | 旧项目的历史人工二创辅助包；保留证据，不作为 v0.2 新任务的生产路线 | `draft-project/jianying/native-import-packs/` |
| HyperFrames 源工程 | AI 动态包装工程、prompt、组件配置和渲染记录，不是剪映草稿 | `draft-project/hyperframes/` |
| HyperFrames 导出素材 | 可进入剪映或发布候选的 MP4/PNG/透明叠加素材 | `output/hyperframes/` |

## 总口径

```text
Mac 本地素材根负责全量收口。
batch-notes.md 连接云端初稿和本地素材。
腾讯云负责先把想法变项目包，Mac 负责把项目包和真实素材合并成可剪方案。
本地路径不是云端立项的前置条件，只是 Mac task ready 的条件。
iCloud 云盘不承载全量素材库，只做文档同步、按需中转和归档副本。
iCloud 照片只接收 80 中的 iCloudReady 精选。
项目 L3 源文件承担事实原件或工作源职责。
剪映真实草稿留在本机活动区，只由人管理。
正式剪辑交接默认使用标准剪辑交接包；需要可编辑时间线时明确选择可编辑时间线。
一版项目只选择一种剪辑交接方式，失败时不自动换另一种。
HyperFrames 只生产 AI 动态包装素材。
AI 只做分析和校验，不做最终删除、发布和审美确认。
阿里云盘只做整理后项目的单向远程镜像。
移动硬盘只做冷归档。
发布稳定后，Mac 不长期保留全量源素材；Mac 保留归档索引卡、资产卡片、80 精选入口和必要 Final，源素材从阿里云盘镜像或移动硬盘冷归档恢复。
```

## 子文档索引

编号规则：`00` 是本地执行总纲；一级制度子文档使用 `01` 到 `06`；素材决策表目录使用 `decision-tables/`，目录内文档使用 `07.xx`；使用指南目录使用 `usage-guides/`，目录内文档使用 `08.xx`。其中 `08.xx` 是具体使用情形号，不是普通章节号。

| 子文档 | 责任 | 什么时候看 |
| --- | --- | --- |
| [terminology-and-layout.md](terminology-and-layout.md) | 完整术语、L1-L4、目录层级 | 看不懂 L3、Raw、80、资产库时 |
| [platform-and-cloud-boundaries.md](platform-and-cloud-boundaries.md) | Mac、iCloud、阿里云盘、移动硬盘边界 | 判断东西放电脑、云盘还是硬盘时 |
| [project-materials.md](project-materials.md) | 项目目录树、素材进入 Mac、Wink/DJI/Insta、L3、命名 | 整理项目素材和命名时 |
| [icloud-photos.md](icloud-photos.md) | 80 子目录、iCloud 照片、iPhone 同步、Live Photo | 想把内容同步到 iPhone 时 |
| [editing-and-hyperframes.md](editing-and-hyperframes.md) | 两种正式剪辑交接方式、真实剪映草稿边界、HyperFrames | 剪辑、包装、打包工程时 |
| [automation-checklist.md](automation-checklist.md) | 拍摄后流程、AI 分析、重复照片、复用纪念资产、检查清单 | 拍完后批量整理或复查时 |
| [decision-tables/](decision-tables/README.md) | 素材决策表索引；`07.xx` 素材高频情形决策表 | 需要按具体素材情形判断“放哪里、是否进手机、是否进资产库”时 |
| [usage-guides/](usage-guides/README.md) | 按具体情形写成的操作指南；`08.xx` 是情形号 | 手里有 tags、灵感、拍摄素材，不知道先落哪里、用哪个能力时 |
| [../templates/](../templates/README.md) | 可复制模板 | 新建事件批次、正式项目、资产卡片、交付包、归档包时 |

## 80 入库固定结构

`icloud-selected` 不能平铺，固定使用下一级目录：

```text
icloud-selected/
├── project-selected
├── cover-candidates
├── memorial
├── phone-reusable
├── live-photo-groups
├── final-output
└── pending-review
```

## 素材高频情形决策表

完整决策表放在子子文档：

[07.01_素材高频情形决策表](decision-tables/frequent-decisions.md)

执行总纲只保留最高频速查：

| 情形 | 处理 |
| --- | --- |
| 项目可用但不精选 | 留在项目 L3 内容目录 |
| 手机常看 / 常用 | 复制到 `icloud-selected` 对应子目录 |
| 未来可能复用 | 源文件留项目 L3，资产库只登记卡片 |
| 超脱项目的纪念素材 | 副本进 `80/memorial`，索引进 `library/memorial` |
| 大量近重复但想保存 | 进 `raw-vault/连拍原始组_保留/` |

## 剪辑交接、剪映与 HyperFrames 边界

```text
标准剪辑交接包（默认）
= manifest + clips.csv + captions.srt + 剪辑交接说明
= 人使用任意合适的剪辑软件精剪

可编辑时间线（可选）
= timeline.otio + timeline.kdenlive + 校验记录
= 只在明确选择后生成；不可用时阻塞，不换路线

剪映真实草稿
= 本机活动区或剪映官方本机目录
= 只由人建立和编辑；不放 iCloud / 移动硬盘上直接编辑

旧 native import pack
= 仅历史证据
= 不是 v0.2 正式剪辑路线

HyperFrames
= AI 动态包装素材生产器
= 源工程放 draft-project/HyperFrames
= 导出素材放 output/HyperFrames 或回填 L3
```

## 自动化入口

```bash
python3 scripts/ensure_project_structure.py "正式项目目录"
python3 scripts/link_batch_to_content_project.py "inbox/YYYYMMDD_事件名_待整理"
./scripts/run_analyze_project.sh "正式项目目录"
python3 scripts/check_outline_contract.py "/Users/vsiyo/Desktop/照片筛选"
```

## 最终执行口令

> Mac 本地素材根负责全量收口；iCloud 云盘不承载全量素材库，只做按需中转；iCloud 照片只接收 80 中的 iCloudReady 精选；项目 L3 源文件负责保存事实原件；默认交付标准剪辑交接包，需要时才明确选择可编辑时间线；剪映真实草稿留在本机活动区并由人管理；HyperFrames 只生产 AI 动态包装素材；AI 只做分析和校验不做最终删除；阿里云盘只做整理后项目的单向远程镜像；移动硬盘只做冷归档。
