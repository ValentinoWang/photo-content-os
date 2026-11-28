# Acceptance Run: 20261126T162436Z-devbox-unit-174890

- Run ID: 20261126T162436Z-devbox-unit-174890
- Task ID: 2026-11-26-Pho_R23-studio-project-pick
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/preview-ui-p/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: fdfecccb8eab944166133f8d794d821739b2eadef791e68250a4c60dde9f1dd1
- Source identity: d480294e571831aaceb88933b149fcc4ee97f2e6
- Runtime identity: photo-dev-isolated-wheel
- Executor or reviewer: codex
- Started at: 2026-11-26T16:24:27Z
- Completed at: 2026-11-26T16:25:00Z
- Evidence directory: evidence/

## Scope

真实 Studio HTTP、同名项目、并发和过期检查、损坏文件以及安装版 watch 与策划台替身。Python 46 项和 Node 1 项全部通过。

## Procedure

在 photo-dev 的制作台主目录，以隔离 Python 运行任务单的两个 pytest 文件，再以 Node 运行 R282 回归。用真实 HTTP 提交选择，使用替身核对 Media 确认。合成 MP4 供项目页读取。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/verification.txt | 退出码 0 |

## Findings

真实 Studio HTTP、同名项目、并发和过期检查、损坏文件以及安装版 watch 与策划台替身。Python 46 项和 Node 1 项全部通过。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/verification.txt | a9b0a2b2783b59e057b91b5c310d68cf8eb02490a4af1764ce2e5073889f8403 | 实测输出或校验记录 |
| evidence/installed-wheel.json | ebec340656f6a24b145281126277721c0b89ecb3cce828f27b571662d85608bf | 实测输出或校验记录 |
