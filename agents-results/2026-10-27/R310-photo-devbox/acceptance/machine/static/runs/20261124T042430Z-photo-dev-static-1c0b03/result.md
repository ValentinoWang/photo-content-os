# Acceptance Run: 20261124T042430Z-photo-dev-static-1c0b03

- Run ID: 20261124T042430Z-photo-dev-static-1c0b03
- Task ID: 2026-10-27-R310-photo-devbox
- Lane: machine/static
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R310-photo-devbox/acceptance-contract.md
- Contract version: 3
- Contract SHA-256: 4defe4814ceb15c1bd546613e2b2d55df837ee002c28ab90ab76f7bb88429873
- Source identity: e40196d47b1edb7adcebc0422f420f2bacc1f3c9
- Runtime identity: photo-dev Ubuntu 24.04
- Executor or reviewer: Codex
- Started at: 2026-11-24T04:24:30Z
- Completed at: 2026-11-24T04:24:31.792555Z
- Evidence directory: evidence/

## Scope

核对 Git 版本中的技能入口、链接、三份自测迁移字节、FFmpeg 9.0 并行安装安排、R278 最小同步分支及源码摘要。装机实测另见补登记录。

## Procedure

在 photo-dev 执行原验收范围。实际命令、远端 Git HEAD、终端输出和退出码由原始证据第 3 组保留。开始时间来自任务日志名，结束时间来自远端日志修改时间。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-03 | PASS | evidence/receipt.json | 绑定 e40196d 的实际运行 |

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/receipt.json | 980c7b25fbdcfef517793b38f734417dde39e558b526d46635fa6a0fc2a779b8 | 原始证据路径、摘要和命令组 |

## Unverified items

人工 H-01、H-02 仍待验收。此次三组检查未重装或传输实际 Studio 数据。
