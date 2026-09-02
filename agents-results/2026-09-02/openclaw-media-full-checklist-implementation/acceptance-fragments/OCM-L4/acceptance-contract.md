# Acceptance Contract: OCM-L4

- Task ID: OCM-L4
- Contract version: 2
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 产品负责人与对应领域验收负责人
- Approval evidence: 用户于 2026-09-02 明确要求逐条可判定 AC、锁定新增测试并修复全部已列问题
- Request source: agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- SSOT node: L4
- SSOT path: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/ssot-development-paths.md
- Readiness mode: FORMAL
- Decision refs: decision.scope.full-checklist@1, decision.archive.location-lifecycle@1
- Assumption IDs: none
- Invalidation keys: checklist.l4
- AC budget: 2
- Baseline identity: main@a3ae47100d6fce4cb139ce17a479eea16717e73a; checklist-sha256:73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb
- Product Context refs: SRC-L4, source-notes.md
- Role Context refs: 本地内容创作者，以及可选配对的上游中台用户
- Resolved Surface Contract refs: .ssot/source-requirements.json#SURF-LIBRARY
- Screen Contract ref: .ssot/source-requirements.json#SURF-LIBRARY
- Visual Contract refs: .ssot/source-requirements.json
- UI Change declaration: agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-L4/ui-change.json
- Human acceptance workspace: none

## User and scenario

本地内容创作者从受支持的真实入口使用“归档索引卡（检索关键词、精选副本入口、恢复方式）”，必要时主动配对上游账号或本地第三方工具。

## Problem

当前源码只覆盖该条目的局部原语或历史界面，不足以证明 HTML 中的完整业务承诺。

## Expected outcome

归档索引卡（检索关键词、精选副本入口、恢复方式）：包 HTTP 接口。这是素材库里唯一后端完备的部分。

## Non-goals

不以删除条目、伪造外部成功、自动永久删除、绕过用户确认或修改生产剪映草稿作为实现方式。

## Normal path

```gherkin
Given 用户从真实入口进入对应界面，且所需本地资料与能力状态已就绪
When 用户查看或执行“归档索引卡（检索关键词、精选副本入口、恢复方式）”
Then 系统完成“归档索引卡（检索关键词、精选副本入口、恢复方式）：包 HTTP 接口。这是素材库里唯一后端完备的部分。”，并显示真实进度、回执和下一步
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
| AC-01 | behavior | machine/e2e | SRC-CHECKLIST-L4 | 归档索引卡（检索关键词、精选副本入口、恢复方式）：包 HTTP 接口。这是素材库里唯一后端完备的部分。；从真实入口完成正常业务闭环，回读结果与可见状态一致 | Automatic | Yes |
| AC-02 | behavior | machine/local-runtime | SRC-CHECKLIST-L4 | 恢复必须写入新目录并逐项校验大小与 SHA-256；目标非空、清单漂移或校验失败时禁止覆盖原件。 | Automatic | Yes |

## Human acceptance

机器证据负责本条目的确定性行为；用户理解、跨屏连贯性和视觉判断集中由 OCM-Z1 的八个 Surface 与项目对话框人工验收负责。

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| 99_System_OpenClaw/tests/test_full_checklist_acceptance.py | 7da3443fa91763713b05943f1a5961f3b0f5b140090afb88222bca9376a38435 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |
| 99_System_OpenClaw/tests/test_desktop_openapi_route_sync.py | 188cee88f34e367eddbfa78f77ae9e072f56131ace6ad730088be259c3486bd5 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |
| 99_System_OpenClaw/tests/test_media_delete_recommendations.py | f0997262a8d178ff96a971489c6cd9fb73efd4fd0ba0ce59f4f12c76ea0a5174 | 45 项静态、HTTP 与 OpenAPI/服务器双向同步门禁 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 正常闭环自动验收 | acceptance-fragments/OCM-L4/acceptance/machine/e2e/runs/&lt;run-id&gt;/result.md | Automatic | Yes |
| AC-02 | 失败、重试与恢复自动验收 | acceptance-fragments/OCM-L4/acceptance/machine/local-runtime/runs/&lt;run-id&gt;/result.md | Automatic | Yes |

## Exploratory testing

重点探查大批量、长标题、缺少元数据、中途关闭、刷新、跨日期、多位置、多账号、多提供方和恶意路径组合。

## Production monitoring and rollback

本合同先要求本地运行验收。任一远端或发布候选必须另外绑定不可变候选身份、指标窗口、停止阈值和前向修复或回退方法。

## Risks and open decisions

合同已按用户本次明确整改指令批准并锁定测试基线；实现节点仅登记 IMPLEMENTED，仍需执行证据与独立验收后才能晋升 VERIFIED/ACCEPTED。
