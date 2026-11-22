# Acceptance Contract: 2026-10-19-R207-photo-edit-tools-in-repo

- Task ID: 2026-10-19-R207-photo-edit-tools-in-repo
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 用户
- Approval evidence: 用户要求按 docs/tasks/R207-edit-tools-in-repo/TASK.md 和既有需求卡完成全部工作；不代表人工验收通过。
- Request source: acceptance/requests/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.edit-tools-runtime
- AC budget: 2
- Baseline identity: c1b4db387e3c0c0aa6cabdb1af283a8e1d0f0594
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo

## User and scenario

Photo 操作者安装剪辑工具并在现有 Studio 项目生成候选；页面语义和布局不变。

## Problem

默认运行时依赖本机桌面目录和另一个仓库，干净检出不能复现。

## Expected outcome

按锁定版本安装到本仓库，缺失或损坏明确报告，所选后端独立执行。

## Non-goals

不修改桌面收藏、素材、系统应用、真实剪映草稿和其他会话的文件。

## Normal path

安装 → 环境检查 → 明确选定的后端生成可播放候选。重复安装保持锁定版本。

## Exception paths

缺失、不可读、版本或提交漂移明确报错并提示安装命令；安装失败不换版本或后端。

## Invariants

共享 Chromium 锁目录和 MEDIA_CHROMIUM 变量不变；第三方源码及依赖不提交。

## Data impact

仅创建本检出的忽略目录和任务证据，不读取或改变真实素材。

## Permissions

沿用既有本机操作权限；不改项目状态、角色或审批。

## Performance and reliability

浏览器共用并发槽，默认最多两个；合成短片验证后清理本任务进程。

## Acceptance criteria

| ID | Class | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | machine/integration-contract | 仓库工具版本可验证，缺失和漂移失败，默认寻址独立于 HOME | Integration | Automatic | Yes |
| AC-02 | behavior | machine/local-runtime | 两个明确选择的后端用仓库工具完成合成短片渲染，无替代后端 | Runtime | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 安装及环境检查能按说明完成 | acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/checklist.md#h-01 | 产品负责人 | No |
| H-02 | 现有项目能生成可播放候选 | acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/checklist.md#h-02 | 产品负责人 | No |

用户已要求自行推送；本卡保留人工复核入口，不作为额外推送审批。

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_edit_tools_runtime.py | 00bda2a8e131eb1d5ef62ae0554a92d06b620d1cbef577d2114d3de081524826 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | Integration test | tests/test_edit_tools_runtime.py | Automatic | Yes |
| AC-02 | Local runtime render | evidence/2026-10-19/R207-edit-tools-in-repo/smoke.json | Automatic | Yes |
| H-01 | 操作者复核 | acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/checklist.md#h-01 | Human | No |
| H-02 | 产品路径复核 | acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/checklist.md#h-02 | Human | No |

## Exploratory testing

独立临时 HOME、环境覆盖、重复安装和依赖漂移。

## Production monitoring and rollback

此次仅本地验证，无生产部署；回滚本任务提交即可恢复代码，工具目录保留供排查。

## Risks and open decisions

机器冒烟不代表用户项目和人工检查通过；全套测试现有 FFmpeg 缺少 drawtext 失败另行记录。
