# photo-content-os 开发机（rbox）

本机只跑 Claude、Codex，只改代码、管 git；测试、门禁、拍图、渲染都经 `scripts/devbox/rbox` 放到开发机上跑。分工规则见 Harness Core `remote-dev-box-harness.md`，检查卡见 `devbox-split-guard-card.md`。本文件只写本项目的差异。

## 机器

| 项 | 值 |
|---|---|
| 别名 | 本机 `~/.ssh/config` 里的 `photo-dev`。rbox 只认这个别名，地址、端口、密钥都写在那一段，Harness 控制台也按它判在线 |
| 地址 | 2026-10-27 装机时：移动 `223.109.239.36`，端口 `13640`；电信 `180.127.11.177`，端口同 |
| 配置 | 4 核、7.7 GB 内存、系统盘 196 GB（装机时剩 149 GB），Ubuntu 22.04 |
| 性质 | 租来的机器，专给 photo-content-os 用，不和 Cadenvo、寸木、茶思屋共用 |
| 装机记录 | 本机 `~/.local/share/photo-rbox/devbox-deploy-times.tsv`（Harness 统一的 9 列格式，失败的那次也记） |

## 换机器（到期、换线路）

1. 改本机 `~/.ssh/config` 里 `photo-dev` 那一段的地址和端口，装上本机公钥。
2. `rbox init`：开发机上建和本机同名的路径。
3. `rbox sync <任意 worktree>`，再在开发机上 `rsync -a <那个 worktree>/ /root/pco/` 给主目录打底：setup 要用里面的 `scripts/setup_edit_tools.py` 和锁文件。
4. ffmpeg 先从本机传：开发机直连 GitHub 的发布文件只有 100–200 KB/s，157 MB 的包要 15 分钟以上。在本机下好 BtbN 的 `ffmpeg-n9.0-latest-linux64-gpl-9.0.tar.xz`（和本机 Homebrew 同为 9.0），用单独的连接限速传到开发机 `/root/.prbox/ffmpeg-upload.tar.xz`（`rsync --bwlimit=3072 -e 'ssh -o ControlPath=none'`）。10-27 实测：本机下载 54–64 秒，上传约 58 秒。不要用 master 版：它删了 `-filter_complex_script`。
5. `rbox setup`：系统包、Python 包、Node、剪辑工具和浏览器、ffmpeg、macOS 替身。10-27 装机用时见装机记录。
6. `rbox harness`：推 Harness Core。要跑 R277、R278 门禁就再 `rbox studio-data`。
7. 机器到期前：删掉开发机上的 `/root/.photo-content-os`（真实 Studio 数据）。

## 开发机上的目录

| 本机路径 | 开发机 |
|---|---|
| `/Users/vsiyo/Desktop/创业项目/photo-content-os`（主目录） | 软链到 `/root/pco`。`.venv`、`.tools` 装在这里 |
| `/private/tmp/task-worktrees/photo-content-os-*`、`~/.local/share/task-worktrees/photo-content-os-*` | 两处都软链到 `/root/pco-wt`。worktree 里的 `.venv` 软链到主目录那份；`.tools` 不链，门禁和渲染经环境变量找主目录的 |
| git | 裸仓库 `/root/pco.git`，提交从本机推上去（开发机不放 GitHub 凭据）。每次推送后，副本的 git 索引对齐到本机同一个提交，`git status` 和本机一样 |
| `/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core` | 同一路径（`rbox harness` 推过去） |
| `~/.photo-content-os` | 软链到 `/root/.photo-content-os`：门禁、渲染写的 `evidence/`，加上 `rbox studio-data` 推上去的真实 Studio 数据 |
| — | `/root/.prbox`：日志、排队锁、`bin/`（ffmpeg、ffprobe、with-macos-cp）、`shims/`、每个任务自己的 TMPDIR |

两边绝对路径一样，所以测试和门禁里写死的仓库路径、worktree 软链不用改。

## 常用

```bash
R=scripts/devbox/rbox
$R run  "$PWD" -- .venv/bin/python -m pytest -q tests/test_r280_light.py      # 单项，前台
RBOX_QUEUE=heavy $R bg full "$PWD" -- .venv/bin/python -m pytest -q tests      # 全量，后台排队（10-27 实测 4 分 30 秒）
$R wait full                                                                   # 等它结束，回传末尾和退出码
$R log full 'FAILED'                                                           # 只看匹配的行
$R pull ~/.photo-content-os/evidence/R2xx-任务                                  # 拉回截图、帧
$R list "$PWD"                                                                 # 看这次会推哪些文件
$R status
```

- 每次 `run`、`bg` 都先问 Harness 的在线判定（`Core/scripts/devbox/devbox_status.py where`）：判本机就停下，改在本机跑、守本机预算；读不到状态也停下，不当成不在线。
- 然后推一次目录：只推 git 跟踪的和没被 `.gitignore` 忽略的新文件，没有改动时 1–3 秒。目录里有任务在跑或在排队时拒绝推，免得换掉正在测的文件。
- 排队：全量、门禁、渲染用 `RBOX_QUEUE=heavy`，同一时间只跑一个；只开一个浏览器的拍图用 `light`。外壳是 `queue_run.sh`，和寸木那份一样。
- 开发机 4 核：pytest 不要开超过 4 路。

### 门禁

```bash
RBOX_QUEUE=heavy $R bg r276 "$PWD" -- node scripts/direct_video/frontend_gate.mjs --checks-only
RBOX_QUEUE=heavy $R bg r277 "$PWD" -- with-macos-cp env DIRECT_GATE_PORT=8768 R277_SOURCE_STATE=/root/.photo-content-os/studio-r278 node scripts/direct_video/revision_frontend_gate.mjs --checks-only
RBOX_QUEUE=heavy $R bg r278 "$PWD" -- env DIRECT_GATE_PORT=8768 R278_DESIGN_MEDIA_ROOT=/root/pco/docs/tasks/R278-direct-rescript/design/img node scripts/direct_video/rescript_frontend_gate.mjs --checks-only
```

- 门禁要的 `HARNESS_CORE`、`UI_COPY_QUALITY_CHECKER`、`VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER`、字体变量，rbox 都设好了。
- R277（以及 R276 `--real`）复制 Studio 状态时写死了 macOS 的 `/bin/cp -cR`，所以要用 `with-macos-cp` 包一层：它只在这一个命令的挂载命名空间里把 cp 换成替身，开发机上别的进程看到的还是原来的 cp。
- R277、R278 要用真实 Studio 数据：先 `rbox studio-data`。

## 什么不推、什么放到了开发机

- **照片、视频、音频不随代码推**：仓库规定媒体不进 git，测试素材测试时现造，所以清单里本来就没有媒体文件。
- **证据目录不推**：`evidence/`、`agents-results/`。例外是测试要读的 `evidence/2026-09-01/openclaw-media-ui-prototype-and-checklist`（3 个文本文件），默认就推。别的要用 `RBOX_WITH='evidence/…'` 点名推。
- **私密文件不推**：`.env*`、`*.pem`、`*.key`、`auth.json`、`.claude*`、`.codex*`。自测 `test_push_rules.sh`。
- **真实 Studio 数据**：用户 2026-10-27 同意放到这台开发机。`rbox studio-data` 只推门禁用到的 `studio-r276`、`studio-r278`、`evidence/R277-shot-visual-revision` 和 R278 的设计图，共约 1.8 GB。素材根 `~/Desktop/照片筛选` 不推，开发机上的 `LOCAL_MEDIA_ROOT` 指到一个空目录。
- **开发机上不许有 Claude、Codex 和 AI 凭据**：`rbox run`、`rbox bg` 发命令之前，先用 `ai_guard.py` 检查一遍（自测 `test_ai_guard.sh`）。巡检时跑 `rbox ai-check`。

## 和本机不一样的地方（2026-10-27 装机时）

| 项 | 本机 | 开发机 | 影响 |
|---|---|---|---|
| Python | 3.13.16（Homebrew） | 3.13.9（uv 下的独立版） | 补丁号不同；第三方包按本机 `pip freeze` 装，141 个，版本一样 |
| PyTorch | 2.8.0 | 2.8.0+cpu | 开发机没有显卡 |
| ffmpeg | 9.0.2（Homebrew） | 9.0.2（BtbN 静态版） | 同版本，编译选项不同 |
| melt | 7.39.0（Kdenlive 自带） | 7.4.0（Ubuntu 22.04 的包） | 版本差得多；Kdenlive 相关的渲染结果可能不同 |
| 中文字体 | STHeiti Medium（macOS 自带） | Noto Sans CJK Bold | rbox 设了 `DIRECT_VIDEO_FONT`、`VIDEO_RENDER_TEST_FONT`；写死 `/System/Library/Fonts/STHeiti Medium.ttc` 的测试，由同一路径的链接指到 Noto |
| Arial | `/System/Library/Fonts/Supplemental/Arial.ttf` | 同一路径链到 Liberation Sans（和 Arial 等宽） | 字形不同，只保证能跑 |
| 浏览器 | `~/Library/Caches/ms-playwright` | `.tools/browsers`（同为 1228 版） | rbox 设了 `VIDEO_RENDER_BROWSER`、`VIDEO_RENDER_PLAYWRIGHT_MODULE` |
| Obsidian 库 | iCloud 里的自媒体库 | 没有 | `tests/test_obsidian_doc_sync.py` 里用系统 python 跑同步检查的那一项会因为缺库里的文档而红 |
