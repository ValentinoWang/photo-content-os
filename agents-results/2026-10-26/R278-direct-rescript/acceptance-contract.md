# Acceptance Contract: 2026-10-26-R278-photo-direct-rescript

- Task ID: 2026-10-26-R278-photo-direct-rescript
- Contract version: 3
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27R282第二次交付准备授权，R282批准设计的交接分支和旧包兼容扩展共用门禁；只更新当前摘要/版本/来源，AC/H、保护路径和阻塞判据不变；不代表人工PASS
- Request source: acceptance/requests/2026-W44/2026-10-26-R278-photo-direct-rescript/request.json; docs/tasks/R278-direct-rescript/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.direct-rescript, studio.direct-style-base, studio.direct-style-draft
- AC budget: 3
- Baseline identity: 6a430c5ecc2d0df4c88b5285bb29e8bfba3b62d3；本批输入见handoff-r282/
- Product Context refs: agents-results/2026-10-26/R278-direct-rescript/acceptance-context.json
- Role Context refs: agents-results/2026-10-26/R278-direct-rescript/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-26/R278-direct-rescript/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-26/R278-direct-rescript/acceptance-context.json
- Visual Contract refs: docs/tasks/R278-direct-rescript/design/contract.json; docs/tasks/R278-direct-rescript/design/index.html
- UI Change declaration: agents-results/2026-10-26/R278-direct-rescript/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript

## User and scenario

本机创作者打开已有脚本直出作品，回到分镜表修改并重新生成；首次生成先选成片风格或用第一镜样张定好风格。用户2026-10-27已决定：改分镜页当前画面不标「这一版」；画面说明为空时显示「写这一镜画什么（可不填）」，其他空列仍为「—」。

## Problem

已有结果缺少回到分镜的入口；风格不能只靠可选说明，必须显式选定来源并能看样张后再决定。

## Expected outcome

原样验收需求卡三项：已有七镜和当前风格预填；修改台词、画面和风格意见后新建七镜；从头定风格时先生成、修改、选用第一镜样张，再复用其设计和首镜。

## Non-goals

不做历史切换、外部风格导入、音乐音效合成、中台自动填入和九种风格库。本次只准备交付验收物，不改产品、测试、设计稿，不触发新付费生成，不推送或重启用户服务。

## Normal path

Given 已生成七镜且任务停止；When 点「改分镜脚本」；Then 进入已预填六列表和当前风格。When 修改台词、画面及风格意见并生成；Then 新建任务且旧结果留本机。Given 首次作品；When 定风格、修改样张、选用并生成；Then 复用样张设计和匹配首镜。

## Exception paths

写镜、合成、看图或核改中锁定入口；读取失败不显示可执行入口。风格缺失、来源不可用、样张未就绪或并发修改被拒绝；失败保留输入并提供重试；离页停止轮询。请求沿用来源和令牌校验，不跨作品读写或泄露本机路径。

## Invariants

旧任务文件保留；画面、字幕、景别运镜参与写镜；音乐音效只保存。沿用不改不再定设计；有意见只调整原设计。首镜匹配时字节复用，不匹配则重写。媒体外置，人工三项保持待验。

## Data impact

新任务、样张和各版本片段在本机独立目录；分镜字段随任务保存。测试使用临时目录与既有只读状态克隆，不写用户运行中的作品。

## Permissions

沿用本机 Studio 来源及令牌检查。人工通过只能由真实用户签署，本任务不创建人工结果。

## Performance and reliability

H-03卡上三分钟标准原字保留。实测首次215.621秒（约3分36秒），修改168.813秒（约2分49秒）；用户2026-10-27看过时长后原话「这个没事 大概差不多就行」。这里只记录用户对近似时长的解释，不把它当成人工PASS，也不宣称实测小于三分钟。新机器证据是确定性测试和夹具，不证明新真实模型时延。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/e2e | 返回入口、预填分镜、当前风格、编辑运算、片段与放大及锁定状态 | E2E | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/integration-contract | 保存四列并参与写镜、调整风格、新建生成与来源快照，保留旧任务 | Integration | Automatic | Yes |
| AC-03 | behavior | H-03 | machine/integration-contract | 样张创建修改及选用条件、风格继承与首镜复用、片段版本隔离、安全恢复 | Integration | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 返回七镜分镜和当前风格 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 修改台词画面并调整强调色 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 从头定样张、修改并选用生成 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r278_clips.py | 5fd045560a32e2768d33527ac54331542eea1135ad2a967145134f2a94b343cf | AC-01, AC-02, AC-03 |
| tests/test_r278_direct_frontend.py | 5353332357e17696a420e77e2df0a7cdff88c3df2810857db24f29185a01ec83 | AC-01, AC-02, AC-03 |
| tests/test_r278_style_base.py | 329e483a28fa46c3ff465e0b79602b6ae07e8c03368a4ee77c46f1d14125e21f | AC-01, AC-02, AC-03 |
| tests/test_r278_direct_rescript.mjs | 98468f866da84d49c0d9ec01e457b166128434f79895a4d912333c99bf0f23b0 | AC-01, AC-02, AC-03 |
| scripts/direct_video/rescript_frontend_gate.mjs | a43315ea3e46506d1fb438d42abcc362cfdc8f36070e386b27ad33088c22c055 | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | R278 专项与浏览器交互合同 | tests/test_r278_clips.py; tests/test_r278_direct_frontend.py; tests/test_r278_style_base.py; tests/test_r278_direct_rescript.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-02 | R278 专项与浏览器交互合同 | tests/test_r278_clips.py; tests/test_r278_direct_frontend.py; tests/test_r278_style_base.py; tests/test_r278_direct_rescript.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| AC-03 | R278 专项与浏览器交互合同 | tests/test_r278_clips.py; tests/test_r278_direct_frontend.py; tests/test_r278_style_base.py; tests/test_r278_direct_rescript.mjs; scripts/direct_video/rescript_frontend_gate.mjs | Automatic | Yes |
| H-01 | 需求原文、真实样张及用户实测 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-01; docs/tasks/R278-direct-rescript/REPORT-A.md; docs/tasks/R278-direct-rescript/REPORT-F1.md | Human | Yes |
| H-02 | 需求原文、真实样张及用户实测 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-02; docs/tasks/R278-direct-rescript/REPORT-A.md; docs/tasks/R278-direct-rescript/REPORT-F1.md | Human | Yes |
| H-03 | 需求原文、真实样张及用户实测 | acceptance/human/2026-W44/2026-10-26-R278-photo-direct-rescript/checklist.md#h-03; docs/tasks/R278-direct-rescript/REPORT-A.md; docs/tasks/R278-direct-rescript/REPORT-F1.md | Human | Yes |

## Exploratory testing

既有真实样张两版及前端截图在本机 Photo Content OS 证据文件夹 R278-direct-rescript 内：live-5z2bi1gp/inspected-artifacts 的 initial/revised 关键帧与片段；frontend/gallery.html 为前端截图索引。只记录位置，不把图片视频复制入仓库。真实服务层生成不等于真实 HTTP 用户流程。

## Production monitoring and rollback

本次不部署。8769 由总控维持，H-01/H-02 用「断更一年，我拆了四句话」，H-03 用「断更一年，我的担心准吗」。出现失败由总控保留结果后处理，禁止本线程停止服务或改实现。

## Risks and open decisions

H-01 至 H-03 原样待用户验收；用户已接受实测时长大致接近，原话及实测见 Performance and reliability，不代签PASS。两版存在非阻塞 number_unspoken 的 0% 提醒，未隐去。真实强调色局部修改、七镜从头写和样张视觉判断仍待人工。沿用既有严格视觉声明，run 内实体截图与媒体外置的既有冲突如实报，不伪造视觉归档或全站结论。需求卡待确认但 confirmation_required=false；本次授权交付装配不等于代替用户确认需求。
