# Acceptance Run: 20261026T170643Z-macos-headless-serial-fc072d9-bff40c

- Run ID: 20261026T170643Z-macos-headless-serial-fc072d9-bff40c
- Task ID: 2026-10-26-R277-photo-shot-visual-revision
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 8646e9ada223ec50d5af77c0e6fd3f8d7762c46bdc639849cedb02e0efce9b3d
- Source identity: fc072d9694a6c807f2eafd4a4104c8e803d89b2a
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T17:06:43.203128Z
- Completed at: 2026-10-26T17:12:19.755082+00:00
- Evidence directory: evidence/

## Scope

R277 Node 17状态、42次合同、标记几何、详情/版本/样例/问题记录/轮询；从只读studio-r278克隆重放真实旧任务。

## Procedure

第二次交付，从当前fc072d9和原origin/main基底重新执行；未沿用作废提交的机器结果。先准备两旧卡rebaseline，再创建本run；命令、真实起止时间和退出码见machine-results.json。固定.venv、指定headless-shell及Playwright，DIRECT_GATE_PORT=8768，R277_SOURCE_STATE指向只读studio-r278并克隆后使用。浏览器一次一个、全部门禁串行、结束时关闭自有浏览器及临时服务。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-02 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-03 | PASS | evidence/ | 仅本run明示的确定性机器范围 |

## Findings

42/42合同PASS；真实旧任务、标记、详情、版本、日志和轮询PASS；源8670文件前后哈希相同。--checks-only，无新整页截图。 未对真实作品发起生成或付费模型请求；API夹具及历史投影重放不证明新的真实模型语义或人工观感。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/r277-node.log | 887ba2b3eea6122a632ba4c2b3fa9367f7c1127e77c02144e208c51dc8527f6b | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r277-frontend.log | d21246ed1ee4a957d59f4a4ba9beb905630198de63be4113282948f4ede59933 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r277-contracts-external.json | 74e7989060d94c7d95d7916b377d37bfa5eea0afccd9664212591a926d833e78 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | e9dea59860ba2fde8b776b7df1a90b8cd26411a6833dfc7cf5fca96855169191 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/machine-results.json | a0cb8b5368272afe24d99a6aaa11994e837c97d88bb326d69d858902fdbdfbc4 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r277-source-preservation-external.json | 384f7801d4f44ebdd775dbf838c371349286c33faa59208a647acdf7c3dcf672 | 第二次交付新运行日志或明确复用的外置证据索引 |

## Unverified items

H-01至H-03仍待用户亲自验收。H-03首次215.621秒、修改168.813秒；用户2026-10-27原话「这个没事 大概差不多就行」，仅记录解释，不更改卡片文字或视作人工PASS。Obsidian时间戳、outline及全量测试已知9失败6错误另列，不包含在本限定专项PASS中。严格视觉run内实体图片要求与项目媒体外置的既有归档差异不由本run消除，不声称严格视觉归档或新全链路模型生成已通过。

## Conclusion

PASS：仅覆盖fc072d9上的上述机器范围。不是人工通过、全仓通过、部署或READY。
