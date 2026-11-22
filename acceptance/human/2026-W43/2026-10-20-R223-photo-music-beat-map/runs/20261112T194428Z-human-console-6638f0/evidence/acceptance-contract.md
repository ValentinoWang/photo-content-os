# Acceptance Contract: 2026-10-20-R223-photo-music-beat-map

- Task ID: 2026-10-20-R223-photo-music-beat-map
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户阶段 C 指令；Claude 已复核 A 与 B；H-01 至 H-03 原样沿用需求卡
- Request source: acceptance/requests/2026-W43/2026-10-20-R223-photo-music-beat-map/request.json; docs/tasks/R223-music-beat-map/TASK.md; docs/tasks/R223-music-beat-map/DESIGN.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: music.analysis, music.beat-map, music.tags
- AC budget: 3
- Baseline identity: 本批 origin/main 与 verified head，详见 baseline.json
- Product Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Role Context refs: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Resolved Surface Contract refs: docs/tasks/R220-studio-ia-preview/resolved-surface-contract.json
- Screen Contract ref: docs/tasks/R220-studio-ia-preview/acceptance-context.json
- Visual Contract refs: docs/tasks/R223-music-beat-map/mock/design-contract.json; docs/tasks/R223-music-beat-map/DESIGN.md
- UI Change declaration: agents-results/2026-10-21/r223-delivery/ui-change.json
- Human acceptance workspace: acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map

## User and scenario

本机创作者在音乐库筛歌、试听并核对拍子，只有用户判断鼓点听感是否对齐。

## Problem

曲库需要 AI 标签、可解释的段落与拍点状态；取消曲目授权记录及展示。

## Expected outcome

按批准的 TASK、DESIGN 和交互稿实现标签、分面筛选、节拍图、增量分析状态与独立重试；供 R226 共用完整拍点接口。

## Non-goals

不开放人工改标签、不自动排成片、不扩曲库。本阶段不推送、不迁移真实库、不操作 8765。

## Normal path

Given 临时库中已完成分析的歌；When 筛选、选歌并播放；Then 页面显示真实派生标签与测得节拍，播放器位置与节拍图同步。

## Exception paths

排队、分析、部分失败、未知失败、不可读音频明确显示；不可读不重试；两部分重试独立且失败回滚。非法 part、未知曲目和非法写来源按 DESIGN 10.1 返回精确状态与错误码。

## Invariants

只用素材根定位媒体；taxonomy 是名称与顺序权威；原始分数不下发；R226 读取完整结果，缺失不返回半成品；不改原始音频。人工记录不变。

## Data impact

测试只写临时副本；本轮没有生产迁移或模型版本改动。分析 sidecar 原子写；软件回退保留用户原始文件。

## Permissions

本机页面、CSRF 令牌与 Origin 校验；不代替用户签署。

## Performance and reliability

队列一次一首，状态不长于一秒轮询，完成即停止；rAF 不重画整页；标签与节拍独立失败恢复。

## Acceptance criteria

| ID | Class | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | machine/integration-contract | 迁移、分析、派生标签、完整读取、独立队列及重分析错误码与 OpenAPI 契约一致 | Integration | Automatic | Yes |
| AC-02 | behavior | machine/e2e | 标签筛选、播放跳转、即时重试回滚、并发独立、轮询及 R226 共用模块符合设计 | E2E | Automatic | Yes |
| AC-03 | behavior | machine/e2e | 已批准三档全部状态、文案编号与十三行数字公式；真实复制品结果可显示，原件不变 | Visual | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 音乐标签和节拍图 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 鼓点与节拍同步听感 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 新导入自动分析及夏日筛选 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_r223_music_analysis.py | 1ad66c0329ff743703f4a0fed14b5ec90df292cfb2a69d7025ee3d3ad1408232 | AC-01, AC-02, AC-03 |
| tests/test_r223_sections.py | 8d1241bdc92b558632581c64acc4b0c8f7acb683928062f75440886eb7393a75 | AC-01, AC-02, AC-03 |
| tests/test_r223_music_analysis_runtime.py | c6d945a51cff3ce540eda0ce6e864c1efdfeefd183ee8ed7f06b1baff73153d2 | AC-01, AC-02, AC-03 |
| tests/test_r223_beat_map.mjs | 1d6fa412d672a86dd0e2e5b6828236f67ac8817f25d3d32fb5e17bd391e6fa01 | AC-01, AC-02, AC-03 |
| scripts/verify_r223_interactions.mjs | 77603cb7e38a40704ab2ac4accb0051fe0358e0a40ec2119b794afd3c0c40e5b | AC-01, AC-02, AC-03 |
| scripts/check_r223_design.py | 7f2b48d69ff50d097e0b9fc4d2f2981b41ab291aa3f1a5ada5570a409180d705 | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | R223 全部后端、分段、真实模型与接口测试 | tests/test_r223_music_analysis.py; tests/test_r223_sections.py; tests/test_r223_music_analysis_runtime.py | Automatic | Yes |
| AC-02 | 真实挂载浏览器交互与共享模块 | scripts/verify_r223_interactions.mjs; tests/test_r223_beat_map.mjs | Automatic | Yes |
| AC-03 | 页面矩阵、公式、文案、视觉证据绑定；复用 Claude 已通过的 B 截图 | scripts/check_r223_design.py; scripts/capture_r223.mjs; evidence/2026-10-21/R223-music-beat-map/phase-b/ | Automatic | Yes |
| H-01 | 原样需求卡人工体验 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-01 | Human | Yes |
| H-02 | 原样需求卡人工体验 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-02 | Human | Yes |
| H-03 | 原样需求卡人工体验 | acceptance/human/2026-W43/2026-10-20-R223-photo-music-beat-map/checklist.md#h-03 | Human | Yes |

## Exploratory testing

两部分同时重试、未知错误、平坦能量与结构抖动、手机展开、队列无页面刷新；阶段 B 已由 Claude 复核。

## Production monitoring and rollback

本轮不执行部署。推送、finish、主目录同步、真实库备份迁移及 Studio 重启由 Claude 获准后串行安排；失败停止，恢复备份不覆盖音频。

## Risks and open decisions

全库已知字幕/视频环境与 Obsidian 同步失败不属于上述 PASS 范围；不修改既有失败来凑绿。人工听感和真实平台账户仍需用户验收。
