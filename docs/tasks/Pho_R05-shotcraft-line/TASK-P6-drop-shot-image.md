<!-- drive-task-kind: unit -->

## 背景

用户 2026-11-23 说「镜头配方和截图只保留一个」。总控定：宣传片镜头表只留「镜头配方」，「截图」整项功能删干净（界面列、上传接口、存图、把截图交给 Opus、错误码、测试），不留没人用的代码。设计稿已改好并提交（c72d70d，docs/design-drafts/page-script-to-video--promo-line--Pho_R05/index.html 和 contract.json），照稿实现。

工作区：/Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image（已在 origin/main 之上多一笔稿子提交）。Python 用 /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python，Node 用 /Users/vsiyo/Desktop/Opensource_Tool/npm-global/bin/node。

已定取舍：
- 后端请求里每镜不再接受 imageId：按 generate.py 现有的字段校验方式处理，带了 imageId 的请求报 400（和其他未知字段一致）；若现有校验对未知字段是忽略，就照忽略，不新加规则，写进汇报。
- 前端本地草稿里旧的 imageId、imageUrl 直接忽略，不发给后端，不做迁移。
- 不删 state 目录里已存在的 direct-promo-images 文件夹（用户数据），只是不再写入、不再读取。
- 不改口播（talk）链路、不改配方弹窗、不改镜头详情。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| U1 前端 | studio/static/direct-promo.js、studio/static/direct-view.js、studio/static/direct.css | direct-promo.js 第 16 行 promoPayload、第 24 行表格模板、第 28 行 onImage 绑定；direct-view.js 第 164 行 onImage 上传；direct.css 第 170–172 行 .dv-shotpic 和 col.c-x 宽度 | 删「截图」列（th、td、col.c-x）、加截图按钮、onImage 参数和上传请求、payload 里的 imageId；删 .dv-shotpic 样式和 c-x 宽度 | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image && HARNESS_CORE=/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core STUDIO_PYTHON=/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python /Users/vsiyo/Desktop/Opensource_Tool/npm-global/bin/node /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_pho_r05_promo_frontend.mjs | 退出码 0，9 个状态 differences=0 |
| U2 后端（和 U1 同线程顺序做） | studio/server.py、studio/direct_recipes.py、studio/api_contract.py、scripts/direct_video/generate.py | server.py 第 1046–1059 行 promo-images 路由；direct_recipes.py 第 40–60 行存图函数；api_contract.py 第 30、235 行 uploadPromoImage 和第 244 行 shots 的 imageId；generate.py 第 127、136、379–385、546–588、624 行 | 删上传路由、存图函数、契约里的接口和 imageId 字段、promo_image_invalid 错误码；generate 不再读 imageId、不再把截图拼进 image_paths（sample_images 保留） | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image && /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_api.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_video.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_c.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_d.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_media.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_ps7_direct.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_pho_r05_promo_plan.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_pho_r05_recipe_library.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_music_library.py /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r223_music_analysis.py | 退出码 0；在 studio、scripts、tests 三个目录 git grep promo_image、imageId、promo-images、uploadPromoImage、shotpic 都无输出 |
| U3 测试（依赖 U1、U2） | /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r05-drop-shot-image/tests/test_r276_direct_api.py、tests/test_r276_direct_video.py、tests/test_pho_r05_promo_frontend.mjs | api 测试第 98–105 行上传断言；video 测试第 617 行起 test_promo_image_reaches_model_with_valid_suffix；前端测试第 20–21 行 payload 例子 | 删上传断言和截图进模型那条测试；前端 payload 例子去掉 imageId；api 测试里加一条：带 imageId 的宣传片请求按 U2 定的方式处理（400 或忽略） | 同 U2 的 pytest 命令和 U1 的 node 命令 | 两条命令都退出码 0 |

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

## 提交

三个单元做完后提交一笔（或按单元各一笔），提交说明尾行写：

Request: 2026-11-22-Pho_R05-shotcraft-line
Verify: 2026-11-22-Pho_R05-shotcraft-line/H-05
Lesson-Skip: 不是修复: 用户改需求，删掉截图功能
Co-Authored-By: Antigravity <noreply@google.com>
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

不推送，不 finish 工作区，汇报真实退出码和 git diff --stat。
