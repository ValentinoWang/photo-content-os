# Acceptance Contract: 2026-11-25-Pho_R13-avatar-clip

- Task ID: 2026-11-25-Pho_R13-avatar-clip
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控按任务单递交，人工项留给任务委托人，真实生成需本人确认费用。
- Request source: acceptance/requests/2026-W48/2026-11-25-Pho_R13-avatar-clip/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.avatar-videoretalk
- AC budget: 2
- Baseline identity: 0556ebbd405fc6228e8d63d1fa36cb2ec356a7df
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-25-Pho_R13-avatar-clip

## User and scenario

制作台使用者提供一段配音和一段正面底片视频，在确认同意和费用后调用百炼声动人像（videoretalk）生成口型对上配音的数字人口播视频，并在中断后按账本续查而不重复提交扣费。

## Problem

制作台此前缺少「数字人出镜」片段生成能力，无法在配音之后、剪辑之前把正面底片和配音合成为带「AI 生成」标记且支持长配音分段拼接、断点续跑的口播视频。

## Expected outcome

提供命令入口（`scripts/generate_avatar_clip.py`）和程序接口（`scripts/avatar/videoretalk.py`），支持默认试算（不调用云端）、加 `--live` 提交云端生成、超过约 110 秒按停顿切段并顺序拼接、账本落盘续查不重提、明确拒绝可重试、结果未知停下并支持带操作原因解锁，以及在成品旁附带「AI 生成」标记。

## Non-goals

本期不做制作台页面入口；机器验证只运行本地替身专项测试，不调用任何百炼或其他付费接口，不跑 `--live`，不上传用户本人声音或肖像。真实生成与成片口型核验留待人工验收。

## Normal path

默认运行只计算分段计划和预估费用，不调用云端接口；使用公开示例底片和配音确认费用后加 `--live` 提交，提交前写账本，轮询取回视频、拼接并输出带「AI 生成」标记的成片；再次以相同参数运行直接沿用已有结果，不重新提交。

## Exception paths

本人素材缺少本人同意原话时拒绝提交；云端返回明确 4xx 拒绝时账本记为 `rejected` 允许下次重试；欠费单独返回 `avatar_account_arrears` 错误码；提交后断网或回复状态不明时账本记为 `unknown` 并停下阻止重复扣费，须核实云端无任务后通过 `--forget-unknown <段号> --reason "<原因>"` 显式解锁。

## Invariants

已提交云端的任务在中断续跑时不会静默重提；结果未知状态不会在未人工核实前自动重试；输出成品旁 JSON 始终保留「AI 生成」标记。

## Data impact

在指定输出目录写入分段任务账本与成品旁附「AI 生成」标记元数据；不改动已有作品库与剪辑后端数据。

## Permissions

执行方仅在本机运行替身专项测试（不调用任何付费接口）；任务委托人在本人确认费用后执行公开示例素材的真实生成验收。

## Performance and reliability

长配音按静音停顿优先、必要时硬切控制在 110 秒以内分段生成并拼接；提交前先落账本，同一输入片段最多尝试一次云端创建，中断后可续查原任务。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 替身专项覆盖默认试算、本人同意校验、按停顿/硬切分段、提交上传轮询、AI 生成标记、中断续查与输入变更重提 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/unit | 替身专项覆盖提交被 4xx 明确拒绝可重试、欠费单独报错、结果未知阻断重提以及带原因解锁账本后重试 | Unit | Automatic | Yes |

## Human acceptance

本人确认费用（一次约 0.9 元：videoretalk 11 秒，0.08 元/秒）后，使用公开示例底片和配音运行 `scripts/generate_avatar_clip.py --live` 执行真跑验收，当前保持待验。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 确认费用后用公开示例素材真跑生成并核对口型、AI 生成标记与二次沿用 | acceptance/human/2026-W48/2026-11-25-Pho_R13-avatar-clip/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_avatar_videoretalk.py | 4cc7966fe6e8e58f404f35b2f6315951031d43ddbc473966d2b41d813b7912e0 | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 本机替身专项测试（开发机离线） | tests/test_avatar_videoretalk.py | Automatic | Yes |
| AC-02 | 本机替身专项测试（含拒绝重试、欠费报错、未知阻断与解锁） | tests/test_avatar_videoretalk.py | Automatic | Yes |
| H-01 | 本人确认费用后用公开示例底片与配音运行真跑生成并复跑验证 | acceptance/human/2026-W48/2026-11-25-Pho_R13-avatar-clip/checklist.md#h-01 | Human | No |

## Exploratory testing

未安排探索性验证。

## Production monitoring and rollback

本轮不启动真实云端生成，不影响现有制作台流程；需要回退时可停用 `scripts/generate_avatar_clip.py` 调用。

## Risks and open decisions

真实百炼声动人像（videoretalk）生成效果、口型同步质量与线上收费账单表现待 H-01 核对。
