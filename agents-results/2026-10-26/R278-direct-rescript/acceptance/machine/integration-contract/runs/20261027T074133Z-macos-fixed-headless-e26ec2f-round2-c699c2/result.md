# Acceptance Run: 20261027T074133Z-macos-fixed-headless-e26ec2f-round2-c699c2

- Run ID: 20261027T074133Z-macos-fixed-headless-e26ec2f-round2-c699c2
- Task ID: 2026-10-26-R278-photo-direct-rescript
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md
- Contract version: 4
- Contract SHA-256: 28846dbb7938c890f1ba0879e777798688816ef0b3602341d5c64715859bd017
- Source identity: e26ec2f19d5e1136577873beb932f537a2a0037f
- Runtime identity: fixed-venv;playwright-1228;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-27T07:41:33.411852Z
- Completed at: 2026-10-27T07:51:39.998503+00:00
- Evidence directory: evidence/

## Scope

六代全部指定Python专项：369 passed in 268.92s (0:04:28)；真实HTML渲染三条执行，仓库安全和runtime通过。R280令牌/对比度/媒体隔离和旧代全部Python；生成模型使用替身，不代表新真实成片。

## Procedure

R280交付，真实basea28a991、sourcee26ec2f；三旧卡先用Git绑定批准合同正式准备，再创建本run并实际执行。固定Playwright revision1228的headless-shell，禁止系统Chrome或回退；一次一个浏览器、渲染/门禁串行8768，R277源只读克隆；固定浏览器存在性和磁盘全程监控。没有改产品/测试/判据或安装工具，命令/时间/退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run限定机器范围 |

## Findings

六代全部指定Python专项：369 passed in 268.92s (0:04:28)；真实HTML渲染三条执行，仓库安全和runtime通过。R280令牌/对比度/媒体隔离和旧代全部Python；生成模型使用替身，不代表新真实成片。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | 19ab0584c15df68b01942803f0da1a7c58ad67f7d29b99e6f5c587aec71b3195 | 当前执行或明示复用的索引 |
| evidence/fixed-browser.json | 57ec96e0f392b48f1a6c17e147094f05cc266decaf4175991561711ab1054509 | 当前执行或明示复用的索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前执行或明示复用的索引 |
| evidence/node-test-scope.json | ce336a256c89e6a2340e6ee1142e7fb91f8afc711eb86e3df00383ca7192c77d | 当前执行或明示复用的索引 |
| evidence/pytest-targeted.log | 390362ef2ccdbd71723b930b18c95e2619bf56e98520981eda33c22e7d5ce346 | 当前执行或明示复用的索引 |
| evidence/runtime.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 当前执行或明示复用的索引 |
| evidence/protected-inventory.json | b585ea9a3b3baeef5d7fac4f9c884bd981f90392335eeacc8d02102fa32b1c55 | 当前执行或明示复用的索引 |

## Unverified items

人工项PENDING。主题与布局受控检查不替代整体审美和真人验收；R282原中台交接、R299及绑定前置条件继续保留，主题PASS不证明该外部链路。无付费模型/真实配音成片/全量pytest；同步、outline、严格截图实体归档差异照实保留。

## Conclusion

PASS：仅上述机器范围，不是当前完整中台链路、人工PASS或READY。
