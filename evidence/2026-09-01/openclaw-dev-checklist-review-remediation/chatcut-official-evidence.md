# ChatCut 官方资料调查证据

## 证据身份

- 调查日期：2026-09-02
- 调查方式：通过遵循 macOS 系统代理自动配置的系统浏览器访问 ChatCut 官方网站
- 证据级别：官方文档调查，不是 OpenClaw 实现、运行连接或生产验收
- 用途：支撑 D4 的产品选择；正式产品决定以 `.ssot/nodes/D4.json` 中的带版本接受记录为准

## 官方事实

| 主题 | 官方页面 | 本次可确认内容 | 不能据此声称 |
|---|---|---|---|
| 产品与接入形态 | `https://chatcut.io/docs`、`/docs/agent-plugin`、`/docs/desktop-app` | ChatCut 提供桌面应用、Codex/Claude 代理插件和桌面本地 MCP | OpenClaw 已经实现或连接 ChatCut |
| 本地媒体与时间线 | `https://chatcut.io/docs/desktop-app` | 桌面应用可以读取本地媒体，并让代理操作真实时间线 | OpenClaw 已完成实际连接，或可绕过 ChatCut 账号 |
| 导出能力 | `https://chatcut.io/docs/exporting` | 官方列出视频、音频、字幕、FCP7 XMEML、CapCut/剪映草稿等导出 | 每种格式都已由本仓库回读验收 |
| 登录账号 | `https://chatcut.io/docs/sign-in-and-account` | 支持 Google 或邮箱一次性验证码登录 | OpenClaw 可以代管 ChatCut 密码或绕过登录 |
| 隐私和条款 | `https://chatcut.io/privacy`、`https://chatcut.io/terms`、`/docs/usage-policy` | 厂商公开隐私、条款和使用政策，接入前需要按当时版本复核 | 当前调查等同于法律批准或长期兼容承诺 |

## 有界结论

1. “仓库内没有 ChatCut 代码”只能说明当前尚未集成，不能说明产品不存在。
2. 官方 Desktop 本地 MCP 是当前最适合 OpenClaw 桌面工作流的候选路径，因为它能在本机媒体和真实时间线上工作。
3. 托管代理插件与 Desktop 本地 MCP 是两条不同路径，不能共用一个含糊的连接状态或验收合同。
4. 本次没有找到公开、稳定、面向任意客户端的通用 REST API 或 SDK 合同。因此不得自行调用未公开接口，也不得虚构接口测试。
5. ChatCut 账号、项目同步和托管模型的边界继续按厂商官方合同处理；D4 只冻结 OpenClaw 的 Desktop 桌面本地 MCP 可选接入路径。

## D4 正式决定

保留 ChatCut 为可选第三方集成，使用 ChatCut Desktop 桌面本地模型上下文协议（MCP）。只有能力探测成功且用户明确连接后才显示可用；不加入 OpenClaw 内建编辑后端集合，不改变 `06_edit_decision_list.json` 的唯一权威，不调用未公开接口。

用户/产品负责人已于 2026-09-02 接受决定标识 `OPTIONAL_DESKTOP_LOCAL_MCP`。官方资料仅提供来源证据，不替代 D4 决定记录。

## 官方链接

- https://chatcut.io/docs
- https://chatcut.io/docs/agent-plugin
- https://chatcut.io/docs/desktop-app
- https://chatcut.io/docs/exporting
- https://chatcut.io/docs/sign-in-and-account
- https://chatcut.io/privacy
- https://chatcut.io/terms
- https://chatcut.io/docs/usage-policy
