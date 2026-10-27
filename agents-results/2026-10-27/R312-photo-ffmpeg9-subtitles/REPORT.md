# R312 交付验收报告

记录时间：2026-10-27T11:12:30.523862+00:00。任务：剪第一版时烧字幕在新版 ffmpeg 上恢复正常 · 待验收（2026-10-27-R312-photo-ffmpeg9-subtitles）。

**本轮目标：G1 PASS、G12 PASS、G16 PASS。** 提交前完整交付检查16项PASS、仅G9调度台投影FAIL，退出1；不称全门禁全绿或发布READY。已正式递交非阻塞卡，H-01原文不变、五分钟、任务委托人，人工仍PENDING。

## 源码身份与编辑范围

任务worktree：`~/.local/share/task-worktrees/photo-content-os-ffmpeg9-subtitles`。base=`78b6e41c9605c359967a8fa0fc274fabbd512fed`（origin/main 78b6e41）；verified head/source_commit=`5d62356222028aa31083fc693845875b1acf5edd`（5d62356）；tree=`34dc9f1ee1686aa241d761d9f46cae4b07bbde6d`。总控2c4ff30的同代码历史全量不当作本轮证据；本轮在5d62356重新运行。

本执行线程只准备acceptance/与本任务agents-results/验收物、日志与报告，未改scripts/、studio/、tests/、技能或AGENTS.md，未修改原需求卡。没有操作真实Studio数据、媒体根、成片或剪映草稿，没有安装环境、启动常驻服务或推送业务远端。rbox同步源码到开发机是测试协议，不是业务发布。

## 机器运行

所有pytest均经 `.agents/skills/photo-remote-dev-box/scripts/rbox` 在photo-dev、固定.venv运行。定向与全量分别入heavy队列串行；本机未跑pytest、浏览器或渲染。本机重活进程前后 **0→0**，见local-process-budget.json。

| 范围 | 原始结果 | 本轮证据 |
| --- | --- | --- |
| 任务单指定定向五组 | **38 passed、2 subtests passed**，0失败、0跳过，1条Pillow弃用警告，27.12秒；退出0 | `acceptance/machine/integration-contract/runs/20261027T105409Z-photo-dev-target-709114/` |
| 全量tests | **3 failed、1214 passed、36 skipped、1 warning、2005 subtests passed**，287.91秒；原始退出1 | `acceptance/machine/non-functional/runs/20261027T105409Z-photo-dev-full-02bac1/` |
| 全量允许失败边界核对 | 三个实际失败ID精确等于TASK预先点名清单，0额外失败、0收集错误、36跳过 | 同full run的acceptance-assessment.json；冻结清单expected-environment-failures.json |

定向实际选择：tests/test_direct_video_subtitles.py、tests/test_bilingual_subtitles_r6.py、tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests、tests/test_output_video_review.py、tests/test_full_checklist_acceptance.py。包含新增场景切换帧回归；原字幕、双语、预览黑帧及认可浅色/深色视频区检查通过。

全量实际命令核心：`RBOX_QUEUE=heavy … bg <唯一任务名> <任务 worktree> -- .venv/bin/python -m pytest -q -p no:cacheprovider -rfE tests`。外壳只追加Git/环境身份读取、JUnit导出和结果读取，保留pytest原始退出码，不改测试选择或断言。完整remote_script、参数、时间、队列和退出码在各run的evidence/command.json。

JUnit定向tests=40含2个子测试；全量tests=3258含2005个子测试，独立pytest用例数1253=1214通过+3失败+36跳过。不能把JUnit总数误报为独立用例数。原始输出保存在pytest-target.log、pytest-full.log；每个失败和跳过的ID、原因及失败详情保存在test-summary.json。

## 三项环境失败（保持原始失败）

| 测试ID | 实际失败与环境差异 |
| --- | --- |
| tests/test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies | 文档检查子进程退出1，缺少开发机Obsidian目标文档；真实FileNotFoundError原文保留，未当作同步通过 |
| tests/test_pf_video_pipeline.py::FrameMappingTests::test_every_frame_matches_retained_source_clock | 帧时钟列表不一致，首个差异索引210（实际0、预期330）；开发机melt7.4对本机7.39 |
| tests/test_pipeline_backends.py::MeltPipelineTests::test_overlay_and_subtitle_pixels_are_rendered | 像素断言0不大于10；开发机melt7.4的叠层/字幕结果差异 |

**全量pytest没有全绿，真实退出码仍为1。** full run的Status: PASS只表示合同AC-02预先定义的「允许三项环境差异、无额外回归」条件满足。pytest失败、缺失运行和允许边界核对分开记录，没有把三项断言伪装成通过，没有新增skip或放宽测试。36项条件跳过的ID和原因全部可查，未执行的项目不称通过。

## 开发机环境与未验证范围

实际输出ffmpeg `n9.0.2-36-g6882969ce9-20261026`、melt `7.4.0`；STHeiti路径实际链接至NotoSansCJK-Bold。按技能说明，本机melt为7.39，中文字体/苹方和Arial不同；开发机用Noto及Liberation的同路径链接，存在特定macOS复制命令的cp替身，且没有Obsidian库。这些差异没有被本次验收修复，也不代表两机等价渲染。

本轮不跑真实作品「开始剪第一版」的人工作业，不调用付费模型；合成字幕和帧断言不能替代真实口播对齐判断。H-01完整保留给任务委托人，不写feedback、签署或人工PASS。没有把视频或原尺寸帧拉回本机，当前本任务文本证据约94KB。

## G16与旧卡保护

已逐张读取11张现存卡的binding及合同，全部可读。protected-test-inventory.json记录合同摘要、完整保护文件列表、实际base..head变更文件及交集。

本批实际改动的测试文件是test_full_checklist_acceptance.py和test_output_video_review.py；test_pf_video_pipeline.py本身未改，关联实现路径的修复由本次定向/全量覆盖。这些实际变更没有命中任何旧卡锁定的文件，故**没有rebaseline目标，不应补造准备记录**。旧卡的合同、保护测试、人工状态和责任均保留。最终G16还由正式check-delivery核对，不只依赖手工盘点。

## 递交与结构检查

- 合同版本1，APPROVED/LOCKED；声明UI Change为none，本轮未改渲染界面。
- 绑定与handoff位于acceptance/human/2026-W44/未-2026-10-27-R312-photo-ffmpeg9-subtitles/，request_id与task_id完全相同。
- H-01步骤及预期与当前request.json逐字核对一致；non-blocking、estimated_minutes=5、required_role=任务委托人。
- handoff只引用当前5d62356的两份新run，结果摘要完整；机器范围通过后立即入非阻塞队列，随后重建索引与台账。
- 合同校验、本任务深层check、check-project均OK。候选召回最高分0.30926375222348906，无达到0.35或L0的候选，无需新增关系；其他旧责任不被本卡承接或取消。

## check-delivery 提交前原样结果

命令：`python3 ~/Desktop/Opensource_Tool/Harness_Engineering/tools/harnessctl.py acceptance check-delivery --project . --range origin/main..HEAD`。本次范围为78b6e41..5d62356，退出1：

```text
check-delivery  origin/main..HEAD  (2 commits, tree 34dc9f1)
  G1 有卡  PASS  
  G2 基准一致  PASS  
  G3 机器先绿  PASS  
  G4 看得懂  PASS  
  G5 有入口  PASS  
  G6 去重已声明  PASS  
  G7 失效传播  PASS  
  G8 坏一条不连累  PASS  
  G9 页面可见  FAIL  2026-10-27-R312-photo-ffmpeg9-subtitles 没有出现在 ready/ACTIVE 投影中 → 重新生成调度台并确认新卡 ready/ACTIVE → python3 tools/console/generate_console.py；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py check-project --project-root .
  G10 不自证  PASS  
  G11 有需求卡  PASS  
  G12 验收覆盖需求  PASS  
  G13 沿用已有卡  PASS  
  G14 已通过不可变  PASS  
  G15 自动替代完整  PASS  
  G16 不连累前面的卡  PASS  
  G17 真实链路没被替换  PASS  2026-10-27-R312-photo-ffmpeg9-subtitles: 证据里没有脚本
结果：FAIL（本命令如实返回门禁状态；推送策略由调用方应用）
```

G9是已登记主检出的调度台快照尚无本卡；本线程不改登记、不写假ready、不覆盖其他主检出或Harness生成文件。G17如实显示证据里没有可执行脚本，不外推为所有产品入口的独立静态审计。

## 规则卡逐项结果

| 规则 | 结果 |
| --- | --- |
| 每次Git写操作前断言本worktree | rbox同步源码和后续暂存/提交均在新worktree根断言后执行；不推送 |
| G16必须通过、读不到不当不相关 | 11张旧合同全部可读，实际保护交集为空；正式G16 PASS，无旧卡被改写 |
| 逐文件git add -f与隐私检查 | 只暂存合同、运行、台账、TASK与REPORT明确文件；本机路径用~或任务worktree脱敏；不提交本地delivery缓存；仓库安全在验收物提交后经rbox检查并补结果 |
| 如实报告通过范围 | 定向38+2通过；全量1214过/3失败/36跳过/2005子测试，退出1保持；环境差异与人工未验完整列出 |
| 本机不跑pytest/browser | 本机重活0→0，pytest和可能涉及的渲染都在开发机，无本机大媒体证据 |

仅普通验收证据包，无SSOT声明，不创建Obsidian快照或提醒。提交后的门禁、仓库安全和Git收尾状态另补在下一节。只提交验收物，不推送。
