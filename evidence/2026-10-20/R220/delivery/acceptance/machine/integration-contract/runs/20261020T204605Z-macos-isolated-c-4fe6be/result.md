# Acceptance Run: 20261020T204605Z-macos-isolated-c-4fe6be

- Run ID: 20261020T204605Z-macos-isolated-c-4fe6be
- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-20/R220/delivery/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: f77604f0429d1e76203f71aefa694ba773d8ca192650e63010938302e196685c
- Source identity: 69ecf5550997a57a84c11eb5467356ed12d1ccd0
- Runtime identity: fixed-venv+chrome;isolated-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T20:46:05.545243Z
- Completed at: 2026-10-20T20:56:08.890709+00:00
- Evidence directory: evidence/

## Scope

旧合同三个受保护测试全部重跑，另加 HTTP、存储、完整清单、桥接与 OpenAPI 范围；60 项和七个子测试，CAS、持久化、续跑、隔离与公式。

## Procedure

执行 evidence/ 中各日志记录的验证。原始图像和合成媒体在仓库外；所有持久化写入测试目录或副本。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 旧合同三个受保护测试全部重跑，另加 HTTP、存储、完整清单、桥接与 OpenAPI 范围；60 项和七个子测试，CAS、持久化、续跑、隔离与公式。 |

## Findings

原样旧 R220 诊断固定数量的环境断言失败另列；未改产品和原断言。缺工具夹具用于恢复该显示分支，真实重查仍到服务。第一轮旧 HTTP 命令遗漏媒体隔离、读取 v1 索引即被拒绝；没有分析/迁移/曲目写入，已显式绑定复制品重跑。初次合成进度夹具总数小于完成数已修正。全库历史 FFmpeg 与文档同步失败不属于本 PASS。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/formulas.log | a8ef25232a27692b3edde9b069bef025798e7713cf785b3281186c570a5e6b86 | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r220-tests.log | 564129b6430520f1518eac9c2841f5fa7f129bffe8300163d879cb16eb510871 | 当前源码范围的原始检查证据；本机路径已脱敏 |

## Unverified items

H-01 至 H-03 等用户验收；不证明真实平台会员账户、本轮未联网下载、不替代用户听感。没有使用或操作 8765。

## Conclusion

仅上述机器范围 PASS，绑定本合同与当前 Source identity。人工作业保持未验收，不代表全库或生产已通过。
