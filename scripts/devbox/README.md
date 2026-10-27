# photo-content-os 开发机（rbox）

本机只跑 Claude、Codex，只改代码、管 git；测试、门禁、拍图、渲染都经 `scripts/devbox/rbox` 放到开发机上跑。分工规则见 Harness Core `remote-dev-box-harness.md`，检查卡见 `devbox-split-guard-card.md`。本文件只写本项目的差异。

## 机器

| 项 | 值 |
|---|---|
| 地址 | 移动 `root@223.109.239.36 -p 13640`（rbox 默认）；电信 `root@180.127.11.177 -p 13640` |
| 配置 | 4 核、7.7 GB 内存、系统盘 196 GB（2026-10-27 装机时剩 149 GB），Ubuntu 22.04 |
| 性质 | 租来的机器，专给 photo-content-os 用，不和 Cadenvo、寸木、茶思屋共用 |
| 登录 | 本机 `~/.ssh/id_ed25519` 免密；本机 `~/.ssh/config` 里的别名是 `photo-dev` |

换机器（到期、换线路）：export `RBOX_HOST`、`RBOX_PORT`，或者改 `rbox` 开头的两个默认值，再依次跑 `init`、`setup`、`harness`。

## 开发机上的目录

| 本机路径 | 开发机 |
|---|---|
| `/Users/vsiyo/Desktop/创业项目/photo-content-os`（主目录） | 软链到 `/root/pco`。`.venv`、`.tools` 装在这里 |
| `/private/tmp/task-worktrees/photo-content-os-*`、`~/.local/share/task-worktrees/photo-content-os-*` | 两处都软链到 `/root/pco-wt`。worktree 里的 `.venv`、`.tools` 软链到主目录那份 |
| `/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core` | 同一路径（`rbox harness` 推过去） |
| — | `/root/.prbox`：日志、排队锁、`bin/`（ffmpeg、ffprobe）、每个任务自己的 TMPDIR |

两边绝对路径一样，所以测试和门禁里写死的仓库路径、worktree 软链不用改。

## 常用

```bash
R=scripts/devbox/rbox
$R run  "$PWD" -- .venv/bin/python -m pytest -q tests/test_r280_light.py      # 单项，前台
RBOX_QUEUE=heavy $R bg full "$PWD" -- .venv/bin/python -m pytest -q tests      # 全量，后台排队
$R wait full                                                                   # 等它结束，回传末尾和退出码
$R log full 'FAILED'                                                           # 只看匹配的行
$R pull ~/.photo-content-os/evidence/R2xx-任务                                  # 拉回截图、帧
$R status
```

- 每次 `run`、`bg` 都先推一次目录：只推 git 跟踪的和没被 `.gitignore` 忽略的新文件，没有改动时 2–3 秒。
- 排队：全量、门禁、渲染用 `RBOX_QUEUE=heavy`，同一时间只跑一个；只开一个浏览器的拍图用 `light`。外壳是 `queue_run.sh`，和寸木那份一样。
- 开发机 4 核：pytest 不要开超过 4 路。

## 什么不推、什么不能上开发机

- **照片、视频、音频不推**：仓库规定媒体不进 git，测试素材测试时现造，所以清单里本来就没有媒体文件。
- **证据目录不推**：`evidence/`、`agents-results/`。门禁要读其中某个目录时，用 `RBOX_WITH='evidence/2026-09-01/…'` 点名推。
- **私密文件不推**：`.env*`、`*.pem`、`*.key`、`auth.json`、`.claude*`、`.codex*`。
- **本机 Studio 数据不推**：`~/.photo-content-os/`（真实作品、照片）和素材根 `~/Desktop/照片筛选`。开发机上的 `LOCAL_MEDIA_ROOT` 指到一个空目录。
- **开发机上不许有 Claude、Codex 和 AI 凭据**：`rbox run`、`rbox bg` 发命令之前，先用 `ai_guard.py` 检查一遍。巡检时跑 `rbox ai-check`。

## 和本机不一样的地方（2026-10-27 装机时）

| 项 | 本机 | 开发机 | 影响 |
|---|---|---|---|
| Python | 3.13.16（Homebrew） | 3.13.9（uv 下的独立版） | 补丁号不同；第三方包按本机 `pip freeze` 装，版本一样 |
| PyTorch | 2.8.0 | 2.8.0+cpu | 开发机没有显卡 |
| ffmpeg | 9.0.2（Homebrew） | BtbN 静态版 master | 渲染结果的编码细节可能有差别 |
| 中文字体 | STHeiti（macOS 自带） | Noto Sans CJK | rbox 设了 `DIRECT_VIDEO_FONT`、`VIDEO_RENDER_TEST_FONT`；`tests/test_r277_boxes.py` 写死了 STHeiti，在开发机上找不到字体 |
| 浏览器 | `~/Library/Caches/ms-playwright` | `.tools/browsers`（同为 1228 版） | rbox 设了 `VIDEO_RENDER_BROWSER`、`VIDEO_RENDER_PLAYWRIGHT_MODULE` |

## 还不能上开发机的门禁

R277 `revision_frontend_gate.mjs`、R278 `rescript_frontend_gate.mjs`，以及 R276 `frontend_gate.mjs --real` 要复制本机真实的 Studio 数据（`~/.photo-content-os/studio-r276`、`studio-r278`，里面有用户的作品和照片），复制时用的 `/bin/cp -cR` 也只有 macOS 有。R278 还要读 `docs/tasks/R278-direct-rescript/design/img` 下没进 git 的图。真实数据能不能放到这台租来的机器上，要等用户定。用户没定之前，这三项留在本机跑，并且守本机预算（见 Core「本机例外的执行预算」）。R276 `--checks-only` 用的是合成数据，可以在开发机上跑。
