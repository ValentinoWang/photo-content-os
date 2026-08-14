# 可复制模板索引

这里放每次开新批次、新项目、交付包或归档包时可以直接复制的模板。模板集中放在系统区，不放到业务目录里，避免把真实素材入口弄乱。

复制原则：

```text
复制整个 TEMPLATE 目录或模板文件 -> 放到对应业务目录 -> 改目录名 / 文件名 -> 填真实信息
```

常用复制命令：

```bash
cd /Users/vsiyo/Desktop/照片筛选

# 新素材事件批次
cp -R 99_System_OpenClaw/templates/00_Inbox_事件批次_TEMPLATE \
  00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理

# 新正式项目
cp -R 99_System_OpenClaw/templates/01_Project_正式项目_TEMPLATE \
  "01_Project_Workspace/主题集合/YYYYMMDD_项目名"

# 对外交付包
cp -R 99_System_OpenClaw/templates/04_Delivery_交付包_TEMPLATE \
  "04_Delivery_External/For_Client_Review/YYYYMMDD_对象_用途"

# 冷归档包
cp -R 99_System_OpenClaw/templates/05_Archive_归档包_TEMPLATE \
  "05_Archive_Cold_Storage/YYYY_Completed_Projects/YYYYMMDD_项目名"
```

模板说明：

| 模板 | 复制到哪里 | 用途 |
| --- | --- | --- |
| `00_Inbox_事件批次_TEMPLATE/` | `00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理/` | 新素材进入 Mac 后的第一张说明卡 |
| `01_Project_正式项目_TEMPLATE/` | `01_Project_Workspace/主题集合/项目目录/` | 正式项目起步结构和说明 |
| `02_Asset_资产卡片_TEMPLATE.asset.md` | `02_Asset_Library/分类目录/` | 复用素材索引卡片 |
| `03_Jianying_草稿记录_TEMPLATE.md` | `03_Jianying_Active_Drafts/` 或项目 `90_Draft_Project/剪映工程/` | 记录真实剪映草稿位置、版本和备份 |
| `04_Delivery_交付包_TEMPLATE/` | `04_Delivery_External/For_Client_Review` 等 | 给客户、摄影师、外包的交付说明 |
| `05_Archive_归档包_TEMPLATE/` | `05_Archive_Cold_Storage/` | 项目冷归档说明 |
| `06_Project_Archive_Index_TEMPLATE.archive.md` | `02_Asset_Library/Project_Archive_Index/` | 发布后保留在 Mac 上的轻量检索卡 |
