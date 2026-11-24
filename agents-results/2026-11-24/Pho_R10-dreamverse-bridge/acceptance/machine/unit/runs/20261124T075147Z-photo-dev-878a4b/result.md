# Acceptance Run: 20261124T075147Z-photo-dev-878a4b

- Run ID: 20261124T075147Z-photo-dev-878a4b
- Task ID: 2026-11-24-Pho_R10-dreamverse-bridge
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-24/Pho_R10-dreamverse-bridge/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 189222c79a69bd368f6a4377bce794f73d11566167e1266d8058aeeafd643981
- Source identity: 308eb2e86d264118514261a45db987632dc3cb4e
- Runtime identity: photo-dev / rbox / pytest 替身服务
- Executor or reviewer: Codex
- Started at: 2026-11-24T07:49:00Z
- Completed at: 2026-11-24T07:49:04Z
- Evidence directory: evidence/

## Scope

AC-01。实际运行任务单的 verify_unit.sh，由 rbox 在 photo-dev 执行六项替身专项测试。没有调用百炼。

## Procedure

核对命令退出码并保存原始末尾。对照冻结范围内变更与旧卡合同及受保护测试的 Git 字节。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/verify-unit-receipt.json | 六项通过，退出码 0。 |

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/verify-unit-output.txt | 55d7cc1be5b57461464a6234faad066abf511286fa71b0f7ea5829e390c9d354 | 本轮开发机验证的原始末尾 |
| evidence/verify-unit-receipt.json | 3e535a90f30468983bba0bb96f1c27b3703166d16f2f68d27a3e74e9ed7bcb0b | 启动脚本、源码摘要、结果和退出码 |
| evidence/scope-receipt.json | dfcea90e46021ba06d6cb0dbb3e22dc3279c0108a53ed98d6c3dbca691238700 | 主线改动文件及旧卡相关 Git 字节的对照 |
| evidence/prior-live-status.json | 5c5e50d7f15458b679ba8aa3b890d56efddc48caa80ed964762b7836ccbc073e | 既有真实失败摘要，当前人工状态仍待验 |

## Unverified items

H-01、H-02 仍待任务委托人验收。H-02 当前未完成：百炼账户欠费（HTTP 400 Arrearage），两次提交均未取得任务 ID，账本为 unknown。错误码来自第二次收据。

## Conclusion

开发机替身测试通过。真实生成及中断续跑尚未验收。
