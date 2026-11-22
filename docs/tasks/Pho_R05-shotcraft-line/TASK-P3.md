<!-- drive-task-kind: full -->

## 背景

需求卡 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/acceptance/requests/2026-W47/2026-11-22-Pho_R05-shotcraft-line/`（只读），计划 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/PLAN.md`，先读这两份。上游 shotcraft 本机克隆 `/Users/vsiyo/Desktop/创业项目/内容创作/video-shotcraft`（只读，固定提交 `3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d`，Apache-2.0）。工作区 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line`，分支 task/pho-r05-shotcraft。三条线（P1、P2、P3）并行，各改各的文件，别人的文件不碰。

先例：R283 把 code-video-showcase 九种风格改写进 `scripts/direct_video/style_library/`，看 `docs/tasks/R283-direct-style-library/` 下的 TASK.md、SAMPLES-TASK.md、REPORT-S.md 学它的格式和渲染方式。

你做 P3：把 shotcraft 的整片观感并进制作台已有的视频风格库，新增第十种风格「产品界面（ui）」；再把 shotcraft 审美准则 `/Users/vsiyo/Desktop/创业项目/内容创作/video-shotcraft/references/aesthetic-rules.md` 里能机器判断的条目并进直出检查。shotcraft 的色板体系看上游 `template/THEMES.md`、`template/themes/ui.cjs`，模板观感看 `template/TEMPLATE.md` 和 `template/src/`。

## 不要动

- 不改 `scripts/direct_video/shot_recipes/`、`scripts/direct_video/recipe_samples/`、`scripts/video_render/`。
- 不改已有九种风格的文件。
- **本机例外预算**：开发机 photo-dev 连不上，渲染在本机跑。浏览器只开无头的、同一时间只开一个、用完就关；渲染走 `render_style_sample.sh` 用的同一把内核文件锁排队；不跑全量 pytest；磁盘低于 3 GB 停下汇报。
- 缺 `.venv` 就运行 `bash scripts/setup_dev_environment.sh` 建；Playwright 和浏览器按 R283 REPORT-S.md 的写法用 `VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER` 指向本仓库 `.tools/` 下的固定版本（主检出 `/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.tools/`）。
- 不提交、不推送、不改已有提交；脚本里不写本机绝对路径（仓库安全检查会拦），用 `$HOME` 和相对路径。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| P3-1 | 新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/ui.html`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/ui.json`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/ui.jpg`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/ui.mp4`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/LICENSE-video-shotcraft.txt`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/index.json`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/style_library/README.md` | 新建与末尾追加 | 照 R283 九种的格式：同一段「聚光灯效应」台词、1080×1920、30fps、360 帧，json 字段与 `flat.json` 相同（id、name、recipe、palette、typeScale、motionSummary、bannedShort、motionRules、banned、visualGrammar、adapted）。观感取 shotcraft 的产品界面宣传片：浅色界面卡片、单一强调色、界面元素依次入场。用 `bash scripts/direct_video/render_style_sample.sh ui` 渲染，逐张看联系表，最多三轮。 | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/verify-P3.sh` | 退出码 0（测试若写死九种，按十种更新测试并在汇报说明） |
| P3-2（依赖 P3-1：同一线程先做 P3-1，验证脚本同时覆盖两者） | 新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/rules/aesthetic.md`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/scripts/direct_video/lint.py`、新建 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/tests/test_pho_r05_aesthetic_lint.py` | lint.py 内新增检查函数并接入现有入口 | 1) 逐条读 aesthetic-rules.md，分成「能从 HTML 和帧号机判」「只能看图」两类，`aesthetic.md` 列全部条目（编号沿用上游 R/Q/S/C/P）、归类和理由。2) 能机判的（如关键信息落定后静止 ≥1 秒、收尾停顿、匀速运动）在 lint.py 里实现为 WARN，不改变现有 ERROR 行为。3) 同时让 lint 支持横屏 1920×1080（画布尺寸从 HTML 读，字幕区按比例算），竖屏结果不变。4) 测试：每条新检查一个正例一个反例；横屏一个通过样例；现有九种风格 html 跑 lint 结果与改前一致。 | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/verify-P3.sh` | 退出码 0；汇报写到 `/Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/REPORT-P3.md`（机判条目清单、九种风格改前改后 lint 输出对比） |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| 改共用检查 | 现有样例结果不变 | 新检查把九种风格判失败 | 改前改后对比 |
| 第三方内容 | 保留许可原文与来源 | 只抄配色不写出处 | README |
| 读不到不等于没有 | 读不到画布尺寸报错 | 默认按竖屏算 | 测试 |
| OPS-13 本机跑浏览器 | 开渲染前数本机无头浏览器实例，不是 0 就等（最多等 30 分钟，期间写检查代码） | 不数就开 | 汇报写开跑前实例数 |
| TEST-13 新增检查 | 新检查写在 lint.py 现有检查结构里，每条带正例反例，测试文件开头注释写保护的规矩编号（aesthetic.md 里的上游编号） | 按修复零散加断言 | 测试 |

## 取舍裁定

- 新检查一律 WARN，升 ERROR 由总控定。
- 风格里的界面截图不用真实产品，用中性占位界面。

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
