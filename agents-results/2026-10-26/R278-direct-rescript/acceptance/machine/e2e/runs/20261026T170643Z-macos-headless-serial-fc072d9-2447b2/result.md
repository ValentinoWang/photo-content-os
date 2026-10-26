# Acceptance Run: 20261026T170643Z-macos-headless-serial-fc072d9-2447b2

- Run ID: 20261026T170643Z-macos-headless-serial-fc072d9-2447b2
- Task ID: 2026-10-26-R278-photo-direct-rescript
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: c09cdffe9bb97c23b7526c7dce449611d0c5eada03d8db47bbfd86c3c72ac49d
- Source identity: fc072d9694a6c807f2eafd4a4104c8e803d89b2a
- Runtime identity: fixed-venv;isolated-state;fixtures
- Executor or reviewer: Codex
- Started at: 2026-10-26T17:06:43.495190Z
- Completed at: 2026-10-26T17:12:19.755082+00:00
- Evidence directory: evidence/

## Scope

R278 Node 专项、40次逐块合同与挂载交互；包含来源标签删除、新占位、旧视频回调、样张计时和原编辑运算。

## Procedure

第二次交付，从当前fc072d9和原origin/main基底重新执行；未沿用作废提交的机器结果。先准备两旧卡rebaseline，再创建本run；命令、真实起止时间和退出码见machine-results.json。固定.venv、指定headless-shell及Playwright，DIRECT_GATE_PORT=8768，R277_SOURCE_STATE指向只读studio-r278并克隆后使用。浏览器一次一个、全部门禁串行、结束时关闭自有浏览器及临时服务。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-02 | PASS | evidence/ | 仅本run明示的确定性机器范围 |
| AC-03 | PASS | evidence/ | 仅本run明示的确定性机器范围 |

## Findings

40/40合同及挂载交互PASS，0新截图；原41张图由用户授权复用、文件和图库链接哈希核验一致，仅个人抽看两张。 未对真实作品发起生成或付费模型请求；API夹具及历史投影重放不证明新的真实模型语义或人工观感。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/r278-node.log | 6fac0ce626d2c7bea77a38a4506a6f100664e49bdc61f9c5775d57857099be33 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r278-frontend.log | 8cbd5da8bc44cc7f26cc629ca878f15979ec685dbb22033d4968de400c703826 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r278-contracts-external.json | 10b7e78fe4c6a54e01e8e99cef3bcba9720aefec3bf4fc4973b849dbc13a37eb | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/browser-evidence-summary.json | e9dea59860ba2fde8b776b7df1a90b8cd26411a6833dfc7cf5fca96855169191 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/machine-results.json | a0cb8b5368272afe24d99a6aaa11994e837c97d88bb326d69d858902fdbdfbc4 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/reused-screenshot-evidence.json | e3accb5144d27fbbbe4c24d3292009895466e892e19ceef17de2e0d4e6d0cf85 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/visual-sample-review.json | efa3fa0cf5d4c0b6b31e82d64347ec28da3b9fd81d3b397162bc41cfe2869453 | 第二次交付新运行日志或明确复用的外置证据索引 |
| evidence/r278-source-preservation-external.json | 7cf4267cc4d378bab337124c5de63e5f09d1c306621e71539197f8f0d46106a4 | 第二次交付新运行日志或明确复用的外置证据索引 |

## Unverified items

H-01至H-03仍待用户亲自验收。H-03首次215.621秒、修改168.813秒；用户2026-10-27原话「这个没事 大概差不多就行」，仅记录解释，不更改卡片文字或视作人工PASS。Obsidian时间戳、outline及全量测试已知9失败6错误另列，不包含在本限定专项PASS中。严格视觉run内实体图片要求与项目媒体外置的既有归档差异不由本run消除，不声称严格视觉归档或新全链路模型生成已通过。

## Conclusion

PASS：仅覆盖fc072d9上的上述机器范围。不是人工通过、全仓通过、部署或READY。
