# Acceptance Run: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-d7ae41

- Run ID: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-d7ae41
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: a6a8df161dae7eb8f89c584472e7a7bef213ff813161dcd2eca1b70e19c88e91
- Source identity: 7d0ab0046ef286a5bac8c468d86ebc10ccf557cd
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T20:05:26.122915Z
- Completed at: 2026-10-26T20:09:36.236965+00:00
- Evidence directory: evidence/

## Scope

R276原Node与完整checks-only门禁PASS，合同数26；R277使用只读源克隆。

## Procedure

第四次交付，真实base130c931、源码7d0ab00；R278先通过Git绑定的新批准合同准备，再创建run并执行。R276/R277原保护摘要未变，不伪造无差异rebaseline。固定.venv及指定headless-shell，8768、单浏览器、串行门禁。未调用付费模型、未操作8769或用户任务。开始完成时间及真实退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run的限定机器范围 |

## Findings

R276原Node与完整checks-only门禁PASS，合同数26；R277使用只读源克隆。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | fb0450a77ef5a8237a93f366a13ed09f3fe4199e0de90a36f4153d90a9ccc277 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r276-node.log | 77d9ffb32e2151858d3c2292ccd8ee75b28e6c5412de0a8a5eda63bad53baa7c | 本轮执行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | c667e265aacf0a2cb7c9ee880d274e812e4e66f753696ca93bc907d096b8ea5f | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r276-frontend.log | 4c458bdf24bb5a08ba5eddfa7c361ce1bbb42bdbc6d4dce169d40df2609a664d | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r276-contracts.json | 86ada7b00a94a611651b986dfa4ac1d993508382facc29d215b7d4a626000806 | 本轮执行日志或明确复用的外置证据索引 |

## Unverified items

全部H项PENDING。七镜画法一致及只改底色的模型视觉语义仍由人验；前端建任务请求有夹具拦截。媒体外置与深层check要求run内reviewed实体图的差异未伪造解决。不跑全量pytest；同步和outline既有失败照实保留。第三轮历史焦点失败记录在总控备份和外置日志，本轮未重现，不称根因修复。

## Conclusion

PASS：仅上述机器范围；不是人工PASS或READY。
