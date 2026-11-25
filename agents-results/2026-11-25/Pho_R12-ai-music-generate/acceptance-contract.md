# Acceptance Contract: 2026-11-25-Pho_R12-ai-music-generate

- Task ID: 2026-11-25-Pho_R12-ai-music-generate
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控明确授权按任务单与需求卡 Pho_R12 递交，人工项保留真实配乐生成待验。
- Request source: acceptance/requests/2026-W48/2026-11-25-Pho_R12-ai-music-generate/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.music-ai-generate
- AC budget: 2
- Baseline identity: c934a944d04f7ebff4373c299ff96b0d071fdc4c
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-25-Pho_R12-ai-music-generate

## User and scenario

制作台使用者按提示词、目标秒数和可选 BPM，通过 WaveSpeed（ACE-Step 1.5）或阿里百炼（Fun-Music）生成纯音乐或人声配乐，经统一后处理后直接入库，后续沿用现有节拍分析、标签与选曲流程。

## Problem

出片路线总览第 4 环「配乐」原先只支持导入已有曲目，缺少按秒计费的 AI 生成配乐入口、请求缓存防重复扣费机制及统一音频后处理入库流程。

## Expected outcome

命令行 `scripts/generate_music.py` 与 `MusicLibrary.import_generated` 可对接两家服务商生成配乐、按请求摘要缓存原始与处理后音频、完成去静音/裁切/淡入淡出/-16 LUFS 响度归一，并以 `platform=ai_generated` 及 `ai_generated: true` 元数据合规入库。

## Non-goals

本次不做 Studio 页面的前端生成按钮（另出设计稿）。本次交付前不调用真实付费接口，真实生成听感留待人工验收。

## Normal path

读取钥匙串（百炼兜底读取备用环境文件）获取密钥，按请求摘要查库与缓存；未命中时向 WaveSpeed 或百炼提交任务，保存原始返回音频，经 ffmpeg 后处理后走现有 `_store` 写入音乐库索引，打印入库状态、时长、响度、花费估算与发片「AI 生成」标识提示。

## Exception paths

缺密钥、读不到钥匙串或备用文件、AccessDenied/401/403 及提交前网络错误或超时均不落盘失败缓存，排障后可直接重跑。服务商受理后写 `pending`，其后失败转 `failed` 并默认拦截，人工确认后通过 `--retry-failed` 改名留档旧失败记录再重试；`pending` 始终拦截并给出任务号与缓存目录。

## Invariants

相同请求参数命中库内记录或成功缓存时零网络请求、不重复付费；读不到密钥或缓存文件绝不当成未配置或空库；现有音乐库导入、分析、筛选与 v2 规范完全兼容。

## Data impact

扩展 `schemas/music-track.schema.json` 允许 `platform=ai_generated`、`sources[].kind=generated` 与 `ai_generated`/`generation` 字段；私有缓存与原始音频留在素材根 `library/music/.ai-generate/<摘要>/`，不进 Git。

## Permissions

执行方运行离线假 HTTP 与真实 ffmpeg 后处理测试。任务委托人在配好本人 WaveSpeed 或百炼密钥后验收真实生成与听感。

## Performance and reliability

不自动重试已受理的付费请求；原始返回音频和后处理音频原子落盘；失败记录改名留档不删除。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 两家假 HTTP 覆盖直出成功、异步轮询、AccessDenied、缺密钥与不可读报错；受理前失败不锁缓存，受理后失败拦截且 `--retry-failed` 留档重跑，`pending` 始终拦截并报告任务号与缓存目录 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/unit | ffmpeg 现场合成「2s 静音+35s 正弦+3s 静音」后处理输出 30.0±0.05s、首尾无 ≥0.1s 静音、响度 -16±1 LUFS；入库通过 v2 schema、重复入库返回已在库里，且原有 4 组音乐测试、运行时契约与音乐分析注册表检查全过 | Unit | Automatic | Yes |

## Human acceptance

配好 WaveSpeed 或百炼 Fun-Music 密钥后实际生成一段 30 秒温暖吉他配乐并核对入库标记与听感，当前保持待验。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 实测生成 30 秒温暖吉他配乐并核对音乐库标记与听感 | acceptance/human/2026-W48/2026-11-25-Pho_R12-ai-music-generate/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_music_ai_generate.py | 1cc9c9a612bf7a7930bb2513568bf9a2c3ac3175e5b357cbfd8b817ba0ea3de8 | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 离线假 HTTP 与缓存边界专项测试 | tests/test_music_ai_generate.py | Automatic | Yes |
| AC-02 | 真实 ffmpeg 后处理与原有 4 组音乐测试回归 | tests/test_music_ai_generate.py | Automatic | Yes |
| H-01 | 本机真实密钥生成 30 秒配乐并收听核对 | acceptance/human/2026-W48/2026-11-25-Pho_R12-ai-music-generate/checklist.md#h-01 | Human | No |

## Exploratory testing

未安排探索性验证。

## Production monitoring and rollback

本轮未改动既有导入链路与 Studio 前端，需要时可仅停止调用 `scripts/generate_music.py` 或回退本需求提交。

## Risks and open decisions

真实付费接口的国内连通性、WaveSpeed 空歌词人声行为及百炼 `WorkspaceId` 专属域名与生成时长分布待 H-01 实测确认。
