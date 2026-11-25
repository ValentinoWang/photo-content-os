# Acceptance Run: 20261125T091539Z-local-unit-05b105

- Run ID: 20261125T091539Z-local-unit-05b105
- Task ID: 2026-11-25-Pho_R15-dreamverse-shot-controls
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-25/Pho_R15-dreamverse-shot-controls/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: c827d3129a3a5102f1e03a2706a7fe48be75bf6eae1b291680d3a0a78030966a
- Source identity: 05b10524014c2106915393db14293b3f5a5bad18
- Runtime identity: macOS / .venv / pytest + node 22.22 回环 HTTP 替身（开发机不可达）
- Executor or reviewer: Antigravity
- Started at: 2026-11-25T09:15:39Z
- Completed at: 2026-11-25T09:15:39Z
- Evidence directory: evidence/

## Scope

AC-01、AC-02：在冻结源码 05b1052 上运行 DreamVerse 全部三套离线单元测试（含既有受保护万相与 Seedance 测试及新增单镜控制测试）与运行时契约检查；另附单镜真实出片与三帧核验摘要。开发机 photo-dev 连接被拒（Connection refused），按规则在本机无重活进程（0）下执行离线测试。

## Procedure

1. 通过 task_worktree.py evidence 在源码提交 05b1052 上执行 pytest -q tests/test_dreamverse_bridge.py tests/test_seedance_provider.py tests/test_dreamverse_shot_controls.py（退出码 0，15 passed）。
2. 执行 bash scripts/check_runtime_contract.sh（退出码 0）。
3. 使用更新后的万相插件真跑单镜 empty_track（prompt_extend=false、默认负面词、5 秒 9:16 720p），证据存于仓库外 ~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25-controls/。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/verify-unit-output.txt | 桥接默认值、覆盖、清空、重确认、500 字边界及 Seedance 显式拒绝全过 |
| AC-02 | PASS | evidence/verify-unit-output.txt | 万相本地回环 HTTP 替身与 Python/TS 哈希一致，15 passed + 运行时契约通过 |

## Findings

无测试失败。按冻结范围复算，改动仅涉 DreamVerse 插件、桥接、新增单测及本需求卡；既有受保护测试与无关已通过卡（Pho_R08、R207、R223）无源码差异。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/verify-unit-output.txt | 081c734d1638586781b79ffe8db007f8ef8a29c23551abd3599576b7cf301ab3 | 单元测试、运行时契约检查与单镜真跑摘要 |
| evidence/scope-receipt.txt | 7adc1bba67391ef66b64a5a437cba0f24cd843c2ebecd02c61ffbdc50979f87b | 冻结范围、未改受保护测试与无关已通过卡核对 |

## Unverified items

H-01 成片观感与首次跑道成片的最终人工确认留待任务委托人审看签署。

## Conclusion

AC-01 与 AC-02 机器验证通过，单镜真跑三帧确认无人且无标识；人工验收 H-01 待任务委托人完成。
