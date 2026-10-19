# Acceptance Run: 20261019T160843Z-local-8a9c92

- Run ID: 20261019T160843Z-local-8a9c92
- Task ID: 2026-10-19-R207-photo-edit-tools-in-repo
- Lane: machine/integration-contract
- Status: FAIL
- Acceptance contract: evidence/2026-10-19/R207-edit-tools-in-repo/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 9052c4533ef123a8791f1a8787839d4454e223515062246d13c05eee0b2b9590
- Source identity: 493cc9aa8621227f4253f082396295c763ef5103
- Runtime identity: macos-arm64-node24.13.0-chromium149.0.7827.55
- Executor or reviewer: Codex
- Started at: 2026-10-19T16:08:43.990591Z
- Completed at: 2026-10-19T16:11:46.780994+00:00
- Evidence directory: evidence/

## Scope

重叠后源码的首次验收尝试，含安装、相关回归、冒烟和必需检查。

## Procedure

命令和退出码见任务根 repair-checks.json。所有日志原样保留。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | FAIL | evidence/idempotent.log | 稀疏检出未包含新顶层 third_party，锁清单读不到 |
| AC-02 | FAIL | evidence/smoke.log | 同一检出问题阻塞 probe |

## Findings

切回旧基准后，cherry-pick 新增目录仍带 skip-worktree，磁盘缺少 third_party。git sparse-checkout add third_party 修复检出，无源码改动；后续独立 run 重跑。doctor 的 --allow-offline 退出码为 0，但栏目明确 unavailable，未据退出码冒充通过。检出修复之后的原生 OpenFilm 回归通过；全量回归仍为既有 drawtext 失败，未改测试。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/doc-sync.log | cf370d86c02a59b6e7b199495adce38bfccf1b7db6be2d1e31140ce53d602c45 | 实际运行日志或摘要 |
| evidence/doctor.log | 3bceb76d4898ba82d879ce5cfdb25b1b279edabc0feb3e7d1cf8db0fef6e285b | 实际运行日志或摘要 |
| evidence/draft-help.log | 56b7ab792c3517cf3756705e80c79bc7052f1f9ab9e4b2e8cc5122a9314aa62d | 实际运行日志或摘要 |
| evidence/focused.log | 144d97802ae5aa802a0b6f7dc134352d2f204c20e6307e911145471ac846aaf6 | 实际运行日志或摘要 |
| evidence/idempotent.log | e79eca795c69ff2d7813ae16db2084af4b21946ed6e690d2eb7461ab272e58da | 实际运行日志或摘要 |
| evidence/openfilm-native.log | 29e3842ec495d93c21b512c8054d32df03c68395fdcf546192ff0871b3ff9432 | 实际运行日志或摘要 |
| evidence/outline.log | 7954d4ef5f7d9f2bbcc671dff87fe47e251f1aaed3f74275334967e923ebac41 | 实际运行日志或摘要 |
| evidence/pytest-all.log | 447c0b2c25a2b2ee00fb5969bb57aad0b3b4d97ab795699e2c3aa3a24b7b1cd2 | 实际运行日志或摘要 |
| evidence/runtime-contract.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 实际运行日志或摘要 |
| evidence/smoke.log | 443502c66568eec081126a38383f1d03719a58c8a5715c584ba08cdb9f704567 | 实际运行日志或摘要 |
| evidence/task-help.log | 3767f6ee233b6b017a497fae00b05ba2e54a056003939f6ceb9e1059ad97b135 | 实际运行日志或摘要 |

## Unverified items

此运行不支持 AC-01/AC-02 通过或人工通过。

## Conclusion

FAIL；保留失败，另建重跑，不重写成 PASS。
