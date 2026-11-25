# Acceptance Contract: 2026-11-25-Pho_R15-dreamverse-shot-controls

- Task ID: 2026-11-25-Pho_R15-dreamverse-shot-controls
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控明确授权按任务单递交，并完成单镜真实出片与三帧核验；人工 H-01 待任务委托人审看视频。
- Request source: acceptance/requests/2026-W48/2026-11-25-Pho_R15-dreamverse-shot-controls/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.dreamverse-shot-controls
- AC budget: 2
- Baseline identity: 05b10524014c2106915393db14293b3f5a5bad18
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-25-Pho_R15-dreamverse-shot-controls

## User and scenario

制作台使用者为万相 2.6 文生视频镜头单独控制是否开启大模型提示词改写（`prompt_extend`）与负面提示词（`negative_prompt`），防止空镜被自动加入人物，并在默认情况下排除品牌标识、logo、商标、水印和文字。

## Problem

万相插件原先固定传 `prompt_extend: true` 且未传 `negative_prompt`，11-25 首次两镜实测中「清晨空跑道慢推」被自动加入晨跑者，「起跑器特写」末段鞋面出现类勾形图案（品牌标识风险）。

## Expected outcome

每个万相镜头可单独设置 `prompt_extend`（默认 `true`）与 `negative_prompt`（默认 `品牌标识、logo、商标、水印、文字`，可覆盖或传 `""` 清空），按百炼万相 2.6 官方文档透传至 `parameters.prompt_extend` 和 `input.negative_prompt`；修改任一控制项触发重新 `--confirm`；不支持这两项参数的 Seedance 镜头显式拒绝并在文档写明。

## Non-goals

不改动默认参数下的既有历史账本兼容行为，不触碰受保护的旧万相与 Seedance 测试文件，不调用真实方舟接口。

## Normal path

清单中省略控制项时沿用 `prompt_extend: true` 与默认去标负面词；设置 `prompt_extend: false` 或自定义 `negative_prompt` 时经桥接校验并透传至万相插件与 DreamVerse `shot.render`，账本记录实际使用的控制参数。

## Exception paths

`prompt_extend` 非布尔值、`negative_prompt` 非字符串或超过 500 字符、或在 `seedance` 镜头上传入这两项字段时，桥接与插件在提交前拒绝，不发起云端请求。

## Invariants

默认规格（`prompt_extend: true` 与默认负面词）保持旧版 5 元组规格哈希，兼容既有账本与受保护测试；改动控制项必须改变规格哈希并要求重新确认；已有已通过卡与人工记录不可篡改。

## Data impact

万相新增账本行记录 `prompt_extend` 与 `negative_prompt`；真实验证视频、抽帧与账本保留在仓库外 `~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25-controls/`，媒体文件不入库。

## Permissions

执行方运行离线单元测试、运行时契约检查及一次受限单镜真实出片并提交验收卡；任务委托人独立审看视频并签署人工结论。

## Performance and reliability

关闭 `prompt_extend` 时省略仅在改写开启下生效的 `shot_type` 字段；文档写明关闭改写时提示词须写全场景与材质并附 `shots.json` 示例。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 桥接校验并透传万相 `prompt_extend` 与默认/覆盖/清空 `negative_prompt`，改动触发重确认，500 字上限与类型校验及 Seedance 显式拒绝均生效 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/unit | 万相插件本地回环 HTTP 替身核对 `parameters.prompt_extend`、`input.negative_prompt` 映射及 Python/TS 哈希一致，且既有万相与 Seedance 全部测试与运行时契约检查通过 | Unit | Automatic | Yes |

## Human acceptance

已完成本机单镜真实出片（`task_id=858eedc5-239d-44ce-98e2-6812e7dab24f`，5 秒 9:16 720p，`prompt_extend=false`，默认负面词；成片位于 `~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25-controls/output/empty_track.mp4`，可对照首次含跑者的 `~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25/output/track.mp4`），H-01 留待任务委托人审看签署。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 核对关闭提示词改写后的空跑道视频无人物且无标识 | acceptance/human/2026-W48/2026-11-25-Pho_R15-dreamverse-shot-controls/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_dreamverse_shot_controls.py | 644a8ff07a9120632dc6e245a73a8ed7353ec56ed14777a334c220638dee303e | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 离线桥接与校验单元测试 | tests/test_dreamverse_shot_controls.py | Automatic | Yes |
| AC-02 | 万相回环 HTTP 替身、原万相/Seedance 测试及运行时契约检查 | tests/test_dreamverse_shot_controls.py | Automatic | Yes |
| H-01 | 对照空跑道新成片与首次含跑者成片 | acceptance/human/2026-W48/2026-11-25-Pho_R15-dreamverse-shot-controls/checklist.md#h-01 | Human | No |

## Exploratory testing

已完成一次单镜真跑验证（`empty_track.mp4` 与首/中/末三帧），确认画面无人、无品牌标识和文字，并据此在 README 补充关闭改写时写全场景与材质的提示词说明。

## Production monitoring and rollback

本改动默认保持 `prompt_extend: true`；若需还原默认负面词，可在单镜清单传 `"negative_prompt": ""` 或回退本提交。

## Risks and open decisions

关闭 `prompt_extend` 后模型严格按字面生成，提示词未写清“红色塑胶田径场”等材质与场景时可能偏离预期场地；最终画面效果由任务委托人在 H-01 确认。
