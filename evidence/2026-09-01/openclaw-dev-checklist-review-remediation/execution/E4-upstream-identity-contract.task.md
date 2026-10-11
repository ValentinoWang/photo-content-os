# E4 上游统一身份合同实现任务

任务编号：E4
直接父节点：D6
版本：计划 4；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.login.identity@1`
失效键：`identity.upstream-account-contract`

## 目标

实现可注入的上游统一身份配对合同。只有用户明确发起配对时，合同才查询或幂等创建同一上游身份系统账号并回读身份、角色和撤销状态；本地不得保存密码、令牌或第二套用户账号。当前上游平台不支持配对时，返回稳定不可用结果，供后续 E5 保持 Studio 本地完整功能。

## 允许写入

- `99_System_OpenClaw/scripts/upstream_identity.py`
- `99_System_OpenClaw/tests/test_upstream_identity.py`

## 允许读取

- `99_System_OpenClaw/scripts/openclaw_product_contract.py`
- `99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json`
- `99_System_OpenClaw/scripts/runtime_paths.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改桌面服务、前端、共享身份快照、SSOT 文件或其他测试。
- 不得发起真实上游请求、创建真实账号、读取或保存令牌/密码/密钥。
- 不得建立本地账号库或任何可反序列化的账户凭据存储。
- 不得写真实媒体、项目、Inbox、归档、成片或剪映草稿。

## 行为合同

1. 通过可注入的上游客户端接口完成查找、幂等创建和回读；代码本身没有固定 URL、默认账号或网络调用。
2. 配对输入必须包含显式用户确认和非空本地配对意图；缺失确认必须拒绝且不得调用客户端。
3. 返回对象只能包含上游主体标识、去重角色列表、撤销状态、配对状态和不含秘密的会话引用；禁止出现密码、访问令牌、刷新令牌或密钥字段。
4. 用现有上游合同的运行平台判断可否配对。平台不支持、上游未安装或合同不兼容必须返回稳定的 `unavailable` 状态，而不是阻断本地功能或伪称登录。
5. 单元测试用假客户端覆盖：未确认不调用、已存在账号回读、仅一次幂等创建、已撤销账号、Windows/Linux 不可用、字段脱敏和无本地账号库。

## 验收命令

执行 `execution/E4-upstream-identity-contract.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
