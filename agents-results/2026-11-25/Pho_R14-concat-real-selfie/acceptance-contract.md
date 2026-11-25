# Acceptance Contract: 2026-11-25-Pho_R14-concat-real-selfie

- Task ID: 2026-11-25-Pho_R14-concat-real-selfie
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控验收三张抽帧与 Concat 界面截图通过并明确授权递交验收卡，人工项留待任务委托人复核真机成片与工程。
- Request source: acceptance/requests/2026-W48/2026-11-25-Pho_R14-concat-real-selfie/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.concat-real-selfie
- AC budget: 2
- Baseline identity: c00096f796ffeb9534674f48b324ab8e47cdfeec
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-25-Pho_R14-concat-real-selfie

## User and scenario

内容创作者使用已有本机 FunASR 转写的真实竖屏自拍口播视频，依次经删减计算、转写转源字幕和 Concat 后端，生成可打开精修的粗稿工程与成片。

## Problem

仓库缺少将 `audio_transcript_v1` 转成源时间轴 `.srt` 的独立命令行入口；同时 `concat_adapter` 未读取手机竖屏视频的旋转元数据（`side_data_list.rotation` / `tags.rotate`），导致 90°/270° 旋转竖屏素材被建成 1920×1080 横屏工程并导出带左右黑边的成片。

## Expected outcome

1. `scripts/transcript_to_srt.py` 将 `audio_transcript_v1` 转为源时间轴 `.srt`，复用 `srt_timestamp`，按停顿/12 字上限/句读切条并去除中文单字间多余空格，非法输入与覆盖源路径明确拒绝。
2. `scripts/edit_backends/concat_adapter.py` 按旋转后的显示宽高创建与导出 Concat 工程，真实自拍竖屏素材输出全满 1080×1920 无黑边成片，单行字幕清晰，工程可在 Concat 打开修改保存。

## Non-goals

不在本机安装 `funasr`、不下载模型、不调用云端转写；不等待三分钟以上长口播拍摄；不修改其他剪辑后端或 Studio 页面。

## Normal path

读取 `audio_transcript_v1` JSON → 运行 `scripts/spoken_edit.py` 生成删减建议 → 运行 `scripts/transcript_to_srt.py` 生成源 `.srt` → 调用 `edit_backends.execution.render(backend_id="concat")` 建立 1080×1920 Concat 工程并导出 MP4 → 用 `concat --project` 打开工程精修保存。

## Exception paths

转写 schema 非法、状态未就绪、时间倒序、空段落或输出覆盖输入文件时 `transcript_to_srt.py` 返回非零退出码；旋转元数据缺失或为 0°/180° 时保留原编码宽高。

## Invariants

已有 Concat 单测与受保护基线不回归；私有真人素材与抽帧留在 `~/.photo-content-os/evidence/concat-real-run/`，不进入 Git 仓库。

## Data impact

仅新增只读转换脚本与回归测试；不修改原始素材文件、不改动既有项目数据存储格式。

## Permissions

执行方运行离线单元测试与本机真机自拍验证；任务委托人按 H-01 复核本机成片与 Concat 工程。

## Performance and reliability

两段真实自拍（22 秒 / 11.7 秒）全链渲染耗时均在 10 秒内，导出音画时长误差小于 1 帧，Concat 进程随上下文与 PID 校验干净退出无残留。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | `transcript_to_srt.py` 词级按停顿/字数/句读切条、去中文多余空格、回读 SRT 一致，且拒绝非法输入与覆盖输入 | Unit | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/unit | `concat_adapter.py` 按 `side_data_list.rotation` / `tags.rotate` 正确计算 90°/270° 显示宽高（1080×1920），现有剪辑后端及运行契约检查全通过 | Unit | Automatic | Yes |

## Human acceptance

请在本机打开 `~/.photo-content-os/evidence/concat-real-run/clip1-campus/concat-run/candidate.mp4` 和它的 Concat 工程（`~/.photo-content-os/evidence/concat-real-run/clip1-campus/concat-run/concat-project`）：确认竖屏全满无黑边，口误重复那句被剪掉，字幕单行可读，工程能打开改一处并保存。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 核对真实自拍 Concat 成片画幅、剪辑、单行字幕及工程可改保存 | acceptance/human/2026-W48/2026-11-25-Pho_R14-concat-real-selfie/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_transcript_to_srt.py | 611ac6e74900fd0b21d6a1a4c6f047d6bf8a0833e9d22c521cb2e20ddeac77b2 | AC-01 |
| tests/test_concat_real_selfie.py | 7e9281b6469871d3b4d6acc37f3923171091d3c4b28f7bc2edaa93c156767ff9 | AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 本机 pytest 单元测试与 CLI 校验 | tests/test_transcript_to_srt.py | Automatic | Yes |
| AC-02 | 本机 pytest 旋转画幅回归 + 现有剪辑/口播单测 + 运行契约检查 | tests/test_concat_real_selfie.py | Automatic | Yes |
| H-01 | 任务委托人复核本机真实自拍成片与 Concat 工程 | acceptance/human/2026-W48/2026-11-25-Pho_R14-concat-real-selfie/checklist.md#h-01 | Human | No |

## Exploratory testing

已用两段真实自拍短口播（22.0s 校园近景、11.7s 机场抵达）实跑全链并抽 10 帧与截取 Concat 界面图目视核验；长于 3 分钟的真人口播待用户拍好后补充实测。

## Production monitoring and rollback

两项改动彼此独立且只影响新增 CLI 与 Concat 工程画幅计算；如需回退，直接撤销单笔源码提交即可恢复原行为。

## Risks and open decisions

当前素材根暂无 3 分钟以上真人口播视频且本机未装 FunASR 模型，本次验证基于两段既有本机转写的真实自拍短口播；长口播实测待后续素材就绪。
