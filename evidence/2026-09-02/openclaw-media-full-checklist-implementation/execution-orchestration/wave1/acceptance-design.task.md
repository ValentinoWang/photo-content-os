任务：OCM-ACCEPTANCE-DESIGN（父节点 F，SSOT 版本 plan=1/dag=1/interface=1/node-contract=1/schema=2）。

目标：把现有 45 项清单和 OCM-Z1 的 46 份模板验收合同改成逐项、可观察、可执行的行为合同，并在实现前建立一个受保护的自动验收测试基线。用户已在当前任务中明确要求严格按冻结 HTML 完成 45 项，因此行为范围由“用户 2026-09-02 严格按 HTML 全量落地指令”批准；不得伪造 OCM-Z1 人工视觉验收结果。

权威输入（只读）：
- /Users/vsiyo/Desktop/照片筛选/AGENTS.md
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-02/openclaw-media-full-checklist-implementation/.ssot/source-requirements.json
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-02/openclaw-media-full-checklist-implementation/.ssot/nodes/*.json
- /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/tests/ 中的既有测试，仅用于选择不会由后续实现修改的保护基线和复用测试方式。

允许写入：
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-02/openclaw-media-full-checklist-implementation/build_ssot.py
- /Users/vsiyo/Desktop/照片筛选/agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/**
- /Users/vsiyo/Desktop/照片筛选/99_System_OpenClaw/tests/test_full_checklist_acceptance.py

禁止写入：
- 99_System_OpenClaw/desktop/**、99_System_OpenClaw/scripts/**、99_System_OpenClaw/schemas/**
- .ssot 手工文件（只能由 build_ssot.py 重生成）
- acceptance/human/**（人工验收由主线程另行递交，不能代签）
- Git、远端、Obsidian、Harness Core、.agents/skills/**、.harness/**

要求：
1. 先完整读取 design-acceptance-contract Skill 与模板/验证器要求。
2. 将每条合同的 Problem、Expected outcome、Normal path、Exception paths、Invariants、Data impact、Permissions、Performance/reliability 和 AC 从对应 HTML article 的具体内容生成，不能再使用 46 份逐字相同的模板段落。
3. 每条 AC 必须是该条目的具体可观测判据。特别覆盖 I4 四种且仅四种机器删除理由、H1 六段到五段命名映射、L3 生命周期与物理位置两条独立事实、S3 动态检查数量、C2 queued/running/completed/failed/expired/cancelled、D2 跨平台系统回收站、D3 DashScope 明示上传且仅在已安装 FunASR 时失败兜底、K1-K6 位于项目屏/工作台且不得建立 Studio 路由。
4. 合同批准状态只能引用上述用户明确指令；Test baseline 只有在新受保护测试文件写完、可解析且路径/sha256 登记一致时才设 LOCKED。测试可先呈红色，但必须精确描述预期行为，不得改已有受保护测试。
5. 新测试应以公共 HTTP/静态表面为主，覆盖缺失的新 API、真实纵向交互、关键视觉/DOM 锚点和禁止的模板/假接口/SURF-STUDIO。不要硬编码用户机器绝对路径，不依赖外网，不执行真实媒体删除。
6. OCM-Z1 必须绑定项目级人工工作区 acceptance/human/2026-W36/2026-09-02-OCM-Z1（物理目录仍可带 未- 前缀），列出人工视觉 H 项，但保持未签署。
7. 运行 build_ssot.py、整包 --skip-archive 校验、46 份合同验证和新测试的语法/收集检查。合同生成必须可重复。
8. 不得把测试数量或文档数量写成完成结论。

完成条件：模板重复审计为 0；46 份合同校验通过；受保护测试路径和 sha256 与当前文件一致；build_ssot.py 重跑后结果稳定；把结构化 JSON 返回写到 supervisor 指定的 STRUCTURED_RETURN_PATH，包含 proposed_state、acceptance_self_check、failure_class、failure_origin、changed_files、commands、unverified_items。
