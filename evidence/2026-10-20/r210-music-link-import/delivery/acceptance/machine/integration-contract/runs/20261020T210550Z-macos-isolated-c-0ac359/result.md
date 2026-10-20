# Acceptance Run: 20261020T210550Z-macos-isolated-c-0ac359

- Run ID: 20261020T210550Z-macos-isolated-c-0ac359
- Task ID: 2026-10-19-R210-photo-music-link-import
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-20/r210-music-link-import/delivery/acceptance-contract.md
- Contract version: 3
- Contract SHA-256: df5810569bd7306524a29c4e5f24a450aa183bffbe9e81ad7a2a4d7034fc29bc
- Source identity: 7b8a4aa822b402f614fe1e5bec1529a726c4db83
- Runtime identity: fixed-venv+chrome;isolated-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T21:05:50.015382Z
- Completed at: 2026-10-20T21:08:16.166858+00:00
- Evidence directory: evidence/

## Scope

旧合同全部七个受保护测试模块；89 项。复制品的三个音频重新测量、哈希核对，两个原分享链接在网络拒绝下运行真实 CLI 去重；会员与抖音边界离线。

## Procedure

执行 evidence/ 中各日志记录的验证。原始图像和合成媒体在仓库外；所有持久化写入测试目录或副本。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/ | 旧合同全部七个受保护测试模块；89 项。复制品的三个音频重新测量、哈希核对，两个原分享链接在网络拒绝下运行真实 CLI 去重；会员与抖音边界离线。 |
| AC-02 | PASS | evidence/ | 旧合同全部七个受保护测试模块；89 项。复制品的三个音频重新测量、哈希核对，两个原分享链接在网络拒绝下运行真实 CLI 去重；会员与抖音边界离线。 |
| AC-03 | PASS | evidence/ | 旧合同全部七个受保护测试模块；89 项。复制品的三个音频重新测量、哈希核对，两个原分享链接在网络拒绝下运行真实 CLI 去重；会员与抖音边界离线。 |

## Findings

原样旧 R220 诊断固定数量的环境断言失败另列；未改产品和原断言。缺工具夹具用于恢复该显示分支，真实重查仍到服务。第一轮旧 HTTP 命令遗漏媒体隔离、读取 v1 索引即被拒绝；没有分析/迁移/曲目写入，已显式绑定复制品重跑。初次合成进度夹具总数小于完成数已修正。全库历史 FFmpeg 与文档同步失败不属于本 PASS。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/local-readback.log | 9ff921f73e3c0aaf10046424973181f084bf4512c0dc9f70306a4bde8f4314a5 | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r210-tests.log | 4e9fd2ce0b29a03ce63ba5604905ac4ac374960eced075a9e7c4bc782d1184c3 | 当前源码范围的原始检查证据；本机路径已脱敏 |

## Unverified items

H-01 至 H-03 等用户验收；不证明真实平台会员账户、本轮未联网下载、不替代用户听感。没有使用或操作 8765。

## Conclusion

仅上述机器范围 PASS，绑定本合同与当前 Source identity。人工作业保持未验收，不代表全库或生产已通过。
