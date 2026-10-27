# R310 交付准备报告

记录时间：2026-10-27T09:26:12.243278+00:00

状态：**部分完成，按任务单停止**。G16 已通过；G12 仍失败，G1 仍有三笔提交缺卡，尚未达到「只剩人工未签」的目标。未创建 handoff，未暂存、未提交、未向业务 Git 远端推送。没有代签人工结果。

## 停止原因

开发机浅色专项实际返回九项通过，但同一次真实执行输出：

> [rbox] Harness 的 devbox_status.py 还没进主检出，这次不问在线判定

只读核查发现：默认检查器 `~/Desktop/Opensource_Tool/Harness_Engineering/Core/scripts/devbox/devbox_status.py` 不存在；`scripts/devbox/rbox:139` 的缺文件分支直接 `return 0`，仍继续同步和远端执行。这与该脚本说明及 README 的「读不到状态也停下」要求冲突。不是测试失败，也不是已证明开发机离线，而是缺少检查器时跳过了在线判定。

三份自测虽通过，`test_where.sh` 用的是存在的假检查器，覆盖返回 0、10、2，不覆盖检查器文件缺失；不能用它证明真实保护链完整。未通过环境变量或替身掩盖该问题。

TASK.md 明确要求「不改 scripts/devbox/ 和别的产品代码、测试、AGENTS.md。发现这些文件有问题，写进汇报后停下」。因此未改实现或测试，未继续生成机器全绿交付声明；交总控处理此依赖/失败放行分支，再重新冻结源码和证据。没有向用户增加批准流程。

## 已完成的验收准备

- 用 `git sparse-checkout add` 只补七个指定子目录：
  - `agents-results/2026-10-21/r223-delivery`
  - `agents-results/2026-10-26/R276-direct-video-opus`
  - `agents-results/2026-10-26/R277-shot-visual-revision`
  - `agents-results/2026-10-26/R278-direct-rescript`
  - `agents-results/2026-10-27/R280-studio-light`
  - `agents-results/2026-10-27/R282-direct-handoff`
  - `agents-results/2026-10-26/R283-direct-style-library`
- 在 `acceptance/surfaces.yaml` 增加 `scripts/devbox/** → photo.devbox`，作为开发工具范围，未标为验收物来改变源码身份。
- 在 `agents-results/2026-10-27/R310-photo-devbox/` 准备合同、baseline、claims、候选审阅记录、两份限定范围的机器运行及阻塞发现。不是 SSOT 开发包，无归档声明，不适用 Obsidian SSOT 快照。
- 在 `acceptance/human/2026-W44/未-2026-10-27-R310-photo-devbox/` 准备 checklist 和 binding。H-01、H-02 的步骤和预期直接读取当前 request.json，原样保留；角色为任务委托人，两项均为非阻塞。未创建 handoff，五分钟预算尚未递交。
- 合同检查 `check_acceptance_contract.py` 返回 `OK`。候选召回共 28 项，最高分 0.16909453722715678，无 L0 命中、无达到 0.35 的候选；入口分别是本机活动监视器/测试对话和同步清单，未改旧卡。

这些文件是未提交准备物，不能视为已递交或已通过的卡；未生成机器全绿 handoff、未刷新项目投影或声称 READY。

## 实际执行和边界

verified head：`40cf307c4`（完整值见 baseline.json）；base 为 `c1465ff`。本轮未改非验收物，源码身份未推进。

| 执行 | 位置 | 实际结果 |
| --- | --- | --- |
| `bash scripts/devbox/test_push_rules.sh` | 本机，获准例外 | 退出 0：rbox 推送清单自测全过 |
| `bash scripts/devbox/test_ai_guard.sh` | 本机，不加 --remote | 退出 0：开发机不跑 AI：门禁自测全过 |
| `bash scripts/devbox/test_where.sh` | 本机，假状态检查器 | 退出 0：rbox 在线判定自测全过；缺文件分支未覆盖 |
| `scripts/devbox/rbox run <任务 worktree> -- .venv/bin/python -m pytest -q tests/test_r280_light.py` | photo-dev，固定 .venv | 9 passed in 0.06s，退出 0；同时命中跳过在线判定问题 |
| `harnessctl acceptance check-delivery --project . --range origin/main..HEAD --read-only` | 本机，任务点名的交付只读检查 | 退出 1；完整结果如下 |

本机重活进程在三份自测之前为 **0**，之后仍为 **0**；未在本机跑 pytest、浏览器、渲染或前端门禁。只读交付检查也未启动浏览器。未动开发机真实 Studio 数据或媒体根，未安装环境或启动常驻服务。rbox 为执行远端测试自动同步文件和源码提交到开发机副本，这是远端执行协议；没有推送业务托管远端。

单元运行结论为 **PARTIAL**（夹具通过，但真实保护分支有缺口）；集成运行的 **PASS** 只指远端浅色九项，不代表完整迁移、等价渲染或总体交付通过。运行日志里的本机路径以 `~` 和「任务 worktree」替换，断言、结果和退出码未改。

## check-delivery 原样结果

开场复现：G1 FAIL（三笔提交缺卡）、G12 FAIL（缺同编号验收卡）、G16 FAIL（七张旧合同未检出），G6 WARN（scripts/devbox 未映射）；其他 G 项 PASS。

补检出后最终只读结果，逐行保留：

```text
check-delivery  origin/main..HEAD  (3 commits, tree d5ff6a3)
  G1 有卡  FAIL  非豁免提交没有对应卡片; 提交 cd10bae 没有卡片覆盖; 提交 c4faa52 没有卡片覆盖; 提交 40cf307 没有卡片覆盖 → 为非豁免提交创建交付验收卡；阻塞卡需用户通过，并遵守切片额度 → python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py handoff <任务根> --project-root . --replace --baseline <基准文件> --claims <声明文件> <原递交参数>；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py repair retired <不可恢复的未通过卡目录> --project-root . --actor <执行者> --reason <原因>
  G2 基准一致  PASS  
  G3 机器先绿  PASS  
  G4 看得懂  PASS  
  G5 有入口  PASS  
  G6 去重已声明  WARN  旧验收未声明范围：2026-10-27-R310-photo-devbox
  G7 失效传播  PASS  
  G8 坏一条不连累  PASS  
  G9 页面可见  PASS  
  G10 不自证  PASS  
  G11 有需求卡  PASS  
  G12 验收覆盖需求  FAIL  2026-10-27-R310-photo-devbox 缺少同编号的需求卡或验收卡 → Verify 属于所列需求；未覆盖及增删改标准在 claims.request_changes 逐项解释 → python3 tools/harnessctl.py acceptance request list --project .；python3 tools/harnessctl.py acceptance request new --help
  G13 沿用已有卡  PASS  
  G14 已通过不可变  PASS  
  G15 自动替代完整  PASS  
  G16 不连累前面的卡  PASS  
  G17 真实链路没被替换  PASS  
结果：FAIL（本命令如实返回门禁状态；推送策略由调用方应用）
```

G16 的缺合同问题已解决，未修改旧合同、旧保护测试或旧卡状态。G6 原来的未映射文件警告已消除，当前警告来自本卡仍处于准备中、未 handoff。G2/G3 等 PASS 在无本卡递交时不能解释为本任务完整机器验收通过。

## 总控已报告的历史结果（本轮未重跑）

| 范围 | 总控 TASK.md 的结果和限制 |
| --- | --- |
| 全量 `full-pytest-2` | 1204 通过、12 失败、36 跳过；绝非全绿 |
| 9 项本机同样红 | 8 项是 ffmpeg 9 已删除 `-filter_complex_script`；1 项 test_full_checklist_acceptance 仍查 R280 之前的深色令牌；本轮未做两机对照复验 |
| 3 项开发机环境失败 | 1 项缺 Obsidian 库；2 项 melt 7.4 与本机 7.39 的像素差异 |
| R276 | checks-only PASS，26 次设计比对 |
| R278 | checks-only PASS，R278/R282/R283 共 54 次合同比较 |
| R277 | 夹具、真实首屏、标注回放过；固定标注框因 Mac/Linux 中文字体度量不同失败，仍须留本机，未在本轮运行 |
| 浅色专项 | 总控此前 9 过；本轮也在开发机重新得到 9 过 |

开发机使用 Noto 替代 macOS 黑体、Liberation 替代 Arial 的同路径字体链接；特定 macOS 复制命令使用 cp 替身。字体字形/度量不等价；melt 版本不同；缺少 Obsidian 库。上述替代和未验证范围不因浅色专项通过而消失。

## 规则卡短表逐行交结果

| 规则 | 结果 |
| --- | --- |
| Git 写操作前断言本 worktree | sparse-checkout 前已断言当前根目录；本机自测内部临时 Git 写入前也断言调用位置。未做 add/commit/push |
| G16 必须过，不能把读不到当不相关 | 最终 G16 PASS；只补七个子目录，旧卡与测试均未改 |
| git add -f 只加必需验收物、路径脱敏、仓库安全检查 | 没有暂存或提交；新验收文本未持久化本机 /Users 路径。仓库安全检查尚未运行，因发现实现问题按任务单停止，不声称通过 |
| 只说实际通过范围，保留差异 | 只认三份夹具自测和远端浅色九项；全量红项、R277 本机例外、字体/cp替身均已列明 |
| 本机只跑三份自测，其余经 rbox | 本机重活 0→0；pytest 仅经 rbox 在 photo-dev 运行，无浏览器或渲染 |

## 后续未完成项

总控处理真实在线检查器缺失时放行的问题后，按实际新源码重新冻结 verified head、更新合同保护摘要和机器证据；机器通过后生成非阻塞 handoff（同编号 request-id、任务委托人、五分钟），重建索引和日志，再跑 G1/G12/G16 及仓库安全检查。仅明确列出合同必需文件暂存，提交后再验证实际范围。人工 H 两项继续由任务委托人签署。

本轮没有为了门禁改需求、旧卡、实现、测试或豁免，也没有完成提交。

## Git 状态

业务项目：HEAD 仍为 `40cf307`，未创建提交，暂存区为空。当前状态（REPORT 写入前）：

```text
 M acceptance/surfaces.yaml
?? acceptance/human/2026-W44/未-2026-10-27-R310-photo-devbox/
?? agents-results/2026-10-27/R310-photo-devbox/
?? docs/tasks/R310-photo-devbox/
```

`docs/tasks/R310-photo-devbox/` 开场即为未跟踪目录；本报告按任务要求不提交。只新增本任务验收准备物及 surfaces 映射，其余未碰。

Harness SSOT：本轮未编辑任何 Core 文件；以下十个生成文件开场已脏，收尾保持相同路径，未暂存或回退他人改动：

```text
 M tools/console/generated/console-data/cutover.json
 M tools/console/generated/console-data/harness-engineering.json
 M tools/console/generated/console-data/harness-engineering/acceptance.json
 M tools/console/generated/console-data/harness-engineering/bundles.json
 M tools/console/generated/console-data/harness-engineering/requests.json
 M tools/console/generated/console-data/harness-engineering/tasks.json
 M tools/console/generated/console-data/index.json
 M tools/console/generated/manifest.json
 M tools/console/generated/projects.json
 M tools/console/generated/version.json
```

已按任务单写报告并停止。


## 第二阶段：fb6f2fe 正式递交（2026-10-27）

记录时间：2026-10-27T09:36:13.989520+00:00。本节是当前结果；前文保留第一阶段停止现场。

已完成用户本轮指定目标：**G16 PASS、G12 PASS、G1 PASS**。非阻塞 handoff 已正式创建，人工 H-01/H-02 保持 PENDING，未签署；全批检查仍因 **G9 调度台快照未同步而 FAIL，退出 1**，不能称全门禁全绿或发布 READY。

验收物提交：`5235c57617c7e55e3e156cbda09a2305fb520026`（`5235c57`，chore(acceptance): 递交 R310 开发机交付验收卡）。只包含 `acceptance/**`、`agents-results/**` 下逐文件列出的30个文件，未提交本任务 docs 目录、交付检查缓存或无关日志，**未推送**。未改实现、测试、AGENTS.md、需求卡或其他卡。未操作开发机真实数据、重装环境或起常驻服务。

### 新源码身份与证据

- base：`c1465ffffb34697d3ad01a3fd3e9c33f55273307`。
- verified head/source_commit：`fb6f2fe7a656c78461bb4fd1967e88bbb2175401`，tree：`087eb3d6bb336632633ff55820d42adb60e55c45`。
- 当前批次 HEAD：`5235c57617c7e55e3e156cbda09a2305fb520026`；新增提交全部是验收物，最终门禁缓存确认 verified head 没有推进。
- 合同版本2、baseline、test_where新保护摘要和binding已更新。原40cf307合同与baseline保存在 `history/40cf307/`，旧两份运行保留原状态和源码；新handoff只引用下表两份新源码PASS，未改造或复用旧证据冒充新head。

| 运行 | 执行位置与结果 | 已提交证据 |
| --- | --- | --- |
| `bash scripts/devbox/test_push_rules.sh` | 本机，退出0，推送清单自测全过 | 新unit run的evidence/test_push_rules.log |
| `bash scripts/devbox/test_ai_guard.sh` | 本机，不加--remote，退出0，AI门禁自测全过 | 新unit run的evidence/test_ai_guard.log |
| `bash scripts/devbox/test_where.sh` | 本机，退出0；含缺检查器且无法直连的第四种拒绝夹具 | 新unit run的evidence/test_where.log |
| `.venv/bin/python -m pytest -q tests/test_r280_light.py` | 仅经rbox在photo-dev执行；**9 passed in 0.06s**，退出0；整次rbox调用6.8秒（含同步和身份读取） | 新integration run的evidence/pytest-r280.log与command.json |

新unit run：`acceptance/machine/unit/runs/20261027T092843Z-macos-phase2-cb3478`；新integration run：`acceptance/machine/integration-contract/runs/20261027T092843Z-photo-dev-phase2-830f59`。两份结果均为PASS，绑定合同版本2。机器运行时间和退出码保存在各自证据JSON。

三份本机自测前重活进程为 **0**，之后 **0**。未在本机跑pytest、浏览器、渲染或产品前端门禁。真实远端调用先输出「改用直连判断：开发机连得上」，才同步并执行；远端回读完整HEAD为fb6f2fe，四个受保护文件摘要均匹配当前合同。检查器存在的三个状态和缺检查器且无法直连的失败分支由临时夹具验证；未谎称真实开发机离线，也未修改生产工具做反向实验。

### 正式递交及其他检查

handoff位于 `acceptance/human/2026-W44/未-2026-10-27-R310-photo-devbox/handoff.json`：schema v2，`request_id` 与 `task_id` 均为 `2026-10-27-R310-photo-devbox`，`blocking=false`、`estimated_minutes=5`、`required_role=任务委托人`。H-01/H-02逐项与当前request.json的步骤、预期做了原文相等核对，无增删改。机器通过后立即创建handoff，随后重建索引和人工台账，排入non_blocking_entries。

| 检查 | 结果 |
| --- | --- |
| 当前合同校验 | OK |
| 本任务深层check | OK: agents-results/2026-10-27/R310-photo-devbox |
| check-project | OK |
| 候选召回 | 28项，最高0.16909453722715678，无L0、无达到0.35的候选；没有替代或改写旧卡 |
| 仓库安全 `python3 scripts/check_repository_safety.py --base origin/main` | Repository safety check passed.（在30个文件完整暂存后运行；TASK.md明确允许本机执行此轻量检查） |
| `git diff --cached --check` | 通过，无空白错误 |
| 提交范围与handoff摘要回读 | 30个文件全在允许前缀；无docs；新运行结果摘要完整且身份均为fb6f2fe |

首次逐文件git add因当前任务证据目录尚未加入稀疏定义而被拒绝；仅补入 `agents-results/2026-10-27/R310-photo-devbox` 后重新逐文件add，核对30个路径完整，再重跑仓库安全检查通过。没有用整目录add或关闭稀疏检出。七个旧合同子目录继续保持，G16没有通过忽略旧卡或修改测试来放行。

G9读取Harness里已登记Photo主检出的调度台快照，当前卡只在任务worktree中；标准投影输入尚不含本卡。未改登记指向、未向主检出复制卡、未手写ready状态或覆盖他人生成文件来凑绿。此项留给总控合入并同步调度台后复查。

### check-delivery 提交前原样结果

命令：`python3 ~/Desktop/Opensource_Tool/Harness_Engineering/tools/harnessctl.py acceptance check-delivery --project . --range origin/main..HEAD`。退出1。

```text
check-delivery  origin/main..HEAD  (4 commits, tree 087eb3d)
  G1 有卡  PASS  
  G2 基准一致  PASS  
  G3 机器先绿  PASS  
  G4 看得懂  PASS  
  G5 有入口  PASS  
  G6 去重已声明  PASS  
  G7 失效传播  PASS  
  G8 坏一条不连累  PASS  
  G9 页面可见  FAIL  2026-10-27-R310-photo-devbox 没有出现在 ready/ACTIVE 投影中 → 重新生成调度台并确认新卡 ready/ACTIVE → python3 tools/console/generate_console.py；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py check-project --project-root .
  G10 不自证  PASS  
  G11 有需求卡  PASS  
  G12 验收覆盖需求  PASS  
  G13 沿用已有卡  PASS  
  G14 已通过不可变  PASS  
  G15 自动替代完整  PASS  
  G16 不连累前面的卡  PASS  
  G17 真实链路没被替换  PASS  2026-10-27-R310-photo-devbox: 证据里没有脚本
结果：FAIL（本命令如实返回门禁状态；推送策略由调用方应用）
```

### check-delivery 提交后原样结果

同一命令，当前实际范围为5笔提交；退出1。缓存head等于当前5235c57，verified_head等于fb6f2fe；以下为该次原始输出：

```text
check-delivery  origin/main..HEAD  (5 commits, tree 28b0e25)
  G1 有卡  PASS  
  G2 基准一致  PASS  
  G3 机器先绿  PASS  
  G4 看得懂  PASS  
  G5 有入口  PASS  
  G6 去重已声明  PASS  
  G7 失效传播  PASS  
  G8 坏一条不连累  PASS  
  G9 页面可见  FAIL  2026-10-27-R310-photo-devbox 没有出现在 ready/ACTIVE 投影中 → 重新生成调度台并确认新卡 ready/ACTIVE → python3 tools/console/generate_console.py；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py check-project --project-root .
  G10 不自证  PASS  
  G11 有需求卡  PASS  
  G12 验收覆盖需求  PASS  
  G13 沿用已有卡  PASS  
  G14 已通过不可变  PASS  
  G15 自动替代完整  PASS  
  G16 不连累前面的卡  PASS  
  G17 真实链路没被替换  PASS  2026-10-27-R310-photo-devbox: 证据里没有脚本
结果：FAIL（本命令如实返回门禁状态；推送策略由调用方应用）
```

G1已PASS，三笔原提交及修复提交均无缺卡问题；本卡是非阻塞抽查，人工未签不造成G1失败。G2/G3等结果只覆盖这次handoff声明的机器范围。G17如实显示证据里没有可执行脚本，不能解读为对所有开发工具做了新静态审计。

### 范围限制与规则卡逐项结果

总控先前的全量 **1204通过、12失败、36跳过** 仍仅为历史记录，本轮未重跑。9项本机同样红（8项ffmpeg9删除旧参数，1项旧深色令牌检查）、3项开发机差异（Obsidian库缺失、melt像素两项）均未修复或归零。R276既有26次设计比对PASS、R278既有54次合同比较PASS未由本轮重验；R277仍因Mac/Linux字体度量不同留本机，本轮未运行。

开发机Noto代黑体、Liberation代Arial的字体链接，以及特定复制命令的cp替身、melt7.4对本机7.39、缺Obsidian库的差异照旧。新的浅色九项PASS不证明等价渲染、真实AI生成、全量全绿或人工验收通过。

| 规则卡行 | 第二阶段结果 |
| --- | --- |
| Git写操作前核对worktree | 暂存、补稀疏和提交前均断言任务根；提交前核对30个路径和HEAD；没有推送 |
| G16不得跳过旧保护 | 提交前后均PASS；不改旧合同、旧测试或旧卡状态 |
| 逐文件git add -f、路径脱敏、安全检查 | 精确30文件；没有本机绝对路径入新验收文本；完整暂存后安全检查PASS，docs与缓存未提交 |
| 只说实测范围并写替身/差异 | 两份新机器PASS仅限三份自测和远端浅色九项；历史全量失败、R277及字体/cp/melt差异保留 |
| 本机执行预算 | 三份获准自测前后0→0；pytest仅在开发机，未开浏览器或渲染 |

### 第二阶段 Git 收尾状态

业务项目：HEAD=`5235c57617c7e55e3e156cbda09a2305fb520026`，跟踪文件和暂存区均干净，仅下列未跟踪文件；其中两份是第一阶段现场文件，交付缓存仅本地使用，TASK/REPORT按要求不提交：

```text
?? acceptance/.delivery-check.json
?? agents-results/2026-10-27/R310-photo-devbox/candidate-review.json
?? agents-results/2026-10-27/R310-photo-devbox/check-delivery-stopped.log
?? docs/tasks/R310-photo-devbox/
```

Harness SSOT：本轮未修改Core或调度台来源、未提交Harness文件；仍见开场同样十个生成文件脏路径，未暂存、回退或覆盖它们：

```text
M tools/console/generated/console-data/cutover.json
 M tools/console/generated/console-data/harness-engineering.json
 M tools/console/generated/console-data/harness-engineering/acceptance.json
 M tools/console/generated/console-data/harness-engineering/bundles.json
 M tools/console/generated/console-data/harness-engineering/requests.json
 M tools/console/generated/console-data/harness-engineering/tasks.json
 M tools/console/generated/console-data/index.json
 M tools/console/generated/manifest.json
 M tools/console/generated/projects.json
 M tools/console/generated/version.json
```

本包是普通验收证据包，不是声明SSOT；无Obsidian快照或手机提醒。未推送，任务worktree保留供总控合入。第二阶段结果已写入本节，执行到此停止。
