# Acceptance Run: 20261025T232446Z-macos-chrome-c39-1da705

- Run ID: 20261025T232446Z-macos-chrome-c39-1da705
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: f62a10c6c6038f7ce122bc243bce4a301bcb954bfe95912e4c0672a34dab21fc
- Source identity: c39b465f696856babc835ea6893196240d9198e9
- Runtime identity: chrome;isolated-studio-8767;API-fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-25T23:24:46.924001Z
- Completed at: 2026-10-25T23:26:21.509731+00:00
- Evidence directory: evidence/

## Scope

当前源码的实际前端挂载、26 次状态图文合同、31 张整页截图与浏览器交互；API 为夹具投影，不证明真实生成。

## Procedure

在 c39b465、产品及测试无未提交修改的工作区执行任务单第二段要求；证据原始日志均在 evidence/。已有 .venv 仅用于执行，未修改链接；8765/8766 未访问，独立 8767 已收尾。源日志先执行后装配进本 run，不将 run 创建时间当成重新执行命令的时间。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/ | 仅以下明示范围 |

## Findings

134 tests passed in 21.68 seconds；H-03 独立 1 passed in 0.48 seconds；Node 回归 PASS；浏览器 26 comparisons、31 captures 和交互 PASS；仓库安全检查 PASS。模型执行使用假可执行文件，浏览器使用仓库原有投影夹具；没有付费模型调用或新作品生成。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/design-comparisons.json | cd2c3ddaa3290bf1dfad242e9bfe8fa0a73bcb16ac9364f894b66356dd22a132 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/done-1440.inventory.json | f45476a46a8b2a4001990902743bf2d23ae3be9cc510ed2c98f2358aa5ff2c44 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/frontend-gate.log | 457893f7e693ed1d36044245c015122884d18e170ec1971d422db4cf68002c79 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/frontend-node.log | 77d9ffb32e2151858d3c2292ccd8ee75b28e6c5412de0a8a5eda63bad53baa7c | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/frontend-screenshot-manifest-external.json | 9815a7124739df9f8059e90b40dad7298e3ce21b4c891e8d535faad11b680bd1 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/ready-1440.inventory.json | 5f3ece5f78c78edf525b50f23490f1bda2bb45a14849c53c7a189b89c066aa4f | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/writing-960.inventory.json | 992e95af5d22c6d34ad42f71e1f6fa0a53680bba4b4d0da1f9522d2106a8001d | 当前源码上的执行结果或明确来源的既有证据 |

## Unverified items

H-01、H-02、H-03 均等用户亲自验收，七镜带声同步观感仍未新实测。既有真实 B 证据不冒充当前新跑。媒体继续留仓库外；Core 要求 run 内截图实体的严格归档规则与项目外置规则冲突仍未解决，外部清单不称该门禁 PASS。夹具完成态 composedAt 未随旧时钟平移，可能显示 0:00；耗时公式由独立 Node 正反例证明，不靠这张截图判断。

## Conclusion

本 run 在合同第 2 版与指定源码身份上的上述机器范围 PASS；不代表全仓、严格视觉归档、人工验收或可推送。
