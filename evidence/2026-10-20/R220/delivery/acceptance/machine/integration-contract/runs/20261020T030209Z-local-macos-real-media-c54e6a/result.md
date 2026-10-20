# Acceptance Run: 20261020T030209Z-local-macos-real-media-c54e6a

- Run ID: 20261020T030209Z-local-macos-real-media-c54e6a
- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-20/R220/delivery/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 0cafe30ca310cda382b32b61b3e87a55c951b9765e64efcf4f7a3e18fe20fbf9
- Source identity: b7ceabebe01700198270de058d7f8de833300dc7
- Runtime identity: local-macos-real-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T03:02:09.894861Z
- Completed at: 2026-10-20T03:05:28.032484+00:00
- Evidence directory: evidence/

## Scope

AC-01；106 项定向回归与 3 项子测试通过，包括原片隔离、CAS、决定合并和封面三分之一取帧。

## Procedure

固定项目虚拟环境执行八个相关测试模块及项目规定检查。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | AC-01；106 项定向回归与 3 项子测试通过，包括原片隔离、CAS、决定合并和封面三分之一取帧。 |

## Findings

全量回归为 11 failed、729 passed、32 skipped、6 errors、1982 subtests passed；失败属于已记录的字幕/视频环境及文档同步基线。文档同步和 outline 检查仍失败，未修改配对文档或降低检查。局部 PASS 不覆盖这些失败。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/focused.log | 4ca46befa1cf3c85561fb74884fbaff87c3d3e2090a9ef338882642f7aef3aa8 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/full-pytest.log | e7384798aa2b5dd391ab4238135cea2e0dace0a0de06989be098841f35983851 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/obsidian.log | c3842d47b630187433984654ceff5633cc1d8bee57dbf1476a12518ad8482ea9 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/outline.log | 95424311d3c9399cb359cd36aca86929a836f894e074167366e8fd7ba8ea1d38 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/required-checks.json | 60b519ba378a33bfa90b97bc384be45ba53e5d7a64135d2f401d793ad071004e | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/runtime.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/validate-draft.log | 56b7ab792c3517cf3756705e80c79bc7052f1f9ab9e4b2e8cc5122a9314aa62d | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/validate-task.log | 3767f6ee233b6b017a497fae00b05ba2e54a056003939f6ceb9e1059ad97b135 | 隐私净化后的机器证据；原始件在外置归档 |

## Unverified items

H-01 至 H-03 等人工验收；R208 阶段 B 的 H-02、H-03 尚未实现。私人截图不进 Git，深层本地截图检查须从外置归档还原未跟踪图片后运行。

## Conclusion

仅本 lane 明确范围通过，按 warn 交付策略递交；不代表全库检查全绿或人工通过。
