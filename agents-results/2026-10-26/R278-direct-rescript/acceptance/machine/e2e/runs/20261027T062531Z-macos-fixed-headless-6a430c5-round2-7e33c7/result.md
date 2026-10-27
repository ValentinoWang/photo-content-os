# Acceptance Run: 20261027T062531Z-macos-fixed-headless-6a430c5-round2-7e33c7

- Run ID: 20261027T062531Z-macos-fixed-headless-6a430c5-round2-7e33c7
- Task ID: 2026-10-26-R278-photo-direct-rescript
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md
- Contract version: 3
- Contract SHA-256: 0e2a37aa6055f6a357a78b7345ea0c0d31d6d144076e0d18db4710aa0e39bb8d
- Source identity: 6a430c5ecc2d0df4c88b5285bb29e8bfba3b62d3
- Runtime identity: fixed-venv;playwright-1228;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-27T06:25:31.783863Z
- Completed at: 2026-10-27T06:30:33.182299+00:00
- Evidence directory: evidence/

## Scope

共用52/52合同及R282/R278/R283全部挂载交互、五个文字字段/图片/新旧元数据/换版/配音请求通过。建任务和上传用接口替身；只读真实库接口、媒体和Range另验。10张F最终截图复核哈希/图库，个人抽看两张至底部；未新增整页捕获。

## Procedure

第二次交付，真实base614c550、source6a430c5；两旧卡先用Git绑定批准合同正式准备，再创建本run并实际执行。固定Playwright revision1228的headless-shell，禁止系统Chrome或回退；一次一个浏览器、渲染/门禁串行8768，R277源只读克隆；固定浏览器存在性和磁盘全程监控。没有改产品/测试/判据或安装工具，命令/时间/退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run限定机器范围 |

## Findings

共用52/52合同及R282/R278/R283全部挂载交互、五个文字字段/图片/新旧元数据/换版/配音请求通过。建任务和上传用接口替身；只读真实库接口、媒体和Range另验。10张F最终截图复核哈希/图库，个人抽看两张至底部；未新增整页捕获。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | 76f9330e3ecf659ceadf01d09bd9d29d610d6cd14f95f1d6d1cb139248460e32 | 当前执行或明示复用的索引 |
| evidence/fixed-browser.json | 57ec96e0f392b48f1a6c17e147094f05cc266decaf4175991561711ab1054509 | 当前执行或明示复用的索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前执行或明示复用的索引 |
| evidence/external-dependencies.json | 1199aa3c7e229263168535babed07cff9400caf9b8ae5fcff0b72ebd2cc083ed | 当前执行或明示复用的索引 |
| evidence/route-decision.json | aef9c5bd4afb349e94d283ed5bcb01519f6c6ef5d35f8e08cafbfd1537facdff | 当前执行或明示复用的索引 |
| evidence/r278-node.log | 6fac0ce626d2c7bea77a38a4506a6f100664e49bdc61f9c5775d57857099be33 | 当前执行或明示复用的索引 |
| evidence/r282-frontend.log | a7846a4eadb1da36cbd958c10e2db9ce2861b32993fd4f02855ddbe73ffd9f97 | 当前执行或明示复用的索引 |
| evidence/shared-contracts.json | 3edd087ffbf220a321e3bf42b79c4d11f7220e2178712b9796abdffb02fa559b | 当前执行或明示复用的索引 |
| evidence/shared-real-library-api.json | b4fd3502082ec7b7144c298c3d31630c22acfca0c91e7e6fcc628c284d1abcff | 当前执行或明示复用的索引 |
| evidence/browser-evidence-summary.json | 2b7983b532854051017731e1b3b656a9349e0feded3c694c201ac39c2b1ffb9f | 当前执行或明示复用的索引 |
| evidence/reused-screenshot-evidence.json | 8b9777099ade08ab0289e03724cae18bb6e4a61a255f8cf84573e54cc70dbc8e | 当前执行或明示复用的索引 |
| evidence/visual-sample-review.json | 0d8d78dfb50eb81494f3e3056dfa38d8d232a424675dd5a16bd3043c8e654b20 | 当前执行或明示复用的索引 |

## Unverified items

人工三项PENDING。8769当前全部交接为null；P5旧包仅为真实可绑定候选（2镜、Cherry50.24秒、无本机图、版本/时间null），本线程不配置服务。H-01版本/时间及H-03更新依赖未发布R299；未知不能冒充完成。无付费模型/真实配音成片/全量pytest；同步、outline、严格截图实体归档差异照实保留。

## Conclusion

PASS：仅上述机器范围，不是当前完整中台链路、人工PASS或READY。
