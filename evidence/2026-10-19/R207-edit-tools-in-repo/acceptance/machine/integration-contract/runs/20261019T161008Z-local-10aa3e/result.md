# Acceptance Run: 20261019T161008Z-local-10aa3e

- Run ID: 20261019T161008Z-local-10aa3e
- Task ID: 2026-10-19-R207-photo-edit-tools-in-repo
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-19/R207-edit-tools-in-repo/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 9052c4533ef123a8791f1a8787839d4454e223515062246d13c05eee0b2b9590
- Source identity: 493cc9aa8621227f4253f082396295c763ef5103
- Runtime identity: macos-arm64-node24.13.0-chromium149.0.7827.55
- Executor or reviewer: Codex
- Started at: 2026-10-19T16:10:08.938968Z
- Completed at: 2026-10-19T16:11:46.780994+00:00
- Evidence directory: evidence/

## Scope

AC-01 仓库内锁定工具安装、寻址和失败诊断；AC-02 临时 HOME、清空工具路径覆盖，双后端真实合成候选渲染、完整解码与进程清理。验证源码 493cc9aa8621227f4253f082396295c763ef5103。

## Procedure

稀疏检出修复后真实重跑安装、doctor、相关回归、双后端冒烟、运行时合同、文档同步、大纲和两项帮助命令，具体命令见 evidence/repair-final-checks.json。原生 OpenFilm 与全量回归日志复用同源码首次尝试中检出修复后的实际执行结果，未再次重复这两项。与旧源码的唯一差异是证据目录声明，未修改产品代码或受保护测试；旧安装及漂移修复日志仍留在历史 run。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/focused.log | 48 passed, 12 skipped, 2 subtests passed；缺失、损坏、漂移负例与安装命令通过 |
| AC-02 | PASS | evidence/smoke-repair-final.json | 双后端 4 秒合成输入裁剪为 3 秒，candidate、完整解码、无残留 PID |

## Findings

本次范围检查通过；doctor 两工具 online，0.2.16/0.1.5。相关回归的 12 skipped 为显式运行条件不足的既有分支，未冒充通过；原生 OpenFilm 2 passed。必需全量回归 8 failed, 596 passed, 32 skipped, 2 warnings, 6 errors, 1982 subtests passed，仍是未改动的字幕/PF 夹具依赖系统 FFmpeg drawtext，未修复或弱化。外部 Harness G8/G9 另由最终 delivery gate 决定，不包含在本机器 PASS。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/doc-sync.log | cf370d86c02a59b6e7b199495adce38bfccf1b7db6be2d1e31140ce53d602c45 | 实际运行日志或摘要 |
| evidence/doctor.log | 4415353b2c46072de0eea7f5d94e8d8e12f4ecc2412f4d40cc859b25060f635a | 实际运行日志或摘要 |
| evidence/draft-help.log | 56b7ab792c3517cf3756705e80c79bc7052f1f9ab9e4b2e8cc5122a9314aa62d | 实际运行日志或摘要 |
| evidence/focused.log | c4bbb47c1ac6bdd27516e894e1cfab5baba9288493e761a9b568fb09bce6f155 | 实际运行日志或摘要 |
| evidence/idempotent.log | e663bee2309abb3674a5b60892ec682f2f4450045475ced17dd4e1da0b19389f | 实际运行日志或摘要 |
| evidence/openfilm-native.log | 29e3842ec495d93c21b512c8054d32df03c68395fdcf546192ff0871b3ff9432 | 实际运行日志或摘要 |
| evidence/outline.log | 7954d4ef5f7d9f2bbcc671dff87fe47e251f1aaed3f74275334967e923ebac41 | 实际运行日志或摘要 |
| evidence/pytest-all.log | 447c0b2c25a2b2ee00fb5969bb57aad0b3b4d97ab795699e2c3aa3a24b7b1cd2 | 实际运行日志或摘要 |
| evidence/repair-final-checks.json | deb3f247849ea94607dc99a302b2f09e49ed453c779d4df0563ca7399c09f537 | 实际运行日志或摘要 |
| evidence/repair-restack.json | 40044b9982eefe45c9186e82edb5d566c7a273ac18dc77bc0690bad65b653f80 | 实际运行日志或摘要 |
| evidence/runtime-contract.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 实际运行日志或摘要 |
| evidence/smoke-repair-final.json | 82fdfefcbd97492218637a9754e70dc16e8143363f98ceda4a0e9c6e6fa24326 | 实际运行日志或摘要 |
| evidence/smoke.log | 82fdfefcbd97492218637a9754e70dc16e8143363f98ceda4a0e9c6e6fa24326 | 实际运行日志或摘要 |
| evidence/task-help.log | 3767f6ee233b6b017a497fae00b05ba2e54a056003939f6ceb9e1059ad97b135 | 实际运行日志或摘要 |

## Unverified items

不代表全量回归通过、H-01/H-02 真人通过、真实用户项目、Windows/Linux 实机或生产部署。

## Conclusion

仅 R207 AC-01/AC-02 范围机器 PASS；人工清单仍待用户复核。
