# Acceptance Run: 20261126T162143Z-devbox-browser-753510

- Run ID: 20261126T162143Z-devbox-browser-753510
- Task ID: 2026-11-26-Pho_R23-studio-project-pick
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/preview-ui-p/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: fdfecccb8eab944166133f8d794d821739b2eadef791e68250a4c60dde9f1dd1
- Source identity: d480294e571831aaceb88933b149fcc4ee97f2e6
- Runtime identity: photo-dev-chromium-149.0.7827.55
- Executor or reviewer: codex
- Started at: 2026-11-26T16:21:43Z
- Completed at: 2026-11-26T16:21:49Z
- Evidence directory: evidence/

## Scope

真实 Studio 使用三条合成项目。逐张检查桌面和手机版待选、确认后项目页及读取失败。首页手机版实拍覆盖 390 × 1305 的完整页面。确认后进入脚本直出仍保留版本，独立项目没有来源条。

## Procedure

在隔离素材根启动真实 Studio。Chromium 检查视口、过期请求隐藏和默认标题。实际提交选择并打开项目核对作品版本。拍完退出 Chromium 和 Studio。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/screenshot-manifest.json | 退出码 0 |

## Findings

真实 Studio 使用三条合成项目。逐张检查桌面和手机版待选、确认后项目页及读取失败。首页手机版实拍覆盖 390 × 1305 的完整页面。确认后进入脚本直出仍保留版本，独立项目没有来源条。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/screenshot-manifest.json | 253ec94a0eb524f363fb2002fd29133994ee8aa58d7c5244654779f5e5474916 | 实测输出或校验记录 |
