# 和设计稿哪里不一样

本轮是**待返工/复核的实现轮，不是验收完成**。已做后端、前端、四道检查及 27 状态 × 4 宽度的实现截图；文案门禁有 1 项失败，设计稿并排图未完成，另有功能缺口见最后一节。按 TASK 的停止规则，不增加未批准文案或元素，停在本汇报。

设计稿 `file://` 打开被浏览器安全策略拒绝（只允许 HTTP/HTTPS）。没有改用本地 HTTP、原始 CDP 或其他浏览器入口去绕过这个拒绝，因此没有生成设计稿截图，也没有把实现截图冒充并排对照。只读核对了设计源码、27 状态文案表及设计编号；mock 目录、私人原照片、视频均未复制进仓库。

| 状态 | 本轮与稿的差异/范围 | 实现截图 | 并排图 |
|---|---|---|---|
| `home` | 真实数据为 7 条待处理、8 件最近作品；最近 8 件恰为无素材的旧测试作品，封面按要求保留底色。诊断修复说明中仍有 doctor 返回的命令行文字。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#home) | 未生成，见下述限制 |
| `inbox` | 真实空状态使用 12 件作品、140 段视频、245 张照片；有当前作品时继续读取原分批/删除建议。未重拍非空整理状态。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#inbox) | 未生成，见下述限制 |
| `projects` | 真实为 3 组、12 件作品，含「其他作品」8 件；名称原样取父目录 manifest，不使用稿中的缩写。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#projects) | 未生成，见下述限制 |
| `project` | 兰大组为 3 件真实作品；封面来自开场候选、成片封面、首张照片缩略图的回退链。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#project) | 未生成，见下述限制 |
| `piece-review` | 真实 128 个镜头：精选 27、可用 71、不用 27、淘汰 3；时长 1:32。按原片拍摄时间排序，先路上而非稿中手定的校运会顺序。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-review) | 未生成，见下述限制 |
| `piece-review-alt` | 主播放器切换到真实备选；展开打分细节，另交检视栏连续分段图。未放「收进素材库」。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-review-alt) | 未生成，见下述限制 |
| `piece-confirmed` | 确认状态由真实媒体数据的内存夹具演示；没有写用户决定。步骤 2 显示确认标记。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-confirmed) | 未生成，见下述限制 |
| `piece-partial` | 内存夹具模拟 9/18 页，路上相关 72 条暂不计入分类；剩余精选 13。没有改真实 shots.json。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-partial) | 未生成，见下述限制 |
| `piece-running` | 假进度 3/18 页；首批展示 36 张，余下可点「再看」。未启动真实模型任务。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-running) | 未生成，见下述限制 |
| `piece-empty` | 用兰大真实作品模拟无挑选结果；仍显示两版已出成片。无实测分类耗时历史，因此不显示预计分钟。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-empty) | 未生成，见下述限制 |
| `piece-not-started` | 使用真实的 224 张照片补充包，无成片。此分支的 AI 挑选说明未进入文案表，是当前唯一 copy.unapproved-text。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-not-started) | 未生成，见下述限制 |
| `piece-script` | 原 renderProject 主体、文档、双轨、状态栏及 MediaClaw 分支保留。旧标题、六步进度、not_started 等旧显示与简化稿有差异，未擅自改写。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#piece-script) | 未生成，见下述限制 |
| `player-reel` | 真实精选样片连播；源片为竖屏时按内容留黑边。播放通过实测。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#player-reel) | 未生成，见下述限制 |
| `player-versions` | 真实已导出成片播放；版本数和可选片数按实际目录，没有使用稿里的演示数量。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#player-versions) | 未生成，见下述限制 |
| `library` | 真实 state 副本没有结构化素材索引，页面为 0 项；未伪造已登记素材。因此非空预览、来源跳转、加入作品缺真实数据截图，空状态也缺批准设计。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#library) | 未生成，见下述限制 |
| `music` | 真实三首：本机、网易云、汽水各一首。默认详情选择网易云曲目；波形来自各自实测缓存。音乐表格已与旧时间线样式隔离。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music) | 未生成，见下述限制 |
| `music-empty` | 仅在内存响应中模拟空库，未删除三首真实曲目。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music-empty) | 未生成，见下述限制 |
| `music-importing` | 假网络响应的后台导入状态；没有发平台请求。未画虚假的百分比进度。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music-importing) | 未生成，见下述限制 |
| `music-dup` | 假网络响应模拟重复结果；实际一次联网/缓存行为由 R210 的假网络测试验证。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music-dup) | 未生成，见下述限制 |
| `music-vip` | 假网络响应模拟会员结果；不是对真实歌曲会员状态的判断。换平台按钮接 R210 search_elsewhere。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music-vip) | 未生成，见下述限制 |
| `music-douyin` | 假网络响应；后端使用 R210 的 DOUYIN_IMPORT_FAILURE_MESSAGE。未访问抖音。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#music-douyin) | 未生成，见下述限制 |
| `settings-places` | 真实计数与项目/音乐/素材页一致。归档生命周期和位置目前只读；更换/登记操作未补齐。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-places) | 未生成，见下述限制 |
| `settings-tools` | 读取此工作树的真实 doctor 结果；工具尚未就绪的状态与主目录安装情况可能不同。导航仍带既有共享样式的细分隔线，待 Claude 对稿。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-tools) | 未生成，见下述限制 |
| `settings-models` | 预算加减与保存接原版本接口；当前手动模型配置为 0。添加模型入口及只有 CLI 时的呈现未补齐。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-models) | 未生成，见下述限制 |
| `settings-music` | 仅检查出口文件格式/权限与本地网易云会话；不展示服务器地址、不访问平台。出口不存在时的文案仍需批准。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-music) | 未生成，见下述限制 |
| `settings-account` | 真实为未配对，与稿中已连接不同；配对、解除配对、网页中台沿用原接口和面板。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-account) | 未生成，见下述限制 |
| `settings-doctor` | 此工作树为 14 项检查、8 项通过、6 项待处理；问题说明除 ChatCut 外来自 doctor。没有冒充主目录或生产诊断。 | [四宽完整截图](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html#settings-doctor) | 未生成，见下述限制 |

实现截图入口：[gallery.html](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/gallery.html)。108 张完整页面 PNG 加 4 张检视栏连续部分；[screenshot-manifest.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/screenshot-manifest.json) 记录真实视口、路由、时间、尺寸、覆盖范围与 SHA-256，[artifact-verification.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/artifact-verification.json) 已核对所有链接目标及散列。没有伪造长截图。确认/部分完成/运行中/导入错误等不宜改真实数据的状态明确标为内存夹具；照片、帧、音频、成片仍来自真实素材根。

Codex 自查只作参考：查看了桌面/手机首尾及全页缩览，重点全尺寸查看挑镜头、音乐、预算和部分完成。1180/900 宽度做了实际视口截图和机械检查。**尚无 Claude 看图结论，无真人验收，不写视觉 PASS 或 READY。** 截图清单保持 `PENDING_CLAUDE`。

# 后端接口清单

| 方法 | 接口 | 结果/约束 |
|---|---|---|
| GET | `/api/review/catalog` | 项目组、作品、清单数量、成片版本、封面、待过目状态；父 manifest 损坏报错，不当作无项目 |
| GET | `/api/review/pieces/{pieceId}/shots` | 合并 AI 最终结论和用户决定、四栏计数、精选顺序/时长、确认状态、三步进度 |
| POST | `/api/review/pieces/{pieceId}/decisions` | `expectedVersion` CAS；原子写 decisions；确认绑定精选摘要和证据摘要；修改后作废确认；体检淘汰不可改 |
| POST | `/api/review/pieces/{pieceId}/jobs` | start/restart/resume/stop；同一素材工作区互斥；续跑复用本地体检；进度留在作品目录；关闭服务清理拥有的进程组 |
| GET | `/api/review/pieces/{pieceId}/media/shot/{shotId}` | H.264/AAC 派生样片 |
| GET | `/api/review/pieces/{pieceId}/media/frame/{shotId}-{index}` | 编号对应的派生帧图 |
| GET | `/api/review/pieces/{pieceId}/media/output/{outputId}` | output/v* 中的已导出成片 |
| GET | `/api/review/pieces/{pieceId}/media/poster/{outputId}` | 成片封面缓存 |
| GET | `/api/review/pieces/{pieceId}/media/photo/{photoId}` | state 中的首张照片缩略图；核对清单编号 |
| GET | `/api/review/assets/{assetId}/preview` | state 中的素材派生预览；未知索引项 404 |
| GET | `/api/review/music` | 复用 MusicLibrary；返回曲目、授权、实测时长和 peaks |
| GET | `/api/review/music/{trackId}/audio` | 编号查库内音频，本机文件不返回 file:// 原页面链接 |
| GET | `/api/review/music-settings` | 出口、网易云会话分别给 configured/absent/unreadable；不返回出口地址或凭据 |
| POST | `/api/review/music/import` | 后台分享链接或主目录内文件夹导入，复用 R210 导入与缓存逻辑 |
| GET | `/api/review/imports/{jobId}` | 导入中、重复、会员、其他人话失败等结果 |

媒体 GET 同样限制 loopback Host；按编号查找，不接受路径查询；未知编号、路径穿越、原片入口、越出派生目录的符号链接均 404。视频/音频支持单个 Range 的 206/416，响应分块读取，CSP 增加 `media-src 'self'`。公开投影不返回原片路径。

新增 `select_shots.py --previews-only` 与 `--resume`。Studio 启动器在后台补缓存；`prepare_studio_media.py` 也可单独补缓存。兰大已有结果补出 123 个视频样片，抽检 3 个为 H.264 + AAC、540 高、faststart；三首音乐均有 180 段 RMS peaks。未重新挑选、未调用模型、未改真实决定。

主要实现：`studio/media_review.py`、`studio/review_jobs.py`、`studio/server.py`、`studio/api_contract.py`、`studio/static/review-*.js`、`review.css`、`scene-names.json`、`scripts/shot_previews.py`、`prepare_studio_media.py`、`select_shots.py`、`import_music.py`；原工作区主体继续由 app.js 渲染。`studio/README.md` 已改隐私说明。

# 测试和检查结果原文要点

| 检查 | 结果原文/范围 | 证据 |
|---|---|---|
| 负例先行 | 首轮缺模块为红；后续 AI 质量降级、损坏决定、同工作区别名双启动均先红后修 | [red.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/red.log)、[red-final-quality.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/red-final-quality.log)、[red-corrupt-decisions.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/red-corrupt-decisions.log)、[red-job-alias.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/red-job-alias.log) |
| 干净原 HEAD 的相关套件 | `36 passed` | [clean-head-focused.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/clean-head-focused.log) |
| 干净合并基线的既有相关套件 | `100 passed in 15.00s`；由未混入 R220 的合并 index tree 导出，不创建提交/额外 worktree | [clean-merged-focused.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/clean-merged-focused.log)、[clean-merged-tree.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/clean-merged-tree.txt) |
| 当前相关套件 | `95 passed in 42.86s`；含 R220 新合同；其余既有相关套件亦包含于全量运行 | [final-focused.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/final-focused.log) |
| 当前全量 pytest | `11 failed, 726 passed, 32 skipped, 6 errors, 1982 subtests passed` | [final-pytest.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/final-pytest.log) |
| 开工全量基线 | `11 failed, 711 passed, 32 skipped, 6 errors, 1982 subtests passed` | [baseline-pytest.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/baseline-pytest.log) |
| Runtime contract | `Repository safety check passed`、`compileall=ok`、`packages=ok`、`Runtime contract check passed` | [runtime-contract.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/runtime-contract.log) |
| Obsidian doc sync | FAIL：三个文档对提示 source newer than target；本轮未改其覆盖文件，未改 marker 或时间戳放行 | [obsidian-sync.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/obsidian-sync.log) |
| Outline contract | FAIL：调用上述 doc-sync 检查失败 | [outline-contract.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/outline-contract.log) |
| 两个验证 CLI 的 --help | 均正常退出 | [task-help.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/task-help.log)、[draft-help.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/draft-help.log) |
| 四道检查 1：文案表 | **FAIL 1 项**：piece-not-started 的无成片说明缺少对应文案表条目 | [design-check.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/design-check.log) |
| 四道检查 2：设计编号 | 27 状态未报 missing/unapproved ID；combined checker 的唯一失败为上项文字 | [design-inventory.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/design-inventory.json) |
| 四道检查 3：数字公式 | 31 组公式，0 差异、0 状态身份/横向溢出错误；含计数、场景、进度比例、时长、项目、工作台、音乐和诊断 | [number-formulas.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/number-formulas.json)、[number-negative.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/number-negative.log) |
| 四道检查 4：人话静态检查 | `PASS (5 file(s), 0 warning(s))`；仅词法事实，不代表观感或真人通过 | [ui-copy-quality.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/ui-copy-quality.log) |
| 真浏览器走查 | 14 项通过：实际镜头/成片/音乐播放、分段跳转、声音、波形跳转、分页和刷新、新建取消、配对入口、存储被禁、延迟回包不覆盖新导航等 | [browser-walkthrough.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/browser-walkthrough.json) |
| 预览 CLI/编码 | `--previews-only` 正常退出；123 个缓存，抽检 3 个编码/faststart | [previews-only.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/previews-only.log)、[preview-codecs.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/preview-codecs.json) |
| 真实决定保护 | 原 state 与副本 creative-projects.json SHA-256 相同；真实兰大 decisions.json 仍不存在，无需删除 | [original-state-check.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/original-state-check.json) |
| 截图交付检查 | 108 个主截图 + 4 个检视栏部分，27 状态、四宽齐全，全部文件与散列匹配 | [artifact-verification.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/artifact-verification.json) |

全量失败集合与开工基线相同，没有修改这些测试来放行：字幕渲染 4 项、edit_tools_runtime 2 项、doc sync 1 项、pf_video_pipeline 4 项失败及 6 项 setup error。它们分别涉及现有 FFmpeg 字幕/合成环境、剪辑工具状态断言和文档同步；只列出，未修别人范围。R220 的无模块/AI 降级/媒体/原导航源码断言等新失败已修复。数字合同的正反例已接入正常 pytest 命令，另有音乐标题宽度四视口正反例。

测试与截图未发真实音乐平台请求。R210 网络结果用假适配器，UI 导入结果用拦截响应；浏览器只允许本机 origin。广州出口仅校验本地配置，没有把配置可读说成远端下载已验证。

资源已收尾：Studio 端口关闭，拥有的采集浏览器、3 个 CUA 创建标签和后台进程已关闭；没有关闭用户原有浏览器标签。见 [cleanup.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/cleanup.json)。临时 state 副本留在仓库外，重现路径见 [state-location.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/state-location.txt)。

Git 状态：

- 工作树 HEAD 保持 `aafbd2490c51886e648dc544c4f1444be632c8b8`；原两笔 R208 A2 提交保留。已 fetch，并将 `origin/main` 的 `7c1c0416a144e965100080d078dd30d59f3c56c2` 合入 index/工作区。唯一冲突 requirements-dev.txt 已保留两侧依赖解决；**MERGE_HEAD 尚在，因用户禁止提交，没有创建 merge commit**。本轮实现文件未提交，未推送，未 rebase/force。原 R208 未跟踪证据未删。
- 主目录仅由本轮写入本 REPORT；其余会话的未提交改动没有处理。[business-main-status.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/business-main-status.txt) / [worktree-status.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/worktree-status.txt)。
- Harness SSOT 本轮只读、没有改动；其目录本身有其他会话的脏状态，不能写成 clean。[harness-status.txt](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/harness-status.txt)。
- 合并后人工日志含 R210 的 blocking PENDING 与 R207 的非阻塞 PENDING。未替用户通过或改状态；本轮也未建立 release/handoff。worktree check 因保留未合并提交和未提交文件为红，符合本轮“不提交不 finish”的停止范围，原文留在 [worktree-check.log](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/worktree-check.log)。
- 工作树缺少 `develop/harness/fullstack-ai-harness.md`；实际读取的是 TASK 指定的 Core SSOT 正文和项目 adapter，没有补造链接或改 Harness。

# 需要新文案

1. **当前门禁项，piece-not-started**：无成片时的独立说明是设计源码已有句子，但未进入导出的该状态文案表：
   > AI 会把每段视频切成镜头，先在本机量清晰度、曝光和抖动，再让大模型看图，挑出这条视频要用的精选。原素材只读，不会被改动。
   建议总控补上这个真实分支后重新提取文案表；本轮不扩 approved-extras、不拆节点规避检查。
2. 真实素材索引为空时，需要批准空状态说明和可走的登记/返回入口；目前没有编造素材或新增说明。
3. 下载出口不存在时，需要批准「未配置」一类的值及下一步。已避免把出口缺失说成账号「没登录」；缺失值暂不显示，未擅自加文案。
4. 模型只有 CLI 可用、没有手动 provider 配置时的显示，以及模型配置/存放位置相关操作，需要明确批准的状态和表单。
5. 后台挑选失败、不可读、停止后未完成等恢复提示及未连接素材目录作品，需要补足状态稿；当前后端保留明确状态/错误，不切换脚本、模型或编辑器。
6. doctor 原始修复说明中有开发命令路径；TASK 要求动态沿用，故未擅自翻译。若要面向普通使用者改写，需总控给文案。未知授权曲目未额外添加未入表的通用劝告。

approved-extras 只含 TASK 明确允许的未连接状态和原样保留的脚本主体旧词；动态值用 data-design-data 标记，没有把上述失败项加白名单。原文件为 [approved-extras.json](/private/tmp/task-worktrees/photo-content-os-r208-a1/evidence/2026-10-20/R220/approved-extras.json)。

# 稿外元素

没有新画一套 IA、没有新增能点却无效果的「下一步：配乐卡点」或「收进素材库」。新建/文件夹导入沿用 TASK 批准的对话框文字。

保留的旧脚本主体带原来的二级标题、旧六步条、交付状态及既有入口；按 TASK 不改行为，故相对简化稿仍多这些旧元素。真实数据的错误/零配置/无素材分支在现稿中不全；本轮没有自作新增布局。请由 Claude 处理这些缺口及样式继承差异，再决定下一轮。

# 没做完的

- 文案表 1 项失败未豁免；**四道检查没有全部绿**。
- 27 状态四宽的**设计稿截图及 108 张并排对照图为 0**；浏览器策略限制未绕过。实现截图已交，尚需 Claude 对稿与逐页判断。
- 素材库真实副本没有索引：非空预览、来源跳转、加入作品尚缺真实数据端到端证据；未选择当前作品时的加入流程仍需补齐。单个镜头片段不能由现有登记合同直接登记，故按 TASK 隐藏收进素材库。
- 模型添加、更换/登记存放位置和生命周期操作没有补齐；预算加减/保存接口已接。未把旧占位提示包装成完成动作。
- 按每段视频/每张照片记录历史实测耗时的估算尚未完成；当前没有这类历史，估时项按要求隐藏。
- 正在挑选的三步显示当前阶段的实际完成/总数，过去阶段的分项计数尚未完整保留展示。真实长时模型任务未在本轮重跑，启动/停止/续跑使用假进程验证。
- 统一媒体 OpenAPI 路由目前以 video/mp4 为主要响应描述；帧/封面等混合 MIME 的精细 schema 仍需补齐。实际 HTTP MIME 按文件正确返回。
- Obsidian 文档同步、outline 与全量基线失败未擅自修复；R210 人工 blocking 仍待处理。本地预览不代表生产或全站通过。
- 没有 Claude 视觉认可、真人验证、验收卡、提交或推送。后续只能在总控补齐文案/状态并批准后继续；本轮在汇报后停止。
