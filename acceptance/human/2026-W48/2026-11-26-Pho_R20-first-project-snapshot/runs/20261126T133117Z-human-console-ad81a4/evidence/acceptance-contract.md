# Acceptance Contract: 2026-11-26-Pho_R20-first-project-snapshot

- Task ID: 2026-11-26-Pho_R20-first-project-snapshot
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控指定 U08-P 的完成条件，批准固定 U08 提交，并在第 3 轮指定登记和递交本卡。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R20-first-project-snapshot/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.first-project-snapshot
- AC budget: 1
- Baseline identity: a271e9c1424d36d982dd92518ba38b891136991f
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R20-first-project-snapshot

## User and scenario
制作台维护者给首次选项目和交接的后续接入固定一份可复查的策划台契约。

## Problem
原快照缺少首次交接操作、引用定义和样例，制作台无法单独验证并交给下游核对。

## Expected outcome
制作台快照与获准的 U08 提交同源，包含首次交接定义和正反样例。

## Non-goals
启用工作台页面或设备入口，使用真实素材，调用付费接口。

## Normal path
从获准的干净检出生成快照，对照契约定义、样例和来源摘要。

## Exception paths
检出含未提交改动、缺引用定义或内容摘要不符时拒绝。要求首次交接的调用方遇到旧快照时明确报缺。

## Invariants
保留制作台的管线别名、兼容策略和当前接口前缀。已有 v1 快照可供旧调用方加载。

## Data impact
更新仓库内的快照。素材目录不参与刷新。

## Permissions
只有调用方明确请求并批准换版时才写入快照。

## Performance and reliability
读取本地 Git 对象和 JSON。重复刷新逐字节一致。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 快照与获准提交的首次交接约定和样例一致，拒绝来源和内容校验失败，并可逐字节再生成 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看首次交接约定与正反样例 | acceptance/human/2026-W48/2026-11-26-Pho_R20-first-project-snapshot/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_p1a_first_project_snapshot.py | 36ba37e16dc516bf3472d192a3385c574aa6c95106e0b7d9160c4fca5f76db76 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 对照冻结提交并运行首次交接回归 | tests/test_p1a_first_project_snapshot.py | Automatic | Yes |
| H-01 | 查看首次交接部分 | acceptance/human/2026-W48/2026-11-26-Pho_R20-first-project-snapshot/checklist.md#h-01 | Human | No |

## Exploratory testing
无。

## Production monitoring and rollback
需回退时通过普通 Git 回退恢复上一版快照和读取规则。

## Risks and open decisions
工作台启用和真实项目交接由后续单元验收。
