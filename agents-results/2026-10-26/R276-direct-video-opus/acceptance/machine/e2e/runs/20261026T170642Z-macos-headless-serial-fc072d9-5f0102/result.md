# Acceptance Run: 20261026T170642Z-macos-headless-serial-fc072d9-5f0102

- Run ID: 20261026T170642Z-macos-headless-serial-fc072d9-5f0102
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: a6a8df161dae7eb8f89c584472e7a7bef213ff813161dcd2eca1b70e19c88e91
- Source identity: fc072d9694a6c807f2eafd4a4104c8e803d89b2a
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T17:06:42.998239Z
- Completed at: 2026-10-26T17:12:19.755082+00:00
- Evidence directory: evidence/

## Scope

R276 Node 专项、26次合同、公式和全部旧交互，含旧成片视频移除后的回调回归。

## Procedure

第二次交付，从当前fc072d9和原origin/main基底重新执行；未沿用作废提交的机器结果。先准备两旧卡rebaseline，再创建本run；命令、真实起止时间和退出码见machine-results.json。固定.venv、指定headless-shell及Playwright，DIRECT_GATE_PORT=8768，R277_SOURCE_STATE指向只读studio-r278并克隆后使用。浏览器一次一个、全部门禁串行、结束时关闭自有浏览器及临时服务。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-02 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-03 | PASS | evidence/ | 仅本run明示的确定性机器范围 |

## Findings

26/26合同PASS；公式、请求、重新合成及旧视频回调均PASS。--checks-only，没有新整页截图。 未对真实作品发起生成或付费模型请求；API夹具及历史投影重放不证明新的真实模型语义或人工观感。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/r276-node.log | 77d9ffb32e2151858d3c2292ccd8ee75b28e6c5412de0a8a5eda63bad53baa7c | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r276-frontend.log | 4c458bdf24bb5a08ba5eddfa7c361ce1bbb42bdbc6d4dce169d40df2609a664d | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r276-contracts-external.json | 86ada7b00a94a611651b986dfa4ac1d993508382facc29d215b7d4a626000806 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | e9dea59860ba2fde8b776b7df1a90b8cd26411a6833dfc7cf5fca96855169191 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/machine-results.json | a0cb8b5368272afe24d99a6aaa11994e837c97d88bb326d69d858902fdbdfbc4 | 第二次交付新运行日志或明确复用的外置证据索引 |

## Unverified items

H-01至H-03仍待用户亲自验收。H-03首次215.621秒、修改168.813秒；用户2026-10-27原话「这个没事 大概差不多就行」，仅记录解释，不更改卡片文字或视作人工PASS。Obsidian时间戳、outline及全量测试已知9失败6错误另列，不包含在本限定专项PASS中。严格视觉run内实体图片要求与项目媒体外置的既有归档差异不由本run消除，不声称严格视觉归档或新全链路模型生成已通过。

## Conclusion

PASS：仅覆盖fc072d9上的上述机器范围。不是人工通过、全仓通过、部署或READY。
