# Acceptance Run: 20261020T030209Z-local-macos-real-media-934018

- Run ID: 20261020T030209Z-local-macos-real-media-934018
- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: evidence/2026-10-20/R220/delivery/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 0cafe30ca310cda382b32b61b3e87a55c951b9765e64efcf4f7a3e18fe20fbf9
- Source identity: b7ceabebe01700198270de058d7f8de833300dc7
- Runtime identity: local-macos-real-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T03:02:09.974391Z
- Completed at: 2026-10-20T03:05:28.032484+00:00
- Evidence directory: evidence/

## Scope

AC-02；真实派生镜头、成片与音乐播放，六项导航与四处小修；26 项走查通过。

## Procedure

运行 scripts/verify_r220_browser.mjs；仅本机回环源与真实 state 副本，不写真实镜头决定。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/ | AC-02；真实派生镜头、成片与音乐播放，六项导航与四处小修；26 项走查通过。 |

## Findings

全量回归为 11 failed、729 passed、32 skipped、6 errors、1982 subtests passed；失败属于已记录的字幕/视频环境及文档同步基线。文档同步和 outline 检查仍失败，未修改配对文档或降低检查。局部 PASS 不覆盖这些失败。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/browser-walkthrough.json | 9b9e2461ae4843d11606aeb2f56f5e93e3eea3d03aa6ac2a7c663aff0a9de71d | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/four-gates.json | a6dc4a96d81c14b4d7eae17da1c9735f16424d86d5db8c829f250fab4f24f475 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/screenshot-manifest.json | 5fed92cdadb4459beff5817d7113e729c56bb557538ee6baee2918a605b87826 | 隐私净化后的机器证据；原始件在外置归档 |

## Unverified items

H-01 至 H-03 等人工验收；R208 阶段 B 的 H-02、H-03 尚未实现。私人截图不进 Git，深层本地截图检查须从外置归档还原未跟踪图片后运行。

## Conclusion

仅本 lane 明确范围通过，按 warn 交付策略递交；不代表全库检查全绿或人工通过。
