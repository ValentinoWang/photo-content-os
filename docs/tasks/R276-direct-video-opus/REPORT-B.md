# R276 第二段 B 汇报

日期：2026-10-26。两跑、03 单镜重写及最终合成都完成。仅在指定 worktree 修改代码；测试任务与媒体输出使用授权的本机隔离目录。未提交、未推送；未访问或操作 8765。

## 结果与验收范围

- **H-01 的后端链路**：七镜从建任务到全部写好并渲染 **495.902 秒（8 分 15.902 秒）**，满足十五分钟机器时间条件；无自动重写。初次无声预览总耗时 **591.515 秒**。
- **H-02 的后端链路**：带声成片 **1080×1920、30fps、1855 帧、61.833333 秒**，原配音 61.84 秒；差约 0.006667 秒，在半帧以内。视频与音频轨时长差 **0 秒**，实际解码、帧数、黑帧检查通过。
- **H-03**：对第 03 镜原样发送“数字再大一点”，**70.604 秒**完成重写与重渲。只有 03 的代码和海报字节改变，`posterRevision` 从 1 到 2；其他六镜代码、海报字节、`writtenAt`、`posterRevision` 全部不变。重新合成后再核对一次，仍不变。
- 本次没有烧字幕，投影没有 `subtitles` 或 `subtitleBurnedIn` 字段，也没有“字幕已烧录”结论。画面中的标题和图解文字属于镜头 HTML。
- **限制**：本地 FunASR 确实执行，但没有得到覆盖全文并满足严格匹配的词边界，采用 `proportional`。与提供的上游句级时序比较，内部分镜边界最大偏差 **0.986667 秒**。音视频轨同长不能证明逐字切镜精确，不能将该结果写成逐字对齐通过。
- 上述是接口、渲染、媒体检查和关键帧证据。没有代替真人签署 H-01–H-03，也没有进行 Studio 前端页面验收。

## 环境与输入

独立 Studio 端口 **8766**，状态目录 `~/.photo-content-os/studio-r276/`；先原样复制 `~/.photo-content-os/studio/creative-projects.json`。作品标题匹配“断更一年，我拆了四句话”，编号 `project-fc6baa3294`。未修改原状态文件或原配音。

运行时配置：

- `VIDEO_RENDER_PLAYWRIGHT_MODULE`：用户指定上游 Web 的 `node_modules/playwright/index.js`，版本 1.61.1。
- `VIDEO_RENDER_BROWSER`：用户指定 `chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`。
- 旧 `VIDEO_RENDER_TEST_BROWSER` 保留为次优先级兼容别名；最终旧渲染器测试也设置该别名指向相同浏览器。
- `.venv` 临时软链接到主检出的固定环境，没有安装或更改依赖；收尾移除。
- 模型通过 `llm_common.generate_text` 请求 `claude_cli / claude-opus-5-5`，继承 account3 登录目录。未替换模型、转写器或渲染函数来生成真跑证据。

**输入差异已核对并记录**：`run23/final-video.json` 的 `shots` 实际为空，保留了完整口播和 **15** 条 `sentenceTimings`；其对应的 v4 项目分镜实际为 **11** 镜。为按本次十镜要求执行，将原 v4 第 06、07 镜相邻两段合并成一镜。所有原话、顺序均保留，十镜拼接与 `final-video.json` 的 `script` 逐字相等。没有把文件原本的镜数写成十镜。

第二跑严格使用指定七镜 `storyboard.json` 的 dialogue 顺序；与任务输入逐项核对相同。配音上传前后的 SHA-256 相等。

## 第一跑：十镜带配音

任务：`dv_0d6e5d7cd39741d6abeadb19`。

| 阶段 | 用时 / 结果 |
| --- | --- |
| 全片设计 | 28.487 秒 |
| 首次全镜 ready，含标点问题恢复 | 684.720 秒 |
| 本地转写与分配 | 14.132 秒；`proportional` |
| 配音上传到重定时、全镜重渲完成 | 174.254 秒 |
| 按更短实测 D 自动重写 | 0 次；本跑分配时长均长于原估算 D，按新帧数重渲 |
| 初次合成 | 22.080 秒后失败：分段容器时长造成串接偏差 |
| 修复串接后的接口合成 | 18.086 秒后被黑帧检查拦截，未发布候选 |
| 01、05 开场黑帧修复 | 通过单镜 rewrite 分别执行；见下表与 metrics |
| 最终合成与检查 | 38.175 秒；全部通过 |
| 最终成功墙钟总耗时 | **1506.901 秒（约 25 分 7 秒）**，包含诊断、修代码、服务重启及补救重试，不能作为一次顺利生成的耗时 |

另有一个前置尝试因 Claude 可执行文件链接更换期间一度查找失败，在 **187.9 秒**后以失败状态停止；保留 `b1-preliminary-progress.json`、`b1-preliminary-metrics.json`。它不计入上表新任务墙钟，不能隐藏为“无失败一次成功”。本机后续 CLI 恢复后可正常调用。

| 镜 | 模型写代码，各次秒数 | 渲染，各次秒数 | 自动重写 | 额外请求重写 | 最终自查 |
| --- | --- | --- | --- | --- | --- |
| 01 | 69.141 / 21.093 / 59.822 / 26.923 | 16.782 / 17.647 / 24.796 | 1 | 2 | 0 error / 0 warning |
| 02 | 45.417 | 20.069 / 15.233 | 0 | 0 | 0 error / 1 warning |
| 03 | 121.044 | 14.728 / 15.661 | 0 | 0 | 0 error / 0 warning |
| 04 | 73.300 / 29.183 / 93.441 | 13.279 / 12.749 | 1 | 1 | 0 error / 2 warning |
| 05 | 105.165 / 32.241 | 15.663 / 15.395 / 22.404 | 0 | 1 | 0 error / 0 warning |
| 06 | 60.719 | 17.236 / 20.651 | 0 | 0 | 0 error / 0 warning |
| 07 | 98.174 / 27.161 | 14.240 / 19.416 | 1 | 0 | 0 error / 1 warning |
| 08 | 68.404 | 10.513 / 11.204 | 0 | 0 | 0 error / 0 warning |
| 09 | 77.681 | 11.655 / 11.898 | 0 | 0 | 0 error / 0 warning |
| 10 | 96.402 | 17.350 / 18.808 | 0 | 0 | 0 error / 0 warning |

“各次”按同一镜头的发生顺序列出：包括首次、一次 lint 自动重写、修复请求和配音重渲；各镜并行执行，不能把表格横向求和当作整片墙钟。自动重写为单次写镜流程里的第二次模型调用；额外请求为显式单镜修复，未将其伪装成自动重试。

- 自动 lint 重写共 **3 次**：01、04、07 各一次。
- 额外修复请求 **4 次**：01 标点及开场各一次，04 标点一次，05 开场一次。
- 最终所有镜头 **0 error**。提醒保留：02 的 9% 为 91% 的补数；04 的 0%/100% 为轴端点；07 的 50% 对应口播的一半。没有删除 warning 或改成无条件通过。
- 最终合成的十镜均命中已验证帧缓存，没有再次调用 HTML 渲染器。
- 正常速度、静音的 Chromium 播放从头到尾进入 `ended`：**1855 帧、0 丢帧**。这是播放与解码验证，没有声称人工听音完成。

## 第二跑：七镜无声预览与 03 重写

任务：`dv_0e184e961bd14ac084c67411`。

| 阶段 | 用时 / 结果 |
| --- | --- |
| 全片设计 | 22.766 秒 |
| 七镜全部写好并渲染 | **495.902 秒** |
| 初次无声合成与检查 | 95.613 秒 |
| 初次预览总耗时 | **591.515 秒** |
| 03 镜重写与重渲 | **70.604 秒** |
| 重写后重新合成 | 88.640 秒 |
| 最终预览 | 1080×1920、30fps、4284 帧、142.8 秒，无音轨、无字幕 |

| 镜 | 模型写代码，各次秒数 | 渲染，各次秒数 | 自动重写 | 额外请求重写 | 最终自查 |
| --- | --- | --- | --- | --- | --- |
| 01 | 93.193 | 58.449 | 0 | 0 | 0 error / 0 warning |
| 02 | 114.330 | 59.080 | 0 | 0 | 0 error / 2 warning |
| 03 | 83.252 / 31.104 | 75.512 / 38.856 | 0 | 1 | 0 error / 1 warning |
| 04 | 122.683 | 48.312 | 0 | 0 | 0 error / 0 warning |
| 05 | 158.178 | 58.156 | 0 | 0 | 0 error / 1 warning |
| 06 | 146.349 | 55.326 | 0 | 0 | 0 error / 0 warning |
| 07 | 107.186 | 42.664 | 0 | 0 | 0 error / 0 warning |

七镜首次全部一次写成，**0 次自动重写**。03 行第二次模型与渲染为 H-03 指定修改。当前提醒保留为 02 的 0%/50%、03 的 0%、05 的 254；均未提升为 error，也未为了真跑清除。最终镜头均为 0 error。

H-03 的前后证据经真实 HTTP `/code`、`poster.jpg` 读取字节并求 SHA-256，时间和 revision 来自任务投影。`b-h03-proof.json` 记录全部七镜的前后值，`unchangedShots` 为 `01、02、04、05、06、07`，`changedShots` 只有 `03`，`unaffectedAfterComposition=true`。最终关键帧和 03 对照图已亲自查看，数字明显变大，没有裁切。

## 真跑发现的问题与修复

1. **浏览器配置**：`media.py` 优先读正式变量 `VIDEO_RENDER_BROWSER`，再读兼容别名。增加优先级和缺省测试。
2. **SVG 命名空间误报**：`http://www.w3.org/2000/svg` / XLink 用于命名空间标识，不构成资源加载。此前把所有 HTTP 字符串当网络资源；现区分命名空间标识与 src/href、网络 API。真实网络地址、fetch、XMLHttpRequest、WebSocket 仍拒绝。
3. **标点框误报**：单引号与双引号 HTML 等价；真跑候选的 `.pb{display:inline-block;width:1em;text-align:center}` 也实现了规则要求的全角居中。检查现在识别这类等价写法，不强制只有类名 `fw`。反例验证半宽、左对齐、完全未包框仍失败。同时补齐模型提示中原先遗漏的全角标点规则。
4. **分段 MP4 串接时长**：1855 帧原来读成视频 61.832357 秒、音频 61.833333 秒；两个分段容器尾部时长偏小，导致整体平均帧率偏离 30。复用的 `compose.py` 现在按累计帧边界生成显式 concat `duration`，避免容器尾部舍入累积。修后严格检查得到 61.833333 秒和 30/1；没有放宽帧数或时长容差。无声路径复用同一清单生成函数。
5. **真实开场黑帧**：01 与 05 第 0 帧全体透明，成片帧 0、749 被检查拦截。补上每镜第 0 帧必须有不透明页眉及主图雏形的规则，只重写这两镜开场。最终黑帧为 0，原检测阈值未改。
6. **失败投影缺少已测结果**：输出检查失败原来只显示未知；现在保留真实的 playable、音画时差、黑帧结果，并返回 `output_check_failed`。配音任务从合成开始就如实标 `narrated`，失败时也不误标为无声。已补回归。
7. **可核对的耗时与候选**：私有 `metrics.json` 记录设计、每次写代码、lint、每次渲染、对齐和合成；候选 HTML 留在本机任务 `checks/code-attempts/`。这些不进入公共投影或 Git 媒体证据。

B 阶段修改文件：`scripts/direct_video/media.py`、`generate.py`、`lint.py`、`rules/shots.md`，`scripts/video_render/compose.py`，`tests/test_r276_direct_media.py`、`tests/test_r276_direct_video.py`，本报告和文本/JSON 证据。没有重写渲染器。

## 产物与证据

所有媒体在 `~/.photo-content-os/evidence/R276-direct-video-opus/`：

| 文件 | 内容 |
| --- | --- |
| `b1.mp4` | 最终十镜带声成片 |
| `b1-contact-sheet.png` | 最终十镜联系表，1422×1126，已查看 |
| `b2.mp4` | 03 镜重写后的最终无声预览 |
| `b2-contact-sheet.png` | 最终七镜联系表，1140×1126，已查看 |
| `b2-before-rewrite.mp4` | H-03 修改前的预览，用于对照 |
| `shot03-comparison.png` | 03 修改前后对照，已查看 |

仓库只保留文本/JSON：`b-run-summary.json`、两跑 metrics/progress、`b-h03-proof.json`、`b-compose-rounding-proof.json`、`b-blackframe-proof.json`、`b1-source-and-cut-comparison.json`、播放器证据、`b-visual-findings.json`、`b-artifact-manifest.json` 和测试日志。SHA-256、文件字节数和图片尺寸见 manifest，交付文件均实际存在。日志中的本机路径会在最终归档时脱敏。

## 收尾检查

- `tests/test_r276_*.py`：**64 passed，25.24 秒**；其中后端与媒体 59 项，另包含并行会话新增的前端静态回归 5 项。真实浏览器/海报测试已运行，没有因缺运行时而跳过。
- A 里相同相关测试命令：**47 passed、20 subtests passed，83.11 秒**；原先跳过的八项真实浏览器测试本次全部执行。
- `bash scripts/check_runtime_contract.sh`：通过。
- `.venv/bin/python scripts/check_repository_safety.py --base origin/main`：通过（该命令检查已跟踪范围）；本任务新增未跟踪文件另做路径和媒体类型检查，通过。
- `git diff --check`：通过。
- B 未重跑全量 pytest；全量已在 A 执行，本轮按指示跑新增与相关测试。

8766 已在无活动任务时停止；临时 `.venv` 链接收尾移除。未提交、未推送。

worktree 中途出现并行会话的前端文件与前端测试改动：`studio/static/` 下直出相关文件及 `tests/test_r276_direct_frontend.*`。本次未编辑、回退或接管这些文件；前端静态测试通过也不等于本次做过前端视觉验收。

业务项目 git 状态：保留 A/B 后端与证据的未提交改动，以及上述并行前端改动。Harness SSOT：本次没有修改；其仓库有其他会话未提交内容，保持原样。没有创建 declared SSOT bundle 或改动人工验收签署。

本阶段到此停止。仍未做到的是逐字声学切镜通过、人工听音与整页前端/真人验收；这些没有写成已经完成。

相关测试完整命令：

```bash
.venv/bin/python -m pytest -q tests/test_p0_llm_and_evidence.py tests/test_llm_creative_scripts.py tests/test_p5_local_prompts.py tests/test_p2_desktop_server.py tests/test_desktop_openapi_route_sync.py tests/test_full_checklist_acceptance.py tests/test_video_render.py
```

补充隐私盘点：并行会话的 `docs/tasks/R276-direct-video-opus/REPORT-F1.md` 有 12 行本机绝对路径。该文件不属于本次后端交付，保持原样；行号记录在 `new-file-safety-b.json`，交总控处理。本任务文件补充检查通过，不将其扩大表述为整个共享工作树的未跟踪文件都通过。
