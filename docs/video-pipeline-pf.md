# Photo 原生视频候选交接

Photo 用已有 Media Agent 的 `runtime_factory`，不另外建立任务队列。设备下载后的 `handoff.json` 和同目录 `video.json` 必须属于当前确认的作品、版本和 Photo 项目。CreativeProject、媒体根目录和脚本参数仅来自本机绑定；`LOCAL_MEDIA_ROOT` 指向素材根，软件目录不参与素材寻址。

本机 binding 保持 MX 的七项：`identity`、`handoff_digest`、`creative_store`、`project_root`、`steps`、`candidate_ref`、`source_refs`。`source_refs` 包含口播原片；直出线包含原始配音 WAV。每一步必须使用对应脚本的真实函数签名。

参数支持 `{"local_ref":"相对路径"}`（转成 Path）、`{"json_ref":"相对JSON文件"}`（读 JSON）、`$handoff`、`$project_root`、`$tts_path`、`$output_root`。`$output_root` 指向本次 run 内该 action 的独立目录，避免将日志和渲染缓存混在一起。真实函数返回值落入本机 `native-<action>.json`，不回传原生返回值或日志。后一步可使用 `{"runtime_ref":"native-suggest.json"}` 读取本次返回值，或用 `{"runtime_path":"native-suggest.json"}` 传它的 Path；这些引用限定在当前 run，不能读取其他任务。

口播步骤示例（其余身份和 store 仍由本机明确配置）：

```json
[
  {"action":"suggest","function":"generate_suggestions","kwargs":{
    "audio":{"local_ref":"audio.wav"},"transcript":{"json_ref":"transcript.json"}}},
  {"action":"kdenlive","function":"render","kwargs":{
    "source":{"local_ref":"source.mp4"},"suggestions_path":{"runtime_path":"native-suggest.json"},
    "subtitles":{"local_ref":"source.srt"},"animations":{"json_ref":"animations.json"},
    "output_dir":"$output_root","project_id":"confirmed-project","project_revision":1}}
]
```

Kdenlive 是本机配置明确选择的 action；ChatCut 未连接不会暗中改用 Kdenlive。`chatcut_desktop` 是注册名，真实 `tools/list` 的工具名和 schema digest 单独绑定。未握手不会 online，未导出不会生成候选。动画配置保留 `animation_id`，几何为 `{x,y,width,height}`（时间线像素）；未指定几何时保留动画原始尺寸。MLT entry 裁切源区间，producer 从第 0 帧开始；工程具有 bin、可编辑音视频轨和 sequence。字幕放在底部 20% 区域。

直出使用 `compose` action / `compose` 函数，参数 `manifest_path` 指向 PC 的私有 manifest，`output` 使用 `$output_root`。manifest 的镜头 id 与确认分镜的 `shotId` 完全相同（MC 当前为两或三位数字），不能按顺序猜绑定。字幕取确认分镜的字幕栏和实际时段；缺字幕或越界就阻断。原始 HTML、固定字体、图片和 WAV 在本机准备，未实现从云端自动生成这些素材。

转写步骤用 `transcribe_project(project=..., provider_name=..., model=...)`，由 bridge 的 `--live` 决定是否允许在线转写，本机 kwargs 不能覆盖它。`fun_asr` 是在线 Fun-ASR，`funasr` 是本地模型，二者不混用。分析 CLI 需显式 `--audio --transcript-provider fun_asr --transcript-model fun-asr --live`；离线夹具用 sidecar 或现成转写 JSON，并在分析入口加 `--skip-llm`。

`video_candidate.project_candidate` 对实际输出做解码、AV 差、帧数、输入 hash、字幕单调和黑帧检测。PC 直出先生成本机字幕烧录版，再生成低清；PB 已烧录的字幕不重复烧录。字幕区域顶部比率为 0.8。预览限制短边 ≤480、长边 ≤854、20,000,000 字节、H.264/AAC；超预算明确失败。源时长保留实际探测值；不同帧率转换产生的末尾不足一帧差值不冒充剪点，真实末尾剪点不超过原片时长。波形来自原始音轨 8 kHz 单声道 PCM 的实测峰值包络，最多 400 点，静音保持零值。

runtime 的唯一 JSON 回执和项目 `candidate_ref` 使用 `{candidate,preview_ref,progress}`。`preview_ref` 相对于 Agent workspace；candidate 采用 MC 字段和规范摘要。本机 placeholder preview artifact 只提供实际字节 hash/大小；Agent 上传后替换为服务端 artifact（含真正 downloadPath），重新计算 candidateDigest。preview 使用权威 schema 的 `shortEdge/longEdge`；不新增 `durationSeconds`。原片、工程、高清成片、帧目录、绝对路径和诊断不进入这个投影。

`retry_video_shot(run_ref,shot_id=...,inputs={"workspace_ref":...})` 仅接受完整 descriptor 的同一 `retryShotId`、同一已存在 run 和明确 compose 步骤。保留配音及其他镜头缓存；另一镜 hash/依赖变化时阻断，不能顺便重渲。节点仍记入原 runtime SQLite。运行中、未知或非直出任务不能借这个入口重跑。

机器回归：`tests/test_pf_video_pipeline.py`、`tests/test_pf_agent_runtime.py` 和 `tests/test_video_render.py`。前两类 source-clock/原生 Agent 验证与浏览器资源清零验证均不代表真人精修、云端采用或生产部署。固定 Agent 环境、Playwright 路径与运行命令见 PF-REPORT.md。

## 安装仓库内剪辑工具

先运行 `bash scripts/setup_edit_tools.sh`（Windows：`powershell -ExecutionPolicy Bypass -File scripts/setup_edit_tools.ps1`），再运行 `.venv/bin/python scripts/doctor.py`。也可直接运行 `python3 scripts/setup_edit_tools.py`。

`third_party/edit-tools.lock.json` 锁定 OpenChatCut 0.2.16 的完整 Git 提交、OpenFilm 0.1.5、Node 24.13.0 与 Playwright 1.61.1 的 Chromium。安装器校验 Node 下载摘要，用 `npm ci` 安装锁文件依赖；源码、依赖与浏览器均放在 Git 忽略的 `.tools/`。重复执行保留匹配的工具，发现版本漂移或安装损坏会明确报告并重装。不会安装或升级系统应用。

适配器默认从当前检出根的 `.tools/` 寻址。可继续显式设置 `CONTENT_OS_OPENCHATCUT_ROOT`、`CONTENT_OS_OPENCHATCUT_NODE`、`CONTENT_OS_OPENCHATCUT_BROWSER`、`CONTENT_OS_OPENCHATCUT_REFINE_BROWSER`、`CONTENT_OS_OPENFILM_PACKAGE`；OpenFilm Node 可由 `CONTENT_OS_OPENFILM_NODE` 覆盖，其浏览器目录可由 `PLAYWRIGHT_BROWSERS_PATH` 覆盖。缺失或不支持的版本会阻断所选后端，不会换用其他后端。

浏览器通过 `scripts/qa/with_chromium_slot.sh` 排队；默认共用 `/tmp/openclaw-media-chromium-slots`，保留所有 `MEDIA_CHROMIUM_*` 参数。`CONTENT_OS_CHROMIUM_SLOT`（OpenChatCut）和 `CONTENT_OS_CHROMIUM_SLOT_SCRIPT`（OpenFilm）仍可显式覆盖。Mac 需要系统 `lockf`，Linux 需要 `flock`；Windows 原生浏览器排队尚需提供兼容的 Bash/锁工具，未满足时明确阻断。

命令行若未继承系统的 PAC 代理，请先按本机网络配置设置标准 `HTTPS_PROXY` / `HTTP_PROXY` 再安装；安装器只继承当前命令的网络设置，不修改系统代理。
