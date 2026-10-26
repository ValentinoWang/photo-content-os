# R283 视频风格加风格库 · 任务单（样张段 S 和后端段 B 并行）

需求卡：「脚本直出的视频风格加风格库：九种现成风格直接挑 · 待确认（2026-10-26-R283-photo-direct-style-library）」，在本 worktree 的 `acceptance/requests/2026-W44/2026-10-26-R283-photo-direct-style-library/`（只读）。验收项 H-01–H-03 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。用户 2026-10-27 定：R278 验收的同时就做 R283。前端段等样张段做完再另派。

## 0. 位置和边界

- 只在任务 worktree 里改，就是 R278 那个。
  - HEAD 是 `130c931`：R278 的代码和验收物都已提交，等用户验收。
  - 不许 `git worktree add`，不许改主目录，不提交、不推送，不改写已有提交。
- 端口 8765–8769 上的 Studio 都不许动；状态目录 `~/.photo-content-os/studio-r276`、`studio-r278` 只读。
  - 8769 是用户正在验收 R278 的 Studio，已经改从总控 scratchpad 里的导出副本运行，不在本 worktree。
- **本机例外预算**（用户定了 photo-content-os 在本机跑）：
  - 浏览器只开无头的，同一时间只开一个，用完就关；
  - 渲染排队，一个接一个跑；
  - 不跑全量 pytest；
  - 磁盘低于 3 GB 停下汇报。
- 两个线程同时跑，各改各的文件，见下面 S、B 两节。别人的文件不碰；需要对方改的写进汇报。
- **设计稿以它为准**：`docs/tasks/R278-direct-rescript/design/spec.html` 里标「R283」的规则、文案、接口、门禁，状态 `first-lib`、`first-none`、`library`。给用户看的预览在同目录 `index.html` 第 5 节。
- **改一个名字**：spec 写的数据目录 `scripts/direct_video/styles/` 改成 `scripts/direct_video/style_library/`。原因是 R278 已经有模块 `scripts/direct_video/styles.py`，同名目录会和模块混淆。下面都用新名字。
- 遇到要拍板的事：先做不受影响的部分，写进汇报后停下。

## S 样张段（cdx 2）

**你改的文件**：
- `scripts/direct_video/style_library/` 下的数据文件：`<id>.html`、`<id>.json`、`<id>.jpg`、`<id>.mp4`、`index.json`、`README.md`、`LICENSE-code-video-showcase.txt`；
- 新建 `scripts/direct_video/render_style_sample.sh`；
- `docs/tasks/R283-direct-style-library/` 下的汇报。

**步骤**：

1. 先读 `docs/tasks/R283-direct-style-library/SAMPLES-TASK.md`。这是原来给子代理的样张任务单，内容、硬规则、从配方改什么留什么、json 字段、合格线都照它；里面的路径按本节改。配方原文和上游许可在同目录 `reference/`。
2. **现状**：
   - `flat`、`math` 已经真画出来了，html、json、jpg、mp4 都在 `style_library/`；
   - `launch` 有 html 和 json，还没渲染；
   - `whiteboard`、`dataviz` 只有写了一半的 html；
   - `cyber`、`ink`、`pixel`、`code` 还没开始。
   已经画出来的两种，也按合格线复看一遍。
3. **写 `render_style_sample.sh`**，照 `docs/tasks/R283-direct-style-library/render_sample.reference.sh` 改成在本 worktree 里跑：
   - 用 worktree 的 `.venv`、`scripts/direct_video/lint.py`、`scripts/video_render/multi_shot.py`；
   - Playwright 和浏览器从环境变量 `VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER` 读，没有就报错退出；
   - 用锁保证同一时间只渲染一个；
   - 输出 `style_library/<id>.jpg`（最后一帧 360×640）和 `<id>.mp4`（360×640，无声）；
   - 工作目录和联系表放 `~/.photo-content-os/evidence/R283-direct-style-library/work/<id>/`，出完图就删原尺寸帧；
   - 脚本里不许有本机绝对路径（仓库安全检查会拦），用 `$HOME` 和相对路径。
4. **九种都做完**：每种有 html、json、jpg、mp4。每张都用 Read 读联系表和最后一帧逐张看，每种最多改三轮。
5. **`style_library/index.json`**：顺序是 `flat, math, launch, whiteboard, cyber, ink, dataviz, pixel, code`。
6. **`style_library/README.md`**：写明「改写自 Moessif/code-video-showcase 的风格配方（MIT），上游提交 2a5fb1f」，每种改了什么（取 json 里的 `adapted`）。把 `reference/LICENSE-code-video-showcase.txt` 复制一份到 `style_library/`。
7. **汇报**写到 `docs/tasks/R283-direct-style-library/REPORT-S.md`：每种一行，写合格与否、规则检查的 WARN、改了配方哪里、做不到的地方；再列出每张联系表的路径。写完停止。

## B 后端段（cdx 1）

**你改的文件**：
- `scripts/direct_video/` 下的 .py：风格库的读取放进 `styles.py`，或者新建 `style_library.py` 模块；
- `studio/direct_video.py`、`studio/direct_style_contract.py`、`studio/server.py`、`studio/api_contract.py`、`schemas/studio-openapi.json`；
- 新测试 `tests/test_r283_style_library.py`。

`style_library/` 下的数据文件归 S，不许改。

**照 spec 第 5 节标 R283 的三行、第 6 节「R283 后端」那一条做**：

1. **读风格库**：读 `style_library/index.json` 和每种的 `<id>.json`、`<id>.html`、`<id>.jpg`、`<id>.mp4`。校验：
   - `palette` 四个颜色，`typeScale` 三个整数；
   - `motionSummary` ≤30 字，`bannedShort` 1–8 条、每条 ≤12 字；
   - `motionRules`、`banned`、`visualGrammar` 都要有。
   不合格的那一种不出现在列表里，并写日志。
2. **`GET /api/direct/styles`** 多一个 `library: [{id, name, design: {palette, typeScale, motionRules, banned, motionSummary, bannedShort}, posterUrl, clipUrl}]`，顺序照 `index.json`。
   再加 `GET /api/direct/styles/library/{id}/poster.jpg` 和 `…/clip.mp4`，支持 Range，未知 id 返回 404。
3. **`POST …/direct/jobs` 的 `styleBase` 多一种 `{kind:'library', id}`**：
   - `style` 为空 → 全片设计照 `<id>.json` 原样复制，不调模型定设计；
   - `style` 不空 → 只在这套设计上按这句改，只调一次模型，和沿用并改走同一条路；
   - 写每一镜的提示里多两样：`visualGrammar` 当作 `form_profile.visual_grammar`，这样 `rules/shots.md`「默认禁用」里和这一风格冲突的条目按它来；`<id>.html` 当作「同一风格的一镜样例，内容不同，只照画法」。R277 的重写这一镜也一样带上；
   - 未知 id 返回 404 `style_base_not_found`。
4. **任务投影**：`design.source.kind` 多一个 `'library'`，`{kind:'library', id, name, instruction}`。
5. **测试**：
   - 逻辑测试用临时目录里的假风格库；
   - 另写一条读真实 `style_library/` 的测试：列 9 种、每种四个文件都在、字段合规、九份样张代码过 `lint.py` 没有 ERROR。这一条要等 S 做完才会过：你结束时它没过就写进汇报，不要为了它改数据文件。
   - 先在现有代码上跑一遍，确认会失败，再实现。
   - 测试里不真调模型，这一段也不做真跑。
6. **跑哪些**：`tests/test_r283_style_library.py`、`tests/test_r278_*.py`，再加 R276、R277 的 .py 测试，但跑时**不设** `VIDEO_RENDER_*` 环境变量，让真渲染的用例跳过：渲染排队给 S 用，真渲染留到交付时再跑。跳过了几条写进汇报。
7. 契约、OpenAPI 同步；投影里不出现本机绝对路径。
8. **汇报**写到 `docs/tasks/R283-direct-style-library/REPORT-B.md`：改了哪些文件；实现前失败、实现后结果；真实风格库那条测试的状态；跳过的用例；需要 S 配合的地方。写完停止。

## 交接

- 2026-10-27 两段都做完了：
  - 样张段 S：cdx 2，线程 `01a1794e-b2cd-…`，汇报 `REPORT-S.md`。九种样张都真渲染过，总控把九张拼在一起看过，都合格。
  - 后端段 B：cdx 1，线程 `01a1794e-b615-…`，汇报 `REPORT-B.md`。样张补齐后，`tests/test_r283_style_library.py` 34 项全部通过。
- 样张媒体进不进 Git：用户同意逐个文件登记放行。总控已在 `scripts/repository-safety-media-allowlist.json` 登记 18 个文件（9 张 jpg、9 段 mp4，每个写了理由和 SHA-256）。以后改样张，要同步更新对应的 SHA-256。
- 设计稿更新：风格库在「选现成的风格」里一直显示，删掉了 `first-none-r278` 状态，`lib-data.js` 换成九种真数据，`contract.json` 重新生成，共 120 个状态。
- 前端段 F：cdx 2，续跑线程 `01a178b3-…`，任务单 `FRONTEND-TASK.md`，汇报写到 `REPORT-F.md`。
