# Acceptance Run: 20261019T172042Z-local-macos-offline-948a4d

- Run ID: 20261019T172042Z-local-macos-offline-948a4d
- Task ID: 2026-10-19-R210-photo-music-link-import
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: evidence/2026-10-20/r210-music-link-import/delivery/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: caa196481bf08abcd7f45eb12f7324ef135f6bf6b5b379c0198db9e1766cd43d
- Source identity: 73895b1b3f4e4d5ccd081e24b8d2de3e8187347f
- Runtime identity: python3.13-musicdl2.14.2
- Executor or reviewer: Codex
- Started at: 2026-10-19T17:20:42.386333Z
- Completed at: 2026-10-19T17:21:30.049867+00:00
- Evidence directory: evidence/

## Scope

AC-01–AC-03 的离线协议、缓存、授权、原子写入、去重、匿名分享与隧道失败边界。已有网易云、汽水条目的本地重新测量和真实 CLI 重复导入。仅机器域；不代表三平台真实导入通过。

## Procedure

执行六个音乐测试模块、现有曲目 ffprobe/哈希/授权核验、真实 CLI 原分享文字重复导入与列表读取；用禁止 HTTP 和隧道的桩断言零请求。没有再次请求平台。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/focused.log; evidence/local-audio-readback.json | 合成成功/失败路径与已有两首真实音频；抖音缺失数据明确失败 |
| AC-02 | PASS | evidence/focused.log; evidence/cli-readback.log | 本地/NCM、哈希和编号去重；真实两首原输入零请求 |
| AC-03 | PASS | evidence/focused.log; evidence/checks.json | 手机匿名分享不跟跳、缓存和代理失败/隧道清理 |

## Findings

已知产品缺口：抖音分享页没有作品音乐，尚未入库；完整三平台目标未达到。真实会员曲没有样例。全套项目检查的既有失败另存 phase2f 检查日志，不在本次局部机器 PASS 覆盖范围。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/checks.json | a9eea27aeb8c92a8d4a33b8b1e6d30ed318b5d5bd76fb68a8910993769b04cc7 | 局部机器验证原始证据 |
| evidence/cli-readback.log | ca23a6323857181de5f63c153dcbc646d6365aabd2c26f7fbc4bbea4b2a233c9 | 局部机器验证原始证据 |
| evidence/focused.log | beff4504ec32cf4a0ad6815392bf88bceb97e538fc2bb69bb0f4ff682f8fb35e | 局部机器验证原始证据 |
| evidence/local-audio-readback.json | 98e11b2465f1d4836dae47b552f2d313124aed4d1d488beb5aedbdd0b29af235 | 局部机器验证原始证据 |

## Unverified items

H-01：抖音待处理，不能判通过。H-02：机器已有去重证据，未代签人工结果。H-03：待用户提供会员曲链接。未验证发布、商用授权或任何用户账号登录态。

## Conclusion

仅以上机器域验证通过，可据此递交部分交付验收卡。总体交付未就绪，不推送；不创建人工 PASS。
