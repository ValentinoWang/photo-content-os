# Acceptance Contract: 2026-11-26-Pho_R21-installed-watch-project-handoff

- Task ID: 2026-11-26-Pho_R21-installed-watch-project-handoff
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控在 U13-P 任务单指定安装版交接完成条件，并在第二轮授权重新导出 OpenAPI 及完成交付。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R21-installed-watch-project-handoff/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.installed-watch-project-handoff
- AC budget: 1
- Baseline identity: 54674e9a82e8b408c6b95a07ccb39736a0a32226
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R21-installed-watch-project-handoff

## User and scenario

制作人员在本地确认一个制作项目，随后设备接收策划台提交的交接。

## Problem

安装版设备缺少从本地确认到项目交接的持久关联。

## Expected outcome

交接绑定到已确认的项目和版本，重启后仍可读回同一份交接。

## Non-goals

正式项目选择页面、真实素材演练和付费服务调用。

## Normal path

配对设备运行普通 watch。本地确认已有项目或新建项目后接收交接并读回。

## Exception paths

缺少确认时保持待选。同名项目身份、设备、版本或摘要不符时拒绝交接。

## Invariants

项目按 ID 和版本匹配。重启可恢复已保存的关联，不重复投递。旧显式工具调用保持原有入口。

## Data impact

项目选择与投递记录保存在素材根目录内，以相对路径引用项目和工作区。

## Permissions

只有明确的本地确认可以产生项目选择。

## Performance and reliability

已确认的任务可在设备重启后继续，重复运行不会新增一次投递记录。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 固定提交构建的安装版在替身支持下，把正式交接落到本地确认项目并在重启后读回，拒绝错配且通过原有 R282 回归 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看安装版交接试跑记录 | acceptance/human/2026-W48/2026-11-26-Pho_R21-installed-watch-project-handoff/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_p1a_installed_watch.py | 325a91a4b33499ea1fcf2a7cdc32fd0b5bdb723e5f6a0f4fda8fb30da9259b2f | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 安装版交接与 R282 点名回归 | tests/test_p1a_installed_watch.py | Automatic | Yes |
| H-01 | 查看安装版交接试跑记录 | acceptance/human/2026-W48/2026-11-26-Pho_R21-installed-watch-project-handoff/checklist.md#h-01 | Human | No |

## Exploratory testing

无。

## Production monitoring and rollback

需要回退时使用普通 Git 回退，保留已交接项目原始材料。

## Risks and open decisions

本次试跑使用合成项目、确认替身和渲染替身。
