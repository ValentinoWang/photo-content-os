# R277 A 段后端汇报

日期：2026-10-26。以本 worktree 的 TASK.md 第 0、2、4 节及交接 3 为准，起点 `90875ba`。第 2 节后端实现及 2.6 测试已执行；**仍有一项旧测试与新增字段要求冲突，不能声称全部门禁通过或项目 READY**。本阶段到此停止，不开始 B/C。

仅在指定 worktree 修改。`studio/static/` 零改动，R276 旧测试零改动；没有提交、推送、回退、创建其他 worktree、停止他人进程或操作端口 8765。预置 `.venv` 链接保留。没有修改主目录或 R276 worktree。测试服务均在系统分配的临时端口，关闭自己的服务后清理临时状态。

## 1. 第一关：后台 Opus 看图实测

先改 `llm_common.generate_text_with_claude_cli` 图片分支，真实调用成功后才继续其他后端实现。

- 入口：`generate_text(provider='claude_cli', model='claude-opus-5-5', image_paths=[关键帧], …)`。
- 用 `subprocess.Popen(..., stdin=DEVNULL, stdout=日志, stderr=STDOUT, start_new_session=True)` 启动独立 Python 后台进程；与 Studio 一样由普通无 TTY 子进程调用统一入口，没有使用 shell 函数。stdinTTY、stdoutTTY 均为 false。
- 可执行文件：继承环境中真实 `claude`，即 `~/Desktop/Opensource_Tool/npm-global/bin/claude`；账号继承 `CLAUDE_CONFIG_DIR=~/.claude-account3`，未改账号配置。
- 图片：R276 frontend-f2 第 02 镜关键帧；原文件仍在仓库外。输入 SHA-256 见 `opus-image-probe.json`。
- **成功，用时 6.451 秒**。Opus 描述了「发出去，会被人看低」、经典实验、橙色约 50% / 青色约 25% 两柱，以及「没有人在等我宣布回归」。已查看输入图片，描述与实际画面一致。

图片分支实际 argv（提示与图片均不进 argv）：

```sh
claude -p --output-format stream-json --model claude-opus-5-5 \
  --safe-mode --setting-sources '' --tools '' \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --no-session-persistence --input-format stream-json --verbose
```

在空临时目录运行，继续移除子进程 `CLAUDECODE`，保留原超时与 `OPENCLAW_CLAUDE_CONFIG_DIR` 处理。无图时原来的 argv、文本 stdin、JSON 结果解析保持不变。有图时先经 `validated_image_paths`，每图转一个 base64 image block，末尾附 text block，一行 stream-json user message 写入 stdin。stdout 逐行解析，取最后一个 `type=result` 的 `result`；非零退出、超时、坏 JSON、无结果、空结果、is_error 均抛不含提示原文的 `LLMError`。未开放工具、目录读取或 MCP；此次实测未单独落盘 CLI 的原始事件流，不能把假模型测试的 permission_denials 当成真实事件证据。

证据目录：`evidence/2026-10-26/R277-shot-visual-revision/`，含 `probe_opus.py`、`opus-image-probe.json`、`opus-image-probe.log`。图片仍引用仓库外 R276 证据，未拷进 Git。

## 2. 改动文件与行为

| 文件 | 本段变化 |
| --- | --- |
| `scripts/llm_common.py` | 仅为 Claude 入口增加图片 stream-json 分支；统一出口不变。 |
| `scripts/direct_video/generate.py` | 接入版本、图片自查/核对、样例提示和用户规则；旧任务按需迁移；配音与合成使用选中代码；恢复中断的看图状态。 |
| `scripts/direct_video/revisions.py`（新） | lines 校验、多版本保存/退回、look、逐条 verify、样例命令、规则草稿调用。 |
| `scripts/direct_video/revision_library.py`（新） | 跨作品样例库、问题记录、规则提案和采用层；原子 JSON 写入，读坏不当成空库。 |
| `scripts/direct_video/media.py` | 复用已渲染帧生成 .3/.6/.9D 三张小 JPEG；读取同一渲染器采集的 boxes。 |
| `scripts/video_render/render-frames.mjs` | 在与海报同一帧采集 `[id],[data-s]` 的实际 DOM 坐标、可见性和中文名称。 |
| `studio/direct_video.py` | 5 个新增单镜投影字段、命令适配、规则/样例列表、版本化媒体读取和路径脱敏。 |
| `studio/server.py` | 注册接口分派、PUT/DELETE 支持、沿用 loopback/同源/CSRF、受控错误状态。 |
| `studio/direct_revision_contract.py`（新） | R277 请求、投影和路由合同；供 canonical api_contract 引用。 |
| `studio/api_contract.py`、`schemas/studio-openapi.json` | 增量登记新合同；OpenAPI 由 build_openapi 生成，保留原排序格式。 |
| `tests/test_r277_revisions.py`、`tests/test_r277_api.py`、`tests/test_r277_boxes.py`（新） | 共 50 项，状态/假可执行模型/临时 HTTP/真实浏览器 DOM 与媒体检查。 |
| 本汇报及 `evidence/2026-10-26/R277-shot-visual-revision/` | 普通报告、文本证据、可复跑探针和合成接口示例；未创建 SSOT 开发包。 |

预置 TASK、design、需求卡保留原样，不算本轮重新设计或修改。

### 版本与恢复

- `currentVersion=0` 表示尚无写好代码；第一次写好代码是第 1 版。每次真正产出新代码分配递增版本，lint 自动修复的候选单独保留在原 code-attempts，不冒充两个已生成版本。
- 私有版本目录：Studio 状态根下 `direct-jobs/<作品>/<任务>/versions/<镜号>/<版号>/`，有 `code.html`、成功后的 `poster.jpg`、`checks.json`、`review.json`。版本元数据在 job.json。渲染失败的新代码仍保留为一版，不复制旧海报冒充新版。
- 退回复制选中代码/关键帧并恢复该版的 `posterRevision`、`codeChars`、`checks`、`writtenAt`、`attempts` 等字段；版本不删除。新版本的 posterRevision 从已有各版最大值递增，避免退回后重写复用编号。
- 退回和重写都令 `output.status=none`，清空旧时长/帧数/检查摘要。退回后合成若发现帧缓存属于另一版，会按当前选中代码重渲；配音重算也读取当前代码。
- 配音时长改变但无需重写的重渲同样保存新版本，避免覆盖旧关键帧。
- R276 旧任务第一次读取时保存现有代码为第 1 版，不编造原先不存在的 look/boxes。第一次请求 look 时可从原代码重渲补齐三帧和 boxes。读取 latest 只迁移选中的最新任务，不批量迁移历史任务。
- 保留 R276 整任务互斥：同任务已有后台动作时，四类镜头动作均返回 job_busy；这是比“同镜互斥”更严格的原有边界。合成中的持久化状态同样拒绝修改。没有新增跨镜同时修改能力。

### 块与图片判断

1080×1920，海报帧索引为 `min(N-1, floor(.8*N))`，boxes 就在该帧量。排除自己或祖先的透明度 0、display:none、不可见、零宽高和完全在画布外的元素。文字去多余空白、前 12 个 Unicode 字符加「」；SVG 图形优先同横向范围上方的文字，再按距离选邻近文字；rect 后接“柱子”，其余接“图形”；取不到为“第 N 块”。重复元素标识分配独立后备 ID。

真实 Chromium 对 R276 设计稿第 02 镜原代码测得 `b1` 名称「约 50%」柱子、`b2` 名称「约 25%」柱子，并检查了祖先透明、隐藏、零尺寸、12 字截断、后备名称和运动后的坐标。

渲染后自动 look：三张实际 JPEG + 全片设计 + 口播 + boxes，只接收最多 5 个合法 finding。revise/rewrite 后再发三帧与原始 lines 自动核对；必须按 index 完整返回，每项只能 done/missed，missed 必须有原因。分别写到对应版本；任一图片判断失败只写 look_failed / verify_failed，镜头的渲染、lint 和检查结果不因此失败。重启中断 look 时也保留渲染成功。

### 样例、计数、规则

- `direct-samples/<sampleId>/code.html`、`poster.jpg` 为独立复制，`index.json` 存作品、任务、镜号、版本、时间、口播、主动作。删掉原任务后仍能读取、参考样例。
- 选样例用“口播 + 主动作”的字符二元组集合 Jaccard 重合度（交集/并集），最高 2 个；无样例不附字段。提示附代码和两张以内的样例图；图在任务自己的 sample-context 里再作一次快照，防止另一个请求取消样例导致输入消失。
- revise 接受后逐条记问题；main/dim → 主次不清，del/short → 字太多，space/color/sync 分别对应任务单类别。own 不计类，校验拒绝或未发送不记。旧 rewrite 的单条 own 同样不计类。
- 每类累计达到 3 条发出要求时让 Opus 起草；之后该类每新增 3 条可出下一份草稿，拒绝不清次数。草稿状态 running/pending/adopted/rejected/failed，失败不激活。
- 规则状态保存在 `direct-rules/state.json`：revision、rules、proposals、issues。采用 pending 草稿才使 revision +1 并追加规则；重复采用同一草稿幂等；与另一决定冲突返回 proposal_not_ready。拒绝只改状态。
- 生成时将仓库 `rules/shots.md` 和用户层合并。**没有改仓库 shots.md**；已有镜头不因采用规则自动重写。

## 3. 接口与字段的实际形状

完整的真实 HTTP 响应示例在证据 `api-examples.json`，由 `capture_api.py` 在隔离临时 Studio 中生成；内容和模型都是合成测试数据，只有第 1 节图片探针是真 Opus。示例含 initial、reviseAccepted、revised、logPending、adopted、reverted、sampleSaved、samples、sampleImage；样例图片接口返回 200、image/jpeg，哈希在该文件内。

所有写接口沿用 loopback、CSRF 和与当前 Host 同源。成功返回 200；各镜命令包装统一为 `{"ok":true,"job":{…}}`，后台动作的返回表示已接受，随后轮询 job 查看完成。

| 方法与路径（项目/任务/镜号略为 P/J/S） | 请求 | 响应补充 |
| --- | --- | --- |
| POST `/api/projects/P/direct/jobs/J/shots/S/revise` | `{"lines":[{"text":"柱子变灰","boxId":"b3","action":"dim"},{"text":"简化颜色","issue":"color"},{"text":"底色不动","own":true}]}` | 加一版并自动 look、verify。每条非空，合计原文 1–200 Unicode 字符；selector 必须且只能有一种，拒绝未知块/动作/字段。 |
| POST 同镜 `/current` | `{"version":1}` | 同步切换；不调模型、不删版本、旧成片撤下。不存在或非整数版本 404。无成功关键帧的失败版本不能作为退回目标。 |
| POST 同镜 `/look` | `{}` 或空 body | 接受后 look.running，后台完成为 done/failed；不令旧成片失效。 |
| PUT 同镜 `/sample` | `{}` 或空 body | 当前版本存为样例，sample=true；重复保存不增副本。 |
| DELETE 同镜 `/sample` | `{}` 或空 body | 取消当前版本样例，sample=false；不删除镜头版本。 |
| GET `/api/direct/revision-log` | 无 | `{"ok":true,"rulesRevision":0,"categories":[{"category":"主次不清","count":3,"sources":[…],"proposals":[…]},…]}`。固定包含五类，零计数也返回。 |
| POST `/api/direct/rules/proposals/{proposalId}/adopt` | `{}` 或空 body | `{"ok":true,"proposal":{…,"status":"adopted"}}`；规则版号从日志取。 |
| POST 同草稿 `/reject` | `{}` 或空 body | `{"ok":true,"proposal":{…,"status":"rejected"}}`；规则不变。 |
| GET `/api/direct/samples` | 无 | `{"ok":true,"samples":[{"sampleId":"sample_…","projectId":"…","jobId":"…","shotId":"01","version":1,"projectTitle":"合成测试","savedAt":"…","dialogue":"…","mainAction":"…","posterUrl":"/api/direct/samples?poster=sample_…"}]}`。 |

不新增媒体路由，使用两个增量查询参数：

- 原 `/shots/S/poster.jpg?version=1` 和 `/shots/S/code?version=1` 读取保留的旧版，供两版对比；不传 version 仍读当前版。原有查询写法不受影响。
- `/api/direct/samples?poster={sampleId}` 返回样例库独立复制的 JPEG；不传 poster 返回列表。两者均已写入 OpenAPI。

`revision-log.sources[]` 实际字段为 `category,text,projectId,projectTitle,jobId,shotId,submittedAt`；一次实际发出的一条要求对应一条记录。`proposals[]` / 采用响应内的实际字段为 `proposalId,category,throughCount,status,text,failureCode`。throughCount 表示起草覆盖到的累计条数；用户可以看到 failed 草稿，未读到库文件不会显示成零问题。

单镜仅追加这 5 个字段，R276 的 16 个字段均仍在；其中 writingStartedAt 的缺省兼容仍保留：

```json
{
  "currentVersion": 2,
  "versions": [
    {"version": 1, "createdAt": "…", "posterRevision": 1, "codeChars": 4320, "request": null, "verify": null},
    {"version": 2, "createdAt": "…", "posterRevision": 2, "codeChars": 4360,
     "request": {"lines": [{"text": "柱子变灰", "boxId": "b3", "action": "dim"}, {"text": "底色不动", "own": true}]},
     "verify": {"status": "done", "items": [{"index": 0, "result": "done", "reason": ""}, {"index": 1, "result": "missed", "reason": "底色还发生了变化"}]}}
  ],
  "boxes": [{"id": "b3", "name": "「约 25%」柱子", "x": 580, "y": 886, "w": 300, "h": 316}],
  "look": {"status": "done", "failureCode": null, "findings": [{"boxId": "b3", "kind": "主次", "text": "次要柱子抢眼", "suggest": "dim"}]},
  "sample": false
}
```

上段为形状示意，时间与数值以 `api-examples.json` 的实际响应为准。verify 失败的实际形状为 `{"status":"failed","failureCode":"verify_failed","items":[]}`；look 失败为 `{"status":"failed","failureCode":"look_failed","findings":[]}`。

错误与修复归属：

| failureCode | 落点 / HTTP | 处理方 |
| --- | --- | --- |
| look_failed | 单镜 look.failureCode；命令已接受时仍 200 | 后台模型/帧读取失败，可重新 look；不能显示成“没有问题”。 |
| verify_failed | 对应版本 verify.failureCode；命令已接受时仍 200 | 后台核对失败，不能显示成“全部做到了”。 |
| version_not_found | 写命令/旧版媒体 404 | 选择不存在版本，刷新版本列表。 |
| instruction_too_long | revise 400 | 用户把合计原文缩到 200 字以内。 |
| instruction_invalid | revise 400（沿用旧码） | 空内容、未知字段/块/动作、互斥 selector 等请求合同错误。 |
| sample_not_found / proposal_not_found | 库查询或决策 404 | 刷新对应列表。 |
| proposal_not_ready | 决策 409 | 草稿尚在起草、已作不同决定或已失败，不可再作为 pending 采用。 |
| job_busy / shots_not_ready | 沿用 409 | 等后台动作完成，或先恢复可用镜头；不排队执行冲突操作。 |

本段按约束不改前端失败映射；B 段需要接上以上新状态和失败码，尤其不能把 look/verify 失败画成空结果或成功。

## 4. 测试命令与结果

固定使用 worktree 的 `.venv/bin/python`。渲染配置沿用交接 3：

```sh
export VIDEO_RENDER_PLAYWRIGHT_MODULE="$HOME/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js"
export VIDEO_RENDER_BROWSER="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell"
export VIDEO_RENDER_TEST_BROWSER="$VIDEO_RENDER_BROWSER"
export OBSIDIAN_ROOT="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/自媒体"
export UI_COPY_QUALITY_CHECKER="$HOME/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/ui-copy-quality/scripts/check_ui_copy_quality.py"
```

| 命令 | 结果 / 文本证据 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_video.py tests/test_r276_direct_api.py tests/test_r276_direct_c.py tests/test_r276_direct_frontend.py tests/test_r276_direct_media.py tests/test_r277_revisions.py tests/test_r277_api.py tests/test_r277_boxes.py --junitxml=evidence/2026-10-26/R277-shot-visual-revision/pytest-focused.xml` | **177 passed、1 failed**，78.66 秒。R277 **50/50 通过**，真实浏览器未跳过。唯一失败见下一节。`pytest-focused.log/xml`。 |
| `.venv/bin/python -m pytest -q tests/test_r277_revisions.py tests/test_r277_api.py` | **48 passed**，61.56 秒，含图片传输所有错误分支；另 2 个真实浏览器测试计入上行。`pytest-r277-final.log`。 |
| 最后局部改动复验：`.venv/bin/python -m pytest -q tests/test_r277_revisions.py::test_restart_during_look_preserves_render_success tests/test_r277_api.py::test_revision_routes_artifacts_samples_and_privacy tests/test_r277_revisions.py::test_samples_copy_survives_job_deletion_and_two_prompt_examples tests/test_desktop_openapi_route_sync.py` | **4 passed**，6.95 秒；覆盖最后的恢复细节、样例输入快照、latest/HTTP 与 OpenAPI 同步。`pytest-last-change.log`。 |
| `.venv/bin/python -m pytest -q tests --junitxml=evidence/2026-10-26/R277-shot-visual-revision/pytest-full.xml` | **1010 passed、25 skipped、10 failed、6 errors、2003 subtests passed**，232.98 秒。含 llm、api_contract/server、video_render 等现有测试。此轮收集了当时的 40 项 R277 测试；后续补充的 10 项及最后小改动由上面专项覆盖，未冒称全量已重跑到最终代码。 |
| `bash scripts/check_runtime_contract.sh` | PASS，含编译/环境/编码/隐私检查。 |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | PASS，收尾再次通过。 |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | PASS，显式配置 Core 文案检查器。 |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | FAIL，既有三组 source-newer-than-target；未改配对文档、未弱化 marker。 |
| `.venv/bin/python scripts/check_outline_contract.py .` | FAIL，调用同一 doc-sync 门禁而失败。 |
| 两个 validate 脚本 `--help` | `validate_content_os_task.py`、`validate_jianying_draft.py` 均 PASS。 |
| `node tests/test_r276_direct_frontend.mjs` | PASS。 |
| `.venv/bin/python <Core>/scripts/quality/check_ai_egress_ownership.py --runtime-root scripts --gateway scripts/llm_common.py` | PASS。初次把 runtime-root 写成 scripts/direct_video，检查器因 gateway 不在根下拒绝；改正范围后通过，没有放宽 checker。日志两份均保留。 |
| Python 编译、`node --check scripts/video_render/render-frames.mjs`、`git diff --check` | PASS。 |

2.6 要求的覆盖全部有对应测试：多版本/不删旧版/回退字段/撤下输出/当前版合成和配音；同镜动作与合成互斥；样例独立复制及最多两个提示；两层规则；第 02 镜 boxes 与命名；lines 校验与 1/200/201 字边界；看图失败隔离；verify 落对应版本；按条计数、own 不计、未发送不计；3 次起草、采用前不生效、采用幂等、拒绝留次数；路径脱敏与旧字段值不变。测试没有真实调用模型，唯一真实调用是第一关探针。

## 5. 全量 10 个失败、6 个错误逐项判断

本轮原因分类有证据，不将所有失败概括为“都与本任务无关”。`pytest-full.xml/log` 保存每条完整堆栈；`unchanged-failure-sources.txt` 确认相关既有测试和源文档未改。R276 REPORT-A/B/F2 也记录相同 FFmpeg/文档同步类别。本轮另做了 `ffmpeg-filters.log` 和 `ffmpeg-negative-probes.json`：当前 ffmpeg 没有 drawtext/subtitles/ass；最小 drawtext 调用直接报 `No such filter: 'drawtext'`、退出 8。

| 全量项目 | 判断 |
| --- | --- |
| `test_bilingual_subtitles_r6.py::BilingualCaptionTests::test_real_two_layer_burn` | 既有 FFmpeg 字幕烧录路径，filter_complex_script 退出 8；本轮没改该功能或测试。判为环境能力缺失。 |
| `test_direct_video_subtitles.py::RenderedSubtitleTests::test_chinese_glyphs_do_not_fall_back_to_identical_missing_glyph_boxes` | 同上，合成测试字幕烧录时退出 8，不是新镜头 renderer 或 boxes 的失败。 |
| 同类 `test_real_cut_first_frames_80166667_and_122866667` | 同上，字幕烧录前置失败，未进入帧内容断言。 |
| 同类 `test_white_text_has_a_dark_backplate_on_white_and_black` | 同上，字幕烧录前置失败。 |
| `test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies` | 三组 source-newer-than-target，与独立 doc-sync/outline 结果相同；checkout 文件时间晚于 Obsidian 目标。源文档未改，判为既有同步/mtime 问题。 |
| `test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_black_native_frames_fail_even_with_burned_subtitles` | 既有 pipeline 在 captions.filters 烧字幕时退出 8；本轮未改该路径。判为 FFmpeg 环境。 |
| 同类 `test_dark_design_with_a_few_dots_is_not_a_black_frame` | 同上；在字幕生成前置阶段失败，没有到黑帧判断本身。 |
| 同类 `test_dark_design_with_a_small_white_header_is_not_a_black_frame` | 同上。 |
| 同类 `test_uniform_deep_gray_has_no_content_and_fails` | 同上。 |
| `test_r276_direct_video.py::test_busy_job_and_projection` | **本任务增量字段导致的明确合同冲突**：旧断言要求字段集合完全等于旧 16 项，新需求必须追加 currentVersion、versions、boxes、look、sample。原测试保留，未删字段绕过；R277 另测旧字段集合和值完整保留。需总控决定如何调整该旧断言及受保护合同。 |
| `test_pf_video_pipeline.py::FrameMappingTests::test_alpha_and_geometry_have_exact_pixel_bounds`（ERROR） | setUpClass 的合成视频命令带 drawtext，当前 ffmpeg 退出 8；未进入测试主体。判为环境。 |
| 同类 `test_changed_source_fails_projection`（ERROR） | 同一 setUpClass 前置失败。 |
| 同类 `test_editable_document_structure_and_neutral_producers`（ERROR） | 同一 setUpClass 前置失败。 |
| 同类 `test_every_frame_matches_retained_source_clock`（ERROR） | 同一 setUpClass 前置失败。 |
| 同类 `test_projection_checks_preview_waveform_and_no_local_paths`（ERROR） | 同一 setUpClass 前置失败。 |
| 同类 `test_real_silence_envelope_has_no_simulated_peaks`（ERROR） | 同一 setUpClass 前置失败。 |

以上环境归因基于堆栈、缺失滤镜实测、未改动文件和 R276 报告，没有在另一份全量基线 checkout 重跑；因此不把它写成已完成全仓基线对照。没有安装/替换 ffmpeg、改用户 Obsidian 页面、放宽测试或更新旧验收摘要。

## 6. 待总控处理与明确边界

1. **需要拍板：旧投影测试**。`tests/test_r276_direct_video.py:340` 的 exact-set 断言与批准的“只加字段”要求不能同时成立。建议由总控按受保护测试流程把该处改成“旧字段必须完整存在并保持原值，允许批准的新增字段”；本轮未修改它，也不在此擅自重绑旧验收卡。
2. B/C 前端、实际 H-01–H-03 流程和截图未做。没有启动用户的作品任务，没有对生产状态运行自动迁移，没有真实跑全套三帧自查/重写/规则起草；这些后端路径的机器证据来自假可执行模型，图片传输可用性已由第一关真 Opus 验证。
3. B 段请使用版本化 poster/code 查询参数做两版比较，接上 sample 列表的 posterUrl，并覆盖新失败码。预览仍是 JPEG，没有添加播放/拖帧能力。
4. 起草按每新增三条同类要求执行；一次拒绝不清次数、下一组三条再出草稿。若希望“拒绝后立即重起同一份草稿”或不同镜同时修改，属于尚未规定的交互，本轮未扩展。
5. 开场人验机器日志里 R220 的 studio.shot-review / studio.navigation 仍为 PENDING，与入口相交；未代签、修改或降级旧人验，也未宣告 R277 人验完成。A 段不具备整卡绿色前端/人验条件，未写冒充完整交接的 handoff。
6. 本报告与证据是普通任务文件，不是 `agents-results/<date>/<bundle>/` 声明式 SSOT，无 ssot-archive.json，不触发 Obsidian SSOT 快照或提醒。

## 7. Git 与收尾状态

- 业务仓库：8 个既有代码/schema 文件修改；新增 3 个后端模块、3 个测试模块、REPORT-A 和文本证据。完整 `git status --short` 见 `business-git-status.txt`。任务单/设计/需求卡与 `.venv` 是开场已有的未跟踪输入，未清理。`studio/static/`、R276 测试均无 diff。没有提交或推送，工作保留给总控审阅。
- Harness SSOT：本轮零修改。完整状态见 `harness-git-status.txt`；其中其他会话已有的未提交内容保留，未回退。
- 项目声明的 `develop/harness/fullstack-ai-harness.md` 在稀疏 worktree 中不存在，已读 Core 权威全文与项目 overlay，没有创建替代副本或修改 Core 规则。

按本阶段约定停止。
