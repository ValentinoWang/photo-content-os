# Acceptance Contract: 2026-10-26-R277-photo-shot-visual-revision

- Task ID: 2026-10-26-R277-photo-shot-visual-revision
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 已确认需求卡中的真实确认「可以 请实现」及用户第二段交付指令；本合同仅据现行标准装配，不追称实现前已存在
- Request source: acceptance/requests/2026-W44/2026-10-26-R277-photo-shot-visual-revision/request.json; docs/tasks/R277-shot-visual-revision/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.direct-shot-revision, studio.direct-shot-versions, studio.direct-revision-log
- AC budget: 3
- Baseline identity: 277cd1c6ca730f77bd653a31a8b7ca22ea90277b，冻结 base/head/tree 见 baseline.json
- Product Context refs: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-context.json
- Role Context refs: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-26/R277-shot-visual-revision/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-context.json
- Visual Contract refs: docs/tasks/R277-shot-visual-revision/design/contract.json; docs/tasks/R277-shot-visual-revision/design/revise.html
- UI Change declaration: agents-results/2026-10-26/R277-shot-visual-revision/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision

## User and scenario

本机创作者在作品「断更一年，我拆了四句话」脚本直出页选中一镜，点画面选改法、比较版本并积累样例和规则。

## Problem

笼统意见不能定位画面问题，也不能逐条比较要求是否做到；画面经验需要有可追溯且需人工采用的积累入口。

## Expected outcome

按现行需求卡 H-01 至 H-03 原文验收选块修改、两版核对、退回、样例和问题记录；其他六镜不变，未采用规则前规则不变。

## Non-goals

不承接 R276 生成、配音、合成流程；不重写全片设计，不改中台界面。本任务不改产品、测试或 docs，不部署、不推送。

## Normal path

Given 已选中一镜；When 点画面块、选改法并补充说明；Then 只重写这一镜并显示两版和逐条核对。When 退回或存样例；Then 保留版本且独立保存样例。When 同类修改累计三次；Then 起草规则，人工采用才生效。

## Exception paths

旧任务未看图时先显式看图；看图、重写、核对和草稿失败如实显示并按允许状态重试。非法输入、越界路径、跨作品、错误版本、缺来源令牌或并发冲突被拒绝；恢复保留已渲染成功结果。

## Invariants

非目标镜代码、关键帧、写好时间不变；退回不删版本；样例独立复制且后续写镜参考；规则草稿未采用不改规则版本。媒体留仓库外，不代签人工 PASS。

## Data impact

单镜版本、热区、看图、样例和问题计数位于本机状态目录；采用前只存草稿；测试使用临时状态，不改真实作品。

## Permissions

沿用本机 Studio 令牌及来源校验；规则由人显式采用，人工验收只由真实用户签署。

## Performance and reliability

真实第 02 镜重写用时 160 秒；核对报告可明确记录没做到，不能把模型结果冒称必然成功；恢复保留成功渲染。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 热区、看图、选块意见限制、单镜重写不变性和逐条核对 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/integration-contract | 版本切换、样例独立复制和后续生成参考 | Integration | Automatic | Yes |
| AC-03 | behavior | H-03 | machine/e2e | 问题计数与三次阈值草稿、显式采用和批准的页面交互 | E2E | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 选块重写和两版核对 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 退回旧版并保存样例 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 问题记录和待采用草稿 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r277_api.py | 913d08ffa2854a09b4034073d84885733105d6d5b5a55ff6950e1a5e7441136e | AC-01, AC-02, AC-03 |
| tests/test_r277_boxes.py | ba9b91d7c481a2d06be284aae6d3f355ca721aec708c8fff0393ceca7d7ac93f | AC-01, AC-02, AC-03 |
| tests/test_r277_frontend.py | b7a78eb47417d11cd4e2388285e986ff724506f7be185f29063507ba62f55d3b | AC-01, AC-02, AC-03 |
| tests/test_r277_revisions.py | b5232e7d28a85a5dec1383d349bd3dda261a34521ee9e76497792cf67fea777c | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | R277 后端接口和浏览器夹具交互 | tests/test_r277_revisions.py; tests/test_r277_boxes.py; tests/test_r277_api.py; tests/test_r277_frontend.mjs; scripts/direct_video/revision_frontend_gate.mjs | Automatic | Yes |
| AC-02 | R277 后端接口和浏览器夹具交互 | tests/test_r277_revisions.py; tests/test_r277_boxes.py; tests/test_r277_api.py; tests/test_r277_frontend.mjs; scripts/direct_video/revision_frontend_gate.mjs | Automatic | Yes |
| AC-03 | R277 后端接口和浏览器夹具交互 | tests/test_r277_revisions.py; tests/test_r277_boxes.py; tests/test_r277_api.py; tests/test_r277_frontend.mjs; scripts/direct_video/revision_frontend_gate.mjs | Automatic | Yes |
| H-01 | 原样需求标准及真实任务报告 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-01; docs/tasks/R277-shot-visual-revision/REPORT-C.md | Human | Yes |
| H-02 | 原样需求标准及真实任务报告 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-02; docs/tasks/R277-shot-visual-revision/REPORT-C.md | Human | Yes |
| H-03 | 原样需求标准及真实任务报告 | acceptance/human/2026-W44/2026-10-26-R277-photo-shot-visual-revision/checklist.md#h-03; docs/tasks/R277-shot-visual-revision/REPORT-C.md | Human | Yes |

## Exploratory testing

既有 REPORT-A/B/C 记录模型真跑、恢复和标记避让；本次只从新源码重跑机器命令与夹具重放，不调用付费模型。

## Production monitoring and rollback

本任务不部署、不重启用户 Studio。推送后由总控另开运行 R277 的 Studio，失败时停止新任务并保留版本、媒体和人工记录。

## Risks and open decisions

真实依据为 REPORT-C.md 第 4 轮及此前真跑链路，任务 dv_0e184e961bd14ac084c67411；本机 Photo Content OS 证据文件夹 R277-shot-visual-revision 的 real-c4 等目录保留媒体和截图，不复制进仓库。

H-01：3 个橙点，重写 160 秒，3 条要求核对 3 条做到，其余 6 镜不变。原卡说点「约 25%」「约 50%」两根柱子，真实第 02 镜是「25%」「估计 50%」文字块；旧任务需先点「让 Opus 看一遍」才有橙点。差异如实披露，原卡不改。

H-02：显示「按字数估 20.8 秒 · 用第 1 版 · 共 2 版」，第 01 镜「♥ 已存为样例」。H-03：第 05 镜三次缩小变灰后有草稿，没点采用时 rulesRevision 仍为 0；额外第 05 镜操作为验证三次阈值。

REPORT-C 第 4 轮保留 390 宽真实对比的 1 号与单位「天」约 28.807px² 最小相交例外，交接 10 已由总控决定继续交付，不称零遮挡。严格视觉归档要求 run 内实体截图与媒体外置规则存在既有冲突。本次机器证据不代表新真模型全链路、全站、人工验收或 READY。
