# Acceptance Contract: 2026-10-26-R280-photo-studio-light

- Task ID: 2026-10-26-R280-photo-studio-light
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27R280交付授权、已批准浅色设计及追加旧任务溢出修复；原H两项不变，不追称实现前已有合同，不代表人工PASS
- Request source: acceptance/requests/2026-W44/2026-10-26-R280-photo-studio-light/request.json; docs/tasks/R280-studio-light/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.light-theme, studio.light-media-isolation
- AC budget: 2
- Baseline identity: e26ec2f19d5e1136577873beb932f537a2a0037f，见baseline.json
- Product Context refs: agents-results/2026-10-27/R280-studio-light/acceptance-context.json
- Role Context refs: agents-results/2026-10-27/R280-studio-light/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-27/R280-studio-light/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-27/R280-studio-light/acceptance-context.json
- Visual Contract refs: agents-results/2026-10-27/R280-studio-light/visual-contract.json; docs/tasks/R280-studio-light/design/index.html
- UI Change declaration: agents-results/2026-10-27/R280-studio-light/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R280-photo-studio-light

## User and scenario

本机创作者依次阅读Studio各入口及作品三分页、单镜详情。

## Problem

整体深色界面过暗，需要浅色阅读面，视频画面应保留原样。

## Expected outcome

原H-01/H-02不变：浅底、清楚文字、青底白字主操作，媒体区域保持；追加批准的旧任务说明列不撑宽。

## Non-goals

不加主题开关，不改上游中台；本线程不改产品/测试/docs或用户状态。

## Normal path

Given 原本机作品与内容；When 打开各页和第02镜；Then 使用批准浅色令牌，媒体画布独立深色。

## Exception paths

错误底说明色使用更强文字令牌达到阈值；空态沿用原文，不注入数据。旧长文本允许既有省略，不扩大页面。

## Invariants

媒体文件不改；文案、DOM、字号、间距不变，只有另批准的旧预览说明列约束；未自签。

## Data impact

纯主题与布局约束，不修改作品、素材或任务。

## Permissions

本地角色与权限沿用原应用；验收只由用户签署。

## Performance and reliability

不新增请求、轮询或生成链路；门禁覆盖原交互和真实旧任务两宽横向边界。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 获批浅色令牌与字面量、正文4.5和小字3对比度、媒体表面隔离 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/e2e | 原五代前端交互合同保留，真实旧任务1440/960无整页溢出、长元数据受列宽约束 | E2E | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 各页浅色清晰 | acceptance/human/2026-W44/2026-10-26-R280-photo-studio-light/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 作品分页和媒体保色 | acceptance/human/2026-W44/2026-10-26-R280-photo-studio-light/checklist.md#h-02 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r280_light.py | e98f6199f0f0a897e3a94fa53fa57d5b70b369225e2803e67259e1e1ffa585ef | AC-01, AC-02 |
| scripts/direct_video/rescript_frontend_gate.mjs | 91f3d8d20aba8db5466050c62295214b358921c68e1e8a8c4b25cbc6c680d1cc | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 令牌回归和原前端门禁 | tests/test_r280_light.py; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-02 | 令牌回归和原前端门禁 | tests/test_r280_light.py; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| H-01 | 原两项用户验收 | acceptance/human/2026-W44/2026-10-26-R280-photo-studio-light/checklist.md#h-01 | Human | Yes |
| H-02 | 原两项用户验收 | acceptance/human/2026-W44/2026-10-26-R280-photo-studio-light/checklist.md#h-02 | Human | Yes |

## Exploratory testing

仓库外~/.photo-content-os/evidence/R280-studio-light/最终19图及gallery逐文件复核；旧溢出图仅备份，不沿用为最终视觉结论。

## Production monitoring and rollback

8769由总控从e26ec2f导出运行，本线程不部署、停启或操作用户任务。

## Risks and open decisions

两个人工项PENDING；检查过截图不是人工PASS。旧任务溢出修复是用户追加授权，原只换颜色标准之外的范围如实保留。无test_r280_*.mjs，执行现有五代Node及R280 Python，不补造测试。文档同步、outline、历史全量及严格实体截图归档差异另列；不跑全量。
