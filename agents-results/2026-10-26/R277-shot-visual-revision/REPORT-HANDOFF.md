# R277 第二段交付准备与 R276 rebaseline 汇报

2026-10-26。本次交付准备已完成：R276 原合同重定基准并重新 handoff，随后 R277 handoff；**G16 PASS，交付检查仅 G1、G9 失败，尚不能报告 READY。未推送，未代签人工通过。**

验收物提交：`2ff655f6f57ab038a913af8cf97c92d5cea43ed2`，标题 `chore(acceptance): hand off R277 with R276 rebaseline`。本汇报、提交后检查和最终边界记录单独作回执提交；回执身份以包含本文件的 Git 提交为准。没有 amend、rebase 或改写本轮产品提交。用户保留的 r277-aborted-handoff 分支未检出、未用作材料来源、未删除。

## 源码身份和材料位置

- Frozen base：`4c1fc220b32a1cd67a30adb323affca8724b47e1`。
- Verified head：`277cd1c6ca730f77bd653a31a8b7ca22ea90277b`。
- Verified tree：`363864e01b731310a35f698fda7e8b21aa488f5f`。
- 提交后检查的范围 head：`2ff655f6f57ab038a913af8cf97c92d5cea43ed2`；该范围 head 与 verified head 分别记录，不混用。
- 需求「脚本直出里改一镜的画面：在画面上点着改、看两版对比、攒好样例，让画面规则越用越准 · 已确认（2026-10-26-R277-photo-shot-visual-revision）」原文与确认记录未改。递交后同编号验收卡为待验收，H-01 至 H-03 原字不变。
- R277 合同：`agents-results/2026-10-26/R277-shot-visual-revision/acceptance-contract.md`；binding、checklist、handoff：`acceptance/human/2026-W44/未-2026-10-26-R277-photo-shot-visual-revision/`。
- R276 卡「Studio 里一键直出：Opus 按口播稿写每一镜动画，本机渲染出成片 · 待验收（2026-10-26-R276-photo-direct-video-opus）」合同仍在 `agents-results/2026-10-26/R276-direct-video-opus/acceptance-contract.md`；人工目录 `acceptance/human/2026-W44/未-2026-10-26-R276-photo-direct-video-opus/`。
- 两卡均为 PENDING、Blocking Yes、保留未-，没有新增人工 run 或反馈。R276 清单 SHA-256 与开工完全相同，原 8766 卡级及逐项入口不变；本线程未访问该服务。
- R277 每项有稳定 claim_key 和按 surfaces.yaml 的范围；三项入口均为 note 位置说明，没有把 R276 服务当成 R277 查看入口。推送后由总控另开运行本轮代码的 Studio。
- 两个 runs.json 分别指向本轮新建的四个机器 run。R276 ready_at 为 `2026-10-26T03:41:09.533714Z`；R277 ready_at 为 `2026-10-26T03:41:10.522621Z`。全部 source_identity/source_commit 等于本轮 verified head。

## 本轮机器验证

所有机器命令在 277cd1c 上从头执行，未沿用上一段日志。固定 .venv、渲染 Playwright index.js、指定 Chromium 和 VIDEO_RENDER_TEST_BROWSER 按任务单配置；Node 门禁使用同安装 index.mjs 和 HARNESS_CORE。专项 pytest 独占运行，之后单独跑 R276 专项与单镜测试，再串行跑两套浏览器门禁；全仓 pytest 在两套门禁结束后才开始。

| 命令／验证 | 结果 | 日志 |
| --- | --- | --- |
| pytest tests/test_r276_*.py tests/test_r277_*.py，另加 OpenAPI 同步、p2 frontend、r220 公式、checklist 静态 | **204 passed，81.47 秒**，无超时 | pytest-targeted.log |
| pytest tests/test_r276_*.py，原合同完整范围再跑 | **134 passed，20.57 秒** | ../R276-direct-video-opus/handoff-3/pytest-r276.log |
| H-03 test_rewrite_only_one_shot_and_invalidate_output | **1 passed，0.10 秒** | ../R276-direct-video-opus/handoff-3/h03-backend-invariance.log |
| node tests/test_r277_frontend.mjs | PASS，17 夹具状态 | frontend-node.log |
| node tests/test_r276_direct_frontend.mjs | PASS | ../R276-direct-video-opus/handoff-3/frontend-node.log |
| revision_frontend_gate.mjs，8768 | **PASS，42/42 合同、72 截图、详情／问题记录／轮询／标记避让交互** | frontend-gate.log |
| frontend_gate.mjs，8767 | **PASS，26/26 合同、31 整页截图、公式与交互** | ../R276-direct-video-opus/handoff-3/frontend-gate.log |
| check_repository_safety.py --base origin/main | **PASS**，执行、暂存验收物后及提交后均通过 | repository-safety.log、repository-safety-staged.log、repository-safety-after-artifacts.log |
| bash scripts/check_runtime_contract.sh | PASS，运行时路径／编译／包／编码合同 | runtime-contract.log |
| validate_music_analysis_registry.py | PASS | required-checks/registry.log |
| check_obsidian_doc_sync.py，显式 OBSIDIAN_ROOT | FAIL，三个既有文档时间戳同步项 | required-checks/obsidian.log |
| check_outline_contract.py . | FAIL，同一文档同步前置项 | required-checks/outline.log |
| 全仓 pytest -q tests | **1039 passed、9 failed、6 errors、25 skipped；2003 subtests passed；195.65 秒** | required-checks/full-pytest.log |
| validate_content_os_task.py --help、validate_jianying_draft.py --help | PASS | required-checks/task-help.log、draft-help.log |
| 合同、bind-human、handoff、check-project | PASS | check-contract.log、bind-human.log、handoff-final.log、check-project-final.log；R276 同类回执在 handoff-3 |
| evidence-retention | PASS，0 violations | evidence-retention.log |
| git diff --cached --check | PASS，最终暂存仅验收物 | 本轮提交回执 |
| task_worktree.py check | FAIL：worktree 尚未合并且存在本轮回执文件；保留分支未合并 | task-worktree-check.log；本轮明确不推送、不删除保留分支，不擅自 finish |

全仓失败集中在 FFmpeg 字幕／视频流水线与 Obsidian 同步，符合任务单预告的既有类别；这些源码由开工／收尾哈希证明未改。本轮没有把全仓失败算入专项 PASS，也没有改测试、放宽超时、跳过测试或扩安全基线。

完整原始全仓日志字节已保存在本机 Photo Content OS 证据文件夹的 `R277-shot-visual-revision/handoff-validation-277/full-pytest.raw.log`；仓库日志仅去掉行尾空白以满足 diff 检查，原始／仓库 SHA-256 和转换声明在 required-checks/log-normalization.json。新合同及 run 末尾多余空行也仅作格式整理，经管理器重新绑定、重新 handoff，未改变验收语义或执行结果。

## 截图与真跑边界

本轮 R277 图片在本机 Photo Content OS 证据文件夹 `R277-shot-visual-revision/handoff/`；R276 在 `R276-direct-video-opus/handoff-3-277-frontend/`，没有图片、音视频或原始媒体入 Git。103 张图的文件存在、SHA-256 与本轮 capture time 均已核验。R277 的72张含完整页与明确标注的详情视窗，未把视窗图冒称整页。

本人本轮打开了四张完整图至底部：R277 compare 的 1440×900 与390×900；R276 ready 的1440×900与 writing 的390×900。检查相邻镜卡、详情、两版、逐条核对、按钮、折叠内容和页面底部，抽样未见新增溢出或层级问题。实际 viewport、route、capture time、scroll coverage、输出尺寸、哈希与逐图结论在 screenshot-manifest-external.json、R276 handoff-3 的同名文件及 visual-sample-review.json。此为四图抽样，非103图逐张审阅、全站或生产验收；两套服务均为隔离状态／API投影夹具，未调用真实付费模型或修改真实作品。

合同保留任务单要求的真实依据：REPORT-C.md 第4轮及相关真跑链路，任务 dv_0e184e961bd14ac084c67411。H-01 为3橙点、160秒重写、3条均做到，其余6镜不变；H-02 显示「按字数估 20.8 秒 · 用第 1 版 · 共 2 版」、01镜「♥ 已存为样例」；H-03 为05镜三次缩小变灰后出草稿、未采用时规则版本0。原卡的「约 25%」「约 50%」柱子和实跑「25%」「估计 50%」文字块差异、旧任务需先点「让 Opus 看一遍」才有橙点均在合同说明，卡原文不改。REPORT-C 中390宽单位「天」的最小相交例外也保留，不称零遮挡。这些历史真实依据没有冒充本轮重新调用模型的结果。

额外执行管理器深层 check <task-root> 仍 FAIL：要求 machine/e2e run 内有效 reviewed screenshot-manifest 及实体图，项目则要求媒体外置，既有 R276 历史 run 同样缺该归档。精确错误见 check-task-r277.log、check-task-r276.log。没有用外部软链接、空清单或伪造实体图绕过；本轮限定机器 PASS 和交付 G1～G17 结果不代表 strict visual-fidelity 深层归档已通过。

## R276 保护摘要和 G16

| 文件 | 原 SHA-256 | 本轮 SHA-256 | 结论 |
| --- | --- | --- | --- |
| tests/test_r276_direct_video.py | e14bb66d4425c469a6fe820278e508e411a10f3502cfccf9bfeca1ed44bca57e | 95dd1530a9573600e502c4fae680befb6dbcbc96c3c3c29bf2a21568ac74011a | 仅此文件变化 |
| tests/test_r276_direct_api.py | 94b03c8a331ed3342e395800d34e6fac579c5672898af660eeca16db2f37154a | 94b03c8a331ed3342e395800d34e6fac579c5672898af660eeca16db2f37154a | 不变 |
| tests/test_r276_direct_media.py | d74658695d78ebc24f9869c88adb938c510517129d4ba655322115bad5eaec9e | d74658695d78ebc24f9869c88adb938c510517129d4ba655322115bad5eaec9e | 不变 |
| tests/test_r276_direct_c.py | 88fdd5e2a0f05e2459d527ce23984fe1fc6366f06de3aa48fcc095cbcd1b1d90 | 88fdd5e2a0f05e2459d527ce23984fe1fc6366f06de3aa48fcc095cbcd1b1d90 | 不变 |
| tests/test_r276_direct_d.py | fe7b1505535e7636404ba68d505358e7797d055e5d8ba2c4866afb4e4f39bed7 | fe7b1505535e7636404ba68d505358e7797d055e5d8ba2c4866afb4e4f39bed7 | 不变 |

唯一代码变化是 test_busy_job_and_projection 的严格相等字段集合增加 currentVersion、versions、boxes、look、sample 五个字段；没有弱化为子集断言。其余四个受保护文件摘要不变。

顺序完整落盘：管理器 rebaseline 准备新旧哈希 → 在本轮 head 复跑 R276 原合同全部机器命令 → 用同 head 新 PASS handoff --replace → R277 handoff。R276 protected-test-rebaseline.json 及 handoff.protected_test_rebaselines 记录 completed；R277 claims 的 H-01 有唯一 protected_test_overlap，target 为R276、decision=rebaseline、reason 包含五个字段、原三项语义不变及 H-03 证据边界。**最终 G16 PASS**。

H-03 始终由后端单镜不变性测试及 R276 REPORT-B 真跑证明；原始 b-h03-proof.json 留在原位置且本轮复算哈希。新的当前源码绑定在 R276 handoff-3/h03-evidence-binding.json，不把前端详情 DOM 测试当受保护测试。非保护重叠的两份前端脚本改到 R277 元素、按钮「重写这一镜」、合同比对跳过 DV-DETAIL，及13状态 approved-extras 增加「画面问题记录」均写进 R277 G16 reason。R276 卡 H-03 的旧按钮名原字不改，由其总控告知对应关系，rebaseline reason 同样记录。

旧卡召回来自本轮 candidates.py --range 4c1fc22..HEAD。逐张读取 R207、R210、R220、R223、R276 的原话、理解、标准、清单与合同，分别声明 independent：工具安装与候选、音乐导入与会员边界、导航精选与既有预览、标签节拍、生成配音合成，均不被本卡单镜详情／版本／样例／问题记录承接。最高召回约0.562，无高分覆盖例外，unmapped为空。首轮 G6 提示同批重新 handoff 的 R276 也须声明与 R277 的关系，已补反向 independent 并经管理器重新递交；旧 H 文本、入口、保护范围不变，没有改 Core 或取消旧卡责任。

## 提交后交付门禁

命令：check_delivery.py --project-root <本worktree> --range 4c1fc22..HEAD --json --read-only。验收物提交后返回 **exit 1 / FAIL，15 PASS、仅2 FAIL**；完整原始结果见 check-delivery-after-artifacts.json。最初的 G6 缺口在 precommit-final 和本次提交后检查都已通过，未隐藏初次日志。

| 门禁 | 结果 | 原因与推送影响 |
| --- | --- | --- |
| G1 有卡 | **FAIL** | 两张 blocking 卡还没有用户对当前交接的人工 PASS；人工责任未完成，不能称 READY。默认 warn 为普通失败，enforce 时拒绝推送。 |
| G2 基准一致 | PASS | base、verified head/tree、source_commit 和卡片摘要一致。 |
| G3 机器先绿 | PASS | 四个引用的机器 run 都是本轮277cd1c的限定范围 PASS，文件摘要匹配。 |
| G4 看得懂 | PASS | 三项原样中文步骤与预期有效。 |
| G5 有入口 | PASS | R277 三项 note 入口有效；R276 原8766入口保留。 |
| G6 去重已声明 | PASS | 五张候选关系完整，同批 R276/R277 双向独立声明有效。 |
| G7 失效传播 | PASS | 未改动已通过卡的结论或验收责任。 |
| G8 坏一条不连累 | PASS | 只读生成健康与修复路径检查通过。 |
| G9 页面可见 | **FAIL** | 总控调度台快照尚无两卡的新 ready/ACTIVE 交接；按指令未重建。默认 warn 为普通失败，enforce 时拒绝推送。 |
| G10 不自证 | PASS | 没有人工反馈、签署或去掉未-。 |
| G11 有需求卡 | PASS | 本轮产品提交和验收物提交 Request/Verify 尾行有效。 |
| G12 验收覆盖需求 | PASS | Verify 与同编号需求和三项验收覆盖一致。 |
| G13 沿用已有卡 | PASS | 没有另开完全相同的验收责任。 |
| G14 已通过不可变 | PASS | 未修改已通过卡或人工历史。 |
| G15 自动替代完整 | PASS | 没有虚构替代；重新递交关系完整。 |
| G16 不连累前面的卡 | PASS | R276 已完成同批同源码 rebaseline、新 PASS 与重新交接；硬门禁通过。 |
| G17 真实链路没被替换 | PASS | 当前任务证据根没有执行脚本；未隐藏任何证据脚本替换，仓库夹具与历史重放边界明确披露。 |

除 G1/G9 外没有其他交付门禁失败。手工检查保留真实非零退出，不用 policy 隐藏失败；本任务无条件不推送。

## 推送前仍缺什么

1. 用户按两张卡原三项完成实际验收并亲自提交结果；R277 入口要由总控在推送后另开对应版本的 Studio，R276 七镜配音同步也仍由人工判断。
2. 总控在合适的共享工作区状态发布调度台快照，使两卡当前 ready/ACTIVE 可见，重新确认 G9；本线程没有改 Harness 仓库或重建调度台。
3. 协调既有严格截图归档与媒体外置冲突、全仓 FFmpeg 环境及文档同步问题。它们已单列失败，不被两项交付门禁摘要掩盖。
4. 若后续源码或冻结范围变化，按新身份重跑受影响验证，不把本轮277cd1c证据冒充下一版。

## 边界和 Git 状态

验收物提交只包含 acceptance/** 与 agents-results/**，回执提交也只含验收物。本轮未改 studio/、scripts/、tests/、schemas/、docs/ 和需求原文；开工与收尾哈希全一致。.venv 链接、inode 和 mtime 不变。8765/8766 未访问或停启；临时8767/8768由门禁收尾。历史R210/R220/R223证据保持原位，未安装钩子、未推送、未改写277cd1c，未使用或删除保留分支。任务单副本没有复制进 worktree。

业务项目：两次本地验收物提交，回执完成后仅保留原有未跟踪 .venv。保留 worktree，按用户明确边界不推送、不执行 finish；task_worktree.py 的未合并提示如实保留。

Harness SSOT：有开工已存在的其他会话修改，本线程未写入；前后 git status 相同，详细状态保存在 before.json 和 boundary-proof-final.json。本任务是普通合同和证据包，没有创建或更新 ssot-archive.json 声明的 SSOT，不触发 Obsidian SSOT 快照。完成回执提交后停止。
