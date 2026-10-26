# Acceptance Run: 20261026T170643Z-macos-headless-serial-fc072d9-61e71b

- Run ID: 20261026T170643Z-macos-headless-serial-fc072d9-61e71b
- Task ID: 2026-10-26-R278-photo-direct-rescript
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: c09cdffe9bb97c23b7526c7dce449611d0c5eada03d8db47bbfd86c3c72ac49d
- Source identity: fc072d9694a6c807f2eafd4a4104c8e803d89b2a
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T17:06:43.363261Z
- Completed at: 2026-10-26T17:12:19.755082+00:00
- Evidence directory: evidence/

## Scope

同次263项 R276/R277/R278 Python 专项，包含原两卡所有受保护Python测试、H-03单镜不变性；仓库安全与运行时合同。

## Procedure

第二次交付，从当前fc072d9和原origin/main基底重新执行；未沿用作废提交的机器结果。先准备两旧卡rebaseline，再创建本run；命令、真实起止时间和退出码见machine-results.json。固定.venv、指定headless-shell及Playwright，DIRECT_GATE_PORT=8768，R277_SOURCE_STATE指向只读studio-r278并克隆后使用。浏览器一次一个、全部门禁串行、结束时关闭自有浏览器及临时服务。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-02 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-03 | PASS | evidence/ | 仅本run明示的确定性机器范围 |

## Findings

263 passed in 100.42s，仓库安全和运行时合同PASS。模型单测使用假生成器/假可执行文件及临时状态；指定浏览器渲染测试串行运行。 未对真实作品发起生成或付费模型请求；API夹具及历史投影重放不证明新的真实模型语义或人工观感。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-targeted.log | 9ba49fb78b7111c5a3323d4e53f6a93e1ba58a660917708eec904004aa85a3c2 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/machine-results.json | a0cb8b5368272afe24d99a6aaa11994e837c97d88bb326d69d858902fdbdfbc4 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/runtime.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 第二次交付新运行日志或明确复用的外置证据索引 |

## Unverified items

H-01至H-03仍待用户亲自验收。H-03首次215.621秒、修改168.813秒；用户2026-10-27原话「这个没事 大概差不多就行」，仅记录解释，不更改卡片文字或视作人工PASS。Obsidian时间戳、outline及全量测试已知9失败6错误另列，不包含在本限定专项PASS中。严格视觉run内实体图片要求与项目媒体外置的既有归档差异不由本run消除，不声称严格视觉归档或新全链路模型生成已通过。

## Conclusion

PASS：仅覆盖fc072d9上的上述机器范围。不是人工通过、全仓通过、部署或READY。
