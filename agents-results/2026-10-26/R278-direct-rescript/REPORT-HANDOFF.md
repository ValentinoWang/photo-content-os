# R278 第二次交付准备汇报

2026-10-27（台北）。第二次交付准备完成：在 **fc072d9** 上从头验证，R276、R277 已完成受保护测试 rebaseline 并重新 handoff，R278 已递交。三卡均 **PENDING**，没有人工 PASS。提交后交付检查 **15 PASS，仅 G1/G9 FAIL，exit 1**；尚不能报告 READY。未推送。

验收物提交：`a5d29a3a5d892d2ea89436513b3287dcf93d925a`，124个文件，仅 acceptance/** 与 agents-results/**。本汇报单独做仅含本文件的回执提交；回执身份以包含本文件的 Git 提交为准。未 amend、rebase 或改写 fc072d9。

## 本次身份与材料

- Frozen base：`107b56eb0ab66881d706e8bdecae30f945619da2`。
- Verified head：`fc072d9694a6c807f2eafd4a4104c8e803d89b2a`；verified tree：`2ef184b559dd9d8a520fdc5e320114e379f66e6b`。
- 提交后检查 range head：`a5d29a3a5d892d2ea89436513b3287dcf93d925a`；验收物提交不推进 verified head。
- 上一轮4fd1243及其db54a3b、ffc8c00结果按总控指令作废，本轮未引用它们的机器结果；旧提交的备份和撤销由总控完成，本线程没有操作历史。
- 用户确认的两处界面更新已包含在fc072d9：当前画面旁不显示「这一版」；空画面说明显示「写这一镜画什么（可不填）」。本线程没有改代码、设计稿、测试或文档来重复实现。
- R278合同：`agents-results/2026-10-26/R278-direct-rescript/acceptance-contract.md`，版本1、APPROVED、LOCKED。binding、checklist、handoff在 `acceptance/human/2026-W44/未-2026-10-26-R278-photo-direct-rescript/`。baseline.json、claims.json、runs.json和上下文声明在本汇报同目录。
- R276、R277合同仍在各自的 `agents-results/2026-10-26/R276-direct-video-opus/`、`R277-shot-visual-revision/`；本轮baseline和claims输入位于各自handoff-r278子目录，机器run位于各自acceptance树。人工workspace仍是acceptance/human/2026-W44/下对应的未-目录。
- 需求「脚本直出先定视频风格，生成过以后能回到分镜脚本改了重新生成 · 待确认（2026-10-26-R278-photo-direct-rescript）」的H-01至H-03原字保留；confirmation_required=false，本次交付授权不等于代替用户确认需求或签署人工验收。

## 逐项入口与人工边界

| 项 | claim_key | open_route |
| --- | --- | --- |
| H-01 | studio.direct-rescript | http://127.0.0.1:8769/#view=piece&piece=project-fc6baa3294&ptab=direct |
| H-02 | studio.direct-style-base | http://127.0.0.1:8769/#view=piece&piece=project-fc6baa3294&ptab=direct |
| H-03 | studio.direct-style-draft | http://127.0.0.1:8769/#view=piece&piece=project-6546d6621b&ptab=direct |

三项surfaces均为：`acceptance.artifacts`、`acceptance.evidence`、`photo.documentation`、`photo.tests-scripts`、`photo.video-pipeline`、`studio.backend`、`studio.frontend`。每项恰好一条claim；清单每项仅中文验收步骤和预期表现，入口单独存claims。

H-01/H-02进入作品「断更一年，我拆了四句话」；H-03进入「断更一年，我的担心准吗」。两旧卡原三项和入口保留，清单摘要与准备前相同，所需角色仍是产品负责人、Blocking Yes，未去掉未-、未写人工run或反馈。

**H-03时长说明：** 首次实测215.621秒（约3分36秒），改一次168.813秒（约2分49秒）。用户2026-10-27看过这两个时长后原话：**「这个没事 大概差不多就行」**。合同和本报告如实记录该解释，卡上“三分钟内”文字不改；没有把该句话当成人工PASS，也没有声称215.621秒小于三分钟。

真实样张两版关键帧和片段仍在仓库外 `~/.photo-content-os/evidence/R278-direct-rescript/live-5z2bi1gp/inspected-artifacts/`，initial-/revised-区分两版；原非阻塞0%数字提醒仍保留。它们是既有服务层真跑证据，本轮未重新调用付费模型，不能冒称新的真实HTTP生成或七镜风格语义验收。

## 本轮机器验证

先准备两张旧卡rebaseline，再创建六个新run、执行本轮命令。使用固定.venv、指定Playwright与headless-shell；R278合同指向worktree内design，样例媒体显式从仓库外读取；DIRECT_GATE_PORT=8768，R277_SOURCE_STATE=~/.photo-content-os/studio-r278，只读后APFS克隆到临时状态。浏览器一次一个、无头，全部门禁串行；用完关闭自己的浏览器及8768服务。主验证与全量测试都有低于3 GiB停止检查，未触发停止条件。

| 检查 | 结果 | 本包证据 |
| --- | --- | --- |
| pytest tests/test_r278_*.py tests/test_r276_*.py tests/test_r277_*.py | **263 passed，100.42秒**，无失败、跳过；包含两旧合同完整Python范围及单镜不变性 | pytest-targeted.log、machine-results.json |
| 三份R278/R276/R277 Node专项 | PASS；R277保留17状态 | r278-node.log、r276-node.log、r277-node.log |
| rescript_frontend_gate.mjs --checks-only | PASS；40次逐块合同与挂载交互，含新占位、无来源标签、旧视频回调、样张计时及原编辑运算 | r278-frontend.log、r278-contracts-external.json |
| frontend_gate.mjs --checks-only | PASS；26次合同、公式与原交互，含旧视频重新合成回调回归 | r276-frontend.log、r276-contracts-external.json |
| revision_frontend_gate.mjs --checks-only | PASS；42/42合同、真实旧任务、标记几何、详情、版本、日志、轮询及390实际宽度检查 | r277-frontend.log、r277-contracts-external.json |
| check_repository_safety.py --base origin/main | **PASS**；本轮及验收物提交后均通过 | repository-safety.log；提交后外置handoff-2-fc072d9-final |
| check_runtime_contract.sh、音乐注册表 | PASS | required-checks/runtime.log、registry.log |
| check_obsidian_doc_sync.py，显式OBSIDIAN_ROOT | FAIL；三个既有时间戳同步项，按指令不修 | required-checks/obsidian.log |
| check_outline_contract.py . | FAIL；既有文档同步前置项，按指令不修 | required-checks/outline.log |
| 全量 pytest -q tests | **1106 passed、9 failed、6 errors、25 skipped；2003 subtests passed；251.64秒** | required-checks/full-pytest.log |
| validate_content_os_task.py --help、validate_jianying_draft.py --help | PASS | required-checks/task-help.log、draft-help.log |
| evidence-retention、合同检查、bind-human、index、log、check-project | PASS | required-checks/evidence-retention.log、artifact-check-results.json及对应日志 |
| 两旧卡handoff --replace、R278 handoff | PASS，三卡均PENDING | handoff-*.log、handoff-result-summary.json |
| 深层check三个任务根 | FAIL；新旧E2E run内缺reviewed screenshot-manifest及实体图；媒体外置与该归档要求的既有差异未修 | deep-check-*.log |
| 暂存diff --check、提交范围检查 | PASS；仅验收物，没有图片、视频、音频入Git | 验收物提交及boundary-precommit.json |

全量失败仍为已知字幕/字形、FFmpeg、视频流水线及文档同步类别，精确失败名与六项错误保留在日志。没有改这些实现、测试、时间戳或判据，也没把全量失败并入专项PASS。原日志字节保存在仓库外handoff-2-fc072d9-raw，本包只剥行尾空白；log-normalization.json记录原始/规范化SHA-256。

六个本轮机器run都以fc072d9为source identity、在准备审计后开始，并在各自限定范围内PASS；两旧卡各引用integration-contract与e2e新run，不引用上一轮旧绿。具体ID、result摘要与完成后的handoff绑定见runs.json、handoff-result-summary.json及各卡handoff.machine_evidence。

三份checks-only没有新整页截图；门禁生成的测试缩略图在仓库外，属于夹具。R277只读状态源前后8670个文件哈希一致；R278历史job原件、复制件及结束时摘要一致。前端夹具、历史投影重放与真实后端写入/模型生成的范围始终分开。

## 复用截图与视觉范围

按本次明确授权复用 `~/.photo-content-os/evidence/R278-direct-rescript/frontend/gallery.html` 中41张已经逐张审阅的图。41个文件SHA-256、41个图库目标均核验匹配；完整索引、视口、尺寸、捕获时间、滚动覆盖和此前review note在reused-screenshot-evidence.json。F1第11节最新重拍8张，其余33张是此前保留证据；不把整套数量说成本轮重拍。

本人本轮另打开rescript-1440和rescript-960两张完整图至底部：检查七镜、画面新占位、无来源标签、台词、相邻风格区、选项及底部生成条。1440保持六列，960按设计在表内横滚、预览与选项纵排；抽样未见新增整页横溢或意外裁切。它们的实际视口是1440×900、960×900，本轮抽样不代表新手机截图、全站或全部41图重新目检。

独立深层check仍要求run内实体截图归档；本轮依用户要求复用仓库外媒体，未复制媒体、建立外链伪装实体图、制造空清单或削弱判据。该独立检查FAIL已单列，交付G1–G17的15PASS不代表严格视觉归档已通过。

## G16与保护摘要

R278 H-01的protected_test_overlap对R276、R277各声明一次decision=rebaseline，保留原人工责任，不supersede。实际顺序：准备审计 → 新源码完整专项及旧前端门禁PASS → R276/R277同头重新handoff → R278递交。两个旧handoff.protected_test_rebaselines均追加本轮phase=completed，ready_at刷新；准备文件保留为审计，不手改人工事实。

| 卡 | 新ready_at（UTC） | 人工状态 |
| --- | --- | --- |
| 2026-10-26-R276-photo-direct-video-opus | 2026-10-26T17:16:05.333875Z | PENDING |
| 2026-10-26-R277-photo-shot-visual-revision | 2026-10-26T17:16:06.556019Z | PENDING |
| 2026-10-26-R278-photo-direct-rescript | 2026-10-26T17:16:07.932204Z | PENDING |

| 卡 | 变化的受保护文件 | 原SHA-256 | fc072d9 SHA-256 |
| --- | --- | --- | --- |
| R276 | tests/test_r276_direct_video.py | 95dd1530a9573600e502c4fae680befb6dbcbc96c3c3c29bf2a21568ac74011a | c932e418ed2362b44e50514c689b9e6a6b7b9b1569fea31e06f8b385764a3e69 |
| R276 | tests/test_r276_direct_api.py | 94b03c8a331ed3342e395800d34e6fac579c5672898af660eeca16db2f37154a | 875dbb95f91f9d464055e21de8b17d45f504a90a133c99eb87c8374b0ecb6b72 |
| R276 | tests/test_r276_direct_c.py | 88fdd5e2a0f05e2459d527ce23984fe1fc6366f06de3aa48fcc095cbcd1b1d90 | 85f8665a1a972174bcaab842caba43109dd82d5cb1c36c66fd300f21f0d4cb9c |
| R277 | tests/test_r277_revisions.py | b5232e7d28a85a5dec1383d349bd3dda261a34521ee9e76497792cf67fea777c | 13b8699cdd6b8f5d55cc95b6945fa6f5a431d86f38dbc82b9329159fd8adc7ca |

逐处核对：R276 direct_video的合法假设计补motionSummary/bannedShort，ready、假网关及两个失败分支补必需style；严格投影集合新增visual/subtitle/camera/audio/fromDraft。direct_api公共创建夹具、direct_c写镜时钟用例补style。R277 revisions的ready_image、project2/project3创建补style，旧投影严格字段集合增加同五字段。没有删除、减少、跳过或放宽旧失败次数、版本、样例、不变性和隐私断言。来源为REPORT-A第4节及本轮Git文件摘要。

不变的保护文件：R276 direct_media、direct_d；R277 api、boxes、frontend.py。全部新旧摘要，包括这五份未变文件，见protected-test-audit.json。

| 相关门禁/Node文件 | base SHA-256 | fc072d9 SHA-256 | 变化 |
| --- | --- | --- | --- |
| scripts/direct_video/frontend_gate.mjs | 33aec80148dba3bd04c47e61851a10923a85fc9b6387dfee8e34e310463f2c09 | 26dd9c5bd0218731316220ccd7f1ddd0cf4691b07c9f9f4a0549bd73ea767941 | 有 |
| scripts/direct_video/revision_frontend_gate.mjs | 18c077ee4aa840fdb255525365c902b61f917f55dcd4944449b2e7469351fd08 | c2576f4bda1306aa127dd3c72b8d95410c16613df09fc1d33f70b31cb5bf6c76 | 有 |
| tests/test_r276_direct_frontend.mjs | 50f464ff2f30a003f89e413feefbd0b0ef5ba63afff6474b9ce41b842170e721 | 50f464ff2f30a003f89e413feefbd0b0ef5ba63afff6474b9ce41b842170e721 | 无 |
| tests/test_r277_frontend.mjs | a798dd2df41e76508054527e280e1dab4103e9c2fd5446a3b84fefe34a09c08c | a798dd2df41e76508054527e280e1dab4103e9c2fd5446a3b84fefe34a09c08c | 无 |

两份旧门禁未登记在旧合同Protected acceptance tests表内，但按任务要求另行审阅：R276保留请求、导入、成片及交互，只组合R278已批准的分支文案，增加旧视频回调回归；R277状态源可配且只读克隆，按操作后投影组合外层步骤锁，保留镜详情、标记、版本及几何/溢出断言。修法见REPORT-F1第6、10、11节；本线程只验证，不修改它们或任何approved-extras。

candidates.py按origin/main..HEAD从头召回，最高综合分约0.611，unmapped为空。对R207工具候选、R210音乐导入、R220导航精选预览、R223标签节拍分别声明具体independent；R276原生成/配音/合成/单镜不变性、R277选块/版本/样例/规则也不由本卡全片重生成承接。新旧claims含对应双向独立声明，没有互相refines、自动退役或取消旧卡责任。

仅使用稀疏检出的各原位验收子目录；R223原位目录用于读取既有卡，未搬移或刷新R210/R220旧证据，没有处理其已知Core冲突。

## 提交后交付检查

命令：`check_delivery.py --project-root <worktree> --range origin/main..HEAD --json --read-only`。验收物提交后实际exit 1：15 PASS、仅G1/G9 FAIL，无WARN。完整结果保存在仓库外 `~/.photo-content-os/evidence/R278-direct-rescript/handoff-2-fc072d9-final/check-delivery.json`，SHA-256：`a868744d4475098aeca83dc2cf8dd8f981501982b7ff2c86c7bdf75ac401def1`。本包check-delivery-precommit.json保留提交前同结论。

| 门禁 | 结果 | 原因及推送影响 |
| --- | --- | --- |
| G1 有卡 | FAIL | 三张blocking卡未获当前用户人工PASS。普通失败；默认warn仅提示，enforce拒推，不能报告READY。 |
| G2 基准一致 | PASS | base、verified head/tree、source_commit与绑定/清单/合同摘要一致；本项不阻推。 |
| G3 机器先绿 | PASS | 六条引用证据均为本轮fc072d9限定机器PASS，result摘要匹配；本项不阻推。 |
| G4 看得懂 | PASS | 原样三项中文清单通过可读性检查；本项不阻推。 |
| G5 有入口 | PASS | R278每项实际网址有效，两旧卡原入口保留；本项不阻推。 |
| G6 去重已声明 | PASS | 召回候选、主题与新旧关系完整，无遗漏警告；本项不阻推。 |
| G7 失效传播 | PASS | 未改已通过卡结论或责任；本项不阻推。 |
| G8 坏一条不连累 | PASS | 只读生成健康与修复路径检查通过；本项不阻推。 |
| G9 页面可见 | FAIL | 三张当前ready/ACTIVE交接未发布到调度台快照，本线程未写Harness。普通失败；默认warn提示，enforce拒推。 |
| G10 不自证 | PASS | 没有人工签署、反馈或去掉未-；本项不阻推。 |
| G11 有需求卡 | PASS | 需求及提交Request/Verify尾注有效；本项不阻推。 |
| G12 验收覆盖需求 | PASS | Verify属于对应需求，三项原文覆盖，无标准变更；本项不阻推。 |
| G13 沿用已有卡 | PASS | 没有另开完全相同的验收责任；本项不阻推。 |
| G14 已通过不可变 | PASS | 没有修改已通过卡或人工历史；本项不阻推。 |
| G15 自动替代完整 | PASS | 无虚构替代，关系与重算一致；本项不阻推。 |
| G16 不连累前面的卡 | PASS | 两卡均有同批同头completed rebaseline、新PASS及重新handoff；硬门禁通过。 |
| G17 真实链路没被替换 | PASS | 三个任务证据根没有执行脚本；夹具与历史重放范围已披露；本项不阻推。 |

本任务无条件不推送；默认warn的技术策略不等于人工通过或发布就绪。独立的文档同步、全量测试和深层视觉归档FAIL已另外列明，未被这张交付门禁表掩盖。

## 边界与Git状态

边界快照 `2026-10-26T17:19:40.263782+00:00`：源码、测试、schemas和docs的581个受控文件开工/收尾摘要全部相同，没有上一轮的并行改动；.venv软链目标、inode、mtime保持不变。8769仍为原PID 58162监听；没有停启8765/8766/8767/8769，临时8768及自有无头浏览器已退出。

业务项目：本轮验收物提交a5d29a3，回执仅追加本文件。提交后工作区仅原有未跟踪.venv；没有推送、安装钩子、改写fc072d9、创建新worktree或执行finish。
Harness SSOT：本线程零写入。开工状态79项、收尾状态77项，其他会话内容原样保留；没有回退、暂存或提交。完整状态在boundary-before.json、boundary-precommit.json和仓库外handoff-2-fc072d9-final/boundary-final.json。
本包是普通合同和证据，不含ssot-archive.json声明的SSOT开发包；不生成Obsidian SSOT快照或提醒。

## 推送前还缺什么

1. 用户按三张卡原标准亲自验收并提交结果；H-03近似时长解释不是PASS。两旧卡原文及入口不变，验收时由总控确保打开对应版本。
2. 总控发布三卡当前ready/ACTIVE的调度台快照并复核G9，本线程不修改Harness或发布快照。
3. 对已知文档时间戳、outline、全量9失败6错误及严格视觉实体图归档差异，由对应责任方另行处理或裁决；本任务按明确范围保留原失败。
4. 若后续源码、测试或冻结范围变化，重新核对受影响证据；不把fc072d9的PASS用于其他源码身份。

按指令：本汇报做仅含本文件的回执提交后停止，不推送。
