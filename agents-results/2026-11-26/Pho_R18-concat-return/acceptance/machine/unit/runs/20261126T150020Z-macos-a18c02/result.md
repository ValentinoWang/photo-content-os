# Acceptance Run: 20261126T150020Z-macos-a18c02

- Run ID: 20261126T150020Z-macos-a18c02
- Task ID: 2026-11-26-Pho_R18-concat-return
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R18-concat-return/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 98442a4c3cd677fd12cc94265f316f072d73ebaa6da8eec86ad6b967a7ec00f0
- Source identity: c159863c792237c3f9ae181fc20c7537312e87a1
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T14:58:01.435562+00:00
- Completed at: 2026-11-26T14:58:46.108947+00:00
- Evidence directory: evidence/

## Scope

macOS 本机合成片段，固定提交构建的安装版隔离运行。Media 传输、Concat MCP 和桌面打开使用替身。导出检查、预览生成和媒体探测用本机 FFmpeg 与 ffprobe。

## Procedure

```sh
cd "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p"
proj="/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p"
scratch="/Users/vsiyo/.local/share/task-scratch/p1a-u19-p"
u19wheel=/tmp/p1a-u19-wheel/openclaw_media-0.2.0-py3-none-any.whl
u13wheel=/tmp/p1a-u13-wheel/openclaw_media-0.2.0-py3-none-any.whl
P1A_AGENT_WHEEL="$u19wheel" P1A_AGENT_WHEEL_SHA256=b9055aae69c49272d6adce9e451bf77a2e56c8381f8987e92cd2e2101e62960a P1A_AGENT_SOURCE_SHA=6eebfd33d P1A_EVIDENCE_PATH="$scratch/u19-wheel.json" "$proj/.venv/bin/python" -m pytest -v -p no:cacheprovider --basetemp "$scratch/pytest-u19" "$proj/tests/test_p1a_installed_concat_return.py" "$proj/tests/test_ps3_video_workflow.py"
P1A_AGENT_WHEEL="$u13wheel" P1A_AGENT_WHEEL_SHA256=ad2f1703a78b3362fe790e891ac363448596b62036807725fd734b19b8dffc39 P1A_AGENT_SOURCE_SHA=ef90bf8b31aed390d11602a5bac300ac4e6f6ecf "$proj/.venv/bin/python" -m pytest -q -p no:cacheprovider --basetemp "$scratch/pytest-u13" "$proj/tests/test_r282_handoff.py" "$proj/tests/test_p1a_installed_watch.py"
"$proj/.venv/bin/python" -m pytest -q -p no:cacheprovider --basetemp "$scratch/pytest-editors" "$proj/tests/test_concat_return.py" "$proj/tests/test_ps4_returned_candidate.py" "$proj/tests/test_ps3_openfilm_session.py" "$proj/tests/test_concat_backend.py" "$proj/tests/test_candidate_download_path.py"
"$proj/.venv/bin/python" "$proj/scripts/export_studio_openapi.py" --check
"/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/.venv/bin/python" -m pytest -q "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_edit_tools_runtime.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_openmotion_import.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_openmotion_previews.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_pho_r05_recipe_library.py"
"/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/.venv/bin/python" -m pytest -q "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_r223_music_analysis.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_r223_sections.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_r223_music_analysis_runtime.py"
CONTENT_OS_OPENFILM_PACKAGE="<固定 OpenFilm 0.1.5 路径>" CONTENT_OS_OPENFILM_NODE="<Node 路径>" PLAYWRIGHT_BROWSERS_PATH="<已安装浏览器路径>" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/.venv/bin/python" -m pytest -q -rs "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u19-p/tests/test_ps3_openfilm_session.py"
```

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/editors-pytest.txt | 保留 Concat 原四项断言，全部执行且通过。 |

## Findings

探测、核对和回传替身验证均通过。试跑显示首次建立和打开各 1 次，上传断线和租约失效后恢复期间渲染 0 次，作品读回 1 条 480 × 854 候选。旧的手填环境变量不参与回传。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/editors-pytest.txt | 5b99f483f13ba040350ff52972516760e1412fac6f3a3a1757c0f5f765690fe3 | 本次检查原始输出或测量摘要 |
| evidence/unaffected-pytest.txt | 87277d49633a1058326b88f146f175446e72affb7184852dbe8f92e8b6b3ba84 | 本次检查原始输出或测量摘要 |
| evidence/r223-pytest.txt | 4b653dbd8e7bcc4bf0c0c4a6995778275b65093f471ae98831328754e0120b71 | 本次检查原始输出或测量摘要 |
| evidence/scope-review.txt | cc628aa6e67d3bb3bf102898bb57f45a8697c1e481a472856d5c15325e339db1 | 本次检查原始输出或测量摘要 |
| evidence/openfilm-pinned-pytest.txt | 435e1687ea8104ee48cec625127ec23d2c7e4d094bc5154c8f15bb4a4ea26838 | 本次检查原始输出或测量摘要 |

## Unverified items

真实 Concat 桌面操作、真实素材和生产环境。人工验收未签署。

## Conclusion

AC-01 通过。
