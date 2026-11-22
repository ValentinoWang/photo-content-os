<!-- drive-task-kind: full -->

## 背景

用户 2026-11-22 手机原话：「不过这配方卡怎么这么丑就配房卡的封面液怎么这么丑？」。8 个镜头配方样张（`scripts/direct_video/recipe_samples/<id>/{portrait,landscape}.html`，封面取最后一帧）的毛病：内容挤在上半截、竖屏下半截空；配色发灰对比弱、8 张各用各的色；文字是「示意」「一段新的开始」这类占位话；顶上小标签像 App 界面不像视频画面。

总控已重画一张当标准：`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/blur-slide/portrait.html`（先读它，照它的结构、令牌、字号和片头标抄）。成片联系表：`~/.photo-content-os/evidence/Pho_R05-shotcraft-line/work/blur-slide-portrait/sheet.png`。

本线负责：blur-slide（只做 landscape）、marker-underline-title、gauge-readout-moves、beat-cut-moves，每个 portrait（1080×1920）和 landscape（1920×1080）两版。另一条线同时在做其余配方，不碰它们的目录。

## 不要动

- 每个配方的**动作手法和节奏**不改：读该配方现有 html 的 seekFrame 和 `notes.md`，入场顺序、帧数、缓动照原样搬到新版式上（元素换了就按同样的错峰规则套到新元素上）；`body data-hold`、`const D` 不改。
- 不改 blur-slide/portrait.html、渲染脚本、lint、不属于本线的配方目录；不提交、不推送；不用开发机（rbox / ssh），本机渲染。

## 视觉系统（全部照抄，不自创）

- `:root{--ink:#121317;--paper:#f3eee6;--accent:#ff5b2e;--mute:#8b8f98;--line:rgba(243,238,230,.14)}`，字体族照标准稿那一行。整张只用一个强调色 --accent。
- 深底（ink 底、paper 字）为默认；表里标「浅」的用 paper 底、ink 字，并在同一个 :root 后另写一条覆盖 --line 为 rgba(18,19,23,.12)、--mute 为 #6b6f78（:root 那一行原样保留，验证脚本要查它）。
- 片头标：左「● 制作台」，右「宣传片 · 0N」，下面一条 2px 细线；竖版 left/right 96、top 150、线 top 230；横版 left/right 120、top 80、线 top 150。
- 片脚：左右两段 34px（横版 30px）mute 色，右段 paper 色（浅底用 ink）；竖版 bottom 200，横版 bottom 90。内容照表。
- 字号档：主标题竖 160–180 / 横 120–140，加粗 700；眉题 46 / 40，accent 色、字距 8；正文 56 / 44；说明 34 / 30。全片不出现小于 30px 的字。
- 构图：竖版主体从 top≈620 起，主体加图形要占到画面高度 1/2 以上，不许下半截大片空着；横版文字放左半、图形（卡片、圆环、刻度、方格）放右半，垂直居中。
- 禁用：「示意」占位框、灰色占位块、App 式顶栏、emoji、多种强调色、阴影堆叠、渐变文字。

## 每张写什么（编号就是片头标的 0N）

| 编号 | 配方 | 底 | 眉题 | 主体 | 片脚 左 / 右 |
| --- | --- | --- | --- | --- | --- |
| 01 | blur-slide | 深 | 写好台词以后 | 「画面交给它 / 你只管说」（交给它用 accent），副句「按音乐小节出片，不用自己对轴」 | 125 BPM · 4/4 / 第 1–3 小节 |
| 02 | marker-underline-title | 浅 | 以前剪一条要一下午 | 两行大字「30 秒的片子 / 今晚就能发」，accent 记号笔划线画在「今晚」下面 | 宣传片 / 第 4–6 小节 |
| 03 | gauge-readout-moves | 深 | 先读你的配乐 | 竖向刻度尺 60–180（每 10 一格），指针停在 125；读数框 accent 底大字「125」，旁边小字「BPM」；下方正文「每一刀都切在重拍上」 | 4/4 拍 / 每小节 1.92 秒 |
| 04 | beat-cut-moves | 深 | 跟着鼓点换镜 | 一排 4 个大方格写 1 2 3 4（占满内容宽），按原配方的切点逐个点亮成 accent 实心，最后一帧 4 格全亮；格子上方大字「第 3 小节」，下方正文「镜头长短按小节算，不按秒猜」 | 125 BPM / 换镜 |
| 05 | product-card-progressive-assemble | 浅 | 这次做的是什么 | 卡片（宽约内容宽、ink 描边 2px、圆角 28、白底 #fbf8f3）逐块拼出：accent 方块图标内写白字「制」、名称「制作台」、副名「宣传片生产线」、三个标签「竖屏」「横屏」「按拍切」、数据行「124 张镜头配方 · 10 种风格」、底部 ink 实心按钮「开始做片」 | 本机运行 / 免费 |
| 06 | list-reveal | 深 | 从配乐到成片 | 4 行大列表，每行 accent 两位编号 + 大字 + 右侧 mute 小字：「01 选一首配乐 · 读出节拍」「02 写分镜 · 一镜一句」「03 挑镜头配方 · 124 张」「04 出成片 · 本机渲染」；行间 --line 分隔，最后一行整行 accent 字 | 四步 / 一个页面 |
| 07 | circle-match-iris | 深 | 渲染完成 | 大圆环（竖版直径约 640）从 0 走到 100%，弧用 accent、底环用 --line；环心大字「100%」；环下正文「成片已导出」、说明「1080 × 1920 · 0:30」 | 宣传片_v1.mp4 / 已保存 |
| 08 | spotlight-hero-card | 深 | 第一条做完了 | 保留聚光灯；被照亮的卡片：上半是 accent→#c23c1a 渐变的缩略画面（里面白字「画面交给它」），下半写「宣传片_v1.mp4」和 mute 小字「0:30 · 1080×1920」；卡片下方两行大字「下一条，/ 也这么做」 | 制作台 / 宣传片 |

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| P2R-A | `/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/blur-slide/landscape.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/marker-underline-title/portrait.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/marker-underline-title/landscape.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/marker-underline-title/notes.md`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/gauge-readout-moves/portrait.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/gauge-readout-moves/landscape.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/gauge-readout-moves/notes.md`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/beat-cut-moves/portrait.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/beat-cut-moves/landscape.html`、`/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/scripts/direct_video/recipe_samples/beat-cut-moves/notes.md` | 整个文件重写版式，seekFrame 动作照搬；jpg、mp4 由渲染脚本重新生成 | 按视觉系统和表重写；每张写完跑 `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/docs/tasks/Pho_R05-shotcraft-line/lint-one.sh <html>`（errors 必须为空，warnings 里的 number_unspoken 可留）；再先 export 下面的环境变量、跑 `bash scripts/direct_video/render_recipe_sample.sh <id> <portrait 或 landscape>`，用 Read 打开它打印的 sheet.png 逐张看，下半截空、字压线、元素出画就改了重渲；notes.md 第二段改写成新版内容说明，第三段写看过联系表的结论 | `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/docs/tasks/Pho_R05-shotcraft-line/verify-P2R.sh` | 本线负责的 id 在验证输出里一条都不出现（另一条线未完成的项会报，不算本线失败）；汇报写 `/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/.task-scratch/P2R-A-REPORT.md`，列每张的 sheet.png 路径 |

渲染环境变量：`export VIDEO_RENDER_PLAYWRIGHT_MODULE=$HOME/Desktop/创业项目/内容创作/production-desk/.tools/browser-runtime/node_modules/playwright/index.mjs VIDEO_RENDER_BROWSER=$HOME/Desktop/创业项目/内容创作/production-desk/.tools/browsers/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| FE-11 对外文案 | 文字照表抄，不自编口号 | 「一键成片」「让创作更简单」 | verify-P2R.sh 的 FILLER 检查 + 总控看图 |
| FE-15 全局观感 | 令牌、字号档照视觉系统一处取值 | 每张自己挑颜色 | verify-P2R.sh 的 NO SYSTEM 检查 |
| FE-26 观感 | 每张看过联系表才算完 | 只看 lint 绿 | 汇报里有 sheet 路径 |

## 取舍裁定

- 表里没写到的细节（图形具体尺寸、横版两栏比例）按「和 blur-slide 标准稿同一气质、最简单」自己定，写进汇报，不停下问。
- 上游动作里有图形而新版式没有对应元素的，把动作套到表里的主体图形上；实在套不上写进 notes.md。

## 派前核对（总控 2026-11-22 实跑）

- `bash /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-promo-entry/docs/tasks/Pho_R05-shotcraft-line/verify-P2R.sh`：标准稿 blur-slide/portrait 已全过；其余 15 张报 NO SYSTEM / FILLER / STALE（产物未生成），退出码 1。

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

## 交接（总控 2026-11-22 第 1 段后追加）

- 第 1 段（线程 01a2040f-d1d5）只读了材料，没改文件，从头做。原版动作用 `git show HEAD:scripts/direct_video/recipe_samples/<id>/<portrait|landscape>.html` 对照。
