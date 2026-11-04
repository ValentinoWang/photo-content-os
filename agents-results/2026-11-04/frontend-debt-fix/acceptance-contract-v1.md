# Acceptance Contract: 2026-11-04-Pho_R01-frontend-debt-fix

- Task ID: 2026-11-04-Pho_R01-frontend-debt-fix
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户 2026-11-04 手机原话「推」；总控 TASK-2、TASK-3、TASK-4 分别指明补修范围、验证和递交步骤，不代表人工 PASS
- Request source: acceptance/requests/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.frontend-debt-fix
- AC budget: 3
- Baseline identity: dd8096ed8fc3ccbb838b9a890e8112d653dcc64e，见 baseline.json
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix

## User and scenario

创作者在工作台填写分镜、处理素材和切换作品做法时，需要保留输入、看清失败并确认有影响的操作。

## Problem

超长输入被截断、未知错误被误报、回收站缺工作台确认、页签键盘操作及部分按钮和读屏行为不一致。H-02 实测又发现 macOS 回收站调用、数字往返编号和部分失败回执缺陷，总控任务单指明与本轮一起修复。

## Expected outcome

超限保留原文并禁止提交；未知错误码原样显示；回收站二次确认后只移除有回执的项目、待处理项仍可见；做法页签方向键循环；镜头按钮可读屏且按钮文字不被选中。

## Non-goals

不改字号、圆角、间距，不做美化或组件改版，不动主检出中的未提交改动；不推送、不发布、不代签人工验收。不处理真实媒体；Linux 定时环境暂不覆盖 macOS 专用真实测试，接手：总控。

## Normal path

输入超限时保留并提示；选择合成素材时取消不移动、确认后产生可核验回执；通过左右方向键切换做法。

## Exception paths

系统调用失败或只部分成功时保留未确认候选和错误码；文件可能已移动但验证失败时明确状态待确认，不声称没移动。全量出现基线之外的新失败、测试收集错误或未完成时不递交机器 PASS。

## Invariants

私人素材、真实作品和主检出未提交内容不动；人工验收不由机器替代。经确认的旧卡保护测试不可悄悄重写哈希。

## Data impact

仅隔离合成文件实测系统回收站并按名称和哈希恢复；新增任务证据和验收物。

## Permissions

执行者准备机器证据及交付卡；任务委托人独立完成 H-01、H-02、H-03。

## Performance and reliability

开发机连接被拒，按项目本机预算串行运行，全量使用 nice 10 和归档快照。前端和回收站真实操作只断言测试覆盖范围。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01, H-03 | machine/integration-contract | 输入限制、未知错误、镜头按钮、方向键和按钮选择的定向检查通过 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/integration-contract | 合成素材经真实 macOS 废纸篓完成取消、确认、回执和恢复；部分成功和未知失败码有定向测试 | Integration | Automatic | Yes |
| AC-03 | behavior | H-01, H-02, H-03 | machine/non-functional | 指定源码全量完成，对照原基线无新增失败，原失败及跳过如实列出 | Regression | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 超长文字保留与提示 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-01 | 任务委托人 | Yes |
| H-02 | 工作台回收站确认 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-02 | 任务委托人 | Yes |
| H-03 | 做法页签方向键 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-03 | 任务委托人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_input_limit.mjs | 5271e455480ebe78d44c6a3c96060ee598fa04559877e608fe95f365ba894786 | AC-01, H-01 |
| tests/test_review_tabs.mjs | 2efd0b3dc3d432f804ce7b313649e48272b6d345d44e4438af3b48c343e4d839 | AC-01, H-03 |
| tests/test_r276_direct_frontend.mjs | ec2cef3d58bca41a03d93a11ed899091ed5659007eb96b7054feb763206636ca | AC-01 |
| tests/test_media_trash_flow.py | 2c2916616710adb4f781851c0e84d5bcabf434b243c6f5b865f9d1c0b775a312 | AC-02, H-02 |
| tests/test_media_delete_recommendations.py | 9e323f23a5f1b92fbf646438aca6d73a1efab5c26bcd899a89de257aaf69bace | AC-02 |
| tests/test_ssot_policy_integration.py | 838c6ab12585acd2f9cc5a6d3ef03147a5b0ddeaede8b1995e77830f243b0230 | AC-02 |
| tests/test_trash_result.mjs | faca52e1138c515563fc25af348c4083fbb0ca4e39dbfd1f253487a81f0de0e5 | AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 任务单 Node 与前端定向检查 | tests/test_input_limit.mjs; tests/test_review_tabs.mjs; tests/test_r276_direct_frontend.mjs | Automatic | Yes |
| AC-02 | 真机合成回收站、回执及部分失败定向检查 | tests/test_media_trash_flow.py; tests/test_media_delete_recommendations.py; tests/test_ssot_policy_integration.py; tests/test_trash_result.mjs | Automatic | Yes |
| AC-03 | 隔离归档全量对照逐项基线 | baseline-failures.txt | Automatic | Yes |
| H-01 | 用户核对超长输入 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-01 | Human | Yes |
| H-02 | 用户核对确认及移动 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-02 | Human | Yes |
| H-03 | 用户核对键盘方向切换 | acceptance/human/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/checklist.md#h-03 | Human | Yes |

## Exploratory testing

在本地真实 Studio 用合成素材验证 H-02；部分失败截图为模拟响应，单独标注。

## Production monitoring and rollback

不部署、不推送，发现新增失败停止并交总控处理。

## Risks and open decisions

人工尚未签。全量原有字幕、黑帧、文档同步等失败单独列出，不声称全绿。macOS 专用系统测试在 Linux 上跳过，未新增定时 macOS 层。
