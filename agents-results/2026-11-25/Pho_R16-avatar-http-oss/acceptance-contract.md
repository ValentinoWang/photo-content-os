# Acceptance Contract: 2026-11-25-Pho_R16-avatar-http-oss

- Task ID: 2026-11-25-Pho_R16-avatar-http-oss
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户要求执行第四轮任务单，原任务取回成功；人工 H-01 待任务委托人审看。
- Request source: acceptance/requests/2026-W48/2026-11-25-Pho_R16-avatar-http-oss/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.avatar-http-oss
- AC budget: 1
- Baseline identity: f72da6d1965cbd6f62e556e102b2cdbf54162e89
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-25-Pho_R16-avatar-http-oss

## User and scenario
数字人任务完成后，从官方结果地址取回生成视频。

## Problem
官方返回 HTTP 签名链接时，原程序拒绝下载。

## Expected outcome
官方 OSS 签名 HTTP 链接升级到 HTTPS，保留签名并取回结果；恢复已有任务不重复提交。

## Non-goals
不改动其他数字人生成功能。

## Normal path
验证官方主机与签名后升级协议并下载。

## Exception paths
非官方主机、无签名的 HTTP 地址和无效地址被拒绝。

## Invariants
不传鉴权到结果下载，禁止重定向；原受保护测试保持不变。

## Data impact
生成文件和标签保存在本机产物目录，媒体不入库。

## Permissions
任务委托人独立审看视频并签署人工结论。

## Performance and reliability
续跑使用已有任务号，不重新提交。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 官方签名链接升级并保留参数，不可信地址拒绝，既有数字人测试通过 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 查看取回的视频 | acceptance/human/2026-W48/2026-11-25-Pho_R16-avatar-http-oss/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_avatar_http_oss.py | beec8f57cd0177780ec2b1910dff83fe0afcf1d79f50b401b0e63674e563fa43 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 数字人下载和既有回归测试 | tests/test_avatar_http_oss.py | Automatic | Yes |
| H-01 | 播放取回的视频 | acceptance/human/2026-W48/2026-11-25-Pho_R16-avatar-http-oss/checklist.md#h-01 | Human | No |

## Exploratory testing
原任务已续跑取回视频及 AI 标签。

## Production monitoring and rollback
如需回退，回退本次源码提交。

## Risks and open decisions
人工视频审看待完成。
