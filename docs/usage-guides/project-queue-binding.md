# 08.03 已有项目包和本地素材：绑定任务队列

> 情形编号：`08.03`。  
> 适用情形：云端已经有项目包，Mac 本地也已经有对应素材批次，现在要让 Mac 进入素材匹配、分镜或 EDL 等执行流程。

## 前置条件

云端项目包至少应有：

```text
01_idea_card.md
02_project_brief.md
04_script.md
```

Mac 本地至少应有：

```text
00_Inbox_Mac_Intake/YYYYMMDD_事件名/
└── 00_批次说明.md
```

云端默认不需要知道完整 Mac 路径。它只需要知道稳定的批次名：

```yaml
batch_id: YYYYMMDD_事件名
```

Mac 会把它解析为：

```text
/Users/vsiyo/Desktop/照片筛选/00_Inbox_Mac_Intake/YYYYMMDD_事件名/
```

只有当人明确提供完整路径时，云端 task 才可以把它作为可选 hint 写入 `local_batch_path`；不能假设腾讯云天然知道 `/Users/...`。

## 云端 task 什么时候可以 ready

只有存在本地素材绑定线索时，云端才应该写：

```text
98_Agent任务队列/01_cloud_to_mac_ready/task_*.yaml
```

本地绑定线索包括任意一个：

```text
batch_id
batch_note_path
inbox_batch_path
local_project_path
content_os_link_path
Mac 已回写 result
```

没有这些线索时，任务应保持 `pending_local_binding`，不能让 Mac Runner 执行空输入。

## 给云端的正确写法

```text
【创作-再创】
参考爆款：xxx
模仿重点：开头钩子 / 节奏 / 文案结构 / 镜头顺序 / 情绪推进
tags：#xxx #xxx
本地素材批次ID：YYYYMMDD_事件名
目标平台：抖音 / 小红书
目标：生成 02_project_brief.md、04_script.md；如果需要 Mac 处理，只用 batch_id 派发任务。
```

不建议默认写：

```text
我的素材批次：/Users/vsiyo/Desktop/照片筛选/00_Inbox_Mac_Intake/YYYYMMDD_事件名
```

除非这条完整路径是人明确提供给云端的。

## 允许的 Mac 能力

只允许使用 `mac_runner_capabilities.yaml` 中的白名单 action，例如：

```text
analyze_project
match_materials_to_brief
generate_storyboard_edl
write_local_assets
create_native_import_pack
review_output_video
```

不允许任意 shell，不允许旧 action 名，不允许云端自造别名。

## Mac 桥接命令

手动处理当前 ready 队列：

```bash
python3 99_System_OpenClaw/scripts/33_enqueue_openclaw_queue_job.py --all-ready --process
```

常驻监听：

```bash
python3 99_System_OpenClaw/scripts/33_enqueue_openclaw_queue_job.py --watch --process --interval 10
```

## 执行链路

```text
98_Agent任务队列/01_cloud_to_mac_ready/task_*.yaml
-> 33_enqueue_openclaw_queue_job.py
-> _OpenClawQueue/cloud_to_mac/*.json
-> 32_process_openclaw_queue.py
-> 00_Inbox_Mac_Intake/事件批次/_openclaw/link.json
-> 如无正式项目目录，自动创建 01_Project_Workspace/主题集合/项目名
-> _OpenClawQueue/mac_to_cloud/*.result.json
-> 98_Agent任务队列/02_mac_to_cloud_results/result_*.yaml
```

## 产物

本地批次：

```text
_openclaw/link.json
_openclaw/status.json
_openclaw/project.json
```

任务层回写：

```text
98_Agent任务队列/02_mac_to_cloud_results/result_*.yaml
```

## 下一步

```text
正式项目壳已创建，但素材还在 00_Inbox_Mac_Intake
-> 运行 35_promote_inbox_batch_to_project.py，把素材移动进 01 并清掉 00

素材已经进入正式项目或需要生成素材匹配 / 分镜 / EDL
-> 看 08.04
```
