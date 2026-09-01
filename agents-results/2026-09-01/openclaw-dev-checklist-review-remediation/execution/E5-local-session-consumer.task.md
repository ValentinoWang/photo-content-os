# E5 可选上游会话的本地消费

任务编号：E5
直接父节点：E4
版本：计划 5；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.login.identity@1`
失效键：`identity.local-session-consumer`

## 目标

实现本地工作台对 E4 上游配对结果的受控消费。模块仅在内存中保留不含秘密的会话引用，并以每次上游回读结果决定上游专属能力；未登录、未配对、不可用、Windows/Linux 不支持配对、过期、登出或撤销时，本地工作台功能必须仍为完整可用。

## 允许写入

- `99_System_OpenClaw/desktop/upstream_session.py`
- `99_System_OpenClaw/tests/test_upstream_session.py`

## 允许读取

- `99_System_OpenClaw/scripts/upstream_identity.py`
- `99_System_OpenClaw/scripts/openclaw_product_contract.py`
- `99_System_OpenClaw/desktop/project_store.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改其他源码、测试、共享桌面服务、前端或 SSOT 文件。
- 不得发起真实上游请求、创建真实账号或存储密码、令牌、原始密钥。
- 不得访问或写入真实媒体、项目、Inbox、归档、成片或剪映草稿。

## 行为合同

1. 只接受 E4 的安全白名单配对结果；不含上游主体标识、角色、撤销标记、配对状态和会话引用的结果必须拒绝，未知字段和秘密字段也必须拒绝。
2. 默认、未配对、不可用、过期、登出和已撤销状态都必须声明 `local_features_available=true`，且上游专属能力关闭。不得把本地功能降级为只读。
3. 刷新只能经过可注入的上游回读器，并覆盖旧会话；撤销或无效结果必须立即移除会话引用。登出必须清空全部上游状态。
4. 会话数据默认只在内存中保存；不得创建本地账户、密码或令牌数据库，错误与序列化不得泄露秘密。
5. 测试使用假回读器，覆盖未配对完整本地功能、配对后上游能力、刷新、过期、撤销、登出、Windows/Linux 不可用和秘密字段拒绝。

## 验收命令

执行 `execution/E5-local-session-consumer.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
