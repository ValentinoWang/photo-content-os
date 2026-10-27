# B 后端汇报

日期：2026-10-27。需求：「中台交过来的分镜和配音直接进脚本直出 · 待确认（2026-10-26-R282-photo-direct-handoff-storyboard）」。只执行任务单第 0、1 节与 B 段；HEAD 保持 `614c550`，没有提交、推送。

**结论：部分完成，不能报 READY。** 可独立完成的读取、图片、配音接入、版本冲突和接口合同已实现并通过选定回归。当前中台交接格式缺少交接时间、分镜版本号，影响 H-01 的时间显示和 H-03；按任务单要求把需拍板事项写在这里，停止，不修改中台仓库或 F 段文件。

## 1. 接口与实现

- `GET /api/projects/{id}/direct/handoff` 返回 `{ok: true, handoff: null | {...}}`。缺失、不可读、身份不匹配时为 `null`。
- `studio/direct_handoff_contract.py` 的 `read_handoff()` 是公共读取入口；`_video_handoff_projection()` 与脚本直出共用。保留素材根、workspace、binding、canonical creative store、作品和作品版本校验，拒绝越界路径及非法任务标识。
- 图片读取 `video-inputs/{jobId}/shot-images/{shotId}.jpg`，存在且位于本机 workspace 内才给 `image.url`；图片元数据保留来源、版权状态和原片时间。图片接口为 `…/direct/handoff/images/{shotId}?v=<内容哈希>`，旧哈希或文件已不存在返回 404。
- `POST …/direct/jobs` 接受可选 `handoff: {jobId, revision}`；须与当前包相同，否则 409 `handoff_changed`，不创建任务或调用模型。任务保存这两个字段，后续新交接不会改写已建任务。
- 交接含配音时，从 `mxHandoff.tts_ref` 取本机 WAV，复制为这次任务的独立配音。与上传配音共用 `copy_narration()`、`_align()`：校验音频、转写、分配实测时长、重写过长动画，再使用现有带配音合成流程。配音缺失、损坏或越界时阻止建任务，不生成无声替代品。
- 任务投影字段：`handoff`（旧任务为 `null`）、`handoffNewer`（布尔值）。有来源时比较 `handoff.revision`；无来源时按 `handedAt > createdAt` 比较，正确处理时区。未知时间不推断为更新。
- 任务轮询只读取交接身份，不读取图片字节或扫描历史交接目录。
- `studio/api_contract.py` 和 `schemas/studio-openapi.json` 已同步，包含新路由、输入、任务字段及 409 说明。

## 2. 版本和时间来源：需要总控处理

已只读核对中台实际文件：

- `apps/media/agent/openclaw_media/video_exchange.py`（任务单中的路径少了 `apps/media/`）。
- `apps/media/api/openclaw_app/services/media_business/creation_video.py`。
- `apps/media/api/openclaw_app/services/device_job_service.py`。
- `apps/media/web/src/media/creation-workbench/CreationVideoPanel.tsx`。

| 返回字段 | 当前取值及限制 |
| --- | --- |
| `revision` | 取 `video.json.identity.workRevision`，即中台作品版本。不是 Photo 的 `photoProjectRevision`，也不是本机文件计数。 |
| `handedAt` | 当前返回 `null`。描述文件未携带该事实；不使用文件 mtime、配音时间或本机请求时间冒充交接时间。 |
| `title` | 取已绑定的本机作品标题；当前描述文件没有中台作品标题字段。 |

有两处实际协议缺口：

1. 中台创建交接时设置 `state.handoffCreatedAt`，但构造的 `VideoHandoffDescriptor` 不含该字段，Agent 原样落盘也未补充它。因此无法从现有包取得交接时间；非交接任务的时间比较分支目前只有确定性单测，真实包无法触发。
2. `save_creation_video_storyboard()` 修改分镜后通过 `_save()` 增加的是视频状态 `state.revision`，并不增加 `state.workRevision`。描述文件只带后者。所以仅改第 02 镜再交接，可能得到新 jobId、相同 `workRevision`；按任务要求的数值大小判断不能识别这次更新。

需要总控确定并提供随包传输的交接时间和随分镜修改递增的版本字段，然后对齐 B/F。当前没有擅自用 jobId 不同替代版本比较，也没有修改只读中台协议。H-01 时间和 H-03 完整链路未完成，H-02 未做真实模型/渲染验收。

## 3. 先红后绿与回归

新增测试只在 `tests/test_r282_handoff.py`。先写测试，未改产品代码时运行：

```bash
.venv/bin/python -m pytest -q tests/test_r282_handoff.py
```

结果：**22 failed，14.42 秒**。失败包含路由 404、未拒绝旧来源、投影缺字段、配音未接入及 OpenAPI 缺路由。实现后补充无配音、冻结来源、损坏/越界配音、不可读文件和读取预算边界；最后同文件复验：**29 passed，15.21 秒**。

选定后端回归命令：

```bash
.venv/bin/python -m pytest -q --tb=short \
  tests/test_r282_handoff.py \
  tests/test_r276_direct_video.py tests/test_r276_direct_api.py \
  tests/test_r276_direct_media.py tests/test_r276_direct_c.py tests/test_r276_direct_d.py \
  tests/test_r277_api.py tests/test_r277_boxes.py tests/test_r277_revisions.py \
  tests/test_r278_style_base.py tests/test_r278_clips.py tests/test_r283_style_library.py \
  tests/test_ps_studio_handoff.py tests/test_ps7_direct.py \
  tests/test_ps3_video_workflow.py tests/test_ps4_returned_candidate.py \
  tests/test_desktop_openapi_route_sync.py tests/test_full_checklist_acceptance.py
```

结果：**351 passed，3 skipped，22 subtests passed，125.00 秒**。没有跑全量 pytest。进程环境核对 `VIDEO_RENDER_*` 为零；跳过真实 HTML 渲染和两项 DOM 测量，不开浏览器。生成测试使用现有模型/媒体替身，不真调模型；既有缓存帧合成测试运行真实 FFmpeg，但不启动 HTML 渲染。预算测试最后加强后单独复验：**1 passed**；随后上述 R282 文件完整 29 项再次通过。

实现过程回归发现公共读取抽取遗漏 `project` 变量，已修复，相关旧交接用例全部复验通过；没有修改旧测试断言。

| 保护点 | 检查与结果 |
| --- | --- |
| 两个页面同源、身份隔离 | `test_invalid_inputs_match_video_projection`、`test_bound_descriptor_and_canonical_revision`；通过。 |
| 只读接口、图片仅限本机 | `test_projection_columns_local_image_and_read_only`、`test_external_image_symlink_not_served`、不可读文件测试；通过。 |
| 来源冻结、拒绝过期版本 | `test_create_rejects_changed_handoff_before_work`、`test_create_handoff_without_audio_and_frozen_source`；通过。 |
| 配音实测、改短、带声合成 | `test_handoff_narration_alignment_shortening_and_composition`；替身验证通过，0.4 秒音频分两镜各 0.2 秒，两镜均重写并以 narrated 合成；非真实成片验收。 |
| 配音读取失败不静默降级 | 缺失、无效 WAV、外部符号链接、路径穿越、损坏 mx 元数据测试；通过。 |
| 更新提示两种条件 | `test_newer_handoff_conditions`；版本和时间比较均通过，真实时间来源缺口见第 2 节。 |
| 范围有界 | 增加 10 个无关交接目录前后，轮询都只调用一次描述文件读取、读取 0 次图片字节；通过。 |
| 合同不漂移 | OpenAPI 精确生成内容相等、新接口测试及 route sync；通过。 |

## 4. 真实交接包只读实测

在素材根发现 23 份中台旧交接描述文件。选择已有绑定 `testing/video-pipeline-2026-10-12/p5-binding.json`，按公共读取函数的 workspace/binding 规则打开：

`testing/video-pipeline-2026-10-12/video-inputs/job_b807de35d0824fd5bc48360ebad2d041/video.json`

使用真实现存 creative store、绑定、描述文件及生产 HTTP Handler，在系统分配的回环端口 **51414** 发起 GET；响应 **200**：`revision=3`、2 镜、Cherry 配音 50.24 秒、0 张已落地图片、`handedAt=null`。没有生成、转写、渲染、启动浏览器或访问 8765–8769。

为遵守现有状态目录只读，绕过会建目录/锁文件的应用初始化，只装配现有 store 的生产读取方法、DirectVideo 读取适配器和 HTTP Handler；未替换身份校验、投影或路由。实测前后 creative store、binding、descriptor 三份文件 SHA-256 均相同，临时 HTTP 服务已关闭。这证明旧真实包可被接口读取，不证明完整应用启动或 H-01–H-03 已验收。用户验收应重新在中台点「交给我的电脑」取得当前作品交接；旧包不能代替当前版本验收。

## 5. 其余检查与未通过项

| 检查 | 结果 |
| --- | --- |
| `bash scripts/check_runtime_contract.sh` | 通过，最后源码复验含 compileall、packages、encoding、安全检查。 |
| `validate_music_analysis_registry.py` | 配置 `UI_COPY_QUALITY_CHECKER` 为 Core checker 后通过：126 IDs、121 文案。首次漏配置失败已纠正，未修改门禁。 |
| `check_repository_safety.py --base origin/main` | 通过，最后源码复验通过。 |
| `check_obsidian_doc_sync.py` | 失败：3 组现有本地文档时间戳晚于 Obsidian 配对文档。显式设置 `OBSIDIAN_ROOT`。 |
| `check_outline_contract.py .` | 失败于同一文档同步检查；显式设置 `OBSIDIAN_ROOT` 后复验仍失败。 |
| 两个 validator 的 `--help` | 均通过。 |
| `git diff --check` | 通过。 |
| `task_worktree.py check` | 按现状报告当前 worktree 有未提交文件；依用户“不提交、不推送、写报告后停止”保留，不执行 finish。 |

文档同步失败涉及 collaboration、editing_handoff、historical_jianying 三组；`scripts/README.md`、`docs/execution-rules.md`、两个检查脚本和 `doc-sync-contract.json` 均与 HEAD 相同（`git diff --exit-code HEAD -- ...` 为 0）。本轮没有改动这些文件、Obsidian 文档或时间戳，不通过放宽 marker 规避问题。需另行处理现有文档同步，不能将全局检查报成全绿。

## 6. 边界、协作与 Git 状态

B 实际改动：

- `scripts/direct_video/generate.py`
- `studio/direct_video.py`
- `studio/direct_handoff_contract.py`（新增）
- `studio/server.py`
- `studio/api_contract.py`
- `schemas/studio-openapi.json`
- `tests/test_r282_handoff.py`（新增）
- 本报告。

F 对接字段已定为 `handoff`、`handoffNewer`；本轮读取所见 F 实现使用相同字段。F 需保留 `handedAt=null` 的未知处理；不要把夹具里的时间当成真实中台已经提供的字段。分镜版本和时间缺口由总控先决定协议再继续，不能仅靠前端文案弥补。

业务仓库最后检查还可见 F 正在修改的 `scripts/direct_video/rescript_frontend_gate.mjs`、`studio/static/direct-view.js`、`direct-storyboard.js`、`direct-rescript.css` 及 F 新测试/夹具；没有编辑、回退或暂存它们。`.venv`、任务单目录和只读需求卡本来未跟踪，保留。

Harness SSOT：**本轮零修改**。只读检查时其工作区已有 77 个已跟踪修改项、17 个未跟踪项，属于外部工作，未处理。项目缺失的 `develop/harness/fullstack-ai-harness.md` 没有补建，已改读 Core 权威规则与现有项目 adapter。本报告是执行汇报，不新建或更新声明式 SSOT 包，无 SSOT 快照操作。

启动时已读取机器验收日志，相交的 R276/R277/R278/R283 人工项仍为 PENDING；未代签、未重绑或创建 READY 交付。机器输出留在工具会话记录，无媒体或真实交接内容写入 Git。磁盘可用空间从约 4.3 GiB 到最后约 **4.2 GiB**，未低于 3 GB。

已按任务要求在写完本报告后停止。

## 补充 1

2026-10-27：已按 TASK.md 末尾「补充 1」完成 B 部分。本节替代上文第 2 节关于版本来源、时间来源的旧实现结论；上文保留为首轮记录。Studio 后端已支持约定的两个可选字段，中台产出新字段和 F 的显示处理由各自线程完成，本轮未修改。

### 行为与合同

- `handoff.revision` 只读取 `video.json` 顶层 `storyboardRevision`。缺失、null、字符串、布尔、浮点、非正整数等无效值返回 `null`，不再使用 `identity.workRevision`。测试特意让作品版本为 70、分镜版本为 7，防止混用。
- `handoff.handedAt` 读取顶层 `handedAt`。接受完整 ISO UTC 时间（`Z` 或 `+00:00`，可带小数秒）；非法日期、无时区、非 UTC 偏移、非时间字符串和非字符串返回 `null`。两个字段分别校验，一个无效不会丢弃另一个或整个交接包。
- 旧包缺少两字段时仍正常返回分镜、图片和配音，两个元数据为 `null`。
- 建任务的 `handoff.revision=null` 时只比较 `jobId`，即使当前包已有分镜版本也允许；`jobId` 不匹配仍为 409。提交整数版本时继续要求它等于当前有效分镜版本，格式错误或版本不匹配仍为 409 `handoff_changed`。
- `handoffNewer` 在任务和当前包都有有效分镜版本时比较大小；否则尝试比较包的 `handedAt` 与任务 `createdAt`。时间缺失、无效或不可比较时为 false；相同版本不会仅因为交接时间较晚而变成 true。
- OpenAPI 的读取响应、建任务输入、任务来源均允许 `revision` 为整数或 `null`，时间字段说明已更新；生成的 schema 与代码精确同步。

### 先红后绿

先在 `tests/test_r282_handoff.py` 补测试并调整原用例的来源字段，再在未改实现时运行：

```bash
.venv/bin/python -m pytest -q --tb=short tests/test_r282_handoff.py -k supplement
```

结果：**22 failed，7 passed，29 deselected，11.46 秒**。确认了旧实现混用作品版本、拒绝空版本、空版本比较断连以及 OpenAPI 类型不符。随后才改实现；另外补了两个独立字段降级用例，确保有效字段被保留。

最终选定回归：

```bash
.venv/bin/python -m pytest -q --tb=short \
  tests/test_r282_handoff.py tests/test_r276_direct_api.py \
  tests/test_r278_style_base.py tests/test_ps_studio_handoff.py \
  tests/test_ps7_direct.py tests/test_desktop_openapi_route_sync.py \
  tests/test_full_checklist_acceptance.py
```

结果：**147 passed，22 subtests passed，40.58 秒**，其中 R282 文件覆盖 60 项。覆盖新包、旧包、格式错误、有效字段独立保留、空版本建任务、错误来源拒绝、两种更新判断及生产任务 GET 的时间回退；原身份、图片、配音和合同回归均通过。未跑全量 pytest，未设置 `VIDEO_RENDER_*`（核对为零），未开浏览器或真实调用模型。

`bash scripts/check_runtime_contract.sh`、`check_repository_safety.py --base origin/main`、`git diff --check` 均通过。上文已有文档同步/大纲检查未通过项不在此次修改范围，本轮未修复或宣称其通过。

### 旧真实包复测与边界

只读重测上文同一 `p5-binding.json` 绑定的真实旧包，使用生产 DirectVideo 读取适配器：交接仍可读，**revision=null、handedAt=null、2 镜、Cherry 配音 50.24 秒**；creative store、binding、descriptor 的 SHA-256 前后相同。此轮是读取投影复测，没有启动完整应用或执行生成；带新字段的中台真实交接和人工 H-01–H-03 尚未验收。

补充 1 实际只改 `studio/direct_handoff_contract.py`、`studio/direct_video.py`、`schemas/studio-openapi.json`、`tests/test_r282_handoff.py`，并追加本节。F 的脚本、样式、测试、夹具、门禁均未编辑；中台仓库及现有状态目录只读。业务仓库仍保留首轮 B 和并行 F 的未提交改动，未暂存、提交、推送。

Harness SSOT 本轮零修改；只读检查所见仍有外部的 77 个已跟踪修改项、17 个未跟踪项，未处理。相交的人工作品验收仍为 PENDING，未改验收记录。磁盘最后约 **5.1 GiB** 可用。写完本节后停止。
