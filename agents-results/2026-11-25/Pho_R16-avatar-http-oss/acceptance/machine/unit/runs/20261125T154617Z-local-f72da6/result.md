# Acceptance Run: 20261125T154617Z-local-f72da6

- Run ID: 20261125T154617Z-local-f72da6
- Task ID: 2026-11-25-Pho_R16-avatar-http-oss
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-25/Pho_R16-avatar-http-oss/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: b825fa00c1fd69fb44df32af8ea4aa3dfd7f882fa7ebe52978702e050e6fe440
- Source identity: f72da6d1965cbd6f62e556e102b2cdbf54162e89
- Runtime identity: local
- Executor or reviewer: codex
- Started at: 2026-11-25T15:46:00Z
- Completed at: 2026-11-25T15:46:17.587113Z
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
| evidence/pytest-result.md | 2acb59dde60cf11288eb0935e57c696034f93851527e509c8f1f1a5e51190193 | 执行命令和输出 |

## Unverified items

人工视频观感未验证。

## Conclusion

AC-01 测试通过；不代表人工验收通过。
