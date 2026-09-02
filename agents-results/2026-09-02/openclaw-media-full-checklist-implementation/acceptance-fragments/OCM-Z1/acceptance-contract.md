# Acceptance Contract: OCM-Z1

- Task ID: OCM-Z1
- Contract version: 1
- Contract status: DRAFT
- Test baseline: PLANNED
- Acceptance owner: 产品负责人与对应领域验收负责人
- Approval evidence: 尚未批准
- Request source: agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html sha256:88f32d8d882d3c98bf152c87e31ef6bf0dd7f94701a6db03e39e5bfeaa0697bf
- SSOT node: Z1
- SSOT path: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/ssot-development-paths.md
- Readiness mode: FORMAL
- Decision refs: decision.scope.full-checklist@1, decision.organizer.auto-batching@1, decision.library.structured-index@1, decision.deletion.system-trash@1, decision.creative-model.user-config@1, decision.chatcut.desktop-mcp@1, decision.archive.location-lifecycle@1, decision.identity.optional-upstream@1, decision.edl.machine-authority@1, decision.jianying.historical-only@1
- Assumption IDs: none
- Invalidation keys: checklist.z1
- AC budget: 2
- Baseline identity: main@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35; checklist-sha256:88f32d8d882d3c98bf152c87e31ef6bf0dd7f94701a6db03e39e5bfeaa0697bf
- Product Context refs: SRC-D1 through SRC-K6, source-notes.md
- Role Context refs: 本地内容创作者，以及可选配对的上游中台用户
- Resolved Surface Contract refs: .ssot/surface-inventory.json#ALL-NINE-SURFACES
- Screen Contract ref: .ssot/interaction-matrix.json#ALL-NINE-SURFACES
- Visual Contract refs: .ssot/visual-fidelity-contract.json
- UI Change declaration: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-Z1/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W36/2026-09-02-OCM-Z1

## User and scenario

本地内容创作者从受支持的真实入口使用“九屏共享入口与全清单整合”，必要时主动配对上游账号或本地第三方工具。

## Problem

当前源码只覆盖该条目的局部原语或历史界面，不足以证明 HTML 中的完整业务承诺。

## Expected outcome

九个表面在真实入口中共同完成 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；项目内视觉工作台同时展示现状证据、确定性原型、候选方向、选择记录和工程交接。

## Non-goals

不以删除条目、伪造外部成功、自动永久删除、绕过用户确认或修改生产剪映草稿作为实现方式。

## Normal path

```gherkin
Given 用户从真实入口进入对应界面，且所需本地资料与能力状态已就绪
When 用户查看或执行“九屏共享入口与全清单整合”
Then 系统完成“九个表面在真实入口中共同完成 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；项目内视觉工作台同时展示现状证据、确定性原型、候选方向、选择记录和工程交接。”，并显示真实进度、回执和下一步
```

## Exception paths

覆盖缺少资料、路径越界、能力不支持、凭据缺失、并发版本冲突、外部超时、重复提交、部分失败、重试和再次进入。任一前置不满足时必须明确阻断或呈现不支持，不得伪造完成。

## Invariants

原始媒体不被自动永久删除；机器执行剪辑方案只读结构化权威；未配对上游身份不限制本地功能；外部能力只在实时探测与主动连接后呈现。

## Data impact

实现必须声明创建、更新、移动、恢复、幂等键、回执和保留期。破坏性动作仅在可恢复、用户二次确认且回读成功时允许。

## Permissions

本地用户可查看与执行本地功能；账号、外部模型和 ChatCut 需用户主动配置或连接；发布和人工验收由指定负责人签署。

## Performance and reliability

界面不因单个探测或外部超时失去响应；长任务提供进度、取消、重试和重启后恢复；实际阈值在测试基线锁定前由该节点冻结。

## Acceptance criteria

| ID | Class | Source requirement refs | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | SRC-D1, SRC-D2, SRC-D3, SRC-A1, SRC-A2, SRC-H1, SRC-H2, SRC-H3, SRC-H4, SRC-I1, SRC-I2, SRC-I3, SRC-I4, SRC-I5, SRC-L1, SRC-L2, SRC-L3, SRC-L4, SRC-L5, SRC-P1, SRC-P2, SRC-P3, SRC-P4, SRC-P5, SRC-P6, SRC-S1, SRC-S2, SRC-S3, SRC-S4, SRC-S5, SRC-C1, SRC-C2, SRC-C3, SRC-T1, SRC-T2, SRC-T3, SRC-T4, SRC-T5, SRC-T6, SRC-K1, SRC-K2, SRC-K3, SRC-K4, SRC-K5, SRC-K6 | 九个表面在真实入口中共同完成 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；项目内视觉工作台同时展示现状证据、确定性原型、候选方向、选择记录和工程交接。；从真实入口完成正常业务闭环，回读结果与可见状态一致 | E2E and local runtime | Automatic | Yes |
| AC-02 | behavior | SRC-D1, SRC-D2, SRC-D3, SRC-A1, SRC-A2, SRC-H1, SRC-H2, SRC-H3, SRC-H4, SRC-I1, SRC-I2, SRC-I3, SRC-I4, SRC-I5, SRC-L1, SRC-L2, SRC-L3, SRC-L4, SRC-L5, SRC-P1, SRC-P2, SRC-P3, SRC-P4, SRC-P5, SRC-P6, SRC-S1, SRC-S2, SRC-S3, SRC-S4, SRC-S5, SRC-C1, SRC-C2, SRC-C3, SRC-T1, SRC-T2, SRC-T3, SRC-T4, SRC-T5, SRC-T6, SRC-K1, SRC-K2, SRC-K3, SRC-K4, SRC-K5, SRC-K6 | 前置、权限、路径、版本、能力或外部系统异常时失败关闭，不伪造成功且可重试或恢复 | Integration, E2E and negative paths | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 登录中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 安装向导中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 工作台中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-03 | 产品负责人 | Yes |
| H-04 | 整理台中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-04 | 产品负责人 | Yes |
| H-05 | 素材库中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-05 | 产品负责人 | Yes |
| H-06 | 项目中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-06 | 产品负责人 | Yes |
| H-07 | 设置与诊断中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-07 | 产品负责人 | Yes |
| H-08 | 网页中台中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-08 | 产品负责人 | Yes |
| H-09 | Studio 能力迁移区中目标用户能否不借助隐藏说明完成主要任务 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-09 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| none | none | Behavior specification only; executable baseline not yet locked |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 正常闭环自动验收 | acceptance-fragments/OCM-Z1/acceptance/machine/e2e/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| AC-02 | 失败、重试与恢复自动验收 | acceptance-fragments/OCM-Z1/acceptance/machine/integration-contract/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| H-01 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-01 | Human | Yes |
| H-02 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-02 | Human | Yes |
| H-03 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-03 | Human | Yes |
| H-04 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-04 | Human | Yes |
| H-05 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-05 | Human | Yes |
| H-06 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-06 | Human | Yes |
| H-07 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-07 | Human | Yes |
| H-08 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-08 | Human | Yes |
| H-09 | 九屏产品验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-09 | Human | Yes |

## Exploratory testing

重点探查大批量、长标题、缺少元数据、中途关闭、刷新、跨日期、多位置、多账号、多提供方和恶意路径组合。

## Production monitoring and rollback

本合同先要求本地运行验收。任一远端或发布候选必须另外绑定不可变候选身份、指标窗口、停止阈值和前向修复或回退方法。

## Risks and open decisions

合同保持 DRAFT，至到行为被产品负责人批准且受保护的自动验收基线被锁定。
