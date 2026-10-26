# Acceptance Contract: 2026-10-26-R283-photo-direct-style-library

- Task ID: 2026-10-26-R283-photo-direct-style-library
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27第四次交付指令及现行需求卡，原样装配三项；不代表人工PASS，不追称实现前已存在
- Request source: acceptance/requests/2026-W44/2026-10-26-R283-photo-direct-style-library/request.json; docs/tasks/R283-direct-style-library/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.direct-style-library, studio.direct-library-generation, studio.direct-library-adjustment
- AC budget: 3
- Baseline identity: 7d0ab0046ef286a5bac8c468d86ebc10ccf557cd，冻结基准见baseline.json
- Product Context refs: agents-results/2026-10-26/R283-direct-style-library/acceptance-context.json
- Role Context refs: agents-results/2026-10-26/R283-direct-style-library/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-26/R283-direct-style-library/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-26/R283-direct-style-library/acceptance-context.json
- Visual Contract refs: docs/tasks/R278-direct-rescript/design/contract.json; docs/tasks/R278-direct-rescript/design/index.html
- UI Change declaration: agents-results/2026-10-26/R283-direct-style-library/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library

## User and scenario

本机创作者在未生成过的作品选择九种现成风格，比较同台词样张，直接生成或只改底色后生成。

## Problem

只有本机成片和从头定风格时，新用户缺少可直接采用、能看到真实样张的固定风格。

## Expected outcome

按原需求H-01至H-03验九卡及白板预览、沿用白板不重新定设计、修改水墨底色保留其他设计和画法。

## Non-goals

不收三维和竖屏手机两类，不做配乐音效、用户增删库。交付线程只改验收物，不改产品、测试、docs，不触发付费模型或用户任务。

## Normal path

Given 有台词；When 选白板库卡；Then 单选、预览及生成载荷对应。When 不填调整生成；Then 原设计复制且写镜携带该画法和样张。When 选水墨并只改底色；Then 按原设计和单句意见调整，其他字段保留。

## Exception paths

缺文件、非法字段、坏JSON或库外符号链接独立排除并日志；未知来源404，非法Range416；无选择时不能生成。失败不冒充成功或静默换风格。

## Invariants

库顺序固定九种；只读范围有界、不缓存旧文件、不写盘。单选跨两组共享状态，媒体切换离页释放。不改时零定设计调用，调整正常一次，任务冻结样张及画法，重启后单镜重写保持。

## Data impact

库数据只读；创建任务复制风格和样张上下文，不改来源库。18个合成样张已由总控逐文件登记放行，本线程不改允许列表或媒体。

## Permissions

沿用本机Studio令牌和来源校验、路径隐私；只有人亲自签署人工验收。

## Performance and reliability

列表读取只随索引范围增长；非法单项独立隔离。模型语义和七镜观感仍由原卡人工检验，不把夹具调用次数当成新付费模型生成。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/e2e | 九卡单选、媒体生命周期、真实只读接口及Range、无选择禁用与库生成载荷 | E2E | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/integration-contract | 原设计复制、零定设计调用、每镜和重写注入画法与样张、任务快照及真实九种库合规 | Integration | Automatic | Yes |
| AC-03 | behavior | H-03 | machine/integration-contract | 单句调整原设计，保留非目标字段及完整禁用项、来源投影、失败边界和隐私 | Integration | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 九卡与白板样张选择 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 白板七镜风格一致 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 水墨只改底色 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r283_frontend.py | ef550d5c94ac83bef05058906c9c756db4ec010e2f030ae60899e7fbeed29f1c | AC-01, AC-02, AC-03 |
| tests/test_r283_style_library.py | 41db92d1130c2547a28fdc45c42042b4e24bf90c84a2d486d0ac0c1395f7dfcd | AC-01, AC-02, AC-03 |
| tests/test_r283_frontend.mjs | 78aa1ea9717ea59ecc3a6e3aafac23719b8e9638e8d39f7d67fddcebbb1fb2ca | AC-01, AC-02, AC-03 |
| scripts/direct_video/rescript_frontend_gate.mjs | a3e655dedebd99533545aa6e5377e4ad313bdb0c5d8d19b74f5e4e48b5ceb9ed | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | R283接口、设计逻辑与挂载交互 | tests/test_r283_frontend.py; tests/test_r283_style_library.py; tests/test_r283_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-02 | R283接口、设计逻辑与挂载交互 | tests/test_r283_frontend.py; tests/test_r283_style_library.py; tests/test_r283_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-03 | R283接口、设计逻辑与挂载交互 | tests/test_r283_frontend.py; tests/test_r283_style_library.py; tests/test_r283_frontend.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| H-01 | 原样需求与用户七镜实测 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-01 | Human | Yes |
| H-02 | 原样需求与用户七镜实测 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-02 | Human | Yes |
| H-03 | 原样需求与用户七镜实测 | acceptance/human/2026-W44/2026-10-26-R283-photo-direct-style-library/checklist.md#h-03 | Human | Yes |

## Exploratory testing

样张媒体、六帧联系表及末帧在仓库外 ~/.photo-content-os/evidence/R283-direct-style-library/，逐种记录见REPORT-S；前端16张完整页及图库在同根frontend/，此前逐张审阅见REPORT-F。本线程核验哈希并抽看，不把历史样张当作本轮新模型七镜。

## Production monitoring and rollback

8769由总控从7d0ab00导出副本运行，状态只读；本线程不停止、重启、部署或操作用户任务。失败时由总控保留状态和媒体后处理。

## Risks and open decisions

三项人工PENDING。H-02七镜画法、H-03模型只改底色仍须用户实测；不以假模型和接口请求证明视觉语义。全量测试按R283任务预算不重跑，既有文档同步/outline与历史全量红灯单列；严格视觉实体图归档与媒体外置的既有差异不伪造解决。
