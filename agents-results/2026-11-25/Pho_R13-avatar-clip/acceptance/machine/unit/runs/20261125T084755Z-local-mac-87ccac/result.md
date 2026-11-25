# Acceptance Run: 20261125T084755Z-local-mac-87ccac

- Run ID: 20261125T084755Z-local-mac-87ccac
- Task ID: 2026-11-25-Pho_R13-avatar-clip
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-25/Pho_R13-avatar-clip/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 5ce0d6f78021bec664fe45c5031f53017338fff7fe41095b078cb39f89ed565b
- Source identity: 0556ebbd405fc6228e8d63d1fa36cb2ec356a7df
- Runtime identity: local-mac / production-desk .venv / pytest / 替身传输层（开发机离线）
- Executor or reviewer: Antigravity
- Started at: 2026-11-25T08:44:38Z
- Completed at: 2026-11-25T08:44:53Z
- Evidence directory: evidence/

## Scope

在本机（开发机离线）执行 Pho_R13 数字人口播片段替身专项测试，覆盖切段、同意校验、账本落盘续查、明确拒绝重试、欠费单独报错、结果未知阻断与解锁以及 AI 生成标记。全程使用替身传输层，不调用任何百炼或其他付费接口，不运行 `--live`。

## Procedure

执行 `"/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar/tests/test_avatar_videoretalk.py`。
工作区 HEAD 与 Source identity 一致（`0556ebbd405fc6228e8d63d1fa36cb2ec356a7df`）。命令退出码 0，29 passed in 10.44s。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-avatar-output.txt | 默认试算、同意校验、静音/硬切分段、提交轮询、AI 生成标记、中断续查与输入变更重提 |
| AC-02 | PASS | evidence/pytest-avatar-output.txt | 4xx 明确拒绝可重试、欠费单独报错、结果未知阻断重提与带原因解锁重试 |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-avatar-output.txt | 8d9769b82a9101d4f297534f5dffa10d2de9d73d971a1aa0dd08c4e2db3cd8e6 | 本机替身专项 pytest 执行命令与原始输出（29 passed） |

## Unverified items

真实百炼声动人像（videoretalk）付费生成、口型同步成片效果与真实云端二次沿用留待任务委托人确认费用后执行 H-01 核对。

## Conclusion

本机替身专项 29 项全部通过，未调用任何付费接口。人工项 H-01 待任务委托人确认费用后完成验收。
