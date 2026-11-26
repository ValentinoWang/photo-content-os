# Acceptance Run: 20261126T081457Z-local-a9b5f2

- Run ID: 20261126T081457Z-local-a9b5f2
- Task ID: 2026-11-26-Pho_R17-openclaw-contract-api-base
- Lane: machine/unit
- Status: PARTIAL
- Acceptance contract: agents-results/2026-11-26/Pho_R17-openclaw-contract-api-base/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: a5e3ab863dafe7fa2cd60eb908347320c72c4ffd5411393bffd90cdd76148df1
- Source identity: 4189a26e832aa89af453d2a3e36c263813e0f53f
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T08:14:57.708048Z
- Completed at: 2026-11-26T08:17:32.584981Z
- Evidence directory: evidence/

## Scope

在发布源码 `4189a26e832aa89af453d2a3e36c263813e0f53f` 上运行交付检查召回的已通过旧卡合同所列的 Python 专项。R223 另执行离线模型与静态设计检查。

## Procedure

```sh
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_r223_music_analysis.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_r223_sections.py
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_edit_tools_runtime.py
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_openmotion_import.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_openmotion_previews.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_pho_r05_recipe_library.py
R223_RUNTIME_TESTS=1 UI_COPY_QUALITY_CHECKER=/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/ui-copy-quality/scripts/check_ui_copy_quality.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_r223_music_analysis.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_r223_sections.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_r223_music_analysis_runtime.py
DESIGN_CONTRACT_CHECKER=/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/ui-copy-quality/scripts/check_design_contract.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/scripts/check_r223_design.py
```

设计检查在临时副本中读取发布源码已有的设计清单。

## Requirement disposition

- R223 退出码 0，见 evidence/R223.txt。
- R207 退出码 0，见 evidence/R207.txt。
- Pho_R08 退出码 0，见 evidence/Pho_R08.txt。

- R223 离线模型及 Python 专项退出码 0，90 passed。
- R223 静态设计检查退出码 0，58 份清单，0 失败。

## Findings

已执行的专项均通过。开发机 SSH 退出 255（Connection refused），本机负载检测判定不能开重活（数据卷约 3.53 GiB）。


最终交付检查 G2、G3、G8–G17 通过。G6 和 G7 仍缺 R223 H-01～H-03 的关系及覆盖证据，检查退出码 1。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/R223.txt | 002ebea44ff94018a217ab4997a90e3552c89dbe0c8dea62d09e964a90fd2103 | R223 pytest 原始输出 |
| evidence/R207.txt | fa7e67862d94fa32c4ea296b40095b0498ebddbbcd4fabbf31e84e145558513d | R207 pytest 原始输出 |
| evidence/Pho_R08.txt | 6d753a98ac5231c038d5f0e3348459ee22b8d825547fcf013fcc14d53bbd34e3 | Pho_R08 pytest 原始输出 |
| evidence/R223-runtime.txt | acfeeb81a00f614e0c4555a607f9467b8d09ba17c7b1399578bbb06d1fffb273 | R223 离线模型及 Python 专项输出 |
| evidence/R223-design.txt | fd5d999e2680f3fbd6573d225a12dc17a02a0c420750932cee06b7bc57e8cdb4 | R223 静态设计检查输出 |
| evidence/check-delivery.txt | c021101a7fdb1ab5fb4c00ae8b6e2b7a2930ac0deff99eb9f440e67d84437ddd | 指定范围的交付检查输出（去除行末空格），退出码 1 |
| evidence/check-delivery-final.txt | 5fb181354c1017798421ffebb97b7e2140d0f5098d3c1ec88865269f0dd8b6e4 | 指定范围的交付检查输出（去除行末空格），退出码 1 |
| evidence/R223-beat-map-browser.txt | fdefefc8c84f7a8ab43e31e590b817d65f33ec480070e2b366fb35bf14a75e9c | R223 节拍图浏览器检查，退出码 0 |
| evidence/R223-interactions-browser.txt | c1bdfe56457980b94db0fea03f866927edb61a3de5254ba1d07dc24eb87c05d0 | R223 音乐交互浏览器检查，7 项通过，退出码 0 |
| evidence/R223-studio-cleanup.txt | 8fc9572a070d05222f7b4f289dd10bf0a95128a0f01c06151098ccb6c87b4ed3 | 隔离 Studio 已关闭，端口拒绝连接 |
| evidence/check-delivery-round3.txt | 444a334e37725146b659551be53120b8062dfe93b89d2ac96bfbe33fa90e40d3 | 第三轮指定范围交付检查（去除行末空格），退出码 0 |

## 第三轮补充记录

在相同源码上按 R223 合同的合成音频起隔离 Studio，两项 JS 测试通过后已关停并确认端口释放。以上 PARTIAL 记录保留第二轮的历史门禁结论。第三轮指定范围 check-delivery 返回 0，G1–G17 全部通过。

## Unverified items

R223 的 tests/test_r223_beat_map.mjs、scripts/verify_r223_interactions.mjs 尚未复验。其余未执行的旧卡合同命令和人工项未判定。

## Conclusion

本记录不声明旧卡 unaffected。
