# Acceptance Run: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-bad49d

- Run ID: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-bad49d
- Task ID: 2026-10-26-R277-photo-shot-visual-revision
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 8646e9ada223ec50d5af77c0e6fd3f8d7762c46bdc639849cedb02e0efce9b3d
- Source identity: 7d0ab0046ef286a5bac8c468d86ebc10ccf557cd
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T20:05:26.363295Z
- Completed at: 2026-10-26T20:09:36.280777+00:00
- Evidence directory: evidence/

## Scope

R277原Node与完整checks-only门禁PASS，合同数42；R277使用只读源克隆。

## Procedure

第四次交付，真实base130c931、源码7d0ab00；R278先通过Git绑定的新批准合同准备，再创建run并执行。R276/R277原保护摘要未变，不伪造无差异rebaseline。固定.venv及指定headless-shell，8768、单浏览器、串行门禁。未调用付费模型、未操作8769或用户任务。开始完成时间及真实退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run的限定机器范围 |

## Findings

R277原Node与完整checks-only门禁PASS，合同数42；R277使用只读源克隆。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | fb0450a77ef5a8237a93f366a13ed09f3fe4199e0de90a36f4153d90a9ccc277 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r277-node.log | 887ba2b3eea6122a632ba4c2b3fa9367f7c1127e77c02144e208c51dc8527f6b | 本轮执行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | c667e265aacf0a2cb7c9ee880d274e812e4e66f753696ca93bc907d096b8ea5f | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r277-frontend.log | d21246ed1ee4a957d59f4a4ba9beb905630198de63be4113282948f4ede59933 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r277-contracts.json | 74e7989060d94c7d95d7916b377d37bfa5eea0afccd9664212591a926d833e78 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r277-source-preservation.json | 384f7801d4f44ebdd775dbf838c371349286c33faa59208a647acdf7c3dcf672 | 本轮执行日志或明确复用的外置证据索引 |

## Unverified items

全部H项PENDING。七镜画法一致及只改底色的模型视觉语义仍由人验；前端建任务请求有夹具拦截。媒体外置与深层check要求run内reviewed实体图的差异未伪造解决。不跑全量pytest；同步和outline既有失败照实保留。第三轮历史焦点失败记录在总控备份和外置日志，本轮未重现，不称根因修复。

## Conclusion

PASS：仅上述机器范围；不是人工PASS或READY。
