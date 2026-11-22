<!-- drive-task-kind: full -->

## 背景

需求卡 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/acceptance/requests/2026-W47/2026-11-22-Pho_R05-shotcraft-line/`（只读），计划 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/PLAN.md`，先读这两份。上游 shotcraft 本机克隆 `/Users/vsiyo/Desktop/创业项目/内容创作/video-shotcraft`（只读，固定提交 `3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d`，Apache-2.0）。工作区 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line`，分支 task/pho-r05-shotcraft。三条线（P1、P2、P3）并行，各改各的文件，别人的文件不碰。

先例：R283 把 code-video-showcase 九种风格改写进 `scripts/direct_video/style_library/`，看 `docs/tasks/R283-direct-style-library/` 下的 TASK.md、SAMPLES-TASK.md、REPORT-S.md 学它的格式和渲染方式。

你做 P1：把 shotcraft 的 124 张镜头配方卡原样收进制作台，成为口播直出和宣传片共用的镜头配方库。只搬文字卡，不搬 Remotion 代码、demos、gallery、视频和音频。

## 不要动

- 不改 `scripts/direct_video/style_library/`、`scripts/direct_video/lint.py`、`scripts/video_render/`（归别的线）。
- **本机例外预算**：开发机 photo-dev 连不上，渲染在本机跑。浏览器只开无头的、同一时间只开一个、用完就关；渲染走 `render_style_sample.sh` 用的同一把内核文件锁排队；不跑全量 pytest；磁盘低于 3 GB 停下汇报。
- 缺 `.venv` 就运行 `bash scripts/setup_dev_environment.sh` 建；Playwright 和浏览器按 R283 REPORT-S.md 的写法用 `VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER` 指向本仓库 `.tools/` 下的固定版本（主检出 `/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.tools/`）。
- 不提交、不推送、不改已有提交；脚本里不写本机绝对路径（仓库安全检查会拦），用 `$HOME` 和相对路径。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| P1-1 | 新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/shot_recipes/<类别>/<id>.md`（124 张）、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/shot_recipes/ATTRIBUTION.md`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/shot_recipes/LICENSE-video-shotcraft.txt`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/shot_recipes/README.md`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/shot_recipes/index.json`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/recipe_library.py`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/tests/test_pho_r05_recipe_library.py` | 新建文件 | 1) 从上游 `references/shots/` 逐字复制 10 个类别目录下的 .md 和 `ATTRIBUTION.md`，上游 `LICENSE` 复制为 `LICENSE-video-shotcraft.txt`。卡内容一字不改。2) `recipe_library.py`：读每张卡的 frontmatter（name、一句话、适用、时长、能量、标签），生成并校验 `index.json`（按类别、文件名排序；每条 id、category、path、summary、use、duration、energy、tags，再加 `portrait_fit`：卡里含「竖屏」「9:16」或时长与动作不依赖横向铺展的标 true，拿不准标 null 并在 README 列出）；提供 `load_index()`、`get(id)`；`python3 scripts/direct_video/recipe_library.py --check` 校验 124 张、10 类、每条字段齐、文件与上游逐字节一致（比较 sha256，上游路径用参数 `--upstream` 传入）。3) README 写上游仓库、提交号、许可、「只搬手法卡、不搬代码和素材」、类别数量表、竖屏适用表。4) 测试覆盖：数量、字段、id 唯一、`get` 找不到报错。 | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/verify-P1.sh` | 退出码 0；汇报写到 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/REPORT-P1.md`（数量表、portrait_fit 为 null 的清单） |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| 第三方内容 | 保留许可原文和来源，固定上游提交 | 只抄内容不带许可 | `--check` |
| 读不到不等于没有 | 卡缺字段报错，不填默认值 | 缺「时长」写空串 | 测试 |
| 删除与精简 | 不搬用不上的 Remotion 代码和素材 | 整目录复制 | `git status` |

## 取舍裁定

- frontmatter 字段名以上游为准（中文键），index.json 用英文键。
- 卡里引用上游路径（如 `template/...`）不改，README 说明这些路径指上游仓库。

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
