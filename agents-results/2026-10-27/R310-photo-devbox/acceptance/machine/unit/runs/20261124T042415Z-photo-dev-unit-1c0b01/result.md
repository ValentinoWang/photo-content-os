# Acceptance Run: 20261124T042415Z-photo-dev-unit-1c0b01

- Run ID: 20261124T042415Z-photo-dev-unit-1c0b01
- Task ID: 2026-10-27-R310-photo-devbox
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R310-photo-devbox/acceptance-contract.md
- Contract version: 3
- Contract SHA-256: 4defe4814ceb15c1bd546613e2b2d55df837ee002c28ab90ab76f7bb88429873
- Source identity: e40196d47b1edb7adcebc0422f420f2bacc1f3c9
- Runtime identity: photo-dev Ubuntu 24.04
- Executor or reviewer: Codex
- Started at: 2026-11-24T04:24:15Z
- Completed at: 2026-11-24T04:24:22.194626Z
- Evidence directory: evidence/

## Scope

四个脚本中 ShellCheck、同步过滤、AI 边界和在线判定全部通过。ShellCheck 从开发机软件源下载到任务临时目录。Git 作者仅对合成夹具命令生效。

## Procedure

在 photo-dev 执行原验收范围。实际命令、远端 Git HEAD、终端输出和退出码由原始证据第 1 组保留。开始时间来自任务日志名，结束时间来自远端日志修改时间。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/receipt.json | 绑定 e40196d 的实际运行 |

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/receipt.json | 7e906b76378bc1213a4ea49aabec42f433028a45c8f88d3e9e3c727f66ee6e60 | 原始证据路径、摘要和命令组 |

## Unverified items

人工 H-01、H-02 仍待验收。此次三组检查未重装或传输实际 Studio 数据。
