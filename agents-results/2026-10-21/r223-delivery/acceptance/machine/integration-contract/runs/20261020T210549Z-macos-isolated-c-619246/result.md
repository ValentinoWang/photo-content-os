# Acceptance Run: 20261020T210549Z-macos-isolated-c-619246

- Run ID: 20261020T210549Z-macos-isolated-c-619246
- Task ID: 2026-10-20-R223-photo-music-beat-map
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-21/r223-delivery/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 5a2024bd9387f15a666635fbafe1fb7147500aedcfeef23772096ec4cc985d42
- Source identity: 7b8a4aa822b402f614fe1e5bec1529a726c4db83
- Runtime identity: fixed-venv+chrome;isolated-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T21:05:49.722476Z
- Completed at: 2026-10-20T21:08:16.157970+00:00
- Evidence directory: evidence/

## Scope

R223 全部后端、分段、模型、错误码和 OpenAPI；临时媒体根。

## Procedure

执行 evidence/ 中各日志记录的验证。原始图像和合成媒体在仓库外；所有持久化写入测试目录或副本。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | R223 全部后端、分段、模型、错误码和 OpenAPI；临时媒体根。 |

## Findings

原样旧 R220 诊断固定数量的环境断言失败另列；未改产品和原断言。缺工具夹具用于恢复该显示分支，真实重查仍到服务。第一轮旧 HTTP 命令遗漏媒体隔离、读取 v1 索引即被拒绝；没有分析/迁移/曲目写入，已显式绑定复制品重跑。初次合成进度夹具总数小于完成数已修正。全库历史 FFmpeg 与文档同步失败不属于本 PASS。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/r223-model.log | d18dc2228911a95a0edf88583dd35c485a65fd9dcedbd546f6560ad91324573e | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r223-tests.log | d215583cc98de61ccc755acc58fa880e8d40baec952f3cb3a1652631ec5c3f5c | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/runtime.log | 570c3247e5f051057cb3ea47ec8b91108c8ba221dcdfdb7d53a18c04b2760cb0 | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/safety.log | 491ca65b72a0e67c37d47b94ede23880e4868105dd36257792aaed7c50c23b8e | 当前源码范围的原始检查证据；本机路径已脱敏 |

## Unverified items

H-01 至 H-03 等用户验收；不证明真实平台会员账户、本轮未联网下载、不替代用户听感。没有使用或操作 8765。

## Conclusion

仅上述机器范围 PASS，绑定本合同与当前 Source identity。人工作业保持未验收，不代表全库或生产已通过。
