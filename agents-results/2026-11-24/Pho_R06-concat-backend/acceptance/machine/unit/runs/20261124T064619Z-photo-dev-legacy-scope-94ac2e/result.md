# Acceptance Run: 20261124T064619Z-photo-dev-legacy-scope-94ac2e

- Run ID: 20261124T064619Z-photo-dev-legacy-scope-94ac2e
- Task ID: 2026-11-24-Pho_R06-concat-backend
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-24/Pho_R06-concat-backend/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 4354c92a65505d5b559bef91a8560b5589ecde9f70e7bd065cd17c521d03dd91
- Source identity: 1d158c7e3b90ad8e6330b340acede0bc7134fc42
- Runtime identity: photo-dev Ubuntu 24.04; Chrome for Testing 149; Node 24.13.0
- Executor or reviewer: Codex
- Started at: 2026-11-24T06:46:19.225200Z
- Completed at: 2026-11-24T06:47:57.195355Z
- Evidence directory: evidence/

## Scope

本次 PASS 仅指 Git 范围和失败对照成立，以及已列出的单元、等价性和设计检查通过。R223 浏览器交互在两端都退出 1，真实模型运行未执行。

## Procedure

- 在 photo-dev 对冻结源码 `1d158c7` 执行 `verify_legacy.sh unit`，115 项通过，零跳过。等价性用例从 `4d78b2a` 的 Git 对象还原旧 OpenChatCut 自动剪切筛选，逐项比较结果、顺序和非 `word` 精度错误。
- 比较 `4d78b2a..4225b88` 的 R223 前端、测试及夹具路径，确认无 diff。`studio/server.py` 在本批只向剪辑器名单加入 Concat。`1d158c7..4225b88` 仅增加验收材料。
- 同一台 photo-dev 用相同 runner、Chrome 和合成音频，在 `4d78b2a` 和 `4225b88` 重现第 22 行第 170 列的同一断言，actual `rgb(21, 32, 33)`，expected `rgb(228, 235, 235)`，退出码均为 1。`4225b88` 的设计检查验证了 58 份清单，零失败。

## Requirement disposition

| Scope | Result | Evidence | Notes |
| --- | --- | --- | --- |
| R207 H-01 | unaffected | evidence/legacy-unit-1d158c7.log | 锁定的工具安装和环境检查测试通过。 |
| R207 H-02 | unaffected | evidence/legacy-unit-1d158c7.log | 筛选逻辑原样搬到 precut.py，等价性测试逐项相同。 |
| R223 H-01 至 H-03 | unaffected | evidence/scope-receipt.json | 本批 diff 不含 R223 的前端文件，改动前后浏览器检查同样失败。 |

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/r223-browser-4d78b2a.log | 655964f6e96b4078e88239e873083ed78f0be7e583df06bfddf79f70b9efda2b | Baseline browser output, exit 1 |
| evidence/r223-browser-4225b88.log | 1bcd775b4ee3b58687a64457e3e5c3eadfae41b2c7c707479ca1e73c08e589fc | Current browser output, exit 1 |
| evidence/legacy-unit-1d158c7.log | 06f91f56ac6278f50ea5786b587caa4e1e872375338c12ff6e649f3ecbc7ea5f | Verified-head unit output, exit 0 |
| evidence/r223-design-4225b88.log | cef2043b3e04d6bfae2c4007aeb386ec83074e9f03a138112ea338d4a7fe1e91 | Design check output, exit 0 |
| evidence/scope-receipt.json | 515a6a38252cf61484de314881b7f6df3d388ed2d81e423890a37d7813caa71e | Same-failure comparison and Git scope evidence |

## Unverified items

R223 真模型用例因依赖下载超时未运行。R223 已有浏览器失败单独登记。Pho_R06 的人工 H-01、H-02 仍待任务委托人验收。
