# 术语与目录层级

> 子文档定位：本文件承载执行细则；执行总纲只保留术语、总口径、决策表和索引。若与执行总纲冲突，以执行总纲和脚本契约检查为准。

## 一、总原则

这套系统只有一句话：

> **Mac 本地素材根负责全量收口；iCloud 云盘不承载全量素材库，只做按需中转；iCloud 照片只接收 80 中的 iCloudReady 精选；L3 根部负责项目可用素材；剪映真实草稿留在本机活动区；HyperFrames 只生产 AI 动态包装素材；Wink 负责修复增强；DJI / Insta360 负责全景重构；AI 只做分析和校验不做最终删除；阿里云盘只做整理后项目的单向远程镜像；移动硬盘只做冷归档。**

底层原则继续保留四个：

```text
1. 信息规约：文件夹提供上下文，文件名只说画面内容和处理状态
2. 叙事导向：按剪辑逻辑组织素材，不按设备和格式堆素材
3. 散落可用：项目可用素材直接暴露在 L3 根部
4. 单一真相：工作真相在 Mac 本地素材根，iCloud 云盘和阿里云盘不参与回写
```

这些原则来自你原本的 V2.0 骨架：信息规约、叙事导向、散落可用、单一真相；其中 L3 按叙事属性组织、L4 只收纳 raw-pending，也是继续保留的核心。

### V4.2 术语统一表

#### 可移植根约定

`$LOCAL_MEDIA_ROOT` 表示本机素材根。所有代码统一通过
`runtime_paths.local_media_root()` 读取；未设置时默认 `~/Desktop/照片筛选`。
软件仓库独立，包含 `scripts/`、`studio/`、`docs/`，不把素材存进 Git。

#### L1-L4 层级速查

L1-L4 是项目素材库里的目录层级，不是内容质量等级。

```text
L1 本地素材根
= $LOCAL_MEDIA_ROOT
= 整套素材系统的根目录

L2 主题集合
= $LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit
= 一组相关项目的集合，例如某一年、某个长期主题、某个创作方向

L3 项目根
= $LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit/2026-lzu-travel-and-sports
= 单条内容或一个可独立归档项目的正式目录

L4 内容目录
= 项目根/post-race-group
= 项目内按叙事场景、素材功能或内容主题划分的目录

L4/raw-pending
= 项目根/post-race-group/raw-pending
= 已经知道属于这个场景，但还需要修复、补齐、转码或人工确认的素材
```

为了和旧文档兼容，本文里继续使用“L3 内容目录 / L3 根部”这类口语说法：

```text
L3 内容目录
= 上面严格层级里的 L4 内容目录
= 项目内按叙事场景划分的素材目录

L3 根部素材
= 某个内容目录下面直接可见的素材
= 不在 raw-pending、80、90、91、ai-analysis 里面
```

实际例子：

```text
L1 本地素材根：
$LOCAL_MEDIA_ROOT

L2 主题集合：
$LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit

L3 项目根：
$LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit/2026-lzu-travel-and-sports

L4 内容目录，也就是口语里的 L3 内容目录：
$LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit/2026-lzu-travel-and-sports/post-race-group

项目 L3 源文件：
$LOCAL_MEDIA_ROOT/projects/2026-lzu-revisit/2026-lzu-travel-and-sports/post-race-group/红墙团队领奖合影_G01_补充01_未修.jpg
```

```text
制度工具根
= 软件仓库 photo-content-os/
= 规则与脚本所在位置，与本地素材根分开

本地素材根
= $LOCAL_MEDIA_ROOT
= 当前唯一整理真相，承载正式素材、工程、输出、精选准备区和 AI 分析资产

项目根
= 本地素材根/projects/主题集合/项目名
= 单个项目的正式目录

主题集合
= 本地素材根/projects/主题集合名
= 一组相关项目的父目录，例如 2026-lzu-revisit

L3 主题目录
= 项目内按叙事场景划分的素材目录
= 也叫 L3 内容目录；严格按完整路径数层时，它是项目根下面的内容目录

L3 根部素材
= 项目可用素材，可查看、可剪辑、可继续筛选
≠ 最终精选
≠ 必然可发布

项目 L3 源文件
= 项目根/某个内容目录/文件名.后缀
= 项目里的事实原件或工作源
≠ 80 精选副本
≠ 90 工程文件
≠ 91 成片输出
≠ ai-analysis 分析缓存

80 精选副本
= 从项目 L3 源文件复制或导出的 iCloudReady 内容
= 只放在 icloud-selected 的下一级目录

raw-vault
= 项目级技术源素材区，存放原始全景、Log、Raw、Live Photo 半组等不可直用素材

L3/raw-pending
= 场景级待处理区，存放已归场景但需修复、转码、防抖、补齐或人工确认的素材

项目根/work-cache
= 项目级加工缓存区，不放在具体项目根内部，不同步阿里云盘

jianying-drafts
= 本机剪映真实草稿活动根；不进 iCloud 云盘，不在移动硬盘上直接剪辑

library
= 跨项目复用索引和成品资产库
= 默认登记资产卡片，不复制项目源文件

icloud-selected
= iCloud 照片入库准备区，只放 iCloudReady 内容

iCloudReady
= 已整理、已修复或已确认无需修复、已去重、可长期回看、可导入 iCloud 照片的内容

output
= 成片输出区

draft-project/HyperFrames
= HyperFrames 源工程、prompt、组件配置和渲染记录；不是剪映草稿

output/HyperFrames
= HyperFrames 导出的 MP4 / PNG / 透明叠加素材 / 口播增强片段

group-photo-distribution
= by-name复制出的发放副本区，不是原始素材库

ai-analysis
= AI 分析资产，默认随项目保留；外包交付默认不提供

additions
= 二次筛选增量入口，不是正式素材区，不进 iCloud 照片，不进阿里云盘镜像

Live Photo 原始组
= 同名 HEIC + MOV + XMP

Live Photo 关键帧衍生图
= 从 Live Photo 生成的展示图，可 Wink 修复

Live Photo MOV 剪辑版
= 从 Live Photo MOV 派生出的剪辑素材

补充01 / 补充02
= 合照重复组在 L3 项目归档层的编号

代表 / 情绪 / 封面候选
= 进入 80 或发布层时使用的精选角色

未修
= 还没有经过 Wink 或其他后期处理

Wink已修
= 已通过 Wink 处理并确认可用

单向远程镜像
= Mac 本地素材根 → 阿里云盘，不回写、不在阿里云盘端改名
```

---
