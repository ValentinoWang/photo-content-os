# E6 ChatCut Desktop 本地 MCP 可选集成

任务编号：E6
直接父节点：C4、D4
版本：计划 5；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.chatcut.integration@1`
失效键：`chatcut.optional-integration`

## 目标

实现 ChatCut Desktop 桌面本地 MCP 的可选探测和连接状态机。只使用公开的本机 `codex mcp get chatcut` 命令进行短时探测，不调用未公开 HTTP 接口、不读取 ChatCut 账号、不访问媒体，也不修改结构化剪辑方案或内建编辑后端集合。

## 允许写入

- `99_System_OpenClaw/desktop/chatcut_mcp.py`
- `99_System_OpenClaw/tests/test_chatcut_mcp.py`

## 允许读取

- `99_System_OpenClaw/desktop/edl_bridge.py`
- `99_System_OpenClaw/scripts/openclaw_product_contract.py`
- `99_System_OpenClaw/AGENTS.md`
- `agents-results/2026-09-01/openclaw-dev-checklist-review-remediation/chatcut-official-evidence.md`

## 禁止范围

- 不得修改其他源码、测试、共享桌面服务、前端、`06_edit_decision_list.json` 或 SSOT 文件。
- 不得调用 HTTP/HTTPS、SDK、浏览器自动化、网络接口或任何未公开 ChatCut 接口。
- 不得访问真实媒体、项目、Inbox、归档、成片、剪映草稿、账号或凭据。

## 行为合同

1. 默认状态必须是隐藏，且不得执行探测。只有用户触发探测时才调用可注入的命令执行器，命令精确为 `codex mcp get chatcut`，并具有短时超时。
2. 命令成功只说明可请求连接；只有用户明确确认连接且连接时重新探测成功才进入已连接状态。超时、缺失、非零退出或异常都保持不可用，不显示为可用。
3. 状态对象不包含命令输出、绝对路径、账号、密钥或媒体资料；错误使用稳定原因码。
4. 实现不得导入或调用 `requests`、`urllib`、`http.client`、socket 或未公开 API。不得把 ChatCut 加入内建编辑后端或作为结构化剪辑方案第二权威。
5. 测试使用假命令执行器，覆盖默认隐藏、精确命令、成功后等待确认、确认时重新探测、超时/失败/异常、输出脱敏和无 HTTP 依赖。

## 验收命令

执行 `execution/E6-chatcut-local-mcp.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
