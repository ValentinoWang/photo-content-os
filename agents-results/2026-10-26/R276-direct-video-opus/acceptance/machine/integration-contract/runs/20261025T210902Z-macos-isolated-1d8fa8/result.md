# Acceptance Run: 20261025T210902Z-macos-isolated-1d8fa8

- Run ID: 20261025T210902Z-macos-isolated-1d8fa8
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 9eadb40e931645d02285777ff09fae656dd313bf0ca93afd2010af6c37c182ec
- Source identity: d095d101c445bb6a349208ce6c5af8be3afbf10c
- Runtime identity: fixed-venv;real-renderer;temporary-state
- Executor or reviewer: Codex
- Started at: 2026-10-25T21:09:02.623946Z
- Completed at: 2026-10-25T21:14:03.830252+00:00
- Evidence directory: evidence/

## Scope

AC-01、AC-02 的后端、真实 HTML 渲染、合成、错误恢复与接口合同；AC-03 后端不变性；全部写入临时状态。

## Procedure

收集本次 verified head 上已执行命令的原始输出，见 evidence/；合同只装配原样批准的 H 项，不改实现或断言。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅上述范围 |
| AC-02 | PASS | evidence/ | 仅上述范围 |
| AC-03 | PASS | evidence/ | 仅上述范围 |

## Findings

134 tests passed in 38.89 seconds；H-03 定向测试另跑通过。测试模型为本机假的可执行文件，真实模型连通与生成复用已通过的 A/B 证据，不宣称本轮调用了 Opus。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/b-h03-proof.json | 42cf935dd0230f59f112512f2f151cadb981866e7e7ed94122083a6af0521662 | 当前源码命令输出或明确边界的证据；媒体仅位置与摘要 |
| evidence/b-media-readback.json | f42c9cc4f415e3985589e2d2fd27b0df6c8da0b40ae624d4e8112278e332523a | 当前源码命令输出或明确边界的证据；媒体仅位置与摘要 |
| evidence/h03-backend-invariance.log | 7fefcaf66f6e7137767bc25d16d128cbf7b8617ad0b6f14fbf9a0b8e7fdd81cd | 当前源码命令输出或明确边界的证据；媒体仅位置与摘要 |
| evidence/pytest-r276.log | 46c7897427f24375069268e48d6ed9fa3f941f79d9923d294b4d40507439274a | 当前源码命令输出或明确边界的证据；媒体仅位置与摘要 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前源码命令输出或明确边界的证据；媒体仅位置与摘要 |

## Unverified items

H-01、H-02、H-03 待真实用户验收；七镜带声同步听感未在本轮真跑。前端夹具的时钟平移没有平移 output.composedAt，导致该夹具完成页显示 0:00；D 的独立实际表达式正反例仍通过，不把该截图当成正确耗时的证明。全部严格视觉归档不在本 PASS 范围，单独 FAIL run 和 manager check 如实保留。

## Conclusion

PASS 只针对上述范围、当前 contract 与 source identity；不代表人工通过、全仓通过或可推送。
