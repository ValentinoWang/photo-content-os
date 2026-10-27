# Acceptance Contract: 2026-10-26-R282-photo-direct-handoff-storyboard

- Task ID: 2026-10-26-R282-photo-direct-handoff-storyboard
- Contract version: 2
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27R280交付准备授权，R280批准设计的追加批准的旧任务横向边界扩展共用门禁；只更新当前摘要/版本/来源，AC/H、保护路径和阻塞判据不变；不代表人工PASS
- Request source: acceptance/requests/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/request.json; docs/tasks/R282-direct-handoff/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.direct-handoff-storyboard, studio.direct-handoff-narration, studio.direct-handoff-newer
- AC budget: 3
- Baseline identity: e26ec2f19d5e1136577873beb932f537a2a0037f；本批输入见handoff-r282/
- Product Context refs: agents-results/2026-10-27/R282-direct-handoff/acceptance-context.json
- Role Context refs: agents-results/2026-10-27/R282-direct-handoff/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-27/R282-direct-handoff/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-27/R282-direct-handoff/acceptance-context.json
- Visual Contract refs: docs/tasks/R278-direct-rescript/design/contract.json; docs/tasks/R278-direct-rescript/design/index.html
- UI Change declaration: agents-results/2026-10-27/R282-direct-handoff/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard

## User and scenario

创作者先在中台交接，在同件本机作品直接使用完整六列分镜、落地图片及配音；修改后可主动换新版。

## Problem

中台已有分镜和配音需要重复粘贴上传，版本与交接来源无法直接看清。

## Expected outcome

原H-01至H-03逐字保留：六列与图同源、沿用配音按实测时长生成、显式换版。

## Non-goals

不回传生成结果；不改中台界面或其原本机渲染线。本线程只验收物，不改代码测试docs或现有状态，不生成付费任务。

## Normal path

Given 同作品有效落地包；When 首次进入；Then 填六列、图片和配音。When 来源身份与版本仍当前；Then 建任务冻结来源并沿用配音。When 新包版本或时间有依据为更新、用户明确接受；Then 全表替换。

## Exception paths

无包、身份范围/版本不符返回null；图仅限本机且哈希有效。建任务来源过期409，不调用模型。带配音包的音频损坏或越界阻止建任务，不静默降级无声。

## Invariants

共用_video_handoff_projection读取规则；空/非法storyboardRevision、handedAt独立留空，不用workRevision或文件mtime替代；只读轮询有界；未接受新版不覆盖本机修改。

## Data impact

创建任务复制独立配音和来源快照，后续中台交接不改已建任务；本机编辑不回写中台。

## Permissions

沿用本机令牌、来源、素材根和路径边界；人工结论只由用户提交。

## Performance and reliability

交接轮询只读取当前描述文件，不读图片字节或扫描历史目录；错误包不清空其他内容。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 同源身份校验、六列与落地图片、可选元数据独立校验及只读有界 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/integration-contract | 沿用交接配音、实测对齐改短及合成、坏音频不降级、过期来源409 | Integration | Automatic | Yes |
| AC-03 | behavior | H-03 | machine/e2e | 旧本机内容保留、两种更新判断、明确接受才替换、旧包元数据省略 | E2E | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 中台分镜与图片完整进入 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 交接配音沿用生成 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 中台新版主动替换 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r282_frontend.py | b8415d29aad4e5419217108747f5f0f65cfcb278e4f4904aeb8cdf7072f425f5 | AC-01, AC-02, AC-03 |
| tests/test_r282_handoff.py | 58d24528c11d3e8b02b8b90205049d1b07cf46bd9837159bfa84ec666c9053fb | AC-01, AC-02, AC-03 |
| tests/test_r282_frontend.mjs | 6ad869cdb883b58abdedeaf2e1d95670082a1bb3f4d483918dd44c2292e73d5e | AC-01, AC-02, AC-03 |
| scripts/direct_video/rescript_frontend_gate.mjs | 91f3d8d20aba8db5466050c62295214b358921c68e1e8a8c4b25cbc6c680d1cc | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 交接身份、音频及真实挂载夹具交互 | tests/test_r282_frontend.py; tests/test_r282_handoff.py; tests/test_r282_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-02 | 交接身份、音频及真实挂载夹具交互 | tests/test_r282_frontend.py; tests/test_r282_handoff.py; tests/test_r282_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-03 | 交接身份、音频及真实挂载夹具交互 | tests/test_r282_frontend.py; tests/test_r282_handoff.py; tests/test_r282_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| H-01 | 当前真实中台交接及用户验收 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-01 | Human | Yes |
| H-02 | 当前真实中台交接及用户验收 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-02 | Human | Yes |
| H-03 | 当前真实中台交接及用户验收 | acceptance/human/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/checklist.md#h-03 | Human | Yes |

## Exploratory testing

前端最终完整截图及审阅在仓库外~/.photo-content-os/evidence/R282-direct-handoff/frontend/和supplement-1/；复用前须核对哈希和图库。合成接口夹具不证明真实中台或配音成片。

## Production monitoring and rollback

8769由总控从2430f0d导出副本运行。本线程不部署、不停启、不改真实作品或状态，失败保留日志交总控处理。

## Risks and open decisions

H-01的版本/时间和H-03的真实更新依赖自媒体创作Agent仓库2026-10-27-R299-media-handoff-storyboard-revision，用户说明正在做、未发布。外部依赖不是本仓库已完成关系；详细depends_on记录见external-dependencies.json。三个人工项保持阻塞PENDING，不能降级。

当前8769的12件Studio作品交接接口均为null，服务未启用交接绑定。生产读取规则只读核对发现p5-f24c41f746可与现存p5-binding旧包匹配，claims指向这件已核实作品；旧包2镜、Cherry配音50.24秒，0张落地图，版本/时间为空。该地址不是当前交接已完成证明；验收前总控须完成当前中台交接和对应binding/workspace配置，未授权本线程写状态或停启服务。

不跑全量pytest；同步、outline及历史全量红灯照实记录。外置媒体与深层检查run内实体截图的既有归档差异不伪造解决。
