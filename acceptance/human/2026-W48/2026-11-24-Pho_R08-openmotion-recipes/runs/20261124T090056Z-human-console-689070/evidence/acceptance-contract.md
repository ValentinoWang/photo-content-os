# Acceptance Contract: 2026-11-24-Pho_R08-openmotion-recipes

- Task ID: 2026-11-24-Pho_R08-openmotion-recipes
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 2026-11-24 需求卡 Pho_R08 原话「这些是不是可以混在一起？OM中的内容」与任务单指示「按 acceptance-handoff 技能给 Pho_R08 递交交付验收卡，人工项只递交不代签」；清单沿用已登记需求的步骤和预期，人工结论另由任务委托人填写。
- Request source: acceptance/requests/2026-W48/2026-11-24-Pho_R08-openmotion-recipes/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.openmotion-recipes
- AC budget: 1
- Baseline identity: 1819385594ce116d77c619b099632ddb4415c93b
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-24-Pho_R08-openmotion-recipes

## User and scenario

视频创作者在制作台宣传片的「选镜头配方」弹窗按类别浏览动效配方库，查看合并进来的 51 张 OpenMotion 单镜配方封面与悬停预览样片，并可离线播放任意一张单镜演示。

## Problem

OpenMotion 离线单镜导入后，原有 51 张卡缺少封面图与预览样片，且选配方弹窗页头写死单一来源 video-shotcraft、卡片未标出 OpenMotion 来源。

## Expected outcome

51 张 OpenMotion 单镜配方均具备本地渲染生成的封面 JPG、本地渲染登记了 SHA-256 的预览 MP4（且 fetch_clips 对本地渲染条目不走上游下载而走本地重渲核对）、按数据动态计算来源的弹窗页头以及 OpenMotion 卡的 OM 小字角标。

## Non-goals

不引入整套 OpenMotion sequence 模板，不改动原有 124 张 video-shotcraft 卡片内容与上游校验，不提交预览 MP4 进仓库，不代签人工验收结论。

## Normal path

1. 运行导入与索引重建后，动效配方库共 175 张卡（124 张 video-shotcraft + 51 张 OpenMotion），全部 51 张 OpenMotion 卡在 index.json 中具备 poster 与 clip 字段。
2. 在 Studio 宣传片打开选配方弹窗，页头按数据展示两个来源（video-shotcraft 和 OpenMotion，都是 Apache-2.0），OpenMotion 卡片类别角标旁显示 OM 小字，封面图与悬停样片均可正常加载，演示页可离线播放。

## Exception paths

OpenMotion 本地重渲样片 SHA-256 与 clips.json 不一致时，fetch_clips 明确报错并写明对应配方编号，不回退到上游下载。

## Invariants

机器证据绑定冻结源码 1819385594ce116d77c619b099632ddb4415c93b 与本合同。预览 MP4 保留在仓库外本地媒体目录，封面 JPG 与单张压缩参考截图随卡登记。人工结论由任务委托人签署。

## Data impact

新增 51 张 OpenMotion 离线单镜卡、演示代码、渲染封面图、clips.json 本地渲染摘要及交付验收卡；原有 124 张卡和真实用户素材保持不变。

## Permissions

执行方在开发机与本机完成机器验证和截图采样并递交待验收卡；任务委托人独立给出 H-01 人工结论。

## Performance and reliability

预览渲染在开发机并行执行，单卡保持原画布比例且宽不超过 960（960x576，30fps），同机重渲 SHA-256 逐字节一致。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | OpenMotion 离线单镜导入、51 张封面与 clips.json SHA-256 登记、fetch_clips 本地重渲核对及弹窗页头与 OM 角标专项测试全部通过，既有 R207/R223 范围单元回归通过 | Unit | Automatic | Yes |

## Human acceptance

沿用已登记需求卡 Pho_R08 的唯一验收项 H-01，递交后由任务委托人验收，不代签。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 按类别查看 OpenMotion 51 张配方卡并离线播放演示 | acceptance/human/2026-W48/2026-11-24-Pho_R08-openmotion-recipes/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_openmotion_import.py | b4eff0e02e435e3c260a1eb8e5d2b7ebf55be0bf68d285527852e25fb73f06fb | AC-01 |
| tests/test_openmotion_previews.py | 6ecbbe2968a190172899c3620f277b2fa93836743c16a933408ee52bda9b951b | AC-01 |
| tests/test_pho_r05_recipe_library.py | 3340934a3734e20e817232950ddc5056b3c7b60f920ccc25d4350af95422ea16 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 开发机专项与回归测试 | tests/test_openmotion_previews.py | Automatic | Yes |
| H-01 | 按类别查看配方卡并离线播放演示 | acceptance/human/2026-W48/2026-11-24-Pho_R08-openmotion-recipes/checklist.md#h-01 | Human | No |

## Exploratory testing

本机实拍桌面 1440 与手机 390 两张 Studio 选配方弹窗截图并逐张核验封面、OM 单行角标及 206 MP4 样片响应，另抽查 3 条渲染样片的画面帧与时长。

## Production monitoring and rollback

本轮无云端部署和生产媒体写入。发现问题可按 Git 提交直接回退。

## Risks and open decisions

H-01 待任务委托人亲自查看并签署结论。
