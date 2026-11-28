<!-- drive-task-kind: full -->

## 背景

制作台接入前端设计工具（NFD）还缺截图包，巡检 72 小时内要补齐。上一轮（同一线程，在 NFD 工作区 `/Users/vsiyo/.local/share/task-worktrees/New_Fronted_Design-photo-nfd-gallery`）已查明：NFD 自带的 `capture plan|script|pack` 只支持有路由的框架，Studio 是零构建原生单页应用，计划产出 0 页（你的报告缺陷 1）。总控裁定：**不改 NFD**，按分工「采集归项目」，在制作台写项目自己的拍图脚本，直接产出符合 `/Users/vsiyo/.local/share/task-worktrees/New_Fronted_Design-photo-nfd-gallery/docs/impl/screenshot-package.md` 的截图包（manifest.json、steps.json、图片）。

Studio：`studio/static/index.html`，左侧导航 `[data-nav="home|inbox|projects|library|music|settings"]` 切六个视图，切换时先清空容器再异步 fetch 渲染（你报告里的附带发现），项目详情由点击进入。目标端桌面，视口 1440×900。

开发机 photo-dev 连不上（上一轮已实测），在本机跑：浏览器无头、同一时间一个。本机磁盘只剩 3 到 4 GB，截图总量控制在 300 MB 内。

## 不要动

- 只在本工作区 `/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery` 新建 `scripts/capture_nfd_gallery.py`、`tests/test_capture_nfd_gallery.py` 和本任务单；不改 `studio/` 下任何文件，不改 NFD 仓库（`/Users/vsiyo/.local/share/task-worktrees/New_Fronted_Design-photo-nfd-gallery` 那边上一轮没有改动，保持原样）。
- 演示数据只用虚构的：`scripts/create_demo_project.py` 造到临时目录，Studio 用临时 `--state-dir`；不碰 `~/.photo-content-os/studio`、`~/Desktop/照片筛选` 等真实目录。
- 拍图走真实 Studio 服务和真实接口（不用夹具拦接口），所以图片封面这类接口能正常出图；只发 GET，不点会触发模型、渲染、写盘的按钮。
- 不调任何付费接口。截图文件不进 git。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| U1 项目拍图脚本 | `/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/scripts/capture_nfd_gallery.py`（新建）、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/tests/test_capture_nfd_gallery.py`（新建） | 新文件 | 用 `/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/.venv/bin/python` 能跑的 Python + Playwright（同步接口）。参数 `--out <截图包目录>`（必填）、`--port`（默认向系统要空闲端口）。流程：建临时工作区和 state 目录 → 用 `create_demo_project.py` 造演示项目 → 起 `scripts/launch_studio.py --state-dir … --port … --no-browser`，读回实际地址 → 无头 Chromium 1440×900 打开 `/`，依次点六个 `[data-nav]`，每次点完等该视图容器有内容、网络空闲再拍；再进演示项目详情拍一张 → 每张整页按 FE-12 分段滚动拼回整页 → 按 screenshot-package.md 写 manifest.json（每页稳定 id、uuid、标题、角色、路由用 `/#<nav>` 这类能复现的写法、视口、整页高度、拍图时间、分组、一级入口；分组按导航，首页排第一）和 steps.json（导航点击的跳转，证据写「实测」）→ 无论成败都停服务、关浏览器、删临时目录。纯函数（manifest 行生成、分组排序、steps 生成）写单元测试，不在测试里起浏览器 | `cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery && /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/tests/test_capture_nfd_gallery.py && /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/.venv/bin/python /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-nfd-gallery/scripts/capture_nfd_gallery.py --out ~/.photo-content-os/evidence/nfd-gallery` | 两步退出码都是 0；截图包目录有 manifest.json、steps.json 和 7 张以上整页图；你用看图工具逐张看过，没有空白页、报错页、半渲染态；跑完本机无头浏览器数回到开跑前的数，8765 以外你起的端口都已关 |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| OPS-13 在本机跑浏览器 | 开跑前数本机重活实例（无头浏览器只数带 --headless、不带 --type= 的主进程），非 0 记 pid、启动时间、父进程链；浏览器无头、同一时刻一个，量完就关 | 不数就开；开了不关 | `pgrep -fl -- '--headless' \| grep -v -- '--type=' \| wc -l` 开跑前、跑完各记一次 |
| FE-12 整页截图 | 长页面分段滚动拼回整页，接缝无重叠无缺口；视口保持 1440×900 | 用超出视口截图把整页挤进一张；截断 | 汇报每页整页高度和拼图高度对得上 |
| TEST-06 浏览器检查起服务 | 端口向系统要空闲的再交给服务，起来后读回实际地址 | 写死 8765（用户可能开着自己的 Studio） | 用户的 8765 在跑时脚本照常完成 |
| OPS-10 自动清理 | 临时目录、服务、浏览器在成功和失败两条路上都清掉 | 失败时留下 Studio 进程 | 故意给错 `--out` 父目录跑一次，进程和临时目录都不留 |
| TEST-13 新增检查文件 | 新测试文件的提交写 `Test-Atom: <编号> new` 和 `Test-Purpose: <保护什么>` | 缺 Test-Atom 被提交钩子拒 | 提交钩子通过 |

## 取舍裁定

- 不改 NFD 工具；NFD 的缺陷（原生单页应用无路由、states 分组、auth none、点击后无等待、夹具只回 JSON）由总控另行登记，你不处理。
- 只拍桌面 1440×900；只拍六个导航视图和一个演示项目详情，不拍弹窗、抽屉。
- 截图包放仓库外 `~/.photo-content-os/evidence/nfd-gallery/`；NFD 适配文件的 `gallery` 登记由总控做。
- 提交：只提交 U1 两个新文件和本任务单，一个提交；说明末尾尾注连成最后一段：`Test-Atom: <编号> new`、`Test-Purpose: …`、`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。不推送，由总控推。

## 固定规则

- 工作区主人是派你的会话 acb21613-1a28-47b7-94bd-d04d982c096a，你是它派的执行方，不运行 claim、adopt，不为身份停下。
- 只在自己的任务工作区改动，只提交任务单授权范围内自己的改动，不回退或提交别人的改动，不杀别人的进程。其他线造成的失败只列出，由总控协调。
- 测试、构建、服务在前台跑完才读结果；服务用完自己停。汇报前确认自己起的后台命令已经结束；不以后台任务或稍后通知代替退出码。
- 每个单元只跑任务单的一条验证命令并保留真实退出码；有管道启用 pipefail。可能很长的输出（测试日志、rbox status 这类状态命令、生成文件、整份源码）不整份打印：日志和状态只读 tail -40 或 rg 出要的行，源码先 rg -n 定位再 sed -n 读区间；单条命令输出预计超过 200 行先截断。`rg` 带 `--max-columns 300`，只要文件名时用 `rg -l`。实现完成后的验收验证首次失败最多再改一次；仍失败交回 tail -40、真实退出码和 git diff --stat。写新功能时测试先红（含新组件未建导致的编译失败）、门禁命中按门禁给的修法修，都不算这里的失败，不停下。
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
