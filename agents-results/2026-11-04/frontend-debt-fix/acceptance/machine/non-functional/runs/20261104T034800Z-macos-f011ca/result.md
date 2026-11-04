# Acceptance Run: 20261104T034800Z-macos-f011ca

- Run ID: 20261104T034800Z-macos-f011ca
- Task ID: 2026-11-04-Pho_R01-frontend-debt-fix
- Lane: machine/non-functional
- Status: PASS
- Acceptance contract: agents-results/2026-11-04/frontend-debt-fix/acceptance-contract-v1.md
- Contract version: 1
- Contract SHA-256: 7fea37247520a99580b784d0ba51d2fc9461b2dfc0b39a882c46fb4ba0db0968
- Source identity: dd8096ed8fc3ccbb838b9a890e8112d653dcc64e
- Runtime identity: local-macos-archive
- Executor or reviewer: Codex
- Started at: 2026-11-04T03:58:01Z
- Completed at: 2026-11-04T03:59:25Z
- Evidence directory: evidence/

## Scope

AC-03：当前源码完整 pytest 与任务单给定基线的失败项逐条比较；记录整理时间如上，全量实际为 03:49:29–03:55:37 UTC。

## Procedure

`git archive` 到独立临时目录，链接固定 .venv，隔离临时文件及 Obsidian 根，设置 Core UI 文案检查器，以 `nice -n 10` 执行 `python -m pytest -q -rfEs --junitxml=... tests`。退出码 1；完整 pytest 原文与 JUnit 原样保留。逐条提取 FAILED/ERROR ID，与任务根 baseline-failures.txt 进行集合比较。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-03 | PASS | evidence/full.log; evidence/full.xml | 全量 1205 passed、10 failed、6 errors、36 skipped、2005 subtests；16 项与基线逐条相等，新增 0，收集错误 0 |

## Findings

pytest 本身不通过；10 项失败和 6 项测试阶段错误为任务单所列相同 ID，涉及字幕、黑帧、文档同步等。原基线 37 skipped，本轮 36 skipped，macOS 新测试在本机执行。未将旧失败写成通过。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/full.log | 925a8de922ba0457320d5a8bf4eb1624c9e2f62ffefac2f5ddb20fb9017a0db1 | pytest 完整原始输出 |
| evidence/full.xml | 12295bf79f993e500d943ec9b2752348d62616f5c9451cbfd9cbbb371d025536 | pytest JUnit 输出 |

## Unverified items

本轮不修任务单列出的既有失败；不代表全量全绿、部署或人工验收通过。

## Conclusion

PASS 仅指 AC-03 的「完整执行且相对指定基线无新增失败」；pytest 退出码仍为 1。
