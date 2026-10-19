# Acceptance Run: 20261019T234752Z-local-macos-offline-d93f10

- Run ID: 20261019T234752Z-local-macos-offline-d93f10
- Task ID: 2026-10-19-R210-photo-music-link-import
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-20/r210-music-link-import/delivery/acceptance-contract.md
- Contract version: 2
- Contract SHA-256: 04b413fea7114008aa5becf7f3f8bed7f88c9ae11402c201d4befb01718500de
- Source identity: 41fd234b422e5c5e64b1536329b64d2d424c905c
- Runtime identity: python3.13-musicdl2.14.2
- Executor or reviewer: Codex
- Started at: 2026-10-19T23:47:52.090014Z
- Completed at: 2026-10-19T23:48:19.578663+00:00
- Evidence directory: evidence/

## Scope

AC-01–AC-03 的离线协议、缓存、授权、原子写入、去重、匿名分享与隧道失败边界。已有网易云、汽水条目的本地重新测量和真实 CLI 重复导入。仅机器域；不代替人工验收。

## Procedure

执行六个音乐测试模块和新增失败文案测试、现有曲目 ffprobe/哈希/授权核验、真实 CLI 原分享文字重复导入与列表读取；用禁止 HTTP 和隧道的桩断言零请求。没有再次请求平台。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/focused.log; evidence/local-audio-readback.json | 合成成功/失败路径与已有两首真实音频；抖音缺失数据明确失败 |
| AC-02 | PASS | evidence/focused.log; evidence/cli-readback.log | 本地/NCM、哈希和编号去重；真实两首原输入零请求 |
| AC-03 | PASS | evidence/focused.log; evidence/checks.json | 实际抖音失败缓存 CLI 回放零请求零隧道；缓存、代理失败/隧道清理 |

## Findings

网易云、汽水已有真实入库证据；用户已取消抖音交付要求。真实会员曲没有样例，只做离线夹具验证。全套项目检查结果另存 phase2g，不在本次局部机器 PASS 覆盖范围。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/checks.json | 19e177908154580d005d38bf15be7c0d1e0c46be829165c26c733805337cd38c | 局部机器验证原始证据 |
| evidence/cli-readback.log | ca23a6323857181de5f63c153dcbc646d6365aabd2c26f7fbc4bbea4b2a233c9 | 局部机器验证原始证据 |
| evidence/douyin-cache-readback.log | fb22188b23c2023837310db69f2319a7810d2970425c523836e706199ad50b4e | 局部机器验证原始证据 |
| evidence/focused.log | 6135649ddf9b6aa707971023c3ee50fad677e57e61e23d5c16e2c3e30bd5c97a | 局部机器验证原始证据 |
| evidence/local-audio-readback.json | 98e11b2465f1d4836dae47b552f2d313124aed4d1d488beb5aedbdd0b29af235 | 局部机器验证原始证据 |

## Unverified items

H-01：两平台机器证据完备，待用户体验验收。H-02：机器已有去重证据，未代签人工结果。H-03：用户可任选网易云会员曲执行，当前仅离线测试。未验证发布、商用授权或任何用户账号登录态。

## Conclusion

仅以上机器域验证通过，可据此递交两平台验收卡；三项人工均待验收。推送另依 check-delivery 策略结论，不创建人工 PASS。
