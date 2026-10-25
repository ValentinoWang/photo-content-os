# R276 第一段 A 汇报

日期：2026-10-26。范围：任务单 2.1–2.4 后端实现与测试。仅修改指定 worktree；未提交、未推送，未操作 8765 上正在使用的 Studio。第二段 B 未开始。

## 实现

| 文件 | 改动 |
| --- | --- |
| `scripts/llm_common.py` | 新增 `claude_cli` 和 `claude`、`claude-cli` 别名；独立默认模型与 300 秒超时；隔离目录、标准输入提示、可解析 JSON、无工具和 MCP、关闭用户/项目自定义配置；错误不回传提示原文。原 Codex/OpenAI 入口保持原行为。 |
| `scripts/direct_video/__init__.py` | 新生成器包。 |
| `scripts/direct_video/rules/shots.md` | 从用户 `direct-video-shots` 技能提取代码规则；注明 HeyGen HyperFrames / Apache-2.0 来源，没有搬入人工交付或审片流程。 |
| `scripts/direct_video/lint.py` | 函数与命令行检查，结构化中文 errors/warnings，时长、逐帧入口、页眉、标点、禁用运行方式、数字提醒等。SVG namespace URI 不作为网络请求。 |
| `scripts/direct_video/generate.py` | 全片设计、逐镜 JSON 验证、最多三镜并发、写好即渲染、lint 失败仅一次重写、单镜修改、配音重定时、后台任务、原子落盘、重启恢复。 |
| `scripts/direct_video/media.py` | 复用现有 `multi_shot.py`、`compose.py`、JPEG 海报、本地 FunASR；海报取约 0.8D，短边不超过 360；支持无声预览和带声合成，合成复用帧缓存。 |
| `scripts/video_candidate.py` | 追加 `check_direct_output`，复用既有解码/帧数检查及黑帧检查。原有函数 AST 与 HEAD 一致。 |
| `studio/direct_video.py` | 工作台适配层、字段白名单投影、路径脱敏、受控错误、任务/代码/海报/成片读取。 |
| `studio/server.py` | 注册并处理九个接口，沿用本机访问与 CSRF；新增接口额外核对 Origin 与当前 Host 一致；MP4 复用流式单段 Range 返回。 |
| `studio/api_contract.py` | 九个路由、请求结构、WAV 类型与大小、任务投影完整字段及状态枚举。创建任务声明 201。 |
| `schemas/studio-openapi.json` | 由 `build_openapi()` 重新生成，保持原排序。 |
| `tests/test_r276_direct_video.py` | 假可执行文件、模型/代码 JSON、lint、并发、重试、单镜不变性、配音、恢复及错误测试。 |
| `tests/test_r276_direct_api.py` | 临时端口真实 HTTP：九接口、安全、隐私、原样代码、Range、二进制 WAV、OpenAPI 投影校验。 |
| `tests/test_r276_direct_media.py` | 合成帧的真实 FFmpeg 无声/带声合成及检查；浏览器渲染测试在未配置 Playwright 时跳过。 |

任务私有文件位于 Studio `state_dir/direct-jobs/<projectId>/<jobId>/`，包括 job、design、shots、checks、posters、帧缓存、配音和成片。投影不携带这些目录。原子替换后才公开代码、海报和成片。写到一半的镜头在重启后标为 `interrupted`，可用单镜 rewrite 重试；只有确认原任务记录的进程已退出，才回收其遗留渲染锁，不清理活进程的锁。

无配音时按含标点字数 ÷ 5.1 估算，保留一位小数。上传配音后先调用本地 FunASR，仅精确文本覆盖和声学词边界均可验证时采用 `narration`；无法对齐或本地 ASR 不可用时标为 `proportional`。分配结果量化到 30fps，所有镜头总帧数对应整段配音，误差不超过半帧。比代码 D 短的镜头按新 D 重写。写好后为 `ready`，调用 compose 得到预览或成片；前端应明确发起此接口。

单镜 rewrite 在返回时即标记该镜 `writing` 并撤下旧成片就绪状态；其他镜代码、海报字节、文件修改时间和 `writtenAt` 不变。并发或前置状态不满足时返回受控错误，不排入冲突写操作。

## Claude 实测

第一关通过后才开始生成器和接口实现。

- 调用：`generate_text(provider='claude_cli', model='claude-opus-5-5', …)`。
- 用独立后台 Python 子进程启动，`stdin=DEVNULL`、stdout 写日志、独立会话；stdin/stdout 都非 TTY。未通过 shell 函数调用。
- 登录目录：继承 `CLAUDE_CONFIG_DIR=~/.claude-account3`，没有切换账号或改写账号配置。
- 真实可执行文件：`~/Desktop/Opensource_Tool/npm-global/bin/claude`。
- 返回：精确 `ok`；耗时 **7.004 秒**。
- 经本机 `claude --help` 确认并采用：`-p --output-format json --safe-mode --setting-sources '' --tools '' --strict-mcp-config --mcp-config '{"mcpServers":{}}' --no-session-persistence`，模型另传 `--model`。提示仅走 stdin，工作目录是空临时目录；子进程移除交互会话的 `CLAUDECODE` 标记。
- `--safe-mode` 的本机说明是禁用 CLAUDE.md、skills、用户插件、hooks、MCP 等自定义项；管理员策略仍由 Claude CLI 执行。这次未改动策略或凭据。
- 可覆盖：`OPENCLAW_CLAUDE_BIN`、`OPENCLAW_CLAUDE_CONFIG_DIR`、`OPENCLAW_CLAUDE_TIMEOUT_SEC`。生成器并发 `DIRECT_VIDEO_WORKERS=1..3`；字体可用 `DIRECT_VIDEO_FONT` 指定，Mac 默认华文黑体 Medium。
- 证据：`evidence/2026-10-26/R276-direct-video-opus/claude-probe.json`、`claude-probe.log`、`claude-help.log`。

这只证明后台模型入口可用，没有把它表述为十镜生成、真实 HTML 渲染或成片链路已实跑。

## 验证

命令从 worktree 根执行，临时借用主检出的固定 `.venv` 软链接；不修改其中依赖。收尾已移除这个临时软链接；重跑时按任务 worktree 规则接回主检出的现有 `.venv`。最终测试的临时帧、音频、MP4 放在仓库外 `~/.photo-content-os/evidence/R276-direct-video-opus/` 下。

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r276_*.py` | 46 passed，1 skipped。 |
| `.venv/bin/python -m pytest -q tests/test_p0_llm_and_evidence.py tests/test_llm_creative_scripts.py tests/test_p5_local_prompts.py tests/test_p2_desktop_server.py tests/test_desktop_openapi_route_sync.py tests/test_full_checklist_acceptance.py tests/test_video_render.py` | 39 passed，8 skipped，20 subtests passed。 |
| `.venv/bin/python -m pytest -q tests` | 9 failed，881 passed，34 skipped，6 errors，2003 subtests passed；109.67 秒。 |
| `bash scripts/check_runtime_contract.sh` | 通过，Python 3.13.16、编译、依赖版本与编码合同均通过。 |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 通过；另对新增未跟踪文件补做源码与隐私扫描。 |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 通过，126 ids / 121 copy entries。 |
| `OBSIDIAN_ROOT=… .venv/bin/python scripts/check_obsidian_doc_sync.py` | 未通过，三份配对文档时间戳检查，见下文。 |
| `OBSIDIAN_ROOT=… .venv/bin/python scripts/check_outline_contract.py .` | 被上述文档同步检查阻塞。 |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 通过。 |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 通过。 |
| `git diff --check` | 通过。 |

`UI_COPY_QUALITY_CHECKER` 已指向 Core 的 `ui-copy-quality/scripts/check_ui_copy_quality.py`；`OBSIDIAN_ROOT` 显式指向现有自媒体库。

媒体测试中的 FFmpeg、帧指纹校验、无声/带声合成、解码、实际帧数、音画时长差和黑帧检查是真实执行；模型和帧来源为合成夹具。带声缓存测试只替换浏览器运行时身份，并断言不得调用真实渲染器；不能据此声称浏览器渲染已验证。

本机没有可解析的 Node Playwright，也没有设置 `VIDEO_RENDER_PLAYWRIGHT_MODULE`。新测试的一项真实 HTML/海报渲染和既有 `test_video_render.py` 的八项浏览器测试据此跳过。未安装依赖、未启动 8766 或第二段的状态目录。

### 全量失败逐项归因

1. `tests/test_bilingual_subtitles_r6.py::BilingualCaptionTests::test_real_two_layer_burn`：既有字幕渲染使用的 FFmpeg 缺少 `drawtext`。
2. `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_chinese_glyphs_do_not_fall_back_to_identical_missing_glyph_boxes`：同上。
3. `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_real_cut_first_frames_80166667_and_122866667`：同上。
4. `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_white_text_has_a_dark_backplate_on_white_and_black`：同上。
5. `tests/test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies`：worktree 中原有 `scripts/README.md`、`docs/execution-rules.md` 的检出时间新于 Obsidian 配对文档；本任务未修改它们，也未更改同步标记。
6. `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_black_native_frames_fail_even_with_burned_subtitles`：在既有字幕烧录处因缺少 `drawtext` 失败。
7. `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_few_dots_is_not_a_black_frame`：同上。
8. `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_small_white_header_is_not_a_black_frame`：同上。
9. `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_uniform_deep_gray_has_no_content_and_fails`：同上。
10. `tests/test_pf_video_pipeline.py::FrameMappingTests::test_alpha_and_geometry_have_exact_pixel_bounds`：公共 setUpClass 用 `drawtext` 创建测试视频失败，测试未执行。
11. 同类 `test_changed_source_fails_projection`：同一初始化错误。
12. 同类 `test_editable_document_structure_and_neutral_producers`：同一初始化错误。
13. 同类 `test_every_frame_matches_retained_source_clock`：同一初始化错误。
14. 同类 `test_projection_checks_preview_waveform_and_no_local_paths`：同一初始化错误。
15. 同类 `test_real_silence_envelope_has_no_simulated_peaks`：同一初始化错误。

归因证据：`baseline-failure-analysis.json` 核对相关测试、字幕实现、同步脚本与文档都和 HEAD 相同；`video_candidate.py` 原有全部函数 AST 未变。`ffmpeg-drawtext-probe.json` 是独立最小命令，返回码 8，明确 `No such filter: 'drawtext'`。没有为了通过而跳过或修改上述旧测试。

## 尚未实测、交接和需要拍板的事项

- A 的后端实现与假模型/合成媒体测试已交付；真实 Opus 编写整片、FunASR 实际转写、Chromium 实际渲染、视觉审片、成片播放及十五分钟耗时目标尚未验证，属于 B / 后续前端工作。没有将 H-01–H-03 标为通过。
- B 前需要配置已安装的固定 Playwright/Chromium；当前缺少的 `drawtext` 会影响既有字幕链路。R276 本次复用的基础合成可运行，未新增字幕烧录需求或改写旧字幕实现。
- 文档时间戳检查失败保留原状。未写 Obsidian、未修改主检出，未放宽规则。
- 无需新增产品决策。是否进入 B 由总控看过本报告后另行启动；本轮停止。
- 开场读取的人工待验收项为 R223 音乐标签/节拍、R220 导航/镜头过目/预览、R210 音乐导入，以及非阻塞 R207 编辑工具。本次未修改它们的受保护测试、标准或签署；R220 的媒体返回通过既有通用函数复用。R276 原始 H-01–H-03 保持原样，A 阶段不递交整条用户链路验收。
- worktree 没有 `develop/harness/fullstack-ai-harness.md`，因此按全局目录直接读取 Core 的现行入口与后端/API/AI 出口规则；没有补写或更改 Harness 链接。
- 本次未创建或更新 declared SSOT bundle，报告和测试证据不是 SSOT，因此没有另建 Obsidian SSOT 快照。

全部文本证据位于 `evidence/2026-10-26/R276-direct-video-opus/`。日志中的本机绝对目录在归档时脱敏，未放入真实口播、配音或视频素材。

Git 状态：业务 worktree 保留本次未提交源码、新测试、报告和文本证据；未暂存。Harness SSOT 本次无修改，其仓库已有其他会话未提交变更，未触碰、未回退。
