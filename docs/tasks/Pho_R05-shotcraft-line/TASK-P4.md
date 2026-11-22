<!-- drive-task-kind: full -->

## 背景

需求卡 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/acceptance/requests/2026-W47/2026-11-22-Pho_R05-shotcraft-line/`（只读），计划 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/PLAN.md`（看「宣传片产线」一节），先读这两份。

你做 P4：宣传片产线的后端，**只做排期和音轨，不做渲染**。宣传片和口播直出共用 `scripts/video_render/multi_shot.py` 渲染和 `scripts/video_render/compose.py` 合成；差别是口播按配音句子定每镜时长，宣传片按音乐小节定。你写一个脚本：读宣传片清单 + 曲目节拍图，算出每镜帧数（对齐重拍），把音乐片段（可叠音效）预混成**一条** PCM WAV，输出 multi_shot 用的渲染清单和 compose 用的合成清单。

现成接口（只读，不改）：
- 节拍图：`studio/music_analysis.py` 的 `load_beat_map(track_id, media_root=Path)`，返回 `bpm`、`meter`、`beats`、`downbeats`（秒，3 位小数）、`sections`、`duration_seconds`；失败抛 `BeatMapUnavailable`（`code` 为 unknown_track / queued / analyzing / beat_failed / result_unreadable）。曲目音频在 `<media_root>/library/music/<track_id>/` 下 `track.json` 的 `audio_file`。
- 合成：`compose.py` 的 `audio_inputs(manifest)` 校验全局 `narration_wav`：非空 PCM WAV，时长等于全部镜头帧数之和 / fps，误差不超过一帧。
- 本机真曲：媒体根 `/Users/vsiyo/Desktop/照片筛选`，曲目 `891759d6a9fc…`（Fever Pitch，125 BPM，4/4，71 个重拍，135.484 秒）。

## 不要动

- 不改 `scripts/video_render/`、`studio/`、`scripts/direct_video/lint.py`、`scripts/direct_video/shot_recipes/`、`scripts/direct_video/recipe_samples/`、`scripts/direct_video/style_library/`（P2 四条线正在同一工作区写 recipe_samples）。
- 不渲染视频、不开浏览器；不跑全量 pytest。
- 不提交、不推送；脚本里不写本机绝对路径（仓库安全检查会拦），媒体根由参数传入。
- `.venv` 已就绪，不重装。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| P4-1 | 新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/promo_plan.py`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/tests/test_pho_r05_promo_plan.py` | 新文件 | 1) 命令行 `promo_plan.py --spec <清单.json> --media-root <目录> --out <目录>`；清单字段：`track_id`、`fps`、`width`、`height`、`start_bar`（从 1 数，第几个重拍开始）、`shots`（每项 `id`、`html`、`bars` 正整数）、可选 `sfx`（每项 `shot`、`file`、`offset_frames` 整数、`gain_db`）、可选 `fade_out_seconds`。2) 每镜起止取对应重拍时间，帧边界按「累计秒数 × fps 四舍五入」算，不逐镜四舍五入后累加（避免漂移）；最后一镜结束若超出曲长或重拍不够，报 `track_too_short`。3) 用 ffmpeg 从音频截 `[起点, 起点+总帧数/fps)`，开头 30ms 淡入、末尾按 `fade_out_seconds` 淡出，叠加音效（按所在镜头起始帧加偏移），输出 48kHz 立体声 pcm_s16le，样本数精确等于 总帧数/fps×48000 取整（用 apad+atrim 补齐）。4) 输出 `render-manifest.json`（multi_shot 格式：width、height、fps、shots 的 id/html/frames/start_frame）、`compose-manifest.json`（同上 + 全局 `narration_wav` 指向 `premix.wav`）、`plan.json`（每镜起止秒、对应重拍号）。5) 错误统一成 `{"code","message"}` 写标准错误、非零退出；`BeatMapUnavailable` 的 code 原样透出。6) 测试：节拍图和音频由测试自己造（假 beat map 字典经可注入参数传入 + 正弦波 WAV），覆盖：帧边界对齐重拍（误差 ≤1 帧）、多镜累计不漂移、WAV 时长过 `compose.audio_inputs`、音效落点、重拍不够报错、节拍图不可用 code 透出。 | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/verify-P4.sh` | 退出码 0，末行打印每镜帧数和 WAV 秒数；汇报写到 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/REPORT-P4.md` |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| TEST-04 造测试数据 | 假节拍图按真实形状造（3 位小数秒、重拍是拍子子集），成功、失败、不够三个分支都有用例 | 只测成功路径 | 测试 |
| DEL-07 失败码 | 未知失败码原样透出，不用通顺话盖住 | 一律报「节拍图读取失败」 | 测试 |
| OPS-05 调 ffmpeg | 参数用列表传，不拼 shell 字符串；ffmpeg 非零时带上标准错误末 800 字 | shell=True 拼路径 | 代码 |

## 取舍裁定

- 只支持全局一条预混 WAV，不做逐镜 WAV。
- 节拍图读取一律走 `load_beat_map`，不自己解析 analysis.json；测试里通过可注入参数绕过它。
- 采样率固定 48kHz 立体声，不读配置。
- 剪映导出不做（制作台已有 `create_jianying_roughcut_draft.py`，宣传片以后要导剪映再接）。
- 本单没覆盖的细节按「最简单、与现有代码一致」自己定，写进汇报，不停下问。

## 派前核对（总控 2026-11-22 实跑）

- `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/verify-P4.sh`：退出非零，失败在「测试文件不存在」（产物未生成），入口正确。
- `compose.audio_inputs` 可从 `scripts/video_render` 导入；`load_beat_map` 对真曲读回 125 BPM、4/4、71 个重拍。

## 固定规则

- 工作区主人是派你的会话 44398e14-d34e-4fbc-b3a2-4994fcc7c48e，你是它派的执行方，不运行 claim、adopt，不为身份停下。
- 只在自己的任务工作区改动，只提交任务单授权范围内自己的改动，不回退或提交别人的改动，不杀别人的进程。其他线造成的失败只列出，由总控协调。
- 测试、构建、服务在前台跑完才读结果；服务用完自己停。汇报前确认自己起的后台命令已经结束；不以后台任务或稍后通知代替退出码。
- 每个单元只跑任务单的一条验证命令并保留真实退出码；有管道启用 pipefail。可能很长的输出（测试日志、rbox status 这类状态命令、生成文件、整份源码）不整份打印：日志和状态只读 tail -40 或 rg 出要的行，源码先 rg -n 定位再 sed -n 读区间；单条命令输出预计超过 200 行先截断。实现完成后的验收验证首次失败最多再改一次；仍失败交回 tail -40、真实退出码和 git diff --stat。写新功能时测试先红（含新组件未建导致的编译失败）、门禁命中按门禁给的修法修，都不算这里的失败，不停下。
- 任务单没覆盖的取舍，按最简单、与现有代码和用户已定规则一致来定，写进汇报「替总控定的」。只有改安全模型、稿外可见内容、需要用户本人签名或凭据、删除用户数据或改别人未提交的工作才停。
- 环境、路径、尾注、编号、缺文件、格式等机械问题就地修；门禁断言仍失败、需看图判断或证实重叠时交总控。持锁时遇到后者，先回到可重试状态并放锁。
- 写明的路径和实际实现不一致时沿 part 声明和调用链定位；确认仍在任务归属内且没有别的工作区在改，再修正并汇报。
- rbox wait <任务> 60 返回 1 表示还没跑完，继续前台等到真实结果或任务单写定的时限；到点说明仍在等什么。
- 证据命令只含直接涉及的模块测试、推送钩子要求的整仓名单和相关格式检查；额外模块另跑另报，已核实的基线红灯也另报。
- 推集成分支只跑 pre-push 逐提交检查。G16、完整 check-delivery 和交付卡留给发布分支同步。只需重拍的前端改动在线内跑门禁，合并后按项目入口登记重拍。
- 验证命令写明文件路径和解释器的绝对路径。模块名、Git 引用、-c 的值、URL 与无斜杠参数沿用其本身的写法。
- 怀疑旧红时对照干净基线、失败提交的父提交和当前提交，汇报各自退出码和通过数；基线已有的失败交总控。
- 汇报原因、现状这类结论时，每条标 A（已验证，附命令和原始输出）、B（强推断，写依据）或 C（推测）；只有 A 能写成事实，B、C 写明还差什么验证。要对照原版做出一样的东西时，同一批输入同时喂原版和新版，逐项比对、差异记表，清零才算完成。
- 有编号清单且任务单允许提交时，按完成项提交并在说明里写项号；清单完成后汇报。每条验证写真实退出码；开发机结果附原始末尾，未运行就写未运行。
- 备用开发机由任务单或提示给完整命令和工作目录，收到更正时先重读被点名的小节，再按更正后的命令继续。
- 工作区搬过家时总控开新线程。提示写明当前工作区和已有产物，执行方按记录从断点做起。
