<!-- drive-task-kind: full -->

## 背景

用户 2026-11-23 定：剪辑主力从 ChatCut 换成 Concat（开源桌面剪辑软件，jub0t/Concat，AGPL-3.0，本机 0.2.12 已装在 `/Users/vsiyo/.local/share/concat-trial/app/Concat.app`），方向是「程序出粗稿，人打开粗稿再改」。原话：「明明依托于 Concat 的自研的开源剪辑才是最优解吧？」。决定记录：`/Users/vsiyo/Desktop/创业项目/内容创作/RefShelf/docs/decisions/2026-11-23-editing-route.md`；AGENTS.md「Historical Jianying material」一节已写明。

本机实测（必读，里面有真实调用顺序和踩过的坑）：`/Users/vsiyo/Desktop/创业项目/内容创作/RefShelf/docs/tasks/T6-concat-trial/REPORT.md`、`result.json`、`mcp-calls.txt`、`timeline.json`、`tools.txt`；实测用的 MCP 客户端 `/Users/vsiyo/.local/share/concat-trial/client/mcp.py`（可参考写法，不要从那里 import）。要点：`concat --mcp headless` 是标准输入输出上逐行的 JSON-RPC 2.0；写入目录要在环境变量 `CONCAT_MCP_ROOTS` 里；轨道序号越大越在上层；界面打开工程要 `open -n -a <Concat.app> --args --project <工程目录>`，`open -a` 只到欢迎页；captions_add 一次传多条，不直接读 SRT 文件；标题默认字号会折行，要给 fontSize。

要做的：在制作台剪辑后端里加一个 `concat` 后端，实现 `scripts/edit_backends/interface.py` 的 `EditBackend`，和 `otio_kdenlive`、`chatcut` 并列，由用户显式选择，不当别的后端的兜底。工作区：`/Users/vsiyo/.local/share/task-worktrees/production-desk-concat-backend`，分支 `line/concat-backend`。

## 不要动

- 不改 `chatcut`、`otio_kdenlive`、`openfilm`、`openchatcut` 各后端的行为和它们的测试断言；`registry.BACKENDS` 只加一行 `concat`，相关测试里写死的后端集合跟着加上 `concat`。
- 不改 Studio 界面（`studio/` 下的页面文件）；Studio 选编辑器的设置值如果只认固定名单，只在名单里加 `concat`，不改页面。
- 不装 brew 包，不改 Claude、Codex、ChatCut 的配置，不运行 `claude mcp add`。
- 不往 `/Applications` 装 Concat；Concat 路径用环境变量 `CONTENT_OS_CONCAT_APP`（默认 `/Applications/Concat.app`，找不到就 probe 报 unavailable，不去别处猜）。
- 不推 main。只推 `line/concat-backend` 到 origin，合并由总控做。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| U1 MCP 会话 | 新建 scripts/edit_backends/concat_mcp.py | 新文件 | 一个只用标准库的 MCP 客户端类：启动 `<app>/Contents/MacOS/concat --mcp headless`（环境带 `CONCAT_MCP_ROOTS=<工程上层目录>`），握手、`call(tool, args)`、超时、逐次调用记入调用方给的日志文件、`close()` 按自己起的进程号收尾；工具报错原样抛 `BackendError("concat_tool_error:<工具>:<原文首行>")` | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-concat-backend/docs/tasks/concat-backend/verify_unit.sh` | 用假 MCP 服务（测试里起一个 Python 子进程按 JSON-RPC 回包）测握手、正常调用、工具报错、超时、close 后无残留进程，全过 |
| U2 后端（依赖 U1） | 新建 scripts/edit_backends/concat_adapter.py；scripts/edit_backends/registry.py | registry 的 BACKENDS 表 | `Backend` 实现 describe / probe / render / open_for_refine / read_back / close。render：建工程 → 导入 source → 按 `suggestions_path` 里可自动执行的删除段（和 `chatcut_handoff.prepare_package` 用同一套筛选：type 为 silence 或 repetition 且 auto_cut_allowed）切掉 → subtitles（SRT）解析后 captions_add → animations 里的透明 MOV 放到源视频上面一层对应时间 → project_save → export 一个预览 MP4 → 回执写 output_dir（工程路径、调用日志、导出文件、time_map）。open_for_refine 用 --project 打开。read_back 用 timeline_read 读回段落和字幕，转成 render_kwargs，不从之前生成的方案推断。describe 的能力按 T6 实测填：automatic_first_cut、transparent_overlay、chinese_subtitle_burn_in、undo、read_back 为 True，export_formats ["mp4"]，license "AGPL-3.0" | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-concat-backend/docs/tasks/concat-backend/verify_unit.sh` | 全过（现有后端测试不改断言，只在写死的后端集合里加 concat） |
| U3 本机真机冒烟（依赖 U2） | 新建 tests/manual/concat_smoke.py | 新文件 | 本机脚本：用 ffmpeg 生成 20 秒 1080×1920 测试片、一份 3 条中文 SRT、一份含 2 段 silence 删除的 suggestions、一段 2 秒透明 MOV，调 `registry.get_backend("concat").render(...)`，再 read_back，打印段数、总时长、字幕条数、导出时长 | `CONTENT_OS_CONCAT_APP=/Users/vsiyo/.local/share/concat-trial/app/Concat.app /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python /Users/vsiyo/.local/share/task-worktrees/production-desk-concat-backend/tests/manual/concat_smoke.py` | 本机跑（Concat 只在 Mac）。退出码 0；打印的总时长 = 20 − 删掉的秒数（差 1 帧内），字幕 3 条，导出 MP4 时长一致；用 preview_frame 取一帧透明层时间点的图，自己打开看下层画面透出 |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| OPS-05 写脚本、起子进程 | 子进程退出码和报错原样传出；写操作逐条判退出码 | MCP 工具报错被吞，回执写成功 | U1 的工具报错用例 |
| OPS-03 / OPS-04 停进程 | close 只停自己起的进程，按进程号 + 启动时间核对 | 用 pkill -f concat 误杀用户开着的 Concat | U1 的 close 用例：另起一个同名进程，close 后它还在 |
| OPS-13 本机跑重活 | 测试在开发机跑；只有 U3 冒烟在本机（Concat 只在 Mac） | 在本机跑整套 pytest | 汇报写 U3 开跑前 `sysctl vm.swapusage` |
| BE-11 读不到不是没有 | Concat 不在、握手失败、工具报错分开报，不写成「没有工程」 | probe 找不到 app 却报 online | U2 probe 用例：app 路径不存在 → unavailable |
| TEST-13 加测试 | 新测试文件提交带 `Test-Atom` 和 `Test-Purpose` 尾注 | 提交检查拦下没编号的新测试文件 | 提交钩子 |
| DEL-07 说通过之前 | 冒烟真跑 Concat；替身只用在 U1、U2 单元测试，汇报写明哪段用了替身 | 只跑假服务就写「Concat 后端可用」 | U3 输出原文进汇报 |

## 取舍裁定

- 删除段的筛选和 ChatCut 后端用同一个函数：把 `chatcut_handoff.prepare_package` 里那段筛选抽成一个共用函数放进 `edit_backends`，两边都调它；ChatCut 的行为和测试断言不变。
- U1、U2 的验证脚本 verify_unit.sh 经 rbox 在开发机上跑 tests/test_concat_backend.py 和 tests/test_edit_backend_interface.py，不改这个脚本。
- 切段写法照 T6：整段放进时间线后在删除段边界 clips_split，再 clips_remove（ripple）。
- SRT 由我们解析（`scripts/` 里已有 SRT 读取函数就用它），captions_add 一次传全部条目。
- 透明叠层用 ProRes 4444 MOV；放在比源视频序号大的轨道。
- 回执格式参照 `kdenlive_adapter` / `kdenlive_render.render` 的返回字段，缺的字段写 None，不编。
- 需求卡、验收卡：提交时钩子要求什么照做（项目用 acceptance-handoff）；要求人工验收签名的，递交卡、写明「等用户」，不代签。
- 任务单没覆盖的取舍按「最简单、与现有后端一致」自己定，写进汇报「替总控定的」。

## 固定规则

- 工作区主人是派你的会话 f0e53bb4-e2fa-4d4e-b8e9-d691fc136b32，你是它派的执行方，不运行 claim、adopt，不为身份停下。
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
