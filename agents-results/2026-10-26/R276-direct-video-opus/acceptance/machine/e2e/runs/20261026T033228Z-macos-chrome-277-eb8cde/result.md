# Acceptance Run: 20261026T033228Z-macos-chrome-277-eb8cde

- Run ID: 20261026T033228Z-macos-chrome-277-eb8cde
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: 540b2cebb2de8f6293c684aaa5c219417dea9f51d2eaf14769a3745577ad9c13
- Source identity: 277cd1c6ca730f77bd653a31a8b7ca22ea90277b
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T03:32:28.446274Z
- Completed at: 2026-10-26T03:36:21.251821+00:00
- Evidence directory: evidence/

## Scope

R276 26 次外层设计合同比较、31 张整页图和浏览器交互，使用仓库 API 投影夹具

## Procedure

所有命令在 277cd1c 上从头执行，未使用上一段验收物或日志。原始命令输出先保存，再装配本 run；run 创建时间不冒充最早命令开始时间。R276 先准备 rebaseline，再复跑原合同。pytest 专项、R276 专项与两份浏览器门禁串行运行；只用临时状态和8767/8768，未操作8765/8766。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/ | 仅本节明示机器范围 |

## Findings

Node PASS；26/26 合同及31张整页输出，公式和浏览器交互 PASS；桌面和手机完整图已抽样查看。 模型单测使用假可执行文件，浏览器接口使用产品仓库内既有夹具；不宣称真实新作品生成。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/frontend-gate.log | 457893f7e693ed1d36044245c015122884d18e170ec1971d422db4cf68002c79 | 本轮新执行日志或外部图像哈希清单 |
| evidence/frontend-node.log | 77d9ffb32e2151858d3c2292ccd8ee75b28e6c5412de0a8a5eda63bad53baa7c | 本轮新执行日志或外部图像哈希清单 |
| evidence/screenshot-manifest-external.json | 5e6c689a6c6bfbdcfd95410e474a39cb8c64d2626ed2aab1414c0b168388c77d | 本轮新执行日志或外部图像哈希清单 |

## Unverified items

H-01 至 H-03 仍待用户本人验收，R277 真实柱子措辞差异和旧任务需先看图保留在合同。R276 真实七镜配音同步不由夹具证明。媒体外置与 strict visual-fidelity run 内实体截图规则仍冲突，本 run 不证明严格视觉归档通过。全仓 FFmpeg 和文档时间戳既有失败另列，不计入此专项 PASS。

## Conclusion

本 run 在其合同和277cd1c源码身份上的上述限定机器范围 PASS；不是全仓、严格视觉归档、人工通过或 READY。
