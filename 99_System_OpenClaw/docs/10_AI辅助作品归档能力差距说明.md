# AI 辅助作品归档能力差距说明

## 结论

现有归档规则已经明确了“发布稳定后，阿里云盘做远程镜像、移动硬盘做冷归档、Mac 只保留索引和精选”的业务边界，但过去主要依靠人工复制模板和勾选清单，缺少可核对的文件清单、内容校验值和机器可判定的归档准入条件。

本次落地先闭合本地、无破坏性的第一段：`45_archive_project.py` 会检查正式项目目录、Final 成片、同步清单和“待增加”目录，随后生成归档清单与索引卡。工具不会自动删除素材、上传云盘、移动硬盘或修改真实剪映草稿。阿里云盘/移动硬盘回读、恢复演练和 Mac 瘦身仍需独立的后续能力，不能用本地清单冒充完成证据。

## 已落地能力

运行：

```bash
python3 99_System_OpenClaw/scripts/45_archive_project.py \
  "01_Project_Workspace/主题集合/YYYYMMDD_项目名"
```

默认只输出检查结果和候选文件数。确认无误后才使用 `--write`，它只在项目内写入 `archive_manifest.json` 和 `Project_Archive_Index/*.archive.md`，每个纳入文件记录相对路径、大小和 SHA-256 内容校验值，并排除 `_ai_analysis`、`App_WorkCache`、`待增加` 和精选临时目录。

目标副本回读：

```bash
python3 99_System_OpenClaw/scripts/45_archive_project.py \
  "项目目录" --manifest "项目目录/05_Archive_Cold_Storage/YYYY_Completed_Projects/项目名/archive_manifest.json" \
  --verify-target "/Volumes/归档盘/项目名" --write-receipt "项目目录/归档回读回执.json"
```

恢复演练必须指向一个尚不存在的新目录：

```bash
python3 99_System_OpenClaw/scripts/45_archive_project.py \
  "项目目录" --manifest "归档清单.json" --restore-from "/Volumes/归档盘/项目名" \
  --restore-to "项目目录_RESTORE_YYYYMMDD"
```

Mac 瘦身只生成计划，不执行删除：

```bash
python3 99_System_OpenClaw/scripts/45_archive_project.py \
  "项目目录" --prune-plan --receipt "阿里云回读回执.json" --receipt "移动硬盘回读回执.json"
```

准入失败时返回非零状态，并保留具体失败项。失败不触发回退路径，也不触发删除。

## 尚未闭合的差距

| 能力 | 当前状态 | 后续验收证据 |
| --- | --- | --- |
| 阿里云盘单向镜像 | 未实现 | 目标端文件数、字节数、SHA-256 回读回执 |
| 移动硬盘冷归档 | 未实现 | 卷标、路径、容量和清单逐项核对 |
| 恢复演练 | 未实现 | 恢复到新目录后的清单校验与 Final 可读性 |
| Mac 瘦身 | 未实现 | 双副本、索引卡和恢复演练全部通过后才可生成删除计划 |
| AI 归档判断 | 仅作分析证据 | 人工确认发布、保留和删除；模型建议不能直接改变归档事实 |

## 证据边界

本地工具输出属于本地运行证据，只能证明“当前项目目录可以生成候选归档清单”。它不能证明外部服务已经上传、移动硬盘可读、项目可以恢复，也不能证明作品已发布稳定。相关状态必须由对应外部回读或恢复节点单独记录。
