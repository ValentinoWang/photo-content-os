# R283 后端段汇报

日期：2026-10-27。仅执行 TASK.md 第 0 节与 B 后端段。

后端实现和临时库测试完成；最终指定回归 **293 passed、3 skipped、1 failed**。唯一失败是 S 段真实风格库尚有七种缺少预览媒体。整体交付仍未完成，不代表前端、真实模型生成、真渲染或人工验收通过。

## 修改文件

| 文件 | 实现 |
| --- | --- |
| `scripts/direct_video/styles.py` | 新增只读 `StyleLibrary`：以 `style_library/index.json` 为顺序来源，校验元数据与四个文件；坏条目独立排除并记录日志；读取不缓存，文件变化下次可见。绑定库来源并冻结画法与样张代码。 |
| `scripts/direct_video/generate.py` | 每镜写代码统一注入 `form_profile.visual_grammar`、完整样张代码和“同一风格的一镜样例，内容不同，只照画法”；R277 重写走同一路径。库来源调整允许保留完整禁用列表。 |
| `studio/direct_video.py` | `/api/direct/styles` 增加 `library`；提供媒体文件定位；库来源通过既有任务投影带出并接受递归路径脱敏。 |
| `studio/server.py` | 注册接口对应的媒体请求调用既有流式 Range 实现，未知或无效风格返回 404 `style_base_not_found`。 |
| `studio/direct_style_contract.py` | 增加两条媒体路由、库列表响应、`styleBase.kind=library` 和 `{kind,id,name,instruction}` 来源契约。 |
| `studio/api_contract.py` | 新媒体路由绕过只适用于 JSON 的修订库契约装饰，保留二进制响应类型。 |
| `schemas/studio-openapi.json` | 从 `build_openapi()` 重新生成并校验一致。 |
| `tests/test_r283_style_library.py` | 新增临时库逻辑、HTTP、设计来源、模型调用次数、提示、重启重写、路径隐私、契约及真实九种样张测试。 |
| `docs/tasks/R283-direct-style-library/REPORT-B.md` | 本汇报。 |

没有写入 `scripts/direct_video/style_library/` 或 `render_style_sample.sh`；它们归 S 段。既有 R276/R277/R278 测试和验收物未修改。

## 行为

- `palette` 必须恰好四个约定颜色键，各为六位十六进制色；`typeScale` 必须三个整数，拒绝布尔值和浮点数。
- `motionSummary` 非空且原字符串最多 30 字；`bannedShort` 为 1–8 条非空字符串，每条原字符串最多 12 字。`motionRules`、`banned`、`visualGrammar` 均须存在且非空。
- JSON 损坏、缺文件、空文件或指向库外的样张链接均排除该项并记录日志。没有为坏项生成替代内容。
- 列表只公开六个设计字段和相对 API URL。指定媒体请求只加载目标配方，再由既有媒体响应器流式送文件；JPG 和 MP4 都支持完整、起止、开放结束、后缀 Range，非法 Range 返回 416。
- `style` 省略、空串或全空白时，六个设计字段原样复制，不调用模型定设计；填写修改说明时，沿用现有调整流程，成功路径只调用一次设计模型，提示带原设计和这句修改。
- 真实配方有八条禁用项，超出旧模型设计的 3–6 条约束。库来源调整接受完整非空列表，并明确要求保留原列表；从头定风格的旧约束保留。既有设计回复不合格时重试一次的机制保留。
- 画法和样张代码在建任务时冻结到私有任务字段；重启、修改库文件以后，重写已有任务的一镜仍用该任务原有上下文。继续沿用该任务时也保留上下文。

## 先红后绿

所有 pytest 启动器均剔除环境中全部 `VIDEO_RENDER_*`，使用本 worktree 的 `.venv/bin/python`，未真调模型。

| 阶段 | 结果 | 证据文件 |
| --- | --- | --- |
| 仅新增测试，在未改实现的 HEAD `130c931` 代码上运行 | **26 failed、6 passed**；缺少读取器、响应没有 `library`、拒绝库来源，真实库还没有索引。 | `red.txt` |
| 补测“只改底色，其余保留”，修复前 | **1 failed、2 passed**；保留八条禁用项被旧设计校验拒绝。 | `red-adjust-eight-bans.txt` |
| 补测短文案尾部空白计入长度，修复前 | **2 failed、14 passed**。 | `red-raw-length.txt` |
| 最后修改后的定向复验：R283、R278 style-base、OpenAPI route sync、full checklist acceptance | **102 passed、1 failed**；唯一失败仍是真实库未齐。 | `final-focused.txt` |
| 最终指定回归：R276、R277、R278 全部 `.py` 测试及 R283 新测试 | **293 passed、3 skipped、1 failed，121.90 秒**；唯一失败为真实库完整性。 | `regression-final.txt` |

最终 R283 文件中 **33 条通过、1 条真实库测试失败**。R276/R277/R278 合计 **260 条通过、3 条跳过**。

回归命令的实际参数为：

```bash
.venv/bin/python -m pytest -q -rs tests/test_r276_*.py tests/test_r277_*.py tests/test_r278_*.py tests/test_r283_style_library.py
```

执行时通过 Python `subprocess.run(..., env={k: v for k, v in os.environ.items() if not k.startswith('VIDEO_RENDER_')})` 启动上述命令；没有设置渲染环境来抢占 S 段浏览器或渲染队列。测试使用临时状态目录和 `port=0`，未操作 8765–8769 的 Studio。

### 跳过的三条

1. `tests/test_r276_direct_media.py::test_real_html_render_and_poster`
2. `tests/test_r277_boxes.py::test_r276_shot02_boxes_at_poster_frame_and_chinese_names`
3. `tests/test_r277_boxes.py::test_local_render_stores_boxes_and_three_review_frames`

均因未配置 Playwright 渲染环境而跳过。已有合成帧的 FFmpeg 编码测试照常执行；未做 HTML 真渲染、付费模型调用、真实七镜生成或视觉质量判断。

## 真实库与 S 段配合

最终回归时，索引已为约定的九个字符串 ID，顺序为 `flat, math, launch, whiteboard, cyber, ink, dataviz, pixel, code`。

- `flat`、`math` 四个文件齐全，可被读取器列出。
- `launch`、`whiteboard`、`cyber`、`ink`、`dataviz`、`pixel`、`code` 尚缺 JPG/MP4，因此真实库测试断言列九种失败；日志逐项点名排除。
- 独立只读盘点时，九份 HTML 均已存在，调用 `lint()` 均为 **0 ERROR、0 WARN**。此检查不代表媒体已经渲染或视觉合格。
- S 段补齐上述七种预览媒体后，请重跑 `tests/test_r283_style_library.py::test_real_library_nine_complete_valid_samples`。该测试没有标成跳过或预期失败，也没有为通过而修改 S 段数据。

盘点快照：`real-library-inventory.json`。S 段仍在并行工作，以上为测试及盘点时状态。

## 规则与附加检查

| 适用规则 | 本次结果 |
| --- | --- |
| 读接口范围有界、不读无关文件、不写盘 | 两项索引配方始终只读索引及两份 JSON/HTML，共 5 次 `read_text`；未索引文件从 1 增到 10 次数不变，测试通过。 |
| 单项损坏独立隔离、读取失败有日志 | 非法字段、缺少四类文件、坏 JSON、库外符号链接测试通过；真实缺媒体也逐项记日志。 |
| 接口、投影与隐私同时验证 | HTTP Range/404、JSON Schema、OpenAPI 生成一致性和投影不含临时目录测试通过。 |
| 结论仅覆盖实际验证范围 | 模型及生成渲染使用替身；真渲染三条跳过；真实库测试如实失败；没有宣称人工通过。 |

附加检查均设置 Core `UI_COPY_QUALITY_CHECKER`，文档检查显式设置实际 Obsidian 自媒体库为 `OBSIDIAN_ROOT`。

| 检查 | 结果 |
| --- | --- |
| `bash scripts/check_runtime_contract.sh` | PASS；最终改动后再次 PASS。 |
| `scripts/validate_music_analysis_registry.py` | PASS：126 IDs、121 copy entries。 |
| `scripts/check_repository_safety.py --base origin/main` | PASS；最终改动后再次 PASS。 |
| `scripts/check_obsidian_doc_sync.py` | FAIL：三个配对的源文件时间戳新于 Obsidian 目标。 |
| `scripts/check_outline_contract.py .` | FAIL：同一文档同步时间戳问题。 |
| `scripts/validate_content_os_task.py --help` | PASS。 |
| `scripts/validate_jianying_draft.py --help` | PASS。 |
| `git diff --check` | PASS。 |

文档同步失败涉及协作规范、剪辑交接协议和历史剪映协议。四份源文件 `scripts/README.md`、`docs/execution-rules.md`、`docs/media-workflow.md`、`docs/editing-and-hyperframes.md` 内容均与 HEAD 完全相同，逐文件比较及哈希已记录在 `doc-sync-input-baseline.json`。本段没有改这些文件、触碰 Obsidian 页面、调整时间戳或放宽同步检查；由总控处理现有同步状态。

任务要求的 `develop/harness/fullstack-ai-harness.md` 在本 worktree 缺失；已阅读 Core 同名权威规则及项目 adapter，没有为此修改规则或创建链接。

## 边界、证据及 Git 状态

- 全程保留现有 worktree，HEAD 仍为 `130c931`；没有提交、推送、增建 worktree、改写提交或编辑主检出。
- 未编辑 `studio-r276`、`studio-r278`，未改动 S 段文件。机器证据均写入仓库外 `~/.photo-content-os/evidence/R283-direct-style-library/backend/`；上文证据文件均相对此目录。
- 磁盘检查从约 7.5 GiB 可用开始，观察到的最低值约 5.2 GiB，没有触及 3 GB 停止线。没有跑全量 pytest、浏览器或本段样张渲染。
- 业务项目：本段七个已有产品文件修改，新增测试及本汇报；工作区另有启动时已有文件和 S 段并行产物。完整写报告前状态见 `git-status-business.txt`。
- Harness SSOT：本段 **零修改**；外部 Harness 仓库本来已有其他线程未提交改动，最后读取到 89 条状态项，未清理或操作。完整状态见 `git-status-harness.txt`。
- 相交的 R276、R277、R278 人工记录仍为 `PENDING`。本段没有修改验收记录、生成替代签署或宣称整体 READY。

本汇报为实施报告，不是新增声明式 SSOT 包。写完本文件即停止。
