# Acceptance Contract: 2026-11-24-Pho_R06-concat-backend

- Task ID: 2026-11-24-Pho_R06-concat-backend
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 2026-11-24 本轮任务委托原话「H-01、H-02 是人工验收项，只递交、状态保持待用户验收，不代签、不写『通过』」；清单沿用已登记需求的步骤和预期，人工结论另由任务委托人填写。
- Request source: acceptance/requests/2026-W48/2026-11-24-Pho_R06-concat-backend/request.json, docs/tasks/concat-backend/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.concat-roughcut, photo.concat-refine
- AC budget: 2
- Baseline identity: 1d158c7e3b90ad8e6330b340acede0bc7134fc42
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-24-Pho_R06-concat-backend

## User and scenario

口播创作者显式选择 Concat 生成可编辑粗稿，再用桌面编辑器精修。

## Problem

既有实现已在主线上，缺少 Pho_R06 对应的交付卡及与当前源码绑定的验证证据。

## Expected outcome

按获准建议删段，保留可编辑的中文字幕和透明动效，并导出可核对的 MP4。人工清单沿用需求卡的两项标准。

## Non-goals

本轮只补交付验收材料。产品代码、测试、需求卡、其他验收卡和人工结论维持现状。

## Normal path

显式选择 Concat，按获准建议生成和保存工程，读回真实时间线并导出。在 20 秒样片中删除两段共 5 秒，得到 3 段、3 条字幕和 15 秒 MP4。

## Exception paths

Concat 不可用时返回相应状态。工具报错或超时保留原因，保存失败时停止导出，结束会话只回收当前会话的子进程。

## Invariants

机器证据绑定冻结源码和本合同。U1/U2 的替身范围与 U3 的真实运行各自明确。人工结论由任务委托人签署。

## Data impact

提交本卡的合同、清单、绑定、文本证据和生成索引。合成媒体留在仓库外，真实素材和项目保持原状。

## Permissions

执行方可以运行指定检查并递交卡。任务委托人操作桌面 Concat，独立给出两项人工结论。

## Performance and reliability

开发机执行指定专项，本机仅运行真实 Mac App 冒烟。样片时间线和导出时长允许一帧误差。没有新增性能目标。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01, H-02 | machine/unit | 指定后端及接口测试退出 0，覆盖工具错误、超时、进程归属、保存失败和后端注册 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01, H-02 | machine/local-runtime | 真实 Concat 生成、保存、回读并导出样片，3 段、3 条字幕、时长误差不超过一帧，5 秒帧红块周围可见原片 | Local runtime | Automatic | Yes |

## Human acceptance

两项原样沿用需求卡，递交后由任务委托人验收。已发布代码，本次按授权递交待验收卡。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看样片的删段、中文字幕和透明动效 | acceptance/human/2026-W48/2026-11-24-Pho_R06-concat-backend/checklist.md#h-01 | 任务委托人 | No |
| H-02 | 在 Concat 打开、精修并保存粗稿 | acceptance/human/2026-W48/2026-11-24-Pho_R06-concat-backend/checklist.md#h-02 | 任务委托人 | No |

## Protected acceptance tests

本轮冻结现有执行入口和测试文件的摘要。该登记不追溯到实现前。

| Path | SHA-256 | Covers |
| --- | --- | --- |
| docs/tasks/concat-backend/verify_unit.sh | 913a3f599dd1a935d0aa1060c807f4965f41dc88859b06223ae474004b413413 | AC-01 |
| tests/test_concat_backend.py | 60cb02666aac41a118df5c079692978d2f21b787a2856aae73b57417ceeb4224 | AC-01 |
| tests/test_edit_backend_interface.py | c866a9dcdb08fb235d23df8c7b5b164cd7d9c7755a113383c33507a9787645cf | AC-01 |
| tests/manual/concat_smoke.py | ceba8d33b09437e4a2dbc43f14c226ca5b2ad95ab45d79dfe4710219d6601556 | AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 开发机指定专项 | docs/tasks/concat-backend/verify_unit.sh | Automatic | Yes |
| AC-02 | 本机真实 Concat 冒烟 | tests/manual/concat_smoke.py | Automatic | Yes |
| H-01 | 查看样片结果 | acceptance/human/2026-W48/2026-11-24-Pho_R06-concat-backend/checklist.md#h-01 | Human | No |
| H-02 | 打开并保存粗稿 | acceptance/human/2026-W48/2026-11-24-Pho_R06-concat-backend/checklist.md#h-02 | Human | No |

## Exploratory testing

未安排补充探索。

## Production monitoring and rollback

本轮无部署和生产媒体写入。门禁不满足时保留原始结果并停止推主线。

## Risks and open decisions

U3 使用合成样片，真实口播工程的桌面精修属于 H-02。H-01、H-02 均待任务委托人填写结论。
