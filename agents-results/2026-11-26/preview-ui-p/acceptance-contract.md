# Acceptance Contract: 2026-11-26-Pho_R23-studio-project-pick

- Task ID: 2026-11-26-Pho_R23-studio-project-pick
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: TASK-UI-P.md 总控裁定（2026-11-26 第 2 轮），用户要求按该节实现到推送。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R23-studio-project-pick/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.studio-project-pick
- AC budget: 2
- Baseline identity: f847a879e98a55d4eb72e5a625ac02dc6e332d6f
- Product Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Role Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Resolved Surface Contract refs: docs/tasks/R220-studio-ia-preview/resolved-surface-contract.json
- Screen Contract ref: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Visual Contract refs: docs/tasks/R220-studio-ia-preview/design-contract.json
- UI Change declaration: agents-results/2026-11-26/preview-ui-p/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R23-studio-project-pick

## User and scenario

本机创作者在 Studio 工作台确认策划台作品应该使用哪个制作项目。

## Problem

请求停在待选，创作者在 Studio 找不到操作入口。确认后的项目页缺少发送该请求的作品版本。

## Expected outcome

工作台顶部可以选已有项目或填名新建。确认后安装版设备把选择交给策划台，项目页显示待选卡上的作品版本。

## Non-goals

作品标题和 Brief 链接、策划台接口及 agent 契约、发布和付费调用。

## Normal path

工作台读取本机待选记录。创作者用项目列表或新建表单明确选择，安装版设备消费该选择并确认，打开项目可以看到来源版本。

## Exception paths

超过时限的请求不显示也不能提交。读取失败在工作台提示。重复提交同一决定，可以读回原有选择。

## Invariants

按请求和项目 ID 匹配。一次请求最多新增一个项目。来源版本取确认时请求中的作品版本。

## Data impact

本机素材根只新增待选记录及确认决定，安装版使用现有项目与选择日志保存结果。

## Permissions

本机 Studio 同源写入保持原有身份和请求校验。设备使用已有配对和策划台确认入口。

## Performance and reliability

工作台自动更新待选请求，保留表单编辑；重复提交与设备重启沿用原有决定。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 同名按 ID 选择，重复新建、过期、文件损坏和安装版确认均按预期处理 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/e2e | 两种宽度的首页和项目页版本一致，点击确认后卡消失，读取失败可见 | E2E | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 核对待选、确认与来源版本 | acceptance/human/2026-W48/2026-11-26-Pho_R23-studio-project-pick/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_p1a_studio_project_pick.py | 7dc9902567fc5460412fea7ce0caba71ada307cfa73d56115b75b8c10bf9a697 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 运行 Studio HTTP 与安装版 watch 测试 | tests/test_p1a_studio_project_pick.py | Automatic | Yes |
| AC-02 | 打开真实 Studio，截图并点击确认、打开项目 | agents-results/2026-11-26/preview-ui-p/acceptance/machine/e2e | Automatic | Yes |
| H-01 | 用策划台作品与电脑工作台实地核对 | acceptance/human/2026-W48/2026-11-26-Pho_R23-studio-project-pick/checklist.md#h-01 | Human | No |

## Exploratory testing

对照长项目名在 390 宽下的折行，以及来源条切换做法后是否保留。

## Production monitoring and rollback

需要回退时回退本次源码提交。

## Risks and open decisions

安装版 watch 配合策划台服务替身验证。真实账号和设备由人工抽验。作品标题和 Brief 在总控的后续任务内。
