# Acceptance Contract: 2026-10-26-R276-photo-direct-video-opus

- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户交付准备指令要求沿用需求卡 H-01、H-02、H-03；前三段及前端 F1/F2 已由总控通过，本合同不增加或放宽行为标准
- Request source: acceptance/requests/2026-W44/2026-10-26-R276-photo-direct-video-opus/request.json; docs/tasks/R276-direct-video-opus/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.direct-generation, studio.direct-output, studio.direct-single-rewrite
- AC budget: 3
- Baseline identity: d095d101c445bb6a349208ce6c5af8be3afbf10c，冻结 base/head/tree 见 baseline.json
- Product Context refs: agents-results/2026-10-26/R276-direct-video-opus/acceptance-context.json
- Role Context refs: agents-results/2026-10-26/R276-direct-video-opus/acceptance-context.json
- Resolved Surface Contract refs: agents-results/2026-10-26/R276-direct-video-opus/resolved-surface-contract.json
- Screen Contract ref: agents-results/2026-10-26/R276-direct-video-opus/acceptance-context.json
- Visual Contract refs: docs/tasks/R276-direct-video-opus/design/contract.json; docs/tasks/R276-direct-video-opus/design/direct.html
- UI Change declaration: agents-results/2026-10-26/R276-direct-video-opus/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus

## User and scenario

本机创作者进入作品的「一键直出」，按一行一镜的口播稿生成动画；人判断画面表达、口播同步与第三镜改后观感。

## Problem

需要从口播稿直接得到逐镜动画和可播放成片，并能单独修一镜；不能将后台更新时间冒充出片时间。

## Expected outcome

原样满足需求卡三项标准：七镜十五分钟内写好并逐镜出现关键帧；配音合成后竖屏播放并对齐；单镜重写不影响其他六镜。固定使用 Opus 与本机已有渲染器。

## Non-goals

不改上游生成界面，不生成配音，不烧字幕，不引入 R277 的单镜详情新交互；本交付任务不修改产品代码、不操作用户 Studio、不推送。

## Normal path

Given 已进入作品并准备七句口播；When 点生成，全部写好后上传配音并合成；Then 看到设计、逐镜关键帧和可播放的竖屏成片。When 仅改第三镜；Then 其他镜代码、海报字节、writtenAt 和 posterRevision 不变。

## Exception paths

调用失败和超时如实显示；自查错误最多自动重写一次，提醒不触发重写；中断或失败可空意见重试，其他状态限制一至二百字；缺配音可出明确标注的无声预览；合成失败保留检查结果且合成时间为空。拒绝跨作品访问、非法输入、并发重复操作、缺令牌及错误来源。

## Invariants

H-03 的受保护证据只有后端不变性测试与 REPORT-B 真跑证据；不绑定前端详情 DOM 测试，避免把 R277 的详情替换误当作本卡语义变化。未记录的历史合成时间为空；不回退 updatedAt。原始媒体不入仓库，不改用户真实状态和人工结果。

## Data impact

单镜代码、检查、海报和任务状态位于本机独立任务目录；测试使用临时目录。配音后会撤下待更新的成片但保留最近成功时间；单镜意见重写、合成失败清空时间。交付只追加验收材料。

## Permissions

本机创作者使用现有令牌和来源校验访问任务；模型隔离工具与用户设置。只有真实用户能签署人工验收，机器结果不构成人工通过。

## Performance and reliability

H-01 从生成到七镜写好不超过十五分钟；B2 实跑 495.902 秒，F2 新七镜约八分二十六秒。写镜并发最多三，单次模型默认三百秒。合成严格检查帧数、黑帧与音画时长；比例分配不是逐字对齐保证。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 按行建任务、设计与逐镜写渲、自查重试、失败恢复及接口安全与合同一致 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/e2e | 配音或无声合成、严格成片检查、正确合成时间与批准页面状态可用 | E2E | Automatic | Yes |
| AC-03 | behavior | H-03 | machine/integration-contract | 后端只重写重渲第三镜，其他镜代码及海报字节、写好时间和海报版本不变 | Integration | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 七句生成逐镜画面 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 配音成片播放和同步观感 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 第三镜放大且其他镜不变 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r276_direct_video.py | e14bb66d4425c469a6fe820278e508e411a10f3502cfccf9bfeca1ed44bca57e | AC-01, AC-02, AC-03 |
| tests/test_r276_direct_api.py | 94b03c8a331ed3342e395800d34e6fac579c5672898af660eeca16db2f37154a | AC-01, AC-02 |
| tests/test_r276_direct_media.py | d74658695d78ebc24f9869c88adb938c510517129d4ba655322115bad5eaec9e | AC-01, AC-02 |
| tests/test_r276_direct_c.py | 88fdd5e2a0f05e2459d527ce23984fe1fc6366f06de3aa48fcc095cbcd1b1d90 | AC-01, AC-02 |
| tests/test_r276_direct_d.py | fe7b1505535e7636404ba68d505358e7797d055e5d8ba2c4866afb4e4f39bed7 | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | R276 后端、接口、重试状态和本机渲染 | tests/test_r276_direct_video.py; tests/test_r276_direct_api.py; tests/test_r276_direct_c.py; tests/test_r276_direct_media.py | Automatic | Yes |
| AC-02 | R276 合成时钟、媒体测试和当前页头、状态合同、浏览器交互 | tests/test_r276_direct_d.py; tests/test_r276_direct_media.py; tests/test_r276_direct_frontend.mjs; scripts/direct_video/frontend_gate.mjs | Automatic | Yes |
| AC-03 | 后端单镜不变性和既有真实任务字节比对 | tests/test_r276_direct_video.py::test_rewrite_only_one_shot_and_invalidate_output; docs/tasks/R276-direct-video-opus/REPORT-B.md | Automatic | Yes |
| H-01 | 原样需求卡，七镜时间及图解观感 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-01 | Human | Yes |
| H-02 | 原样需求卡，七镜配音同步听感 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-02 | Human | Yes |
| H-03 | 原样需求卡，目标镜观感和其他镜保持 | acceptance/human/2026-W44/2026-10-26-R276-photo-direct-video-opus/checklist.md#h-03 | Human | Yes |

## Exploratory testing

已有 A/B/C/D 与 F1/F2 报告覆盖中断、重试、无声、读失败及窄屏；当前交付重跑确定性命令，不另触发真实模型或更改用户作品。

## Production monitoring and rollback

本任务不部署；8766 由总控维护。后续上线如调用或合成失败，停止新任务，由总控按已冻结提交回退，保留媒体与人工记录；不得在本交付任务重启用户服务。

## Risks and open decisions

H-01 至 H-03 保持未验收。B1 为十镜带声，B2 为七镜无声；它们不单独证明 H-02 的七镜配音同步，仍需用户按卡实际验收。ASR 失败使用明示比例分配，不宣称逐词对齐。C 的十七张构图提醒配额未满足已由总控知悉，本交付不改测量规则。全量测试既有九失败六错误与文档同步问题见 F2 汇报，不计作本次机器 PASS；旧卡 G16/G17 的真实阻塞照报，不搬证据或伪造新 PASS。
