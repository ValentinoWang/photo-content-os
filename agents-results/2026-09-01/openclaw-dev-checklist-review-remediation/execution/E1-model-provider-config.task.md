# E1 创意模型提供方配置实现任务

任务编号：E1
直接父节点：D3
版本：计划 4；依赖图 3；接口冻结 4；节点合同 1
决定引用：`decision.scope.audit-remediation@1`、`decision.creative-model.providers@1`
失效键：`creative-model.provider-config`

## 目标

实现桌面工作台可消费的创意模型配置模块。模块只保存提供方、端点、模型、受控密钥引用和可探测能力状态；支持 Codex/OpenAI、Claude/Anthropic、DeepSeek 和通用 OpenAI 兼容提供方。用户的原始密钥不得进入配置、项目数据、测试输出或仓库。

## 允许写入

- `99_System_OpenClaw/desktop/model_provider_config.py`
- `99_System_OpenClaw/tests/test_model_provider_config.py`

## 允许读取

- `99_System_OpenClaw/desktop/project_store.py`
- `99_System_OpenClaw/desktop/server.py`
- `99_System_OpenClaw/AGENTS.md`

## 禁止范围

- 不得修改 `desktop/server.py`、前端、任何共享路由、SSOT 文件或其他测试。
- 不得发起真实网络请求、访问用户环境变量中的密钥、创建账号或持久化明文密钥。
- 不得写真实媒体、项目、Inbox、归档、成片或剪映草稿。

## 行为合同

1. 提供方为明确枚举，至少覆盖 `codex_openai`、`claude_anthropic`、`deepseek` 和 `openai_compatible`；端点必须是 HTTPS，或显式允许的本机回环 HTTP，用于本地兼容服务。
2. 每份配置须有稳定标识、提供方、模型、端点和非空受控密钥引用；受控密钥引用不得含空白、URL、路径分隔符或疑似原始密钥值。序列化和错误对象不得泄露原始密钥。
3. 设计一个可注入的能力探测器；默认库不得联网。探测结果需区分 `available`、`unavailable` 和 `error`，并记录不含秘密的原因码。
4. 配置存储只接受显式工作目录内的 JSON 文件；写入原子化，拒绝越界路径；读取时对未知字段、重复标识或无效配置失败关闭。
5. 单元测试使用临时目录和假探测器，覆盖四类提供方、密钥泄露防护、端点约束、探测状态、持久化回读和越界路径拒绝。

## 验收命令

执行 `execution/E1-model-provider-config.validation.sh`。完成后只在 `STRUCTURED_RETURN_PATH` 写一个 JSON 对象，包含任务编号、版本、实际读写范围、改动文件、命令结果、未验证项、`proposed_state`、`acceptance_self_check`、`failure_class`、`failure_origin`、共享资源影响和风险。不得把节点标记为 `ACCEPTED`。
