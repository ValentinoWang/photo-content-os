# Photo 视频派生执行

执行合同沿用 `openclaw_video_execution.runtime_factory`、MX 白名单、Agent 下载及结果 journal。Photo 使用固定 `.venv/bin/python`，没有新增队列、数据库、模型通道或上传器。原片、原生工程和高清成片仍只在本机。

## 原生入口

- `create_video_shot_image(run_ref, task=descriptor['shotImageTask'], inputs={'workspace_ref': input_ref})`：完整确认摘要、显式 CreativeProject binding、job、镜号均通过后执行。`source_frame` 要求绑定源文件中恰有一个视频，并检查 `sourceTimeSeconds`；`code_render` 要求该镜有已确认的 HTML 与真实代码 SHA-256。返回 `{image_ref, shotId}`，都是受控相对引用。Media 的 `retry_image` 会生成新 job 并复制最后失败任务的原 action / 参数；Photo 再执行这个完整确认任务，不自行猜测失败任务。
- `render_video_revision(run_ref, shot_ids=descriptor['renderShotIds'], previous_job_id=descriptor['previousJobId'], inputs={'workspace_ref': input_ref})`：验证之前 canonical run 的身份、正文、Photo revision、源文件和音轨摘要；未选镜的分镜与动画必须不变。新 job 有自己的 canonical run / receipts，复用之前的帧与编码片段，不覆盖旧 run。
- `retry_video_shot` 保留同一 job 和运行库，要求唯一真实失败镜。`retryShotId` 优先于修订原始选镜范围；只提交该镜进度。

缺原生渲染 binding、未选镜缓存失效、运行库/浏览器版本改变、身份或摘要不符时明确阻塞。修订只运行已绑定的 compose 或 teaching_clips，以及教学路径的 Kdenlive 最终合成，不重做转写或调用模型，不自行改成整片重渲。

## 代码与图片输入

`renderCode.contentDigest` 是原始代码 UTF-8 的 SHA-256，进入执行前校验。已确认代码存为本机素材目录下 `.photo-confirmed/<内容摘要>/shot.html`，原有素材不改写；相同内容沿用相同路径。静态 / CSS 动画使用确定的 CSS 帧时钟；自定义 JavaScript 动画可定义 `window.seekFrame(frame, fps)`。配音时长不变，短动画渲染后保持最后一帧。

同一代码调整动画时长时，从之前已确认的本机编译 manifest 保留代码采样时钟并按目标时长缩放，避免仅裁掉后半段。换代码则以新确认计划的时长建立时钟。生成代码的资源根只包含该代码及对应的受控 `shot-image.jpg`，不能读取其他项目图片；固定字体仍由渲染器注入。

已保存 `shotImageInputs` 必须是对应 job / 镜的 JPEG，实际字节大小、SHA-256 和完整解码均校验。Agent 下载位置仍为 `video-inputs/<jobId>/shot-images/<shotId>.jpg`；已确认 HTML 可通过同目录的 `shot-image.jpg` 使用该图。图片路径不出本机，生成目录拒绝符号链接或同名内容漂移。

## 派生回执

直出逐镜海报取真实代码渲染的第 0 帧，转换为去元数据的单帧 JPEG，≤200000 B、短边≤360、完整解码。Photo progress 提供 `poster_ref / poster_width / poster_height / poster_short_edge`；Agent 转为 `source=code_render` 的受控 artifact。修订或重试只回传选镜进度，未选镜海报由 Media 保留。

源视频测量的包络报告 `waveformSource=source`；直出原始旁白的包络报告 `narration`。原生剪后 / 合成帧时钟对应动画 `timeBasis=edited`。缺图截帧本机 receipt 保存请求时刻与源文件 hash，不把请求时刻伪装为实际测量时刻。未确认版权仍为 unknown。

失败的 `handoff_manifest.json` 含真实、清理后的逐镜计数与唯一失败镜 `failedShotId`，没有诊断正文或路径。当前 Media Agent 的 blocked 分支只取 runtime code；跨仓消费者接入这些失败事实仍需 MC 完成。Media 候选接收还会覆盖 progress 已报告的 waveformSource，属于服务侧协调项。

## 离线验证与实践

核心：`.venv/bin/python -m pytest -q tests`、`bash scripts/run_local_ci.sh`。渲染采用一个浏览器逐镜执行，关闭后才开下一镜；验证中按真实 browser_pid 对 owned process group 查询，不能关闭 MF 的浏览器。

专项：在既有锁定 Agent 环境运行 `tests/test_pf_agent_runtime.py` 和 `tests/test_pf2_agent_runtime.py`。真实服务夹具 `tests/test_pf2_service_e2e.py` 仅在 `PF2_POSTGRES_E2E=1` 且配置专属可丢弃 PostgreSQL 时运行；证据驱动 `evidence/2026-10-12/video-pipeline-pf2/run_service_e2e.py` 建空库、迁移、运行并 DROP，只写 Photo 证据。全部素材和模型返回是合成夹具，不收费。

第三批正常启动 `npm run dev:media:integrated`（Media Web）及 Photo `scripts/launch_studio.py`。真实设备配对后，依次执行缺图截帧 / 代码单帧 / 失败图片重试与保存；再执行 AI 候选→确认→选镜渲染，核对未选镜缓存、海报和字幕。收费 ASR/TTS 仍需第三批显式 `live / --live`；本段不执行。
