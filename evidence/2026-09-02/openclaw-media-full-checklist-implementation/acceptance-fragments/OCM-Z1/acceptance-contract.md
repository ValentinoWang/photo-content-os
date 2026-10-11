# Acceptance Contract: OCM-Z1

- Task ID: OCM-Z1
- Contract version: 2
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 产品负责人与对应领域验收负责人
- Approval evidence: 用户于 2026-09-02 明确要求逐条可判定 AC、锁定新增测试并修复全部已列问题
- Request source: agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- SSOT node: Z1
- SSOT path: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/ssot-development-paths.md
- Readiness mode: FORMAL
- Decision refs: decision.scope.full-checklist@1, decision.organizer.auto-batching@1, decision.library.structured-index@1, decision.deletion.system-trash@1, decision.creative-model.user-config@1, decision.chatcut.desktop-mcp@1, decision.archive.location-lifecycle@1, decision.identity.optional-upstream@1, decision.edl.machine-authority@1, decision.jianying.historical-only@1
- Assumption IDs: none
- Invalidation keys: checklist.z1
- AC budget: 2
- Baseline identity: main@a3ae47100d6fce4cb139ce17a479eea16717e73a; checklist-sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- Product Context refs: SRC-D1 through SRC-K6, source-notes.md
- Role Context refs: 本地内容创作者，以及可选配对的上游中台用户
- Resolved Surface Contract refs: .ssot/source-requirements.json#ALL-EIGHT-SURFACES-AND-PROJECT-DIALOG
- Screen Contract ref: .ssot/source-requirements.json#ALL-EIGHT-SURFACES-AND-PROJECT-DIALOG
- Visual Contract refs: .ssot/source-requirements.json
- UI Change declaration: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-Z1/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W36/2026-09-02-OCM-Z1

## User and scenario

本地内容创作者从受支持的真实入口使用“八个 Surface、项目对话框与全清单整合”，必要时主动配对上游账号或本地第三方工具。

## Problem

当前源码只覆盖该条目的局部原语或历史界面，不足以证明 HTML 中的完整业务承诺。

## Expected outcome

八个 Surface 与新建项目对话框在真实入口中共同覆盖 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；K1-K6 并入工作台与项目页，不建立独立 Studio。

## Non-goals

不以删除条目、伪造外部成功、自动永久删除、绕过用户确认或修改生产剪映草稿作为实现方式。

## Normal path

```gherkin
Given 用户从真实入口进入对应界面，且所需本地资料与能力状态已就绪
When 用户查看或执行“八个 Surface、项目对话框与全清单整合”
Then 系统完成“八个 Surface 与新建项目对话框在真实入口中共同覆盖 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；K1-K6 并入工作台与项目页，不建立独立 Studio。”，并显示真实进度、回执和下一步
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

| ID | Class | Lane | Source requirement refs | Requirement | Mode | Blocking |
| --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | visual-fidelity | SRC-CHECKLIST-D1, SRC-CHECKLIST-D2, SRC-CHECKLIST-D3, SRC-CHECKLIST-A1, SRC-CHECKLIST-A2, SRC-CHECKLIST-H1, SRC-CHECKLIST-H2, SRC-CHECKLIST-H3, SRC-CHECKLIST-H4, SRC-CHECKLIST-I1, SRC-CHECKLIST-I2, SRC-CHECKLIST-I3, SRC-CHECKLIST-I4, SRC-CHECKLIST-I5, SRC-CHECKLIST-L1, SRC-CHECKLIST-L2, SRC-CHECKLIST-L3, SRC-CHECKLIST-L4, SRC-CHECKLIST-L5, SRC-CHECKLIST-P1, SRC-CHECKLIST-P2, SRC-CHECKLIST-P3, SRC-CHECKLIST-P4, SRC-CHECKLIST-P5, SRC-CHECKLIST-P6, SRC-CHECKLIST-S1, SRC-CHECKLIST-S2, SRC-CHECKLIST-S3, SRC-CHECKLIST-S4, SRC-CHECKLIST-S5, SRC-CHECKLIST-C1, SRC-CHECKLIST-C2, SRC-CHECKLIST-C3, SRC-CHECKLIST-T1, SRC-CHECKLIST-T2, SRC-CHECKLIST-T3, SRC-CHECKLIST-T4, SRC-CHECKLIST-T5, SRC-CHECKLIST-T6, SRC-CHECKLIST-K1, SRC-CHECKLIST-K2, SRC-CHECKLIST-K3, SRC-CHECKLIST-K4, SRC-CHECKLIST-K5, SRC-CHECKLIST-K6, SRC-PROTOTYPE-UI | 八个 Surface 与新建项目对话框在真实入口中共同覆盖 45 项来源要求，并保留统一安全、状态、恢复和视觉边界；K1-K6 并入工作台与项目页，不建立独立 Studio。；从真实入口完成正常业务闭环，回读结果与可见状态一致 | Automatic | Yes |
| AC-02 | behavior | machine/e2e | SRC-CHECKLIST-D1, SRC-CHECKLIST-D2, SRC-CHECKLIST-D3, SRC-CHECKLIST-A1, SRC-CHECKLIST-A2, SRC-CHECKLIST-H1, SRC-CHECKLIST-H2, SRC-CHECKLIST-H3, SRC-CHECKLIST-H4, SRC-CHECKLIST-I1, SRC-CHECKLIST-I2, SRC-CHECKLIST-I3, SRC-CHECKLIST-I4, SRC-CHECKLIST-I5, SRC-CHECKLIST-L1, SRC-CHECKLIST-L2, SRC-CHECKLIST-L3, SRC-CHECKLIST-L4, SRC-CHECKLIST-L5, SRC-CHECKLIST-P1, SRC-CHECKLIST-P2, SRC-CHECKLIST-P3, SRC-CHECKLIST-P4, SRC-CHECKLIST-P5, SRC-CHECKLIST-P6, SRC-CHECKLIST-S1, SRC-CHECKLIST-S2, SRC-CHECKLIST-S3, SRC-CHECKLIST-S4, SRC-CHECKLIST-S5, SRC-CHECKLIST-C1, SRC-CHECKLIST-C2, SRC-CHECKLIST-C3, SRC-CHECKLIST-T1, SRC-CHECKLIST-T2, SRC-CHECKLIST-T3, SRC-CHECKLIST-T4, SRC-CHECKLIST-T5, SRC-CHECKLIST-T6, SRC-CHECKLIST-K1, SRC-CHECKLIST-K2, SRC-CHECKLIST-K3, SRC-CHECKLIST-K4, SRC-CHECKLIST-K5, SRC-CHECKLIST-K6, SRC-PROTOTYPE-UI | 16 张双视口截图、DOM 锚点、计算样式、交互轨迹与路由清单必须绑定同一候选；任一漂移或人工验收未签署时不得晋升。 | Automatic | Yes |

## Human acceptance

H-01 至 H-08 分别覆盖八个 Surface，项目对话框随 H-03 工作台闭环验收。工作区处于 PREPARING；机器门禁全绿并生成新 handoff 后由产品负责人独立执行，自动化不得代签。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 登录完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 安装向导完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 工作台完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-03 | 产品负责人 | Yes |
| H-04 | 整理台完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-04 | 产品负责人 | Yes |
| H-05 | 素材库完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-05 | 产品负责人 | Yes |
| H-06 | 项目完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-06 | 产品负责人 | Yes |
| H-07 | 设置与诊断完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-07 | 产品负责人 | Yes |
| H-08 | 网页中台完整业务闭环的理解成本、视觉层级和恢复体验 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-08 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| 99_System_OpenClaw/tests/test_full_checklist_acceptance.py | 7da3443fa91763713b05943f1a5961f3b0f5b140090afb88222bca9376a38435 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |
| 99_System_OpenClaw/tests/test_desktop_openapi_route_sync.py | 188cee88f34e367eddbfa78f77ae9e072f56131ace6ad730088be259c3486bd5 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |
| 99_System_OpenClaw/tests/test_media_delete_recommendations.py | f0997262a8d178ff96a971489c6cd9fb73efd4fd0ba0ce59f4f12c76ea0a5174 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 正常闭环自动验收 | acceptance-fragments/OCM-Z1/acceptance/visual-fidelity/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| AC-02 | 失败、重试与恢复自动验收 | acceptance-fragments/OCM-Z1/acceptance/machine/e2e/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| H-01 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-01 | Human | Yes |
| H-02 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-02 | Human | Yes |
| H-03 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-03 | Human | Yes |
| H-04 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-04 | Human | Yes |
| H-05 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-05 | Human | Yes |
| H-06 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-06 | Human | Yes |
| H-07 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-07 | Human | Yes |
| H-08 | 产品人工验收 | acceptance/human/2026-W36/2026-09-02-OCM-Z1/checklist.md#h-08 | Human | Yes |

## Exploratory testing

重点探查大批量、长标题、缺少元数据、中途关闭、刷新、跨日期、多位置、多账号、多提供方和恶意路径组合。

## Production monitoring and rollback

本合同先要求本地运行验收。任一远端或发布候选必须另外绑定不可变候选身份、指标窗口、停止阈值和前向修复或回退方法。

## Risks and open decisions

合同已按用户本次明确整改指令批准并锁定测试基线；实现节点仅登记 IMPLEMENTED，仍需执行证据与独立验收后才能晋升 VERIFIED/ACCEPTED。
