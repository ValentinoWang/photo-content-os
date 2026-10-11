# B2 删除建议实现任务

任务编号：B2
直接父节点：B1、D2
版本：计划 4；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.delete.behavior@1`
失效键：`contract.media-manifest.integrity`、`decision.delete.behavior`

## 目标

实现纯本地、只读的删除候选生成和显式选择校验。它消费 B1 媒体清单中的内容校验、健康状态、路径和媒体标识，生成可复核候选；本任务绝不移动、删除、改名或打开真实媒体文件。实际移入系统回收站和恢复属于后续 E2，不得提前实现。

## 允许写入

- `99_System_OpenClaw/scripts/media_delete_recommendations.py`
- `99_System_OpenClaw/tests/test_media_delete_recommendations.py`

## 允许读取

- `99_System_OpenClaw/scripts/01_scan_media_manifest.py`
- `99_System_OpenClaw/scripts/media_common.py`
- `99_System_OpenClaw/schemas/media_manifest.schema.json`
- `99_System_OpenClaw/tests/test_media_manifest_contract.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改任何其他源码、测试、SSOT 文件或 worker 证据文件。
- 不得移动、删除、改名、上传或写入任何真实媒体、项目、Inbox、归档、成片或剪映草稿。
- 不得调用回收站、`rm`、外部服务或网络接口。
- 不得存储密钥、绝对用户路径快照或绕过媒体清单的内容校验。

## 行为合同

1. 候选必须由媒体清单对象构造，且仅在 `media_id`、`relative_path`、64 位 SHA-256、`image_health == healthy`、`image_readable is true` 都存在且有效时生成；其他情况必须以稳定错误代码拒绝。
2. 候选要包含确定性的候选编号、媒体标识、相对路径、内容 SHA-256、健康状态、生成理由和状态 `suggested`。候选编号必须绑定上述不可变证据，避免同名或内容变化后复用旧选择。
3. 用户选择只能显式接受传入候选编号的子集；未知、重复、空白或过期候选编号必须拒绝。返回的确认结果必须保留候选证据和用户操作时间，但不产生文件副作用。
4. 所有函数在单元测试内可使用内存数据；不得要求真实媒体目录或 macOS。
5. 添加覆盖成功候选、缺哈希、健康失败、内容变更导致候选编号变化、未知/重复选择拒绝和无副作用的单元测试。

## 验收命令

执行 `execution/B2-delete-recommendation.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
