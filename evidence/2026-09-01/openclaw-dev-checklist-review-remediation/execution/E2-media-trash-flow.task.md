# E2 用户确认的系统回收站流程

任务编号：E2
直接父节点：B4、D2
版本：计划 5；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.delete.behavior@1`
失效键：`media-delete.trash-flow`

## 目标

实现可注入、可审计的系统回收站流程。流程只消费 B2 已确认的候选和明确的二次确认；它必须在回收站实现无法同时提供移动后核对与可验证恢复时失败关闭，原文件保持原处或被标记为待处理。模块本身不得在导入时访问文件、调用系统命令或处理真实媒体。

## 允许写入

- `99_System_OpenClaw/scripts/media_trash_flow.py`
- `99_System_OpenClaw/tests/test_media_trash_flow.py`

## 允许读取

- `99_System_OpenClaw/scripts/media_delete_recommendations.py`
- `99_System_OpenClaw/scripts/media_common.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改其他源码、测试、共享桌面服务、前端或 SSOT 文件。
- 不得对任何真实媒体、项目、Inbox、归档、成片或剪映草稿执行操作。
- 不得使用永久删除、`unlink`、`remove`、`rmtree`、`rm` 或网络接口。
- 不得把用户路径、凭据、令牌或密钥写入日志和回执。

## 行为合同

1. 仅接受 B2 的确认结果、非空操作人及显式二次确认；候选证据、状态或编号不完整时用稳定错误码拒绝。
2. 用注入的系统回收站后端完成移动、移动后内容校验和恢复。每条收据必须至少含候选编号、原始相对路径、内容校验值、操作人、操作时间、回收站定位标识、移动后核对和恢复结果。
3. 后端不支持、目标文件不在明确工作根目录内、内容校验不一致、移动后无法回读或不能恢复时，必须失败关闭，绝不能以普通移动或永久删除替代。部分失败必须返回待处理记录，未成功移动的原文件不可变。
4. 对 macOS、Windows、Linux 使用统一的“系统回收站”接口；平台实现在无法证明可恢复时必须声明不可用，而不能声称已删除。
5. 测试只使用临时目录和假后端，覆盖未确认拒绝、路径越界、收据保留、移动后核对失败、部分失败、恢复成功、恢复校验失败和不支持后端。

## 验收命令

执行 `execution/E2-media-trash-flow.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
