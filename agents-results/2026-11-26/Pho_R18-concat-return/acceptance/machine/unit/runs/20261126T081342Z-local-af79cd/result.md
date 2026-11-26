# Acceptance Run: 20261126T081342Z-local-af79cd

- Run ID: 20261126T081342Z-local-af79cd
- Task ID: 2026-11-26-Pho_R18-concat-return
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R18-concat-return/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: f60b606d4a07b18c75a9ad8e275b12a4d0e9992119bb80123d990b6e00e21716
- Source identity: 4189a26e832aa89af453d2a3e36c263813e0f53f
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T08:13:42.434982Z
- Completed at: 2026-11-26T08:31:31.570824Z
- Evidence directory: evidence/

## Scope

AC-01。发布源码为 `4189a26e832aa89af453d2a3e36c263813e0f53f`，工作区通过 Git 比对仅在验收物路径上有差异。开发机位置判定为本机。使用替身及本机契约审计。

## Procedure

```sh
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_concat_return.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_ps4_returned_candidate.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_ps3_video_workflow.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_concat_backend.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_candidate_download_path.py
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_openmotion_import.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_openmotion_previews.py /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_pho_r05_recipe_library.py
git -C /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix diff --exit-code c93bab6 4189a26 -- acceptance/human/2026-W48/2026-11-24-Pho_R08-openmotion-recipes agents-results/2026-11-24/Pho_R08-openmotion-recipes/acceptance-contract.md tests/test_openmotion_import.py tests/test_openmotion_previews.py tests/test_pho_r05_recipe_library.py
/Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix/tests/test_edit_tools_runtime.py
git -C /Users/vsiyo/.local/share/task-worktrees/production-desk-preview-cards-fix diff --exit-code c93bab6 4189a26 -- acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo evidence/2026-10-19/R207-edit-tools-in-repo/acceptance-contract.md tests/test_edit_tools_runtime.py
```

Concat 回传、候选、视频工作流、Concat 后端和候选下载路径退出码 0（34 passed in 34.36s）。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest.txt | Concat 回传、候选、视频工作流、Concat 后端和候选下载路径退出码 0（34 passed in 34.36s） |

## Findings

- Pho_R08。在发布源码重跑 OpenMotion 导入、预览及配方库三个受保护测试文件，24 项通过。旧卡合同、人工记录与测试文件无差异。 pytest 与 Git 比对退出码均为 0。
- R207。在发布源码重跑工具运行环境受保护测试，20 项通过。README 与自检脚本的差异仅涉及上游契约快照，工具探测及路径规则保持一致。 pytest 与 Git 比对退出码均为 0。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest.txt | 77533954b2a6c7f95cd102567baeeea1b020d65d98df0f12a211f33b197272d8 | Concat 回传、候选、视频工作流、Concat 后端和候选下载路径 |
| evidence/Pho_R08-protected.txt | 6d753a98ac5231c038d5f0e3348459ee22b8d825547fcf013fcc14d53bbd34e3 | Pho_R08 受保护测试原始输出 |
| evidence/R207-protected.txt | fa7e67862d94fa32c4ea296b40095b0498ebddbbcd4fabbf31e84e145558513d | R207 受保护测试原始输出 |
| evidence/R223-runtime.txt | acfeeb81a00f614e0c4555a607f9467b8d09ba17c7b1399578bbb06d1fffb273 | R223 离线模型及 Python 专项，90 passed |
| evidence/R223-design.txt | fd5d999e2680f3fbd6573d225a12dc17a02a0c420750932cee06b7bc57e8cdb4 | R223 静态设计检查，58 份清单，0 失败 |
| evidence/R223-beat-map-browser.txt | fdefefc8c84f7a8ab43e31e590b817d65f33ec480070e2b366fb35bf14a75e9c | R223 节拍图浏览器检查，退出码 0 |
| evidence/R223-interactions-browser.txt | c1bdfe56457980b94db0fea03f866927edb61a3de5254ba1d07dc24eb87c05d0 | R223 音乐交互浏览器检查，7 项通过，退出码 0 |
| evidence/R223-studio-cleanup.txt | 8fc9572a070d05222f7b4f289dd10bf0a95128a0f01c06151098ccb6c87b4ed3 | 隔离 Studio 已关闭，端口拒绝连接 |

## R223 受保护检查

在发布源码重跑 R223 合同的全部受保护检查。90 项 Python、58 份静态设计清单及两项隔离 Studio 浏览器检查通过，旧卡合同、人工记录与测试文件在本批无变化。 Node 命令、测试结果及真实退出码见浏览器原始日志。

## Unverified items

人工验收项继续待验。未调用付费接口。

## Conclusion

本卡合同专项通过。
