# 项目目录与素材处理

> 子文档定位：本文件承载执行细则；执行总纲只保留术语、总口径、决策表和索引。若与执行总纲冲突，以执行总纲和脚本契约检查为准。

## 四、全局目录树

这套系统由一个本地根目录和几个出口组成：

```text
制度工具根
= /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/
= 本地执行总纲、SOP、脚本、测试、schema 和运行器所在位置

本地素材根
= /Users/vsiyo/Desktop/照片筛选
= 存放素材、工程、输出、精选、同步记录和 AI 分析产物；根目录只保留日常入口和业务目录

项目根
= 本地素材根 / 01_Project_Workspace / 主题集合 / 具体项目
= 单个项目的正式目录
```

### 根目录级目录关系

唯一事实来源：

```text
本地素材根 / 制度工具根
├── 00_START_HERE_今天看这里.md
├── 00_Inbox_Mac_Intake     # 新素材入口
├── 01_Project_Workspace    # 项目工作区，主题集合统一放这里
├── 02_Asset_Library       # 跨项目资产库
├── 03_Jianying_Active_Drafts # 本机剪映真实草稿活动根
├── 04_Delivery_External   # 对外交付区
├── 05_Archive_Cold_Storage
└── 99_System_OpenClaw      # 制度细则、脚本、测试、schema、审计
```

`2026年重回兰州大学内容创作` 这类主题集合必须放在本地素材根的 `01_Project_Workspace` 下面；具体项目再放在主题集合下面。当前事实位置是 `/Users/vsiyo/Desktop/照片筛选/01_Project_Workspace/2026年重回兰州大学内容创作/20260514_兰州大学_奔赴与校运会`。

本地素材根标准结构为：

```text
/Users/vsiyo/Desktop/照片筛选
├── 00_Inbox_Mac_Intake
├── 01_Project_Workspace
│   └── 2026年重回兰州大学内容创作
│       └── 20260514_兰州大学_奔赴与校运会
│           └── App_WorkCache
├── 02_Asset_Library
├── 03_Jianying_Active_Drafts
├── 04_Delivery_External
├── 05_Archive_Cold_Storage
└── 99_System_OpenClaw
```

`/Users/vsiyo/Desktop/照片筛选/01_Project_Workspace/2026年重回兰州大学内容创作` 是当前规范位置，不再迁往 iCloud 云盘。

`01_Project_Workspace/2026年重回兰州大学内容创作/...` 里的具体项目目录是源文件和项目上下文的来源地；`02_Asset_Library` 是跨项目复用层。一个兰州大学素材如果有长期通用价值，默认做法是源文件仍留在项目 L3 目录，资产库只登记它的来源、标签、用途和建议截取。只有已经做成跨项目可直接剪辑的调色、裁切、Wink 修复、模板或品牌资产副本，才放进 `02_Asset_Library` 作为独立可复用成品。

本地素材根整体建议保持为：

```text
📂 照片筛选
├── 📄 00_START_HERE_今天看这里.md
├── 📂 99_System_OpenClaw
│   ├── 📂 docs
│   │   ├── 📄 00_本地素材与剪映HyperFrames流转总纲.md
│   │   └── 📄 01-06 SOP 子文档
│   ├── 📂 scripts
│   ├── 📂 tests
│   └── 📂 schemas
├── 📂 00_Inbox_Mac_Intake
│   ├── 📂 20260615_毕业典礼_待整理
│   │   ├── 📄 00_批次说明.md
│   │   ├── 📄 IMG_0001.HEIC
│   │   ├── 📄 IMG_0001.MOV
│   │   └── 📄 ScreenRecording_原始.mp4
│   └── 📂 20260620_麦积山旅行_待整理
│       └── 📄 00_批次说明.md
├── 📂 01_Project_Workspace
│   └── 📂 2026年重回兰州大学内容创作
│       ├── 📂 20260514_兰州大学_奔赴与校运会
│       │   ├── 📄 readme.md
│       │   ├── 📄 aliyun_sync_manifest.md
│       │   ├── 📂 _ai_analysis
│       │   │   ├── media_manifest.json
│       │   │   ├── media_decision_warnings.md
│       │   │   ├── keyframes
│       │   │   ├── audio
│       │   │   ├── prompts
│       │   │   │   ├── project_overview_prompt.md
│       │   │   │   └── project_l3_structure_prompt.md
│       │   │   ├── summaries
│       │   │   ├── user_intent_notes.md
│       │   │   ├── visual_similarity_groups.md
│       │   │   ├── l3_structure_plan.json
│       │   │   ├── additions_merge_plan.md
│       │   │   ├── additions_merge_plan.json
│       │   │   └── project_overview.md
│       │   ├── 📂 00_RawVault_不可直用
│       │   │   └── 📂 Raw_待处理
│       │   ├── 📂 01_由LLM全局分析确认的内容目录
│       │   ├── 📂 02_由LLM全局分析确认的内容目录
│       │   ├── 📂 03_由LLM全局分析确认的内容目录
│       │   ├── 📂 App_WorkCache
│       │   │   ├── 📂 Wink_修复输出暂存
│       │   │   ├── 📂 调色输出暂存
│       │   │   ├── 📂 拼图素材暂存
│       │   │   ├── 📂 拼图输出暂存
│       │   │   ├── 📂 发布图临时导出
│       │   │   ├── 📂 DJI_Studio_Exports
│       │   │   ├── 📂 Insta360_Studio_Exports
│       │   │   └── 📂 Transcode_转码暂存
│       │   ├── 📂 80_To_iCloudPhotos_精选入库
│       │   ├── 📂 90_Draft_Project
│       │   ├── 📂 91_Output
│       │   ├── 📂 92_Aliyun_SyncReady
│       │   └── 📂 待增加
│
├── 📂 02_Asset_Library
│   ├── 📄 Reusable_通用素材索引.md
│   ├── 📂 B-Roll_Scenery
│   ├── 📂 Campus_校园空镜
│   ├── 📂 Music_SFX
│   ├── 📂 Fonts_Brand
│   ├── 📂 HyperFrames_Components
│   ├── 📂 Memorial_人生节点
│   ├── 📂 Reusable_颜值类
│   └── 📂 Reusable_封面模板
├── 📂 03_Jianying_Active_Drafts
│   └── 📄 README.md
├── 📂 04_Delivery_External
│   ├── 📂 For_Outsourcing
│   ├── 📂 For_Photographer
│   └── 📂 For_Client_Review
│
└── 📂 05_Archive_Cold_Storage
    └── 📂 2026_Completed_Projects
```

---


## 九、素材进入 Mac 的统一入口

所有素材先进入 `00_Inbox_Mac_Intake`，但 Inbox 的第一层必须按事件、主题或拍摄批次建目录，不按来源建目录。

正确结构：

```text
00_Inbox_Mac_Intake/
├── YYYYMMDD_事件名_待整理/
│   ├── 00_批次说明.md
│   ├── IMG_0001.HEIC
│   ├── IMG_0001.MOV
│   └── ScreenRecording_原始.mp4
└── YYYYMM_主题混合素材_待拆分/
    └── 00_批次说明.md
```

不要把毕业典礼、麦积山旅行、校运会、商业拍摄等不同事件因为同样来自 iPhone 或 AirDrop 就混在同一个来源目录里。反过来，同一个事件里的 iPhone、相机卡、360、录屏、外部交付文件也不必再手工拆成固定来源目录。

第一层事件批次用于回答：

```text
这批素材属于哪个事件？
它可能服务哪个创作主题？
未来会进入哪个正式项目？
```

来源 / 技术类型由 Codex 扫描时自动判断，用于回答：

```text
这些文件需要怎样处理？
是否有 Live Photo 同名组？
是否是相机卡原片？
是否是 360 原始组？
是否是外部交付包？
是否是录屏原始文件？
```

`00_批次说明.md` 模板：

```markdown
# YYYYMMDD_事件名_待整理

## 云端项目引用

Obsidian 项目ID：

腾讯云初稿路径：
- 01_idea_card:
- 02_project_brief:
- 04_script:
- task:

## 本地素材批次

事件：
地点：
人物：
时间范围：
素材来源：
本地素材批次：
目标项目：
这批素材可能服务的内容：
必须保留 / 特别注意：
不确定的地方：
```

绑定到 Content OS 项目包时执行：

```bash
python3 99_System_OpenClaw/scripts/31_link_batch_to_content_project.py \
  "00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理"
```

脚本会读取 Obsidian 项目ID，校验 `08_内容项目/{project_id}/01_idea_card.md`、`02_project_brief.md`、`04_script.md` 和可选 task，生成 `事件批次/_ai_analysis/content_os_link.yaml`。没有项目ID或项目包缺文件时，本地状态是 `pending_cloud_brief`；项目包齐全时是 `brief_ready`。

事件批次内部不强制建来源子目录：

```text
可以直接平铺导入文件。
可以保留 AirDrop / SD 卡 / 网盘下载包 / zip 解压包原本带来的文件夹。
不需要为了来源手动创建 iPhone、相机卡、360、录屏等标准子目录。
```

需要特别处理的来源，由 Codex / 脚本从扩展名、元数据、文件名、目录名和关键帧中识别：

| 类型 | 识别后处理 |
| --- | --- |
| Live Photo 同名组 | 保持 HEIC / MOV / XMP 同组，不拆散 |
| 360 原始组 | 进入项目 `00_RawVault_不可直用`，重构后再剪 |
| 录屏原始文件 | 默认作为证据或参考源，能否剪辑后续判定 |
| 外部交付包 | 保留包边界，再拆入正式项目 |
| 普通照片 / 视频 | 按内容进入正式项目 L3 |

### 1. iPhone / iPad 素材

```text
iPhone / iPad 拍摄
↓
AirDrop / USB / 图像捕捉 / Finder 导入 Mac
↓
00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理
↓
Mac 上筛选
↓
原始不可直用素材进入项目 RawVault
↓
可用素材进入对应 L3
↓
Wink 修复 / 增强
↓
精选进入 80_To_iCloudPhotos_精选入库
↓
最终导入 iCloud 照片
```

实况照片 / Live Photo 第一次出现时可以并写，之后统一称为 Live Photo。Live Photo 按同名原始组管理：

```text
机场回头_LIVE01.HEIC
机场回头_LIVE01.MOV
机场回头_LIVE01.XMP
机场回头_LIVE01_关键帧_Wink已修.jpg
机场回头_LIVE01_MOV剪辑版.mp4
```

### Live Photo 导出 / 回导标准

从 Mac 照片 App 导出 Live Photo 时，统一使用：

```text
照片 App
↓
文件
↓
导出
↓
导出未修改的原片
↓
勾选 Export IPTC as XMP
```

导出后应该得到：

```text
IMG_1234.HEIC
IMG_1234.MOV
IMG_1234.XMP
```

整理进项目后改成：

```text
机场回头_LIVE01.HEIC
机场回头_LIVE01.MOV
机场回头_LIVE01.XMP
```

回导照片 App 时执行：

```text
把 HEIC + MOV + XMP 放在同一个文件夹
↓
一次性一起拖进照片 App
或 照片 App → 文件 → 导入
↓
检查是否恢复为 Live Photo
```

Live Photo 判断标准：

```text
静态好看 → 做封面 / 图文
动态有生命力 → 取 MOV 做转场 / 氛围镜头
两者都好 → HEIC + MOV + XMP 原始组都保留
无信息、无情绪、无画面价值 → 不进项目
```

Live Photo 衍生品规则：

```text
HEIC + MOV + XMP
= 可重新导回照片 App 的 Live Photo 原始组

关键帧_Wink已修.jpg
= 修复后的展示图，不再承担 Live Photo 原始结构

MOV剪辑版.mp4
= 用于剪映 / 抖音 / 小红书的视频素材
```

最重要的禁忌：

```text
不要用 Wink 修复后的 JPG 覆盖原始 HEIC
不要把 Wink 修复后的 JPG 和原来的 MOV 重新当作原生 Live Photo 管理
不要拆散同一个 Live Photo 的 HEIC / MOV / XMP
不要只把 MOV 或只把 HEIC 导回照片 App 后期待恢复 Live Photo
```

---


## 十、Wink Mac 版修复工作流

Wink 是统一修复入口。

Wink 暂存目录位于具体项目根内的 `App_WorkCache/`：

```text
本地素材根/01_Project_Workspace/主题集合/具体项目/App_WorkCache/Wink_修复输出暂存
```

照片修复、人像美颜、视频增强、防抖、降噪等 Wink 输出都先放这里；确认可用后再回填项目 L3 根部或进入 `91_Output` / `80_To_iCloudPhotos_精选入库`。

### 基本原则

```text
源文件不动
只修副本
修复结果回填 L3 根部
最终精选才进入 iCloud 照片
整理后项目文件夹同步到阿里云盘
```

### 照片修复流程

```text
项目 L3 / Raw_待处理 / 源文件
↓
复制副本到 项目根/App_WorkCache/Wink_修复输出暂存
↓
Wink Mac 版修复
↓
输出修复图
↓
放回项目对应 L3 根部
↓
复制到 80_To_iCloudPhotos_精选入库
↓
导入 iCloud 照片
↓
项目文件夹由阿里云盘单向远程镜像
```

### 视频增强流程

```text
项目 L3 / Raw_待处理 / 原视频
↓
复制副本到 项目根/App_WorkCache/Wink_修复输出暂存
↓
Wink 增强 / 防抖 / 降噪 / 画质提升
↓
输出增强视频
↓
放回项目对应 L3 根部
↓
需要发布或长期保存的复制到 80_To_iCloudPhotos_精选入库
↓
Final 成片进入 91_Output
↓
项目文件夹由阿里云盘单向远程镜像
```

### 命名示例

```text
同学合照_Wink已修.jpg
冲线抬头_关键帧_Wink已修.jpg
夜跑自拍视频_Wink增强_4K.mp4
人像采访_Wink降噪_防抖.mp4
封面候选_01_Wink已修.jpg
```

不允许：

```text
IMG_8851_final_final2.jpg
VID_20260515_wink_new_new.mp4
修复图最新版.jpg
真的最终版.mp4
```

---


## 十一、DJI 全景视频整理标准

DJI 全景素材分四类：

```text
1. 原始全景文件：只归档，不直接剪
2. Reframe 竖版：用于小红书 / 抖音 / 视频号
3. Reframe 横版：用于 B 站 / YouTube / 汇报视频
4. Snapshot 截帧：用于封面、图文、海报
```

### DJI 标准流程

```text
DJI 设备 / SD 卡
↓
Mac 整卡复制
↓
00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理
↓
项目/00_RawVault_不可直用/DJI360_原始全景_待重构/
↓
DJI Studio
↓
检查地平线、防抖、视角、曝光、色彩
↓
导出 9:16 / 16:9 / snapshot / flat360 master
↓
输出到 项目根/App_WorkCache/DJI_Studio_Exports
↓
确认可用后回填项目 L3 根部
↓
精选复制到 80_To_iCloudPhotos_精选入库
↓
项目文件夹由阿里云盘单向远程镜像
```

`DJI Reframe` 不是剪映里的功能，也不是日常必须打开的软件。它是 DJI 给 Adobe Premiere / DaVinci Resolve 使用的官方全景重构插件；本系统的默认路线仍然是先用 DJI Studio 导出可剪 MP4 / 截图，再进剪映。只有你明确要在 Premiere 或 DaVinci 时间线上继续调 360 视角时，才把 DJI Reframe 插件纳入流程。

### DJI 命名规则

```text
起跑瞬间_DJI360_reframe_9x16.mp4
冲线抬头_DJI360_reframe_慢放.mp4
操场全景_DJI360_flat360_master.mp4
奖牌特写_DJI360_snapshot_Wink已修.jpg
```

### DJI 原始文件规则

```text
原始文件尽量保持原名
不要在 Finder 里乱改 DJI 原始文件名
不要直接把原始全景文件拖进剪映
不要把未重构 DJI 全景导入 iCloud 照片
```

DJI 原始关联文件不强制把原因写进每个文件名；用文件夹名或 readme 标记状态，例如：

```text
00_RawVault_不可直用/
└── DJI360_原始全景_待重构/
    ├── DJI_0001.MP4
    ├── DJI_0002.MP4
    └── readme.md
```

---


## 十二、Insta360 全景视频整理标准

Insta360 的原始文件必须成组保存。

Insta360 官方说明，桌面工作流适合处理全分辨率素材；通过 USB 或读卡器连接后会看到包括 INSV、LRV 在内的完整文件结构，而这些文件组应尽量保持在一起。([Insta360][3])

### Insta360 标准流程

```text
Insta360 相机 / SD 卡
↓
Mac 整卡复制
↓
00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理
↓
项目/00_RawVault_不可直用/Insta360_原始全景_待重构/
↓
保持 .insv / .lrv / 元数据文件同目录
↓
Insta360 Studio
↓
预览、拼接、关键帧、重构视角
↓
导出 9:16 / 16:9 / snapshot
↓
输出到 项目根/App_WorkCache/Insta360_Studio_Exports
↓
确认可用后回填项目 L3 根部
↓
精选复制到 80_To_iCloudPhotos_精选入库
↓
项目文件夹由阿里云盘单向远程镜像
```

### Insta360 命名规则

```text
检录背影_Insta360_reframe_9x16.mp4
跑道跟拍_Insta360_reframe_16x9.mp4
冲刺瞬间_Insta360_reframe_慢放.mp4
观众欢呼_Insta360_snapshot_Wink已修.jpg
```

### Insta360 原始文件规则

```text
.insv 不拆
.lrv 不拆
同名文件组不拆
元数据不拆
原始文件不随便改名
重构导出后的视频才改成人话命名
```

---


## 十三、L3 项目可用素材原则

L3 是剪辑师和人工复核真正工作的地方，但它不是最终精选区。L3 内容目录不能由脚本模板硬编码出来，必须来自项目级全局分析：先看全项目素材、关键帧、Raw 关联组、项目叙事，再决定目录如何分。

```text
项目 L3 源文件
= 位于 项目根/某个 L3 内容目录/文件名.后缀 的项目正式素材
= 这个素材在项目语境里的事实原件或工作源
≠ 80 精选副本
≠ 90 剪映工程文件
≠ 91 成片输出
≠ _ai_analysis 分析缓存
≠ 待增加 里的未归档素材

L3 根部 = 项目可用素材区
= 可直接查看、剪辑或进入下一步处理
≠ 最终精选
≠ 一定可发布
≠ 一定可进 iCloud 照片

Raw_待处理 = 场景级待处理区
= 已知道属于哪个场景，但还需要修复、防抖、转码、补齐或人工确认
```

示例，仅表示“目录由项目语义决定”，不是固定模板：

```text
03_400米比赛过程/
├── 400米弯道推进_DJI360_reframe_9x16.mp4
├── 400米看台视角全程.mp4
├── 冲刺段_关键帧_Wink已修.jpg
└── Raw_待处理/
    ├── 起跑准备_待防抖.mp4
    └── LivePhoto半组待补齐/
```

剪辑师打开 L3 根部就能工作和继续筛选；是否发布、是否进入 iCloud 照片，必须再经过 `80_To_iCloudPhotos_精选入库` 判断。
Raw_待处理 只在需要返修、重构、补救或人工确认时进入。

例子：

```text
项目 L3 源文件：
项目根/03_赛后交流与合照/红墙团队领奖合影_G01_补充01_未修.jpg

80 精选副本：
项目根/80_To_iCloudPhotos_精选入库/03_Memorial_纪念资产/红墙团队领奖合影_G01_代表01_Wink已修.jpg

资产库索引：
02_Asset_Library/Memorial_人生节点/兰州大学校运会领奖合影.asset.md
```

`00_RawVault_不可直用` 和 `L3/Raw_待处理` 的边界固定为：

```text
00_RawVault_不可直用
= 项目级技术源素材区
= DJI 原始全景、Insta360 INSV/LRV、Log、Raw、未重构全景、Live Photo 半组等

L3/Raw_待处理
= 场景级待处理区
= 已归入场景但需修复、转码、防抖、补齐或人工确认的素材

普通未修 JPG
= L3 根部 _未修

需要修复但有价值
= L3/Raw_待处理 _待修复
```

### Raw_待处理 判别规则

`Raw_待处理` 不是“看起来一般”的筐。普通照片 / 普通视频进入 `Raw_待处理` 必须有可复核原因，并且原因要写进文件名。DJI / Insta360 / Live Photo 原始关联组不强制改名，原因写入所在文件夹名或 readme。

可以进入：

```text
普通视频待转码
普通录屏待截取
待转码
待修复
待防抖
待降噪
模糊待选
Live Photo 半组或同名组待补齐
```

不应该进入：

```text
画面主体清楚，只是开头 / 结尾需要裁掉
分辨率达到 720p 或以上，只是暂时没选用
已经能作为 B-roll、转场、氛围镜头或备用镜头的素材
```

这类素材应放在 L3 根部，并用状态说明处理动作：

```text
广州白云机场步行自拍_待截取.mp4
兰州中川机场大厅行走_待防抖.mp4
榆中高铁站广场阴天空镜_模糊待选.mp4
```

L3 / L4 限制只适用于正式项目素材区；`_ai_analysis`、`项目根/App_WorkCache`、`93_GroupPhoto_Distribution_合照发放`、`04_Delivery_External` 不受 L3/L4 限制。

“低清”只能在技术指标支持时使用：

```text
视频短边 < 720px = 可写低清 / 低分辨率
视频短边 >= 720px = 不得写低清
```

如果画面有抖动、模糊、构图废段或需二次筛选，应使用：

```text
_待截取
_待防抖
_待降噪
_模糊待选
_待修复
```

不要使用：

```text
_低质
_画质差
_随便待选
```

`99_System_OpenClaw/scripts/07_validate_media_decisions.py` 会检查这些规则；一键脚本会在抽帧前先生成 `_ai_analysis/media_decision_warnings.md`，有 ERROR 时停止后续分析。

---


## 十四、命名规则

继续执行：

> **文件夹已经说明时间、项目、场景，文件名只说明画面内容和处理状态。**

这是你原文里“文件夹层级已经说明时间、项目、场景，文件本身名字说人话”的信息规约逻辑。

命名的唯一事实来源是：

```text
99_System_OpenClaw/docs/00_本地素材与剪映HyperFrames流转总纲.md 的命名规则
99_System_OpenClaw/scripts/prompt_templates/ 的命名与结构 prompt
项目 _ai_analysis/prompts/workflows/ 中按项目渲染后的 prompt
```

脚本不能内置“跑道/成绩表/自拍/高燃”等语义硬编码；脚本只生成证据、执行已确认计划、保护关联组和处理同名冲突。内容目录和文件名由 LLM/人工依据上述 prompt 判读。

### 命名三层

```text
项目名
= 时间 + 主题 + 叙事对象
= 20260514_400米比赛_第一视角

L3 内容目录
= 剪辑/复核功能
= 01_人物呈现与候场状态
= 02_起跑与比赛过程
= 03_赛后交流与结果记录

文件名
= 画面主体 + 动作/内容 + 镜头/关系 + 状态
= 看台候场远景_号码布02.MOV
= 赛前全景相机调试_号码布02_LIVE01.HEIC
= 比赛全程_看台视角.mov
```

### 素材命名与作品风格分层

作品风格是某一次剪辑或输出的表达方向，不等于素材文件名本身。

```text
作品风格
= 第一视角全景跑400米
= 400米比赛记录
= 全景相机幕后 / 不便捷性表达
= 校运会人物状态短片

素材文件名
= 赛前全景相机调试_号码布02_LIVE01
= 起点举手示意_号码布02_近景
= 比赛全程_看台视角
```

统一口径：

```text
L3 原素材命名
= 画面事实 + 素材特质
≠ 单一作品风格

summary / project_overview / 资产卡片
= 画面事实 + 隐含叙事意图 + 可表达观点 + 适配作品风格

90_Draft_Project
= 某次剪辑的作品风格、叙事方案、使用素材记录

91_Output
= 最终成片，可以按作品风格命名
```

例如同一条 `赛前全景相机调试_号码布02_LIVE01`，可以同时服务：

```text
第一视角全景跑400米
400米比赛记录
全景相机幕后 / 不便捷性表达
校运会人物状态短片
```

因此不要把 L3 源文件命名为：

```text
第一视角全景跑400米_赛前全景相机调试_号码布02_LIVE01
```

正确做法是：

```text
L3 源文件：
赛前全景相机调试_号码布02_LIVE01.HEIC
赛前全景相机调试_号码布02_LIVE01.MOV

summary / 资产卡片：
适配作品风格：第一视角全景跑400米、400米比赛记录、全景相机幕后感

90_Draft_Project：
第一视角全景跑400米_剪辑方案.md

91_Output：
第一视角全景跑400米_竖屏版_Final.mp4
400米比赛记录_横屏完整版_Final.mp4
```

只有当素材本身已经是风格化衍生物，才允许把风格写进文件名：

```text
比赛全程_360重构_第一视角.mp4
比赛全程_360重构_小行星视角.mp4
起跑冲刺_竖屏高燃剪辑版.mp4
赛前全景相机调试_封面候选_Wink已修.jpg
```

判断优先级：

```text
1. 当前画面事实
2. 稳定素材特质：人物、动作、设备、视角、处理状态
3. 项目事件上下文
4. 可适配的作品风格
```

也就是：**素材命名用“特质到特质”，作品组织用“风格到风格”。**

内容分析必须分三层：

```text
画面事实
= 画面里能看见的主体、动作、设备、空间和状态

隐含叙事意图
= 这个画面在创作者叙事中想表达的价值，例如设备不便捷、拍摄成本、创作幕后、人物分心、真实尴尬、反差或失败感

可表达观点
= 这段素材能支撑的内容观点，例如“第一视角内容看起来爽，但拍摄准备很麻烦”
```

原则：

```text
1. 项目名已经说明的时间、地点、主题，不在每个文件名里重复
2. L3 目录已经说明的内容功能，不在每个文件名里重复
3. 文件名只写画面可见或可靠确认的信息
4. 如果项目包含人物画面，L3 结构必须有“人物呈现”或等价目录
5. 人物类文件名优先写人物状态、动作和识别线索，例如 号码布02、站位候场、看台候场
6. 动作过程类文件名优先写动作链条，例如 走向起点、起跑区赛前走动、起点举手示意、比赛全程
7. 结果记录类文件名优先写结果对象，例如 成绩表、赛后选手交流
8. 跨项目复用、交付成品、离开项目目录的副本，才需要在文件名或标题中补项目名
9. 同框 / 互动 / 交流 / 关系 只能在两个以上明确主体同时入画且存在关系线索时使用；单人主体不得因为背景有人就写同框
10. 视觉相似、同一主体、同一机位、同一场景、同一动作链条的短片段，默认归入同一个 L3 内容目录；除非画面证据能证明功能不同
11. 文件名只写画面事实，不直接写观点判断；隐含叙事意图写进 summary、项目总览、资产卡片或剪辑备注
12. 看到相机、全景相机、胸前固定设备、控制器、脚架、收音、箱包等创作工具时，必须判断是否存在“创作幕后 / 设备负担 / 拍摄准备成本”的叙事价值，不能简单归为普通候场、普通自拍或普通空镜
13. 作品风格不直接驱动 L3 源文件名；同一素材可适配多个作品风格，风格写进 summary、资产卡片、90_Draft_Project 和 91_Output
14. 只有风格化衍生物、发布成片、剪辑工程、封面候选或对外交付副本，才允许在文件名中写 `第一视角`、`小行星视角`、`竖屏高燃剪辑版`、`Final` 等风格 / 版本信息
```

### 剪辑内容类型命名

LLM / 人工做命名时，先判断素材属于哪种剪辑内容功能，再套用相应口径：

| 内容功能 | L3 目录口径 | 文件名口径 |
| --- | --- | --- |
| 人物呈现 | 人物状态、表情、候场、号码布、明确同框关系 | `看台候场远景_号码布02`、`赛前候场举手示意_号码布02` |
| 创作幕后与设备准备 | 相机、全景相机、胸前固定设备、控制器、脚架、收音、箱包、调试、安装、检查 | `赛前全景相机调试_号码布02`、`胸前设备检查_号码布02` |
| 动作过程 | 起跑、推进、冲刺、操作、运动过程 | `赛前走向起点_号码布02`、`起跑区赛前走动_号码布02`、`起点举手示意_号码布02_看台视角` |
| 环境交代 | 地点、空间、路线、场馆氛围 | `榆中校区操场看台环境`、`中川机场抵达通道` |
| 结果记录 | 成绩、奖牌、证书、赛后确认 | `成绩表_LIVE01`、`赛后选手交流_LIVE01` |
| 情绪互动 | 合照、拥抱、击掌、同学互动 | `同学合照_G01_补充01_未修` |
| 可复用通用素材 | 源文件留项目 L3，资产库只登记索引 | 文件名不为复用强行改名，资产卡片标题可带项目名和用途 |
| Raw 重构源素材 | RawVault 按原始关联组或待重构类型收纳 | `赛前候场_360原始组.OSV/LRF` |
| 待修复/待确认 | 原位置或 Raw_待处理，必须写明原因 | `看台候场_待防抖`、`人物近景_模糊待选` |

### Prompt 工作流

每次运行 `04_generate_ai_prompt.py` 后，项目内会生成：

```text
_ai_analysis/prompts/workflows/
├── 01_l3_structure_prompt.md
├── 02_file_rename_prompt.md
├── 03_clip_content_prompts.md
├── 04_batch_rename_plan_prompt.md
└── 05_icloud_asset_delivery_prompt.md
```

同时生成：

```text
_ai_analysis/visual_similarity_groups.md
= 关键帧视觉相似候选组，只用于复核和提示 LLM，不作为删除或精选依据
```

这些 prompt 的职责：

```text
01_l3_structure_prompt
= 先做项目级 L3 内容目录结构

02_file_rename_prompt
= 对单个素材给出内容化文件名；文件名写画面事实，叙事价值和适配作品风格写进 reason / narrative_value / compatible_work_styles

03_clip_content_prompts
= 按人物呈现 / 创作幕后与设备准备 / 动作过程 / 环境交代 / 结果记录 / 复用 / Raw 等剪辑功能判读，并区分素材功能与作品风格

04_batch_rename_plan_prompt
= 对一批泛名素材生成批量重命名计划；批量命名同样不把单一作品风格塞进 L3 源文件名

05_icloud_asset_delivery_prompt
= 判断 80 入库、资产库登记、交付发放和 91 输出命名；输出层可以使用作品风格，L3 源文件不因此改名
```

### 正确命名

```text
回头看镜头_Wink已修.jpg
赛前全景相机调试_号码布02_LIVE01.HEIC
赛前全景相机调试_号码布02_LIVE01.MOV
赛前全景相机调试_号码布02_LIVE01.XMP
广州地铁嘉禾望岗站列车进站.mp4
榆中高铁站环境扫拍.mp4
起跑瞬间_reframe_9x16.mp4
冲线抬头_reframe_慢放.mp4
会场全景_已调色.mp4
奖牌晃动_特写.mp4
人像采访_Wink降噪_防抖.mp4
比赛全程_360重构_第一视角.mp4
第一视角全景跑400米_竖屏版_Final.mp4
```

### 错误命名

```text
20260515_兰大校运会_DJI_Osmo360_操场_起跑_竖版_最终版_001.mp4
第一视角全景跑400米_赛前全景相机调试_号码布02_LIVE01.HEIC
IMG_8831.MP4
GX010281.MP4
VID_20260515_123456_final_final2.mp4
修复图最新版.jpg
真的最终版.mp4
冲线抬头_LIVE03.HEIC + IMG_8891.MOV + 修复信息.XMP
```

### 统一状态后缀

```text
_Wink已修
_Wink增强
_Wink降噪
_Wink防抖
_已调色
_已降噪
_已防抖
_reframe_9x16
_reframe_16x9
_flat360_master
_snapshot
_封面候选
_发布版
_慢放
_特写
_待截取
_待防抖
_待降噪
_模糊待选
_待修复
```

状态后缀判断：

```text
工具明确时：工具名 + 动作
例如 _Wink已修 / _Wink增强 / _Wink降噪 / _Wink防抖

工具不重要或多工具处理时：已 + 动作
例如 _已调色 / _已降噪 / _已防抖
```

### 地点精细化命名

当素材中能可靠提取城市、站点、地标、线路、场馆等信息时，文件名应该精细化到可识别地点。

可靠依据包括：

```text
1. 画面中清晰可见的站牌、路牌、建筑标识
2. iPhone / 相机写入的 GPS 或 QuickTime location 元数据
3. 同一连续拍摄序列中相邻素材的地点线索
4. 人工确认过的地点信息
```

正确：

```text
广州地铁嘉禾望岗站列车进站.mp4
榆中高铁站环境扫拍.mp4
兰州西站扶梯到达.mp4
```

不够精细：

```text
地铁列车进站.mp4
高铁站环境扫拍.mp4
车站人流.mp4
```

如果只能确定城市，不能确定具体站点，则写到城市即可；如果站点无法确认，不要编造。

---
