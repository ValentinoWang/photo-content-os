# 08.02 已有拍摄素材但未立项：Mac Inbox 落盘

> 情形编号：`08.02`。  
> 适用情形：照片、视频、Live Photo、DJI / Insta / 录屏等真实素材已经在手，但云端还没有完整项目包，或你还不确定它属于哪个内容项目。

## 输入

```text
真实拍摄素材
事件 / 地点 / 人物 / 时间范围
可选：tags、灵感、目标平台、想做的内容方向
```

## 素材放哪里

真实素材先落 Mac：

```text
/Users/vsiyo/Desktop/照片筛选/00_Inbox_Mac_Intake/YYYYMMDD_事件名/
├── 00_批次说明.md
├── 原始照片 / 视频 / Live Photo / DJI / Insta / 录屏
└── _openclaw/
```

Inbox 第一层按事件、主题或拍摄批次建目录，不按设备来源建目录。

## `00_批次说明.md` 写什么

只写文件本身看不出来的信息：

```text
事件：
地点：
人物：
时间范围：
素材来源：
这批素材可能服务的内容：
必须保留 / 特别注意：
不确定的地方：
```

如果后续云端 task 绑定这个批次，Mac OpenClaw 会自动预填“云端自动填充区”，包括：

```text
creation_run_id
batch_id
topic
platform
content_type
feishu_doc_link
source_task_id
requested_outputs
```

脚本只插入缺失区块，不覆盖你已经写过的人工内容。

## 目录能不能改名

可以。改名后保留：

```text
_openclaw/link.json
```

后续同一个 `creation_run_id` 或 `batch_id` 会通过这个 link 找到你改名后的目录，不会重新创建旧目录名。

## 如果云端项目包还没有

先回到云端走：

```text
【创作-灵感】
【素材创作】
【创作咨询】
```

生成或补齐：

```text
01_idea_card.md
02_project_brief.md
04_script.md
```

## 如果没有正式项目目录

Mac OpenClaw 应该自动创建正式项目壳，而不是让 Inbox 目录长期承担项目目录。

手动执行：

```bash
python3 99_System_OpenClaw/scripts/34_ensure_project_from_inbox_batch.py "00_Inbox_Mac_Intake/YYYYMMDD_事件名"
```

自动队列执行时，`32_process_openclaw_queue.py` 也会调用同一套逻辑：

```text
有有效 目标项目 -> 复用该正式项目
无有效 目标项目 -> 在 01_Project_Workspace/主题集合/项目名 下创建项目壳
```

创建项目壳只做这些事：

```text
1. 创建正式项目目录
2. 补齐 80 / 90 / 91 / 92 / 待增加
3. 创建项目级 App_WorkCache
4. 回写 00_批次说明.md 的 目标项目 / 是否已有正式项目目录
5. 写入 _openclaw/project.json
```

它不会把 Inbox 原素材全部搬走，也不会替你删除素材。后续再根据素材分析和 L3 结构计划，把真实素材合并进入正式项目。

## 从 00 正式进入 01 时必须移动

`00_Inbox_Mac_Intake` 是到货区，不是长期副本区。确认批次进入正式项目后，执行：

```bash
python3 99_System_OpenClaw/scripts/35_promote_inbox_batch_to_project.py "00_Inbox_Mac_Intake/YYYYMMDD_事件名"
```

执行后：

```text
真实素材 -> 项目/00_Inbox_待分类/
批次说明 -> 项目/00_Inbox_待分类/00_批次说明.md
旧 _ai_analysis -> 项目/_ai_analysis/promoted_inbox_batches/批次名/
旧 _openclaw -> 项目/_openclaw/promoted_inbox_batches/批次名/
原 00_Inbox_Mac_Intake/事件批次 -> 删除或清空
```

这是移动，不是复制。完成迁移后，`00_Inbox_Mac_Intake` 不应继续保留同一批原素材。

## 如果批次说明已经写了 Obsidian 项目ID

Mac 可运行：

```bash
python3 99_System_OpenClaw/scripts/31_link_batch_to_content_project.py "00_Inbox_Mac_Intake/YYYYMMDD_事件名"
```

结果：

```text
事件批次/_ai_analysis/content_os_link.yaml
状态 pending_cloud_brief 或 brief_ready
```

## 下一步

```text
项目包齐全 + 本地批次存在
-> 看 08.03
```
