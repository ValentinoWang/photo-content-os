任务：OCM-UI-CONTRACT-WORKBENCH（父节点 Z1，SSOT 版本 plan=1/dag=1/interface=1/node-contract=1/schema=2）。

目标：为严格来源原型建立项目自有、发布版 Harness 可验证的 Product Context、Role Context、Surface Definition、Role-Fit、Resolved Surface Contract、Screen Contract、组件词表、UI Change 和视觉工作台。来源原型已经由用户明确选择并要求严格还原，不需要生成新的视觉候选；把冻结原型登记为 selected，候选窗格说明此次没有另开视觉探索。

权威输入（只读）：
- /Users/vsiyo/Desktop/照片筛选/AGENTS.md
- /Users/vsiyo/Desktop/照片筛选/.harness/overlays/project-harness-adapter.yaml
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-02/openclaw-media-full-checklist-implementation/.ssot/source-requirements.json
- /Users/vsiyo/Desktop/照片筛选/.agents/skills/product-context-discovery/**
- /Users/vsiyo/Desktop/照片筛选/.agents/skills/role-fit-ux/**
- /Users/vsiyo/Desktop/照片筛选/.agents/skills/screen-contract-ui/**
- /Users/vsiyo/Desktop/照片筛选/.agents/skills/visual-collaboration-contract/**

允许写入：
- /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/contracts/ui/**
- /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/visual-workbench.html
- /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/visual-workbench.json
- /Users/vsiyo/Desktop/照片筛选/.harness/overlays/project-harness-adapter.yaml（仅补项目真实 UI 路径、令牌、组件、截图与集成命令）

禁止写入：
- 99_System_OpenClaw/desktop/**、scripts/**、tests/**、schemas/**
- agents-results/**、acceptance/**、Git、远端、Obsidian、Harness Core、.agents/skills/**

要求：
1. 完整遵循 product-context-discovery、role-fit-ux、screen-contract-ui、visual-collaboration-contract。所有引用必须为项目相对路径，禁止用户级绝对路径进入工件。
2. Product Context 中把用户已明确的 D1-D6、45 条严格 HTML 和本地创作者角色作为 CONFIRMED 决定，并保留本地全功能、可选上游配对、用户配置模型、ChatCut Desktop MCP、物理位置+生命周期等边界。
3. 不创建 SURF-STUDIO。为九个 surface 建立可验证合同，K1-K6 归入项目屏/工作台。
4. Screen Contract 必须覆盖来源登记中的所有 surface、DOM 锚点、交互与 loading/empty/error/ready/success 状态；视觉层绑定 Archivo、Asap、JetBrains Mono 与全部冻结令牌。
5. visual-workbench.html/json 必须有 evidence/prototype/candidates 三栏、deep_link、完整 work_plane、五种交互状态、selection 与 engineering handoff；prototype 窗格实际加载或链接冻结原型，不能只是文字占位。
6. 使用发布版脚本验证 UI change 和 workbench；若 pipeline 需要 OpenAPI 而项目没有正式 OpenAPI，必须把该缺口明确 disposition，不得伪造 API 文档。
7. 不得修改产品实现或代签人工验收。

完成条件：所有生成/手写 JSON 均通过对应 schema/validator；visual workbench validator 为 pass；ui-change validator 为 pass（若真实发布版 schema 要求每个 surface 分开，则逐 surface 输出）；将结构化 JSON 返回写到 supervisor 指定 STRUCTURED_RETURN_PATH，包含 proposed_state、acceptance_self_check、failure_class、failure_origin、changed_files、commands、unverified_items。
