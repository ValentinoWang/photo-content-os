# Acceptance Run: 20261126T163221Z-devbox-scope-a331c7

- Run ID: 20261126T163221Z-devbox-scope-a331c7
- Task ID: 2026-11-26-Pho_R23-studio-project-pick
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/preview-ui-p/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: fdfecccb8eab944166133f8d794d821739b2eadef791e68250a4c60dde9f1dd1
- Source identity: d480294e571831aaceb88933b149fcc4ee97f2e6
- Runtime identity: photo-dev-scoped-regression
- Executor or reviewer: codex
- Started at: 2026-11-26T16:33:03Z
- Completed at: 2026-11-26T16:33:17Z
- Evidence directory: evidence/

## Scope

G7 对照旧卡的音乐分析、动效配方和剪辑工具。比较这些能力的源码及共用 Studio 路由，再跑对应测试。

## Procedure

对照基线与任务提交的音乐库、节拍图、配方库、编辑后端和工具安装文件。查看 Studio 路由差异，新增写入仅限选项目。运行音乐分析、节拍分段、OpenMotion 导入及离线预览、配方路由、工具路径和剪辑后端接口测试。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/regression.txt | 与选择功能共用的 Studio 范围有补充回归证据 |

## Findings

Python 143 项通过，1 项跳过，退出 0。对应能力拥有者源码没有差异。尝试的旧浏览器脚本另报环境问题，其中一项要求系统 Chrome 发行版，另一项要求 PW_REQ 和隔离服务地址。本次补充证据取 Python 与源码差异结果。新界面浏览器验证另见 AC-02。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/regression.txt | 558c3d4d51222b2e24e718e21cf4ca14202658927053aaf53092dad139b552aa | 受影响范围核对 |
| evidence/shared-routes.diff | 4bc13195ddc021206abca7a2a6d5f8686ed06160f2ca1bd174bf4785000ee539 | 受影响范围核对 |
| evidence/source-scope.txt | c7c97e7e2933dfb448a01393587a2c01dfb75e8413daa0ec8f2a72e7a7d50d7e | 受影响范围核对 |
