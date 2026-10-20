# Acceptance Run: 20261020T204605Z-macos-isolated-c-d843bd

- Run ID: 20261020T204605Z-macos-isolated-c-d843bd
- Task ID: 2026-10-20-R220-photo-studio-ia-preview
- Lane: machine/e2e
- Status: PASS
- Acceptance contract: evidence/2026-10-20/R220/delivery/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: f77604f0429d1e76203f71aefa694ba773d8ca192650e63010938302e196685c
- Source identity: 69ecf5550997a57a84c11eb5467356ed12d1ccd0
- Runtime identity: fixed-venv+chrome;isolated-media
- Executor or reviewer: Codex
- Started at: 2026-10-20T20:46:05.899189Z
- Completed at: 2026-10-20T20:56:08.945905+00:00
- Evidence directory: evidence/

## Scope

26 项完整浏览器走查；实际合成 H.264 派生镜头和成片、复制品真实音频，经真实服务解码播放；29 状态四宽、33 组数字与文案编号检查。缺工具诊断、异常状态和外部平台边界明确使用夹具。

## Procedure

执行 evidence/ 中各日志记录的验证。原始图像和合成媒体在仓库外；所有持久化写入测试目录或副本。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/ | 26 项完整浏览器走查；实际合成 H.264 派生镜头和成片、复制品真实音频，经真实服务解码播放；29 状态四宽、33 组数字与文案编号检查。缺工具诊断、异常状态和外部平台边界明确使用夹具。 |
| AC-03 | PASS | evidence/ | 26 项完整浏览器走查；实际合成 H.264 派生镜头和成片、复制品真实音频，经真实服务解码播放；29 状态四宽、33 组数字与文案编号检查。缺工具诊断、异常状态和外部平台边界明确使用夹具。 |

## Findings

原样旧 R220 诊断固定数量的环境断言失败另列；未改产品和原断言。缺工具夹具用于恢复该显示分支，真实重查仍到服务。第一轮旧 HTTP 命令遗漏媒体隔离、读取 v1 索引即被拒绝；没有分析/迁移/曲目写入，已显式绑定复制品重跑。初次合成进度夹具总数小于完成数已修正。全库历史 FFmpeg 与文档同步失败不属于本 PASS。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/browser-fixture-final.log | 3a198b736da1d5d49ff4b1789d82360ebed0e3811604687ad87fb62e92f043e4 | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r220-design-check.json | a022067f8865f5889fafbc79009b87dfda130f0178d32b21f3e4516106079f2f | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r220-four-gates.json | 2e2684861ace0a0d882125ef0c5390d612c5c2ca469b404039143364eb114d44 | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r220-number-formulas.json | 1817030e7cbf71c4690b7e27304fe93a4ee53a118ff212eb06307098a501ec6c | 当前源码范围的原始检查证据；本机路径已脱敏 |
| evidence/r220-screenshot-manifest.json | 47854c0b820ad7e3becf25d21ac092a4f4d300aa31e09caea2441ba64d82b585 | 当前源码范围的原始检查证据；本机路径已脱敏 |

## Unverified items

H-01 至 H-03 等用户验收；不证明真实平台会员账户、本轮未联网下载、不替代用户听感。没有使用或操作 8765。

## Conclusion

仅上述机器范围 PASS，绑定本合同与当前 Source identity。人工作业保持未验收，不代表全库或生产已通过。
