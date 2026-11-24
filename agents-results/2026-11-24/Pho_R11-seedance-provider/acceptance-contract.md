# Acceptance Contract: 2026-11-24-Pho_R11-seedance-provider

- Task ID: 2026-11-24-Pho_R11-seedance-provider
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控明确授权按任务单递交，人工项保留真实方舟镜头待验。
- Request source: acceptance/requests/2026-W48/2026-11-24-Pho_R11-seedance-provider/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.dreamverse-seedance
- AC budget: 2
- Baseline identity: 73de32703362f761e90bd67294264d7fe70e846f
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-24-Pho_R11-seedance-provider

## User and scenario

制作台使用者在同一份镜头清单里选择万相或 Seedance，并在中断等待后继续查看已提交任务。

## Problem

制作台原先只支持万相，无法为某一镜选择 Seedance。

## Expected outcome

一份清单可混用两个模型。每次确认绑定具体模型和规格。已有任务可查询和取回结果。

## Non-goals

本轮只以替身执行模型测试。真实方舟账号的生成留到人工验收。

## Normal path

安装两个插件，在清单中为目标镜头选 Seedance，确认后生成并取回视频和末帧。未指定时使用万相。

## Exception paths

越界规格在提交前失败。创建回复超时后保留未知收据，同一确认不会重提。

## Invariants

已经提交的任务不能因切换模型被静默替换。旧万相账本继续查询原任务。

## Data impact

新增账本行记录所选模型提供方。旧账本仍可读。

## Permissions

执行方运行替身测试。任务委托人在本人方舟账号开通后验收真实生成。

## Performance and reliability

本地等待中断不取消云端任务，同一确认最多尝试一次创建。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 双插件安装重跑字节一致，Seedance 回环 HTTP 替身覆盖创建、查询、失败和超时 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/unit | 换提供方须重新确认，按提供方选路由，旧万相账本无需重新确认 | Unit | Automatic | Yes |

## Human acceptance

有方舟密钥和开通的本人账号后执行一镜，当前保持待验。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 核对 Seedance 真实生成和续跑 | acceptance/human/2026-W48/2026-11-24-Pho_R11-seedance-provider/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_seedance_provider.py | 0622cfd3dd7f2b75f55bbf70e8dba9410009b9cad3cfda9905fc2ab9be01d5f1 | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 开发机专项执行 | tests/test_seedance_provider.py | Automatic | Yes |
| AC-02 | 开发机专项执行，含原万相与旧账本 | tests/test_seedance_provider.py | Automatic | Yes |
| H-01 | 本人方舟账号生成并续跑一镜 | acceptance/human/2026-W48/2026-11-24-Pho_R11-seedance-provider/checklist.md#h-01 | Human | No |

## Exploratory testing

未安排探索性验证。

## Production monitoring and rollback

本轮不启动真实生成。需要时可在镜头清单里切回万相。

## Risks and open decisions

真实方舟账号可用性、下载和视频效果待 H-01 核对。
