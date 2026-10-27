# R282 中台交过来的分镜和配音直接进脚本直出 · 任务单（后端 B 和前端 F 并行）

需求卡：「中台交过来的分镜和配音直接进脚本直出 · 待确认（2026-10-26-R282-photo-direct-handoff-storyboard）」，在本 worktree 的 `acceptance/requests/2026-W44/2026-10-26-R282-photo-direct-handoff-storyboard/`（只读）。验收项 H-01–H-03 原样照卡。

总控：Claude 会话 `f43dc626-4d80-4822-a763-33a7a646fc64`（photo-content-os-f8）。R278、R283 已在主分支（origin/main `614c550`），本卡接在它们后面。用户已认可设计稿，由 Codex 实现。

## 0. 位置和边界

- **只在任务 worktree 里改**：`photo-content-os-r282-direct-handoff`，用 `task_worktree.py` 建的，基于 origin/main `614c550`，`.venv` 软链到主目录。
  - 不许 `git worktree add`；
  - 不改主目录；
  - 不提交、不推送。
- 端口 8765–8769 上的 Studio 都不许动；`~/.photo-content-os/` 下现有的状态目录只读。门禁用 8768。
- **中台仓库**（`~/Desktop/创业项目/自媒体创作Agent`）只读，不许改；本卡不改中台界面，也不改中台原来那条本机渲染线。
- **本机例外预算**：
  - 浏览器只开无头的，同一时间只开一个，用完就关；
  - 不跑全量 pytest；
  - 磁盘低于 3 GB 停下。
  - 两个线程同时跑：B 跑 pytest 时**不设** `VIDEO_RENDER_*`，让真渲染的用例跳过；浏览器只给 F 用。
- 两个线程各改各的文件，见下面 B、F 两节；需要对方配合的写进汇报。
- 遇到要拍板的事：先做不受影响的部分，写进汇报后停下。

## 1. 设计稿和现有代码

- **设计稿**：`docs/tasks/R278-direct-rescript/design/`，以它为准。
  - `spec.html` 里所有标「R282」的地方：
    - 第 1 节「从中台交过来」「中台又交过来新版本」，以及配音卡的写法；
    - 第 3 节 `DV-SB-SOURCE`、`DV-VOICE`（R282）；
    - 第 4 节交接相关文案；
    - 第 5 节接口：`GET …/direct/handoff`、`POST …/direct/jobs` 的 `handoff`、「中台又交过来新版本」的判断；
    - 第 6 节标 R282 的门禁。
  - 状态：`first-handoff`、`rescript-newer`。
  - `contract.json` 已包含这两个状态。
- **交接包的现有读法**：`studio/server.py` 的 `_video_handoff_projection`（「按脚本做视频」页在用）。
  - 交接描述文件 `video.json`：`scope: video_handoff_v1`；`identity` 带 `jobId`、`photoProjectId`、`photoProjectRevision`；`shots[]`；配音信息。
  - 身份校验、`PHOTO_STUDIO_VIDEO_BINDING`、workspace 的找法都照它，不另起一套。
  - 中台那边的格式：中台仓库 `agent/openclaw_media/video_exchange.py`、`apps/media/web/src/media/creation-workbench/CreationVideoPanel.tsx`（只读）。
- **R276/R278/R283 的脚本直出代码**：`studio/direct_video.py`、`scripts/direct_video/`、`studio/static/direct-*.js`；任务单和汇报在 `docs/tasks/R276-…`、`R278-…`、`R283-…`。

## B 后端段（cdx 1）

**你改的文件**：
- `scripts/direct_video/*.py`；
- `studio/direct_video.py`、`studio/direct_style_contract.py`（或新建 `studio/direct_handoff_contract.py`）、`studio/server.py`、`studio/api_contract.py`、`schemas/studio-openapi.json`；
- 新测试 `tests/test_r282_handoff.py`。

**照 spec 第 5 节 R282 三行做**：

1. **`GET /api/projects/{id}/direct/handoff`**：
   - 读这件作品已经落到本机的交接包，和 `_video_handoff_projection` 同一份、同样的身份校验。读法抽成公共函数，两边共用，不复制一份；
   - 返回 `{handoff: null | {jobId, revision, title, handedAt, shots:[{shotId, startSeconds, endSeconds, dialogue, visual, subtitle, camera, audio, image: null | {source, rightsStatus, sourceTimeSeconds, url}}], narration: null | {voice, durationSeconds}}}`；
   - `image.url` 只有交接里的图已经在本机时才给，路由 `…/direct/handoff/images/{shotId}?v=`；
   - 读不到或校验不过一律返回 `null`，不报错。
   - **`revision` 和 `handedAt` 取交接包里哪个字段**，照中台的格式定，写进汇报。界面要显示「第 N 版」和交接时间。
2. **`POST …/direct/jobs` 加可选 `handoff: {jobId, revision}`**：
   - 必须等于当前交接包，不等返回 409 `handoff_changed`；
   - 交接带了配音：把这条配音当作这次的配音，和上传配音同一套处理（转写、按配音实测每镜时长、比配音长的镜自动改短），成片带配音。
3. **「中台又交过来新版本」**：任务投影加一个字段（名字你定，写进汇报），在两种情况下为真：
   - 任务的 `handoff.revision` 小于当前交接包的 revision；
   - 任务不是从交接来的，但交接包的 `handedAt` 晚于任务的 `createdAt`。
4. **测试**（spec 第 6 节 R282 的后端部分）：
   - 身份校验和 `video_handoff_projection` 一致：换作品、换版本、scope 不对，都返回 `null`；
   - 图只在本机有时才给 url；
   - 带 handoff 建任务时用交接的配音，版本不对返回 409；
   - 新版本判断两种情况都要测；
   - OpenAPI 同步。
   - 先在现有代码上跑一遍，确认会失败，再实现。测试里不真调模型。
5. **找真实交接包**：看看这台电脑上有没有中台交过来的真实交接包，用 `_video_handoff_projection` 的找法只读查找。有的话用它做一次只读的接口实测（不生成）；没有就写进汇报：用户验收 H-01 时要先在中台点「交给我的电脑」。
6. **汇报**写到 `docs/tasks/R282-direct-handoff/REPORT-B.md`，写完停止。

## F 前端段（cdx 2）

**你改的文件**：
- `studio/static/direct-view.js`、`direct-storyboard.js`、`direct-style.js`、`direct-rescript.css`；
- 新测试 `tests/test_r282_frontend.mjs`、`tests/test_r282_frontend.py`，夹具 `tests/fixtures/r282-direct/`；
- 门禁 `scripts/direct_video/rescript_frontend_gate.mjs`。

**照 spec 第 1 节 R282 的规则做**：

1. **第一次进脚本直出、有交接包时**（`first-handoff`）：
   - 分镜脚本表按交接填好六列，画面图用交接的图，来源标签照中台：代码渲染 / 参考关键帧 / AI 示意 · 非实拍 / 原片截帧 m:ss，版权待确认的接「· 待确认」并用警示色；
   - 表头下 `DV-SB-SOURCE` 横条写「从中台交过来：「〈作品名〉」第 N 版 · 〈时间〉 · 带配音（〈音色〉 · m:ss）。」，再接「在这里改只存在本机，不会改中台的分镜。」；
   - 镜头列时间按交接的起止时间，台词改过就改按字数估；
   - 配音卡写「配音（从中台带过来）」，加音色和时长，按钮「换一个配音…」；
   - 建任务时带上 `handoff`。
2. **改分镜脚本一屏、中台又交过来新版本时**（`rescript-newer`）：
   - 横条写「中台又交过来新的分镜：第 N 版 · 〈时间〉。」，加按钮「换成中台这版」；
   - 点按钮后整张表换成中台这版，各列和图都换。
3. 字段名用 B 的实现，暂时没定的就按 spec 第 5 节的写法做夹具；B 的汇报出来后对齐，不一致的写进汇报。
4. **测试和门禁**：
   - spec 第 6 节前端部分里标 R282 的内容；
   - 合同检查把 `first-handoff`、`rescript-newer` 两个状态各块指到真实页面，`check_design_contract.py check` 全部通过；
   - 截图：这两个状态各拍 1440 和 960，放仓库外 `~/.photo-content-os/evidence/R282-direct-handoff/frontend/`，逐张看过。
5. 不写内联 `style=`；新颜色只用令牌。
6. **要跑**：
   - `node tests/test_r282_frontend.mjs`、`node tests/test_r278_direct_rescript.mjs`、`node tests/test_r283_frontend.mjs`；
   - 前端 pytest；
   - `rescript_frontend_gate.mjs --checks-only`，再截图；
   - `check_repository_safety.py --base HEAD`。
   - 环境变量照 R278 的 `REPORT-F1.md` 第 7 节。
7. **汇报**写到 `docs/tasks/R282-direct-handoff/REPORT-F.md`，写完停止。

## 补充 1（2026-10-27，总控）：交接时间和分镜版本号

用户定：改中台交接包，补两个字段。中台那边在协调，字段名先按下面写：

- `video.json` 顶层加两个**可选**键，不放进 `identity`：
  - `handedAt`：这次交接的时间，ISO UTC；
  - `storyboardRevision`：分镜一改就加一的整数。
- 老交接包没有这两个键，照常可用。

Studio 这边改成「有就用、没有就不显示」：

- **B（后端）**：
  - `handoff.revision` 取 `storyboardRevision`，没有就是 `null`；`identity.workRevision` 不再拿来当版本号。
  - `handoff.handedAt` 取 `handedAt`，格式不对就是 `null`。
  - 建任务时 `handoff.revision` 可以是 `null`，这时只比对 `jobId`。
  - `handoffNewer` 只在有依据时为真：两边都有 `storyboardRevision` 就比大小；否则任务有 `createdAt`、包里有 `handedAt` 就比时间；都没有就为假，不猜。
  - 补测试：带两个字段的包、不带的包、字段格式不对。
- **F（前端）**：
  - `revision` 为 `null` 时，横条不写「第 N 版 · 」；`handedAt` 为 `null` 时不写时间，相邻的「 · 」跟着去掉。
  - 新版本横条在没有版本号时写「中台又交过来新的分镜。」，后面接按钮。
  - 夹具补「两个字段都没有」的一份，补测试，截图加拍这种状态的 1440。
