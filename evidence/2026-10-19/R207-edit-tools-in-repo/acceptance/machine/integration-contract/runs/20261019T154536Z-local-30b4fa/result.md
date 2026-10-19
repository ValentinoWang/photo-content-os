# Acceptance Run: 20261019T154536Z-local-30b4fa

- Run ID: 20261019T154536Z-local-30b4fa
- Task ID: 2026-10-19-R207-photo-edit-tools-in-repo
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-19/R207-edit-tools-in-repo/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 9052c4533ef123a8791f1a8787839d4454e223515062246d13c05eee0b2b9590
- Source identity: 190b6efd23247ea1b922341093c2ba6129748ac9
- Runtime identity: macos-arm64-node24.13.0-chromium149.0.7827.55
- Executor or reviewer: Codex
- Started at: 2026-10-19T15:45:36.804325Z
- Completed at: 2026-10-19T15:46:12.831546+00:00
- Evidence directory: evidence/

## Scope

AC-01 仓库内锁定安装、默认路径、缺失/损坏失败、环境覆盖、共享浏览器槽；AC-02 两个后端在临时 HOME 和清空覆盖下的实际合成候选渲染。源码为当前已提交的 190b6efd23247ea1b922341093c2ba6129748ac9。

## Procedure

实际运行安装、重复安装、将受管 OpenFilm 版本改为 9.0.0 后诊断并重装；提交后运行 53 项相关回归及双后端 4 秒合成输入裁剪为 3 秒的真实渲染、完整解码和资源清理检查；运行必需的运行时、同步、大纲和帮助检查。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/focused-committed.log | 53 passed, 1 skipped, 2 subtests passed；真实重复安装和漂移修复通过 |
| AC-02 | PASS | evidence/smoke-verified.json | 双后端实际候选、完整解码通过、无遗留进程 |

## Findings

本次范围内无失败。全量回归的既有字幕/PF 失败由系统 FFmpeg 缺少 drawtext 引起，另存完整失败日志；不计为本次范围通过，也未修复或弱化这些测试。下载受本机 PAC/终端代理差异和连接中断影响；保留所有失败尝试，使用既有代理与 TLS 1.2 后锁定依赖安装成功，未换版本。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/focused-committed.log | 3513343d0da278daa71d2aae0b589011bfec8302c596d3be2e079e7f62119147 | R207 scoped verification |
| evidence/smoke-verified.json | 24a9295c1c4fd37dc5bf54ac0b1ceceb7e5eb349dde43156a010fb84a3aa584c | R207 scoped verification |
| evidence/install-success.log | 62e3c1b998b1ea2215ff91dd5104eb5be32c8c588c76d6e9a94faea017737483 | R207 scoped verification |
| evidence/idempotent.log | 23b165fde39a5a3c4bc6eeaaf754da7a1f43daa63f5f28fa97a4af6ee0281c3e | R207 scoped verification |
| evidence/drift-repair.log | 67b7bb2057d74b7a4c84f64f6fe0d95173a683337c11d99aaf746b09d6677806 | R207 scoped verification |
| evidence/doctor.txt | 4415353b2c46072de0eea7f5d94e8d8e12f4ecc2412f4d40cc859b25060f635a | R207 scoped verification |
| evidence/runtime-contract.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | R207 scoped verification |
| evidence/doc-sync.log | cf370d86c02a59b6e7b199495adce38bfccf1b7db6be2d1e31140ce53d602c45 | R207 scoped verification |
| evidence/outline.log | 7954d4ef5f7d9f2bbcc671dff87fe47e251f1aaed3f74275334967e923ebac41 | R207 scoped verification |
| evidence/task-help.log | 3767f6ee233b6b017a497fae00b05ba2e54a056003939f6ceb9e1059ad97b135 | R207 scoped verification |
| evidence/draft-help.log | 56b7ab792c3517cf3756705e80c79bc7052f1f9ab9e4b2e8cc5122a9314aa62d | R207 scoped verification |

## Unverified items

未代表全量回归通过、用户真实项目、真人 H-01/H-02 验收、Windows/Linux 实机或生产部署。

## Conclusion

仅上述 R207 范围的机器验证通过；人工清单仍待用户执行。
