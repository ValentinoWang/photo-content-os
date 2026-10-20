# R208 A1 汇报

日期：2026-10-19（Asia/Taipei）。**状态：PARTIAL，按要求在 A1 停止；没有提交、暂存或推送，也没有进入 A2。**

实现、离线负例、10 段视频 + 5 张照片的本地体检/真实美感评分/真实多模态终选、最终长截图已经完成。**2–3 个本地模型的完整实测对比没有完成**：L/14 下载期间磁盘可用空间降至约 283 MiB，已终止下载、回收本任务未完成分块 818,937,856 字节；保留已验证的 B/32 缓存。另有 CLIP 骨干权重独立许可未明确的问题。因此不将 A1 报为全部验收通过，也没有正式选定“已确认许可允许”的商用模型。

## 文件与工作区

代码只在 `/private/tmp/task-worktrees/photo-content-os-r208-a1`，基于 `origin/main` 的 `c1b4db387e3c0c0aa6cabdb1af283a8e1d0f0594`。主目录只新增本报告及本任务证据副本。R207 禁止修改的脚本和 README 均未碰；`.gitignore` 只新增 `.tools/`，依赖只向 `requirements-dev.txt` 追加。

- [scripts/select_shots.py](/private/tmp/task-worktrees/photo-content-os-r208-a1/scripts/select_shots.py)
- [scripts/shot_quality.py](/private/tmp/task-worktrees/photo-content-os-r208-a1/scripts/shot_quality.py)
- [scripts/shot_aesthetics.py](/private/tmp/task-worktrees/photo-content-os-r208-a1/scripts/shot_aesthetics.py)
- [scripts/shot_selection_config.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/scripts/shot_selection_config.json)
- [schemas/shots.schema.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/schemas/shots.schema.json)
- [tests/test_select_shots_r208.py](/private/tmp/task-worktrees/photo-content-os-r208-a1/tests/test_select_shots_r208.py)
- [requirements-dev.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/requirements-dev.txt)
- [.gitignore](/private/tmp/task-worktrees/photo-content-os-r208-a1/.gitignore)

- 权重缓存：`/private/tmp/task-worktrees/photo-content-os-r208-a1/.tools/models/`，被 git 忽略；B/32 官方文件 SHA-256 为 `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`。另保留两个评分头缓存，未向 `~/.cache` 下载权重。
- 本机调用适配：`/private/tmp/task-worktrees/photo-content-os-r208-a1/.tools/bin/codex-r208`，用固定 `.venv` Python 启动同一个 Switch/Codex 包装器。没有更换服务、模型或全局 Codex 配置。
- 项目产物：`media-root:projects/2026-lzu-revisit/2026-lzu-travel-and-sports/ai-analysis/shots`，含 `shots.json`、83 张帧图、4 张候选拼图、4 张全候选审计拼图、5 份原始模型回答、调用记录、`overview.html`。素材项目只写这个目录。
- 机器证据：[证据目录](evidence/2026-10-19/R208-A)；代码与证据都是未提交内容。因本段明确禁止提交/推送，保留任务 worktree 供 Claude 审阅；收尾检查如实记录它和并行 R207 的未提交状态，未强行清理。

## 实现边界与运行方法

PySceneDetect 在 320 px、12 fps 的临时代理上检测切镜，区间终点夹到原始探测时长；大于 8 秒的场景再按光流变化峰值切为 2–6 秒候选。代理运行后删除。视频在 20%、50%、80% 取帧；照片处理 EXIF 方向并支持 HEIC。体检保存逐帧原始值和候选聚合值。任一必要测量缺失保留 `unknown_reasons`，不会进入精选；照片的抖动/动感为不适用 null，不会因此变成 unknown。

去重直接调用 `generate_ai_prompt.visual_similarity_groups`，以镜头编号区分同源视频的不同区间，没有平行实现。按素材子目录分场景，64 位平均哈希距离 ≤5（约 0.922 的位一致率）归组；只在体检通过的候选里保留美感总分最高者。全组不合格时不选代表。本样本未发现必须追加 CLIP 去重的证据。

A1 的总分只有美感分，权重 1；动感/叙事匹配等待阶段 B，分项为 null、权重 0，配置拒绝假启用它们。模型只能改变结论和理由，不能改来源、测量、时间或去重事实。

在 worktree 里运行：

```bash
OPENCLAW_CODEX_BIN="$PWD/.tools/bin/codex-r208" .venv/bin/python scripts/select_shots.py \
  projects/2026-lzu-revisit/2026-lzu-travel-and-sports \
  --limit-videos 10 --limit-photos 30
```

`--config` 可覆盖阈值；`--compare-models` 是顺序比较两个候选的入口（本次未完成该入口的全量验证）；`--skip-llm --aesthetic-model none` 无需模型权重/网络，未测美感会如实成为 unknown，离线测试另注入明确的评分测试替身。

首轮真实流程在 Codex 包装器的 Python 缺 `tomllib` 处失败，已保存失败证据。之后用固定 Python 启动同一个包装器，从已保存且核对过素材版本的本地结果继续终选；没有重复伪造体检。续跑脚本与日志留在证据目录。`shots.json` 的 `run_status=complete` 只表示这次单模型挑镜头流程完成，不代表 A1 的双模型对比或完整需求卡已通过。

## 样本与真实结果

目录轮询抽样覆盖 `selfie-moments`、`sports-meet`、`travel` 和 `travel/raw-pending`。当前正式素材扫描范围为 41 段视频、5 张照片（排除派生输出、`raw-vault`）；与 PRD 的 53/288 不是同一实际清单，本次没有为了凑到 30 张而纳入派生截图或其他目录。正式目录现存的标题参考图和 AI 超清图片仍保留并参与体检，未按文件名直接判好坏。

最终 26 段候选视频 + 5 张照片，共 31 条：**精选 4、可用 14、不用 1、被淘汰 7、unknown 5**，并返回 5 个开场钩子。没有 unknown 或淘汰项进入精选。可用包含尚未进入每组前三名终选的本地候选，未冒充模型已经审过。视频和照片重复显示的拼图列不会被算成三次照片评分。

15 个抽样源文件在运行前后逐一核对 SHA-256、大小、mtime，全部不变；验证范围仅是这 15 个源文件。

| 标记 | 条数（可重叠） | 例子 |
|---|---:|---|
| 糊 | 7 | `selfie-moments/私人素材（文件名已省略）` 的 `S1d6f53e6f8-001`；`travel/私人素材（文件名已省略）` 的末段 `S049c7b1b61-005` |
| 过曝 | 0 | 本样本没有超过阈值的例子，不编造 |
| 欠曝 | 0 | 本样本没有超过阈值的例子 |
| 抖 | 3 | `sports-meet/私人素材（文件名已省略）` 的 `S4f8f2673dd-002`、`-003` |
| 重复淘汰 | 1 | `sports-meet/兰州大学校运会私人素材（文件名已省略）` → 保留同场景成绩表 HEIC；另有全组已判糊的镜前两段归为 G001，未保留代表 |
| unknown | 5 | `selfie-moments/私人素材（文件名已省略）` 的 `S6e1e372b05-001`；`travel/私人素材（文件名已省略）` 的 `S049c7b1b61-004`，均为全局运动跟踪不足 |

## 模型考察与暂用理由

下表分开写代码与权重，不能把代码许可证直接当成骨干权重许可。两个评分头的权重与许可证在同一上游仓库，未见另行权重条款；CLIP 官方独立权重许可没有明确声明，相关 [上游问题仍未关闭](https://github.com/openai/CLIP/issues/203)。

| 候选 | 代码许可/来源 | 权重许可/来源 | 本机速度 | 实际分布 |
|---|---|---|---|---|
| LAION v1 B/32 线性评分头 | [MIT](https://github.com/LAION-AI/aesthetic-predictor/blob/6d122adad522ab246644d9dc1c6d7a3810ee255f/LICENSE)；运行实现 OpenCLIP 为 [MIT](https://github.com/mlfoundations/open_clip/blob/main/LICENSE) | [同仓库评分头](https://github.com/LAION-AI/aesthetic-predictor/tree/6d122adad522ab246644d9dc1c6d7a3810ee255f) 随 MIT 发布；CLIP [代码 MIT](https://github.com/openai/CLIP/blob/main/LICENSE)，独立权重条款未明确 | Apple Silicon / MPS，83 帧均值 0.0601 s；首帧 0.4663 s，后 82 帧均值 0.0551 s；另一次首次冷启动探针 3.87 s/帧，单列不混入暖态统计 | 帧分数 min/p25/median/p75/max：2.9253 / 4.0366 / 4.3837 / 4.8268 / 5.9218；31 条候选均分中位数 4.4442 |
| improved LAION v2 L/14 + MLP | [Apache-2.0](https://github.com/christophschuhmann/improved-aesthetic-predictor/blob/6934dd81792f086e613a121dbce43082cb8be85e/LICENSE)；OpenCLIP MIT | [同仓库评分头](https://github.com/christophschuhmann/improved-aesthetic-predictor/tree/6934dd81792f086e613a121dbce43082cb8be85e) 随 Apache-2.0 发布；CLIP 独立权重条款同上未明确 | **未实测**：骨干下载至约 781 MiB 分块后因磁盘不足停止，不能写推理速度 | **未实测**，不能伪造分布 |

本次临时用 B/32 完成本地实验：83 帧实际评分稳定、暖态约 18 帧/秒，候选从照片到视频可共用。**这不是基于已完成双模型对比或已确认骨干商用许可的正式选型**。后续须先解决空间及权重许可，再补第二模型并决定采用哪个。

## 阈值与数值分布

起始配置没有为追求样本结果而回调。糊阈值为项目候选拉普拉斯均值中位数 654.342726 的 40%，即 261.737090。曝光按亮度 >250 或 <5 的像素比例，任一采样帧 >25% 淘汰；取最大比例保留中间坏帧。所有清晰度比较统一到长边 640 px。

抖动以 12 fps、宽 320 px 代理的特征光流 + RANSAC 仿射全局运动测量，先用相位相关提供大平移初值；四角位移除以画面宽度，对连续五个采样间隔做中位数平滑，残差分量的 RMS >0.008 判抖。纯平移时相当于约 2.56 个代理像素的高频残差，能把合成平滑横移与随机抖动区分。可靠跟踪比例 <0.6 记 unknown，不写成“平滑”。这只是起始阈值，不代表所有真实追拍都已验证。

太短 <0.8 s；超过 8 s 的镜头切成 2–6 s；动感均值/峰值/峰值时刻只记录不淘汰。照片没有运动测量。数值分布如下，null 不参与百分位数，unknown 数量单列，不当作 0。

| 指标 | 有效数 | min | p25 | median | p75 | max |
|---|---:|---:|---:|---:|---:|---:|
| blur_variance | 31 | 69.9446 | 321.602 | 654.343 | 1202.14 | 2065.69 |
| blur_project_ratio | 31 | 0.106893 | 0.491488 | 1 | 1.83718 | 3.1569 |
| overexposed_fraction | 31 | 0 | 0.000136719 | 0.00104601 | 0.00555556 | 0.0297526 |
| underexposed_fraction | 31 | 0 | 3.90625e-05 | 0.00467882 | 0.0151085 | 0.0645486 |
| shake_high_frequency | 21 | 0.000305068 | 0.00343869 | 0.00479716 | 0.00688816 | 0.012262 |
| tracking_fraction | 26 | 0 | 0.677083 | 0.992754 | 1 | 1 |
| motion_mean | 26 | 0.00216734 | 0.00926584 | 0.0200342 | 0.0331004 | 0.0448638 |
| motion_peak | 26 | 0.00456188 | 0.0308434 | 0.0473238 | 0.061726 | 0.11556 |
| motion_peak_time_sec | 26 | 0.166667 | 1.77083 | 6.875 | 11.1875 | 15.5 |

## 多模态调用

使用 `llm_common.generate_text` 的传图能力，`gpt-5.6-terra` / `codex_cli`，全部 `medium`，未换强度、未换模型。成功 5 次，另有包装器在发出请求前失败 1 次。总调用计时 237.313 s。本地体检、评分及续跑终选记录合计 509.356 s，不含安装和权重下载。

| 次序 | 调用 | 状态 | 秒 |
|---|---|---|---:|
| 1 | select-001 | failed | 0.128 |
| 2 | select-001 | ok | 50.288 |
| 3 | select-002 | ok | 47.194 |
| 4 | select-003 | ok | 41.976 |
| 5 | select-004 | ok | 56.534 |
| 6 | hooks | ok | 41.194 |

每组回答必须覆盖所有且只能引用该拼图编号，重复、漏项、未知编号都报错；钩子也只允许引用实际展示且仍可用的编号。原始回答保留在 `media-root:projects/2026-lzu-revisit/2026-lzu-travel-and-sports/ai-analysis/shots/llm/`；没有把模型理由反写成体检事实。

## 我看图认为需要复核的地方

1. `S1d6f53e6f8-001` 的镜前体态画面仍可辨认，墙面/门的低纹理可能拉低清晰度；`S3a7e697f5f-001`、`-002` 也有可用帧，统一项目中位数阈值可能误杀。这是观察意见，本次未调阈值。
2. `S4f8f2673dd-002`、`-003` 虽被判抖，但包含值得保留的冲刺动作。三张静帧不能证明是故意追拍还是抖动，A2 应播放原片核对，不能用截图宣布运镜平滑。
3. 模型把 `S1c053bd1b6-001` 的机场拱窗区域说成“体育空间”“蓝色场地”。图像不足以支持这两个断言；应只描述开阔拱窗空间。其入选本身可理解，理由的场景语义有误。
4. `S049c7b1b61-002` 源路径是“抵达通道出站”，模型却说“启程”；B12 标识只证明机场场景，不证明出发/到达方向。保留为模型推断，不作为素材事实。
5. 标题参考截图、带 AI 超清水印图片即使本地体检可用，也没有因此自动成为精选。当前它们未进每组前三名终选，不能说模型已逐张审核了全部 31 条；真正传图覆盖了 10 个候选。

## 检查结果与证据入口

- 先写负例，初次 red 是新模块尚不存在；随后随机抖动夹具暴露跟踪失败，修复大位移初值并用静止底图隔离运动类型，最终 **14 项专项测试全部通过**。夹具运行时由 ffmpeg 生成，没有提交大视频；离线测试不会发模型请求。
- 全套 `pytest -q tests`：**589 passed、32 skipped、9 failed、6 errors、1982 subtests passed**。与新增实现前的 575 passed 基线比较，失败/错误集合完全相同；新增 14 项均绿，没有新增失败。没有修改其他线程的字幕、黑帧或 PF 测试。
- 6 个 PF 错误均发生在原有夹具 ffmpeg 命令，退出码 8；字幕和黑帧原有失败亦见原始日志，不将其未经验证地归因为其他后端。Obsidian 同步失败是新 worktree 的文档 mtime 新于已有目标；这些覆盖文档内容本次没有修改，也没有为过门禁改时间戳或弱化检查。
- `check_runtime_contract.sh` 通过；两个 validate 脚本 `--help` 通过；`pip check` 通过。`check_obsidian_doc_sync.py`、`check_outline_contract.py .` 因上述既有同步检查失败，日志完整保留。
- 最终证据页是本地实验报告，不是产品审阅页或部署验证。真实桌面 1280×900 → 长图 1280×18061，真实手机 390×844 → 长图 390×56270；23/76 张实际滚动帧，97 处重叠接缝像素差为 0，83 张图无坏图，无横向溢出，覆盖最后 `S049c7b1b61-005`。已看首、中、末及候选拼图，长图同时提供连续编号部分供阅读。

绝对路径：

- 总览：`media-root:projects/2026-lzu-revisit/2026-lzu-travel-and-sports/ai-analysis/shots/overview.html`
- 桌面完整图：`evidence/2026-10-19/R208-A/screenshots/overview-desktop-full.png`
- 手机完整图：`evidence/2026-10-19/R208-A/screenshots/overview-phone-full.png`
- 可点击的最终截图索引：[截图索引](evidence/2026-10-19/R208-A/screenshots/index.html)
- 覆盖区间、尺寸、时间和哈希：`evidence/2026-10-19/R208-A/screenshots/capture-manifest.json`

## 收尾与留给 Claude 的问题

- 第二个模型对比及“权重许可明确允许”的正式选型未闭环；本段止于 A1 的部分完成，不进入 A2，不扩大真实素材跑量。
- 主目录原有未提交改动和 R207 工作区未被暂存、还原或修改。业务代码保留在任务 worktree；主目录新增报告及证据。详见 `main-git-status-before-delivery.txt`、`worktree-git-status.txt` 和 `worktree-check.log`。
- 本次没有修改 Harness SSOT；其仓库已有其他工作区改动，原样记录在 `harness-git-status.txt`。没有创建/更新声明式 SSOT 开发包，因此本报告和证据不进入 Obsidian SSOT 快照。
- 本任务的下载、评分、Codex 子调用和临时浏览器均已结束，`process-closeout.json` 无残留；没有常驻服务。只清除了本任务未完成的 L/14 下载分块，没有清理其他线程或真实素材。

原有失败/错误清单：

- `tests/test_bilingual_subtitles_r6.py::BilingualCaptionTests::test_real_two_layer_burn`
- `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_chinese_glyphs_do_not_fall_back_to_identical_missing_glyph_boxes`
- `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_real_cut_first_frames_80166667_and_122866667`
- `tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_white_text_has_a_dark_backplate_on_white_and_black`
- `tests/test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_alpha_and_geometry_have_exact_pixel_bounds`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_changed_source_fails_projection`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_editable_document_structure_and_neutral_producers`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_every_frame_matches_retained_source_clock`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_projection_checks_preview_waveform_and_no_local_paths`
- `tests/test_pf_video_pipeline.py::FrameMappingTests::test_real_silence_envelope_has_no_simulated_peaks`
- `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_black_native_frames_fail_even_with_burned_subtitles`
- `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_few_dots_is_not_a_black_frame`
- `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_small_white_header_is_not_a_black_frame`
- `tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_uniform_deep_gray_has_no_content_and_fails`
