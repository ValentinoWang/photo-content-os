# Acceptance Contract: 2026-11-26-Pho_R17-openclaw-contract-api-base

- Task ID: 2026-11-26-Pho_R17-openclaw-contract-api-base
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控第 2 轮更正指定递交本卡及 H-01 的操作和预期表现。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R17-openclaw-contract-api-base/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.openclaw-contract-api-base
- AC budget: 1
- Baseline identity: c93bab6b7d4d03beb07d9cf8040d214910bc2958
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R17-openclaw-contract-api-base

## User and scenario
制作台维护者刷新与策划台的兼容快照，并从自检读取固定版本。

## Problem
刷新时接口前缀沿用旧快照，自检另存固定版本，容易与策划台权威契约不一致。

## Expected outcome
刷新后的接口前缀取自策划台权威契约，自检显示快照固定的上游提交。

## Non-goals
不改制作台流水线别名、兼容策略或付费服务调用。

## Normal path
读取已提交的上游产品契约和流水线目录，明确批准后写入快照。

## Exception paths
上游产品契约未提交或无法读取，以及接口前缀缺失或无效时，拒绝刷新。

## Invariants
制作台别名和兼容策略保持原值。更新固定快照仍要求显式批准。

## Data impact
仅更新仓库内的兼容快照，不写用户素材。

## Permissions
任务委托人独立核对自检输出。

## Performance and reliability
刷新读取本地 Git 检出和契约文件，兼容检查使用本机已安装的 Agent。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 刷新器随策划台接口前缀变化生成快照，视频执行契约测试通过，Agent 与快照摘要一致 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看制作台自检显示的策划台版本 | acceptance/human/2026-W48/2026-11-26-Pho_R17-openclaw-contract-api-base/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_wave6_bridge_contracts.py | ec9ae9e6dcbd9c76ab2aea1ee3375e1a36f205186c9372785909e37ef02d9452 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 运行契约回归和 Agent 兼容检查 | tests/test_wave6_bridge_contracts.py | Automatic | Yes |
| H-01 | 核对自检输出 | acceptance/human/2026-W48/2026-11-26-Pho_R17-openclaw-contract-api-base/checklist.md#h-01 | Human | No |

## Exploratory testing
无。

## Production monitoring and rollback
需要回退时回退本次源码提交。

## Risks and open decisions
生产侧自检输出留待任务委托人核对。
