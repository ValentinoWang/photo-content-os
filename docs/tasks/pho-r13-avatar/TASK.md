<!-- drive-task-kind: full -->

# Pho_R13 用配音和底片生成数字人口播片段（命令和程序接口）

需求卡：`acceptance/requests/2026-W48/2026-11-25-Pho_R13-avatar-clip/`（已在本工作区，随第一笔提交一起提交）。

用户原话（2026-11-24）：「我觉得所有的内容都可以按照这个文档进行落实」（出片路线图分叉 A「数字人出镜」）。调研结论：`~/Desktop/创业项目/内容创作/RefShelf/docs/decisions/2026-11-25-voice-clone-avatar.md`。

| 卡面条目 | 落到哪 |
| --- | --- |
| 拿配音和本人正面底片，生成口型对上配音的口播视频 | 单元 A1、A2 |
| 超过约 110 秒的配音按停顿切段分别生成，再按顺序拼成一段 | 单元 A1 |
| 中断后重跑查已有任务，不重复提交、不重复收费；结果未知时停下 | 单元 A1 |
| 成片带「AI 生成」标记 | 单元 A1 |
| 制作台页面入口 | 不做，欠着，接手：acb21613（另出设计稿后再派） |

## 背景

百炼「声动人像」`videoretalk`：给一段已有的正面人像视频换口型，对上一段新音频。异步任务，单次音频不到 120 秒，4.8 元/分钟（0.08 元/秒），实测 11 秒 1080×1920 出片约 130 秒。参考实现（只读，不改）：`~/Desktop/创业项目/内容创作/RefShelf-trials/voice-avatar-2026-11-25/test_videoretalk.py`，官方文档 https://help.aliyun.com/zh/model-studio/videoretalk-api 。

1. 临时上传：`GET {base}/uploads?action=getPolicy&model=videoretalk` 拿上传策略，再按策略字段 multipart POST 到 `upload_host`，得到 `oss://<upload_dir>/<文件名>`（参考实现第 58–103 行）。
2. 提交：`POST {base}/services/aigc/image2video/video-synthesis`，头 `X-DashScope-Async: enable`、`X-DashScope-OssResourceResolve: enable`，body `{"model":"videoretalk","input":{"video_url":<oss>,"audio_url":<oss>,"ref_image_url":""},"parameters":{"video_extension":true}}`，返回 `output.task_id`。
3. 查询：`GET {base}/tasks/<task_id>`，`output.task_status` 为 `PENDING/RUNNING/SUCCEEDED/FAILED/CANCELED/UNKNOWN`，成功时 `output.video_url`、`usage.video_duration`。实测结果地址主机是 `dashscope-7c2c.oss-cn-shanghai.aliyuncs.com`。

制作台里同类的「云任务 + 续跑账本」写法见 `scripts/aigc/dreamverse_bridge.py`（`write_ledger`、`record_submission`、`poll_cloud`），照它的思路写，不复用它的类。

## 不要动

- 不改 `studio/**`（含 `studio/static/**`）、不改 `scripts/aigc/**`、不改 `scripts/direct_video/**`。
- 不上传用户本人的声音或肖像。实测只用 `RefShelf-trials/voice-avatar-2026-11-25/avatar_input_latentsync_demo1.mp4`（公开示例人像，Apache-2.0）和 `avatar_audio_10s.wav`（合成声音）。
- 不推送、不合并。只在本工作区提交，推送由总控做。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| A1 数字人客户端、切段、续跑账本 | `新建 scripts/avatar/__init__.py`、`新建 scripts/avatar/videoretalk.py`、`新建 scripts/generate_avatar_clip.py`、`新建 scripts/avatar/README.md`、`新建 tests/test_avatar_videoretalk.py` | 新文件 | 1) 客户端：上传、提交、查询、下载四步，网络调用都可注入替身；每步设连接和读取超时；下载只接受 `dashscope-` 开头、含 `.oss-`、以 `.aliyuncs.com` 结尾的 https 地址，不带鉴权头。2) 切段：音频不超过 `--max-seconds`（默认 110）就一段；超过时用 ffmpeg `silencedetect` 在每段 90 秒到上限之间找最长的停顿切开，找不到停顿就在上限处切并在账本记 `cut: hard`。3) 账本 `<out-dir>/avatar-ledger.json`，原子写：每段记音频哈希、底片哈希、参数哈希、状态、task_id、结果文件哈希。提交前先写「提交中」，拿到 task_id 立刻写；重跑时有 task_id 的只查询不提交；只有「提交中」没有 task_id 的段判为结果未知，报 `avatar_submit_unknown` 停下，不重提；已完成且结果文件哈希对得上的段直接跳过；输入哈希变了的段作废重做。4) 全部段完成后用 ffmpeg 按顺序拼成 `<out-dir>/avatar.mp4`，写入元数据 `comment=AI生成`，旁边写 `avatar.ai-label.json`（模型、段数、总秒数、生成时间 UTC）。5) 失败码各对应一种原因：`avatar_api_key_missing`、`avatar_input_invalid`、`avatar_upload_failed`、`avatar_submit_failed`、`avatar_submit_unknown`、`avatar_task_failed`、`avatar_timeout`、`avatar_download_failed`、`avatar_result_url_invalid`；输出和日志里不出现密钥和带签名的地址。6) 命令：`scripts/generate_avatar_clip.py --video <底片> --audio <配音wav> --out-dir <目录> --material public-sample|self [--owner-consent "<原话>"] [--env-file <文件>] [--max-seconds 110] [--live] [--wait-seconds 900]`；不带 `--live` 只打印切段计划和预计花费（0.08 元/秒），不发任何请求；`--material self` 时必须带 `--owner-consent`，原话写进账本；密钥读环境 `DASHSCOPE_API_KEY`，或 `--env-file` 里的 `SPEECH_TO_TEXT_API_KEY` / `DASHSCOPE_API_KEY`。 | `cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar/tests/test_avatar_videoretalk.py` | 全部通过；用例覆盖：上传 multipart 字段、提交头和 body、提交后崩溃重跑只查询不提交、只有「提交中」时报 `avatar_submit_unknown` 且提交次数为 0、已完成段跳过、输入变了重做、用 ffmpeg 现场生成的「音、停顿、音」wav 能在停顿处切开、无停顿时硬切并记账、拼接后元数据有 AI生成、结果地址不合规被拒、输出里不含密钥；改回去掉账本判断的写法时续跑用例必须红（写进汇报） |
| A2 真实冒烟（花费约 0.9 元，依赖 A1） | `新建 /tmp/pho-r13-smoke/smoke.md` | 本机 | `--live --material public-sample --env-file ~/.config/harness/speech-to-text.env`，底片和配音用上面两份示例文件，输出到 `/tmp/pho-r13-smoke/`；跑完再原样跑一次 | `cat /tmp/pho-r13-smoke/smoke.md` | 第一次得到 `avatar.mp4`（ffprobe 读得出时长和 comment=AI生成）；第二次不发提交、直接复用；从结果里抽首、中、尾三帧存 png 放在 `/tmp/pho-r13-smoke/frames/`，路径写进汇报（总控看图） |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| BE-06 后台任务、云任务 | 交出去的任务先落账再查询，中断后重跑能接上，不重复提交 | 提交成功后进程被杀，重跑又提交一次、收两次钱 | A1 续跑用例 |
| BE-11 外部服务出错 | 缺密钥、上传失败、提交失败、任务失败、超时、下载失败各用不同的码，原文不当结论显示；跨网络的提交断开时结果未知，不重提 | 提交超时后自动重提 | A1 失败码用例 |
| BE-27 时间 | 账本和标签里的时间一律 UTC 带 Z | 写本机时间文本 | A1 用例读账本 |
| OPS-24 会走网络的步骤 | 每步有超时，到时限报读不到、写明卡在哪一步 | 查询循环无限等 | A1 超时用例 |
| TEST-04 夹具 | 测试用的音频视频由 ffmpeg 现场生成真实内容，不用空文件 | 用空字节冒充 wav | A1 用例 |
| TEST-13 新测试文件 | 新增的 `tests/test_avatar_videoretalk.py` 那一笔写 `Test-Atom: PHO-R13-AVATAR new` 和 `Test-Purpose` | 缺编号被提交钩子拒 | `git show` 看尾注 |
| DEL-07 用了替身 | 汇报写明哪几段只用替身、哪段真跑过 | 只跑替身就写「已接入」 | 汇报自查 |

## 取舍裁定

- 每段都用同一段底片，开 `video_extension`，让底片自动延长到音频长度。
- 本期只做命令和程序接口，Studio 不加路由；以后加页面时直接调 `videoretalk.py` 里的入口函数，所以入口函数签名写清楚：`generate_avatar_clip(video: Path, audio: Path, out_dir: Path, *, material: str, owner_consent: str | None, api_key: str, live: bool, max_seconds: float = 110, wait_seconds: float = 900, transport=None) -> dict`。
- 本机跑：项目开发机现在连不上（2026-11-25 策划台会话实查），这些是轻量单元测试加一次真实冒烟，直接本机跑；开跑前按 OPS-13 数一下本机重活进程，非 0 就写进汇报再跑。
- 提交分两笔：A1 一笔（含需求卡目录）、A2 不提交代码，命令、两次原始输出末 20 行和抽帧路径写进 `/tmp/pho-r13-smoke/smoke.md`。尾注顺序如下（尾注连成最后一段）：

```
feat(avatar): A1 用百炼声动人像生成数字人口播片段

<正文>

Request: 2026-11-25-Pho_R13-avatar-clip
Verify: 2026-11-25-Pho_R13-avatar-clip/H-01
Test-Atom: PHO-R13-AVATAR new
Test-Purpose: 保护提交前落账、中断续查不重提、结果未知停下、按停顿切段和 AI 生成标记。
```

## 固定规则

- 工作区主人是派你的会话 acb21613-1a28-47b7-94bd-d04d982c096a，你是它派的执行方，不运行 claim、adopt，不为身份停下。
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
- 任务单有「规则卡短表」就按短表做，不整份读两份写代码规则卡，也不为它跑前端登记或交稿检查；开场说明里的总目录只按任务类型找相关的行。

## 交接

（执行方每段结束在这里追加：完成段、提交号、验证结果、替总控定的、欠着的）

### 执行方交接（2026-11-25）

- A1：提交 `542ece079e665a31bf30cb61b0391553aef5cf5f`。指定 pytest 命令最终真实退出码 **0**，**8 passed**；初始缺模块红灯退出 2。移除提交前账本判断及 task_id 续查判断的变异验证退出 **1**，6 passed、2 failed（续查重提及未知状态未停下）；恢复后 8 passed。
- A2：第一次真实调用退出 **1**，输出 `avatar_submit_failed`；第二次原样运行退出 **1**，输出 `avatar_submit_unknown`，未再次提交。未生成成片，抽帧路径：无。命令及两次原始输出见 `/tmp/pho-r13-smoke/smoke.md`，账本留在 `/tmp/pho-r13-smoke/avatar-ledger.json`。
- 替总控定的：小于 112.5 秒上限时，将可寻找停顿的窗口下界按 `min(90, max_seconds × 0.8)` 处理，使缩短上限仍可切在停顿；下载禁止重定向；单段音频转换为 PCM WAV 后计算哈希。网络调用通过 requests Session 注入替身。
- 欠着的：A2 真实成功出片、元数据和三帧，须先核实云端提交失败原因和账本对应任务，不可删除未知账本盲目重试；制作台页面入口另出设计稿。上传、提交、查询、下载、断点恢复及故障码的自动测试使用替身；仅公开素材上传及一次提交是真实调用，未完成真实查询和下载。开跑前进程清单匹配 21 条 Chrome/渲染相关记录，未干预。项目引用的 `develop/harness/fullstack-ai-harness.md` 不存在，已读取 Core 对应文件。

### A1b 补丁交接

- A｜提交 `e6bd291e6c69d40a7f541f193a3233cedf6281f9`，对应本卡 H-01。指定的 `tests/test_avatar_videoretalk.py` pytest 命令在旧代码上退出 **1**，9 failed、20 passed。补丁后同一命令退出 **0**，**29 passed in 8.56s**。开跑前匹配到 20 条 Chrome、渲染或测试相关进程记录。
- A｜网络替身覆盖四个请求步骤的欠费和安全错误码、4xx 拒绝后重提，以及 5xx、断连、超时和缺任务号保持未知。解锁需提供非空 `--reason`。段号从 0 开始，与 `segment-0000.mp4` 一致。解锁独立更新账本，后续按原生成命令重试。
- A｜按总控确认的欠费调查结果，已删除 `/tmp/pho-r13-smoke/avatar-ledger.json`。A2 仍由总控在账号处理后重跑，本单元未运行 A2。补丁仅在任务工作区提交，未推送或合并。
