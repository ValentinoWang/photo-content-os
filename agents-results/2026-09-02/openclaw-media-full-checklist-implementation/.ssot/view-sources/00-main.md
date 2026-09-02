---
ARTIFACT_CLASS: ssot-development
APPLICABILITY_DECISION: ssot
GOVERNANCE_REASON: 指定 HTML 的 45 项要求横跨八个独立发布切片、九个界面和多个外部边界，需要持久来源守恒和验收权威。
SSOT_DEPTH: L2
TARGET_EVIDENCE_LEVEL: local-runtime
PLAN_VERSION: 1
DAG_VERSION: 1
INTERFACE_FREEZE_VERSION: 1
NODE_CONTRACT_VERSION: 1
SSOT_SCHEMA_VERSION: 2
FACTS_REGISTRY_VERSION: 1
SSOT_PLANNING_COMPILER: .ssot/planning-compiler.json
SSOT_MACHINE_SOURCE: .ssot/manifest.json
NORMATIVE_EXECUTABLE_ARTIFACT_MODE: strict
---

# OpenClaw 媒体 45 项全量落地 SSOT

## 业务结论与范围

这是一份新的实施权威，直接覆盖指定清单的 45 项要求。每个条目都保留独立来源定位、内容校验值、责任节点、验收准则和证据目标，不以降级、删项或过时的“可直接接”标签替代真实实现。

当前不是 45 项完成声明。已有测试只是回归基线；转写策略已按用户决定接受，但所有来源条目仍须以各自的代码、受保护测试和运行证据完成验收。

## 用户、角色与影响行为

主要用户是在本机整理媒体、复用素材、编排项目和交接剪辑的内容创作者。上游账号、模型提供方、本地剪辑工具（ChatCut）和物理存储均由用户主动选择；未登录、未配对或平台不支持时，本地功能保持完整。

## 明确不做的事

- 不自动永久删除媒体，不承诺回收站固定保留天数。
- 不把标记文档格式（Markdown）、界面文本或剪映草稿当作第二份机器执行剪辑方案。
- 不在实时探测失败或用户未主动连接时显示本地剪辑工具（ChatCut）。
- 不修改生产剪映草稿，不把策略停止维护误写成技术加密。

## 已接受的关键策略

转写策略已接受：默认使用在线转写服务（DashScope），音频发送前明示，失败时只在本机转写工具（FunASR）已安装可用的情况下回退。D3 的剩余工作是统一实现、自动验收和运行证据，不是再次等待产品拍板。

## 工程执行附录

## 发布切片

| Macro phase | Release ID | User value | Independent acceptance | Independent failure | Development baseline | Promotion baseline | Release candidate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 安全、契约和已接受决定 | 冻结安全边界与共用契约，先偿还会放大破坏半径的债。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r1:content-digest-pending` |
| R2 | 整理台 | 用户可把散素材自动分批、复核来源和落点，并由本人决定是否进入系统回收站。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r2:content-digest-pending` |
| R3 | 素材库与归档 | 用户可按结构化索引检索复用素材，并明确每个物理位置和生命周期状态。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r3:content-digest-pending` |
| R4 | 项目与结构化时间线 | 用户可查看并编辑唯一权威剪辑方案，输出真实支持的交接产物。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r4:content-digest-pending` |
| R5 | 设置、诊断与网页中台 | 用户可配置模型、预算、位置并理解诊断和上游任务状态。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r5:content-digest-pending` |
| R6 | 登录、安装与工作台 | 用户可选择配对上游身份、完成安装并从工作台进入最近工作。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r6:content-digest-pending` |
| R7 | 既有 Studio 能力迁移 | 新界面保留锁定、版本、失效传播、参考资料、复盘和文档阶段。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r7:content-digest-pending` |
| R8 | 九屏共享入口和最终整合 | 九个界面共享一套导航、状态、安全和验收边界。 | 全部节点合同和证据接受 | 候选不晋升，其他切片不受影响 | `commit@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35` | `origin/main:2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35:must-refetch` | `candidate:r8:content-digest-pending` |

## 实施路径摘要

实施按真实依赖事件驱动：安全与破坏性操作门禁先行；结构化索引、整理台、时间线、设置与 Studio 能力迁移只在有真实产物依赖时串行。八个切片各自形成不可变候选，最后才进入九屏共享入口、机器端到端验收与人工产品验收。

## 权威登记

| Claim/domain | Declared authority path | Authority layer | Lookup method | Change required | Owning node | Validation |
| --- | --- | --- | --- | --- | --- | --- |
| 45 项实施编排 | `.ssot/manifest.json` 与唯一 `.ssot/source-requirements.json` | decision/orchestration | 统一验证 | 是 | F | 来源守恒、表面覆盖与证据轮廓 |
| 原始需求 | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html` | domain-contract | SHA-256 与条目定位 | 否 | F | 45/45 条目 |
| 视觉与信息架构 | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html` | domain-contract | SHA-256 与捕获矩阵 | 否 | Z1 | DOM、计算样式、截图和交互轨迹 |
| 项目内视觉工作台 | `99_System_OpenClaw/visual-workbench.html` 与 `99_System_OpenClaw/visual-workbench.json` | project-generated | Z1 实现与视觉工作台校验 | 是 | Z1 | 证据、原型、候选、选择记录、界面状态和深链接 |
| 当前代码现状 | `source-notes.md` | runtime-evidence | 文件行号和当前主分支 | 是 | F | 新鲜审计与回归基线 |

## 规范性可执行工件

| Artifact ID | Path | Git identity | SHA-256 | Media type | Information architecture | Visual tokens | Layout | Interaction behavior | Seed data | Runtime side effects |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRC-ART-CHECKLIST | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html` | `main@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35#blob:6202f61978a7bc94e01e3d50e80698a32856746b` | `73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb` | text/html | normative | informative | informative | normative | illustrative | simulated |
| SRC-ART-PROTOTYPE | `agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html` | `main@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35#blob:cc44bc4065310264b7bf398680fc6cb0750fd163` | `aae220ef70cf7aeceefaf9a35ab4ee43d85366e92f2831513b53c36023a49cc8` | text/html | normative | normative | normative | normative | illustrative | simulated |

MUST requirement coverage: 100%（以统一机器验证通过为前提）。

| Requirement ID | Source locator | Modality | Summary | Node refs | AC refs | Evidence targets | Release refs | Scope deviation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SRC-CHECKLIST-D1 | `html:h3[1]` | MUST | 从媒体清单生成可解释、可确认且不可拆分实况照片组的事件批次计划；未确认或输入漂移时禁止迁移。 | D1 | D1/AC-01,D1/AC-02 | acceptance-fragments/OCM-D1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-D1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-D2 | `html:h3[2]` | MUST | 以稳定素材身份原子维护结构化索引，支持分类、标签、用途、计数与详情查询，同时保留 Markdown 卡片。 | D2 | D2/AC-01,D2/AC-02 | acceptance-fragments/OCM-D2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-D2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-D3 | `html:h3[3]` | MUST | 按已接受的 DashScope 默认、本机 FunASR 失败兜底与音频发送前明示策略统一所有入口，并以音频夹具验证。 | D3 | D3/AC-01,D3/AC-02 | acceptance-fragments/OCM-D3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-D3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-A1 | `html:h3[4]` | MUST | 使用上游中台身份完成邮箱、Apple 或微信登录；配对始终可选，未登录、撤销或平台不支持时本地能力不退化。 | A1 | A1/AC-01,A1/AC-02 | acceptance-fragments/OCM-A1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-A1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-A2 | `html:h3[5]` | MUST | 向导可重入地完成位置、运行环境、编辑器、账号与设备四步，并能从失败处恢复。 | A2 | A2/AC-01,A2/AC-02 | acceptance-fragments/OCM-A2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-A2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-H1 | `html:h3[6]` | MUST | 最近项目列表 + 六段流水线进度：纯前端改造，接口不用动。原型的六段（素材归档/取证分析/脚本分镜/剪辑决策/时间线/人工精剪）需要和现有五段（Brief/脚本/分镜/EDL/交付）对齐命名。 | H1 | H1/AC-01,H1/AC-02 | acceptance-fragments/OCM-H1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-H1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-H2 | `html:h3[7]` | MUST | 聚合数据中台、Codex、ChatCut Desktop 本地 MCP 与本机引擎的实时状态；单项失败不拖垮整体。 | H2 | H2/AC-01,H2/AC-02 | acceptance-fragments/OCM-H2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-H2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-H3 | `html:h3[8]` | MUST | 素材库统计（视频 412 / 照片 1,240 / 音频 36 / 占用 412 GB）：索引层已拍板要做（第 00 节 d2）。索引层落地后这个统计是顺手的事。 | H3 | H3/AC-01,H3/AC-02 | acceptance-fragments/OCM-H3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-H3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-H4 | `html:h3[9]` | MUST | 本周统计（完成任务 23 / 发布内容 4）：加一个按时间窗聚合的只读接口。数据源都在，只是没人聚合。 | H4 | H4/AC-01,H4/AC-02 | acceptance-fragments/OCM-H4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-H4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R6,R8 | none |
| SRC-CHECKLIST-I1 | `html:h3[10]` | MUST | 拖入素材 → 自动成批：已拍板：做。按第 00 节 d1 的分批器方案实现，整理台保持原型的完整交互（自动成批 → 你确认落点）。 | I1 | I1/AC-01,I1/AC-02 | acceptance-fragments/OCM-I1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-I1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R2,R8 | none |
| SRC-CHECKLIST-I2 | `html:h3[11]` | MUST | 批次卡上的来源构成（iPhone ×6 · 屏幕录制 ×2 · 相机 ×1）：读 manifest 分组计数即可，不用新后端。 | I2 | I2/AC-01,I2/AC-02 | acceptance-fragments/OCM-I2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-I2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R2,R8 | none |
| SRC-CHECKLIST-I3 | `html:h3[12]` | MUST | 连拍识别（「发现 4 组连拍」）与实况配对：把 12 的输出定契约（JSON + schema）、补测试，再接进批次分析流程。 | I3 | I3/AC-01,I3/AC-02 | acceptance-fragments/OCM-I3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-I3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R2,R8 | none |
| SRC-CHECKLIST-I4 | `html:h3[13]` | MUST | 三分落点：进项目 / 归档保留 / 推荐删除：新写。原型已经把规则收得很紧了——推荐删除只按机器可验证的四条理由（时长过短、文件损坏、哈希完全重复、相机低清代理），这四条全都能从 manifest 直接算出来，实现成本不高。 | I4 | I4/AC-01,I4/AC-02 | acceptance-fragments/OCM-I4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-I4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R2,R8 | none |
| SRC-CHECKLIST-I5 | `html:h3[14]` | MUST | 用户勾选建议并二次确认后才移入当前操作系统回收站；回读失败必须阻断，界面不得承诺固定保留天数。 | I5 | I5/AC-01,I5/AC-02 | acceptance-fragments/OCM-I5/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-I5/acceptance/local-runtime/runs/<run-id>/result.md | M45,R2,R8 | none |
| SRC-CHECKLIST-L1 | `html:h3[15]` | MUST | 复用资产卡片列表 + 分类树：索引层已拍板（第 00 节 d2）。落地后这屏基本是纯前端工作。 | L1 | L1/AC-01,L1/AC-02 | acceptance-fragments/OCM-L1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-L1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-L2 | `html:h3[16]` | MUST | 按标签筛选：同上（索引层已拍板）。原型上这排标签目前是静态的，索引接口就位后一并接活。 | L2 | L2/AC-01,L2/AC-02 | acceptance-fragments/OCM-L2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-L2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-L3 | `html:h3[17]` | MUST | 同时展示生命周期和每个物理位置的真实回读状态，逻辑登记不得冒充副本已存在。 | L3 | L3/AC-01,L3/AC-02 | acceptance-fragments/OCM-L3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-L3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-L4 | `html:h3[18]` | MUST | 归档索引卡（检索关键词、精选副本入口、恢复方式）：包 HTTP 接口。这是素材库里唯一后端完备的部分。 | L4 | L4/AC-01,L4/AC-02 | acceptance-fragments/OCM-L4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-L4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-L5 | `html:h3[19]` | MUST | 详情栏主按钮「选择项目并加入」要落到真实动作：要么补 16 号能力，要么这个按钮先降级为「复制卡片路径」这类真能做到的动作。 | L5 | L5/AC-01,L5/AC-02 | acceptance-fragments/OCM-L5/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-L5/acceptance/local-runtime/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-P1 | `html:h3[20]` | MUST | 剪辑决策条目列表（时间码 / 台词 / 角色标签）：纯前端。EDL 已经通过 GET /api/projects/:id 返回了。 | P1 | P1/AC-01,P1/AC-02 | acceptance-fragments/OCM-P1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-P2 | `html:h3[21]` | MUST | 双轨时间线（主画面 + 叠加层）：纯前端渲染。这是原型里少数「后端先行、界面还没跟上」的部分。 | P2 | P2/AC-01,P2/AC-02 | acceptance-fragments/OCM-P2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-P3 | `html:h3[22]` | MUST | 结构化时间线为主视图，同时保留文本说明与受约束的选区修改，不形成第二份机器执行权威。 | P3 | P3/AC-01,P3/AC-02 | acceptance-fragments/OCM-P3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-P4 | `html:h3[23]` | MUST | 「待补素材」缺口清单：纯前端。 | P4 | P4/AC-01,P4/AC-02 | acceptance-fragments/OCM-P4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-P5 | `html:h3[24]` | MUST | 内建只显示 handoff_pack 与 otio_kdenlive；ChatCut 仅在本地 MCP 实时探测和主动连接后成为可选去向。 | P5 | P5/AC-01,P5/AC-02 | acceptance-fragments/OCM-P5/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P5/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-P6 | `html:h3[25]` | MUST | 统一表述为剪映生产路线已停止维护，删除没有证据的“草稿加密”理由。 | P6 | P6/AC-01,P6/AC-02 | acceptance-fragments/OCM-P6/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-P6/acceptance/local-runtime/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-S1 | `html:h3[26]` | MUST | 分析预算四个数字：补一个读写配置的接口。注意 analysis_tiering 的输出 没有 JSON Schema，只有 dataclass 和 POLICY_VERSION。 | S1 | S1/AC-01,S1/AC-02 | acceptance-fragments/OCM-S1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-S1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-S2 | `html:h3[27]` | MUST | 存放位置（素材根目录 / 笔记库）：现有接口是项目级的，设置页要的是全局级，得加一个。 | S2 | S2/AC-01,S2/AC-02 | acceptance-fragments/OCM-S2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-S2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-S3 | `html:h3[28]` | MUST | 诊断页六项检查：包接口。前端别把「6 项」写死。另外这个脚本 零测试覆盖，接之前建议先补。 | S3 | S3/AC-01,S3/AC-02 | acceptance-fragments/OCM-S3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-S3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-S4 | `html:h3[29]` | MUST | Windows 与 Linux 将上游配对显示为“不支持”而不是“配置失败”，并明确本地核心能力仍可用。 | S4 | S4/AC-01,S4/AC-02 | acceptance-fragments/OCM-S4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-S4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-S5 | `html:h3[30]` | MUST | 持久化用户选择的提供方、模型、端点、思考强度和密钥引用，并确保真实执行链消费该配置。 | S5 | S5/AC-01,S5/AC-02 | acceptance-fragments/OCM-S5/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-S5/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-C1 | `html:h3[31]` | MUST | 任务列表上的 media.xxx.v1 标识符是对的：保持现状。上一轮审计已经把它们从主标签降级为次要说明，这个处理是对的。 | C1 | C1/AC-01,C1/AC-02 | acceptance-fragments/OCM-C1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-C1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-C2 | `html:h3[32]` | MUST | 任务状态机（执行中 / 已完成 / 已阻塞）：前端目前只画了 3 态，补齐映射即可。注意 expired 和 cancelled 也要有对应显示。 | C2 | C2/AC-01,C2/AC-02 | acceptance-fragments/OCM-C2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-C2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-C3 | `html:h3[33]` | MUST | 冻结基线要写进界面还是文档：上一轮审计已经把裸 hash 从诊断页移走了，这是对的。但版本不匹配时得有个地方告诉用户——建议放进诊断页的「复制报告」，不放主界面。 | C3 | C3/AC-01,C3/AC-02 | acceptance-fragments/OCM-C3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-C3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-T1 | `html:h3[34]` | MUST | 给 35_promote_inbox_batch_to_project.py 补测试：接 UI 之前先补测试。这条建议优先级高于任何界面工作。 | T1 | T1/AC-01,T1/AC-02 | acceptance-fragments/OCM-T1/acceptance/integration-contract/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-T2 | `html:h3[35]` | MUST | 给素材库三件套补测试（12 / 14 / 15）：和第 00 节的索引层一起做，定契约的同时补测试。 | T2 | T2/AC-01,T2/AC-02 | acceptance-fragments/OCM-T2/acceptance/integration-contract/runs/<run-id>/result.md | M45,R3,R8 | none |
| SRC-CHECKLIST-T3 | `html:h3[36]` | MUST | 给 43_content_os_doctor.py 和 01_scan_media_manifest.py 补测试：补基础用例。 01 至少要覆盖损坏文件、零时长、缺 EXIF 这几种边界。 | T3 | T3/AC-01,T3/AC-02 | acceptance-fragments/OCM-T3/acceptance/integration-contract/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-T4 | `html:h3[37]` | MUST | 给 analysis_tiering 的输出定 JSON Schema：补 schemas/analysis_tiering.schema.json，纳入现有的契约校验流程。 | T4 | T4/AC-01,T4/AC-02 | acceptance-fragments/OCM-T4/acceptance/integration-contract/runs/<run-id>/result.md | M45,R5,R8 | none |
| SRC-CHECKLIST-T5 | `html:h3[38]` | MUST | 所有新增写接口沿用 loopback、同源、CSRF 和明确 revision 域的乐观并发控制，跨端口 Origin 必须拒绝。 | T5 | T5/AC-01,T5/AC-02 | acceptance-fragments/OCM-T5/acceptance/integration-contract/runs/<run-id>/result.md | M45,R1,R8 | none |
| SRC-CHECKLIST-T6 | `html:h3[39]` | MUST | 七个剪映脚本要么物理归档，要么逐项声明历史且不维护，并使文档、能力清单和持续集成保持一致。 | T6 | T6/AC-01,T6/AC-02 | acceptance-fragments/OCM-T6/acceptance/integration-contract/runs/<run-id>/result.md | M45,R4,R8 | none |
| SRC-CHECKLIST-K1 | `html:h3[40]` | MUST | 区块锁定 + AI 只改选中区块：新界面必须保留这个语义。原型里完全没有「锁定」和「选中范围」的表达。 | K1 | K1/AC-01,K1/AC-02 | acceptance-fragments/OCM-K1/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K1/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-CHECKLIST-K2 | `html:h3[41]` | MUST | 版本 diff 与非破坏性回滚：原型里没有版本概念。至少要在项目屏留一个入口。 | K2 | K2/AC-01,K2/AC-02 | acceptance-fragments/OCM-K2/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K2/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-CHECKLIST-K3 | `html:h3[42]` | MUST | 下游 stale 标记（Brief 改了，脚本/分镜/EDL 自动标记需更新）：原型的六段流水线进度条是个好载体，可以顺势把 stale 状态表达进去。 | K3 | K3/AC-01,K3/AC-02 | acceptance-fragments/OCM-K3/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K3/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-CHECKLIST-K4 | `html:h3[43]` | MUST | 研究与参考（reference ≠ 自有素材）：这是一条重要的边界。原型完全没有，接进去时别把参考内容混进素材库。 | K4 | K4/AC-01,K4/AC-02 | acceptance-fragments/OCM-K4/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K4/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-CHECKLIST-K5 | `html:h3[44]` | MUST | 发布与复盘（指标 + 复盘结论 + 下次约束）：原型里完全没有。这块丢了，产品就退化成一次性工具。 | K5 | K5/AC-01,K5/AC-02 | acceptance-fragments/OCM-K5/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K5/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-CHECKLIST-K6 | `html:h3[45]` | MUST | Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。 | K6 | K6/AC-01,K6/AC-02 | acceptance-fragments/OCM-K6/acceptance/e2e/runs/<run-id>/result.md,acceptance-fragments/OCM-K6/acceptance/local-runtime/runs/<run-id>/result.md | M45,R7,R8 | none |
| SRC-PROTOTYPE-UI | `html:h1[1]` | MUST | 冻结原型的视觉令牌、DOM 锚点、控件交互和双视口捕获合同。 | Z1 | Z1/AC-01,Z1/AC-02 | acceptance-fragments/OCM-Z1/acceptance/visual-fidelity/runs/<run-id>/result.md | M45,R8 | none |

### 视觉令牌与 DOM 锚点

| Token | Frozen value | Machine assertion |
| --- | --- | --- |
| `--bg` | `#0D1314` | computed style in 1440x900 and 390x844 |
| `--panel` | `#111819` | computed style in 1440x900 and 390x844 |
| `--panel-2` | `#131C1D` | computed style in 1440x900 and 390x844 |
| `--raise` | `#161F20` | computed style in 1440x900 and 390x844 |
| `--rule` | `#1C2627` | computed style in 1440x900 and 390x844 |
| `--rule-2` | `#253133` | computed style in 1440x900 and 390x844 |
| `--ink` | `#E4EBEB` | computed style in 1440x900 and 390x844 |
| `--ink-2` | `#B0BEBF` | computed style in 1440x900 and 390x844 |
| `--ink-3` | `#7D8C8E` | computed style in 1440x900 and 390x844 |
| `--ink-4` | `#5F7477` | computed style in 1440x900 and 390x844 |
| `--ink-5` | `#46585A` | computed style in 1440x900 and 390x844 |
| `--ac` | `#4FB3BD` | computed style in 1440x900 and 390x844 |
| `--ac-2` | `#2E5F65` | computed style in 1440x900 and 390x844 |
| `--ac-bg` | `#10292C` | computed style in 1440x900 and 390x844 |
| `--ac-soft` | `#8FC7CD` | computed style in 1440x900 and 390x844 |
| `--ok` | `#7FBB92` | computed style in 1440x900 and 390x844 |
| `--ok-bg` | `#16261B` | computed style in 1440x900 and 390x844 |
| `--warn` | `#D9A94B` | computed style in 1440x900 and 390x844 |
| `--warn-bg` | `#1A1410` | computed style in 1440x900 and 390x844 |
| `--warn-line` | `#6B5528` | computed style in 1440x900 and 390x844 |
| `--f-ui` | `"Archivo","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif` | computed style in 1440x900 and 390x844 |
| `--f-tx` | `"Asap","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif` | computed style in 1440x900 and 390x844 |
| `--f-mo` | `"JetBrains Mono",ui-monospace,Menlo,monospace` | computed style in 1440x900 and 390x844 |

字体族固定为 `Archivo`、`Asap`、`JetBrains Mono`。

| Attribute | Value | Owning nodes | Evidence |
| --- | --- | --- | --- |
| `data-screen` | `home` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen` | `inbox` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen` | `library` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen` | `project` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen` | `settings` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen-panel` | `home` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen-panel` | `inbox` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen-panel` | `library` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen-panel` | `project` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-screen-panel` | `settings` | H1,I1,L1,P1,S1 | DOM structure + interaction trace |
| `data-batch` | `a` | D1,I1,I2 | DOM structure + interaction trace |
| `data-batch` | `b` | D1,I1,I2 | DOM structure + interaction trace |
| `data-batch` | `c` | D1,I1,I2 | DOM structure + interaction trace |
| `data-del` | `d1` | I4,I5 | DOM structure + interaction trace |
| `data-del` | `d2` | I4,I5 | DOM structure + interaction trace |
| `data-del` | `d3` | I4,I5 | DOM structure + interaction trace |
| `data-set-pane` | `account` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-set-pane` | `agent` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-set-pane` | `asr` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-set-pane` | `budget` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-set-pane` | `doctor` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-set-pane` | `paths` | S1,S2,S3,S4,S5,D3 | DOM structure + interaction trace |
| `data-asset-add-project` | `present` | L5 | DOM structure + interaction trace |
| `data-edl-view` | `text` | P2,P3 | DOM structure + interaction trace |
| `data-edl-view` | `timeline` | P2,P3 | DOM structure + interaction trace |
| `data-copy-report` | `present` | C3,S3 | DOM structure + interaction trace |
| `data-preserved-k` | `k1` | K1 | DOM structure + interaction trace |
| `data-preserved-k` | `k2` | K2 | DOM structure + interaction trace |
| `data-preserved-k` | `k3` | K3 | DOM structure + interaction trace |
| `data-preserved-k` | `k4` | K4 | DOM structure + interaction trace |
| `data-preserved-k` | `k5` | K5 | DOM structure + interaction trace |
| `data-preserved-k` | `k6` | K6 | DOM structure + interaction trace |

| Surface ID | Routes | States | Locales | Themes | Viewports | Helper modes | Source refs | Checklist item refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SURF-LOGIN | /login | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | A1 |
| SURF-SETUP | /setup | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | A2 |
| SURF-DASHBOARD | /app/home | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | H1,H2,H3,H4 |
| SURF-ORGANIZER | /app/inbox | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | D1,I1,I2,I3,I4,I5,T1 |
| SURF-LIBRARY | /app/library | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | D2,L1,L2,L3,L4,L5,T2 |
| SURF-PROJECT | /app/project/:projectId | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | P1,P2,P3,P4,P5,P6,T5,T6,K1,K2,K3,K4,K5,K6 |
| SURF-SETTINGS | /app/settings | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | D3,S1,S2,S3,S4,S5,T3,T4 |
| SURF-CLOUD | /cloud/tasks | loading,empty,error,ready,success | zh-CN | dark | 1440x900,390x844 | connected/local-only | SRC-ART-CHECKLIST,SRC-ART-PROTOTYPE | C1,C2,C3 |

| Interaction ID | Surface | Control | Preconditions | Trigger | State change | Visible/boundary result | Source refs | AC refs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INT-NAV-SCREENS | SURF-DASHBOARD | 主导航 | 桌面应用已启动 | 选择工作台、整理台、素材库、项目或设置 | 唯一 data-screen-panel 成为可见面板 | 标题、侧栏当前态和面板同步 / 未知目标不改变当前屏 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-H1 | H1/AC-01,Z1/AC-01 |
| INT-INBOX-BATCHES | SURF-ORGANIZER | 批次 A/B/C 与确认落点 | 媒体清单已生成且候选摘要可回读 | 选择批次并确认项目落点 | 候选从预览转为一次幂等迁移 | 批次来源、目标、数量和回执可见 / 清单漂移、碰撞或未确认时禁止移动 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-D1,SRC-CHECKLIST-I1 | D1/AC-01,I1/AC-01,I3/AC-01 |
| INT-INBOX-DELETE | SURF-ORGANIZER | 删除建议、全选和二次确认 | 四类机器理由已生成候选 | 勾选候选并二次确认 | 仅选中候选进入当前系统回收站 | 选择数量、回执和恢复入口可见 / 永久删除、未选中项、失败回读一律禁止 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-I4,SRC-CHECKLIST-I5 | I4/AC-01,I5/AC-01,D2/AC-01 |
| INT-LIBRARY-BROWSE | SURF-LIBRARY | 三种视图、七类分类、标签和详情主按钮 | 结构化索引可查询 | 切换视图、分类、标签或素材详情 | 查询条件和当前素材改变 | 计数、卡片/列表/文本及加入项目动作同步 / 空索引和未知素材显示明确空态/错误态 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-L1,SRC-CHECKLIST-L2,SRC-CHECKLIST-L5 | L1/AC-01,L2/AC-01,L5/AC-01 |
| INT-PROJECT-EDL | SURF-PROJECT | 决策列表、时间线/文本双视图、待补素材与交接包 | 项目和结构化 EDL 身份可回读 | 切换 EDL 视图或生成交接包 | 只改变展示或生成受支持输出，不改第二份权威 | 片段、轨道、缺失素材、输出后端和回执可见 / EDL 无效或后端未探测时失败关闭 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-P1,SRC-CHECKLIST-P2,SRC-CHECKLIST-P3,SRC-CHECKLIST-P4,SRC-CHECKLIST-P5 | P1/AC-01,P2/AC-01,P3/AC-01,P4/AC-01,P5/AC-01 |
| INT-PROJECT-PRESERVED | SURF-PROJECT | 锁定、版本、失效、参考、复盘、Brief 与脚本 | 项目已加载 | 进入 K1-K6 入口并执行对应动作 | 项目文档及版本按 expectedRevision 更新 | 锁定、diff、回滚、stale、参考和发布记录均可回读 / 这些能力不得拆成独立 Studio 路由 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-K1,SRC-CHECKLIST-K2,SRC-CHECKLIST-K3,SRC-CHECKLIST-K4,SRC-CHECKLIST-K5,SRC-CHECKLIST-K6 | K1/AC-01,K2/AC-01,K3/AC-01,K4/AC-01,K5/AC-01,K6/AC-01 |
| INT-SETTINGS-PANELS | SURF-SETTINGS | 六个设置面板 | 本机设置可读 | 选择存放位置、创意模型、转写、预算、账号或诊断 | 当前设置面板切换；保存动作带 CSRF 与 revision | 真实配置、能力探测和动态诊断项可见 / 不支持与配置错误分开，密钥不回显 | SRC-PROTOTYPE-UI,SRC-CHECKLIST-D3,SRC-CHECKLIST-S1,SRC-CHECKLIST-S2,SRC-CHECKLIST-S3,SRC-CHECKLIST-S4,SRC-CHECKLIST-S5 | D3/AC-01,S1/AC-01,S2/AC-01,S3/AC-01,S4/AC-01,S5/AC-01 |
| INT-LOGIN | SURF-LOGIN | 登录两步与跳过 | 桌面本地能力可用 | 选择上游登录、完成配对或跳过 | 只改变可选上游会话 | 连接状态与本地功能可用状态同时显示 / 未登录、撤销、不支持、过期均不降级本地功能 | SRC-CHECKLIST-A1 | A1/AC-01,S4/AC-01 |
| INT-SETUP | SURF-SETUP | 四步可重入向导 | 桌面入口可打开 | 逐步配置位置、运行环境、编辑器、账号与设备 | 每步状态原子保存 | 进度、失败点、重试和完成态可见 / 中断后从最后成功步骤恢复 | SRC-CHECKLIST-A2 | A2/AC-01,A2/AC-02 |
| INT-CLOUD-STATES | SURF-CLOUD | 网页中台任务状态 | 用户已主动配对上游 | 读取或刷新任务 | 上游投影状态更新 | queued/running/completed/failed/expired/cancelled 均有明确文案 / 会话失效只清除上游能力，不影响本地项目 | SRC-CHECKLIST-C2 | C2/AC-01,C2/AC-02 |

| API ID | Method | Path | Status | Schema | Revision | CSRF | Receipt | Source/owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| API-BOOTSTRAP | GET | `/api/bootstrap` | existing | csrfToken, projects, contract | none | read-only | ok + bootstrap snapshot | `99_System_OpenClaw/desktop/server.py` |
| API-HEALTH | GET | `/api/health` | existing | status, localOnly | none | read-only | ok + ready | `99_System_OpenClaw/desktop/server.py` |
| API-SETTINGS | GET | `/api/settings` | existing | settings projection | none | read-only | ok + settings | `99_System_OpenClaw/desktop/server.py` |
| API-PROJECT | GET | `/api/projects/:id` | existing | project projection including documents | none | read-only | ok + project | `99_System_OpenClaw/desktop/server.py` |
| API-ASSETS | GET | `/api/assets?category=&tags=` | existing | asset_library_index.schema.json projection | none | read-only | ok + assets + query | `99_System_OpenClaw/desktop/server.py` |
| API-ASSET-STATS | GET | `/api/assets/statistics` | existing | statistics by category/tag/use | none | read-only | ok + statistics | `99_System_OpenClaw/desktop/server.py` |
| API-INBOX-PLAN | POST | `/api/projects/:id/inbox-plan` | existing | inbox_batch_plan.schema.json | manifest digest | X-Content-OS-CSRF | ok + read-only plan | `99_System_OpenClaw/desktop/server.py` |
| API-INBOX-CONFIRM | POST | `/api/projects/:id/inbox-plan/confirm` | new | planDigest, batchId, targetProjectId, expectedRevision | required | X-Content-OS-CSRF | promotion receipt + journal identity | `planned by D1/I1/T1` |
| API-DELETE-RECOMMEND | POST | `/api/projects/:id/media-delete/recommendations` | existing | manifest -> four-reason candidates | manifest digest | X-Content-OS-CSRF | ok + candidates | `99_System_OpenClaw/desktop/server.py` |
| API-DELETE-CONFIRM | POST | `/api/projects/:id/media-delete/confirm` | existing | selectedCandidateNumbers, secondConfirmation | candidate digest | X-Content-OS-CSRF | system-trash receipt per file | `99_System_OpenClaw/desktop/server.py` |
| API-DOCUMENT-ACTION | POST | `/api/projects/:id/documents/:name/:action` | existing | patch|lock|unlock|rollback|ai-patch | expectedRevision required for writes | X-Content-OS-CSRF | ok + updated project | `99_System_OpenClaw/desktop/server.py` |
| API-DOCUMENT-DIFF | GET | `/api/projects/:id/documents/:name/diff?from=&to=` | existing | unified diff text | version pair | read-only | ok + diff | `99_System_OpenClaw/desktop/server.py` |
| API-PROVIDER | POST | `/api/settings/model-providers` | existing | provider, model, endpoint, reasoning, credentialRef | configuration identity | X-Content-OS-CSRF | ok + redacted settings | `99_System_OpenClaw/desktop/server.py` |
| API-ARCHIVE | POST | `/api/settings/archive/{lifecycle|locations}` | existing | lifecycle or physical location + manifest readback | configuration identity | X-Content-OS-CSRF | ok + archive projection | `99_System_OpenClaw/desktop/server.py` |
| API-UPSTREAM | POST | `/api/settings/upstream/{pair|refresh|logout}` | existing | opaque session reference projection | session generation | X-Content-OS-CSRF | ok + secret-free upstream state | `99_System_OpenClaw/desktop/server.py` |
| API-CHATCUT | POST | `/api/settings/chatcut/{probe|confirm}` | existing | Desktop MCP capability state | probe identity | X-Content-OS-CSRF | ok + chatcut state | `99_System_OpenClaw/desktop/server.py` |
| API-DOCTOR | GET | `/api/diagnostics` | new | dynamic checks array + report digest | none | read-only | ok + checks, no fixed count | `planned by S3/C3` |
| API-BUDGET | GET/POST | `/api/settings/analysis-budget` | new | analysis_tiering.schema.json | expectedRevision on POST | X-Content-OS-CSRF on POST | ok + effective budget | `planned by S1/T4` |
| API-ASSET-ADD | POST | `/api/projects/:id/assets` | new | assetId, intendedUse, expectedRevision | expectedRevision required | X-Content-OS-CSRF | ok + project asset reference | `planned by L5/T5` |
| API-WIZARD | GET/POST | `/api/setup/state` | new | four-step resumable setup state | expectedRevision on POST | X-Content-OS-CSRF on POST | ok + persisted step state | `planned by A2/T5` |
| API-CLOUD-TASKS | GET | `/api/upstream/tasks` | new | queued|running|completed|failed|expired|cancelled | upstream snapshot generation | read-only after optional pairing | ok + task projections | `planned by C1/C2/C3` |

| Runtime component | Kind | Status |
| --- | --- | --- |
| RT-DESKTOP | loopback desktop server | implemented-partial |
| RT-BROWSER | desktop browser frontend | implemented-partial |
| RT-UPSTREAM | optional upstream identity | external-evidence-required |
| RT-CHATCUT | Desktop local MCP | external-evidence-required |
| RT-TRASH | operating-system recycle bin | platform-evidence-required |
| RT-ARCHIVE | user-selected physical locations | physical-readback-required |

## 状态台账

| Task ID | Stage | Versions | State | Attempt | Owner | Guard ID | Blocking reason | Evidence | Unlocks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F | R1 | v1 | ACCEPTED | 0 | 主协调者 | G-SSOT | none | source-notes.md 中的来源校验值、主分支身份、45 项代码定位和 304 项回归基线 | PD,PD1,PD2,PD3,PD4,PD5,PD6,PD7,PD8,PD9,TRD,D1,D2,D3,A1,A2,H1,H2,H3,H4,I1,I2,I3,I4,I5,L1,L2,L3,L4,L5,P1,P2,P3,P4,P5,P6,S1,S2,S3,S4,S5,C1,C2,C3,T1,T2,T3,T4,T5,T6,K1,K2,K3,K4,K5,K6 |
| PD | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | D1,D2,D3,T1,T2,T3,T4,T5,T6,Q1 |
| PD1 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | D1,I2,I3,Q1 |
| PD2 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | D2,T2,Q1 |
| PD3 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | I4,I5,Q1 |
| PD4 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | H2,S5,Q1 |
| PD5 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | H2,P5,Q1 |
| PD6 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | A2,L3,L4,S2,Q1 |
| PD7 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | A1,A2,H2,S4,C1,C2,C3,Q1 |
| PD8 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | P1,P2,P3,P4,P5,K1,K2,K3,K4,K5,K6,Q1 |
| PD9 | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 用户在本任务中明确拍板，并登记为决定版本 1 | A2,P5,P6,T6,Q1 |
| TRD | R1 | v1 | ACCEPTED | 0 | 产品负责人 | G-SSOT | none | 尚无完成证据；硬依赖或人工决定未满足 | D3,Q1 |
| D1 | R1 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T1 | 尚无完成证据；硬依赖或人工决定未满足 | I1,Q1 |
| D2 | R1 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T2 | 尚无完成证据；硬依赖或人工决定未满足 | H3,L1,L2,L5,Q1 |
| D3 | R1 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q1 |
| T1 | R1 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | D1,Q1 |
| T3 | R1 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | I4,S3,Q1 |
| T5 | R1 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | A1,A2,I1,I4,I5,L5,P3,P5,S1,S2,S5,Q1 |
| Q1 | R1 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | D1,D2,D3,T1,T3,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| I1 | R2 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | D1,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q2 |
| I2 | R2 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q2 |
| I3 | R2 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T2 | 尚无完成证据；硬依赖或人工决定未满足 | Q2 |
| I4 | R2 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T3,T5 | 尚无完成证据；硬依赖或人工决定未满足 | I5,Q2 |
| I5 | R2 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | I4,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q2 |
| Q2 | R2 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | I1,I2,I3,I4,I5 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| L1 | R3 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | D2 | 尚无完成证据；硬依赖或人工决定未满足 | Q3 |
| L2 | R3 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | D2 | 尚无完成证据；硬依赖或人工决定未满足 | Q3 |
| L3 | R3 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q3 |
| L4 | R3 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q3 |
| L5 | R3 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | D2,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q3 |
| T2 | R3 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | D2,I3,Q3 |
| Q3 | R3 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | L1,L2,L3,L4,L5,T2 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| P1 | R4 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | P3,Q4 |
| P2 | R4 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | P3,P5,Q4 |
| P3 | R4 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | P1,P2,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q4 |
| P4 | R4 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q4 |
| P5 | R4 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | P2,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q4 |
| P6 | R4 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T6 | 尚无完成证据；硬依赖或人工决定未满足 | Q4 |
| T6 | R4 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | P6,Q4 |
| Q4 | R4 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | P1,P2,P3,P4,P5,P6,T6 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| S1 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T4,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q5 |
| S2 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T5 | 尚无完成证据；硬依赖或人工决定未满足 | A2,Q5 |
| S3 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T3 | 尚无完成证据；硬依赖或人工决定未满足 | A2,H2,Q5 |
| S4 | R5 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q5 |
| S5 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T5 | 尚无完成证据；硬依赖或人工决定未满足 | H2,Q5 |
| C1 | R5 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | C2,Q5 |
| C2 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | C1 | 尚无完成证据；硬依赖或人工决定未满足 | C3,Q5 |
| C3 | R5 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | C2 | 尚无完成证据；硬依赖或人工决定未满足 | Q5 |
| T4 | R5 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | S1,Q5 |
| Q5 | R5 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | S1,S2,S3,S4,S5,C1,C2,C3,T4 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| A1 | R6 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q6 |
| A2 | R6 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | S2,S3,T5 | 尚无完成证据；硬依赖或人工决定未满足 | Q6 |
| H1 | R6 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q6 |
| H2 | R6 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | S3,S5 | 尚无完成证据；硬依赖或人工决定未满足 | Q6 |
| H3 | R6 | v1 | BLOCKED | 0 | 对应领域维护者 | G-SSOT | D2 | 尚无完成证据；硬依赖或人工决定未满足 | Q6 |
| H4 | R6 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q6 |
| Q6 | R6 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | A1,A2,H1,H2,H3,H4 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| K1 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| K2 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| K3 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| K4 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| K5 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| K6 | R7 | v1 | READY | 0 | 对应领域维护者 | G-SSOT | none | 尚无完成证据；验收合同为 DRAFT，测试基线为 PLANNED | Q7 |
| Q7 | R7 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | K1,K2,K3,K4,K5,K6 | 尚无完成证据；硬依赖或人工决定未满足 | Z1 |
| Z1 | R8 | v1 | BLOCKED | 0 | 桌面前端与服务维护者 | G-SSOT | Q1,Q2,Q3,Q4,Q5,Q6,Q7 | 尚无完成证据；硬依赖或人工决定未满足 | Q8 |
| Q8 | R8 | v1 | BLOCKED | 0 | 独立验收负责人 | G-SSOT | Z1 | 尚无完成证据；硬依赖或人工决定未满足 | RZ |
| RZ | R8 | v1 | BLOCKED | 0 | 产品负责人 | G-SSOT | Q8 | 尚无完成证据；硬依赖或人工决定未满足 | none |

## 语义节点注册表

| Task ID | Semantic key | Work kind | Domain lane | Execution state | Decision state | Decision version | Readiness mode | Hard dependencies | Soft dependencies | Assumptions | Decision refs | Invalidation keys | Write authority | Acceptance authority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F | fact.checklist.full-baseline | fact-discovery | r1 | ACCEPTED | NOT_APPLICABLE | none | FORMAL | none | none | none | none | checklist.f | evidence-only | 主协调者 |
| PD | decision.scope.full-checklist | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd | isolated-record | 用户已明确决定 |
| PD1 | decision.organizer.auto-batching | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd1 | isolated-record | 用户已明确决定 |
| PD2 | decision.library.structured-index | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd2 | isolated-record | 用户已明确决定 |
| PD3 | decision.deletion.system-trash | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd3 | isolated-record | 用户已明确决定 |
| PD4 | decision.creative-model.user-config | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd4 | isolated-record | 用户已明确决定 |
| PD5 | decision.chatcut.desktop-mcp | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd5 | isolated-record | 用户已明确决定 |
| PD6 | decision.archive.location-lifecycle | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd6 | isolated-record | 用户已明确决定 |
| PD7 | decision.identity.optional-upstream | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd7 | isolated-record | 用户已明确决定 |
| PD8 | decision.edl.machine-authority | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd8 | isolated-record | 用户已明确决定 |
| PD9 | decision.jianying.historical-only | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.pd9 | isolated-record | 用户已明确决定 |
| TRD | decision.transcription.provider-boundary | decision-acceptance | r1 | ACCEPTED | ACCEPTED | 1 | FORMAL | F | none | none | none | checklist.trd | isolated-record | 用户已明确决定 |
| D1 | requirement.checklist.d1 | implementation | organizer | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD,PD1,T1 | none | none | decision.scope.full-checklist@1,decision.organizer.auto-batching@1 | checklist.d1 | implementation | 产品负责人和验收负责人 |
| D2 | requirement.checklist.d2 | implementation | library | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD,PD2,T2 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.d2 | implementation | 产品负责人和验收负责人 |
| D3 | requirement.checklist.d3 | implementation | settings | READY | NOT_APPLICABLE | none | FORMAL | F,PD,TRD | none | none | decision.scope.full-checklist@1 | checklist.d3 | implementation | 产品负责人和验收负责人 |
| T1 | requirement.checklist.t1 | implementation | organizer | READY | NOT_APPLICABLE | none | FORMAL | F,PD | none | none | decision.scope.full-checklist@1 | checklist.t1 | implementation | 产品负责人和验收负责人 |
| T3 | requirement.checklist.t3 | implementation | settings | READY | NOT_APPLICABLE | none | FORMAL | F,PD | none | none | decision.scope.full-checklist@1 | checklist.t3 | implementation | 产品负责人和验收负责人 |
| T5 | requirement.checklist.t5 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD | none | none | decision.scope.full-checklist@1 | checklist.t5 | implementation | 产品负责人和验收负责人 |
| Q1 | acceptance.release.r1 | validation | r1 | BLOCKED | NOT_APPLICABLE | none | FORMAL | PD,PD1,PD2,PD3,PD4,PD5,PD6,PD7,PD8,PD9,TRD,D1,D2,D3,T1,T3,T5 | none | none | decision.scope.full-checklist@1 | checklist.q1 | shared-generated | 独立验收负责人 |
| I1 | requirement.checklist.i1 | implementation | organizer | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,D1,T5 | none | none | decision.scope.full-checklist@1,decision.organizer.auto-batching@1 | checklist.i1 | implementation | 产品负责人和验收负责人 |
| I2 | requirement.checklist.i2 | implementation | organizer | READY | NOT_APPLICABLE | none | FORMAL | F,PD1 | none | none | decision.scope.full-checklist@1,decision.organizer.auto-batching@1 | checklist.i2 | implementation | 产品负责人和验收负责人 |
| I3 | requirement.checklist.i3 | implementation | organizer | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD1,T2 | none | none | decision.scope.full-checklist@1,decision.organizer.auto-batching@1 | checklist.i3 | implementation | 产品负责人和验收负责人 |
| I4 | requirement.checklist.i4 | implementation | organizer | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD3,T3,T5 | none | none | decision.scope.full-checklist@1,decision.deletion.system-trash@1 | checklist.i4 | implementation | 产品负责人和验收负责人 |
| I5 | requirement.checklist.i5 | implementation | organizer | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD3,I4,T5 | none | none | decision.scope.full-checklist@1,decision.deletion.system-trash@1 | checklist.i5 | implementation | 产品负责人和验收负责人 |
| Q2 | acceptance.release.r2 | validation | r2 | BLOCKED | NOT_APPLICABLE | none | FORMAL | I1,I2,I3,I4,I5 | none | none | decision.scope.full-checklist@1 | checklist.q2 | shared-generated | 独立验收负责人 |
| L1 | requirement.checklist.l1 | implementation | library | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,D2 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.l1 | implementation | 产品负责人和验收负责人 |
| L2 | requirement.checklist.l2 | implementation | library | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,D2 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.l2 | implementation | 产品负责人和验收负责人 |
| L3 | requirement.checklist.l3 | implementation | library | READY | NOT_APPLICABLE | none | FORMAL | F,PD6 | none | none | decision.scope.full-checklist@1,decision.archive.location-lifecycle@1 | checklist.l3 | implementation | 产品负责人和验收负责人 |
| L4 | requirement.checklist.l4 | implementation | library | READY | NOT_APPLICABLE | none | FORMAL | F,PD6 | none | none | decision.scope.full-checklist@1,decision.archive.location-lifecycle@1 | checklist.l4 | implementation | 产品负责人和验收负责人 |
| L5 | requirement.checklist.l5 | implementation | library | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,D2,T5 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.l5 | implementation | 产品负责人和验收负责人 |
| T2 | requirement.checklist.t2 | implementation | library | READY | NOT_APPLICABLE | none | FORMAL | F,PD,PD2 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.t2 | implementation | 产品负责人和验收负责人 |
| Q3 | acceptance.release.r3 | validation | r3 | BLOCKED | NOT_APPLICABLE | none | FORMAL | L1,L2,L3,L4,L5,T2 | none | none | decision.scope.full-checklist@1 | checklist.q3 | shared-generated | 独立验收负责人 |
| P1 | requirement.checklist.p1 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.p1 | implementation | 产品负责人和验收负责人 |
| P2 | requirement.checklist.p2 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.p2 | implementation | 产品负责人和验收负责人 |
| P3 | requirement.checklist.p3 | implementation | project | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD8,P1,P2,T5 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.p3 | implementation | 产品负责人和验收负责人 |
| P4 | requirement.checklist.p4 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.p4 | implementation | 产品负责人和验收负责人 |
| P5 | requirement.checklist.p5 | implementation | project | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD5,PD8,PD9,P2,T5 | none | none | decision.scope.full-checklist@1,decision.chatcut.desktop-mcp@1,decision.edl.machine-authority@1,decision.jianying.historical-only@1 | checklist.p5 | implementation | 产品负责人和验收负责人 |
| P6 | requirement.checklist.p6 | implementation | project | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD9,T6 | none | none | decision.scope.full-checklist@1,decision.jianying.historical-only@1 | checklist.p6 | implementation | 产品负责人和验收负责人 |
| T6 | requirement.checklist.t6 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD,PD9 | none | none | decision.scope.full-checklist@1,decision.jianying.historical-only@1 | checklist.t6 | implementation | 产品负责人和验收负责人 |
| Q4 | acceptance.release.r4 | validation | r4 | BLOCKED | NOT_APPLICABLE | none | FORMAL | P1,P2,P3,P4,P5,P6,T6 | none | none | decision.scope.full-checklist@1 | checklist.q4 | shared-generated | 独立验收负责人 |
| S1 | requirement.checklist.s1 | implementation | settings | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,T4,T5 | none | none | decision.scope.full-checklist@1 | checklist.s1 | implementation | 产品负责人和验收负责人 |
| S2 | requirement.checklist.s2 | implementation | settings | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD6,T5 | none | none | decision.scope.full-checklist@1,decision.archive.location-lifecycle@1 | checklist.s2 | implementation | 产品负责人和验收负责人 |
| S3 | requirement.checklist.s3 | implementation | settings | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,T3 | none | none | decision.scope.full-checklist@1 | checklist.s3 | implementation | 产品负责人和验收负责人 |
| S4 | requirement.checklist.s4 | implementation | settings | READY | NOT_APPLICABLE | none | FORMAL | F,PD7 | none | none | decision.scope.full-checklist@1,decision.identity.optional-upstream@1 | checklist.s4 | implementation | 产品负责人和验收负责人 |
| S5 | requirement.checklist.s5 | implementation | settings | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD4,T5 | none | none | decision.scope.full-checklist@1,decision.creative-model.user-config@1 | checklist.s5 | implementation | 产品负责人和验收负责人 |
| C1 | requirement.checklist.c1 | implementation | cloud | READY | NOT_APPLICABLE | none | FORMAL | F,PD7 | none | none | decision.scope.full-checklist@1,decision.identity.optional-upstream@1 | checklist.c1 | implementation | 产品负责人和验收负责人 |
| C2 | requirement.checklist.c2 | implementation | cloud | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD7,C1 | none | none | decision.scope.full-checklist@1,decision.identity.optional-upstream@1 | checklist.c2 | implementation | 产品负责人和验收负责人 |
| C3 | requirement.checklist.c3 | implementation | cloud | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD7,C2 | none | none | decision.scope.full-checklist@1,decision.identity.optional-upstream@1 | checklist.c3 | implementation | 产品负责人和验收负责人 |
| T4 | requirement.checklist.t4 | implementation | settings | READY | NOT_APPLICABLE | none | FORMAL | F,PD | none | none | decision.scope.full-checklist@1 | checklist.t4 | implementation | 产品负责人和验收负责人 |
| Q5 | acceptance.release.r5 | validation | r5 | BLOCKED | NOT_APPLICABLE | none | FORMAL | S1,S2,S3,S4,S5,C1,C2,C3,T4 | none | none | decision.scope.full-checklist@1 | checklist.q5 | shared-generated | 独立验收负责人 |
| A1 | requirement.checklist.a1 | implementation | login | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD7,T5 | none | none | decision.scope.full-checklist@1,decision.identity.optional-upstream@1 | checklist.a1 | implementation | 产品负责人和验收负责人 |
| A2 | requirement.checklist.a2 | implementation | setup | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD6,PD7,PD9,S2,S3,T5 | none | none | decision.scope.full-checklist@1,decision.archive.location-lifecycle@1,decision.identity.optional-upstream@1,decision.jianying.historical-only@1 | checklist.a2 | implementation | 产品负责人和验收负责人 |
| H1 | requirement.checklist.h1 | implementation | dashboard | READY | NOT_APPLICABLE | none | FORMAL | F | none | none | decision.scope.full-checklist@1 | checklist.h1 | implementation | 产品负责人和验收负责人 |
| H2 | requirement.checklist.h2 | implementation | dashboard | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,PD4,PD5,PD7,S3,S5 | none | none | decision.scope.full-checklist@1,decision.creative-model.user-config@1,decision.chatcut.desktop-mcp@1,decision.identity.optional-upstream@1 | checklist.h2 | implementation | 产品负责人和验收负责人 |
| H3 | requirement.checklist.h3 | implementation | dashboard | BLOCKED | NOT_APPLICABLE | none | FORMAL | F,D2 | none | none | decision.scope.full-checklist@1,decision.library.structured-index@1 | checklist.h3 | implementation | 产品负责人和验收负责人 |
| H4 | requirement.checklist.h4 | implementation | dashboard | READY | NOT_APPLICABLE | none | FORMAL | F | none | none | decision.scope.full-checklist@1 | checklist.h4 | implementation | 产品负责人和验收负责人 |
| Q6 | acceptance.release.r6 | validation | r6 | BLOCKED | NOT_APPLICABLE | none | FORMAL | A1,A2,H1,H2,H3,H4 | none | none | decision.scope.full-checklist@1 | checklist.q6 | shared-generated | 独立验收负责人 |
| K1 | requirement.checklist.k1 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k1 | implementation | 产品负责人和验收负责人 |
| K2 | requirement.checklist.k2 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k2 | implementation | 产品负责人和验收负责人 |
| K3 | requirement.checklist.k3 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k3 | implementation | 产品负责人和验收负责人 |
| K4 | requirement.checklist.k4 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k4 | implementation | 产品负责人和验收负责人 |
| K5 | requirement.checklist.k5 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k5 | implementation | 产品负责人和验收负责人 |
| K6 | requirement.checklist.k6 | implementation | project | READY | NOT_APPLICABLE | none | FORMAL | F,PD8 | none | none | decision.scope.full-checklist@1,decision.edl.machine-authority@1 | checklist.k6 | implementation | 产品负责人和验收负责人 |
| Q7 | acceptance.release.r7 | validation | r7 | BLOCKED | NOT_APPLICABLE | none | FORMAL | K1,K2,K3,K4,K5,K6 | none | none | decision.scope.full-checklist@1 | checklist.q7 | shared-generated | 独立验收负责人 |
| Z1 | integration.nine-surfaces | implementation | r8 | BLOCKED | NOT_APPLICABLE | none | FORMAL | Q1,Q2,Q3,Q4,Q5,Q6,Q7 | none | none | decision.scope.full-checklist@1,decision.organizer.auto-batching@1,decision.library.structured-index@1,decision.deletion.system-trash@1,decision.creative-model.user-config@1,decision.chatcut.desktop-mcp@1,decision.archive.location-lifecycle@1,decision.identity.optional-upstream@1,decision.edl.machine-authority@1,decision.jianying.historical-only@1 | checklist.z1 | implementation | 产品负责人和独立验收负责人 |
| Q8 | acceptance.release.r8 | validation | r8 | BLOCKED | NOT_APPLICABLE | none | FORMAL | Z1 | none | none | decision.scope.full-checklist@1 | checklist.q8 | shared-generated | 独立验收负责人 |
| RZ | release.full-checklist | release-decision | r8 | BLOCKED | NOT_APPLICABLE | none | FORMAL | Q8 | none | none | decision.scope.full-checklist@1 | checklist.rz | shared-generated | 产品负责人 |

## 依赖边表

| From | To | Dependency type | Dependency scope | Required upstream state | Assumption IDs | Invalidation keys | Transferred input | Gate/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F | PD | hard | specific-output | ACCEPTED | none | edge.f.pd | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD1 | hard | specific-output | ACCEPTED | none | edge.f.pd1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD2 | hard | specific-output | ACCEPTED | none | edge.f.pd2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD3 | hard | specific-output | ACCEPTED | none | edge.f.pd3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD4 | hard | specific-output | ACCEPTED | none | edge.f.pd4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD5 | hard | specific-output | ACCEPTED | none | edge.f.pd5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD6 | hard | specific-output | ACCEPTED | none | edge.f.pd6 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD7 | hard | specific-output | ACCEPTED | none | edge.f.pd7 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD8 | hard | specific-output | ACCEPTED | none | edge.f.pd8 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | PD9 | hard | specific-output | ACCEPTED | none | edge.f.pd9 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | TRD | hard | specific-output | ACCEPTED | none | edge.f.trd | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | D1 | hard | specific-output | ACCEPTED | none | edge.f.d1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | D1 | hard | specific-output | ACCEPTED | none | edge.pd.d1 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| PD1 | D1 | hard | specific-output | ACCEPTED | none | edge.pd1.d1 | PD1 已接受的合同、实现或验收产物 | PD1 节点状态与候选内容校验值 |
| T1 | D1 | hard | specific-output | ACCEPTED | none | edge.t1.d1 | T1 已接受的合同、实现或验收产物 | T1 节点状态与候选内容校验值 |
| F | D2 | hard | specific-output | ACCEPTED | none | edge.f.d2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | D2 | hard | specific-output | ACCEPTED | none | edge.pd.d2 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| PD2 | D2 | hard | specific-output | ACCEPTED | none | edge.pd2.d2 | PD2 已接受的合同、实现或验收产物 | PD2 节点状态与候选内容校验值 |
| T2 | D2 | hard | specific-output | ACCEPTED | none | edge.t2.d2 | T2 已接受的合同、实现或验收产物 | T2 节点状态与候选内容校验值 |
| F | D3 | hard | specific-output | ACCEPTED | none | edge.f.d3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | D3 | hard | specific-output | ACCEPTED | none | edge.pd.d3 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| TRD | D3 | hard | specific-output | ACCEPTED | none | edge.trd.d3 | TRD 已接受的合同、实现或验收产物 | TRD 节点状态与候选内容校验值 |
| F | A1 | hard | specific-output | ACCEPTED | none | edge.f.a1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD7 | A1 | hard | specific-output | ACCEPTED | none | edge.pd7.a1 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| T5 | A1 | hard | specific-output | ACCEPTED | none | edge.t5.a1 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | A2 | hard | specific-output | ACCEPTED | none | edge.f.a2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD6 | A2 | hard | specific-output | ACCEPTED | none | edge.pd6.a2 | PD6 已接受的合同、实现或验收产物 | PD6 节点状态与候选内容校验值 |
| PD7 | A2 | hard | specific-output | ACCEPTED | none | edge.pd7.a2 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| PD9 | A2 | hard | specific-output | ACCEPTED | none | edge.pd9.a2 | PD9 已接受的合同、实现或验收产物 | PD9 节点状态与候选内容校验值 |
| S2 | A2 | hard | specific-output | ACCEPTED | none | edge.s2.a2 | S2 已接受的合同、实现或验收产物 | S2 节点状态与候选内容校验值 |
| S3 | A2 | hard | specific-output | ACCEPTED | none | edge.s3.a2 | S3 已接受的合同、实现或验收产物 | S3 节点状态与候选内容校验值 |
| T5 | A2 | hard | specific-output | ACCEPTED | none | edge.t5.a2 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | H1 | hard | specific-output | ACCEPTED | none | edge.f.h1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | H2 | hard | specific-output | ACCEPTED | none | edge.f.h2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD4 | H2 | hard | specific-output | ACCEPTED | none | edge.pd4.h2 | PD4 已接受的合同、实现或验收产物 | PD4 节点状态与候选内容校验值 |
| PD5 | H2 | hard | specific-output | ACCEPTED | none | edge.pd5.h2 | PD5 已接受的合同、实现或验收产物 | PD5 节点状态与候选内容校验值 |
| PD7 | H2 | hard | specific-output | ACCEPTED | none | edge.pd7.h2 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| S3 | H2 | hard | specific-output | ACCEPTED | none | edge.s3.h2 | S3 已接受的合同、实现或验收产物 | S3 节点状态与候选内容校验值 |
| S5 | H2 | hard | specific-output | ACCEPTED | none | edge.s5.h2 | S5 已接受的合同、实现或验收产物 | S5 节点状态与候选内容校验值 |
| F | H3 | hard | specific-output | ACCEPTED | none | edge.f.h3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| D2 | H3 | hard | specific-output | ACCEPTED | none | edge.d2.h3 | D2 已接受的合同、实现或验收产物 | D2 节点状态与候选内容校验值 |
| F | H4 | hard | specific-output | ACCEPTED | none | edge.f.h4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| F | I1 | hard | specific-output | ACCEPTED | none | edge.f.i1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| D1 | I1 | hard | specific-output | ACCEPTED | none | edge.d1.i1 | D1 已接受的合同、实现或验收产物 | D1 节点状态与候选内容校验值 |
| T5 | I1 | hard | specific-output | ACCEPTED | none | edge.t5.i1 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | I2 | hard | specific-output | ACCEPTED | none | edge.f.i2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD1 | I2 | hard | specific-output | ACCEPTED | none | edge.pd1.i2 | PD1 已接受的合同、实现或验收产物 | PD1 节点状态与候选内容校验值 |
| F | I3 | hard | specific-output | ACCEPTED | none | edge.f.i3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD1 | I3 | hard | specific-output | ACCEPTED | none | edge.pd1.i3 | PD1 已接受的合同、实现或验收产物 | PD1 节点状态与候选内容校验值 |
| T2 | I3 | hard | specific-output | ACCEPTED | none | edge.t2.i3 | T2 已接受的合同、实现或验收产物 | T2 节点状态与候选内容校验值 |
| F | I4 | hard | specific-output | ACCEPTED | none | edge.f.i4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD3 | I4 | hard | specific-output | ACCEPTED | none | edge.pd3.i4 | PD3 已接受的合同、实现或验收产物 | PD3 节点状态与候选内容校验值 |
| T3 | I4 | hard | specific-output | ACCEPTED | none | edge.t3.i4 | T3 已接受的合同、实现或验收产物 | T3 节点状态与候选内容校验值 |
| T5 | I4 | hard | specific-output | ACCEPTED | none | edge.t5.i4 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | I5 | hard | specific-output | ACCEPTED | none | edge.f.i5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD3 | I5 | hard | specific-output | ACCEPTED | none | edge.pd3.i5 | PD3 已接受的合同、实现或验收产物 | PD3 节点状态与候选内容校验值 |
| I4 | I5 | hard | specific-output | ACCEPTED | none | edge.i4.i5 | I4 已接受的合同、实现或验收产物 | I4 节点状态与候选内容校验值 |
| T5 | I5 | hard | specific-output | ACCEPTED | none | edge.t5.i5 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | L1 | hard | specific-output | ACCEPTED | none | edge.f.l1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| D2 | L1 | hard | specific-output | ACCEPTED | none | edge.d2.l1 | D2 已接受的合同、实现或验收产物 | D2 节点状态与候选内容校验值 |
| F | L2 | hard | specific-output | ACCEPTED | none | edge.f.l2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| D2 | L2 | hard | specific-output | ACCEPTED | none | edge.d2.l2 | D2 已接受的合同、实现或验收产物 | D2 节点状态与候选内容校验值 |
| F | L3 | hard | specific-output | ACCEPTED | none | edge.f.l3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD6 | L3 | hard | specific-output | ACCEPTED | none | edge.pd6.l3 | PD6 已接受的合同、实现或验收产物 | PD6 节点状态与候选内容校验值 |
| F | L4 | hard | specific-output | ACCEPTED | none | edge.f.l4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD6 | L4 | hard | specific-output | ACCEPTED | none | edge.pd6.l4 | PD6 已接受的合同、实现或验收产物 | PD6 节点状态与候选内容校验值 |
| F | L5 | hard | specific-output | ACCEPTED | none | edge.f.l5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| D2 | L5 | hard | specific-output | ACCEPTED | none | edge.d2.l5 | D2 已接受的合同、实现或验收产物 | D2 节点状态与候选内容校验值 |
| T5 | L5 | hard | specific-output | ACCEPTED | none | edge.t5.l5 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | P1 | hard | specific-output | ACCEPTED | none | edge.f.p1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | P1 | hard | specific-output | ACCEPTED | none | edge.pd8.p1 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | P2 | hard | specific-output | ACCEPTED | none | edge.f.p2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | P2 | hard | specific-output | ACCEPTED | none | edge.pd8.p2 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | P3 | hard | specific-output | ACCEPTED | none | edge.f.p3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | P3 | hard | specific-output | ACCEPTED | none | edge.pd8.p3 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| P1 | P3 | hard | specific-output | ACCEPTED | none | edge.p1.p3 | P1 已接受的合同、实现或验收产物 | P1 节点状态与候选内容校验值 |
| P2 | P3 | hard | specific-output | ACCEPTED | none | edge.p2.p3 | P2 已接受的合同、实现或验收产物 | P2 节点状态与候选内容校验值 |
| T5 | P3 | hard | specific-output | ACCEPTED | none | edge.t5.p3 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | P4 | hard | specific-output | ACCEPTED | none | edge.f.p4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | P4 | hard | specific-output | ACCEPTED | none | edge.pd8.p4 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | P5 | hard | specific-output | ACCEPTED | none | edge.f.p5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD5 | P5 | hard | specific-output | ACCEPTED | none | edge.pd5.p5 | PD5 已接受的合同、实现或验收产物 | PD5 节点状态与候选内容校验值 |
| PD8 | P5 | hard | specific-output | ACCEPTED | none | edge.pd8.p5 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| PD9 | P5 | hard | specific-output | ACCEPTED | none | edge.pd9.p5 | PD9 已接受的合同、实现或验收产物 | PD9 节点状态与候选内容校验值 |
| P2 | P5 | hard | specific-output | ACCEPTED | none | edge.p2.p5 | P2 已接受的合同、实现或验收产物 | P2 节点状态与候选内容校验值 |
| T5 | P5 | hard | specific-output | ACCEPTED | none | edge.t5.p5 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | P6 | hard | specific-output | ACCEPTED | none | edge.f.p6 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD9 | P6 | hard | specific-output | ACCEPTED | none | edge.pd9.p6 | PD9 已接受的合同、实现或验收产物 | PD9 节点状态与候选内容校验值 |
| T6 | P6 | hard | specific-output | ACCEPTED | none | edge.t6.p6 | T6 已接受的合同、实现或验收产物 | T6 节点状态与候选内容校验值 |
| F | S1 | hard | specific-output | ACCEPTED | none | edge.f.s1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| T4 | S1 | hard | specific-output | ACCEPTED | none | edge.t4.s1 | T4 已接受的合同、实现或验收产物 | T4 节点状态与候选内容校验值 |
| T5 | S1 | hard | specific-output | ACCEPTED | none | edge.t5.s1 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | S2 | hard | specific-output | ACCEPTED | none | edge.f.s2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD6 | S2 | hard | specific-output | ACCEPTED | none | edge.pd6.s2 | PD6 已接受的合同、实现或验收产物 | PD6 节点状态与候选内容校验值 |
| T5 | S2 | hard | specific-output | ACCEPTED | none | edge.t5.s2 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | S3 | hard | specific-output | ACCEPTED | none | edge.f.s3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| T3 | S3 | hard | specific-output | ACCEPTED | none | edge.t3.s3 | T3 已接受的合同、实现或验收产物 | T3 节点状态与候选内容校验值 |
| F | S4 | hard | specific-output | ACCEPTED | none | edge.f.s4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD7 | S4 | hard | specific-output | ACCEPTED | none | edge.pd7.s4 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| F | S5 | hard | specific-output | ACCEPTED | none | edge.f.s5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD4 | S5 | hard | specific-output | ACCEPTED | none | edge.pd4.s5 | PD4 已接受的合同、实现或验收产物 | PD4 节点状态与候选内容校验值 |
| T5 | S5 | hard | specific-output | ACCEPTED | none | edge.t5.s5 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| F | C1 | hard | specific-output | ACCEPTED | none | edge.f.c1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD7 | C1 | hard | specific-output | ACCEPTED | none | edge.pd7.c1 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| F | C2 | hard | specific-output | ACCEPTED | none | edge.f.c2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD7 | C2 | hard | specific-output | ACCEPTED | none | edge.pd7.c2 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| C1 | C2 | hard | specific-output | ACCEPTED | none | edge.c1.c2 | C1 已接受的合同、实现或验收产物 | C1 节点状态与候选内容校验值 |
| F | C3 | hard | specific-output | ACCEPTED | none | edge.f.c3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD7 | C3 | hard | specific-output | ACCEPTED | none | edge.pd7.c3 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| C2 | C3 | hard | specific-output | ACCEPTED | none | edge.c2.c3 | C2 已接受的合同、实现或验收产物 | C2 节点状态与候选内容校验值 |
| F | T1 | hard | specific-output | ACCEPTED | none | edge.f.t1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T1 | hard | specific-output | ACCEPTED | none | edge.pd.t1 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| F | T2 | hard | specific-output | ACCEPTED | none | edge.f.t2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T2 | hard | specific-output | ACCEPTED | none | edge.pd.t2 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| PD2 | T2 | hard | specific-output | ACCEPTED | none | edge.pd2.t2 | PD2 已接受的合同、实现或验收产物 | PD2 节点状态与候选内容校验值 |
| F | T3 | hard | specific-output | ACCEPTED | none | edge.f.t3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T3 | hard | specific-output | ACCEPTED | none | edge.pd.t3 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| F | T4 | hard | specific-output | ACCEPTED | none | edge.f.t4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T4 | hard | specific-output | ACCEPTED | none | edge.pd.t4 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| F | T5 | hard | specific-output | ACCEPTED | none | edge.f.t5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T5 | hard | specific-output | ACCEPTED | none | edge.pd.t5 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| F | T6 | hard | specific-output | ACCEPTED | none | edge.f.t6 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD | T6 | hard | specific-output | ACCEPTED | none | edge.pd.t6 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| PD9 | T6 | hard | specific-output | ACCEPTED | none | edge.pd9.t6 | PD9 已接受的合同、实现或验收产物 | PD9 节点状态与候选内容校验值 |
| F | K1 | hard | specific-output | ACCEPTED | none | edge.f.k1 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K1 | hard | specific-output | ACCEPTED | none | edge.pd8.k1 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | K2 | hard | specific-output | ACCEPTED | none | edge.f.k2 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K2 | hard | specific-output | ACCEPTED | none | edge.pd8.k2 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | K3 | hard | specific-output | ACCEPTED | none | edge.f.k3 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K3 | hard | specific-output | ACCEPTED | none | edge.pd8.k3 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | K4 | hard | specific-output | ACCEPTED | none | edge.f.k4 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K4 | hard | specific-output | ACCEPTED | none | edge.pd8.k4 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | K5 | hard | specific-output | ACCEPTED | none | edge.f.k5 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K5 | hard | specific-output | ACCEPTED | none | edge.pd8.k5 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| F | K6 | hard | specific-output | ACCEPTED | none | edge.f.k6 | F 已接受的合同、实现或验收产物 | F 节点状态与候选内容校验值 |
| PD8 | K6 | hard | specific-output | ACCEPTED | none | edge.pd8.k6 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| PD | Q1 | hard | specific-output | ACCEPTED | none | edge.pd.q1 | PD 已接受的合同、实现或验收产物 | PD 节点状态与候选内容校验值 |
| PD1 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd1.q1 | PD1 已接受的合同、实现或验收产物 | PD1 节点状态与候选内容校验值 |
| PD2 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd2.q1 | PD2 已接受的合同、实现或验收产物 | PD2 节点状态与候选内容校验值 |
| PD3 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd3.q1 | PD3 已接受的合同、实现或验收产物 | PD3 节点状态与候选内容校验值 |
| PD4 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd4.q1 | PD4 已接受的合同、实现或验收产物 | PD4 节点状态与候选内容校验值 |
| PD5 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd5.q1 | PD5 已接受的合同、实现或验收产物 | PD5 节点状态与候选内容校验值 |
| PD6 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd6.q1 | PD6 已接受的合同、实现或验收产物 | PD6 节点状态与候选内容校验值 |
| PD7 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd7.q1 | PD7 已接受的合同、实现或验收产物 | PD7 节点状态与候选内容校验值 |
| PD8 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd8.q1 | PD8 已接受的合同、实现或验收产物 | PD8 节点状态与候选内容校验值 |
| PD9 | Q1 | hard | specific-output | ACCEPTED | none | edge.pd9.q1 | PD9 已接受的合同、实现或验收产物 | PD9 节点状态与候选内容校验值 |
| TRD | Q1 | hard | specific-output | ACCEPTED | none | edge.trd.q1 | TRD 已接受的合同、实现或验收产物 | TRD 节点状态与候选内容校验值 |
| D1 | Q1 | hard | specific-output | ACCEPTED | none | edge.d1.q1 | D1 已接受的合同、实现或验收产物 | D1 节点状态与候选内容校验值 |
| D2 | Q1 | hard | specific-output | ACCEPTED | none | edge.d2.q1 | D2 已接受的合同、实现或验收产物 | D2 节点状态与候选内容校验值 |
| D3 | Q1 | hard | specific-output | ACCEPTED | none | edge.d3.q1 | D3 已接受的合同、实现或验收产物 | D3 节点状态与候选内容校验值 |
| T1 | Q1 | hard | specific-output | ACCEPTED | none | edge.t1.q1 | T1 已接受的合同、实现或验收产物 | T1 节点状态与候选内容校验值 |
| T3 | Q1 | hard | specific-output | ACCEPTED | none | edge.t3.q1 | T3 已接受的合同、实现或验收产物 | T3 节点状态与候选内容校验值 |
| T5 | Q1 | hard | specific-output | ACCEPTED | none | edge.t5.q1 | T5 已接受的合同、实现或验收产物 | T5 节点状态与候选内容校验值 |
| I1 | Q2 | hard | specific-output | ACCEPTED | none | edge.i1.q2 | I1 已接受的合同、实现或验收产物 | I1 节点状态与候选内容校验值 |
| I2 | Q2 | hard | specific-output | ACCEPTED | none | edge.i2.q2 | I2 已接受的合同、实现或验收产物 | I2 节点状态与候选内容校验值 |
| I3 | Q2 | hard | specific-output | ACCEPTED | none | edge.i3.q2 | I3 已接受的合同、实现或验收产物 | I3 节点状态与候选内容校验值 |
| I4 | Q2 | hard | specific-output | ACCEPTED | none | edge.i4.q2 | I4 已接受的合同、实现或验收产物 | I4 节点状态与候选内容校验值 |
| I5 | Q2 | hard | specific-output | ACCEPTED | none | edge.i5.q2 | I5 已接受的合同、实现或验收产物 | I5 节点状态与候选内容校验值 |
| L1 | Q3 | hard | specific-output | ACCEPTED | none | edge.l1.q3 | L1 已接受的合同、实现或验收产物 | L1 节点状态与候选内容校验值 |
| L2 | Q3 | hard | specific-output | ACCEPTED | none | edge.l2.q3 | L2 已接受的合同、实现或验收产物 | L2 节点状态与候选内容校验值 |
| L3 | Q3 | hard | specific-output | ACCEPTED | none | edge.l3.q3 | L3 已接受的合同、实现或验收产物 | L3 节点状态与候选内容校验值 |
| L4 | Q3 | hard | specific-output | ACCEPTED | none | edge.l4.q3 | L4 已接受的合同、实现或验收产物 | L4 节点状态与候选内容校验值 |
| L5 | Q3 | hard | specific-output | ACCEPTED | none | edge.l5.q3 | L5 已接受的合同、实现或验收产物 | L5 节点状态与候选内容校验值 |
| T2 | Q3 | hard | specific-output | ACCEPTED | none | edge.t2.q3 | T2 已接受的合同、实现或验收产物 | T2 节点状态与候选内容校验值 |
| P1 | Q4 | hard | specific-output | ACCEPTED | none | edge.p1.q4 | P1 已接受的合同、实现或验收产物 | P1 节点状态与候选内容校验值 |
| P2 | Q4 | hard | specific-output | ACCEPTED | none | edge.p2.q4 | P2 已接受的合同、实现或验收产物 | P2 节点状态与候选内容校验值 |
| P3 | Q4 | hard | specific-output | ACCEPTED | none | edge.p3.q4 | P3 已接受的合同、实现或验收产物 | P3 节点状态与候选内容校验值 |
| P4 | Q4 | hard | specific-output | ACCEPTED | none | edge.p4.q4 | P4 已接受的合同、实现或验收产物 | P4 节点状态与候选内容校验值 |
| P5 | Q4 | hard | specific-output | ACCEPTED | none | edge.p5.q4 | P5 已接受的合同、实现或验收产物 | P5 节点状态与候选内容校验值 |
| P6 | Q4 | hard | specific-output | ACCEPTED | none | edge.p6.q4 | P6 已接受的合同、实现或验收产物 | P6 节点状态与候选内容校验值 |
| T6 | Q4 | hard | specific-output | ACCEPTED | none | edge.t6.q4 | T6 已接受的合同、实现或验收产物 | T6 节点状态与候选内容校验值 |
| S1 | Q5 | hard | specific-output | ACCEPTED | none | edge.s1.q5 | S1 已接受的合同、实现或验收产物 | S1 节点状态与候选内容校验值 |
| S2 | Q5 | hard | specific-output | ACCEPTED | none | edge.s2.q5 | S2 已接受的合同、实现或验收产物 | S2 节点状态与候选内容校验值 |
| S3 | Q5 | hard | specific-output | ACCEPTED | none | edge.s3.q5 | S3 已接受的合同、实现或验收产物 | S3 节点状态与候选内容校验值 |
| S4 | Q5 | hard | specific-output | ACCEPTED | none | edge.s4.q5 | S4 已接受的合同、实现或验收产物 | S4 节点状态与候选内容校验值 |
| S5 | Q5 | hard | specific-output | ACCEPTED | none | edge.s5.q5 | S5 已接受的合同、实现或验收产物 | S5 节点状态与候选内容校验值 |
| C1 | Q5 | hard | specific-output | ACCEPTED | none | edge.c1.q5 | C1 已接受的合同、实现或验收产物 | C1 节点状态与候选内容校验值 |
| C2 | Q5 | hard | specific-output | ACCEPTED | none | edge.c2.q5 | C2 已接受的合同、实现或验收产物 | C2 节点状态与候选内容校验值 |
| C3 | Q5 | hard | specific-output | ACCEPTED | none | edge.c3.q5 | C3 已接受的合同、实现或验收产物 | C3 节点状态与候选内容校验值 |
| T4 | Q5 | hard | specific-output | ACCEPTED | none | edge.t4.q5 | T4 已接受的合同、实现或验收产物 | T4 节点状态与候选内容校验值 |
| A1 | Q6 | hard | specific-output | ACCEPTED | none | edge.a1.q6 | A1 已接受的合同、实现或验收产物 | A1 节点状态与候选内容校验值 |
| A2 | Q6 | hard | specific-output | ACCEPTED | none | edge.a2.q6 | A2 已接受的合同、实现或验收产物 | A2 节点状态与候选内容校验值 |
| H1 | Q6 | hard | specific-output | ACCEPTED | none | edge.h1.q6 | H1 已接受的合同、实现或验收产物 | H1 节点状态与候选内容校验值 |
| H2 | Q6 | hard | specific-output | ACCEPTED | none | edge.h2.q6 | H2 已接受的合同、实现或验收产物 | H2 节点状态与候选内容校验值 |
| H3 | Q6 | hard | specific-output | ACCEPTED | none | edge.h3.q6 | H3 已接受的合同、实现或验收产物 | H3 节点状态与候选内容校验值 |
| H4 | Q6 | hard | specific-output | ACCEPTED | none | edge.h4.q6 | H4 已接受的合同、实现或验收产物 | H4 节点状态与候选内容校验值 |
| K1 | Q7 | hard | specific-output | ACCEPTED | none | edge.k1.q7 | K1 已接受的合同、实现或验收产物 | K1 节点状态与候选内容校验值 |
| K2 | Q7 | hard | specific-output | ACCEPTED | none | edge.k2.q7 | K2 已接受的合同、实现或验收产物 | K2 节点状态与候选内容校验值 |
| K3 | Q7 | hard | specific-output | ACCEPTED | none | edge.k3.q7 | K3 已接受的合同、实现或验收产物 | K3 节点状态与候选内容校验值 |
| K4 | Q7 | hard | specific-output | ACCEPTED | none | edge.k4.q7 | K4 已接受的合同、实现或验收产物 | K4 节点状态与候选内容校验值 |
| K5 | Q7 | hard | specific-output | ACCEPTED | none | edge.k5.q7 | K5 已接受的合同、实现或验收产物 | K5 节点状态与候选内容校验值 |
| K6 | Q7 | hard | specific-output | ACCEPTED | none | edge.k6.q7 | K6 已接受的合同、实现或验收产物 | K6 节点状态与候选内容校验值 |
| Q1 | Z1 | hard | specific-output | ACCEPTED | none | edge.q1.z1 | Q1 已接受的合同、实现或验收产物 | Q1 节点状态与候选内容校验值 |
| Q2 | Z1 | hard | specific-output | ACCEPTED | none | edge.q2.z1 | Q2 已接受的合同、实现或验收产物 | Q2 节点状态与候选内容校验值 |
| Q3 | Z1 | hard | specific-output | ACCEPTED | none | edge.q3.z1 | Q3 已接受的合同、实现或验收产物 | Q3 节点状态与候选内容校验值 |
| Q4 | Z1 | hard | specific-output | ACCEPTED | none | edge.q4.z1 | Q4 已接受的合同、实现或验收产物 | Q4 节点状态与候选内容校验值 |
| Q5 | Z1 | hard | specific-output | ACCEPTED | none | edge.q5.z1 | Q5 已接受的合同、实现或验收产物 | Q5 节点状态与候选内容校验值 |
| Q6 | Z1 | hard | specific-output | ACCEPTED | none | edge.q6.z1 | Q6 已接受的合同、实现或验收产物 | Q6 节点状态与候选内容校验值 |
| Q7 | Z1 | hard | specific-output | ACCEPTED | none | edge.q7.z1 | Q7 已接受的合同、实现或验收产物 | Q7 节点状态与候选内容校验值 |
| Z1 | Q8 | hard | specific-output | ACCEPTED | none | edge.z1.q8 | Z1 已接受的合同、实现或验收产物 | Z1 节点状态与候选内容校验值 |
| Q8 | RZ | hard | specific-output | ACCEPTED | none | edge.q8.rz | Q8 已接受的合同、实现或验收产物 | Q8 节点状态与候选内容校验值 |

## 当前就绪前沿

| Frontier | Task ID | Eligibility | Unsatisfied hard dependencies | Active assumptions | Resource decision |
| --- | --- | --- | --- | --- | --- |
| F0 | D3 | FORMAL | none | none | conflict-free |
| F0 | T1 | FORMAL | none | none | conflict-free |
| F0 | T3 | FORMAL | none | none | conflict-free |
| F0 | T5 | FORMAL | none | none | conflict-free |
| F0 | I2 | FORMAL | none | none | conflict-free |
| F0 | L3 | FORMAL | none | none | conflict-free |
| F0 | L4 | FORMAL | none | none | conflict-free |
| F0 | T2 | FORMAL | none | none | conflict-free |
| F0 | P1 | FORMAL | none | none | conflict-free |
| F0 | P2 | FORMAL | none | none | conflict-free |
| F0 | P4 | FORMAL | none | none | conflict-free |
| F0 | T6 | FORMAL | none | none | conflict-free |
| F0 | S4 | FORMAL | none | none | conflict-free |
| F0 | C1 | FORMAL | none | none | conflict-free |
| F0 | T4 | FORMAL | none | none | conflict-free |
| F0 | H1 | FORMAL | none | none | conflict-free |
| F0 | H4 | FORMAL | none | none | conflict-free |
| F0 | K1 | FORMAL | none | none | conflict-free |
| F0 | K2 | FORMAL | none | none | conflict-free |
| F0 | K3 | FORMAL | none | none | conflict-free |
| F0 | K4 | FORMAL | none | none | conflict-free |
| F0 | K5 | FORMAL | none | none | conflict-free |
| F0 | K6 | FORMAL | none | none | conflict-free |

## 叶交付物清单

| Deliverable ID | Parallel batch | Deliverable | Authority write region | Dependencies | Isolation decision | Conflict class | Owning node | Grouping reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DL-F | R1 | 冻结 HTML、原型、源码和测试的可回读事实基线 | .ssot/nodes/F.json | none | independent | none | F | n/a |
| DL-PD | R1 | 完整覆盖 HTML 的 45 项要求，不以降级或删除条目换取完成。 | .ssot/nodes/PD.json | F | independent | none | PD | n/a |
| DL-PD1 | R1 | 自动分事件、分批完整实现，先预览确认再执行迁移。 | .ssot/nodes/PD1.json | F | independent | none | PD1 | n/a |
| DL-PD2 | R1 | 新增结构化素材索引，Markdown 继续供人阅读。 | .ssot/nodes/PD2.json | F | independent | none | PD2 | n/a |
| DL-PD3 | R1 | 只生成删除建议；用户选择并二次确认后进入当前系统回收站，禁止永久删除。 | .ssot/nodes/PD3.json | F | independent | none | PD3 | n/a |
| DL-PD4 | R1 | 创意模型由用户配置，支持 Codex/OpenAI、Claude/Anthropic、DeepSeek 和兼容接口。 | .ssot/nodes/PD4.json | F | independent | none | PD4 | n/a |
| DL-PD5 | R1 | ChatCut 只通过 Desktop 本地 MCP 接入，实时探测且主动连接后才显示。 | .ssot/nodes/PD5.json | F | independent | none | PD5 | n/a |
| DL-PD6 | R1 | 生命周期和物理位置同时配置，每个位置独立保存清单、校验值与回读状态。 | .ssot/nodes/PD6.json | F | independent | none | PD6 | n/a |
| DL-PD7 | R1 | 优先复用上游中台身份；配对可选，未登录或平台不支持时本地功能保持完整。 | .ssot/nodes/PD7.json | F | independent | none | PD7 | n/a |
| DL-PD8 | R1 | 结构化 06_edit_decision_list.json 是机器执行唯一剪辑方案权威。 | .ssot/nodes/PD8.json | F | independent | none | PD8 | n/a |
| DL-PD9 | R1 | 剪映脚本仅作历史材料，自动化不得修改生产剪映草稿。 | .ssot/nodes/PD9.json | F | independent | none | PD9 | n/a |
| DL-TRD | R1 | 决定转写提供方、默认策略、音频发送边界、费用和失败占位行为 | .ssot/nodes/TRD.json | F | independent | none | TRD | n/a |
| DL-D1 | R1 | 从媒体清单生成可解释、可确认且不可拆分实况照片组的事件批次计划；未确认或输入漂移时禁止迁移。 | 99_System_OpenClaw/ | F,PD,PD1,T1 | independent | none | D1 | n/a |
| DL-D2 | R1 | 以稳定素材身份原子维护结构化索引，支持分类、标签、用途、计数与详情查询，同时保留 Markdown 卡片。 | 99_System_OpenClaw/ | F,PD,PD2,T2 | independent | none | D2 | n/a |
| DL-D3 | R1 | 按已接受的 DashScope 默认、本机 FunASR 失败兜底与音频发送前明示策略统一所有入口，并以音频夹具验证。 | 99_System_OpenClaw/ | F,PD,TRD | independent | none | D3 | n/a |
| DL-T1 | R1 | 给 35_promote_inbox_batch_to_project.py 补测试：接 UI 之前先补测试。这条建议优先级高于任何界面工作。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD | independent | none | T1 | n/a |
| DL-T3 | R1 | 给 43_content_os_doctor.py 和 01_scan_media_manifest.py 补测试：补基础用例。 01 至少要覆盖损坏文件、零时长、缺 EXIF 这几种边界。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD | independent | none | T3 | n/a |
| DL-T5 | R1 | 所有新增写接口沿用 loopback、同源、CSRF 和明确 revision 域的乐观并发控制，跨端口 Origin 必须拒绝。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD | independent | none | T5 | n/a |
| DL-Q1 | R1 | 汇编 R1 的独立候选、证据和接受结果 | .ssot/nodes/Q1.json | PD,PD1,PD2,PD3,PD4,PD5,PD6,PD7,PD8,PD9,TRD,D1,D2,D3,T1,T3,T5 | independent | none | Q1 | n/a |
| DL-I1 | R2 | 拖入素材 → 自动成批：已拍板：做。按第 00 节 d1 的分批器方案实现，整理台保持原型的完整交互（自动成批 → 你确认落点）。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,D1,T5 | independent | none | I1 | n/a |
| DL-I2 | R2 | 批次卡上的来源构成（iPhone ×6 · 屏幕录制 ×2 · 相机 ×1）：读 manifest 分组计数即可，不用新后端。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD1 | independent | none | I2 | n/a |
| DL-I3 | R2 | 连拍识别（「发现 4 组连拍」）与实况配对：把 12 的输出定契约（JSON + schema）、补测试，再接进批次分析流程。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD1,T2 | independent | none | I3 | n/a |
| DL-I4 | R2 | 三分落点：进项目 / 归档保留 / 推荐删除：新写。原型已经把规则收得很紧了——推荐删除只按机器可验证的四条理由（时长过短、文件损坏、哈希完全重复、相机低清代理），这四条全都能从 manifest 直接算出来，实现成本不高。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD3,T3,T5 | independent | none | I4 | n/a |
| DL-I5 | R2 | 用户勾选建议并二次确认后才移入当前操作系统回收站；回读失败必须阻断，界面不得承诺固定保留天数。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD3,I4,T5 | independent | none | I5 | n/a |
| DL-Q2 | R2 | 汇编 R2 的独立候选、证据和接受结果 | .ssot/nodes/Q2.json | I1,I2,I3,I4,I5 | independent | none | Q2 | n/a |
| DL-L1 | R3 | 复用资产卡片列表 + 分类树：索引层已拍板（第 00 节 d2）。落地后这屏基本是纯前端工作。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,D2 | independent | none | L1 | n/a |
| DL-L2 | R3 | 按标签筛选：同上（索引层已拍板）。原型上这排标签目前是静态的，索引接口就位后一并接活。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,D2 | independent | none | L2 | n/a |
| DL-L3 | R3 | 同时展示生命周期和每个物理位置的真实回读状态，逻辑登记不得冒充副本已存在。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD6 | independent | none | L3 | n/a |
| DL-L4 | R3 | 归档索引卡（检索关键词、精选副本入口、恢复方式）：包 HTTP 接口。这是素材库里唯一后端完备的部分。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD6 | independent | none | L4 | n/a |
| DL-L5 | R3 | 详情栏主按钮「选择项目并加入」要落到真实动作：要么补 16 号能力，要么这个按钮先降级为「复制卡片路径」这类真能做到的动作。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/desktop/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,D2,T5 | independent | none | L5 | n/a |
| DL-T2 | R3 | 给素材库三件套补测试（12 / 14 / 15）：和第 00 节的索引层一起做，定契约的同时补测试。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD,PD2 | independent | none | T2 | n/a |
| DL-Q3 | R3 | 汇编 R3 的独立候选、证据和接受结果 | .ssot/nodes/Q3.json | L1,L2,L3,L4,L5,T2 | independent | none | Q3 | n/a |
| DL-P1 | R4 | 剪辑决策条目列表（时间码 / 台词 / 角色标签）：纯前端。EDL 已经通过 GET /api/projects/:id 返回了。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | P1 | n/a |
| DL-P2 | R4 | 双轨时间线（主画面 + 叠加层）：纯前端渲染。这是原型里少数「后端先行、界面还没跟上」的部分。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | P2 | n/a |
| DL-P3 | R4 | 结构化时间线为主视图，同时保留文本说明与受约束的选区修改，不形成第二份机器执行权威。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD8,P1,P2,T5 | independent | none | P3 | n/a |
| DL-P4 | R4 | 「待补素材」缺口清单：纯前端。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | P4 | n/a |
| DL-P5 | R4 | 内建只显示 handoff_pack 与 otio_kdenlive；ChatCut 仅在本地 MCP 实时探测和主动连接后成为可选去向。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD5,PD8,PD9,P2,T5 | independent | none | P5 | n/a |
| DL-P6 | R4 | 统一表述为剪映生产路线已停止维护，删除没有证据的“草稿加密”理由。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/edit_backends/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD9,T6 | independent | none | P6 | n/a |
| DL-T6 | R4 | 七个剪映脚本要么物理归档，要么逐项声明历史且不维护，并使文档、能力清单和持续集成保持一致。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD,PD9 | independent | none | T6 | n/a |
| DL-Q4 | R4 | 汇编 R4 的独立候选、证据和接受结果 | .ssot/nodes/Q4.json | P1,P2,P3,P4,P5,P6,T6 | independent | none | Q4 | n/a |
| DL-S1 | R5 | 分析预算四个数字：补一个读写配置的接口。注意 analysis_tiering 的输出 没有 JSON Schema，只有 dataclass 和 POLICY_VERSION。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,T4,T5 | independent | none | S1 | n/a |
| DL-S2 | R5 | 存放位置（素材根目录 / 笔记库）：现有接口是项目级的，设置页要的是全局级，得加一个。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD6,T5 | independent | none | S2 | n/a |
| DL-S3 | R5 | 诊断页六项检查：包接口。前端别把「6 项」写死。另外这个脚本 零测试覆盖，接之前建议先补。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,T3 | independent | none | S3 | n/a |
| DL-S4 | R5 | Windows 与 Linux 将上游配对显示为“不支持”而不是“配置失败”，并明确本地核心能力仍可用。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD7 | independent | none | S4 | n/a |
| DL-S5 | R5 | 持久化用户选择的提供方、模型、端点、思考强度和密钥引用，并确保真实执行链消费该配置。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD4,T5 | independent | none | S5 | n/a |
| DL-C1 | R5 | 任务列表上的 media.xxx.v1 标识符是对的：保持现状。上一轮审计已经把它们从主标签降级为次要说明，这个处理是对的。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD7 | independent | none | C1 | n/a |
| DL-C2 | R5 | 任务状态机（执行中 / 已完成 / 已阻塞）：前端目前只画了 3 态，补齐映射即可。注意 expired 和 cancelled 也要有对应显示。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD7,C1 | independent | none | C2 | n/a |
| DL-C3 | R5 | 冻结基线要写进界面还是文档：上一轮审计已经把裸 hash 从诊断页移走了，这是对的。但版本不匹配时得有个地方告诉用户——建议放进诊断页的「复制报告」，不放主界面。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/tests/ | F,PD7,C2 | independent | none | C3 | n/a |
| DL-T4 | R5 | 给 analysis_tiering 的输出定 JSON Schema：补 schemas/analysis_tiering.schema.json，纳入现有的契约校验流程。 | 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/; 99_System_OpenClaw/schemas/; 99_System_OpenClaw/docs/ | F,PD | independent | none | T4 | n/a |
| DL-Q5 | R5 | 汇编 R5 的独立候选、证据和接受结果 | .ssot/nodes/Q5.json | S1,S2,S3,S4,S5,C1,C2,C3,T4 | independent | none | Q5 | n/a |
| DL-A1 | R6 | 使用上游中台身份完成邮箱、Apple 或微信登录；配对始终可选，未登录、撤销或平台不支持时本地能力不退化。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F,PD7,T5 | independent | none | A1 | n/a |
| DL-A2 | R6 | 向导可重入地完成位置、运行环境、编辑器、账号与设备四步，并能从失败处恢复。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F,PD6,PD7,PD9,S2,S3,T5 | independent | none | A2 | n/a |
| DL-H1 | R6 | 最近项目列表 + 六段流水线进度：纯前端改造，接口不用动。原型的六段（素材归档/取证分析/脚本分镜/剪辑决策/时间线/人工精剪）需要和现有五段（Brief/脚本/分镜/EDL/交付）对齐命名。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F | independent | none | H1 | n/a |
| DL-H2 | R6 | 聚合数据中台、Codex、ChatCut Desktop 本地 MCP 与本机引擎的实时状态；单项失败不拖垮整体。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F,PD4,PD5,PD7,S3,S5 | independent | none | H2 | n/a |
| DL-H3 | R6 | 素材库统计（视频 412 / 照片 1,240 / 音频 36 / 占用 412 GB）：索引层已拍板要做（第 00 节 d2）。索引层落地后这个统计是顺手的事。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F,D2 | independent | none | H3 | n/a |
| DL-H4 | R6 | 本周统计（完成任务 23 / 发布内容 4）：加一个按时间窗聚合的只读接口。数据源都在，只是没人聚合。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/scripts/; 99_System_OpenClaw/tests/ | F | independent | none | H4 | n/a |
| DL-Q6 | R6 | 汇编 R6 的独立候选、证据和接受结果 | .ssot/nodes/Q6.json | A1,A2,H1,H2,H3,H4 | independent | none | Q6 | n/a |
| DL-K1 | R7 | 区块锁定 + AI 只改选中区块：新界面必须保留这个语义。原型里完全没有「锁定」和「选中范围」的表达。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K1 | n/a |
| DL-K2 | R7 | 版本 diff 与非破坏性回滚：原型里没有版本概念。至少要在项目屏留一个入口。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K2 | n/a |
| DL-K3 | R7 | 下游 stale 标记（Brief 改了，脚本/分镜/EDL 自动标记需更新）：原型的六段流水线进度条是个好载体，可以顺势把 stale 状态表达进去。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K3 | n/a |
| DL-K4 | R7 | 研究与参考（reference ≠ 自有素材）：这是一条重要的边界。原型完全没有，接进去时别把参考内容混进素材库。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K4 | n/a |
| DL-K5 | R7 | 发布与复盘（指标 + 复盘结论 + 下次约束）：原型里完全没有。这块丢了，产品就退化成一次性工具。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K5 | n/a |
| DL-K6 | R7 | Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/tests/ | F,PD8 | independent | none | K6 | n/a |
| DL-Q7 | R7 | 汇编 R7 的独立候选、证据和接受结果 | .ssot/nodes/Q7.json | K1,K2,K3,K4,K5,K6 | independent | none | Q7 | n/a |
| DL-Z1 | R8 | 把九个表面接入同一入口、共享状态和完整纵向动作链，并建立项目内视觉工作台 | 99_System_OpenClaw/desktop/; 99_System_OpenClaw/visual-workbench.html; 99_System_OpenClaw/visual-workbench.json; 99_System_OpenClaw/tests/ | Q1,Q2,Q3,Q4,Q5,Q6,Q7 | independent | none | Z1 | n/a |
| DL-Q8 | R8 | 汇编 R8 的独立候选、证据和接受结果 | .ssot/nodes/Q8.json | Z1 | independent | none | Q8 | n/a |
| DL-RZ | R8 | 只在八个切片和九屏人工验收均接受后作最终发布决定 | .ssot/nodes/RZ.json | Q8 | independent | none | RZ | n/a |

## 并行宽度

| Parallel batch | Leaf deliverables | Independent deliverables | Conflict-grouped deliverables | Logical lane target | Available worker slots | Wave count |
| --- | --- | --- | --- | --- | --- | --- |
| R1 | 19 | 19 | 0 | 19 | 64 | 1 |
| R2 | 6 | 6 | 0 | 6 | 64 | 1 |
| R3 | 7 | 7 | 0 | 7 | 64 | 1 |
| R4 | 8 | 8 | 0 | 8 | 64 | 1 |
| R5 | 10 | 10 | 0 | 10 | 64 | 1 |
| R6 | 7 | 7 | 0 | 7 | 64 | 1 |
| R7 | 7 | 7 | 0 | 7 | 64 | 1 |
| R8 | 3 | 3 | 0 | 3 | 64 | 1 |

并行宽度表是逻辑交付线上限，不是已运行的外部执行者台账。本 SSOT 不虚构工作者、进程、会话或并行运行证据。

## ASCII 拓扑图

```text
F -> PD,PD1..PD9,TRD
R1: F PD PD1 PD2 PD3 PD4 PD5 PD6 PD7 PD8 PD9 TRD D1 D2 D3 T1 T3 T5 Q1
R2: I1 I2 I3 I4 I5 Q2
R3: L1 L2 L3 L4 L5 T2 Q3
R4: P1 P2 P3 P4 P5 P6 T6 Q4
R5: S1 S2 S3 S4 S5 C1 C2 C3 T4 Q5
R6: A1 A2 H1 H2 H3 H4 Q6
R7: K1 K2 K3 K4 K5 K6 Q7
R8: Z1 Q8 RZ
Q1..Q7 -> Z1 -> Q8 -> RZ
```

```mermaid
flowchart LR
  F["F"]
  PD["PD"]
  PD1["PD1"]
  PD2["PD2"]
  PD3["PD3"]
  PD4["PD4"]
  PD5["PD5"]
  PD6["PD6"]
  PD7["PD7"]
  PD8["PD8"]
  PD9["PD9"]
  TRD["TRD"]
  D1["D1"]
  D2["D2"]
  D3["D3"]
  T1["T1"]
  T3["T3"]
  T5["T5"]
  Q1["Q1"]
  I1["I1"]
  I2["I2"]
  I3["I3"]
  I4["I4"]
  I5["I5"]
  Q2["Q2"]
  L1["L1"]
  L2["L2"]
  L3["L3"]
  L4["L4"]
  L5["L5"]
  T2["T2"]
  Q3["Q3"]
  P1["P1"]
  P2["P2"]
  P3["P3"]
  P4["P4"]
  P5["P5"]
  P6["P6"]
  T6["T6"]
  Q4["Q4"]
  S1["S1"]
  S2["S2"]
  S3["S3"]
  S4["S4"]
  S5["S5"]
  C1["C1"]
  C2["C2"]
  C3["C3"]
  T4["T4"]
  Q5["Q5"]
  A1["A1"]
  A2["A2"]
  H1["H1"]
  H2["H2"]
  H3["H3"]
  H4["H4"]
  Q6["Q6"]
  K1["K1"]
  K2["K2"]
  K3["K3"]
  K4["K4"]
  K5["K5"]
  K6["K6"]
  Q7["Q7"]
  Z1["Z1"]
  Q8["Q8"]
  RZ["RZ"]
  F --> PD
  F --> PD1
  F --> PD2
  F --> PD3
  F --> PD4
  F --> PD5
  F --> PD6
  F --> PD7
  F --> PD8
  F --> PD9
  F --> TRD
  F --> D1
  PD --> D1
  PD1 --> D1
  T1 --> D1
  F --> D2
  PD --> D2
  PD2 --> D2
  T2 --> D2
  F --> D3
  PD --> D3
  TRD --> D3
  F --> A1
  PD7 --> A1
  T5 --> A1
  F --> A2
  PD6 --> A2
  PD7 --> A2
  PD9 --> A2
  S2 --> A2
  S3 --> A2
  T5 --> A2
  F --> H1
  F --> H2
  PD4 --> H2
  PD5 --> H2
  PD7 --> H2
  S3 --> H2
  S5 --> H2
  F --> H3
  D2 --> H3
  F --> H4
  F --> I1
  D1 --> I1
  T5 --> I1
  F --> I2
  PD1 --> I2
  F --> I3
  PD1 --> I3
  T2 --> I3
  F --> I4
  PD3 --> I4
  T3 --> I4
  T5 --> I4
  F --> I5
  PD3 --> I5
  I4 --> I5
  T5 --> I5
  F --> L1
  D2 --> L1
  F --> L2
  D2 --> L2
  F --> L3
  PD6 --> L3
  F --> L4
  PD6 --> L4
  F --> L5
  D2 --> L5
  T5 --> L5
  F --> P1
  PD8 --> P1
  F --> P2
  PD8 --> P2
  F --> P3
  PD8 --> P3
  P1 --> P3
  P2 --> P3
  T5 --> P3
  F --> P4
  PD8 --> P4
  F --> P5
  PD5 --> P5
  PD8 --> P5
  PD9 --> P5
  P2 --> P5
  T5 --> P5
  F --> P6
  PD9 --> P6
  T6 --> P6
  F --> S1
  T4 --> S1
  T5 --> S1
  F --> S2
  PD6 --> S2
  T5 --> S2
  F --> S3
  T3 --> S3
  F --> S4
  PD7 --> S4
  F --> S5
  PD4 --> S5
  T5 --> S5
  F --> C1
  PD7 --> C1
  F --> C2
  PD7 --> C2
  C1 --> C2
  F --> C3
  PD7 --> C3
  C2 --> C3
  F --> T1
  PD --> T1
  F --> T2
  PD --> T2
  PD2 --> T2
  F --> T3
  PD --> T3
  F --> T4
  PD --> T4
  F --> T5
  PD --> T5
  F --> T6
  PD --> T6
  PD9 --> T6
  F --> K1
  PD8 --> K1
  F --> K2
  PD8 --> K2
  F --> K3
  PD8 --> K3
  F --> K4
  PD8 --> K4
  F --> K5
  PD8 --> K5
  F --> K6
  PD8 --> K6
  PD --> Q1
  PD1 --> Q1
  PD2 --> Q1
  PD3 --> Q1
  PD4 --> Q1
  PD5 --> Q1
  PD6 --> Q1
  PD7 --> Q1
  PD8 --> Q1
  PD9 --> Q1
  TRD --> Q1
  D1 --> Q1
  D2 --> Q1
  D3 --> Q1
  T1 --> Q1
  T3 --> Q1
  T5 --> Q1
  I1 --> Q2
  I2 --> Q2
  I3 --> Q2
  I4 --> Q2
  I5 --> Q2
  L1 --> Q3
  L2 --> Q3
  L3 --> Q3
  L4 --> Q3
  L5 --> Q3
  T2 --> Q3
  P1 --> Q4
  P2 --> Q4
  P3 --> Q4
  P4 --> Q4
  P5 --> Q4
  P6 --> Q4
  T6 --> Q4
  S1 --> Q5
  S2 --> Q5
  S3 --> Q5
  S4 --> Q5
  S5 --> Q5
  C1 --> Q5
  C2 --> Q5
  C3 --> Q5
  T4 --> Q5
  A1 --> Q6
  A2 --> Q6
  H1 --> Q6
  H2 --> Q6
  H3 --> Q6
  H4 --> Q6
  K1 --> Q7
  K2 --> Q7
  K3 --> Q7
  K4 --> Q7
  K5 --> Q7
  K6 --> Q7
  Q1 --> Z1
  Q2 --> Z1
  Q3 --> Z1
  Q4 --> Z1
  Q5 --> Z1
  Q6 --> Z1
  Q7 --> Z1
  Z1 --> Q8
  Q8 --> RZ
  classDef accepted fill:#163c2e,stroke:#63d89b,color:#ffffff;
  classDef ready fill:#2f3d1f,stroke:#b9d968,color:#ffffff;
  classDef blocked fill:#3d2424,stroke:#e78686,color:#ffffff;
```

## 事实登记表（Facts Registry）

| 事实类别（Fact category） | 事实键（Fact key） | 登记值（Registered value） | 用途（Usage） |
| --- | --- | --- | --- |
| 命令 | ssot-validate-dev | `99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/report-to-ssot-development-paths/scripts/validate_ssot_bundle.py agents-results/2026-09-02/openclaw-media-full-checklist-implementation --skip-archive` | 开发期统一验证 |
| 路径 | owned-roots | `agents-results`; `.ssot`; `acceptance`; `99_System_OpenClaw`; `.agents/skills`; `scripts/validate_ssot_bundle.py`; `/api`; `/login`; `/setup`; `/app/home`; `/app/inbox`; `/app/library`; `/app/project/`; `/app/settings`; `/cloud/tasks`; `scripts/edit_backends/` | 正文工程定位覆盖 |
| 布局 | machine-layout | `.ssot/nodes`; `.ssot/edges`; `.ssot/view-sources`; `acceptance-fragments` | 机器分片与验收分片布局 |
| 必有标志 | development-validation | `--skip-archive` | 区分开发验证与正式整包验证 |
| 必无标志 | destructive-sync | `--delete` | 禁止破坏性同步 |
| 主机别名 | authoritative-remote | `origin` | 未来晋升时唯一权威远端别名 |
| 版本 | runtime-minimum | `3.11`; `6.2`; `18.7`; `31.4` | 本地 Python 与来源中显式版本号 |

## 验证、清理与完成条件

开发期统一验证命令为 `99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/report-to-ssot-development-paths/scripts/validate_ssot_bundle.py agents-results/2026-09-02/openclaw-media-full-checklist-implementation --skip-archive`。正式完成还要求受保护测试基线、九屏机器验收、产品负责人签署、Obsidian 快照核验与全局归档审计。运行环境最低版本为 `3.11`。

本轮只创建 SSOT，不创建或清理 Git 分支，不提交、不推送、不更改媒体文件。未来实施结束时，先推送并回读权威主分支，再清理已确认无独有内容的候选工作区与分支。
