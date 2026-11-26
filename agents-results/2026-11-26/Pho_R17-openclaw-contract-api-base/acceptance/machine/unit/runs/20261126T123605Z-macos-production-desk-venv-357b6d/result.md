# Acceptance Run: 20261126T123605Z-macos-production-desk-venv-357b6d

- Run ID: 20261126T123605Z-macos-production-desk-venv-357b6d
- Task ID: 2026-11-26-Pho_R17-openclaw-contract-api-base
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R17-openclaw-contract-api-base/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 397c08ea59a2b38cec15d5fc3a0373e408dc4003c1ea0d65da910768ed6809f1
- Source identity: 13b7046233ee8c0dd735d9134aba822c8099e11a
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T12:36:19Z
- Completed at: 2026-11-26T12:36:48.858858Z
- Evidence directory: evidence/

## Scope

修正尾注后在相同文件树的新源码提交上重跑，执行时间晚于重基线。重跑接口前缀传播、视频执行契约和本机 Agent 兼容。 无真实素材、无付费接口。

## Procedure

```sh
PHOTO_P1A_FROZEN_UPSTREAM=/tmp/p1a-u08-upstream "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/.venv/bin/python" -m pytest -v -p no:cacheprovider "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_wave6_bridge_contracts.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_p1a_first_project_snapshot.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_candidate_download_path.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/tests/test_openclaw_video_execution.py"
"/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/.venv/bin/python" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/scripts/openclaw_media_agent.py" contract
LOCAL_MEDIA_ROOT="/Users/vsiyo/.local/share/task-scratch/p1a-u08-p-round3/synthetic-media" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/.venv/bin/python" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u08-p/scripts/doctor.py"
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
| evidence/contract.json | f131acccdb474f7d16eff8b1a3e2220a1c2b9193e8b5122ea347e0dba6975ec8 | 本机 Agent 兼容性输出，退出码 0 |
| evidence/doctor-pairing.txt | 5a2d6332c3c53657004f85aff54d5cc5ddeacb37de8873be484508636866b8a3 | 自检配对行摘录。隔离工作区缺两个可选剪辑软件，doctor 全项退出码为 2。 |

## Unverified items

人工 H-01 尚未签署。未执行真实素材交接或发布演练。

## Conclusion

Pho_R17 的 AC-01 通过。
