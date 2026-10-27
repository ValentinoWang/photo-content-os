---
name: photo-remote-dev-box
description: photo-content-os 的远端开发机（本机 ~/.ssh/config 别名 photo-dev）：本机只改代码、跑 Claude/Codex，pytest 全量、前端门禁（R276、R278/R282/R283）、浏览器拍图、视频渲染都经 scripts/rbox 在开发机上跑。用户说「放到开发机上跑」「本机太卡」「跑全量」「跑门禁」「换开发机」「开发机到期」「装新开发机」，或者要在本机跑 pytest、无头浏览器、渲染之前使用。只改一两行文档、不跑测试时不用。
---

# photo-content-os 开发机：本机写，开发机跑

本技能是 photo-content-os 项目技能，本体在 `.agents/skills/photo-remote-dev-box/`（Codex 从这里读），`.claude/skills/photo-remote-dev-box` 是指过来的软链（Claude 从这里读）。`.gitignore` 忽略 `.agents/skills/*`（那是 harnessctl 生成的 Core 链接），本技能单独放行。改它按普通代码改动走：任务 worktree、需求卡、交付检查。

分工规则见 Harness Core `remote-dev-box-harness.md`，检查卡见 `devbox-split-guard-card.md`。本文件只写本项目的差异和踩过的坑。2026-10-27 第一次装机的完整时间线和提速分析见 `references/2026-10-27-setup-review.md`。

**分工一句话**：Claude、Codex、改代码、git、看图在本机；pytest、门禁、浏览器、渲染、调试服务在开发机。开发机上不跑任何 AI，也不放 AI 凭据。

**为什么**：10-26、10-27 本机负载一再冲到 38–57，交换文件把磁盘挤到不足 1 GB，被 Cadenvo、寸木的巡检会话提醒过好几次；元凶是 Codex 在本机跑门禁（一个门禁 = 页面浏览器 + 渲染器浏览器，约 9 个 Chrome 进程）。用户 10-27 租了这台专用机，要求 3 小时内弄好。

## 机器

| 项 | 值 |
|---|---|
| 别名 | 本机 `~/.ssh/config` 里的 `photo-dev`。rbox 只认这个别名，地址、端口、密钥都写在那一段；Harness 控制台也按它判在线 |
| 地址 | 2026-10-27 装机时：移动 `223.109.239.36`，端口 `13640`；电信 `180.127.11.177`，端口同 |
| 配置 | 4 核、7.7 GB 内存、系统盘 196 GB（装机时剩 149 GB），Ubuntu 22.04，root 登录 |
| 性质 | 租来的机器，专给 photo-content-os 用，不和 Cadenvo（223.109.239.30:14932）、寸木、茶思屋共用 |
| 装机记录 | 本机 `~/.local/share/photo-rbox/devbox-deploy-times.tsv`，Harness 统一的 9 列：日期、机器（只写「IP:端口」）、方式、开始、结束、前置部署时间（分钟）、结果、各步用时（「；」分隔）、备注。失败的那次也记 |

**先核对是不是这台机器**：用户 10-27 第一次发来的连接截图其实是 Cadenvo 那台（223.109.239.30:14932）。拿到连接方式先和各项目 rbox 的默认地址比一遍（`grep -n 'HOST=\|PORT=' <项目>/.agents/skills/*-remote-dev-box/scripts/rbox`），再看机器上有没有别的项目目录（`ls /root`），对上了再装。

## 一个脚本：`scripts/rbox`

```bash
R=.agents/skills/photo-remote-dev-box/scripts/rbox      # 在仓库根或任务 worktree 根下
$R run  "$PWD" -- .venv/bin/python -m pytest -q tests/test_r280_light.py      # 单项，前台
RBOX_QUEUE=heavy $R bg full "$PWD" -- .venv/bin/python -m pytest -q tests      # 全量，后台排队（10-27 实测 4 分 30 秒到 5 分）
$R wait full                                                                   # 等它结束，回传末尾和退出码
$R log full 'FAILED'                                                           # 只看匹配的行
$R pull ~/.photo-content-os/evidence/R2xx-任务                                  # 拉回截图、帧
$R list "$PWD"                                                                 # 看这次会推哪些文件（不连开发机）
$R status                                                                      # 负载、内存、磁盘、后台任务、最近的排队记录
$R ai-check; $R exposure-check                                                 # 开发机上有没有 AI、有没有挂到公网的密钥
```

- **先问在线判定**：每次 `run`、`bg` 先调 Harness 的 `Core/scripts/devbox/devbox_status.py where`：判本机（退出码 10）就停下，改在本机跑、守本机预算；读不到状态也停下，不当成不在线。这个脚本还没发布到 Harness 主检出时，改用直连开发机判断：10 秒内连得上才发，连不上就在推送前停下（10-27 R310 交付准备时 Codex 指出原先这里直接放行）。自测 `test_where.sh` 覆盖四种情况。
- **推送只推将来会提交的文件**：git 跟踪的 + 没被 `.gitignore` 忽略的新文件，没有改动时 1–3 秒。目录里有任务在跑或在排队时拒绝推，免得换掉正在测的文件（`RBOX_PUSH_WHILE_RUNNING=1` 才放行）。
- **开发机副本带 git 索引**：裸仓库 `/root/pco.git`，提交从本机推上去（开发机不放 GitHub 凭据；183 个提交只要 3 秒）。推送后副本 `reset --mixed` 到本机同一提交，`git status` 和本机一样；测试和交付检查要 `git ls-files`、`git log`。
- **排队**：全量、门禁、渲染用 `RBOX_QUEUE=heavy`，同一时间只跑一个；只开一个浏览器的拍图用 `light`（最多 3 个并排、和 heavy 互斥）。外壳 `queue_run.sh` 和寸木那份一样，按内容哈希存，不原地覆盖。排队的后台任务自动 `nice -n 10`。
- **路径两边一样**：开发机上建了和本机同名的绝对路径（下表），测试和门禁里写死的仓库路径、worktree 软链都不用改。
- **4 核**：pytest 不要开超过 4 路。全量目前是单进程（没装 pytest-xdist；要不要加由用户定）。

## 开发机上的目录

| 本机路径 | 开发机 |
|---|---|
| `/Users/vsiyo/Desktop/创业项目/photo-content-os`（主目录） | 软链到 `/root/pco`。`.venv`、`.tools` 装在这里 |
| `/private/tmp/task-worktrees/photo-content-os-*`、`~/.local/share/task-worktrees/photo-content-os-*` | 两处都软链到 `/root/pco-wt`。worktree 里的 `.venv` 软链到主目录那份；`.tools` 不链（本机 worktree 也没有，`tests/test_edit_tools_runtime.py` 要求默认路径落在 worktree 自己下面），门禁和渲染经环境变量找主目录的 |
| `/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core` | 同一路径（`rbox harness` 推过去，门禁读 ui-copy-quality 的检查脚本） |
| `~/.photo-content-os` | 软链到 `/root/.photo-content-os`：门禁、渲染写的 `evidence/`，加上 `rbox studio-data` 推上去的真实 Studio 数据 |
| `~/Desktop/照片筛选`（素材根） | 软链到 `/root/media-root`：只有 `rbox studio-data r277` 推的文本素材目录和空目录占位，没有照片 |
| — | `/root/.prbox`：日志、排队锁、`bin/`（ffmpeg、ffprobe、with-macos-cp）、`shims/`、每个任务自己的 TMPDIR |

rbox 给每个命令设好的环境变量：`LOCAL_MEDIA_ROOT`、`HARNESS_CORE`、`UI_COPY_QUALITY_CHECKER`、`VIDEO_RENDER_PLAYWRIGHT_MODULE`、`PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER`、`DIRECT_VIDEO_FONT`、`VIDEO_RENDER_TEST_FONT`。

## 门禁

```bash
RBOX_QUEUE=heavy $R bg r276 "$PWD" -- node scripts/direct_video/frontend_gate.mjs --checks-only
RBOX_QUEUE=heavy $R bg r278 "$PWD" -- env DIRECT_GATE_PORT=8768 R278_DESIGN_MEDIA_ROOT=/root/pco/docs/tasks/R278-direct-rescript/design/img node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
```

| 门禁 | 在哪跑 | 10-27 结果 | 要的数据 |
|---|---|---|---|
| R276 `frontend_gate.mjs --checks-only` | 开发机 | PASS，26 次设计比对 | 合成数据，不用传 |
| R278 `rescript_frontend_gate.mjs --checks-only`（含 R282、R283） | 开发机 | PASS，54 次合同比较，和本机一致 | `rbox studio-data`（默认 r278）：studio-r276 里一个作品的 `job.json`（44 KB）+ 设计图（2.5 MB）。实测只放这两样就能过 |
| R277 `revision_frontend_gate.mjs --checks-only` | **本机** | 开发机上过了夹具、真实首屏、标注回放，卡在固定标注框位置 | 见下一节 |
| R276 `--real` | 本机 | 没在开发机上试 | 整份 studio-r276 |

### R277 为什么还在本机

镜头代码没指定中文字体，Mac 上落到苹方，开发机上落到 Noto，行高不同，标注框矮 5–9 像素（`review/02` 的 h 89→80、53→48），而夹具里的框是按 Mac 量出来写死的。苹方是苹果的字体，不能装到租来的机器上。所以 R277 门禁按 Core「本机例外」第 2 种（被测对象只在本机）留在本机跑，守本机预算（无头浏览器同一时间一个、量完就关）。要搬上来：先让镜头代码固定用一款仓库自带的中文字体、重新生成夹具里的框，再 `rbox studio-data r277`（约 1.2 GB），用 `with-macos-cp` 包着跑：

```bash
RBOX_QUEUE=heavy $R bg r277 "$PWD" -- with-macos-cp env DIRECT_GATE_PORT=8768 R277_SOURCE_STATE=/root/.photo-content-os/studio-r278 node scripts/direct_video/revision_frontend_gate.mjs --checks-only
```

R277（以及 R276 `--real`）复制 Studio 状态时写死了 macOS 的 `/bin/cp -cR`（GNU cp 没有 `-c`）。不改门禁代码（它们受 R276、R277 验收卡保护，改了要重新递交那两张卡），用 `with-macos-cp`：它在单独的挂载命名空间里把 `/usr/bin/cp` 换成只认 `-cR` 的替身，只对被它包住的命令生效，开发机上别的进程看到的还是原来的 cp。

## 真实数据和隐私

- **照片、视频、音频不随代码推**：仓库规定媒体不进 git，测试素材测试时现造。推送清单里能看到的图片、视频只有仓库媒体白名单里登记过的 22 个公开文件（风格库样张 18 个、合成测试帧 4 个）。
- **证据目录不推**：`evidence/`、`agents-results/`。例外是测试要读的 `evidence/2026-09-01/openclaw-media-ui-prototype-and-checklist`（3 个文本文件），默认就推；别的用 `RBOX_WITH='evidence/…'` 点名推。
- **私密文件不推**：`.env*`、`*.pem`、`*.key`、`auth.json`、`.claude*`、`.codex*`。自测 `test_push_rules.sh`（改坏两处过滤规则各报红一次）。
- **真实 Studio 数据**：用户 2026-10-27 同意放到这台开发机（经 photo-content-os-4d 转达，原话「能啊」）。`rbox studio-data` 按门禁只推它读的东西：
  - `r278`（默认）：一个 `job.json` 和设计图；
  - `r277`：整份 `studio-r278`、`evidence/R277-shot-visual-revision`（约 1.2 GB），R277 打开的作品连着的素材目录 `testing/R131-hiatus-video`（236 KB，只有 json、html）整份推，别的作品连着的目录只建空目录占位。素材目录接口挨个读每件作品，任何一件连着的目录不存在就整个报错（`studio/media_review.py` 的 `piece`）；目录存在、是空的，那件作品就显示成空作品。
  - 作品连着的 4 个真实照片、视频项目（兰大、清华毕业，10-27 共约 8.7 GB）不传。
- **机器到期前**删掉开发机上的 `/root/.photo-content-os` 和 `/root/media-root`。
- **开发机上不许有 Claude、Codex 和 AI 凭据**：`rbox run`、`bg` 发命令之前先用 `ai_guard.py` 检查（执行 claude/codex、装 AI 包 → 拒绝，`RBOX_ALLOW_AI_WORDS=1` 放行会记进开发机 `ai-allow.log`；碰到凭据 → 永远拒绝）；`rbox ai-check` 查现场，`--selftest` 用假目录测该红的红、该绿的绿。`ai_guard.py`、`ai_check_remote.sh`、`exposure_check_remote.sh` 和 Cadenvo 是同一份，改了通知对方。

## 换机器（到期、换线路）

1. 改本机 `~/.ssh/config` 里 `photo-dev` 那一段的地址和端口；装上本机公钥（密码登录一次，用 `expect` 喂密码，密码不写进任何文件）。
2. `rbox init`：开发机上建和本机同名的路径。
3. `rbox sync <任意基于 origin/main 的 worktree>`，再在开发机上 `rsync -a --exclude=.venv --exclude=.tools --exclude=.git <那个 worktree>/ /root/pco/` 给主目录打底：setup 要用里面的 `scripts/setup_edit_tools.py`、锁文件和本技能的替身脚本。没打底 `rbox setup` 会直接拒绝。
4. `rbox setup`：系统包（tmux、Noto CJK、Liberation、Chromium 要的库、melt、mediainfo）、uv、Python 包（按本机 `pip freeze`，torch 系 CPU 版）、Node（按锁文件、sha256 校验）、剪辑工具和浏览器 1228、ffmpeg 9.0、macOS 替身。ffmpeg 由本机后台下载、限速上传，和开发机装 Python 包同时进行。
5. `rbox harness`；要跑 R278 门禁再 `rbox studio-data`。
6. 跑一遍 `RBOX_QUEUE=heavy $R bg full …` 全量和 R276、R278 门禁，结果和下面「已知的红」对一遍。
7. 装机记录写一行（失败的那次也写），通知 Harness 控制台的登记会话和 Cadenvo、寸木的巡检会话（全局说明里的跨账号通信办法）。

**按现在的脚本估计 10–12 分钟**（系统包 1 分、Python 包 3 分、剪辑工具和浏览器 2 分、ffmpeg 和前面几步并行约 2 分），再加 `studio-data` 不到 1 分钟。10-27 第一次装用了 52 分钟（首次 13 分钟失败 + 重跑补装 39 分钟），坑都已写进脚本。平台要是能把配好的机器存成自定义镜像，下次几乎不用装（Cadenvo 用的 `rbox bootstrap` 就是这条路）。

## 新机器上踩过的坑（都已写进脚本）

| 坑 | 现象 | 处理 |
|---|---|---|
| 新镜像没有 tmux、pip、curl | `rbox bg` 起不来；`python3 -m pip` 报 No module named pip | setup 第一步 apt 装 tmux、curl；uv 从 GitHub 发布页下 |
| uv 下不到本机的 Python 补丁版 | 本机 3.13.16，uv 0.9.5 只有 3.13.9 | 用 3.13.9；第三方包按本机 freeze 装，141 个版本一样 |
| PyPI 上 Linux 的 torch 默认带 CUDA | 多拉约 2.5 GB nvidia 包 | torch、torchvision、torchaudio 用阿里云 pytorch-wheels 的 `+cpu` 版 |
| OpenChatCut 的 onnxruntime-node | Linux x64 上去 NuGet 下 CUDA 附加文件，下载被 302 重定向，脚本不跟，`npm ci` 整个失败 | `ONNXRUNTIME_NODE_INSTALL=skip`（CPU 版本来就在 npm 包里） |
| 开发机直连 GitHub 发布文件 100–200 KB/s | ffmpeg 157 MB 下了 10 分钟才到 89 MB | 本机下载（约 2 MB/s，54–64 秒）+ 单独连接限速上传（约 58 秒） |
| BtbN 的 master 版 ffmpeg | 删了 `-filter_complex_script`，开发机上烧字幕的测试全挂 | 钉 `ffmpeg-n9.0-latest`，和本机 Homebrew 9.0.2 同版 |
| 测试写死 macOS 字体路径 | `tests/test_r277_boxes.py` 报 `lstat '/System'`；`test_pf_video_pipeline.py` 找不到 Arial | 同一路径放链接：STHeiti Medium → Noto Sans CJK Bold，Arial → Liberation Sans。字形不同，只保证能跑 |
| 没有 melt | `melt_unavailable` | apt 装 melt 7.4.0（本机 Kdenlive 是 7.39.0，有两项像素测试因此红） |
| 副本没有 `.git` | `git ls-files` 退出码 128 | 裸仓库 + 推送后 `reset --mixed`；`--no-checkout` 建出来的索引是空的，新建时一定要 reset（10-27 第一次漏了，3563 个文件全显示成已删除） |
| `rbox fresh` 后裸仓库里两条同路径的 worktree 记录 | `git worktree list` 重复 | fresh 先 `worktree remove` 再删目录 |
| 门禁复制 Studio 状态用 `cp -cR` | `cp: invalid option -- 'c'` | `with-macos-cp` |
| 素材根指到空目录 | 门禁打开的作品页出不来：`workspace_not_found`、`workspace_outside_media` | 素材根用本机默认的同名路径 `~/Desktop/照片筛选`，软链到 `/root/media-root` |
| 门禁默认把证据写到 `~/.photo-content-os/evidence` | 开发机上落到 `/root` 下，`rbox pull` 用本机路径拉不到 | 开发机上 `~/.photo-content-os` 的同名路径软链到 `/root/.photo-content-os` |
| `$变量` 后面直接跟中文标点（Core E-86） | `rbox setup` 最后一行 `DEPLOY_LOG…: unbound variable`，退出码 1 | 写 `${变量}`；`scripts/lint_scripts.sh` 用 perl 按字节查，改脚本后必跑 |

## 已知的红（2026-10-27 开发机全量：1204 过、12 红、36 跳过）

- **本机同样会红的 9 项**（代码的问题，不是开发机的）：
  - 8 项字幕和黑帧测试（`test_direct_video_subtitles.py`、`test_bilingual_subtitles_r6.py`、`test_pf_video_pipeline.py` 里烧字幕的几项）：`scripts/video_subtitles.py` 用的 `-filter_complex_script` 在 ffmpeg 9 里已删除；
  - `tests/test_full_checklist_acceptance.py` 还查 R280 之前的深色令牌 `--bg:#0D1314`。
- **开发机环境差异的 3 项**：`test_obsidian_doc_sync.py` 里用系统 python 跑同步检查的一项（开发机上没有 Obsidian 库）；`test_pf_video_pipeline.py::FrameMappingTests::test_every_frame_matches_retained_source_clock` 和 `test_pipeline_backends.py::MeltPipelineTests::test_overlay_and_subtitle_pixels_are_rendered`（melt 7.4 对本机 7.39）。

## 失败先分类

照 Core「失败先分类」：环境（ENOENT、缺命令、退出码 127）先补开发机，不改业务代码；负载（计时类断言、CPU 空闲接近 0）等空闲单跑；能在空闲开发机上稳定复现的当真问题修。归类前先做两件事：用同一份代码在本机试那一条命令（10-27 就是这样确认 ffmpeg 9 的问题本机也有）；比两边的解释器和依赖版本（见上面的差异表）。

## 和本机不一样的地方（2026-10-27）

| 项 | 本机 | 开发机 |
|---|---|---|
| Python | 3.13.16（Homebrew） | 3.13.9（uv 下的独立版），第三方包同版 |
| PyTorch | 2.8.0 | 2.8.0+cpu |
| ffmpeg | 9.0.2（Homebrew） | 9.0.2（BtbN 静态版） |
| melt | 7.39.0（Kdenlive 自带） | 7.4.0（Ubuntu 22.04） |
| 中文字体 | STHeiti Medium、苹方 | Noto Sans CJK（STHeiti 路径链到 Noto Bold） |
| Arial | 系统自带 | 同一路径链到 Liberation Sans |
| 浏览器 | `~/Library/Caches/ms-playwright`（1228） | 主目录 `.tools/browsers`（1228） |
| Obsidian 库 | iCloud 里的自媒体库 | 没有 |

## 提速：10-27 第一次装机为什么用了 99 分钟

详见 `references/2026-10-27-setup-review.md`。下次照这几条做：

1. **装环境时别串行等**：ffmpeg、Studio 数据这类大文件一开始就在本机后台传，和开发机装包同时进行（`rbox setup` 已经这样做）。
2. **先补环境再跑全量**：开工就派子代理盘点「测试读了仓库外的什么」（字体、melt、git、证据目录、Studio 数据、macOS 命令），补齐了再跑第一遍全量；10-27 多跑了一遍全量、多查了一轮，约 10 分钟。
3. **数据只传门禁读的**：先 `grep` 门禁读哪些路径再传；10-27 为一个 44 KB 的 job.json 传了 806 MB。用户同意上传后立刻开始传。
4. **代码一次冻结再派交付**：交付准备开始后再改代码，验收物就作废、要重做一轮。派之前自己先把边界情况测一遍（例如检查器缺失、开发机连不上）。
5. **交付检查一次过**：建任务 worktree 时用 `--with` 把旧卡的 `agents-results/<日期>/<目录>` 带上（G16 要读它们的合同）；需求卡的验收步骤只用允许的动词开头（打开、发送、检查、查看……，清单在 Core `acceptance-handoff/references/readability.json`），不写路径和代码术语。
6. **不空等**：等安装、等上传、等全量时，用后台命令加通知，同时写任务单、验收合同或排查下一件事。
