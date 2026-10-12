# PS3 本地证据

权威需求：Media 仓库交接 26、定稿 studio-handoff.html 与 studio-handoff.contract.json。这里只存机器证据和本线程复现材料，不是新 SSOT。

最终代码：Photo git 065a0e4（之后仅 QA 等待和证据提交）。全量测试与本地 CI 以 *-stack-final.log 为准；原生工程两项测试以 stack-native-final.log 为准。旧失败/排队日志保留用于定位，不能作为最终通过证据。

截图/哈希/视口/时间/完整滚动范围：Media docs/development/video-pipeline-build/fe-shots/ps3-capture-manifest.json；同状态对照入口 ps3-comparison.html。fixture 是合成数据和 UI 分支，native 是真实本机 HTTP 编辑、保护检查和工程读回。fixture ChatCut/Kdenlive 候选仅使用同一份 FFmpeg 合成 MP4，不证明两个软件实际导出。

严格文案合同结果仍为红（design-contract-result.json），不修改批准合同、不添加自行批准的 extras。根块在运行 manifest 存在；通用 collector 的后代收集未把状态根块算入 ids，另有折叠 details 和动态数据标注的噪声。可见差异另在最终报告「和设计稿哪里不一样」「需要新文案」列出；不能据此宣称合同通过。

复现采纳/重叠撤回/分割/撤销栈/CAS/源文件不变/导出：设置 CONTENT_OS_OPENFILM_PACKAGE 指向 pinned openfilm 0.1.5、CONTENT_OS_CHROMIUM_SLOT_SCRIPT 指向 Media withChromiumSlot.sh，然后运行 .venv/bin/python -m pytest -q tests/test_ps3_openfilm_session.py --basetemp=<本线程专用目录>。浏览器包装脚本使用默认参数。全量 .venv/bin/python -m pytest -q；本地 CI bash scripts/run_local_ci.sh。TMPDIR 指向本线程专用目录，结束清理。

seed.py、preview-fixtures.py、native-export.py 是本次夹具/渲染复现材料，含本机固定路径，运行前核对目标只能属于自己的临时目录。运行 Studio 必须 scripts/launch_studio.py --no-browser，固定 8765。不要把测试绑定或临时状态用于日常项目。

捕获 scripts/qa/capture_ps3_studio.mjs 需要 PS3_PLAYWRIGHT_MODULE、PS3_CAPTURE_CONFIG、PS3_DESIGN_PATH、PS3_CONTRACT_PATH、PS3_SHOTS_DIR；启动前先用 API 读取项目，缓存 probe，避免持有浏览器槽时再次请求 probe 的排队浏览器。用 withChromiumSlot.sh -- node scripts/qa/capture_ps3_studio.mjs。所有媒体均 FFmpeg 合成，不执行 ASR、TTS 或付费模型。
