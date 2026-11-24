# Acceptance Run: 20261124T075922Z-photo-dev-181938

- Run ID: 20261124T075922Z-photo-dev-181938
- Task ID: 2026-11-24-Pho_R08-openmotion-recipes
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-24/Pho_R08-openmotion-recipes/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 6a2a73357bc14edfc50af18177bf2745067b0b27b17348834d24514ab5798537
- Source identity: 1819385594ce116d77c619b099632ddb4415c93b
- Runtime identity: photo-dev Ubuntu 24.04; Node 24.13.0; Python 3.12.14
- Executor or reviewer: Antigravity
- Started at: 2026-11-24T07:59:00Z
- Completed at: 2026-11-24T07:59:28Z
- Evidence directory: evidence/

## Scope

在冻结源码 `1819385594ce116d77c619b099632ddb4415c93b` 上验证 Pho_R08 的 AC-01（OpenMotion 51 张单镜配方导入、本地渲染封面与预览样片 SHA-256 登记、fetch_clips 本地重渲分支、选配方弹窗页头与 OM 角标），并回归验证既有已通过卡 R207 与 R223 对应测试范围未受影响。

## Procedure

1. 在 photo-dev 经 rbox 运行 `verify_u2.sh` 专项测试（`test_pho_r05_recipe_library.py`、`test_openmotion_import.py`、`test_openmotion_previews.py`），24 项全部通过（0.67s，退出码 0）。
2. 在 photo-dev 经 rbox 运行含 R207 与 R223 范围的联合回归测试（加跑 `test_edit_tools_runtime.py`、`test_r223_music_analysis.py`），105 项全部通过（7.02s，退出码 0）；同时核对 `7dfa949..1819385` 未改动 R207 与 R223 的产品实现文件。
3. 在本机拉回 51 条 MP4 并逐条核对 `clips.json` 的 SHA-256 全部一致，抽查 3 条样片画面与时长，并实拍 Studio 选配方弹窗桌面 1440 与手机 390 两张截图。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/receipt.json | 专项 24 passed、联合回归 105 passed，均退出 0。 |
| R207 H-01, H-02 | unaffected | evidence/receipt.json | 未改动剪辑工具安装与筛选代码，test_edit_tools_runtime.py 在冻结源码通过。 |
| R223 H-01, H-02, H-03 | unaffected | evidence/receipt.json | 未改动音乐分析与节拍图代码，test_r223_music_analysis.py 在冻结源码通过。 |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/receipt.json | e0daf8b8ce7fdb4d6b3932359f0a081bf1e9a842872b3c31dbd0bb7dc7939bd4 | 冻结源码上的专项测试、范围回归、样片核验与弹窗截图收据 |

## Unverified items

H-01 仍待任务委托人亲自在 Studio 打开选配方弹窗按类别查看并抽一张演示离线播放验证。

## Conclusion

在冻结源码 `1819385594ce116d77c619b099632ddb4415c93b` 上，AC-01 全部机器测试通过（24/24 专项、105/105 联合回归），R207 与 R223 范围不受本批改动影响。
