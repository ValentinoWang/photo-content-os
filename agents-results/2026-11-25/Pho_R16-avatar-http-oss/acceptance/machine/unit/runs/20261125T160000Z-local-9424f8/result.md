# Acceptance Run: 20261125T160000Z-local-9424f8

- Run ID: 20261125T160000Z-local-9424f8
- Task ID: 2026-11-25-Pho_R16-avatar-http-oss
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-25/Pho_R16-avatar-http-oss/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: b825fa00c1fd69fb44df32af8ea4aa3dfd7f882fa7ebe52978702e050e6fe440
- Source identity: 9424f8c3d48f220d17ac0e9d893eb6d23793d3d3
- Runtime identity: local
- Executor or reviewer: codex
- Started at: 2026-11-25T15:51:55Z
- Completed at: 2026-11-25T15:52:11.000068Z
- Evidence directory: evidence/

## Scope

AC-01，开发机状态 local，本机测试签名 HTTP 下载、拒绝不可信地址及原数字人回归。

## Procedure

运行测试：见 evidence/pytest-result.md，31 项通过。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-result.md | 31 passed |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-result.md | 00628415307b7bccc8e1e645277b8846d2d74c87720a1b28954999c85117e1c3 | 执行命令和输出 |

## Unverified items

人工视频观感未验证。

## Conclusion

AC-01 测试通过；不代表人工验收通过。
