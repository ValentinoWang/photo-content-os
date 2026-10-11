# E3 生命周期与物理位置配置

任务编号：E3
直接父节点：B4、D5
版本：计划 5；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.archive.lifecycle-location@1`
失效键：`archive.lifecycle-location-config`

## 目标

实现可持久化的生命周期和物理位置配置。用户选择一个或多个位置后，每个位置都必须独立保存媒体清单、内容校验值、观察时间与回读状态；生命周期的变化不得伪造外部副本已经存在。本任务只处理临时配置夹具，不复制媒体或访问云盘、移动硬盘。

## 允许写入

- `99_System_OpenClaw/desktop/archive_location_config.py`
- `99_System_OpenClaw/tests/test_archive_location_config.py`

## 允许读取

- `99_System_OpenClaw/scripts/media_common.py`
- `99_System_OpenClaw/scripts/media_delete_recommendations.py`
- `99_System_OpenClaw/desktop/project_store.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改其他源码、测试、共享桌面服务、前端或 SSOT 文件。
- 不得复制、移动、删除、上传或扫描任何真实媒体、项目、Inbox、归档、成片或剪映草稿。
- 不得调用网络、云盘或外接存储设备。
- 不得把绝对用户路径、凭据或令牌写入持久化配置、日志或回执。

## 行为合同

1. 生命周期必须是明确枚举，且与物理位置分开保存。用户选中的位置须有稳定标识、显示名称和受控位置引用；禁止绝对路径、网络 URL 与目录逃逸。
2. 每个位置必须独立记录不可变的媒体清单条目（相对路径和 64 位内容 SHA-256）、观察时间和回读状态。一个位置的成功回读不得自动推广到其他位置。
3. 只有可注入的回读器可以把某一位置由未知或失败变为已验证；生命周期更新不得修改任何位置的回读状态、内容校验值或观察时间。
4. 存储必须原子写入显式工作目录内的 JSON 文件，拒绝未知字段、重复位置、越界文件名与无效记录。
5. 测试使用临时目录与假回读器，覆盖多位置独立性、生命周期与位置解耦、内容校验拒绝、回读成功/失败、持久化回读和越界路径拒绝。

## 验收命令

执行 `execution/E3-archive-location-config.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
