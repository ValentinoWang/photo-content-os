# Acceptance Run: 20261027T092843Z-photo-dev-phase2-830f59

- Run ID: 20261027T092843Z-photo-dev-phase2-830f59
- Task ID: 2026-10-27-R310-photo-devbox
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R310-photo-devbox/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: 2c5042ae7515a22531e76c3055c5b01b3d816b54e0db3812cd4e7454908243ee
- Source identity: fb6f2fe7a656c78461bb4fd1967e88bbb2175401
- Runtime identity: rbox-fixed-venv-python3.13.9
- Executor or reviewer: Codex
- Started at: 2026-10-27T09:28:43.187313Z
- Completed at: 2026-10-27T09:29:18.569141+00:00
- Evidence directory: evidence/

## Scope

AC-01：rbox在真实photo-dev执行固定.venv浅色专项，9 passed in 0.06s；源HEAD和四份受保护文件摘要从远端回读，匹配本机冻结fb6f2fe。

## Procedure

scripts/devbox/rbox run <任务 worktree> -- bash -c <git rev-parse HEAD、sha256sum四份保护文件、.venv/bin/python -m pytest -q tests/test_r280_light.py>；实际命令完整保存在evidence/command.json。在线检查器未发布，真实直连成功后才同步和执行。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-r280.log; evidence/command.json | 真实远端、固定.venv、九项专项；没有本机pytest或模型替身 |

## Findings

上述命令退出码均为0。第一阶段缺检查器直接放行问题已由总控fb6f2fe修复；本轮见到缺检查器时真实直连成功的输出，第四种拒绝路径由自测夹具覆盖。没有修改实现、测试或需求H项。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/command.json | 5b9fa9ada8b194530e86d4acab52aad975d9cffa92e715b94857b8f58591cfed | 实际执行记录 |
| evidence/pytest-r280.log | 1308d8089e595d079c7d449a91ed3b5ff9a90abd2b410ef2741f41c25cb9540e | 实际执行记录 |

## Unverified items

仅本run范围；人工两项尚未签署。未重跑全量、R276/R278/R277浏览器门禁或渲染。总控历史全量1204通过、12失败、36跳过，其中9项本机同样红、3项开发机环境差异；R277因字体度量不同仍留本机。开发机Noto/Liberation字体链接与特定cp替身、melt7.4对本机7.39、缺Obsidian库均未由浅色专项证明等价。40cf307旧证据不作为本源码PASS。

## Conclusion

PASS：仅上述冻结源码的限定机器范围，不是全量全绿、等价渲染或人工PASS。
