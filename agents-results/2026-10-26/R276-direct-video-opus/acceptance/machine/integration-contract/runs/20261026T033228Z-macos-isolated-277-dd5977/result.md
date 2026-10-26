# Acceptance Run: 20261026T033228Z-macos-isolated-277-dd5977

- Run ID: 20261026T033228Z-macos-isolated-277-dd5977
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: 540b2cebb2de8f6293c684aaa5c219417dea9f51d2eaf14769a3745577ad9c13
- Source identity: 277cd1c6ca730f77bd653a31a8b7ca22ea90277b
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T03:32:28.321183Z
- Completed at: 2026-10-26T03:36:21.250117+00:00
- Evidence directory: evidence/

## Scope

R276 原合同后端、API、真实本地渲染、合成与单镜不变性

## Procedure

所有命令在 277cd1c 上从头执行，未使用上一段验收物或日志。原始命令输出先保存，再装配本 run；run 创建时间不冒充最早命令开始时间。R276 先准备 rebaseline，再复跑原合同。pytest 专项、R276 专项与两份浏览器门禁串行运行；只用临时状态和8767/8768，未操作8765/8766。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本节明示机器范围 |
| AC-02 | PASS | evidence/ | 仅本节明示机器范围 |
| AC-03 | PASS | evidence/ | 仅本节明示机器范围 |

## Findings

134 passed in 20.57s；H-03 独立 1 passed in 0.10s；仓库安全 PASS。 模型单测使用假可执行文件，浏览器接口使用产品仓库内既有夹具；不宣称真实新作品生成。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/h03-backend-invariance.log | 4e8b6c5a89da44bf05d17100903172be04033067c113a6831bdfafbd42b7da52 | 本轮新执行日志或外部图像哈希清单 |
| evidence/h03-evidence-binding.json | b6a5c30cf4ac2e9f0b3cb1a9e06c593906dad3bf8fe1cbebd9d5f387679689ce | 本轮新执行日志或外部图像哈希清单 |
| evidence/historical-b-h03-proof.json | 42cf935dd0230f59f112512f2f151cadb981866e7e7ed94122083a6af0521662 | 明确标注的原始历史真跑证明，不当成277cd1c新跑 |
| evidence/pytest-r276.log | 4600ba35588584311d2059ad8c7d60f5e1fbfcbdea188465e9c90b5cd4f07438 | 本轮新执行日志或外部图像哈希清单 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 本轮新执行日志或外部图像哈希清单 |

## Unverified items

H-01 至 H-03 仍待用户本人验收，R277 真实柱子措辞差异和旧任务需先看图保留在合同。R276 真实七镜配音同步不由夹具证明。媒体外置与 strict visual-fidelity run 内实体截图规则仍冲突，本 run 不证明严格视觉归档通过。全仓 FFmpeg 和文档时间戳既有失败另列，不计入此专项 PASS。

## Conclusion

本 run 在其合同和277cd1c源码身份上的上述限定机器范围 PASS；不是全仓、严格视觉归档、人工通过或 READY。
