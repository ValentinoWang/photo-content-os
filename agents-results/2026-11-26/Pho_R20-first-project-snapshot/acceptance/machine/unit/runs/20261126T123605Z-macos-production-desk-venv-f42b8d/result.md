# Acceptance Run: 20261126T123605Z-macos-production-desk-venv-f42b8d

- Run ID: 20261126T123605Z-macos-production-desk-venv-f42b8d
- Task ID: 2026-11-26-Pho_R20-first-project-snapshot
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R20-first-project-snapshot/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: e6ba4fb8b0b343bc5818968a6e18afc5df213ce354523c348d90f42f10b0dddf
- Source identity: 13b7046233ee8c0dd735d9134aba822c8099e11a
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T12:36:19Z
- Completed at: 2026-11-26T12:36:48.862325Z
- Evidence directory: evidence/

## Scope

修正尾注后在相同文件树的新源码提交上重跑，执行时间晚于重基线。重跑首次交接与候选下载测试。直接比对指定的只读 U08 Git 检出。 无真实素材、无付费接口。

## Procedure

```sh
PHOTO_P1A_FROZEN_UPSTREAM=/tmp/p1a-u08-upstream "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/.venv/bin/python" -m pytest -v -p no:cacheprovider "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_wave6_bridge_contracts.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_p1a_first_project_snapshot.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_candidate_download_path.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_openclaw_video_execution.py"
```

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest.txt | 19 passed，15 subtests passed，pytest 退出码 0 |

## Findings

R207、R223、Pho_R08 的冻结范围与本批变更文件无交集，合同和受保护测试内容一致。逐文件比较见 evidence/file-overlap.txt。候选下载接口前缀回归通过。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest.txt | ab6fd6273e07eb7fb7e2c03f81f752da6fa6d02c8d2e9d0c400a13f12dcded83 | Pytest 输出，移除行末空格，退出码 0 |
| evidence/file-overlap.txt | 7e186337ec66ec55f285f69b5063777f07d12ec4f1c32b8e47fcbbb27866ed3c | 逐卡比较冻结范围、受保护测试及本批变更文件 |
| evidence/check-exits.txt | e25b3ec224ebbdb65750049178a0028e5bbecb4afe2865cfead8cf52b5faaa73 | 实测退出码 |

## Unverified items

人工 H-01 尚未签署。未执行真实素材交接或发布演练。

## Conclusion

Pho_R20 的 AC-01 通过。
