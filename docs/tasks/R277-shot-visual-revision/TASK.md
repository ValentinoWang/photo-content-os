# R277 脚本直出里改一镜的画面 · 任务单

需求卡：`acceptance/requests/2026-W44/2026-10-26-R277-photo-shot-visual-revision/`（已确认，2026-10-26）。验收项 H-01–H-03 原样照卡，不许自行改。

设计稿（用户已认可）：`docs/tasks/R277-shot-visual-revision/design/`。`revise.html` 是可交互稿，`README.md` 写了交互、状态、设计编号、数字公式和后端要新加的东西，`contract.json` 是文案表和设计编号合同（`export_states.py` 导出）。

总控：Claude 会话 `c8166544-2733-4f32-b87f-ff9cd4c8a983`（回信地址 `uds:/tmp/cc-socks/7671.sock`）。

## 0. 和 R276 的关系（先读）

R277 叠在 R276（一键直出）上。R276 的总控是会话 photo-content-os-f8（`uds:/tmp/cc-socks/65898.sock`），任务单 `docs/tasks/R276-direct-video-opus/TASK.md`。和 f8 已定（2026-10-26）：

- **后端只做增量**：R276 投影里已定的字段一个不改名、不改含义，只加字段；新接口先给 f8 过目再实现。
- **起点**：R276 的本地提交 `90875ba`（后端 + R276 前端都在里面，还没推送）。R277 的 worktree 是 `/private/tmp/task-worktrees/photo-content-os-r277-shot-visual-revision`，从这个提交开。不碰 R276 的 worktree `/private/tmp/task-worktrees/photo-content-os-r276-direct-video`。R276 后端在 `scripts/direct_video/`、`studio/direct_video.py`，任务单和汇报在 `docs/tasks/R276-direct-video-opus/`（先读 TASK.md 和 REPORT-A/B/F2）。R276 已有：投影 `writingStartedAt`；`rewrite` 的 instruction 可以为空（中断或失败的镜不带意见重试）；构图提醒在 `checks.warnings`，`code=layout_bottom_gap`。
- **前端（用户 2026-10-26 选定 b）**：R276 前端先按 R276 的稿做完。「选中一镜后的详情」整块在 `studio/static/direct-shot-detail.js`，样式在 `studio/static/direct-shot-detail.css`，对外只有一个入口 `renderShotDetail(container, {job, shot, projectId, api, onRewrite})`；轮询时只有这一镜的 `status`、`posterRevision`、`checks`、`attempts` 变了才重画，重画时保留输入框内容和焦点。R277 前端只替换这两个文件、加自己的新文件，不碰 `direct-view.js`、`direct.css`。
- **预览是关键帧图片**：R276 的单镜预览是后端渲染的关键帧 JPEG（Studio 安全策略不允许在页面里跑生成的代码），没有拖帧和播放。R277 的设计稿里画面下的拖动条和播放按钮**不做**；画面上点选分块，是在关键帧图上按 `boxes` 叠一层热区。两版对比也是两张关键帧。

## 1. 分段

| 段 | 内容 | 什么时候开 |
| --- | --- | --- |
| A 后端 | 第 2 节 | R276 后端定在提交上、f8 看过第 2.3 节接口之后 |
| B 前端 | 第 3 节（开段前总控补全） | R276 前端合进去、详情文件边界落地之后 |
| C 收尾 | 真跑一遍 H-01–H-03 的路径，截图，交付检查 | B 通过之后 |

每段做完写汇报 `docs/tasks/R277-shot-visual-revision/REPORT-<段>.md`（写在 worktree 里），然后停下。

## 2. A 段：后端

### 2.1 每镜多个版本

- 每次重写生成新版本（第 1 版是第一次写好的），旧版本的代码、关键帧、检查结果都留着。
- 「当前用哪一版」单独存；退回只改它，不删版本。合成、配音重算都用当前版本。
- R276 的 `rewrite` 接口保留，等同于 `revise` 只有一条 `{text: instruction, own: true}`：加一版，当前版本指到新版。
- 切换当前版本后，R276 原有的单镜字段（`posterRevision`、`codeChars`、`checks`、`writtenAt`、`attempts`）都反映当前版本；成片和 `rewrite` 一样撤下就绪：`output` 回到 `none` 或标为过期，不能还显示旧成片就绪。

### 2.2 画面上的块

- 坐标系：1080×1920 画布像素，在和关键帧同一帧（0.8·D）量；元素在动，别的帧位置不同，所以只在这一帧量。
- 每镜渲染时，在 0.8·D 那一帧取镜头代码里带 `id` 或 `data-s` 的元素的位置和大小（1080×1920 坐标，`getBoundingClientRect`），存成 `boxes`。看不见的（透明度 0、宽或高为 0、`display:none`）不收。
- 每块的中文名称：优先元素里的文字（截前 12 个字，加「」），图形元素（svg 里的 rect 等）用旁边文字拼，例如「「约 25%」柱子」；取不到就用「第 N 块」。名称规则写进测试。

### 2.3 接口（先给 f8 过目）

投影里每镜新增（R276 的字段原样保留）：

```json
"currentVersion": 2,
"versions": [{"version": 1, "createdAt": "…", "posterRevision": 1, "codeChars": 4320,
              "request": null,
              "verify": null}],
"boxes": [{"id": "b3", "name": "「约 25%」柱子", "x": 580, "y": 886, "w": 300, "h": 316}],
"look": {"status": "none | running | done | failed", "failureCode": null,
         "findings": [{"boxId": "b3", "kind": "主次", "text": "中文一句", "suggest": "main | dim | del | short"}]},
"sample": false
```

`versions[].request`（这一版是按什么改的）：`{"lines": [{"text": "…", "boxId": "b3", "action": "dim"}, {"text": "…", "issue": "color"}, {"text": "底色不动", "own": true}]}`。
`versions[].verify`（重写后逐条核对）：`{"status": "running | done | failed", "items": [{"index": 0, "result": "done | missed", "reason": "没做到时一句中文"}]}`。

新接口（写请求照旧要 loopback、同源、CSRF；投影不出现本机绝对路径）：

| 方法 | 路径 | 做什么 |
| --- | --- | --- |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/revise` | body `{lines: [...]}`（格式同上），各条文字合计 1–200 字；只重写这一镜，加一版，然后自动核对 |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/current` | body `{version}`，切换当前版本（退回） |
| POST | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/look` | 重新看图自查 |
| PUT / DELETE | `/api/projects/{id}/direct/jobs/{jobId}/shots/{shotId}/sample` | 存为样例 / 取消 |
| GET | `/api/direct/revision-log` | 画面问题记录：每类问题的次数、出处（作品名、镜号）、规则草稿 |
| POST | `/api/direct/rules/proposals/{proposalId}/adopt`、`/reject` | 采用 / 不用规则草稿 |
| GET | `/api/direct/samples` | 样例列表（作品名、镜号、存的时间、关键帧地址） |

`failureCode` 新增：`look_failed`、`verify_failed`、`version_not_found`、`instruction_too_long`。

### 2.4 看图自查和核对

- 渲染好后自动跑一次看图自查：取 0.3、0.6、0.9·D 三帧，连同 `boxes`、这一镜口播、全片设计，交给 Opus，返回 `findings`（每条最多落在一块上，`suggest` 只能是四个改法之一；整镜的问题 `boxId` 为 null）。最多 5 条。
- 重写后自动核对：新画面三帧 + 发出去的每条要求，逐条返回 `done | missed`。
- 模型调用一律走 `llm_common.generate_text`（R276 加的 `claude_cli`），不许另起模型进程（Core 规则 `ai-egress-ownership-guard-card.md`）。`generate_text_with_claude_cli` 现在收到 `image_paths` 就报「claude CLI image input is unsupported」；改成：有图时用 `--input-format stream-json --output-format stream-json --verbose`，图片用 `validated_image_paths` 校验后转 base64 图片块；其余参数（`--safe-mode`、`--setting-sources ''`、`--tools ''`、`--strict-mcp-config`、空 `--mcp-config`、`--no-session-persistence`、空临时目录、环境变量处理）原样保留。没图时的写法一个字不改，R276 的测试原样要过。
- **A 段第一件事：实测 Opus 能不能看图。** R276 的 `claude_cli` 是 `--tools ''` 加 `--safe-mode`，只能传文字。先实测 `claude -p` 在不打开其他工具的前提下读到图片的办法（例如 `--input-format stream-json` 带 base64 图片块；或只放开读一个临时目录），从和 Studio 一样的后台子进程里跑通一次，把命令写法、耗时、成败写进汇报。调不通就停下汇报，不要改成只给代码不给图，也不要放开其他工具。
  - 总控已预先实测通过（2026-10-26）：在空临时目录里运行 `claude -p --input-format stream-json --output-format stream-json --verbose --tools '' --safe-mode --strict-mcp-config --model claude-opus-5-5`，标准输入写一行 `{"type":"user","message":{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":"…"}},{"type":"text","text":"…"}]}}`，取最后一行 `type=result` 的 `result`。329×580 的 JPEG，7.1 秒返回，`permission_denials` 为空、没开工具。Codex 照这个写法接进 `generate_text`（加图片参数），再从 Studio 同样的后台子进程里复测一次。
- 看图失败只把 `look.status` 标 `failed`，不影响 R276 的代码检查和渲染。

### 2.5 样例、问题记录、画面规则

- 样例存在 Studio 状态目录 `direct-samples/`（镜头代码、关键帧、作品、镜号、时间），跨作品共用。写新镜时取和这一镜最像的 2 个附进提示（相似度：口播和主动作的字二元组重合度），没有样例就不附。
- 问题记录：每次 `revise` 发出去时按条记一次。改法到问题类的对应：`main`、`dim` → 主次不清；`del`、`short` → 字太多；整镜 `space` → 太空或挤在上面，`color` → 颜色乱，`sync` → 跟口播对不上；自己补的一句不计类。取消、没发出去的不算。
- 同一类到 3 次，让 Opus 起草一条规则（输入：这几次的要求原文），存为待定草稿。「采用」后画面规则升一版：仓库里的 `scripts/direct_video/rules/shots.md` 是代码，只能经提交改，不动它；采用的条文写进 Studio 状态目录里的用户规则层 `direct-rules/`，生成器读规则时把两层合起来；已经写好的镜不变。「不用」只把草稿标掉，次数继续记。
- 样例的代码和关键帧**复制**进样例库自己的目录，不引用任务目录（任务可能被删）。

### 2.5a 互斥

- 同一镜上的 `revise`、`rewrite`、`current`、`look` 互斥；成片正在合成时都不能改。照 R276 现有的受控错误返回（`failureCode` + HTTP 状态），不新造写法。

### 2.6 测试

- 新增 `tests/test_r277_*.py`，假 claude 可执行文件，不真调模型：多版本和退回（退回不删版本、合成用当前版本、切换后 R276 单镜字段跟着变、成片撤下就绪）；同一镜操作互斥、合成中拒绝；样例复制后删掉任务样例仍在；规则两层合并；`boxes` 取法和名称规则（用 R276 设计稿里第 02 镜的代码当样例）；`revise` 字数 1–200、`lines` 校验；看图失败不影响代码检查；核对结果落在对应版本；问题记录计数规则（取消不算、自己补的不计类）；到 3 次出草稿、采用前规则不变；样例附进提示最多 2 个；投影无绝对路径；R276 已有字段不变（拿 R276 的投影测试原样跑）。
- 跑：R276 和 R277 的全部测试；和 `api_contract`、`server` 相关的现有测试；`bash scripts/check_runtime_contract.sh`；`.venv/bin/python scripts/check_repository_safety.py --base origin/main`。全量 pytest 跑一次，失败逐条判断是不是本任务造成的。

## 3. B 段：前端（Codex 账号 2）

### 3.1 先读

- 设计稿（权威）：本目录 `design/revise.html`（`#s=<状态>` 切九个状态）、`design/README.md`（交互、状态、设计编号、数字公式）、`design/revise-extra.js` / `revise-extra.css`（新块的结构和样式，样式照抄进 `direct-shot-detail.css`，颜色只用 `studio/static/styles.css` 的令牌）、`design/contract.json`（文案表和设计编号合同）、`design/approved-extras.json`（总控批准的稿外文案和编号，见 3.5）。
- R276 前端任务单 `docs/tasks/R276-direct-video-opus/FRONTEND-TASK.md` 第 2、3、5 节（详情模块的入口约定、轮询重画规则、不写内联 `style=`、失败代码翻译、门禁写法），和现有 `studio/static/direct-shot-detail.js`、`direct-view.js`、`scripts/direct_video/frontend_gate.mjs`、`tests/test_r276_direct_frontend.mjs`。
- 后端实际字段和接口：`REPORT-A.md` 第 3 节、`evidence/2026-10-26/R277-shot-visual-revision/api-examples.json`。字段以代码为准。
- Core `frontend-screenshot-completion-guard-card.md`、`first-screen-visual-hierarchy-guard-card.md`、`ui-copy-quality-guard-card.md`。

### 3.2 只许改这些文件

- 整块替换：`studio/static/direct-shot-detail.js`、`studio/static/direct-shot-detail.css`。入口不变：`export function renderShotDetail(container, {job, shot, projectId, api, onRewrite})`；外层每次轮询都调，模块自己判断重画（见 3.3）。
- 新建：`studio/static/direct-revision-log.js`（「画面问题记录」页，导出 `renderRevisionLog(container, {api, onBack})`），样式写进 `direct-shot-detail.css`（不新开样式表，免得改 `index.html`）。
- `studio/static/direct-view.js`：**只许加两处**（f8 已同意）：①「上传配音…」左边加按钮「画面问题记录」（照稿，`build_revise.py` 第 37 行）；② 点了以后把直出页主体交给 `renderRevisionLog`，「回到作品」回到原来的直出页（`onBack`）。别的一行不动。
- 测试和门禁：新建 `tests/test_r277_frontend.mjs`、`tests/test_r277_frontend.py`、`scripts/direct_video/revision_frontend_gate.mjs`、夹具 `tests/fixtures/r277-revise/`。R276 的 `tests/test_r276_direct_frontend.mjs` / `.py`、`scripts/direct_video/frontend_gate.mjs` 只许做 3.6 写的那几处改动。
- 不许碰：后端（`scripts/`、`studio/*.py`、`schemas/`）、`review-view.js`、`index.html`、`direct.css`、设计稿目录。接口不够用写进汇报「需要的接口」，不要自己改后端（同时有一个后端线程在这个 worktree 里补 `baseVersion`，见 3.4）。

### 3.3 详情怎么画（和稿的差别）

- **画面是关键帧图片，不是 iframe。** 大画面 360×640：`<img src="…/shots/{id}/poster.jpg?v={posterRevision}">`；下面保留 R276 的一行「关键帧 · 这一镜 x.x 秒处的 80%」（`DV-PVNOTE`）。稿里的拖动条和播放钮（`DV-SCRUB`）**不做**。
- 热区按 `shot.boxes` 画：1080×1920 坐标乘 360/1080（对比图 300 宽乘 300/1080），用 `el.style.setProperty` 或 CSS 变量定位，不写 `style=`。热区按钮的可读名（`aria-label`）用 `box.name`；选中后右边标题也是 `box.name`。
- 橙色「!」：`look.findings` 里 `boxId` 落在某块上的，标在那块右上角；右边选中那块时显示「Opus 看出 · {kind}」+ `text`，`suggest` 对应的改法按钮带「建议」。`boxId` 为 null 的整镜问题：显示在「规则检查」之外的那条 `rv-note`（照稿 review 状态「画面上的「50%」…」那行的位置和样式），`kind` 映射不到改法，不加「建议」。
- `look.status`：`running` → 右边空状态写「Opus 正在看这一镜的画面」，画面上不出橙点；`failed` → 稿 `review-failed`（「重试」→ `POST …/look`）；`done` 且 0 条 → 「Opus 看了这一镜，没看出要改的地方。」。`boxes` 为空（R276 旧任务的镜）→ 「这一镜还没有可以点的块。」+「让 Opus 看一遍」（`POST …/look`，后端会补三帧和块），整镜三个按钮和「补一句」照样能用。
- 「要改的」：每条 = 稿里 `actText` 模板生成的文字，块上的条目带 `boxId`+`action`，整镜带 `issue`，补的一句带 `own:true`；发 `POST …/revise {lines}`。字数按 README 公式，超 200 字按钮灰、字数变红。没有任何条目、这一镜 `failed`/`interrupted` 时，按钮变「重试这一镜」，发 R276 的 `POST …/rewrite {instruction:""}`。
- 重写中（`status` 是 `writing`/`rendering`）：画面盖 `RV-BUSY`。刚在本页发出的 revise 知道条数，写「正在按 N 处改法重写 · m:ss」；不知道条数（刷新过页面、或 rewrite）写「正在重写这一镜 · m:ss」。m:ss = 现在 − `writingStartedAt`；没有这个字段就不显示秒数。右边全部不可点。
- 两版对比（`RV-COMPARE`）：出现条件 = 当前版本是最新一版、这一版 `request` 不为空、有 `baseVersion`（3.4），并且用户还没在这页点过「用第 N 版」。左图 `poster.jpg?version={baseVersion}`，右图当前版；标题「第 {baseVersion} 版」「第 {N} 版 · 按你的 {request.lines 条数} 处改法」。右边「这次改的」逐条列 `request.lines`，后面按 `verify` 标：`running` →「正在核对」，`done` →「做到了」/「没做到」+ `reason`，`failed` →「Opus 这次没核对成，两版照样可以比。」。绿色编号只标在有 `boxId` 的条目上，位置用当前版 `boxes` 里同 id 的块，找不到就不标。
- 「退回第 {baseVersion} 版」→ `POST …/current {version: baseVersion}`；「用第 N 版」只在本页记下（`localStorage` 包 try/catch，读不到就当没点过），不发请求。退回后显示稿 `kept-prev` 那句：条件 = 当前版本 < 最新一版，且最新一版的 `baseVersion` 等于当前版本。
- 「♡ 这镜好」→ `PUT …/sample`；`sample:true` 时是「♥ 已存为样例」，再点 `DELETE`。
- 口播、规则检查、代码：照稿收在最下面三个折叠。规则检查沿用 R276 的五条硬规则 + `checks.errors`/`warnings`；有要看的项时标「N 项要看」（N = errors + warnings 条数）。看代码展开时才 `GET …/code`，对比状态下读当前版。
- **轮询重画**：这一镜的 `status`、`posterRevision`、`checks`、`attempts`、`currentVersion`、`versions`（只比 version、posterRevision、verify.status）、`boxes`、`look.status`、`look.findings`、`sample` 有变化才重画。重画时保留：选中的块、已选的改法和整镜按钮、补的一句（值、焦点、光标）、折叠的开合。换一镜时各镜的这些分开记。
- 失败代码翻成中文：沿用 R276 的翻译表，新加 `instruction_too_long`、`version_not_found`、`sample_not_found`、`proposal_not_found`、`proposal_not_ready`、`look_failed`、`verify_failed`，文字用 `approved-extras.json` 里批准的。页面上不许出现英文代码、绝对路径、`undefined`、`NaN`。

### 3.4 后端补一个字段（另一个线程在做）

`versions[].baseVersion`：这一版是在哪一版的基础上改的（发 revise/rewrite 时的 `currentVersion`；第 1 版为 null；配音变了重渲出来的版本是重渲前的当前版）。前端照这个字段写，夹具里带上。后端线程会写进 `REPORT-A2.md`。

### 3.5 画面问题记录页（`RV-LOG`、`RV-PROPOSAL`、`RV-SAMPLES`）

- 数据：`GET /api/direct/revision-log`、`GET /api/direct/samples`。表格只列 `count > 0` 的类别，按 `count` 从多到少。
- 「出在哪几镜」：按作品分行，每行「{作品名} · {镜号、镜号}」，镜号去重、从小到大。作品名用 `projectTitle`。
- 「现在」列：有 `pending` 草稿 →「建议写进规则」+ 草稿块；`running` →「正在起草规则」；最新一份是 `failed` →「这次没起草成，再攒 3 次会重新起草。」；否则 X = 3 −（count − 这一类已有草稿里最大的 `throughCount`，没有就 0）：X = 1 →「再有 1 次会起草规则」，X = 2 →「记着」。最新一份是 `adopted` 且之后没有新次数 →「已写进规则」。
- 草稿块：「起草的规则修改 · 画面规则第 {rulesRevision} 版 → 第 {rulesRevision+1} 版」；条文 = `text`；依据一行 =「依据：这 {throughCount} 次你都点了「{category}」类改法。」（整行按数据标 `data-design-data`，不编稿里那半句）；「采用」「不用」→ `POST /api/direct/rules/proposals/{id}/adopt|reject`，成功后重读记录；采用后那句里的版本号同样用公式。
- 样例：「存下的样例 · N 镜」，每个 140 宽关键帧（`posterUrl`）+「{作品名第一个逗号前的部分，最多 8 字} · 第 {shotId} 镜」「{M月D日}存」。
- 空：没有记录 →「还没有改过画面。改过的问题会记在这里。」；没有样例 →「还没有存样例。在一镜上点「♡ 这镜好」就会存到这里。」。

### 3.6 R276 测试和门禁的改动（f8 已同意，只许这几处）

- `tests/test_r276_direct_frontend.mjs` 里查 R276 详情 DOM 的断言（`#dv-ask`、`data-rewrite` 等）：意图不变（重画保留输入值、焦点、光标；发重写请求；不带意见重试），改成查 R277 的元素。每处改了什么写进汇报。
- `scripts/direct_video/frontend_gate.mjs`：R276 的合同比对跳过 `DV-DETAIL` 整块（清点时排除这个块的子树），其余照旧必须通过。详情由 R277 的门禁管。
- 不许删 R276 的状态、不许放宽别的断言。

### 3.7 门禁和截图

- `tests/test_r277_frontend.mjs`：README 和本节的数字公式（字数、编号、第几版、「现在」列、坐标换算）；轮询重画保留选中/改法/输入/焦点；对比和退回的出现条件；失败代码翻译含未登记代码。
- `tests/test_r277_frontend.py`：新文件没有 `style=`；`direct-view.js` 相对 `90875ba` 只多了 3.2 那两处（用 `git diff 90875ba -- studio/static/direct-view.js` 的行数和内容判断）。
- `scripts/direct_video/revision_frontend_gate.mjs`：仿 R276 的 `frontend_gate.mjs`。用 Playwright 拦截接口返回夹具，打开真实 Studio（端口 **8768**，临时状态目录，用完关掉），逐状态截图 1440 和 960 两个宽度，放 `~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/`。每张图用 `collect_design_inventory.js` 清点，跑 `check_design_contract.py check --contract design/contract.json --approved-extras design/approved-extras.json`。
  - 九个设计状态各一份夹具（`review`、`select`、`picked`、`rewriting2`、`compare`、`kept-prev`、`saved`、`review-failed`、`log`），夹具数据照稿。`select`/`picked` 要在页面上真点出来（点热区、点改法、输入补的一句），不是夹具直接画好。
  - 另加这些状态，按括号里的设计状态比对合同：`look-running`（review）、`no-boxes`（review-failed）、`verify-running`、`verify-missed`、`verify-failed`（compare）、`log-empty`（log）、`proposal-running`（log）。
  - **真实数据最差首屏**：用真实状态目录 `~/.photo-content-os/studio-r276/` 里的七镜任务 `dv_0e184e961bd14ac084c67411`（R276 REPORT-F2 第 32、41 行；拷一份到临时目录再用，不改原件，用完核对原件哈希没变），它是 R277 之前写的，各镜没有 `boxes`、`look` 为 `none`。截选中第 02 镜的首屏，1440 和 960。这一张要看出：画面清楚是主角，「让 Opus 看一遍」看得见，右边不空、不乱。
- 每张截图你自己先逐张看，再交给总控。总控也会逐张看。
- 稿外文字或元素：`approved-extras.json` 里没有的，写进汇报「需要新文案」「稿外元素」后停下，不要自己加，也不要改 `approved-extras.json`。

## 4. 约束

- 只在自己的 worktree 里改，worktree 用 Core `task-worktree-harness.md` 的脚本建；不改主目录（主目录里有别的会话没提交的改动）。
- 不提交、不推送、不回退别人的改动、不杀别人的进程。端口 8765 和 8766 上的 Studio 都是用户正在用的（8766 跑在 R276 的 worktree 上），不许动；自己要起 Studio 用别的端口，用完关掉。
- 遇到要拍板的事：先做不受影响的部分，把问题写进汇报后停下。
- 证据放 worktree 里的 `evidence/2026-10-26/R277-shot-visual-revision/`；帧、截图放仓库外 `~/.photo-content-os/evidence/R277-shot-visual-revision/`。

## 交接

### 交接 1（2026-10-26，总控）

- 设计稿第 2 版用户已认可（「可以 请实现」），需求卡已按第 2 版改写验收步骤并确认。
- 已和 f8 对齐：后端只做增量；f8 看过 2.3 节接口，同意，并提了六点（rewrite 等同单条 revise、切版本后单镜字段和成片状态、boxes 坐标系、看图可行性先实测、规则两层和样例复制、同镜操作互斥），已写进第 0、2 节。起点等 R276 后端提交号。
- 用户选 (b)：R276 前端先做（f8 已派 cdx 2），详情模块边界见第 0 节。设计稿里的拖动条和播放按钮不做（预览是关键帧图片）。
- 还没开 worktree，还没派 Codex。

### 交接 2（2026-10-26，总控）

- 用户授权：「后面不用等我同意 你们相互协调改完就行」。R276/R277 的提交、推送 origin/main、派 Codex 都不再等用户点头；和 f8 有分歧先商量。已转告 f8。
- 提交仍由总控做（Codex 照旧不提交、不推送）：总控在 R277 的 worktree 里看过改动、跑过测试后提交，推到 origin/main，然后 `task_worktree.py finish`。
- 起点：（交接 3 改为从 R276 本地提交开，见下。）
- 看图可行性已预先实测通过（见 2.4 节）。

### 交接 3（2026-10-26，总控）

- f8 给了 R276 的本地提交 `90875ba`（未推送），总控用 `task_worktree.py create r277-shot-visual-revision --base 90875ba --allow-leftover` 开了 worktree `/private/tmp/task-worktrees/photo-content-os-r277-shot-visual-revision`。`--allow-leftover` 是因为 R276 的 worktree 还没合并，这是和 f8 商量好的叠放，不是遗留；R276 推送后由 f8 `finish`。
- 推送顺序：R277 的提交以 `90875ba` 为父，所以 R276 推到 origin/main 之后 R277 才能推。f8 推前会跟用户确认，推完通知总控。
- 本任务单、设计稿、需求卡是从主目录复制进 worktree 的，**以 worktree 里这份为准**，跟 R277 的代码一起提交。
- 渲染环境（来自 R276 REPORT-F2）：`VIDEO_RENDER_PLAYWRIGHT_MODULE=~/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js`，`VIDEO_RENDER_BROWSER=~/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`；本机 ffmpeg 没有 drawtext。`.venv` 已软链到主目录。
- R276 前端已在 `90875ba` 里：`studio/static/direct-shot-detail.js` 入口是 `export function renderShotDetail(container, {job, shot, projectId, api, onRewrite})`，外层每次轮询都调用，模块自己判断要不要重画。B 段按这个补第 3 节。
- 下一步：派 A 段给 Codex（cdx 1）。

### 交接 4（2026-10-26，总控）

- A 段验收：读过 REPORT-A，看了 `llm_common`、`server.py` 的改动，自己重跑 R276+R277+OpenAPI 同步测试 179 项通过。Codex 线程 `01a1747f-96e0-7e40-a03a-5a9e6e5dbf4c`（cdx 1）。
- REPORT-A 第 6 节第 1 条的拍板：`tests/test_r276_direct_video.py` 字段集合由总控改成「16 个旧字段 + 5 个新字段」，仍然严格相等（f8 同意）。交付卡 G16 要写这处重叠。
- f8 同意（2026-10-26）：`direct-view.js` 加两处；R276 详情 DOM 测试按意图改到 R277 元素上；R276 门禁跳过 `DV-DETAIL`。f8 要求交付卡 G16 写清：R276 卡 H-03（只重写一镜、其他镜不变）由 `tests/test_r276_direct_video.py` 里的单镜重写不变性测试和 R276 REPORT-B 的真跑证据证明，不依赖详情 DOM 测试。
- 第 3 节已补全，`design/approved-extras.json` 已批准。
- 并行两个线程：A2（cdx 1 续跑，补 `versions[].baseVersion`，汇报 REPORT-A2.md）、B（cdx 2，汇报 REPORT-B.md）。文件不重叠：A2 只改后端和 `tests/test_r277_revisions.py`/`test_r277_api.py`，B 只改第 3.2 节列的文件。


### 交接 5（2026-10-26，总控）· B 段第 1 轮看图结论

A2 验收（`baseVersion`，REPORT-A2）。B 段第 1 轮：读了 REPORT-B，逐张看了真实最差首屏 1440/960、review、picked、compare 1440/960、log。整体照稿，热区、编号、建议角标、核对结果、记录页都对。合同缺口两处是总控的批准文件漏了，已补：`approved-extras.json` 的 `log` 把 `RV-PROPOSAL` 设为可选；R276 的 `tests/fixtures/r276-direct/approved-extras.json` 十三个状态都批准「画面问题记录」（f8 已同意这个入口）。

B 段第 2 轮要改的（每条能对照截图检查）：

- B2-1 **没有块时标题自相矛盾**（`no-boxes`、真实最差首屏）：现在标题写「在左边画面上点要改的地方」，下面又说「这一镜还没有可以点的块」。改成：`boxes` 为空时 `RV-INSPECT` 的标题就是「这一镜还没有可以点的块」（已批准），下面一个小按钮「让 Opus 看一遍」（`btn btn--sm`，不是行内链接）；不出现「在左边画面上点要改的地方」。检查：960 宽时按钮不和别的字挤在一行，前面没有空格缩进。
- B2-2 **记录页说明文字太窄**（`log` 1440）：「你在各作品里改过的…才生效。」现在只有约 330px 宽、折成两行，第二行从「到 3 次」开始。改成：说明文字宽度 ≥ 600px（1440 和 960），1440 时一行放下；「回到作品」按钮和标题同一行靠右。门禁量说明元素宽度。
- B2-3 **960 对比状态标题在图片下面**（`compare-960` 以及 `verify-*` 的 960）：上下排列时，「第 02 镜 · 第 2 版 · 共 2 版」和「♡ 这镜好」那一行要在两张图**上面**；顺序 = 标题行 → 两张图 → 退回/用第 N 版 → 这次改的 → 三个折叠。1440 不变。
- B2-4 重跑两份门禁（R277 的 `revision_frontend_gate.mjs` 和 R276 的 `frontend_gate.mjs`），合同检查全部通过；改到的状态重新截图（1440、960，`no-boxes` 和真实最差首屏再加 390），自己逐张看。

后端（cdx 1，A3）：
- A3-1 **读取不许改 `updatedAt`**：R276 旧任务第一次读取时的版本迁移（REPORT-A「版本与恢复」）把 `job.updatedAt` 改成了读取时间，R276 页头「从点生成到出片用了 m:ss」就变成 135:17。迁移只补版本元数据，不改 `updatedAt`；`look`、`sample`/取消样例也不改 `updatedAt`（它们不改成片）。revise、rewrite、current 照旧改。加测试：迁移前后 `updatedAt` 相同；look、sample 之后 `updatedAt` 不变。
- 新起点：f8 修了「出片用时」，提交 `d095d10`，父提交是 `90875ba`，还没推送。改动包括：`output.composedAt`；`direct-view.js` 第 148、149 行；R276 夹具补了 `composedAt`；新增 `tests/test_r276_direct_d.py` 和夹具 `done-no-composed-time.json`。总控等 A3、B2 跑完后提交 R277，再 rebase 到 `d095d10`。`studio-openapi.json` 用 build_openapi 重新生成，其余冲突手工合，合完跑两边测试和两份门禁。

### 交接 6（2026-10-26，总控）· B 段通过，rebase 完成，开 C 段

- B 段第 2 轮看图通过（无块标题、记录页说明一行、960 对比标题在图上）。A3 验收（读取、看图、样例不改 `updatedAt`）。
- 总控已提交 R277 并 rebase 到 f8 的 `d095d10`：当前 HEAD `ae80df4`（父 `d095d10`）。冲突只在 `generate.py` 两处（合成失败时同时清 `composedAt` + R277 的 `touch_updated_at`），`studio-openapi.json` 用 `scripts/export_studio_openapi.py` 重新生成。rebase 后：R276+R277+相关前端 pytest 204 项通过；R277 门禁 38/38、R276 门禁 26/26 通过（证据 `~/.photo-content-os/evidence/R277-shot-visual-revision/rebase/`）。
- `tests/test_r277_frontend.py` 原来那条「`direct-view.js` 相对 `90875ba` 只多两行」的测试，拿固定提交比，R276 一改就失败，以后谁正常改都会挂。总控改成只查两个接点在不在。两行边界由总控在 rebase 后按 `git diff d095d10 HEAD -- studio/static/direct-view.js` 人工核对过：恰好两行。

## 5. C 段：真跑 H-01–H-03（Codex 账号 2）

在真实 Studio 上用真 Opus 照需求卡 H-01–H-03 原样点一遍，截图，证明三条预期都成立。**不改代码**；发现问题写进汇报后停下。

- **环境**：把 `~/.photo-content-os/studio-r276/` 整个拷到临时目录当状态目录（原件不改，用完核对哈希），从本 worktree 起 Studio，端口 8768。模型走真本机 Claude（provider 和环境变量照 R276 `REPORT-B.md`、`REPORT-F2.md` 真跑时的写法，加交接 3 的渲染变量）。8765、8766 不许动。
- **作品**：「断更一年，我拆了四句话」的脚本直出，七镜任务（R276 REPORT-F2 里的 `dv_0e184e961bd14ac084c67411`，或这个作品最新的直出任务，写清用的是哪个）。它是 R277 之前的任务，第 02 镜一开始没有块：先点「让 Opus 看一遍」，等看图完成、画面上出现块和橙色「!」，再照 H-01 往下点。这一步写进汇报（卡上没写，是旧任务必经的一步）。
- **H-01**：照卡点。Opus 实际看出的问题落在哪些块上、说了什么，原样记下；如果「约 25%」「约 50%」两根柱子没有被 Opus 标「!」，照样点它们选改法（卡上的步骤就是这样），如实记录。重写完看两版对比和逐条核对，记下每条 `done`/`missed` 和原因。**其他六镜不变**：重写前后各镜的 `posterRevision`、`writtenAt`、关键帧文件 SHA-256 对比表。
- **H-02**：照卡点。截图标题下那一行，原样抄出文字（卡上写的是「用第 1 版 · 共 2 版」，实际文字不一样就如实写，不改代码）。第 01 镜「已存为样例」截图；样例库目录里有复制出的代码和关键帧。
- **H-03**：H-01 只给「主次不清」记 2 次。为了看到「到 3 次」的那一行，**再对第 05 镜做一次**：让 Opus 看一遍，点一块选「做主角」或「缩小变灰」，重写。这一步是为凑够 3 次而加的，汇报里写明。然后打开「画面问题记录」，等草稿起草完，截「主次不清」那一行和草稿块；**不点「采用」**；用 `GET /api/direct/revision-log` 的 `rulesRevision` 证明规则没变。
- **截图**：每一步 1440 宽，放 `~/.photo-content-os/evidence/R277-shot-visual-revision/real-c/`；同时存每一步的任务投影 JSON 和接口时间线（发了什么请求、多久返回、看图/重写/核对各用了几秒）。
- **汇报**：`docs/tasks/R277-shot-visual-revision/REPORT-C.md`。H-01–H-03 每条：做了哪几步、截图链接、预期逐句对照「成立 / 不成立 + 原因」。不代签人工验收，只给机器证据。然后停止。不提交、不推送。

### 交接 7（2026-10-26，总控）· C 段第 1 轮结论

- H-01、H-02 真跑成立（REPORT-C）。卡上 H-01 的「约 25% / 约 50% 柱子」是设计稿的示意数据；真实第 02 镜是点阵图，对应「25%」「估计 50%」两个文字块，旧任务也要先点「让 Opus 看一遍」。总控试过改卡，但改卡会把用户已确认的卡退回「待确认」，已撤回。这处差异写进交付说明，由用户决定要不要改卡措辞。
- C-01 是真问题，修：

C2-1 **`boxes` 为空且 `look.status` 是 `running` 时**，`RV-INSPECT` 显示「Opus 正在看这一镜的画面」（已批准文案），不显示「这一镜还没有可以点的块」和「让 Opus 看一遍」按钮。判断顺序：先看 `look.status==='running'`，再看有没有块。加一份夹具 `no-boxes-look-running`（按设计状态 `review` 比对合同），截 1440/960，写进 `tests/test_r277_frontend.mjs` 的断言。R277、R276 两份门禁重跑通过。

C2-2 **补跑 H-03**（真 Opus）：重新拷一份 `~/.photo-content-os/studio-r276/` 到临时目录，起 8768。第 05 镜点「让 Opus 看一遍」，截看图进行中那一屏（验证 C2-1），看完后在画面上点三块，每块选「做主角」或「缩小变灰」（凑够「主次不清」3 次，写明是为验证阈值而加），点「重写这一镜」，等重写和核对结束。然后照卡 H-03 打开「画面问题记录」，等草稿起草完，截「主次不清」那一行和草稿块，**不点「采用」**，用 `GET /api/direct/revision-log` 的 `rulesRevision` 证明规则没变。注意：这份新拷贝里没有 H-01 的那 2 次，次数从 0 开始，所以这一行应该正好 3 次、只出自第 05 镜。

汇报追加到 REPORT-C.md「## 第 2 轮」。代码只许改 `direct-shot-detail.js`，加上测试、夹具、门禁；其余同前。

### 交接 8（2026-10-26，总控）· C 段第 2 轮结论

- C-01 修复通过；H-03 真跑成立（主次不清 3 次只出自第 05 镜，草稿 pending，`rulesRevision` 一直是 0）。第 05 镜重写后的核对有一条「没做到」，是 Opus 的真实判断，如实保留。
- 总控看真实截图（`real-c2/real/r03`、`r05`）发现：画面上的编号和橙色「!」压住了块里的字。第 2 版上「66」被 1 号盖成「6 天」，「快 18 天」的「快」、「只要不连着断两次」的「只」也被盖住；橙点盖住「接近自动」。要对比的正好是这几处，不能盖。

C3-1 **编号和「!」不压住块**：编号（`rv-num`）、橙点（`rv-pin`）都放在块外侧，徽标矩形和它所属块的矩形不相交。候选位置按顺序试，取第一个整个落在画面（大画面 360×640、对比图 300 宽）里面的：编号是 ①块左边外侧、上沿对齐 → ②块上方、左对齐 → ③块下方、左对齐 → ④块右边外侧；橙点是 ①块右边外侧、上沿对齐 → ②块上方、右对齐 → ③块下方、右对齐 → ④块左边外侧。外侧间距 2px。四个位置都放不下时，退回现在的角上位置。同一块既有编号又有橙点时，两者也不相交。只改 `direct-shot-detail.js` / `.css`。
- 门禁：在 `review`、`picked`、`compare`、`kept-prev` 夹具和真实最差首屏（有块之后）上，逐个量徽标和它所属块的矩形，断言不相交、徽标在画面里面。截 1440/960，自己看；两份门禁重跑通过。
- 不需要再真跑模型。改完写 REPORT-C.md「## 第 3 轮」，然后停止。

### 交接 9（2026-10-26，总控）· C3 看图结论

C3-1 做到了（编号不再压自己那一块），但 C3-V01、C3-V02 确实存在：总控看 `real-boxes-compare-05-detail-1440.png`，1 号压住「Lally」，3 号压住「断一次」的「断」。回答 Codex 的问题：**可以跳过会压到别的块的候选位置**。C4 改：

- C4-1 候选位置除了要整个落在画面里，还要不和**任何**块（包括别的块）相交、不和已经放下的徽标相交。顺序不变。四个都不行时，在四个候选里选和其他块相交面积最小的那个，但仍不许压自己那块（只有角上回退可以，和现在一样）。
- C4-2 徽标尺寸跟画面缩放走：大画面（360 宽）20px，对比图和手机上画面宽度 ≤ 300px 时 16px，字号同比。
- C4-3 C3-V02 是夹具数据的问题：夹具里的 `boxes` 坐标是手写的，和夹具关键帧上的字对不上。改夹具：用后端同样的取法（`render-frames.mjs` 在 0.8·D 那一帧量带 `id`/`data-s` 的元素）从设计稿镜头代码量出真实 `boxes`，替换手写坐标。坐标以外的字段（名称、findings 的 boxId）照对应关系改，并写清改了哪些。
- 门禁：在 C3 的断言之外，加「徽标不和任何其他块相交」，对夹具和真实重放都断言。确实四个都放不下、只能选相交最小的那几枚要单列出来（块 id、相交面积），总控会看图逐个判断。截 1440/960/390，自己逐张看。两份门禁重跑通过。
- 汇报追加 REPORT-C.md「## 第 4 轮」，然后停止。这是同一个问题的第 2 轮修改；第 3 轮还不过，总控就去问用户。

### 交接 10（2026-10-26，总控）· C 段通过，交付准备

- C4 看图通过：1440、960 下真实对比图的编号和「!」都不压字。390 下对比图只有约 132px 宽，1 号擦到「天」字一角（约 29px²），总控判可以接受。其余列出来的最小相交，压到的都是图表、卡片这类容器块，不是字。
- f8 又加了两类提交：`9637bd9`、`b04e038` 只放验收物；`c39b465` 把「写好 · 用时」改成按 writtenAt − writingStartedAt 算。总控把 R277 rebase 到 `c39b465`，`direct-shot-detail.js` 用 R277 的版本；`tests/test_r276_direct_frontend.mjs` 两边合并，留 R277 的按钮文字「重写这一镜」和 f8 新加的镜卡耗时测试。rebase 后：pytest 204 项通过，R277 门禁 42/42，R276 门禁 26/26（证据 `~/.photo-content-os/evidence/R277-shot-visual-revision/rebase2/`）。
- R277 合成一个提交，带 `Request:`/`Verify:` 尾注（交付规则要求）。
- 交付卡：R276 合同把 `tests/test_r276_direct_video.py` 列为受保护测试，R277 改了它，G16 要对 R276 卡做 rebaseline。顺序已发给 f8 确认：f8 先在 `c39b465` 上 handoff 并推送 R276，然后 R277 以 `c39b465..HEAD` 为范围做交付，包括对 R276 卡的 rebaseline。
- 需求卡 H-01 写的「约 25% / 约 50% 柱子」是设计稿的示意；真实第 02 镜对应「25%」「估计 50%」，旧任务还要先点「让 Opus 看一遍」。没改卡（改卡会退回待确认），交付说明里写清。
