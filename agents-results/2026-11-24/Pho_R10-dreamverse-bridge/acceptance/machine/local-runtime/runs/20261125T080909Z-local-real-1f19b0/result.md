# Acceptance Run: 20261125T080909Z-local-real-1f19b0

- Run ID: 20261125T080909Z-local-real-1f19b0
- Task ID: 2026-11-24-Pho_R10-dreamverse-bridge
- Lane: machine/local-runtime
- Status: PASS
- Acceptance contract: agents-results/2026-11-24/Pho_R10-dreamverse-bridge/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 189222c79a69bd368f6a4377bce794f73d11566167e1266d8058aeeafd643981
- Source identity: 1f19b0ebcc0f3f0128cce4be2cfcba3775891693
- Runtime identity: macOS / DreamVerse sandbox-exec / 真实百炼 wan2.6-t2v
- Executor or reviewer: Antigravity
- Started at: 2026-11-25T08:07:00Z
- Completed at: 2026-11-25T08:09:09Z
- Evidence directory: evidence/

## Scope

补充记录 2026-11-25 百炼充值后对 Pho_R10 万相桥接进行的本机真实两镜生成与第二镜中断续跑实测结果；仅补充机器实测说明，不改动 Pho_R10 的原机器单测记录及人工验收结论。

## Procedure

1. 独立初始化 DreamVerse 运行时并安装万相插件（--provider wanxiang --max-submissions 2），零提交检查模型目录（H-01：wan2.6-t2v，2–15 秒，五种画幅，720p/1080p，退出码 0）。
2. 真跑清晨空跑道慢推（track）与起跑器特写（blocks）两条 5 秒 9:16 720p 视频；在 blocks 云状态 RUNNING 时发送 SIGINT 中断（退出码 130），停止并重启 DreamVerse 后无 --confirm 续跑完成（退出码 0），核对中断前后 task_id 一致且仅 2 次提交。
3. 产物、账本与首/中/末抽帧保留在仓库外 ~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25/。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/real-run-summary.txt | 真实两镜出片与第二镜同云任务中断续跑通过（仅 2 次提交，总计 10 计费秒） |

## Findings

无接口报错。真实出片抽帧发现固定 prompt_extend=true 会给空跑道自动加入人物，后续已在 Pho_R15 补单镜控制。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/real-run-summary.txt | 712b8b8618762f5abac6741f244521b662ac95957aa0b3577dc2ff164875e4c4 | 2026-11-25 真实两镜与中断续跑实测摘要（原视频与账本在仓库外） |

## Unverified items

本条仅补充真实生成的机器实测记录，不替代人工验收；Pho_R10 的 H-01 与 H-02 人工结论维持待验不变。

## Conclusion

2026-11-25 百炼充值后两镜真实生成与第二镜中断续跑实测通过，证据存于 ~/.photo-content-os/evidence/dreamverse-bridge-2026-11-25/；Pho_R10 人工验收状态保持待验。
