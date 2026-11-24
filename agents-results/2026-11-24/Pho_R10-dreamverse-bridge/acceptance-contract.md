# Acceptance Contract: 2026-11-24-Pho_R10-dreamverse-bridge

- Task ID: 2026-11-24-Pho_R10-dreamverse-bridge
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控本轮明确授权递交 Pho_R10 并保留真实生成项待验。验收步骤和预期沿用已登记需求。
- Request source: acceptance/requests/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.dreamverse-model-catalog, photo.dreamverse-shot-resume
- AC budget: 1
- Baseline identity: 308eb2e86d264118514261a45db987632dc3cb4e
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge

## User and scenario

制作台使用者核对 DreamVerse 中的万相模型目录，随后逐镜确认生成，并在第二镜的云任务等待期间中断本地流程。

## Problem

已发布的制作台桥接缺少对应交付卡。当前百炼账户无法完成真实视频生成。

## Expected outcome

确认的镜头只提交一次，生成结果包含视频、末帧与可核对的账本。真实产出与中断续跑由任务委托人确认。

## Non-goals

本轮只补交付卡与机器证据。产品源码和现有人工记录按原样保留。本轮不调用万相。

## Normal path

模型目录列出万相 2.6 的能力。逐镜确认后得到账本条目，恢复等待时按同一任务 ID 查询，完成后取回视频与末帧。

## Exception paths

拿不到云端任务 ID 时留下未知状态并提示人工核对。同一确认不会自动重提。

## Invariants

机器验证限于开发机替身测试。真实生成证据只进入待验说明。

## Data impact

本轮只记录验收文本和参考图，真实账本与服务收据原件保留在仓库外。

## Permissions

执行方运行指定机器检查并递交卡。任务委托人独立填写人工结论。

## Performance and reliability

开发机专项检查确定性验证恢复、重复提交防护和未知状态，无新增性能目标。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01, H-02 | machine/unit | 指定测试退出 0，覆盖模型参数、安装、逐镜确认、中断恢复、重复提交防护及未知结果 | Unit | Automatic | Yes |

## Human acceptance

原样沿用需求卡的两项标准。两项保持待验。H-02 当前未完成：百炼账户欠费（HTTP 400 Arrearage），两次提交均未取得任务 ID，账本为 unknown。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 核对 DreamVerse 模型目录 | acceptance/human/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge/checklist.md#h-01 | 任务委托人 | No |
| H-02 | 核对两镜真实生成、末帧和中断前后的任务 | acceptance/human/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge/checklist.md#h-02 | 任务委托人 | No |

## Protected acceptance tests

本轮只冻结已发布源码中的测试文件。复验入口由任务单提供，原始字节摘要随机器记录保存。

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_dreamverse_bridge.py | e8db0e3b585d5a40fed3f27735119b69565d1adcaf27b6b515bf6a24abba07ed | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 开发机专项执行 | tests/test_dreamverse_bridge.py | Automatic | Yes |
| H-01 | 查模型目录 | acceptance/human/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge/checklist.md#h-01 | Human | No |
| H-02 | 核对真实镜头及恢复后的账本 | acceptance/human/2026-W48/2026-11-24-Pho_R10-dreamverse-bridge/checklist.md#h-02 | Human | No |

## Exploratory testing

本轮未安排探索性验证。

## Production monitoring and rollback

本轮只交付验收材料，不启动生产生成。

## Risks and open decisions

开发机替身无法证明百炼账户可生成成片。两镜的成片、末帧和真实任务恢复证据仍待 H-02 核对。
