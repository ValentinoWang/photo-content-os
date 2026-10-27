# Acceptance Run: 20261027T062531Z-macos-fixed-headless-6a430c5-round2-3c11bb

- Run ID: 20261027T062531Z-macos-fixed-headless-6a430c5-round2-3c11bb
- Task ID: 2026-10-26-R278-photo-direct-rescript
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md
- Contract version: 3
- Contract SHA-256: 0e2a37aa6055f6a357a78b7345ea0c0d31d6d144076e0d18db4710aa0e39bb8d
- Source identity: 6a430c5ecc2d0df4c88b5285bb29e8bfba3b62d3
- Runtime identity: fixed-venv;playwright-1228;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-27T06:25:31.655185Z
- Completed at: 2026-10-27T06:30:33.175936+00:00
- Evidence directory: evidence/

## Scope

五代全部指定Python专项：360 passed in 153.92s (0:02:33)；真实HTML渲染三条执行，仓库安全和runtime通过。R282用替身验证配音对齐、改短与带声合成，不代表真模型或真实成片。

## Procedure

第二次交付，真实base614c550、source6a430c5；两旧卡先用Git绑定批准合同正式准备，再创建本run并实际执行。固定Playwright revision1228的headless-shell，禁止系统Chrome或回退；一次一个浏览器、渲染/门禁串行8768，R277源只读克隆；固定浏览器存在性和磁盘全程监控。没有改产品/测试/判据或安装工具，命令/时间/退出码见machine-results.json。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-02 | PASS | evidence/ | 仅本run限定机器范围 |
| AC-03 | PASS | evidence/ | 仅本run限定机器范围 |

## Findings

五代全部指定Python专项：360 passed in 153.92s (0:02:33)；真实HTML渲染三条执行，仓库安全和runtime通过。R282用替身验证配音对齐、改短与带声合成，不代表真模型或真实成片。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/machine-results.json | 76f9330e3ecf659ceadf01d09bd9d29d610d6cd14f95f1d6d1cb139248460e32 | 当前执行或明示复用的索引 |
| evidence/fixed-browser.json | 57ec96e0f392b48f1a6c17e147094f05cc266decaf4175991561711ab1054509 | 当前执行或明示复用的索引 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前执行或明示复用的索引 |
| evidence/external-dependencies.json | 1199aa3c7e229263168535babed07cff9400caf9b8ae5fcff0b72ebd2cc083ed | 当前执行或明示复用的索引 |
| evidence/route-decision.json | aef9c5bd4afb349e94d283ed5bcb01519f6c6ef5d35f8e08cafbfd1537facdff | 当前执行或明示复用的索引 |
| evidence/pytest-targeted.log | 326ce38c657520f194f11ae8c4d4acf4465f0a95e4a8ad6dd27cf64d06d0dddc | 当前执行或明示复用的索引 |
| evidence/runtime.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 当前执行或明示复用的索引 |
| evidence/live-handoff-inventory.json | a5dcbb08178457af183ff91810f4bf76d70e37cff39a37517e990b5076d28ff2 | 当前执行或明示复用的索引 |
| evidence/live-readonly-api.json | 6ce6c27287f48c7a5dd2811b84a7920dfbd92047cdc0c0b98d45a7656fde8303 | 当前执行或明示复用的索引 |
| evidence/binding-candidate-review.json | cdec8f6ded243bfdf7af3a21c4617b7690446c724cb753a744551d010decbd33 | 当前执行或明示复用的索引 |
| evidence/readonly-package-preservation.json | 2891be244d80dfc509aa702e94d6dea95ef6bb0d64464ff55bb5cd49efdd8828 | 当前执行或明示复用的索引 |

## Unverified items

人工三项PENDING。8769当前全部交接为null；P5旧包仅为真实可绑定候选（2镜、Cherry50.24秒、无本机图、版本/时间null），本线程不配置服务。H-01版本/时间及H-03更新依赖未发布R299；未知不能冒充完成。无付费模型/真实配音成片/全量pytest；同步、outline、严格截图实体归档差异照实保留。

## Conclusion

PASS：仅上述机器范围，不是当前完整中台链路、人工PASS或READY。
