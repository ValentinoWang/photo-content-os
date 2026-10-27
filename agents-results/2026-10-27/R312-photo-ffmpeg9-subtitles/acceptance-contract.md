# Acceptance Contract: 2026-10-27-R312-photo-ffmpeg9-subtitles

- Task ID: 2026-10-27-R312-photo-ffmpeg9-subtitles
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27原话「照它给 R312 递交验收卡」「只提交验收物，不推送」；总控TASK.md指定本轮机器范围和三项环境失败边界，H-01原样非阻塞，不代表人工PASS
- Request source: acceptance/requests/2026-W44/2026-10-27-R312-photo-ffmpeg9-subtitles/request.json; agents-results/2026-10-27/R312-photo-ffmpeg9-subtitles/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.ffmpeg9-subtitles
- AC budget: 2
- Baseline identity: 5d62356222028aa31083fc693845875b1acf5edd，见baseline.json
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-27-R312-photo-ffmpeg9-subtitles

## User and scenario

创作者打开已有字幕的作品，选择剪辑工具开始剪第一版，预期得到带字幕、能播放的第一版成片。

## Problem

ffmpeg9删除旧参数导致烧字幕失败，场景切换抽帧静默返回空；一项静态测试仍使用旧深色令牌。

## Expected outcome

同一字幕内容、样式和位置可用当前ffmpeg正常处理；场景切换有真实帧输出；已有浅色界面和深色视频区的测试标准一致。当前开发机回归仅允许任务单点名的三项环境失败。

## Non-goals

本轮不改实现、测试、技能、界面、字幕样式或内容；不修开发机Obsidian与melt差异，不运行真实作品，不部署、不推送。为已冻结实现补齐交付，不追称实现前已有本合同。

## Normal path

Given 冻结源码与开发机ffmpeg9.0.2；When 运行字幕、双语、预览黑帧、场景抽帧及界面令牌定向验证；Then 定向全部通过；When 在heavy队列执行全量；Then 不出现三项明确环境失败以外的新失败。

## Exception paths

有任何额外失败、收集错误、测试未跑完或来源身份不符，保留原文并停止递交，不改断言、不增环境白名单。环境三项失败保留真实pytest退出码，不把全量写成全绿。

## Invariants

旧卡保护和人工结果不改；真实媒体、成片、剪映草稿和开发机真实数据不碰。测试临时媒体在开发机生成，文本证据脱敏，不拉视频或原尺寸帧到本机。

## Data impact

只新增验收物、证据和生成台账；无产品或真实素材数据更改。

## Permissions

执行者仅准备机器证据和交付卡，任务委托人独立验收H-01。H项非阻塞、五分钟，不能代签。

## Performance and reliability

全量与可能渲染的定向检查经开发机heavy队列串行；固定.venv和源码身份，完整记录开始、结束与退出码。不新增耗时阈值。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 指定字幕/双语、预览黑帧、场景抽帧和浅色令牌定向检查在ffmpeg9环境全通过 | Integration | Automatic | Yes |
| AC-02 | behavior | H-01 | machine/non-functional | 当前源码全量完整执行，零收集错误，仅点名三项环境失败，无其他失败；跳过项ID、原因和数量如实记录 | Regression | Automatic | Yes |

## Human acceptance

原H-01由真实创作者判断第一版成片与口播对齐；合成测试不替代真人完整作品流程。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 第一版成片有字幕且可播放 | acceptance/human/2026-W44/2026-10-27-R312-photo-ffmpeg9-subtitles/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_direct_video_subtitles.py | b84bc4a3d6718b344c3bd9707c363d6c22b321d0e26b9c6d943d5ed109c3dbca | AC-01, AC-02 |
| tests/test_bilingual_subtitles_r6.py | 03ce62a8d9be62ed3ab6e1f1e56efaec6bb1ace0c0e4f97562a9588eda9a203f | AC-01, AC-02 |
| tests/test_pf_video_pipeline.py | 98f336196582e73aa79eb41b1869d2f8d4db9a353e948b84ba2b95bde31c10ef | AC-01, AC-02 |
| tests/test_output_video_review.py | 5b4ea9e62a993582e15b21b76bfb82bfbd1840ec02e35972b42274594a6644ee | AC-01, AC-02 |
| tests/test_full_checklist_acceptance.py | 3051adf605487ce5ff303673ed9757ba9850ef5d6a17f052dff98d26ade18931 | AC-01, AC-02 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 任务单指定五组定向 | tests/test_direct_video_subtitles.py; tests/test_bilingual_subtitles_r6.py; tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests; tests/test_output_video_review.py; tests/test_full_checklist_acceptance.py | Automatic | Yes |
| AC-02 | 开发机全量及精确环境失败核对 | expected-environment-failures.json; .venv/bin/python -m pytest -q -p no:cacheprovider -rfE tests | Automatic | Yes |
| H-01 | 原人工作品流程 | acceptance/human/2026-W44/2026-10-27-R312-photo-ffmpeg9-subtitles/checklist.md#h-01 | Human | No |

## Exploratory testing

本轮不新建额外浏览器验收，不调用付费模型；本任务不改变渲染界面设计，不需要新增屏幕设计合同。

## Production monitoring and rollback

不部署、不操作现有真实任务。发现问题写报告后停下，交总控修复，不自行回退别人提交。

## Risks and open decisions

开发机ffmpeg9.0.2、Noto/Liberation字体替代和melt7.4对本机7.39存在差异；缺Obsidian库。三项允许失败精确登记expected-environment-failures.json，允许失败的回归条件PASS不等于pytest全绿；完整原始结果和未验证边界必须保留。总控2c4ff30的1214过/3红/36跳过只作历史背景，本轮必须在5d62356重新执行。人工未签。
