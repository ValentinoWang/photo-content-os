# Acceptance Run: 20261104T041000Z-macos-a571e4

- Run ID: 20261104T041000Z-macos-a571e4
- Task ID: 2026-11-04-Pho_R01-frontend-debt-fix
- Lane: machine/non-functional
- Status: PASS
- Acceptance contract: agents-results/2026-11-04/frontend-debt-fix/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: d4eefdd9428fad5342f5017e384a1910bc8c09179ec58652572917c892c7fbc8
- Source identity: a571e42ad5b01318f690c728dd9812c62dba91e6
- Runtime identity: local-macos-archive
- Executor or reviewer: Codex
- Started at: 2026-11-04T05:05:43.135524Z
- Completed at: 2026-11-04T05:16:26Z
- Evidence directory: evidence/

## Scope

AC-03：对最终源码归档完整执行 pytest，与任务单列出的失败基线逐条比较。以上时间是证据整理时间，全量实际运行时间为 04:56:41–05:02:21 UTC。

## Procedure

git archive 导出源码，使用固定 .venv，临时文件和 Obsidian 根隔离，设置 Core 界面文字检查器，以 nice -n 10 执行 `python -m pytest -q -rfEs --junitxml=... tests`。原始退出码 1，完整日志和 JUnit 留存；提取 FAILED/ERROR 测试 ID 与 baseline-failures.txt 比较。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-03 | PASS | evidence/full.log; evidence/full.xml | 1205 passed、10 failed、6 errors、36 skipped、2005 subtests；16 项与基线相同，新增失败 0、收集错误 0 |

## Findings

pytest 本身不通过；失败与错误均为任务单登记的原有 ID，涉及字幕、黑帧和文档同步等。原基线跳过 37 项，本次跳过 36 项，macOS 真废纸篓测试实际运行。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/full.log | 893a74338b02f271f1c3009f32029fbc35cf1d4efdbb5f488d44436389a458ca | pytest 原始输出 |
| evidence/full.xml | ef2f307e82284834794f85f9f79600aefc71c61057b776563226f1ae22199f60 | pytest JUnit |

## Unverified items

全量不是全绿；不代表生产部署或人工验收通过。

## Conclusion

PASS 仅指 AC-03 中完整运行且没有新增失败；pytest 退出码仍为 1。
