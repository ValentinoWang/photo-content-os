# R312 交付准备：剪第一版时烧字幕在新版 ffmpeg 上恢复正常

任务卡：「剪第一版时烧字幕在新版 ffmpeg 上恢复正常 · 需求卡（2026-10-27-R312-photo-ffmpeg9-subtitles）」。任务 worktree：`~/.local/share/task-worktrees/photo-content-os-ffmpeg9-subtitles`，基于 origin/main `78b6e41`。

## 已做（总控提交）

- `2c4ff30`：`scripts/video_subtitles.py` 烧字幕的 `-filter_complex_script` 改成 `-/filter_complex`；`scripts/review_output_video.py` 场景抽帧的 `-vsync` 改成 `-fps_mode`；`tests/test_output_video_review.py` 加 `test_scene_change_frames_are_extracted`（旧代码上 0 帧、红）；`tests/test_full_checklist_acceptance.py` 的令牌改成 R280 认可的浅色值，并查视频区 `--media-bg:#0D1314`。
- `5d62356`：只改技能说明 `.agents/skills/photo-remote-dev-box/SKILL.md`。verified head 是它。
- 开发机全量（2c4ff30 的同一份代码）：1214 过、3 红（Obsidian 库 1 项、melt 7.4 两项，都是开发机环境差异，见 SKILL.md）、36 跳过。原来本机也红的 9 项全绿。

## 要你做的

照 R310 的做法给 R312 递交验收卡：G1、G12、G16 通过，其余如实。

1. 先读 SKILL.md（`.agents/skills/photo-remote-dev-box/SKILL.md`）和 Core 交付规则；参照样例 `agents-results/2026-10-27/R310-photo-devbox/`。
2. 在 verified head `5d62356` 上重跑机器证据，全部经 `.agents/skills/photo-remote-dev-box/scripts/rbox` 在开发机上跑（本机不跑 pytest、浏览器）：
   - 定向：`tests/test_direct_video_subtitles.py tests/test_bilingual_subtitles_r6.py tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests tests/test_output_video_review.py tests/test_full_checklist_acceptance.py`；
   - 全量：`RBOX_QUEUE=heavy … bg … -- .venv/bin/python -m pytest -q -p no:cacheprovider -rfE tests`，只允许那 3 项环境差异红，逐项写进证据；
   - 写明是开发机（ffmpeg 9.0.2、Noto 字体、melt 7.4），和本机的差异照 SKILL.md。
3. handoff：`--request-id 2026-10-27-R312-photo-ffmpeg9-subtitles`，`--non-blocking`，`--estimated-minutes 5`，`--required-role` 任务委托人，H-01 原样。
4. 检查 G16：本任务改了 `tests/test_full_checklist_acceptance.py`、`tests/test_output_video_review.py`、`tests/test_pf_video_pipeline.py` 相关代码路径；如果它们受旧卡保护，按 Core 规则在同一次交付里处理（rebaseline），不放宽、不绕过。
5. check-delivery `--range origin/main..HEAD`，结果原样写进本目录 `REPORT.md`。只提交验收物（`acceptance/**`、`agents-results/**`，`git add -f` 只加需要的，包括本 TASK.md），不推送。

## 不要动

- 不改 `scripts/`、`studio/`、`tests/`、技能、AGENTS.md；发现问题写进 REPORT.md 后停下。
- 不碰开发机上的真实数据，不起常驻服务，不推送，不杀别人的进程。
- 本机磁盘只剩 2–3 GB（交换文件 8 GB）：不在本机写大文件，证据里不放视频和原尺寸帧。

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
|---|---|---|---|
| 提交和递交验收 | G16 必须过；改了受保护测试要同一次交付更新那些卡 | 读不到旧卡合同就当成不相关 | `harnessctl acceptance check-delivery --project . --range origin/main..HEAD` |
| 提交证据 | `git add -f` 只加合同需要的文件；不放本机绝对路径 | 整目录 add；汇报里写本机完整路径 | `python3 scripts/check_repository_safety.py --base origin/main` |
| 说「通过」之前 | 只说真正跑通的；3 项环境差异、开发机字体和 melt 差异写明 | 把开发机全量写成全绿 | 汇报逐条对照 |
| 在本机跑测试和浏览器 | 本机不跑 pytest、浏览器 | 本机直接 `.venv/bin/python -m pytest` | 汇报写明本机重活进程数 |
