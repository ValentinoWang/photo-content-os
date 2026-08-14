# 剪映与 HyperFrames

> 子文档定位：本文件承载执行细则；执行总纲只保留术语、总口径、决策表和索引。若与执行总纲冲突，以执行总纲和脚本契约检查为准。

## 十五、剪辑交接与剪映工程规则

Content OS v0.2 先交付可核验的剪辑交接物，再由人开始精剪。真实剪映草稿和项目工程记录必须分开；系统不再为新项目生成或修改剪映草稿。

每个项目版本只允许明确选择一种正式剪辑交接方式：

| 方式 | 用途 | 交接物 |
| --- | --- | --- |
| 标准剪辑交接（默认） | 人使用自己选择的剪辑软件开始精剪 | `manifest.json`、`clips.csv`、`captions.srt`、`剪辑交接说明.md` |
| 自动生成可编辑时间线（可选） | 人在可编辑时间线基础上继续精剪 | `timeline.otio`、`timeline.kdenlive`、校验记录 |

两者都放在 `90_Draft_Project/edit_handoff/{project_revision}/`。所选方式不可用时任务必须阻塞，不得自动换另一种方式。

本机剪映真实草稿活动根推荐为：

```text
/Users/vsiyo/Desktop/照片筛选/03_Jianying_Active_Drafts
```

这里放正在编辑或近期可能复剪的真实剪映草稿。不要把活动草稿放在 iCloud 云盘、阿里云盘或移动硬盘上直接编辑。

项目内工程记录统一放：

```text
90_Draft_Project
```

成片统一放：

```text
91_Output
```

结构：

```text
90_Draft_Project/
├── edit_handoff
│   └── {project_revision}
│       ├── manifest.json / clips.csv / captions.srt / 剪辑交接说明.md
│       └── 或 timeline.otio / timeline.kdenlive / timeline_validation.json
├── 剪映工程
│   ├── official_backups
│   └── 历史 native_import_packs（仅旧项目证据）
├── HyperFrames
│   ├── src
│   ├── render_logs
│   └── README.md
├── 工程说明.md
└── 使用素材记录.md

91_Output/
├── V1
├── V2
├── Final
└── HyperFrames
```

软链接只适合 Mac 内部管理。你的原文已经明确，软链接跨设备拷贝给外部人员时会失效，外包时必须使用剪映 Mac 桌面端的备份 / 打包工程，让所有引用素材物理提取成独立包。

### 人工精剪与真实剪映草稿规则

```text
标准剪辑交接包 或 可编辑时间线
↓
人在剪映中新建或打开真实草稿
↓
草稿保存在 03_Jianying_Active_Drafts 或剪映官方默认本机草稿目录
↓
人工精剪、调色、BGM、字幕、特效
↓
关键版本用 文件 -> 备份 / 打包工程
↓
官方备份包放入 项目/90_Draft_Project/剪映工程/official_backups
↓
Final 导出到 项目/91_Output/Final
```

旧的 `native_import_packs`、`06b_jianying_draft_plan.json` 和 `06d_native_import_pack_result.yaml` 继续保留给旧项目追溯，但只作历史证据。它们不能代替当前版本的剪辑交接包或可编辑时间线，也不能作为新任务的目标。

### 剪映导出规则

`03_Jianying_Active_Drafts` 只保存真实草稿和草稿记录，不保存剪映导出的成片、封面图或测试视频。所有剪映导出物必须回到对应项目目录。

| 导出物 | 目标位置 | 后续动作 |
| --- | --- | --- |
| V1 预览成片 | `项目/91_Output/V1/` | 跑 `local_output_review`，记录返修点 |
| V2 修改版 | `项目/91_Output/V2/` | 跑 `local_output_review`，和 V1 对比 |
| Final 发布版 | `项目/91_Output/Final/` | 人工确认后发布，并复制精选副本到 80/06 |
| Final / 高光回看副本 | `项目/80_To_iCloudPhotos_精选入库/06_Final_Output_发布成片与高光/` | 只作为 iCloud 照片精选入口，不替代 91 Final |
| 封面 / 发布图临时导出 | `项目根/App_WorkCache/发布图临时导出/` | 临时改图、改字、调色，不进归档 |
| 确认可长期使用的封面候选 | `项目/80_To_iCloudPhotos_精选入库/02_Cover_Candidates_封面候选/` | 可导入 iCloud 照片或登记资产卡片 |
| 官方备份 / 打包工程 | `项目/90_Draft_Project/剪映工程/official_backups/` | 用于复剪、归档或外包交付 |

推荐命名：

```text
YYYYMMDD_项目名_V1_问题预览.mp4
YYYYMMDD_项目名_V2_节奏修正版.mp4
YYYYMMDD_项目名_Final_平台版.mp4
YYYYMMDD_项目名_封面候选01.png
```

导出后必须明确状态：

```text
V1 / V2 = 候选版本，需要质检和返修判断
Final = 人确认可发布的版本
80/06 = iCloud 照片精选副本
official_backups = 可复剪工程包，不是成片
```

V1 / V2 / Final 导出后，优先由 Obsidian `local_output_review` 任务触发 Mac OpenClaw runner：

```bash
cd /Users/vsiyo/Desktop/照片筛选
python3 99_System_OpenClaw/mac_openclaw_runner.py run-task task_YYYYMMDD_NNN
```

没有任务时再手动调用 `19_review_output_video.py`，并把报告、metrics 和 result 写入项目 `_ai_analysis/output_review/`。质检是独立证据，不改变项目阶段；是否成为最终版始终由人确认。

不允许：

```text
让脚本默认移动真实剪映草稿
让脚本直接修生产用 draft_content.json
把任何历史导入包当作当前版本的已完成粗剪
在没有明确选择的情况下切换剪辑交接方式
把剪映真实草稿放在 iCloud 或移动硬盘上直接编辑
把剪映导出的成片长期堆在 03_Jianying_Active_Drafts
```

### HyperFrames 规则

HyperFrames 在这套系统中只负责 AI 动态包装素材：

```text
标题卡
信息卡
数据图
口播图文增强
章节卡
可复用动画组件
```

它在数据流里的位置是：

```text
腾讯云初稿 / Obsidian brief / 04_script
↓
Mac OpenClaw 素材匹配、Storyboard、EDL
↓
需要标题卡、信息卡、图文动画、透明叠加或口播增强时
↓
90_Draft_Project/HyperFrames 保存源工程、prompt、组件配置和渲染记录
↓
91_Output/HyperFrames 输出 MP4 / PNG / 透明叠加素材
↓
人把导出媒体导入所选剪辑工作区，和 L3 内容目录素材、标准剪辑交接包或可编辑时间线一起精剪
↓
最终成片仍导出到 91_Output/V1、V2 或 Final，并走 local_output_review
```

所以 HyperFrames 不是单独一条发布流水线，也不是剪映草稿生成器；它是剪映前或剪映中的包装素材生产环节。

项目内源工程放：

```text
90_Draft_Project/HyperFrames/
```

项目内导出素材放：

```text
91_Output/HyperFrames/
```

跨项目可复用组件放：

```text
02_Asset_Library/HyperFrames_Components/
```

进入剪映的只应该是 HyperFrames 导出的 MP4、PNG、透明叠加素材或音频，不是 HyperFrames 源工程。HyperFrames 导出的候选成片仍要走本地成片质检和人工确认。

### 外包交付规则

```text
项目 L3 根部素材
↓
剪映工程
↓
文件 → 备份 / 打包工程
↓
输出独立工程包
↓
进入 04_Delivery_External/For_Outsourcing
↓
同步到阿里云盘
↓
分享阿里云盘链接
```

不允许：

```text
直接把带软链接的项目文件夹发给外包
直接把只在 iCloud 云端的占位文件发给外包
直接把 DJI / Insta 原始全景文件发给不会重构的外包
直接把未整理 Inbox 发给外包
```

---
