# Acceptance Run: 20261020T030210Z-local-macos-real-media-68fb7f

- Run ID: 20261020T030210Z-local-macos-real-media-68fb7f
- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Lane: visual-fidelity
- Status: PASS
- Acceptance contract: evidence/2026-10-20/R220/delivery/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 0cafe30ca310cda382b32b61b3e87a55c951b9765e64efcf4f7a3e18fe20fbf9
- Source identity: b7ceabebe01700198270de058d7f8de833300dc7
- Runtime identity: local-macos-real-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T03:02:10.052448Z
- Completed at: 2026-10-20T03:05:28.032484+00:00
- Evidence directory: evidence/

## Scope

AC-03；29 状态四宽契约、数字与词法检查通过；受影响桌面/手机完整截图和并排图抽样自核。

## Procedure

运行 capture_r220.mjs、已批准文案扩展下的设计契约检查、词法检查和 compare_r220_screenshots.py；设计稿只读。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-03 | PASS | evidence/ | AC-03；29 状态四宽契约、数字与词法检查通过；受影响桌面/手机完整截图和并排图抽样自核。 |

## Findings

全量回归为 11 failed、729 passed、32 skipped、6 errors、1982 subtests passed；失败属于已记录的字幕/视频环境及文档同步基线。文档同步和 outline 检查仍失败，未修改配对文档或降低检查。局部 PASS 不覆盖这些失败。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/approved-extras.json | ce9f6cce6d36123a6ad6f24b741704026abd0835a4b5c20158e82cabfd92103a | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/artifact-verification.json | 30c2fba9a19ef490c064f68d13470baf853a3042e6d51ee46b678dbfe3c343c1 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/copy-quality.log | 6a20cb38636b86bb1bbc292153b69b94132da82cff8aceb974f1302539a544c3 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/design-check.json | a022067f8865f5889fafbc79009b87dfda130f0178d32b21f3e4516106079f2f | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/four-gates.json | a6dc4a96d81c14b4d7eae17da1c9735f16424d86d5db8c829f250fab4f24f475 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/number-formulas.json | a214491f83e8ca1af0333be5adceab6fb38c804b39cf6f6e9c623c1eb7a33cbc | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/private-artifact-index.json | bd3d23c909becd593d0b0b3364e4a936500504be20d13e61c80e3b375c75cef0 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/ui-copy-quality.json | aca39f64f153feefe59cbdf32dd6d438df5e866751d0d42e47f934ad83d4d2b3 | 隐私净化后的机器证据；原始件在外置归档 |
| evidence/visual-review.md | dcaf0e5451451ed0dafc08157ae5ef6a5ae50ec085b7c2293c4446b9969ca3d9 | 隐私净化后的机器证据；原始件在外置归档 |

## Unverified items

H-01 至 H-03 等人工验收；R208 阶段 B 的 H-02、H-03 尚未实现。私人截图不进 Git，深层本地截图检查须从外置归档还原未跟踪图片后运行。

## Conclusion

仅本 lane 明确范围通过，按 warn 交付策略递交；不代表全库检查全绿或人工通过。
