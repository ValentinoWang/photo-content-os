# R276 第三段 C 汇报

日期：2026-10-26。第 1、2 项已完成；第 3 项提醒通道已实现，但真实 B 样本“至少 10 张报提醒”的验收条件未满足，保留为未关闭事项。127 项 R276 测试与 47 项相关既有测试通过，不将单元测试通过写成该真实样本条件已通过。

本阶段没有提交、推送、启动 Studio 或调用真实模型；没有访问 8765。`studio/static/` 和 `tests/test_r276_direct_frontend.*` 完全未改，20 个文件的前后 SHA-256 相同。

## 1. writingStartedAt

- 新任务每镜都有 `writingStartedAt`：未开始时为 `null`，开始写时为 UTC ISO 字符串。
- 首次、lint 自动重写、按意见重写、失败/中断重试、配音后重写，每次模型调用前都会刷新到最近一次开始时间。
- 写完、渲染、失败、中断和重启后均保留最近值；只有重渲而不写代码时不刷新。
- rewrite 返回时即提供本次开始时间，实际模型开始时再次更新，前端可以直接据此计时。
- 老任务从未记录过开始时间时，投影补 `null`，不根据 writtenAt 或耗时倒推历史时间。B 阶段原任务和媒体文件保持只读。

涉及 `scripts/direct_video/generate.py`、`studio/direct_video.py`，并在 OpenAPI 的每镜必备字段中声明 nullable `date-time`。

## 2. 不带意见重试

`POST /api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/rewrite`：

| 当前镜头状态 | instruction 规则 |
| --- | --- |
| `failed`、`interrupted` | 可省略、空字符串、空白字符串或 null；也接受正常的 1–200 字意见 |
| 其他状态 | 必须有非空意见，原请求不超过 200 字符，去除首尾空白后非空 |
| 所有状态 | 非字符串/非 null、超过 200 字符均拒绝 |

没有请求体与 `{}` 等效。仍保留设计完成、任务不忙、项目和镜头存在等原先约束。

空意见重试保留上一条实际修改意见；有原代码时提供原代码。失败镜头上一次 `checks.errors` 原样交给 Opus，即使从未成功保存过 HTML 也可重试。一次重试沿用既有 lint 自查机制；构图 warning 不会启动该机制。其他镜头的代码、海报和时间字段保持不变。

## 3. 构图提醒实现及真实样本差异

新文件 `scripts/direct_video/layout.py` 参考用户技能 `direct-video-shots/scripts/preview_frames.py` 的 CONTENT_BOX 和 30% 规则。关键帧 JPEG 生成后测量，结果接入 `checks.warnings`，错误列表不变：

```json
{"code":"layout_bottom_gap","message":"画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%"}
```

量法：

1. 从关键帧四边采样，取 RGB 中位数作为背景；使用 3×3 中值过滤抑制 JPEG 孤立噪点。
2. 对齐原画布 1080×1920，检查 y=200–1500，两侧各留 72px。1500 是参考脚本为 y=1536 字幕带预留 36px 后的边界。
3. 检出与背景明显不同的可见像素行，以最后一行换算内容下沿。30% 指 `(1500 - 下沿) / (1500 - 200) > 0.30`。
4. 图片无法读取、比例不符或背景边缘明显不稳定时记 `unmeasurable` 及原因，私有证据不报成“测量通过”；测量未知时保留上次已测得的提醒。
5. 结果保存在本机任务 `checks/layout/NN.json`，提示同时保存至 `checks/NN.json` 和任务投影。只在渲染之后加入提醒；新一次测量替换旧的同码提醒，不累积重复。新提醒不会触发自动重写。

### 真实 B17 逐张结果

以下测量读取 B 的最终 10+7 张海报，所有原文件 SHA-256 在测量前后相同；没有修改 B 成片、海报或 job.json。

| 跑次/镜 | 内容下沿 y | 下方空白 | layout_bottom_gap |
| --- | --- | --- | --- |
| b1-01 | 1443 | 4.4% | 无 |
| b1-02 | 1434 | 5.1% | 无 |
| b1-03 | 1434 | 5.1% | 无 |
| b1-04 | 1500 | 0.0% | 无 |
| b1-05 | 1443 | 4.4% | 无 |
| b1-06 | 1476 | 1.8% | 无 |
| b1-07 | 1485 | 1.2% | 无 |
| b1-08 | 1482 | 1.4% | 无 |
| b1-09 | 1209 | 22.4% | 无 |
| b1-10 | 1398 | 7.8% | 无 |
| b2-01 | 1500 | 0.0% | 无 |
| b2-02 | 1500 | 0.0% | 无 |
| b2-03 | 1500 | 0.0% | 无 |
| b2-04 | 1500 | 0.0% | 无 |
| b2-05 | 1500 | 0.0% | 无 |
| b2-06 | 1485 | 1.2% | 无 |
| b2-07 | 1410 | 6.9% | 无 |

结果：**17 张可测，0 张超过 30%，0 张不可测**；“至少 10 张”未达到。逐张路径、SHA-256、背景 RGB、内容下沿和比例见 `c-b17-layout-regression.json`，其中 `minimumMet=false`。

最大空白比例为 22.4%（B1-09）。即便将判断边界从 1500 改为字面的 1536，基于已检出的下沿，空白比例上界也只有 **24.5%**，仍不到 30%。

具体原因：参考脚本把页眉以外的可见文字、图形都算作内容。B1-02 的柱形条到约 y=1173，图下注释到约 y=1434；B2 多张的图下注释或引导语到 y≈1500。单靠该像素下沿不能判定主图是否显小、信息是否稀疏。

已向总控请求澄清主体边界，尚未收到更改定义。当前保留参考区间与原阈值。**待确认：是否要排除来源小字、引导语及次要图形，仅度量主图主体；若如此，需要先明确这类主体边界。** 当前不将 17 张全部标为构图良好，也不将“至少 10 张”写成通过。

两张带量线的诊断图已逐张查看：

- `~/.photo-content-os/evidence/R276-direct-video-opus/c-layout-b1.png`
- `~/.photo-content-os/evidence/R276-direct-video-opus/c-layout-b2.png`

青线为 y=200/1500，橙线为实际检出的下沿。图片哈希、尺寸及视觉检查范围见 `c-layout-visual-review.json`。原帧保持完整。

## 测试与合同

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_*.py` | **127 passed，19.80 秒**；前端静态回归也通过，没有改前端文件 |
| B17 真实样本数量校验（`tests-c-real-b17.log`） | **未通过：0/17 条提醒，要求至少 10 条；退出码 1** |
| A 里相同的相关测试命令（见下） | **47 passed，20 subtests passed，47.86 秒** |
| `bash scripts/check_runtime_contract.sh` | 通过 |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 通过；本任务新增未跟踪文件另行检查 |
| `git diff --check` | 通过 |

相关测试命令：

```bash
.venv/bin/python -m pytest -q tests/test_p0_llm_and_evidence.py tests/test_llm_creative_scripts.py tests/test_p5_local_prompts.py tests/test_p2_desktop_server.py tests/test_desktop_openapi_route_sync.py tests/test_full_checklist_acceptance.py tests/test_video_render.py
```

新增测试覆盖：各次写入计时刷新、成功/失败后保留、重启与中断、配音重写与单纯重渲、旧任务空时间；两类可重试状态的空/缺省/null/空白请求；其他状态反例；类型/长度反例和 1/200 边界；原错误、原意见、原代码转交；其他镜头不变；深浅不同背景、30% 严格边界、JPEG 噪点、未知测量、提醒不触发重写及重新测量清理旧提醒。

`studio/api_contract.py` 已声明 `writingStartedAt`、依状态而定的可选 instruction 和 `layout_bottom_gap` 提醒语义；`schemas/studio-openapi.json` 由 `build_openapi()` 重新生成。没有改变路由路径或既有字段名。

## C 修改文件与收尾

- `scripts/direct_video/generate.py`：写入开始时间、无意见重试上下文、提醒写入与重渲更新。
- `scripts/direct_video/media.py`、新增 `layout.py`：关键帧测量。
- `studio/direct_video.py`：新字段投影与旧任务未知值。
- `studio/api_contract.py`、`schemas/studio-openapi.json`：接口合同。
- `tests/test_r276_direct_c.py`：C 正反例；`tests/test_r276_direct_video.py` 的投影字段清单补新字段。
- 本报告及 C 文本/JSON 证据；诊断图在仓库外。

未修改 `studio/static/`、`tests/test_r276_direct_frontend.*`、Harness SSOT、主检出、Obsidian 或人工验收签署。没有创建 declared SSOT bundle。临时 `.venv` 链接收尾移除。

业务项目保留 A/B/C 未提交内容及前端线程自己的改动，没有提交、推送。Harness SSOT 本次未改，其既有其他会话改动保持原样。

本阶段停止。未关闭项仅为第 3 项真实样本至少 10 条提醒的验证条件；其测量定义需总控确认。


## D 段

日期：2026-10-26；基于总控合并提交 `90875ba`，本段仅修复页头出片耗时，未提交或推送。

`output.composedAt` 已加入持久化与公开投影、`api_contract.py` 及重新生成的 `schemas/studio-openapi.json`。成功合成后记录 ISO 时间，每次成功合成刷新；首次未合成、合成中、合成失败（包括进程中断恢复）以及用户单镜重写撤下成片时为 null。上传配音以及其后的时长重排、必要的配音后重写保留此前时间，直到重新合成。旧任务没有记录时公开投影为 null，不从 `updatedAt` 推算。

`studio/static/direct-view.js` 仅第 148、149 行的两种完成态页头耗时句改用 `composedAt − createdAt`；`composedAt` 为 null 或缺省时整句不显示，后续提示保留。按钮代码逐字比对未变，其他静态文件未改。

后端新增 6 项测试，覆盖未合成、成功及再次成功、单镜重写清空、配音上传保留（短配音重写／长配音仅重渲两条路径）、合成失败清空和旧任务缺字段。前端 Node 测试从实际页头分支执行正反例，两种完成态都验证：夹具 `updatedAt − createdAt = 135:17` 时仍显示 `composedAt − createdAt = 3:41`；空值夹具完全不显示耗时句。现有任务夹具补齐字段，新增 `done-no-composed-time.json`。

| 验证 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_*.py`（配置本机 Playwright 和浏览器，含真实 HTML 渲染测试） | **134 passed，43.49 秒** |
| `node tests/test_r276_direct_frontend.mjs` | **PASS**，包含新增正例和反例 |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | **PASS** |
| OpenAPI 与 `build_openapi()` 相等；字段 required、nullable、date-time 检查 | **PASS** |
| `git diff --check` | **PASS** |
| 实际 `createDirectView` 和共享样式的桌面、手机渲染 | 4 张整页截图逐张查看；1440×900 与 390×900，正例／空值反例；无横向溢出，页头和按钮正常 |

截图使用独立静态服务随机端口 59631、合成接口夹具；未访问运行中的 Studio。查看范围是页头、相邻区域及完整页面排版；夹具不供媒体字节，缩略图空缺与播放区域不作为本段媒体验收。临时静态服务与浏览器已关闭。

文本证据：`evidence/2026-10-26/R276-direct-video-opus/tests-d-r276.log`、`verification-d.json`、`d-screenshot-manifest.json`。截图与同名清单位于仓库外 `~/.photo-content-os/evidence/R276-direct-video-opus/d-composed-at/`。

本段请求均已完成；没有重新执行或改写 C 段的构图判定。业务工作区保留本段未提交修改；已有未跟踪 `.venv` 链接原样保留。Harness SSOT 未改，检查时其工作区有 57 项已有或其他线程修改。未操作 8765、8766，未修改总控正在使用的 Studio 状态。
