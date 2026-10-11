# 平台职责与云端边界

> 子文档定位：本文件承载执行细则；执行总纲只保留术语、总口径、决策表和索引。若与执行总纲冲突，以执行总纲和脚本契约检查为准。

## 二、各平台职责边界

| 平台 / 工具                      | 定位            | 执行规则                                                                                                                                                          |
| ---------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **MacBook**                  | 活动整理中枢        | 所有照片、视频、Live Photo、DJI 全景、Insta 全景、录屏原始文件、外部交付原包都先进入 Mac，并先按事件批次收口；发布稳定后不长期保留全量源素材，只保留轻量索引、精选入口和必要 Final。                                                                                                              |
| **98_Agent任务队列**          | 文档任务队列        | 位于 Obsidian / iCloud vault，负责云端和 Mac 之间的任务说明、brief、YAML task 和结果文档沉淀；它告诉 Mac “要做什么”，不承载真实素材执行状态。 |
| **_OpenClawQueue**           | 本地素材执行控制队列 | 位于 Mac 本地素材根，负责 JSON 控制文件、本地批次绑定、执行状态和结果位置；它告诉 Mac 本地素材系统“从哪个批次开始、怎么执行、结果放哪里”。 |
| **剪映 Mac 版**                | 人工精剪活动工具      | 真实草稿优先留在本机 SSD，由人创建和编辑；项目 `90_Draft_Project/edit_handoff/{project_revision}` 保存当前版本的剪辑交接物，旧 native import pack 仅保留为历史证据。                                                                                   |
| **HyperFrames**              | AI 动态包装素材生产器  | 负责标题卡、信息卡、图文动画、口播增强和可复用组件；进入剪映的是导出的 MP4/PNG，不是 HyperFrames 源工程。                                                                                         |
| **iCloud 云盘**                | 按需中转盘         | 不承载全量素材库；只在需要跨设备、临时传输或人工导入 iCloud 照片时使用，不能作为项目源文件、Raw、缓存和分析资产的唯一位置。                                                                                                           |
| **Syncthing / iCloud 文档同步** | 文档任务层同步器 | 只承载 Obsidian vault 里的 `98_Agent任务队列` 等轻量任务说明和结果摘要；不直接同步 Mac 本机 `_OpenClawQueue`，不把 `00_Inbox_Mac_Intake`、项目 L3、原始照片、视频、Live Photo 组或剪映缓存作为同步对象。 |
| **iCloud 照片**                | 精选展示库         | 只保存整理过、修复过、值得长期回看的内容；Live Photo 只接收已整理的同名原始组或精选衍生图，不保存未筛选素材、Raw、废片、全景原始文件、临时文件。                                                                                                             |
| **Wink Mac 版**               | 修复与增强工具       | 统一负责照片修复、视频增强、人像修复、画质增强、防抖、降噪、调色等。Wink 在 App Store 标注支持 iPhone、iPad、Mac，并提供视频与照片增强、4K upscaling、防抖、降噪、AI Color 等功能。([App Store][1])                           |
| **DJI Studio / DJI Reframe 插件** | DJI 全景重构工具    | 日常默认用 DJI Studio 把 DJI 原始全景素材重构成 9:16、16:9、截图或 master 文件，再进入剪映。DJI Reframe 是给 Adobe Premiere 或 DaVinci Resolve 使用的官方全景重构插件，不是剪映流程的必经步骤；只有需要在 Premiere / DaVinci 里继续调视角时才用。DJI 官方下载中心列有 DJI Studio、DJI Reframe - Plugin for Adobe Premiere 和 DJI Reframe - Plugin for DaVinci Resolve。([DJI Official][2]) |
| **Insta360 Studio**          | Insta 全景重构工具  | Insta 原始 .insv / .lrv / 元数据文件成组保留，先用 Insta360 Studio 重构后再剪。Insta360 官方说明，桌面端通过 USB 或读卡器传输最稳定，并且 INSV、LRV、元数据应作为一组保留。([Insta360][3])                           |
| **阿里云盘**                     | 远程镜像备份盘       | 每个整理后的项目文件夹单向上传到阿里云盘；不在阿里云盘端改名、移动、删除、剪辑。阿里云盘官网显示其支持 Mac 客户端并可开启本地自动同步；阿里云文档也说明同步备份可支持双向同步或单向上传。([阿里云盘][4])                                                    |
| **外接硬盘**                     | 冷归档           | 项目发布稳定 1 个月后，完整项目包从 Mac 本地素材根迁移到外接硬盘，同时保留阿里云盘远程镜像；Mac 只留 `Project_Archive_Index` 索引卡用于检索和恢复。                                                                                                            |

---


## 三、本地与云端关系

你的系统里 Mac 本地是真相，云端只是不同出口，它们职责完全不同。

```text
Mac 本地素材根
= 全量素材、项目结构、工程、输出、AI 分析资产的唯一工作真相

iCloud 云盘
= 按需中转盘
= Mac / iPad / iPhone 文件 App 可访问
= 不承载全量素材库，不放 Raw、缓存和未筛选项目全量素材

iCloud 照片
= 精选展示库
= 只放整理后的照片、视频、Live Photo 原始组 / 关键帧和成片
= 不承担项目素材库职责

阿里云盘
= 远程镜像备份盘
= 只接收整理后的项目文件夹
= 不参与日常剪辑，不作为文件真相

Syncthing / iCloud 文档同步
= 同步 Obsidian vault 里的 98_Agent任务队列
= Mac Agent 再桥接到本机 _OpenClawQueue
= 不同步 00_Inbox_Mac_Intake 原素材
```

Apple 官方说明 iCloud Drive 可以在 Mac 上开启 “Sync this Mac”，并可在 Finder 里查看 iCloud Drive 文件夹；同时 Apple 也提醒，第三方云服务管理同类文件夹可能干扰 iCloud Drive 的更新。因此阿里云盘在这套系统中只做**单向远程镜像**，不做第二个工作同步盘。([苹果支持][5])

最终关系是：

```text
Mac 本地整理
↓
iCloud 照片：80 精选展示入库
↓
阿里云盘：整理后项目的远程镜像
↓
移动硬盘：完整冷归档
↓
Mac 长期只留轻量索引卡
```

---

## 四、发布后的素材生命周期

发布后素材不是“全部留 Mac”或“全部删掉”二选一，而是分层退场：

| 阶段 | 触发条件 | Mac 上状态 | 备份 / 归档状态 | 检索入口 |
| --- | --- | --- | --- | --- |
| 活动期 | 正在剪辑或刚导出 V1/V2 | 完整项目留 Mac | 可暂不同步完整包 | 项目目录 |
| 发布冷却期 | Final 发布后到稳定期 | 完整项目可暂留，方便返修 | 阿里云盘单向镜像完成 | `aliyun_sync_manifest.md` |
| 冷归档期 | 发布稳定约 1 个月 | 全量源素材迁出 Mac | 移动硬盘完整包 + 阿里云盘镜像 | `Project_Archive_Index` |
| 恢复期 | 要复剪旧项目 | 从冷归档恢复副本到 Mac | 原归档不直接编辑 | 索引卡里的恢复步骤 |

Mac 长期保留的不是全量素材，而是：

```text
02_Asset_Library/Project_Archive_Index/*.archive.md
02_Asset_Library 的资产卡片
必要的 Final 小体积副本
iCloud 照片里的 80 精选和相册
```

Mac 发布稳定后可以移走：

```text
项目 L3 全量源素材
00_RawVault_不可直用
大体积 360 / Raw / Log 原始组
剪映官方备份包的大体积副本
_ai_analysis/keyframes 和 audio 等可重建缓存
项目根/App_WorkCache 临时输出
```

---


## 五、阿里云盘远程镜像目录

阿里云盘云端建立一个完全对应的镜像根目录：

```text
📂 Creator_Media_RemoteMirror_阿里云盘
│
├── 📂 项目素材
│   └── 📂 2026年重回兰州大学内容创作
│       └── 📂 20260514_兰州大学_奔赴与校运会
│
├── 📂 02_Asset_Library
│
├── 📂 04_Delivery_External
│
└── 📂 05_Archive_Cold_Storage
```

阿里云盘不镜像这些目录和临时入口：

```text
00_Inbox_Mac_Intake
项目根/App_WorkCache
03_Jianying_Active_Drafts
项目/待增加
未完成临时转码文件
软件缓存
本地删除复核区
```

原因很简单：

```text
00_Inbox_Mac_Intake = 未整理入口，里面可能有废片、重复素材、临时素材
项目根/App_WorkCache = 项目级加工缓存区，里面是加工副本、临时输出、转码中间件
03_Jianying_Active_Drafts = 本机活动剪映草稿区，不作为远程镜像源
项目/待增加 = 未合并增量入口，还没有进入正式项目素材判断
```

阿里云盘只接收整理后的内容：

```text
项目素材
02_Asset_Library
04_Delivery_External
05_Archive_Cold_Storage
```

---


## 六、阿里云盘同步模式

阿里云盘只使用：

```text
单向上传
Mac 本地素材根 → 阿里云盘
```

不使用：

```text
双向同步
阿里云盘 → Mac
阿里云盘端编辑
阿里云盘端删除
阿里云盘端重命名
```

阿里云文档对同步备份的说明里，双向同步会让本地与云端完全一致，一端变更同步到另一端；而单向上传更适合备份场景，云端目录变化不会影响本地文件。你的素材系统应该使用单向上传逻辑。([阿里云帮助中心][6])

### 阿里云盘同步任务

在 Mac 的阿里云盘客户端中建立这些任务：

```text
任务 1：
本地路径：
/Users/vsiyo/Desktop/照片筛选/01_Project_Workspace/2026年重回兰州大学内容创作
云端路径：
Creator_Media_RemoteMirror_阿里云盘/项目素材/2026年重回兰州大学内容创作
模式：
单向上传

任务 2：
本地路径：
/Users/vsiyo/Desktop/照片筛选/02_Asset_Library
云端路径：
Creator_Media_RemoteMirror_阿里云盘/02_Asset_Library
模式：
单向上传

任务 3：
本地路径：
/Users/vsiyo/Desktop/照片筛选/04_Delivery_External
云端路径：
Creator_Media_RemoteMirror_阿里云盘/04_Delivery_External
模式：
单向上传

任务 4：
本地路径：
/Users/vsiyo/Desktop/照片筛选/05_Archive_Cold_Storage
云端路径：
Creator_Media_RemoteMirror_阿里云盘/05_Archive_Cold_Storage
模式：
单向上传
```

### 每个项目的同步记录

每个具体项目文件夹必须有：

```text
aliyun_sync_manifest.md
```

模板：

```markdown
# 阿里云盘远程镜像记录

项目名称：20260514_兰州大学_奔赴与校运会

## 本地工作路径

/Users/vsiyo/Desktop/照片筛选/01_Project_Workspace/2026年重回兰州大学内容创作/20260514_兰州大学_奔赴与校运会

## 阿里云盘镜像路径

Creator_Media_RemoteMirror_阿里云盘/项目素材/2026年重回兰州大学内容创作/20260514_兰州大学_奔赴与校运会

## 同步模式

单向上传：Mac 本地素材根 → 阿里云盘

## 同步范围

- [x] L3 可用素材
- [x] RawVault 原始不可直用素材
- [x] Wink 修复结果
- [x] DJI Studio 输出
- [x] Insta360 Studio 输出
- [x] 剪映工程说明
- [x] Final 成片
- [x] iCloud 照片精选入库文件夹

## 不同步范围

- [ ] 00_Inbox_Mac_Intake
- [ ] 项目根/App_WorkCache
- [ ] 项目/待增加
- [ ] 未完成临时转码文件
- [ ] 未合并的待增加素材
- [ ] 软件缓存

## _ai_analysis 同步规则

- [x] 默认同步 media_manifest.json、project_overview.md、summaries/、prompts/、*_plan.json
- [ ] keyframes/ 与 audio/ 是可重建分析缓存，可按空间情况排除

## 操作日志

- [2026-05-XX]：项目完成初步整理，进入 项目素材
- [2026-05-XX]：DJI / Insta 全景已完成重构输出
- [2026-05-XX]：Wink 修复结果已回填 L3
- [2026-05-XX]：Final 输出完成
- [2026-05-XX]：阿里云盘远程镜像检查完成
```

---


## 七、iCloud 云盘执行规则

iCloud 云盘是按需中转和文档同步层，不是项目素材工作区。只有临时跨设备传输、Obsidian 文档同步、归档副本或人工导入 iCloud 照片前的过桥文件可以放在这里。

Apple 的 Finder 可以显示 iCloud Drive 文件状态：只在 iCloud、等待上传、已下载、保持下载等；其中“Downloaded”表示文件在 Mac 和 iCloud 之间已经保持最新，“Keep Downloaded”表示即使空间紧张也保持下载。([苹果支持][7])

如果某个中转文件临时放在 iCloud 云盘，剪辑或处理前必须执行：

```text
项目文件夹右键
↓
保持下载 / Keep Downloaded
↓
确认 Finder 里没有等待上传、只在云端、空间不足状态
↓
再复制回 Mac 本地素材根，进入剪映 / DJI Studio / Insta360 Studio / Wink / HyperFrames
```

不允许：

```text
直接剪只在云端的占位文件
直接让 Wink 处理未下载文件
直接让 DJI / Insta 软件读取 iCloud 占位文件
直接让阿里云盘同步未下载完整的 iCloud 占位文件
直接把剪映真实草稿放在 iCloud 云盘上编辑
```

---
