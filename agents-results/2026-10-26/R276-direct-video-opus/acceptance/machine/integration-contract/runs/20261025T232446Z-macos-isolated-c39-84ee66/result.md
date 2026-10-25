# Acceptance Run: 20261025T232446Z-macos-isolated-c39-84ee66

- Run ID: 20261025T232446Z-macos-isolated-c39-84ee66
- Task ID: 2026-10-26-R276-photo-direct-video-opus
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: f62a10c6c6038f7ce122bc243bce4a301bcb954bfe95912e4c0672a34dab21fc
- Source identity: c39b465f696856babc835ea6893196240d9198e9
- Runtime identity: fixed-venv;real-renderer;temporary-state
- Executor or reviewer: Codex
- Started at: 2026-10-25T23:24:46.817113Z
- Completed at: 2026-10-25T23:26:21.509731+00:00
- Evidence directory: evidence/

## Scope

后端任务、HTTP 接口、真实 HTML 渲染、合成和输出时间；H-03 只以单镜重写后端不变性测试与原 B 真跑证据证明，不保护前端详情 DOM。

## Procedure

在 c39b465、产品及测试无未提交修改的工作区执行任务单第二段要求；证据原始日志均在 evidence/。已有 .venv 仅用于执行，未修改链接；8765/8766 未访问，独立 8767 已收尾。源日志先执行后装配进本 run，不将 run 创建时间当成重新执行命令的时间。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅以下明示范围 |
| AC-02 | PASS | evidence/ | 仅以下明示范围 |
| AC-03 | PASS | evidence/ | 仅以下明示范围 |

## Findings

134 tests passed in 21.68 seconds；H-03 独立 1 passed in 0.48 seconds；Node 回归 PASS；浏览器 26 comparisons、31 captures 和交互 PASS；仓库安全检查 PASS。模型执行使用假可执行文件，浏览器使用仓库原有投影夹具；没有付费模型调用或新作品生成。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/b-h03-proof.json | 42cf935dd0230f59f112512f2f151cadb981866e7e7ed94122083a6af0521662 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/h03-backend-invariance.log | 0c33791aa03cbc8826ba04efd1b062adb3baa875c47625e4de7090bd753d7635 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/h03-evidence-binding.json | e055be9ab741ab0832797bfb23130479b9dcc13a94c0daa8faebfdeb91bcacfe | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/protected-tests.json | 14daab841e95f2be9f8e990e0d2f8c67bcd3391b6166984a8415cc97936efc79 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/pytest-r276.log | 5c1be040c43019b9aa151a49bfca5ddc469eac0436ee602a976e4f6704dbcb24 | 当前源码上的执行结果或明确来源的既有证据 |
| evidence/repository-safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前源码上的执行结果或明确来源的既有证据 |

## Unverified items

H-01、H-02、H-03 均等用户亲自验收，七镜带声同步观感仍未新实测。既有真实 B 证据不冒充当前新跑。媒体继续留仓库外；Core 要求 run 内截图实体的严格归档规则与项目外置规则冲突仍未解决，外部清单不称该门禁 PASS。夹具完成态 composedAt 未随旧时钟平移，可能显示 0:00；耗时公式由独立 Node 正反例证明，不靠这张截图判断。

## Conclusion

本 run 在合同第 2 版与指定源码身份上的上述机器范围 PASS；不代表全仓、严格视觉归档、人工验收或可推送。
