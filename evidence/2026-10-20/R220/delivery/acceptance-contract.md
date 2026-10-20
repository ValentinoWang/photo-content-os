# Acceptance Contract: 2026-10-20-R220-photo-studio-ia-preview

- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户第 3 轮指令「第 2 轮通过；做完 4 处小修并自核截图，然后按收尾顺序完成提交、验收卡、check-delivery、推送和 finish」；需求卡 H-01 至 H-03 原样递交
- Request source: acceptance/requests/2026-W43/2026-10-20-R220-photo-studio-ia-preview/request.json; docs/tasks/R220-studio-ia-preview/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: studio.navigation, studio.shot-review, studio.media-preview
- AC budget: 3
- Baseline identity: origin/main at delivery freeze; approved TASK round 3
- Product Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Role Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Resolved Surface Contract refs: docs/tasks/R220-studio-ia-preview/resolved-surface-contract.json
- Screen Contract ref: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Visual Contract refs: docs/tasks/R220-studio-ia-preview/design-contract.json; docs/tasks/R220-studio-ia-preview/TASK.md
- UI Change declaration: docs/tasks/R220-studio-ia-preview/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview

## User and scenario

本机创作者从 Studio 进入项目、作品、挑镜头、素材库、音乐库与设置；私有素材保留在本机。

## Problem

已有导航、预览和状态阅读不一致，旧样式串扰；已由 Claude 认可第 2 轮，收尾修正封面与三处小排版。

## Expected outcome

六项导航均可到达；作品正确分组，精选可连续播放并保存决定；成片和音乐可播放，状态清楚。

## Non-goals

配乐卡点与自动出草稿、抖音导入、素材库新登记流程、模型新建表单；不修改现有整理算法。

## Normal path

Given 本机作品与派生媒体；When 导航、预览或修改镜头结论；Then 只读编号媒体，以 CAS 保存用户决定，确认后进入下一阶段入口。

## Exception paths

读取失败不显示为空；路径穿越与未知编号 404；部分结果不可确认；停止可续跑；会员、重复和导入失败保留明确信息。

## Invariants

原片不经 HTTP API 返回；不靠修改真实决定制作截图；模型任务不可重复启动；私有设计稿、截图和绝对运行路径不进入本轮机器证据提交。

## Data impact

派生预览、封面与波形缓存；独立决定文件原子写入并作废旧确认；不改变原始媒体和实际剪映草稿。

## Permissions

仅本机创作者和回环接口；写请求校验 CSRF；人工通过由用户签署。

## Performance and reliability

媒体 Range 分块流式读取；证据缓存与目录锁；异步旧响应不覆盖新导航；封面失败不替换已有缓存。

## Acceptance criteria

| ID | Class | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | machine/integration-contract | 分组、决定合并、CAS 确认作废、续跑和原片隔离正确 | Integration | Automatic | Yes |
| AC-02 | behavior | machine/e2e | 六项导航、真实派生镜头成片音乐播放、状态及四处小修可观察 | E2E | Automatic | Yes |
| AC-03 | behavior | visual-fidelity | 29 状态四宽契约与数字无漂移；最后修改桌面手机截图已核对 | Visual | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 导航和设置入口 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 精选连播和修改保存 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 成片和音乐试听体验 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_studio_review.py | aa1f02edf4592017801af3238a9867596c9d86c01ced504aa93a30d5d70f548d | AC-01, AC-02, AC-03 |
| tests/test_r220_number_formulas.py | dae2208fea72e2454c7acbaeef496c53505eef73f85fa1f9219754a481859006 | AC-01, AC-02, AC-03 |
| tests/test_r220_number_formulas.mjs | a3666ecefe1226f47f457caf845d79be557ea9ed1fedadd660d4e5787dcbdee4 | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 后端与派生媒体合同 | tests/test_studio_review.py | Automatic | Yes |
| AC-02 | 浏览器关键路径 | scripts/verify_r220_browser.mjs | Automatic | Yes |
| AC-03 | 契约、公式与截图矩阵 | scripts/capture_r220.mjs; tests/test_r220_number_formulas.py | Automatic | Yes |
| H-01 | 产品体验 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-01 | Human | Yes |
| H-02 | 产品体验 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-02 | Human | Yes |
| H-03 | 产品体验 | acceptance/human/2026-W43/2026-10-20-R220-photo-studio-ia-preview/checklist.md#h-03 | Human | Yes |

## Exploratory testing

真实最差首屏、照片空态、异常停止、手机分页、长检视栏；外部平台导入用假网络，不重新取真实平台数据。

## Production monitoring and rollback

无外部服务部署；本机启动失败查日志并停止；必要时回退软件提交，保留用户原片和决定。不自动选择替代模型或剪辑工具。

## Risks and open decisions

局部机器 PASS 不覆盖既有全量字幕/视频/文档同步失败。素材库登记、预计耗时、模型表单等沿用 REPORT-2 的明确限制；不冒充人工通过。私有截图只引用仓库外归档和散列。推送必须先解决旧 R208 未发布历史中的私人图像，之后遵守 check-delivery 策略。
