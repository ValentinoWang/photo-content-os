# Acceptance Run: 20261026T033228Z-macos-isolated-277-84b7f7

- Run ID: 20261026T033228Z-macos-isolated-277-84b7f7
- Task ID: 2026-10-26-R277-photo-shot-visual-revision
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R277-shot-visual-revision/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: f5998674c6e484665967242c509ffe4ce97d5df71832007292c9065655f6938d
- Source identity: 277cd1c6ca730f77bd653a31a8b7ca22ea90277b
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T03:32:28.567165Z
- Completed at: 2026-10-26T03:36:21.253699+00:00
- Evidence directory: evidence/

## Scope

R277 与相关 R276、OpenAPI、p2、r220、checklist 204项专项及运行时安全验证

## Procedure

所有命令在 277cd1c 上从头执行，未使用上一段验收物或日志。原始命令输出先保存，再装配本 run；run 创建时间不冒充最早命令开始时间。R276 先准备 rebaseline，再复跑原合同。pytest 专项、R276 专项与两份浏览器门禁串行运行；只用临时状态和8767/8768，未操作8765/8766。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本节明示机器范围 |
| AC-02 | PASS | evidence/ | 仅本节明示机器范围 |
| AC-03 | PASS | evidence/ | 仅本节明示机器范围 |

## Findings

204/204 passed in 81.47s；专项独占，无同跑全仓或浏览器门禁。仓库安全和运行时 PASS。 模型单测使用假可执行文件，浏览器接口使用产品仓库内既有夹具；不宣称真实新作品生成。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-targeted.log | 5c943fb555a77c1fff8c1ab81031652d573078629dcfe550eadc12177bc6c61d | 本轮新执行日志或外部图像哈希清单 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 本轮新执行日志或外部图像哈希清单 |
| evidence/runtime-contract.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 本轮新执行日志或外部图像哈希清单 |

## Unverified items

H-01 至 H-03 仍待用户本人验收，R277 真实柱子措辞差异和旧任务需先看图保留在合同。R276 真实七镜配音同步不由夹具证明。媒体外置与 strict visual-fidelity run 内实体截图规则仍冲突，本 run 不证明严格视觉归档通过。全仓 FFmpeg 和文档时间戳既有失败另列，不计入此专项 PASS。

## Conclusion

本 run 在其合同和277cd1c源码身份上的上述限定机器范围 PASS；不是全仓、严格视觉归档、人工通过或 READY。
