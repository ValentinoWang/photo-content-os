# Acceptance Contract: OCM-K6

- Task ID: OCM-K6
- Contract version: 1
- Contract status: DRAFT
- Test baseline: PLANNED
- Acceptance owner: 产品负责人与对应领域验收负责人
- Approval evidence: 尚未批准
- Request source: agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- SSOT node: K6
- SSOT path: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/ssot-development-paths.md
- Readiness mode: FORMAL
- Decision refs: decision.scope.full-checklist@1, decision.edl.machine-authority@1
- Assumption IDs: none
- Invalidation keys: checklist.k6
- AC budget: 2
- Baseline identity: main@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35; checklist-sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- Product Context refs: SRC-K6, source-notes.md
- Role Context refs: 本地内容创作者，以及可选配对的上游中台用户
- Resolved Surface Contract refs: .ssot/source-requirements.json#SURF-PROJECT
- Screen Contract ref: .ssot/source-requirements.json#SURF-PROJECT
- Visual Contract refs: .ssot/source-requirements.json
- UI Change declaration: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-K6/ui-change.json
- Human acceptance workspace: none

## User and scenario

本地内容创作者从受支持的真实入口使用“Brief 和脚本两个文档阶段”，必要时主动配对上游账号或本地第三方工具。

## Problem

当前源码只覆盖该条目的局部原语或历史界面，不足以证明 HTML 中的完整业务承诺。

## Expected outcome

Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。

## Non-goals

不以删除条目、伪造外部成功、自动永久删除、绕过用户确认或修改生产剪映草稿作为实现方式。

## Normal path

```gherkin
Given 用户从真实入口进入对应界面，且所需本地资料与能力状态已就绪
When 用户查看或执行“Brief 和脚本两个文档阶段”
Then 系统完成“Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。”，并显示真实进度、回执和下一步
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
| AC-01 | behavior | machine/e2e | SRC-CHECKLIST-K6 | Brief 与脚本作为独立版本化阶段保留，并建立到项目文件和素材匹配输入的单向权威编译。；从真实入口完成正常业务闭环，回读结果与可见状态一致 | Automatic | Yes |
| AC-02 | behavior | machine/local-runtime | SRC-CHECKLIST-K6 | 前置、权限、路径、版本、能力或外部系统异常时失败关闭，不伪造成功且可重试或恢复 | Automatic | Yes |

## Human acceptance

机器证据负责本条目的确定性行为；用户理解、跨屏连贯性和视觉判断集中由 OCM-Z1 的九屏人工验收负责。

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| none | none | Behavior specification only; executable baseline not yet locked |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 正常闭环自动验收 | acceptance-fragments/OCM-K6/acceptance/machine/e2e/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| AC-02 | 失败、重试与恢复自动验收 | acceptance-fragments/OCM-K6/acceptance/machine/integration-contract/runs/&lt;run-id&gt;/result.md | Automatic | Yes |

## Exploratory testing

重点探查大批量、长标题、缺少元数据、中途关闭、刷新、跨日期、多位置、多账号、多提供方和恶意路径组合。

## Production monitoring and rollback

本合同先要求本地运行验收。任一远端或发布候选必须另外绑定不可变候选身份、指标窗口、停止阈值和前向修复或回退方法。

## Risks and open decisions

合同保持 DRAFT，直到行为被产品负责人批准且受保护的自动验收基线被锁定。
