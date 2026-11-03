# 工作台前端五处修复（Pho_R01）

需求卡：`acceptance/requests/2026-W45/2026-11-04-Pho_R01-frontend-debt-fix/`（标准只读，不许改）。
来源：前端设计工具技术债体检，用户要求按优先级并行修复。所有线程共用这一个任务 worktree，只改自己名下的文件。

## 公共约束

- 先读 `develop/Harness/ai-coding-rules.md` 下表列出的行，开工说明每行落在哪段改动，汇报逐行交结果。
- 不提交、不推送、不 rebase、不回退别人的改动、不杀别人的进程。总控负责提交。
- 只用下面文案表里的字。要新文案或稿外元素：写进汇报「需要新文案」后继续做别的，不自己编。
- 不改字号、圆角、间距这些写死的样式；不做组件重构；不改后端上限的值。
- 别的线程造成的失败只列出，不修。
- 开发机现在连不上（端口拒绝），这次测试在本机跑：只跑下面点名的 node 和 pytest；**不开浏览器**，浏览器冒烟由总控做。开跑前读 `sysctl vm.swapusage`，已用超过 97% 就等，最多等 10 分钟后只跑 node 测试。Python 用主检出的 `.venv`（`git worktree list` 第一行是主检出）。
- 改旧测试前先查 `protected_tests`（受保护测试不许改断言，写进汇报）。

## 规则卡短表

| 触发场景 | 必须做到 | 会失败的反例 | 检查命令 |
| --- | --- | --- | --- |
| FE-21 输入上限 | 超出时保留原文、标红、写超出多少、不让提交；前后端上限同源 | 留着 maxlength，粘贴被静默截断 | 新单元测试：2001 字不丢字且 overBy=1；测试读 `studio/api_contract.py` 的 maxLength 和前端常量比对 |
| BE-11 未知失败码 | 不认识的码原样露出，不用通顺话盖住 | `failureMessage('x')` 仍返回「读不到这一镜的状态」 | 单元测试：未知码输出含码；不带码的调用点不再落到这句 |
| FE-07 按钮 | 按钮字不可选 | 共享样式没有 `user-select:none` | 体检「按钮文字可能被选中」降到 0 |
| FE-06 事件 | 键盘处理绑在当前组件内，重绘后仍在 | 绑到 document，切页后还响应 | 单元或静态测试：处理函数在 tablist 上 |
| FE-09 同一事实一份实现 | 上限判定只有一份函数，各处调它 | 每个文件各写一遍判断 | `rg 'maxlength=' studio/static` 为 0 |
| TEST-15 分层 | 能下沉的写单元测试 | 用浏览器检查纯函数 | 新增测试是 node 单元测试 |

## 跨线接口（T1 实现，T2 调用）

文件 `studio/static/input-limit.js`，ES 模块：

| 函数 | 参数 | 返回 / 行为 |
| --- | --- | --- |
| `overBy(value, limit)` | 字符串、正整数 | 超出字数，按码位数（`[...value].length`，和后端 `len` 一致），不超为 0 |
| `syncLimit(field)` | 带 `data-limit` 的输入框 | 超出时给框加 `is-over`、`aria-invalid="true"`，并在框后放一个 `<small class="limit-hint" role="alert">`；不超时移除这些。返回超出字数 |
| `bindLimits(root)` | 容器 | 给 root 内所有 `[data-limit]` 绑 input 并同步一次；重复调用不重复绑、不重复放提示 |
| `anyOver(root)` | 容器 | root 内有超出的框返回 true |

`maxlength` 全部换成 `data-limit`，数值不变。样式 `.is-over`、`.limit-hint` 由 T1 写进 `styles.css`，颜色用已有的错误色令牌。T1 没落盘时 T2 先按这张表写，文件到了再跑。没写到的细节由 T1 定，追加到本文末「共用约定」。

## 文案表

| 位置 | 文字 |
| --- | --- |
| 超长提示 | `超出 {N} 字`，N=字数−上限 |
| 确认框标题 | `移入回收站？` |
| 确认框正文 | `确认将选中的 {N} 项移入系统回收站？`，N=`selectedDeleteNumbers.length` |
| 确认框按钮 | `取消`、`移入回收站` |
| 未知失败码 | `没做成（错误码 {code}），可以重试` |
| 风格库读取失败 | `读不到风格库，点重试` |
| 修改记录读取失败 | `读不到修改记录，点重试` |
| 视频播放失败 | `视频播放失败，再点一次试试` |
| 镜头状态读取失败 | `读不到这一镜的状态，点重试`（只留给真的读状态失败） |
| 镜头缩略按钮的名称 | `第 {NN} 镜`（读屏用，`aria-label`，不新增可见文字） |

## T1：外壳（只改 `index.html`、`app.js`、`styles.css`、`review.css`、新建 `input-limit.js`，都在 `studio/static/`）

1. 建 `input-limit.js`。`index.html` 全部 `maxlength` 换 `data-limit`。项目表单和登录表单提交前调 `anyOver`，超出不提交；提交按钮按它禁用。
2. `app.js:73` 的 `window.confirm` 换成确认框。沿用已有写法：`index.html` 里加 `<dialog id="confirm-dialog">`，表单类用已有的 `.dialog-form`，按钮用已有 `.btn`、`.btn--pri`（这是移入系统回收站，能恢复，不用危险色）。取消和 Esc 什么都不做。默认焦点在「取消」。
3. 共享按钮样式加 `user-select:none`：体检点名 `styles.css` 2 处、`review.css` 3 处。
4. 测试：新建 `tests/test_input_limit.mjs`（overBy、syncLimit 用最小替身、上限和 `studio/api_contract.py` 比对）。

## T2：脚本直出（只改 `studio/static/` 下 `direct-storyboard.js`、`direct-style.js`、`direct-view.js`、`direct-revision-log.js`，以及它们的测试）

1. `direct-storyboard.js:49`、`direct-style.js:36,42,43` 的 `maxlength` 换 `data-limit`；每次重画后调 `bindLimits`；提交类按钮（开始、先定风格、改）在 `anyOver` 为真时禁用。注意 `pasteRows` 分行粘贴后的行也要同步。
2. `direct-view.js:16` 的 `failureMessage`：认识的码照旧；不认识的按文案表露码；不传码不再返回兜底句，调用点改成文案表里对应的句子（`:146` 风格库、`:176` 播放、`direct-revision-log.js:24,31` 修改记录）。把全部调用点逐个列进汇报，文案表对不上的保留原样并写进「需要新文案」。
3. 测试：更新 `tests/test_r276_direct_frontend.mjs` 里相关断言前先查保护；加未知码用例。

## T3：无障碍（只改 `studio/static/review-view.js`、`review-shots.js`，以及它们的测试）

1. `review-view.js:97` 做法页签：左右方向键切换、循环，Home/End 到首尾；选中的 `tabindex=0`，其余 `-1`；切换后焦点跟到新页签（注意重绘后恢复焦点）。键盘处理绑在这个 tablist 上。没有对应面板 id 时不要编 `aria-controls`。
2. `review-shots.js:75` 的 `data-hero` 按钮加 `aria-label`。
3. 测试：node 单元测试覆盖方向键计算（把下一个页签的计算写成纯函数）。

## 验收（各线程跑自己的部分）

```
node tests/test_input_limit.mjs                # T1
node tests/test_r276_direct_frontend.mjs       # T2
node tests/test_r278_direct_rescript.mjs       # T2
<主检出>/.venv/bin/python -m pytest -q tests/test_r276_direct_frontend.py tests/test_r278_direct_frontend.py tests/test_r283_frontend.py tests/test_checklist_remediation_static.py tests/test_p2_frontend_contract.py
```

汇报写进最后一条消息：改了哪些文件、规则卡逐行结果、测试原始结果（含 Ran N 或 passed 数）、需要新文案、别人造成的失败。

## 共用约定

## 第二段（T2 续）：不带码的失败不再落到「读不到这一镜的状态」

总控定文案（并入文案表）：

| 位置 | 文字 |
| --- | --- |
| 这一镜失败且没有错误码（`direct-view.js:161`） | `这一镜没写成，可以重试` |
| 整个任务或写入失败且没有错误码（`:212`、`:246`、`:252`、`direct-style.js:48`、`direct-revision-log.js:31`） | `没做成，可以重试` |
| 脚本导入失败（`:239` 非 wav 分支） | `导入失败，可以重试` |
| 输出检查某项数据缺失（`:176–178`） | `读不到这项检查结果` |

- 改完后 `读不到这一镜的状态` 只允许出现在真正读任务状态失败的 `:148`。
- `direct-shot-detail.js:8` 的 `message` 也要处理：`failureMessage` 对空码现在返回空串，这里不能显示空白，用 `没做成，可以重试`。这一段允许改这个文件。
- 测试断言：上述每处不再出现旧句；`:148` 仍是旧句（静态检查即可）；`direct-shot-detail` 空码不为空。
- 只改这几个文件和 `tests/test_r276_direct_frontend.mjs`，其余约束同前。

## 第三段（总控复验后的修正）

T1：
1. 看图发现 `<dialog>` 没有任何样式，用的是浏览器默认的 3px 黑边，新确认框和新建作品框都带着它。在 `styles.css` 加 `dialog{border:0;padding:0;background:transparent;border-radius:10px}`，`.dialog-form` 圆角同为 10px，加已有令牌的遮罩 `dialog::backdrop`（如已有则沿用）。别的页面不动。
2. `user-select:none` 改到 `styles.css` 基础的 `button{...}` 规则上一处，并把上次散加到 `.btn`、`.btn--pri`、`.cap .btn`、`.hero-ctl .btn`、`.topbar .btn` 的声明全部删掉。验收：重跑体检「按钮文字可能被选中」为 0；如工具仍报，把报的选择器写进汇报，不要逐个加回。

T3：
`review-shots.js:75` 的 `data-hero` 按钮（内容只有 `<i>`）核对有没有 `aria-label="第 NN 镜"`，没有就加，并在 `tests/test_review_tabs.mjs` 加静态检查。

约束同前：不提交，只改自己名下文件。
