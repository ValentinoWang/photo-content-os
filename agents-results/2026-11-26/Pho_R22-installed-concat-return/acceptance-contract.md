# Acceptance Contract: 2026-11-26-Pho_R22-installed-concat-return

- Task ID: 2026-11-26-Pho_R22-installed-concat-return
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 任务单 TASK-U19-P.md 和总控裁定第 1、4 项，以及本轮明确指定回传按任务绑定和固定版本验证。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R22-installed-concat-return/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.installed-concat-return
- AC budget: 1
- Baseline identity: ba41bdfdf3294f2b5fd1c2a7dc52de64c85e6f20
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R22-installed-concat-return

## User and scenario

制作人员在已确认的本地项目中用 Concat 精修，设备负责回传检查通过的成片。

## Problem

制作台创建的工程和经过检查的成片缺少同一任务上的持久关联，设备重启后无法续传。

## Expected outcome

首次打开精修后等待回传，设备跨租约和重启沿用同一份候选，作品只有一条可播放预览。

## Non-goals

正式界面改版、真实素材和真人精修演练，或调用付费服务。

## Normal path

设备交接已选项目，制作台创建并打开工程，操作者完成精修并回传。经过核对的候选由设备续传并由作品服务确认。

## Exception paths

打不开工程、工程仍被占用或导出未通过检查时不给待上传候选。项目身份、版本或摘要不符时拒绝沿用。

## Invariants

已打开和已建两项证据同时存在才结束原租约。回传固定同一任务的候选内容和预览字节，重复请求不增加候选。

## Data impact

打开证据与检查通过的候选保存在任务的本机运行目录。失败的成片保留供重试。

## Permissions

回传只使用已确认项目的任务身份。服务端签发的有效租约控制作品候选的写入。

## Performance and reliability

重启或续租不触发再次渲染，网络失败可以重试。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 用固定提交的安装版和替身通过真实载荷接线，首次建工程和打开，接收验证通过的导出，过期重启后不重新渲染并读回唯一 480p 候选，同时拒绝占用、打不开、错配和文件变化 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看精修试跑记录 | acceptance/human/2026-W48/2026-11-26-Pho_R22-installed-concat-return/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_p1a_installed_concat_return.py | ea7f0201a63aea0fc7b05a69b2112c234713b150e0e31b2b944dc27b370aea3f | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 运行安装版 Concat 精修续传测试 | tests/test_p1a_installed_concat_return.py | Automatic | Yes |
| H-01 | 核对试跑记录 | acceptance/human/2026-W48/2026-11-26-Pho_R22-installed-concat-return/checklist.md#h-01 | Human | No |

## Exploratory testing

无。

## Production monitoring and rollback

需要回退时回退本次源码提交。

## Risks and open decisions

安装版替身闭环不覆盖真人 Concat 和生产素材，按总控裁定留待后续实机验收。
