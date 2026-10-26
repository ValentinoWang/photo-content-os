# Acceptance Run: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-ac0b6f

- Run ID: 20261026T200526Z-macos-v4-headless-serial-7d0ab00-ac0b6f
- Task ID: 2026-10-26-R283-photo-direct-style-library
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R283-direct-style-library/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 839e69bc7b5d1cf8a8a51d804293d08e559dfe7ab4b2e2509ed7da4dd9da8cfe
- Source identity: 7d0ab0046ef286a5bac8c468d86ebc10ccf557cd
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T20:05:26.789542Z
- Completed at: 2026-10-26T20:09:36.304787+00:00
- Evidence directory: evidence/

## Scope

共用门禁本轮首次执行44/44合同和全部挂载交互PASS；真实只读九种库元数据、媒体及Range通过；历史16截图仅哈希复核复用。

## Procedure

第四次交付，真实base130c931、源码7d0ab00；R278先通过Git绑定的新批准合同准备，再创建run并执行。R276/R277原保护摘要未变，不伪造无差异rebaseline。固定.venv及指定headless-shell，8768、单浏览器、串行门禁。未调用付费模型、未操作8769或用户任务。开始完成时间及真实退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run的限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run的限定机器范围 |

## Findings

共用门禁本轮首次执行44/44合同和全部挂载交互PASS；真实只读九种库元数据、媒体及Range通过；历史16截图仅哈希复核复用。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | fb0450a77ef5a8237a93f366a13ed09f3fe4199e0de90a36f4153d90a9ccc277 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r283-node.log | 46454671feee94095d9a7d7cd373daadf9d8da14468afadad0f3fbc9afbbc488 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | c667e265aacf0a2cb7c9ee880d274e812e4e66f753696ca93bc907d096b8ea5f | 本轮执行日志或明确复用的外置证据索引 |
| evidence/r283-frontend.log | b11ec5dc0ee2c65c3968b7a6c1e5046dcf20b11e4bb585b887c88d782eaca313 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/shared-contracts.json | 0d479b42eccdac3ce6cc74de86e7a5d20cce55d079330ab7eb85055c9ec0d9e7 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/shared-real-library-api.json | b4fd3502082ec7b7144c298c3d31630c22acfca0c91e7e6fcc628c284d1abcff | 本轮执行日志或明确复用的外置证据索引 |
| evidence/reused-screenshot-evidence.json | 7e9941d54df5d72eecf96d4d46843d8046caab925725cb50c1494ddb63b71754 | 本轮执行日志或明确复用的外置证据索引 |
| evidence/visual-sample-review.json | 49841fd9cdcfdaca9e0b1548d992811fc2305ca41b45ae0aa635f3173b3eb93c | 本轮执行日志或明确复用的外置证据索引 |

## Unverified items

全部H项PENDING。七镜画法一致及只改底色的模型视觉语义仍由人验；前端建任务请求有夹具拦截。媒体外置与深层check要求run内reviewed实体图的差异未伪造解决。不跑全量pytest；同步和outline既有失败照实保留。第三轮历史焦点失败记录在总控备份和外置日志，本轮未重现，不称根因修复。

## Conclusion

PASS：仅上述机器范围；不是人工PASS或READY。
