# Acceptance Run: 20261027T074134Z-macos-fixed-headless-e26ec2f-round2-6ae25b

- Run ID: 20261027T074134Z-macos-fixed-headless-e26ec2f-round2-6ae25b
- Task ID: 2026-10-26-R280-photo-studio-light
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R280-studio-light/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: dae824d5fb346a4ec75091c4235a51f7fc18eb8e697d8747881977914935f261
- Source identity: e26ec2f19d5e1136577873beb932f537a2a0037f
- Runtime identity: fixed-venv;playwright-1228;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-27T07:41:34.613339Z
- Completed at: 2026-10-27T07:51:40.031208+00:00
- Evidence directory: evidence/

## Scope

共用54/54合同和五代既有交互，包含真实旧任务1440/960横向边界；前端建任务/上传有接口夹具，真实只读库/媒体/Range另验。19张最终图哈希与图库复核、个人抽看桌面旧任务和手机详情至底部，没有新增捕获。

## Procedure

R280交付，真实basea28a991、sourcee26ec2f；三旧卡先用Git绑定批准合同正式准备，再创建本run并实际执行。固定Playwright revision1228的headless-shell，禁止系统Chrome或回退；一次一个浏览器、渲染/门禁串行8768，R277源只读克隆；固定浏览器存在性和磁盘全程监控。没有改产品/测试/判据或安装工具，命令/时间/退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run限定机器范围 |

## Findings

共用54/54合同和五代既有交互，包含真实旧任务1440/960横向边界；前端建任务/上传有接口夹具，真实只读库/媒体/Range另验。19张最终图哈希与图库复核、个人抽看桌面旧任务和手机详情至底部，没有新增捕获。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | 19ab0584c15df68b01942803f0da1a7c58ad67f7d29b99e6f5c587aec71b3195 | 当前执行或明示复用的索引 |
| evidence/fixed-browser.json | 57ec96e0f392b48f1a6c17e147094f05cc266decaf4175991561711ab1054509 | 当前执行或明示复用的索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前执行或明示复用的索引 |
| evidence/node-test-scope.json | ce336a256c89e6a2340e6ee1142e7fb91f8afc711eb86e3df00383ca7192c77d | 当前执行或明示复用的索引 |
| evidence/r278-node.log | 6fac0ce626d2c7bea77a38a4506a6f100664e49bdc61f9c5775d57857099be33 | 当前执行或明示复用的索引 |
| evidence/r282-frontend.log | a9b80f3882b17cf84d4c47cd5453fd26c45953a79b805ae37d75b771f98ab861 | 当前执行或明示复用的索引 |
| evidence/shared-contracts.json | 9243f76ecfb3a2f7d5db3d6ae9621aaa25a3dfe7935bd07ed92d2ba11fb6e9b3 | 当前执行或明示复用的索引 |
| evidence/shared-real-library-api.json | b4fd3502082ec7b7144c298c3d31630c22acfca0c91e7e6fcc628c284d1abcff | 当前执行或明示复用的索引 |
| evidence/browser-evidence-summary.json | 1e037568c8f1b51f31a06d104c9bf82872ab3d1cfd196dd2235b20d532131305 | 当前执行或明示复用的索引 |
| evidence/reused-screenshot-evidence.json | 7600325568d47ff8ebad8dcd1fb11ffadd801433ff0dd364242d865f2c6c3eac | 当前执行或明示复用的索引 |
| evidence/visual-sample-review.json | 57de022c3925672956d84b5b836f7e85b2d3b9c409f149576f795b419583383f | 当前执行或明示复用的索引 |

## Unverified items

人工项PENDING。主题与布局受控检查不替代整体审美和真人验收；R282原中台交接、R299及绑定前置条件继续保留，主题PASS不证明该外部链路。无付费模型/真实配音成片/全量pytest；同步、outline、严格截图实体归档差异照实保留。

## Conclusion

PASS：仅上述机器范围，不是当前完整中台链路、人工PASS或READY。
