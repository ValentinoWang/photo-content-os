# R278 第一段 A：后端汇报

日期：2026-10-26。对应需求卡「脚本直出先定视频风格，生成过以后能回到分镜脚本改了重新生成 · 待确认（2026-10-26-R278-photo-direct-rescript）」。

本段完成 TASK 第 2–5 节的后端工作。所有业务源码改动均在指定任务 worktree；主目录的任务单、设计稿和上游分镜只读。没有提交、推送、创建新 worktree、修改前端或操作 8765/8766/8767 的 Studio。

## 1. 改动文件

| 文件 | 改动 |
| --- | --- |
| scripts/direct_video/generate.py | 保存四列；校验设计短文案；接入风格来源与样张目录；复用既有逐镜自查、原子状态、恢复及后台工作机制；写镜及 R277 重写带编导三列。 |
| scripts/direct_video/styles.py（新） | 风格来源解析、继承/调整、设计失败重试一次、样张创建/修改/恢复、整镜匹配与字节复用、版本片段保留及老任务按需压片。 |
| scripts/direct_video/media.py | 关键帧生成同一步压出 clips/NN.mp4；360×640、30 fps、H.264、CRF 28、无音轨、faststart，按本镜帧数编码。 |
| scripts/direct_video/revisions.py | 切回旧版本时恢复该版本片段；该版本没有片段时撤下当前片段，防止读到另一版内容。 |
| studio/direct_video.py | 四列、短文案、source、fromDraft 投影；跨作品风格列表；样张服务与投影；片段读取；来源标题从当前作品读取，支持老任务。 |
| studio/direct_style_contract.py（新） | 风格、样张、片段路由与请求/响应契约；DirectStyleDraft schema。 |
| studio/server.py | 新路由分发；样张写操作返回 202；新增 400/404/409 错误映射；复用同源、CSRF、本机访问与媒体 Range。 |
| studio/api_contract.py | 合入新路由、字段与 schema。 |
| schemas/studio-openapi.json | 用 scripts/export_studio_openapi.py 重新生成，保持规范排序。 |
| tests/test_r278_style_base.py（新） | 风格来源、样张、四列、短文案、旧任务、安全、隐私与契约测试，共 61 项参数化用例。 |
| tests/test_r278_clips.py（新） | 3 项片段测试，使用合成小帧；不真调模型、不做 HTML 真渲染。 |
| tests/test_r276_direct_video.py、tests/test_r276_direct_api.py、tests/test_r276_direct_c.py、tests/test_r277_revisions.py | 必需的请求夹具、假设计响应和投影字段集合调整，逐处见第 4 节。 |
| evidence/2026-10-26/R278-direct-rescript/ | 红/绿测试日志、实测脚本与 JSON、媒体核验、源码哈希和 Git 状态。 |
| docs/tasks/R278-direct-rescript/REPORT-A.md | 本汇报。 |

未修改规则、模型网关、原始媒体、真实剪映草稿、Obsidian 创作内容或任何验收卡。

## 2. TASK 第 2 节完成情况

### 2.1 四列：完成

- visual、subtitle、camera、audio 按字符串去首尾空白后校验，空白保存为 null，非字符串或超过 2000 字返回 script_invalid。
- 原 script 调用继续可用，投影对老任务缺失字段返回 null。
- 定设计包含前三列，并要求 perShot.mainAction 根据画面确定。
- 初次写镜和 R277 重写均包含前三列及任务单指定的中文解释；颜色、字号遵循全片设计。
- audio 只保存，没有送入任何新增提示，也未进入媒体渲染或片段音轨。

### 2.2 短文案：完成

- 新定设计、沿用并改、样张均在同一次模型回复中生成 motionSummary、bannedShort。
- 与原设计字段一起校验；缺字段、长度/条数不合格、数字加单位、坐标或百分比等不合格时，最多重试一次。
- 沿用不改保留来源字段；老设计的短文案投影为 null。

### 2.3 风格来源：完成

- GET /api/direct/styles 跨当前作品收集 design.status=done 的任务；按创建时间降序，相同全片视觉字段只保留最新条目。
- 每次列表请求只批量读取一次作品表；没有逐条重新读取作品表。无数据库变更。
- posterUrl 选择镜号最小且关键帧存在的镜头，没有则为 null；返回可读取的相对 API URL。
- job 来源不改跳过定设计；改一句时传入原设计及意见，正常路径只调用一次模型定设计。后续各镜仍按正常写镜流程调用模型。
- draft 来源必须 ready；设计复制；第 01 镜的台词、画面、字幕/花字、景别/运镜全相同才复用，任一改变即重新写镜。音乐列变化不影响该匹配。
- 复用时对代码、关键帧做字节复制，已有片段也复制；fromDraft=true。任务创建时已固定来源快照，之后修改来源样张不会改写目标任务。
- design.source 带 inherited/adjusted/drafted、来源身份、作品标题与意见。
- 缺风格 400 style_required；来源不存在 404 style_base_not_found；样张未 ready 返回 409 draft_not_ready。

### 2.4 样张：完成

- 创建、查询、关键帧、修改接口均已接入；另提供样张 clip.mp4，使用同一媒体 Range 路径。
- 状态存在独立 direct-style-drafts/<projectId>/<draftId>/ 下，内部沿用 job.json、design.json、shots、posters、clips 和版本文件。
- 后台复用定设计 → 写一镜 → lint（失败重写一次）→ 渲染；样张不额外触发 R277 看图/核改模型调用。
- 投影含整镜 shot、dialogue、design、sample、failureCode、startedAt、revisions；rendering 映射为 writing。
- 写入中再次修改返回 409 draft_busy。原子状态持久化及重启后中断标失败、再次修改重试均有测试。

### 2.5 每镜小片段：完成

- 新镜及重新渲染都会同步压片；旧版本保留自己的片段，切换版本恢复对应文件，不会把另一版本帧误当成当前版本。
- 老任务缺片段但当前版本帧仍在时首次请求压片；缺帧或只有另一版缓存时返回 404。
- 路由支持 Range；合成小帧验证了尺寸、编码、无音轨、帧率、帧数、时长、faststart，以及 CRF 28 编码参数。
- 实测样张两版均实际压出片段并完整解码。

### 2.6 契约与兼容：完成，待总控处理受保护基线

- API 契约与生成的 OpenAPI 同步，新投影通过 schema 校验；字段及诊断递归脱敏。
- 写请求沿用 loopback、同源和 X-Content-OS-CSRF。
- 受保护测试改动已列明；未改卡片、binding、handoff 或人工记录，不代替总控执行 G16 rebaseline。
- 当前前端仍属旧版本，空风格建任务会按新后端契约返回 style_required；前端接线由下一段完成。

## 3. 测试与检查

先写了两份新测试文件，在修改业务实现前执行：

| 日志 | 实现前结果 |
| --- | --- |
| red-style.log | 54 failed，1.69 秒。包括四列未保存/未校验、缺少短文案校验、风格来源未实现、样张方法和路由缺失。 |
| red-clips.log | 3 failed，1.65 秒。包括渲染后缺片段、片段路由不存在、LocalMedia 缺 encode_clip。 |

随后扩展了 7 项边界用例，总计新增 64 项：风格/分镜 61 项，片段 3 项。其中老任务来源标题的独立失败证据在 red-legacy-title.log：原实现返回作品编号，修复后返回作品标题。

| 检查 | 最终结果 |
| --- | --- |
| 两份 R278 新测试 + tests/test_r276_*.py + tests/test_r277_*.py | **260 passed，91.52 秒，无失败、无跳过**；其中新增 64 项，既有专项 196 项。见 targeted-final.log。 |
| scripts/check_repository_safety.py --base origin/main | 通过；见 repository-safety.log。 |
| scripts/export_studio_openapi.py --check | 通过，导出内容与权威构建函数一致。 |
| git diff --check | 通过。 |
| 新增/改动文件补充扫描 | 28 个文件的文件策略、运行时路径和新增证据本机路径扫描无失败；原有 .venv 软链不纳入。见 untracked-safety.json。 |
| 两版实测 JPEG/MP4 | 图片解析、完整视频解码、媒体参数、faststart、SHA-256 一致性均通过。见 media-verification.json。 |

专项 pytest 命令：

~~~sh
.venv/bin/python -m pytest -q \
  tests/test_r278_style_base.py tests/test_r278_clips.py \
  tests/test_r276_*.py tests/test_r277_*.py
~~~

按 TASK 第 5 节设置 VIDEO_RENDER_PLAYWRIGHT_MODULE、VIDEO_RENDER_BROWSER。新测试模型全部是假生成器；既有专项中的 Claude 传输测试使用假可执行文件。

没有跑全量 pytest、没有起交互浏览器或前端截图流程。既有真实 HTML 渲染测试及第 4 节实测使用现有渲染器所需的 headless Chromium。

证据文本中的本机路径已归一化；完整原始诊断日志保留在仓库外的本任务证据目录 diagnostic-raw/。源码哈希及两仓库状态记录见 verification-summary.json。

## 4. R276/R277 受保护测试逐处变更

下表列出所有直接改动点；公共夹具对其调用用例的影响也在此明确说明。没有删除测试、减少用例、改宽容条件或移除原有行为/隐私断言。

| 文件 | 用例或夹具 | 变更与原因 |
| --- | --- | --- |
| tests/test_r276_direct_video.py | design(rows) 公共假设计夹具 | 补 motionSummary、bannedShort。新模型响应必须包含它们，否则所有依赖 FakeModel 或假 CLI 的合法设计都会失败；原有字段不变。 |
| 同上 | ready(...) 公共建任务夹具 | 补 style，满足现在必需的风格条件；影响使用该夹具的 R276/C/D 用例，原测试目标不变。 |
| 同上 | test_default_gateway_with_fake_executable_generates_job | storyboard 建任务补 style，保留网关真实调用假可执行文件及响应耗尽断言。 |
| 同上 | test_failed_design_and_model_timeout_are_bounded：无效设计分支 | 建任务补 style，使测试继续到达 design_invalid 分支。 |
| 同上 | test_failed_design_and_model_timeout_are_bounded：写镜超时分支 | 建任务补 style，使测试继续到达 model_timeout 分支；单镜尝试次数断言不变。 |
| 同上 | test_busy_job_and_projection | 精确字段集合增加 visual、subtitle、camera、audio、fromDraft；继续精确核对完整集合、忙碌错误及路径不泄露。 |
| tests/test_r276_direct_api.py | create(api) 公共 HTTP 建任务夹具 | 补 style；影响引用它的 R276/R277 HTTP 用例，HTTP 状态、轮询和原断言不变。 |
| tests/test_r276_direct_c.py | test_writing_clock_updates_on_each_model_attempt_and_survives_restart | 建任务补 style；逐次写入时钟、重试及重启断言不变。 |
| tests/test_r277_revisions.py | ready_image 公共夹具 | 补 style，保证假可执行文件链路继续获得合法任务；版本、图片、核改与隔离断言不变。 |
| 同上 | test_samples_copy_survives_job_deletion_and_two_prompt_examples：project2 | 建任务补 style；样例复制与提示数量断言不变。 |
| 同上 | test_samples_copy_survives_job_deletion_and_two_prompt_examples：project3 | 建任务补 style；同上。 |
| 同上 | test_legacy_projection_fields_and_privacy | 新字段集合增加 visual、subtitle、camera、audio、fromDraft；原字段集合和逐字段值仍必须完全相等，隐私/schema 断言仍保留。 |

补风格以外的必要调整只有：合法假模型响应增加必需短文案，以及两个投影白名单容纳明确新增字段。R277 之所以也需改，是其直接创建任务的夹具未带风格，且有精确字段集合断言。所有直接改动已逐处披露，供总控核对后处理相关受保护卡。

## 5. TASK 第 4 节：唯一一次真实实测

直接调用 DirectVideo 服务层，没有起 HTTP Studio 服务。临时状态、代码、关键帧和 MP4 全在仓库外独立目录：

~/.photo-content-os/evidence/R278-direct-rescript/live-5z2bi1gp/

模型走产品原入口 llm_common.generate_text → claude_cli → claude-opus-5-5，登录目录沿用 ~/.claude-account3；没有修改账号设置、模型网关或替换模型/渲染响应。

输入严格使用任务单风格原文，shot 只提供《断更一年，我拆了四句话》第 01 镜台词及 shotId=01；没有带入上游画面、字幕或音乐列。首次 ready 且读取文件后，仅修改一次「主色再深一点」。

| 步骤 | 定设计 | 写代码 | 渲染及压片 | 端到端耗时 | 模型调用 | 结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 首次样张 | 20.359 秒 | 160.806 秒 | 33.949 秒 | 215.621 秒 | 2 | ready，关键帧和 clips/01.mp4 可读 |
| 修改样张一次 | 10.352 秒 | 124.978 秒 | 33.106 秒 | 168.813 秒 | 2 | ready，posterRevision 从 1 变 2，两文件已更新 |
| 合计 | | | | 384.434 秒 | **4** | 无额外样张、无自动代码重试 |

- 修改后主色由 #0E5A63 变成 #08424A；其余色板、字号和短文案保持。
- 两版自查均无 error；均有非阻塞 number_unspoken 提醒：「画面数字 0% 未出现在本镜口播，请核对出处和数量。」未把该提醒隐去，也未为它额外调用模型。
- 初版 JPEG 48,780 字节、MP4 130,272 字节；修改版 JPEG 55,597 字节、MP4 93,629 字节。各文件 SHA-256 在 live-result.json。
- 两版 JPEG 都为 360×640；片段都为 H.264、360×640、30 fps、546 帧、18.2 秒、单视频流、faststart。用 FFmpeg 完整解码通过，没有音轨。
- 两次的关键帧和片段另存 inspected-artifacts/initial-*、inspected-artifacts/revised-*，仓库里没有图片、视频或帧。
- 实测进程正常退出，exit code=0；临时状态目录下 cache 已删除，剩余 frame-*.png 数为 0。
- 全程检查磁盘可用空间，未低于 3 GiB；收尾约 6.9 GiB。
- 此次证明服务层样张生成、修改、真实模型与真实渲染/压片；未声称真实 HTTP 前端流程或视觉效果已获人工验收。

证据：live_sample.py、live.log、live-result.json、media-verification.json。

## 6. 总控需处理的事项与范围

1. 按 G16 核对上面的 R276/R277 测试修改，并对相应受保护基线重新绑定及复核；本执行段没有自行改任何验收记录。
2. R276/R277 的相交阻塞项在开工时都是 PENDING，本段不作人工通过或发布 READY 声明。
3. 真实样张的 0% 提醒留给总控结合画面判断，属于已有非阻塞数字提醒；本段未扩大为语义判断修复任务。
4. 前端、设计合同采集、页面截图、R282 交接和 R283 风格库均未做，按任务边界留给后续段。

后端任务单第 2 节没有遗留实现项。没有需要本段额外决策才能继续的后端问题；受保护基线及前端/人工验收由总控继续。

## 7. Git 与 Harness 状态

- 业务项目 HEAD 仍为 107b56e，工作区有上述未提交修改与新增文件；未暂存、未提交、未推送。已有 .venv 软链保留原状。
- Harness SSOT：本任务没有修改任何 Harness 文件。收尾读取该仓库状态有 57 条既有/并行工作项，未清理、回退或提交。
- 完整状态和 14 个 Python 源码/测试文件哈希已存 verification-summary.json。
- 本段只产生实现、测试、普通证据和汇报，没有创建或修改声明的 agents-results SSOT 开发包。
