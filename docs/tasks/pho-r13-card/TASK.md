<!-- drive-task-kind: unit -->

## 背景

Pho_R13 数字人口播片段的源码已推到 origin/main（542ece0 A1、e6bd291 A1b、08eff20 任务单、0556ebb 机器证据）。推送门禁报 G1「提交没有卡片覆盖」、G12「缺少同编号验收卡」。这一单只递交交付验收卡，不改源码。
写法照抄同项目最近一张同类卡：提交 d512ebe（「递交 Seedance 镜头生成验收卡」，卡目录 acceptance/human/2026-W48/未-2026-11-24-Pho_R11-seedance-provider，任务根 agents-results/2026-11-24/Pho_R11-seedance-provider）。先 git show --stat d512ebe 看它改了哪些文件，再用同一套脚本 /Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py（先跑 --help 和 handoff --help）生成本卡。需求卡在 acceptance/requests/2026-W48/2026-11-25-Pho_R13-avatar-clip/，H-01 的验收标准以它为准。
人工项 H-01 的清单写成用户自己执行：本人确认费用（一次约 0.9 元：videoretalk 11 秒，0.08 元/秒）后，用公开示例底片和配音运行 scripts/generate_avatar_clip.py --live 生成一段，看口型、看「AI 生成」标记，再原样运行一次确认沿用已有结果、不再提交。机器证据只写替身专项测试的结果，不调用任何百炼接口，不跑 --live（用户 2026-11-25 要求付费接口必须先经他同意）。
本卡的批准证据写：总控按任务单递交，人工项留给任务委托人，真实生成需本人确认费用。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| C1 递交 Pho_R13 交付验收卡 | acceptance/human/2026-W48/未-2026-11-25-Pho_R13-avatar-clip/handoff.json（新建）、acceptance/human/2026-W48/未-2026-11-25-Pho_R13-avatar-clip/binding.md（新建）、acceptance/human/2026-W48/未-2026-11-25-Pho_R13-avatar-clip/checklist.md（新建）、agents-results/2026-11-25/Pho_R13-avatar-clip/acceptance/acceptance-contract.md（新建）、agents-results/2026-11-25/Pho_R13-avatar-clip/acceptance/index.md（新建）、acceptance/human-acceptance-log.json、acceptance/human-acceptance-log.md | 照 d512ebe 的同名位置 | 用 manage_acceptance_artifacts.py 生成，不手写 log；source_commit 取 0556ebb；替身测试用 "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar/tests/test_avatar_videoretalk.py 本机跑（开发机不在线），结果写进 evidence。单独一笔提交，说明照 d512ebe 的三段式，尾注段只有 Acceptance: none — 仅递交验收物和投影，人工 H-01 待验。 再加 Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>。不推送。 | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar && python3 /Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py log --project-root /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar --check | 验证命令退出码 0（--check 不存在时改跑 log --project-root /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r13-avatar 后 git diff --exit-code acceptance/human-acceptance-log.json，退出码 0）；新卡目录三个文件齐全；git status 只剩 .githooks 和 docs/tasks/pho-r13-card/ 未跟踪 |

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
