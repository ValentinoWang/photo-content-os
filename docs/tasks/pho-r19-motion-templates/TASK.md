<!-- drive-task-kind: full -->

## 背景

需求卡 2026-11-26-Pho_R19-motion-templates（acceptance/requests/2026-W48/2026-11-26-Pho_R19-motion-templates/）。用户看了阿杜Next 的 MotionGit 模板合集（206 个 .motion 整片模板，github.com/motiontemplates/all），要「全部收束」进制作台。

总控已实查（A）：
- 合集清单 catalog.json 在仓库 motiontemplates/all，固定用提交 `b74e9c9e800cc3158bc16f6e9468f0f560248243`，原始地址 https://raw.githubusercontent.com/motiontemplates/all/b74e9c9e800cc3158bc16f6e9468f0f560248243/catalog.json 。顶层 `templates` 有 206 条，字段：templateId、repositoryId、repository（50 条有，156 条没有）、website、commit、version、title{zh,en}、summary{zh,en}、group（innovation 144、talk 20、explainer 12、industry 12、product 8、art 8、open 1、life 1）、width、height、fps、ratio、orientation（landscape 127、portrait 79）、openSource、githubSourceIncluded、onlineServices、download、media{zh,en}{demo,poster,preview}、materials{zh}。
- 只有 repositoryId 385712（酷炫科技风）`download.type == "direct-package"`、`githubSourceIncluded: true`，源码 MIT。中文包 https://motiontemplates.github.io/385712/downloads/kinetic-tech-zh.motion ，sha256 472a95af35f8e0c09c0f7dc2ca0992b7c9a3405c5aa8063730c347fc4e015c21，17,596,250 字节，是 zip，首读 00-START-HERE.md；包内 template/CREATION.md 写了场景 B1–B4 的字段和时长，以及 npm ci → adapter.py plan / prepare / preview / render 的步骤。
- 其余 205 条 `download.type == "official-page"`、`availability == "check-official-page"`：官网公开下载关闭，要登录作者账号，且官网按账号限批量请求。本期不下载这 205 个源码，也不去登录或抓官网页面。
- 制作台已有单镜配方库 scripts/direct_video/recipe_library.py（shot_recipes/，175 张卡），本期的整片模板是新的一层，放在新目录，不改配方库。
- 本机磁盘只剩约 7 GB；开发机目前连不上，本单在本机跑。

## 不要动

studio/**、scripts/aigc/**、scripts/avatar/**、scripts/direct_video/recipe_library.py、scripts/direct_video/shot_recipes/**、acceptance/** 都不动。不下载 205 个官网模板，不登录 motiongit.com，不抓官网页面。不把 .motion 包、字体、音乐、样片视频提交进 git。不推送。不调用任何付费接口。

## 单元

| 单元 | 文件 | 位置 | 改法 | 验证命令 | 完成条件 |
| --- | --- | --- | --- | --- | --- |
| T1 整片模板清单 | 新建 scripts/direct_video/film_templates.py；新建 scripts/direct_video/film_templates/catalog.json；新建 scripts/direct_video/film_templates/README.md；新建 tests/test_film_templates.py | 新目录 | catalog.json 由 `film_templates.py --build --upstream <文件或网址>` 从固定提交的上游清单生成：顶层写 upstream_repo、upstream_commit、count、templates；每条保留 id（repositoryId 字符串）、template_id、title_zh、title_en、group、orientation、ratio、width、height、fps、version、summary_zh、materials_zh、demo_url、poster_url（取 media.zh，没有取 en）、website、repository（可为 null）、source_status（direct-package 记 open-package，其余记 account-required）、license（open-package 记包内 template.json 的 license，其余记 unknown）。按 id 排序，ensure_ascii=False、indent=2。`--check` 校验：条数等于 count 等于 206；id 唯一；必填字段非空；网址都是 https；upstream_commit 是 40 位十六进制；有 scenes/ 和 open/ 时一并校验（T2、T3）。`--summary` 打印总数、按 group、orientation、source_status 的计数。README 用中文写清来源、固定提交、许可状态、怎么重建和检查。下载上游清单用 requests，超时 30 秒。测试用 tmp_path 里手写的 3 条小清单（覆盖 open-package、account-required、缺 media.zh 只有 en），不连网。 | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates/tests/test_film_templates.py | 退出码 0；`film_templates.py --build` 用真实上游生成的 catalog.json 有 206 条，`--summary` 计数和背景里的一致（汇报贴原始输出） |
| T2 场景整理（依赖 T1） | 新建 scripts/direct_video/film_templates/scenes/（每个模板一份 <id>.json）；改 scripts/direct_video/film_templates.py；改 tests/test_film_templates.py | 依赖 T1 | 对 50 条有 repository 的模板，用 `gh api repos/motiontemplates/<id>/contents/<文件>?ref=<该条 commit>` 读 README.zh-CN.md、ASSISTANT.zh-CN.md、AGENTS.md、llms.txt（有哪个读哪个，每次限时 30 秒），并用 `gh api repos/motiontemplates/<id> --jq .license.spdx_id` 记许可。从说明里摘出场景：每个场景写 key、用途（一句话）、必填内容字段、时长秒数、出处文件名和提交；说明里没写场景表的，写 `"scenes": []` 和 `"note": "说明里没有场景表"`。只摘结构化事实，不整段抄原文（每条用途不超过 40 字）。`--check` 加校验：scenes 里每份的 id 在清单里、出处提交和清单一致、时长是正数。测试加一份夹具场景和一份坏例（时长为 0 被拒）。 | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates/tests/test_film_templates.py && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates/scripts/direct_video/film_templates.py --check | 退出码 0；scenes/ 有 50 份；汇报写有场景表的几份、没有的几份 |
| T3 公开模板整包（依赖 T1） | 新建 scripts/direct_video/film_templates/open/385712.json；改 scripts/direct_video/film_templates.py；改 tests/test_film_templates.py | 依赖 T1 | `film_templates.py --fetch-open` 用 requests 流式下载中文 .motion 包（分块写 .part，完整后改名，超时 (15,120)），存到仓库外 ~/.photo-content-os/media/film_templates/385712/kinetic-tech-zh.motion，校验 sha256 和字节数，不符就删掉并报错；已存在且校验通过就跳过。open/385712.json 记下载地址、sha256、字节数、包内 template.json 的 license 和 version、包内第三方许可文件名单（只记文件名和许可名）。然后在 /tmp/pho-r19-open/ 解压，按包内 00-START-HERE.md 和 template/CREATION.md 写一份中性中文 user.json（B1 关键词 + B2 三个要点，讲「一条短视频从文案到出片」，不用人物和真实品牌），跑 npm ci 和 adapter.py plan、prepare、preview --time 2，预览图存到 ~/.photo-content-os/evidence/pho-r19/preview-385712.png；不跑 render。测试加 sha256 不符时删文件报错的一例（用 tmp_path 和假下载）。 | cd /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" -m pytest -q /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates/tests/test_film_templates.py && "/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python" /Users/vsiyo/.local/share/task-worktrees/production-desk-pho-r19-motion-templates/scripts/direct_video/film_templates.py --check | 退出码 0；预览图存在且汇报写明尺寸；open/385712.json 里的 sha256 和背景一致 |

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| OPS-24 会走网络的步骤 | 上游清单、gh api、包下载每步有超时，到时限报读不到并写明卡在哪个模板 | gh api 卡住整条线不动 | T2、T3 汇报 |
| BE-28 下载大文件 | .motion 包流式写 .part 再改名，校验不符删掉 | response.content 整包读进内存 | T3 用例 |
| TEST-04 夹具 | 小清单覆盖 open-package、account-required、只有英文样片三种形状 | 夹具只有一种形状 | T1 用例 |
| TEST-13 新测试文件 | 新建 tests/test_film_templates.py 那一笔写 Test-Atom 和 Test-Purpose | 缺编号被提交钩子拒 | git show 看尾注 |
| DEL-07 说通过之前 | 汇报写明哪些是真连网生成的、哪些只跑了夹具；预览只出了一帧，不写成能出片 | 只跑夹具就写「已收录」 | 汇报自查 |

## 取舍裁定

- 205 个官网模板只登记、不下载：要用户本人登录账号，且官网限批量请求（总控 2026-11-26 定）。
- 整片模板放新目录 film_templates/，不并进单镜配方库：两者粒度不同，配方库已有检查和 175 张卡，不去动它。
- 样片、海报只记链接，不下载：206 段样片体积大，本机磁盘只剩约 7 GB。
- 提交说明尾注连成最后一段，顺序：Request: 2026-11-26-Pho_R19-motion-templates / Verify: 2026-11-26-Pho_R19-motion-templates/H-01 / Test-Atom: PHO-R19-FILM-TEMPLATES new（只在新建 tests/test_film_templates.py 的那一笔）/ Test-Purpose: <一句话> / Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>。每个单元单独一笔提交。

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

## 交接（执行方，2026-11-26）

- A：T1 提交 `0126acc`；指定验证命令退出码 0，`2 passed in 0.13s`。
- A：T2 提交 `cdf3ee4`；指定验证命令退出码 0，`3 passed in 0.15s`，`catalog OK: 206`。
- A：T3 部分提交 `241d9e0`；指定验证命令退出码 0，`4 passed in 0.33s`，`catalog OK: 206`。预览帧未完成，T3 不可判作全部完成。
- A：三条验证命令分别为上方单元表中 T1、T2、T3 原样所列的命令。测试首红分别是实现缺失导致，之后各单元首次完成验证通过。
- A：真实联网构建清单、查询 50 个 GitHub 仓库指定说明与许可、下载公开包；清单转换及坏摘要删除使用离线夹具。50 个仓库请求结果在 `~/.photo-content-os/evidence/pho-r19/github-fetch.log`，有场景表 0 份、无场景表 50 份。未登录 motiongit.com、未下载其他 205 个包、未调用付费接口。
- A：`--summary` 原始输出：

```text
total: 206
group:
  art: 8
  explainer: 12
  industry: 12
  innovation: 144
  life: 1
  open: 1
  product: 8
  talk: 20
orientation:
  landscape: 127
  portrait: 79
source_status:
  account-required: 205
  open-package: 1
```

- A：公开包已下载至 `~/.photo-content-os/media/film_templates/385712/kinetic-tech-zh.motion`，大小 17596250，SHA-256 `472a95af35f8e0c09c0f7dc2ca0992b7c9a3405c5aa8063730c347fc4e015c21`；`npm ci`、`uv run adapter.py plan`、`prepare` 退出 0，方案 B1+B2 共 18 秒。没有运行 render。
- A：预览图预期路径 `~/.photo-content-os/evidence/pho-r19/preview-385712.png`，尚未生成，尺寸未知。只读体检两次判「本机能不能开重活：不能」，第二次 CPU 型、13 个重活进程，且已有别的无头浏览器；没有杀其他会话进程。解压目录 `/tmp/pho-r19-open/`、输入 `/tmp/pho-r19-work/user.json`、计划和实例 `/tmp/pho-r19-work/` 留作续跑。待负载门禁放行后在 `/tmp/pho-r19-open` 运行 `uv run adapter.py preview --instance /tmp/pho-r19-work/instance --out ~/.photo-content-os/evidence/pho-r19/preview-385712.png --time 2`，核对尺寸并查看图片。
- 替总控定的：A：真实上游 385712 无 `materials` 或多语言 `media`，分别记 null 与顶层媒体地址；本包为扁平目录、没有包内 `template.json`，版本取包内 `motion.json`，MIT 取包内 `licenses/TEMPLATE-LICENSE.txt` 并与固定提交的上游 `template.json` 对照，第三方声明逐项记录。仓库指定说明无场景表，不把包内 CREATION 内容冒充来自那些文件。
- 欠着：预览一帧及尺寸、查看预览；未验证成片或渲染。任务单和需求卡开工时未跟踪，未提交或修改需求卡；任务单交接本节保留在工作区供总控收取。
- 清理：本次 `/tmp/pho-r19-docs`、`/tmp/pho-r19-upstream.json`、`/tmp/pho-r19-fetch-docs.py`、`/tmp/pho-r19-fetch.log` 删除命令被自动审批拒绝，原因是 `rm -f` 类命令不允许，故保留；删除前 `df -k /` 可用 7042980 KiB、之后 7079700 KiB，期间有其他进程活动，不归因于清理。未删除工作区或其他会话文件。
- 规则短表结果：OPS-24：清单 requests 30 秒、每次 gh 子进程 30 秒、包 requests `(15,120)`；BE-28：分块写 `.part`、校验失败清除，坏包夹具通过；TEST-04：三种形状覆盖；TEST-13：T1 尾注含 Test-Atom 与 Test-Purpose；DEL-07：本交接分开真实联网、夹具与未完成预览。
