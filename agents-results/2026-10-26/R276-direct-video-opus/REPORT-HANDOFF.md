# R276 交付准备汇报

日期：2026-10-26。交付材料已准备并本地提交，**整体交付检查未通过，不可报告 READY**；未推送，未代签人工通过。

验收物提交：`9637bd9cb1ae52efbf300197134216b512fc8234`（`chore(acceptance): prepare R276 cards and verified-head machine evidence`）。父提交仍为 `d095d10`。本报告与提交后检查结果再作一个仅含验收物的本地回执提交；其提交标识由本报告所在 Git 提交确定，不改写前述提交。

## 验收物与源码身份

- 卡片：「Studio 里一键直出：Opus 按口播稿写每一镜动画，本机渲染出成片 · 待验收（2026-10-26-R276-photo-direct-video-opus）」。状态 `PENDING`，Blocking 保持 Yes，未创建任何人工运行或反馈。
- 卡片、binding、handoff：`acceptance/human/2026-W44/未-2026-10-26-R276-photo-direct-video-opus/`。三项步骤和预期逐字沿用需求卡，未增删改 H 项。
- 合同：`agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md`。源需求与批准证据写入合同；当前测试摘要锁定，不追称此前已存在这份合同。
- claims、baseline、机器 run 和证据都在同一任务目录；`runs.json` 记录确切 run 路径。自动日志用管理器生成，H-01、H-02、H-03 均各有 claim_key、surfaces、open_route。
- H-01 和 H-02 的入口原样登记为 `http://127.0.0.1:8766/#view=piece&piece=project-fc6baa3294&ptab=direct`。只写入卡片，没有访问或操作 8766。
- 基底为 `2263a04272eca5dc6d80590a066025ecf9c12f2b`；verified head 为 `d095d101c445bb6a349208ce6c5af8be3afbf10c`，tree 为 `6673f1ff467d7a821a04359f882a54ddb0d8dfc7`。验收物提交后复算结果仍相同，见 `check-delivery-after-artifacts.json`。
- 为读取旧卡冻结依赖，除本任务目录外只补检出已跟踪的 `agents-results/2026-10-21/r223-delivery/`；其字节未改、未进入新提交。没有把旧卡证据挪到新位置。
- `acceptance/surfaces.yaml` 增加 `scripts/direct_video/** → photo.video-pipeline` 的现行路径映射，召回不再有 unmapped。

## 机器验证

| 命令或校验 | 结果 | 边界 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_*.py` | **134 passed，38.89 秒** | 配置任务单指定 Playwright 模块与真实浏览器；包含实际 HTML 渲染。模型调用测试使用假可执行文件，没有付费调用 |
| `node tests/test_r276_direct_frontend.mjs` | **PASS** | 包含 composedAt 正例和空值反例，不退回 updatedAt |
| `node scripts/direct_video/frontend_gate.mjs` | **PASS：26 次合同检查，31 张整页截图，公式与浏览器交互** | 独立 8767、临时状态、API 投影夹具；不冒充真实生成。首轮误用了 CommonJS 入口失败，换同安装的 ESM `index.mjs` 重跑通过；没有改脚本 |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_video.py::test_rewrite_only_one_shot_and_invalidate_output` | **1 passed，0.17 秒** | H-03 的当前源码后端不变性正证据 |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | **PASS** | 原测试前、已暂存验收物及提交后均通过；媒体不入仓库 |
| `check_acceptance_contract.py` / bind-human | **PASS** | 合同、清单、保护摘要及 binding 一致 |
| 管理器 `check-project` | **PASS** | 当前队列及生成日志有效，不代表总控调度台已发布 |
| 管理器 `check <任务根>` | **FAIL** | Core 要求 run 内实体截图，项目要求图片在仓库外；详见下文，未绕过 |
| `git diff --check` | **PASS** | 交付日志只移除行末空格，未改变门禁结果 |

当前源码上的机器后端 run 与夹具 E2E run 均为有明确范围的 PASS，并已用于 handoff。严格 `visual-fidelity` run 单独记为 FAIL；不把缺少的计算样式、对比度、交互轨迹或截图归档证明写成通过。没有重跑全仓；任务单已说明的全量 9 失败、6 错误及 Obsidian 时间戳问题仍引用 `docs/tasks/R276-direct-video-opus/REPORT-F2.md`，不归入本次 PASS。

截图在 `~/.photo-content-os/evidence/R276-direct-video-opus/handoff-frontend-final/`。31 张的实际视口为 1440×900、960×900，以及五种状态的 390×900；哈希和完整滚动覆盖均复核。四张联系表覆盖全部 31 图，另单独打开 done 桌面、unavailable 手机原始整页图，查看了相邻区域与底部；这个检查范围不冒称每张原图都逐张放大审阅。完成态夹具的旧时钟平移没有同步移动 composedAt，页头因此显示 0:00；该截图只证明布局，不证明出片耗时，正确数值由 D 的独立正反例验证。

## 成片、联系表及 H-03

真跑媒体全部留在 `~/.photo-content-os/evidence/R276-direct-video-opus/`，没有复制入仓库：

| 文件 | 用途 |
| --- | --- |
| `b1.mp4`、`b1-contact-sheet.png` | 已批准 B1 十镜带声成片及联系表 |
| `b2.mp4`、`b2-contact-sheet.png` | 已批准 B2 七镜无声成片及联系表 |
| `b2-before-rewrite.mp4`、`shot03-comparison.png` | 第三镜重写前成片及前后对照 |

`b-media-readback.json` 记录六个文件本次只读核验的大小与 SHA-256。B1 的十镜带声和 B2 的七镜无声，不能合称已经证明 H-02 要求的七镜带声同步；人工 H-02 预期保持原样等待用户实际核验。

H-03 只保护 `tests/test_r276_direct_video.py` 中 `test_rewrite_only_one_shot_and_invalidate_output`，并绑定 `docs/tasks/R276-direct-video-opus/REPORT-B.md` 与原始 `evidence/2026-10-26/R276-direct-video-opus/b-h03-proof.json`：真实修改“数字再大一点”后只有 03 改变，01、02、04、05、06、07 的代码、海报字节、writtenAt、posterRevision 不变，重新合成后仍不变。见 `h03-evidence-binding.json`。**未将前端详情 DOM 测试列入受保护测试，也未把它作为 H-03 的证明。**

## 旧卡关系与 G16 决定

`candidates.py --range origin/main..HEAD` 召回 R207、R210、R220、R223，逐张读取其标准和合同并声明 independent：旧卡分别验安装和剪辑交接、平台音乐导入边界、导航精选及已有播放、音乐标签节拍；本卡不承接这些责任。完整理由在 `relations-review.json` 和每项 claims 中。

只审当前 ACTIVE、有 handoff 且 PENDING 的旧卡；历史非 ISO 周 OCM-Z1 单列排除。它们锁定的测试与本批实际改动交集均为空，因此没有编造 supersede/rebaseline 决定，没有刷新旧保护摘要，也没有重新递交旧卡。`g16-readonly-audit.json` 保留逐卡清单；**提交后 G16 PASS、G17 PASS**。任务单提醒的旧卡 G16/G17 冲突在本批最终检查中没有复现。初轮稀疏检出缺 R223 合同的 G16 失败已通过只读检出原字节解决，不是挪证据或改 Core。

## 交付门禁

实际执行 `check_delivery.py --project-root <本 worktree> --range origin/main..HEAD --json --read-only`；在验收物提交 `9637bd9` 后返回 **exit 1 / FAIL，13 项 PASS、4 项 FAIL**。完整原始结果为 `check-delivery-after-artifacts.json`。

| 门禁 | 结果 | 原因与推送影响 |
| --- | --- | --- |
| G1 有卡 | **FAIL** | 新卡已递交，阻塞项尚无当前人工 PASS；不能报告就绪 |
| G2 基准一致 | PASS | 验收物追加后 verified head/tree 仍为冻结源码 |
| G3 机器先绿 | PASS | 所引用后端及夹具 E2E run 是同源码身份 PASS；不是严格视觉归档或人工结论 |
| G4 看得懂 | PASS | 中文步骤与预期，原样三项 |
| G5 有入口 | PASS | 三项均登记有效入口；未借此访问用户服务 |
| G6 去重已声明 | PASS | 候选逐卡关系与映射完整 |
| G7 失效传播 | PASS | 未改已通过卡的验收责任 |
| G8 逐条隔离 | PASS | Core 只读生成健康检查通过 |
| G9 页面可见 | **FAIL** | 总控 Harness 已生成快照没有这张卡的 ready/ACTIVE 条目；项目本地日志已有 PENDING。禁止改 Harness 仓库，故没有发布快照 |
| G10 不自证 | PASS | 没有人工反馈、签署或去掉“未-” |
| G11 有需求卡 | **FAIL** | `d095d10` 已有正确 Request，但缺 Verify 尾行；任务禁止改写该提交，本次追加正确尾行不能追补旧提交 |
| G12 覆盖需求 | **FAIL** | 同一旧提交缺 Verify；H 项本身保持完整 |
| G13 沿用已有卡 | PASS | 无完全相同的旧验收项重复开卡 |
| G14 已通过不可变 | PASS | 未修改已通过卡及人工事实 |
| G15 自动替代完整 | PASS | 没有虚构替代责任或改旧卡 |
| G16 不连累旧卡 | **PASS** | 空保护测试交集，没有硬拒绝 |
| G17 真实链路未替换 | **PASS** | 本任务证据根没有可执行脚本；仓库测试中的模型/接口夹具边界另行明示，不称真生成 |

手工检查不隐藏 FAIL。本项目未配置 enforce，Core 的默认 warn 对普通失败不产生 G16 那种硬拒绝；enforce 时上述失败均阻止推送。无论默认策略如何，本任务明确不推送，阻塞人工项未通过、G9 未发布和提交尾行未解决前均不称 READY。

调度台曾尝试使用临时登记文件作只读 preview，Core 以 `authority-path-escape` 拒绝该外部登记，exit 2，日志保留为 `console-worktree-preview.log`；没有为了通过而改 Core 登记表、生成目录或入口。

## 尚需总控处理

1. 用户按原卡完成 H-01～H-03，并由用户亲自提交结果；特别是七镜带声的同步观感。
2. 将验收物按总控既定路线接入登记项目，再发布总控调度台快照，使 G9 看得到真实新卡；本任务没有授权写 Harness 仓库。
3. 在保持 `90875ba`、`d095d10` 不变的前提下，由总控协调提交尾行门禁的正式处理路径；不能由本线程 amend、rebase 或伪造历史。再次运行 G11/G12 确认。
4. 协调 Core 截图归档与项目媒体外置规则。当前 `check <任务根>` 要求 `evidence/screenshots/` 中实体图且解析后仍在 run 内，不能用仓库外软链接或 JSON 假装图片。没有获准改变这两条规则，因此严格视觉 lane 与该任务检查保持 FAIL。
5. 若推送范围或产品源码变化，按新源码身份重跑受影响验证；不能沿用本批身份冒充新版本。

## 边界与 Git 状态

只新增/更新 `acceptance/**` 与本任务 `agents-results/**` 验收物。未改 `studio/`、`scripts/`、`tests/`、`schemas/`；未改两个原提交，R277 的基底可继续使用。8765、8766 未访问、未停启；临时 8767 已由检查脚本收尾。`.venv` 是开工前已有链接，未删除、重建或修改。未安装钩子，未推送。

Harness SSOT 仓库没有本线程编辑；既有其他线程修改原样保留，状态只读记录于 `frozen-source-proof.json`。没有声明 SSOT 开发包，不触发 Obsidian 审计快照。已清理本次创建的未跟踪 delivery 缓存；业务 worktree 最终只保留原有未跟踪 `.venv`，报告回执提交后停止。


## 第二次 handoff（c39b465）

日期：2026-10-26。本次验收物提交为 **`e38d09c0c29cc271c568b85cce312f1e2096a2af`**（`chore(acceptance): re-handoff R276 at c39b465`），仅包含验收物；本节另作只含本报告的本地回执提交。已有 `90875ba → d095d10 → 9637bd9 → b04e038 → c39b465` 五个提交原样保留，没有 amend、rebase、推送或改写。

本次 verified head 为 `c39b465f696856babc835ea6893196240d9198e9`，tree 为 `a4b1d6867fdc0af33a642ce22720b2b46b465ac8`，base 仍为 `2263a04272eca5dc6d80590a066025ecf9c12f2b`。新 baseline 与两个机器 PASS run 均绑定该身份，不沿用 d095d10 的机器结果冒充新跑。

### 卡片与受保护摘要

合同元数据更新为第 2 版，只更新源码绑定及本次委托依据；受保护测试表的字节、路径和五个 SHA-256 全部不变。开工时逐一重算五个后端 `.py` 文件，均与原锁定值相同，因此没有刷新摘要，也没有触发异常后自行继续修订。完整比对在 `handoff-2/protected-tests.json`。

H-01～H-03 的步骤与预期逐字不变；清单只更新内部合同版本元数据。管理器重新 bind-human、handoff --replace，并更新 ready_at、claims、baseline、runs 和生成日志。卡片仍为 **PENDING、Blocking Yes、保留“未-”前缀**，没有新增人工结果或反馈。H-03 仍只保护后端单镜不变性测试并引用 REPORT-B 真跑，不保护前端详情 DOM。

卡片与合同位置沿用第一节；新机器 run 路径见 `handoff-2/runs.json`，当前 handoff 只引用新的两个 PASS run。第一次结果留在 Git 历史和原 run 中，不再充当当前 handoff 的源码证明。

### 每条机器验证

| 验证 | 本次结果 | 证据 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_*.py` | **134 passed，21.68 秒** | `handoff-2/pytest-r276.log` |
| `node tests/test_r276_direct_frontend.mjs` | **PASS** | `handoff-2/frontend-node.log` |
| `node scripts/direct_video/frontend_gate.mjs` | **PASS：26 次设计合同比较、31 张整页截图、公式及浏览器交互** | `handoff-2/frontend-gate.log` |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_video.py::test_rewrite_only_one_shot_and_invalidate_output` | **1 passed，0.48 秒** | `handoff-2/h03-backend-invariance.log` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | **PASS**，执行及暂存验收物后均通过 | `handoff-2/repository-safety.log` |
| 合同、binding 校验 / check-project | **PASS** | `handoff-2/check-contract.log`、`check-project.log` |
| 受保护摘要与清单正文保持 | **5/5 不变**，三个人工项正文不变 | `handoff-2/protected-tests.json`、`checklist-preservation.json` |

后端渲染按任务单配置 `VIDEO_RENDER_PLAYWRIGHT_MODULE` 和 `VIDEO_RENDER_BROWSER`；浏览器门禁使用同一 Playwright 安装的 ESM `index.mjs`，`HARNESS_CORE` 指 Core。独立临时 Studio 只用 8767，检查后已关闭。没有调用真实付费模型，没有新生成作品或改运行中的作品。

本轮图片在 `~/.photo-content-os/evidence/R276-direct-video-opus/handoff-2-frontend/`，未入仓库。31 张实际视口和整页覆盖、哈希均复核；查看了四张联系表，并单独打开 ready 桌面 1440×900、writing 手机 390×900 的原始整页图（含底部），新“写好 · 用时”文字和相邻区域可读，没有横向溢出。此为明确范围的夹具布局检查，不冒称对全部原图逐张放大审阅或真实模型/音画同步验收。

### 召回与 G16

重新执行 `candidates.py --range origin/main..HEAD`，除同编号本卡外仍只有 R207、R210、R220、R223 四张相关旧卡；四张均沿用 independent 的具体理由。没有 unmapped。对当前 ACTIVE、有 handoff 且 PENDING 的旧卡只读核对后，受保护测试与实际改动交集均为空。没有重新基线、替代或改写任何旧卡，**G16 PASS**；详见 `handoff-2/candidates.json`、`g16-readonly-audit.json`。

### 交付检查逐项结果

执行 `check_delivery.py --project-root <本 worktree> --range origin/main..HEAD --json --read-only`，返回 **exit 1、FAIL；13 项通过，只有任务单预期的 4 项失败**。门禁复算 verified head/tree 与上面一致；原始 JSON 在 `handoff-2/check-delivery.json`，本次摘要在 `handoff-2/delivery-summary.json`。

| 门禁 | 结果 | 原因或边界 |
| --- | --- | --- |
| G1 有卡 | **FAIL** | 阻塞卡还没有用户亲自签署当前版本 |
| G2 基准一致 | PASS | 新基准及源码身份一致 |
| G3 机器先绿 | PASS | 引用的是 c39b465 的新 PASS run |
| G4 看得懂 | PASS | 原样中文三项 |
| G5 有入口 | PASS | 原有逐项入口保留，没有访问 8766 |
| G6 去重已声明 | PASS | 四张旧卡关系与范围声明有效 |
| G7 失效传播 | PASS | 未篡改旧的通过结论 |
| G8 逐条隔离 | PASS | Core 只读生成健康检查通过 |
| G9 页面可见 | **FAIL** | 总控调度台快照尚未发布这张卡的 ready/ACTIVE 条目 |
| G10 不自证 | PASS | 无人工结果、反馈或去掉“未-” |
| G11 有需求卡 | **FAIL** | d095d10 有 Request、缺 Verify；按总控决定保留历史，不改写 |
| G12 覆盖需求 | **FAIL** | 同一旧提交缺 Verify；本卡 H 项本身仍完整 |
| G13 沿用已有卡 | PASS | 没有新开相同验收责任的卡 |
| G14 已通过不可变 | PASS | 没有修改已通过卡 |
| G15 自动替代完整 | PASS | 未虚构替代或遗漏退役 |
| G16 不连累旧卡 | **PASS** | 四张旧卡受保护测试交集为空 |
| G17 真实链路未替换 | **PASS** | 证据根没有执行脚本；仓库测试的夹具边界明确披露 |

没有其他 G1～G17 门禁失败。另行重跑管理器 `check <任务根>` 仍因原有截图外置与 run 内实体截图要求冲突而 FAIL，见 `handoff-2/check-task.log`；这不是新产品失败，也未被伪装成已修复。全仓既有失败没有在本段重跑或改写。

### 推送前仍缺什么与收尾

当前不能报告 READY。仍需用户验收 H-01～H-03、由总控发布调度台快照，并由总控处理保留历史前提下 d095d10 的 Verify 门禁；严格截图归档冲突也仍需协调。普通失败在默认 warn 策略下不属于 G16 的硬拒绝，enforce 时阻止推送；本任务无条件不推送。

只追加验收物提交，随后回执提交只含本报告。本段没有修改 `studio/`、`scripts/`、`tests/` 或其他产品路径；文件 SHA-256 与开工快照一致。`.venv` 的链接目标、inode、mtime 均未变化。8765、8766 未访问、未停启；Harness 仓库无本线程修改，其已有其他线程状态保留。核验记录在 `handoff-2/boundary-proof.json`、`before.json`。未安装钩子，未代签人工通过。回执提交后停止。
