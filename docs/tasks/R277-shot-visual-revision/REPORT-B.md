R277 B 段前端汇报 · 2026-10-26

按本 worktree 的 TASK.md 第 0、3、4 节及交接 3/4 实施。详情、问题记录页、两个入口接点、夹具、测试、门禁和规定截图已交付；浏览器功能断言通过。**严格合同门禁尚未全绿，不报 READY**：R277 两种无草稿状态与合同必选编号冲突；R276 外层合同尚未收录已经批准的新入口文字。保持设计稿和批准文件原样，列清缺口后在本报告停止。

本段全部服务只用 8768。无提交、推送、回退或他人进程操作；没有改后端线程负责的文件、真实状态、真实素材、剪映草稿或成片。46 张最终截图逐张查看，包含实际旧任务首屏、完整长页、展开状态和手机表格三段水平覆盖。真实截图只是本机副本读取，不代表已部署或 R277 真模型链路验收。

**本段文件**

| 文件 | 改动 |
| --- | --- |
| `studio/static/direct-shot-detail.js` | 保持唯一导出 `renderShotDetail`；关键帧图片、按 boxes 的百分比热区、橙点与选中建议、四种块改法、整镜问题、补一句、Unicode 1–200 字校验、空要求失败/中断重试、重写遮罩和计时、baseVersion 对比/退回、样例开关、底部三个折叠和代码懒加载。 |
| `studio/static/direct-shot-detail.css` | 按 revise-extra.css 并入详情与记录页样式；颜色改为现有 styles.css 语义令牌；大图 360×640、比较图 300 宽，窄屏调整网格；修正按钮拆字、折叠标题拆字和记录表表头拆字。 |
| `studio/static/direct-revision-log.js`（新） | 保持唯一导出 `renderRevisionLog`；并读记录/样例、非零类别排序、按作品归组镜号去重排序、throughCount 计数、草稿状态、采用/不用、样例标题/日期和空态。 |
| `studio/static/direct-view.js` | 相对 `90875ba` 恰好两条原行替换：在现有上传配音按钮左侧插入记录入口；在 bindVoice 内接记录页/返回。原页面 DOM 暂存并恢复，返回重读任务。 |
| `scripts/direct_video/revision_frontend_gate.mjs`（新） | 真实 Studio 8768 + 临时状态；Playwright API 拦截；16 状态、1440/960、390 补充；实际点选/输入/发送；Core 合同清点；完整页面/首屏截图、尺寸/哈希、真实状态前后哈希与自有进程清理。 |
| `tests/test_r277_frontend.mjs`（新） | 16 份夹具、baseVersion、85 字要求；浏览器验证 Unicode 上限、坐标、编号/版号、轮询变化下选中/改法/值/焦点/光标/折叠保留、各镜独立、比较与退回条件、忙碌状态、中文失败表及未知码、请求载荷与 CSRF；记录页所有“现在”分支、来源和样例公式。 |
| `tests/test_r277_frontend.py`（新） | 无内联样式、无硬编码色值/本机路径、唯一导出、夹具版本来源；通过 git diff 的行数与精确内容锁定 direct-view 两处边界。 |
| `tests/fixtures/r277-revise/*.json`（新，16 份） | review、select、picked、rewriting2、compare、kept-prev、saved、review-failed、log、look-running、no-boxes、verify-running、verify-missed、verify-failed、log-empty、proposal-running。所有版本均含 baseVersion；第 1 版 null，示例第 2 版来源 1。select/picked 从真实点击与输入得到；rewriting2 从选好的四条要求实际发 revise 得到，夹具保留交互开始前的数据。 |
| `tests/test_r276_direct_frontend.mjs` | 仅迁移详情控件选择器/按钮文案；保持原输入、焦点、光标、切镜、禁用、空要求重试和导出断言。详细逐处说明见后。 |
| `scripts/direct_video/frontend_gate.mjs` | 仅迁移详情交互与 DV-DETAIL 合同边界，其他状态和功能断言保留。详细逐处说明见后。 |
| `docs/tasks/R277-shot-visual-revision/REPORT-B.md` | 本报告。 |

`tests/test_r276_direct_frontend.py` 未改，原有边界/无内联样式/懒加载约束继续通过。`review-view.js`、`index.html`、`direct.css`、design/ 以及后端文件均未由本段修改。实现文件 25 个（含 16 份 JSON），另加本报告。

轮询只在规定的字段签名变化时重画；同镜无变化时原输入节点不换。每镜单独保存选择、要求、补充句、折叠；重画保留焦点与 selection range。busy 时禁止右侧按钮、输入和折叠交互。看图/核对尚在运行且外层任务轮询已停止时，详情才补充轮询，防止 R276 在渲染结束后停轮询而卡在“正在核对”。离开/移除详情后停止刷新，避免迟到请求把记录页覆盖。采用新版只在本页/本地存储记下，读写存储均有 try/catch，不发 current。

**截图与逐图审查**

最终图片和清点文件：`~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/`。最终清单：[screenshot-manifest.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/screenshot-manifest.json)；逐图发现：[personal-review.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/personal-review.json)。清单记录实际 viewport、route、捕获时间、页面滚动覆盖、输出尺寸、SHA-256、浏览器、fallback-local 字体模式及 Codex /root 的审看结论。下面每个链接均核对存在且哈希匹配。

规定 16 状态 × 1440/960 共 32 张，展开状态 2 张，额外 390 状态 4 张，真实任务完整页/详情首屏 6 张，手机记录表补充 2 张，共 **46 张**。除明确标为 first-screen 的三张外，均捕获完整页面高度；真实完整页已看到底部。390 记录表初始图与 part-2/part-3 是同页的三部分，实际水平覆盖 0–300、160–460、320–620，连续无缝隙；没有把初始手机视口当作整张表。

真实数据来自 `~/.photo-content-os/studio-r276/` 的任务 `dv_0e184e961bd14ac084c67411`，先复制到临时状态再起服务，选中第 02 镜，不调用 look/revise/模型。原目录 **8599 文件前后 SHA-256 完全相同**：[source-preservation.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/source-preservation.json)。没有给旧镜头编造 boxes 或 findings。画面清晰为主，“让 Opus 看一遍”可见，整镜按钮和补一句没有被空状态藏掉。

夹具截图使用批准设计里的镜头 HTML 在独立设计浏览器里取关键帧，Studio 里始终只有 img，没有执行镜头 HTML、iframe 播放或拖帧控件。核对 done/missed 是合成夹具结果，不是真 Opus 判断。五张 `reference-*.png` 与 `poster-*.jpg` 是参考/夹具输入，不冒充应用验收截图。

| 最终图 | 实际视口 | 图片尺寸 | 逐图结论 |
| --- | --- | --- | --- |
| [real-worst-complete-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-complete-1440.png) | 1440×900 | 1440×2226 | 真实旧七镜任务副本；检查了成片、设计、七镜、第 02 镜详情至底部，完整覆盖。顶部用时受旧任务副本迁移 updatedAt 影响，单列给总控。 |
| [real-worst-first-screen-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-first-screen-1440.png) | 1440×900 | 1440×900 | 真实第 02 镜画面占主位；无块状态有补看入口，右侧不空；960 并排，390 上下布局。 |
| [real-worst-complete-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-complete-960.png) | 960×900 | 960×3055 | 真实旧七镜任务副本；检查了成片、设计、七镜、第 02 镜详情至底部，完整覆盖。顶部用时受旧任务副本迁移 updatedAt 影响，单列给总控。 |
| [real-worst-first-screen-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-first-screen-960.png) | 960×900 | 960×900 | 真实第 02 镜画面占主位；无块状态有补看入口，右侧不空；960 并排，390 上下布局。 |
| [real-worst-complete-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-complete-390.png) | 390×900 | 390×3715 | 真实旧七镜任务副本；检查了成片、设计、七镜、第 02 镜详情至底部，完整覆盖。顶部用时受旧任务副本迁移 updatedAt 影响，单列给总控。 |
| [real-worst-first-screen-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/real-worst-first-screen-390.png) | 390×900 | 390×900 | 真实第 02 镜画面占主位；无块状态有补看入口，右侧不空；960 并排，390 上下布局。 |
| [review-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-1440.png) | 1440×900 | 1440×1549 | 关键帧为主，三处橙点与右侧提示对应；页面底部三个折叠完整。 |
| [review-expanded-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-expanded-1440.png) | 1440×900 | 1440×1639 | 口播、提醒、五条硬规则与代码全部展开可读；标题/正文左边缘一致，长文本换行，底部完整。 |
| [review-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-960.png) | 960×900 | 960×1982 | 关键帧为主，三处橙点与右侧提示对应；页面底部三个折叠完整。 |
| [review-expanded-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-expanded-960.png) | 960×900 | 960×2235 | 口播、提醒、五条硬规则与代码全部展开可读；标题/正文左边缘一致，长文本换行，底部完整。 |
| [select-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/select-1440.png) | 1440×900 | 1440×1549 | 块名、热区选框、Opus 说明和建议对应；960 四个改法分两列，无拆字。 |
| [select-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/select-960.png) | 960×900 | 960×2006 | 块名、热区选框、Opus 说明和建议对应；960 四个改法分两列，无拆字。 |
| [picked-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/picked-1440.png) | 1440×900 | 1440×1557 | 三处编号与三条要求对应；补充句和焦点保留，85 / 200 字，底部未截断。 |
| [picked-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/picked-960.png) | 960×900 | 960×2157 | 三处编号与三条要求对应；补充句和焦点保留，85 / 200 字，底部未截断。 |
| [rewriting2-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/rewriting2-1440.png) | 1440×900 | 1440×1549 | 遮罩清楚，显示按 4 处改法重写和 0:42；右侧控制禁用，无去掉条目按钮，样例按钮不拆字。 |
| [rewriting2-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/rewriting2-960.png) | 960×900 | 960×2000 | 遮罩清楚，显示按 4 处改法重写和 0:42；右侧控制禁用，无去掉条目按钮，样例按钮不拆字。 |
| [compare-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/compare-1440.png) | 1440×900 | 1440×1484 | 两版关键帧、baseVersion 标题、四条核对、退回/采用按钮完整；960 的比较图和文字上下排列。 |
| [compare-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/compare-960.png) | 960×900 | 960×2360 | 两版关键帧、baseVersion 标题、四条核对、退回/采用按钮完整；960 的比较图和文字上下排列。 |
| [kept-prev-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/kept-prev-1440.png) | 1440×900 | 1440×1549 | 恢复旧画面；标题用第 1 版、共 2 版与退回说明一致，折叠和整镜区完整。 |
| [kept-prev-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/kept-prev-960.png) | 960×900 | 960×1984 | 恢复旧画面；标题用第 1 版、共 2 版与退回说明一致，折叠和整镜区完整。 |
| [saved-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/saved-1440.png) | 1440×900 | 1440×1549 | 第 01 镜显示绿色已存为样例；画面仍为主位，空修改区不做大卡。 |
| [saved-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/saved-960.png) | 960×900 | 960×1982 | 第 01 镜显示绿色已存为样例；画面仍为主位，空修改区不做大卡。 |
| [review-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-failed-1440.png) | 1440×900 | 1440×1549 | 无橙点；失败说明和重试入口明确，仍可选择整镜问题和补一句。 |
| [review-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-failed-960.png) | 960×900 | 960×1982 | 无橙点；失败说明和重试入口明确，仍可选择整镜问题和补一句。 |
| [log-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-1440.png) | 1440×900 | 1440×975 | 计数 3/2/1、作品来源、提案与两个样例层级清楚；960 表头不拆字。390 的同表分三部分连续覆盖。 |
| [log-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-960.png) | 960×900 | 960×1057 | 计数 3/2/1、作品来源、提案与两个样例层级清楚；960 表头不拆字。390 的同表分三部分连续覆盖。 |
| [look-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/look-running-1440.png) | 1440×900 | 1440×1549 | 无橙点；正在看图状态可读，右侧修改区和底部折叠完整。 |
| [look-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/look-running-960.png) | 960×900 | 960×1982 | 无橙点；正在看图状态可读，右侧修改区和底部折叠完整。 |
| [no-boxes-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/no-boxes-1440.png) | 1440×900 | 1440×1549 | 无热区；让 Opus 看一遍可见，整镜按钮/补一句可用；390 上下布局无水平溢出。 |
| [no-boxes-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/no-boxes-960.png) | 960×900 | 960×1982 | 无热区；让 Opus 看一遍可见，整镜按钮/补一句可用；390 上下布局无水平溢出。 |
| [verify-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-running-1440.png) | 1440×900 | 1440×1484 | 两版可见，四条均显示正在核对，未冒充完成；选择版本按钮仍可见。 |
| [verify-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-running-960.png) | 960×900 | 960×2360 | 两版可见，四条均显示正在核对，未冒充完成；选择版本按钮仍可见。 |
| [verify-missed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-missed-1440.png) | 1440×900 | 1440×1484 | 第 2 条未做到与黄色原因对齐，其余结果为绿；960 长行可读，无裁切。 |
| [verify-missed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-missed-960.png) | 960×900 | 960×2382 | 第 2 条未做到与黄色原因对齐，其余结果为绿；960 长行可读，无裁切。 |
| [verify-failed-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-failed-1440.png) | 1440×900 | 1440×1484 | 核对失败说明醒目，未显示虚假的做到了；两图和两个版本选择按钮仍完整。 |
| [verify-failed-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/verify-failed-960.png) | 960×900 | 960×2369 | 核对失败说明醒目，未显示虚假的做到了；两图和两个版本选择按钮仍完整。 |
| [log-empty-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-empty-1440.png) | 1440×900 | 1440×900 | 只有两条相应空态与小字号 0 镜，没有伪造提案或空大卡；返回入口清楚。 |
| [log-empty-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-empty-960.png) | 960×900 | 960×900 | 只有两条相应空态与小字号 0 镜，没有伪造提案或空大卡；返回入口清楚。 |
| [proposal-running-1440.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/proposal-running-1440.png) | 1440×900 | 1440×900 | 现在列显示正在起草规则，没有待采用草稿；样例及页面底部完整。 |
| [proposal-running-960.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/proposal-running-960.png) | 960×900 | 960×902 | 现在列显示正在起草规则，没有待采用草稿；样例及页面底部完整。 |
| [review-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/review-390.png) | 390×900 | 390×2688 | 关键帧为主，三处橙点与右侧提示对应；页面底部三个折叠完整。 |
| [compare-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/compare-390.png) | 390×900 | 390×2422 | 两版关键帧、baseVersion 标题、四条核对、退回/采用按钮完整；960 的比较图和文字上下排列。 |
| [no-boxes-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/no-boxes-390.png) | 390×900 | 390×2684 | 无热区；让 Opus 看一遍可见，整镜按钮/补一句可用；390 上下布局无水平溢出。 |
| [log-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-390.png) | 390×900 | 390×1136 | 计数 3/2/1、作品来源、提案与两个样例层级清楚；960 表头不拆字。390 的同表分三部分连续覆盖。 水平覆盖 0–300 / 620。 |
| [log-panel-part-2-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-panel-part-2-390.png) | 390×900 | 390×1136 | 手机记录表第 2/3 部分：水平 160–460，来源和提案操作可见，与两边重叠。 水平覆盖 160–460 / 620。 |
| [log-panel-part-3-390.png](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/log-panel-part-3-390.png) | 390×900 | 390×1136 | 手机记录表第 3/3 部分：水平 320–620，完整提案正文、依据与采用/不用可见。 水平覆盖 320–620 / 620。 |

**合同检查**

复跑：

```sh
HARNESS_CORE=~/Desktop/Opensource_Tool/Harness_Engineering/Core \
  node scripts/direct_video/revision_frontend_gate.mjs
```

功能断言 PASS；浏览器错误为空。Core `collect_design_inventory.js` + `check_design_contract.py check --contract design/contract.json --approved-extras design/approved-extras.json`：**34/38 通过**（32 规定状态图、2 展开图、4 手机图）。保留退出码 1，未放宽检查。每份 `{状态}-{宽度}.inventory.json` / `.contract.json` 与 [contracts.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/contracts.json) 可复核。

仅四份失败：`log-empty-1440`、`log-empty-960`、`proposal-running-1440`、`proposal-running-960`，均为 `design.missing-element: RV-PROPOSAL`。第 3.7 节把它们按 log 合同比对；现合同把草稿块列成必选，approved-extras 又没有将它列为可选。实际这两个状态应无待采用草稿，不能放一张假草稿来满足合同。需要总控在授权文件中声明相应条件，不由本段改批准文件。

手机表格补充分段通过外部执行探针 [phone-log-panel.mjs](~/.photo-content-os/evidence/R277-shot-visual-revision/phone-log-panel.mjs) 在同一 8768、隔离临时状态、相同拦截夹具补拍，尺寸和连续水平覆盖断言通过；[日志](~/.photo-content-os/evidence/R277-shot-visual-revision/phone-log-panel.log)。它没有修改应用或合同。

R276 门禁在 8768 执行：为遵守端口约束，使用仓库外的 [执行副本](~/.photo-content-os/evidence/R277-shot-visual-revision/r276-gate-8768.mjs)，只调整运行端口和 import/ROOT 的绝对解析；测试、状态和断言与已修改的仓库脚本相同。**所有功能断言执行到最后的合同总断言；26 份合同 16 通过、10 失败**，失败唯一文字是“画面问题记录”。涉及 empty、filled、unavailable、ready、done-silent 各两宽。此入口已经在 R277 设计稿获批，但 R276 文案合同还没有它；按“只跳过 DV-DETAIL，其余照旧”没有为它扩大 allowlist 或额外排除 DOM。见 [R276 日志](~/.photo-content-os/evidence/R277-shot-visual-revision/r276-gate.log)、[R276 合同结果](~/.photo-content-os/evidence/R277-shot-visual-revision/r276-regression/contracts.json)。R276 门禁另有 31 张机器捕获，属于既有回归运行输出；本段视觉交付及逐张审查范围是上表 46 张，不将机器捕获自动当成独立视觉通过。

**R276 测试与门禁逐处改动**

| 位置 | 原来 → 现在 | 保留的验收意图 |
| --- | --- | --- |
| test_r276_direct_frontend.mjs：详情 busy 检查 | `[data-rewrite]` → `[data-revise]` | 写/渲染中输入和提交按钮都不可用。 |
| 同文件：failed/interrupted/rendered 三状态矩阵 | 提交选择器换成 `[data-revise]`；有效要求按钮文案“让 Opus 重写这一镜” → “重写这一镜” | failed/interrupted 无要求能重试；rendered 无要求不能提交；有效意见能提交。 |
| 同文件：保留状态与导出 | 原输入值、焦点、光标、相同签名不换节点、换镜恢复与唯一导出断言保留 | 没有删除或放宽这些断言。 |
| frontend_gate.mjs：清点器 | visible 过滤只排除 `[data-design-id="DV-DETAIL"]` 整棵子树 | 其余 DOM 文字与编号照旧清点，不排除新入口。 |
| 同文件：合同必选编号 | 临时派生检查合同只去掉详情子树的 DV-DETAIL / DV-FACTS / DV-CHECKS / DV-REWRITE / DV-CODE / DV-PVNOTE | 仓库合同文件不改；其他必选编号、文案和状态不改。普通/real/live 三个清点入口同样应用此边界。 |
| 同文件：修改请求拦截 | 原 `/rewrite` 外，接 R277 详情的 `/revise`，严格要求单条 `{text:'数字再大一点',own:true}` | 仍要求只改第 03 镜；其他六镜字段、海报、写好时间均保持。空要求重试仍检查 R276 `/rewrite`。 |
| 同文件：详情输入与按钮 | `#dv-ask` → `[data-extra]`，按钮名称匹配 R277；代码折叠改按 DV-CODE 编号查找 | 真正发请求与代码展开才读取的原断言保留，代码读取次数仍从 0 变 1。 |
| 同文件：提醒可见性 | 先点开 DV-CHECKS，再要求构图提醒可见 | 提醒已按批准稿收进折叠，不能删掉原提醒断言。 |
| 状态矩阵与其他测试 | 原 13 状态、两宽及原 5 个手机状态全部保留 | 轮询启动/停止、选镜保持、离页停轮询、空要求重试、导入、配音、生成、成片跳转/合成与未涉及镜不变均保留并执行。 |

G16 交接：总控修改的 `tests/test_r276_direct_video.py` 字段集合（16 旧 + 5 新、严格相等）不属于本段修改。R276 卡 H-03 的“不改其他镜”仍由 `test_rewrite_only_one_shot_and_invalidate_output` 及 R276 REPORT-B 真跑证据承担，不依赖本段详情 DOM 测试。本段没有改人工验收项或签署 H-01–H-03，也没有在门禁未绿时生成 READY/handoff。

**测试与常规检查**

固定 `.venv/bin/python`；文档检查显式设 `OBSIDIAN_ROOT` 为既有自媒体库，`UI_COPY_QUALITY_CHECKER` 指向 Core。相关组合 **115 passed, 2 skipped（159.38 秒）**；最后一次前端静态/公式子集 **10 passed**。R277 浏览器断言由门禁执行，包含 R276 `testDetail`，不能用仅运行 mjs 的夹具审计替代。

| 命令 | 结果 | 完整输出 |
| --- | --- | --- |
| `bash scripts/check_runtime_contract.sh` | 通过 | [check_runtime_contract.log](~/.photo-content-os/evidence/R277-shot-visual-revision/check_runtime_contract.log) |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 通过 | [validate_music_analysis_registry.log](~/.photo-content-os/evidence/R277-shot-visual-revision/validate_music_analysis_registry.log) |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 通过 | [check_repository_safety.log](~/.photo-content-os/evidence/R277-shot-visual-revision/check_repository_safety.log) |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 未通过（原因见下） | [check_obsidian_doc_sync.log](~/.photo-content-os/evidence/R277-shot-visual-revision/check_obsidian_doc_sync.log) |
| `.venv/bin/python scripts/check_outline_contract.py .` | 未通过（原因见下） | [check_outline_contract.log](~/.photo-content-os/evidence/R277-shot-visual-revision/check_outline_contract.log) |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 通过 | [validate_content_os_task.log](~/.photo-content-os/evidence/R277-shot-visual-revision/validate_content_os_task.log) |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 通过 | [validate_jianying_draft.log](~/.photo-content-os/evidence/R277-shot-visual-revision/validate_jianying_draft.log) |
| `.venv/bin/python -m pytest -q tests/test_r276_direct_video.py tests/test_r276_direct_frontend.py tests/test_r277_frontend.py tests/test_r277_revisions.py tests/test_r277_api.py tests/test_r277_boxes.py tests/test_p2_frontend_contract.py tests/test_r220_number_formulas.py tests/test_checklist_remediation_static.py tests/test_desktop_openapi_route_sync.py` | 通过 | [targeted-pytest.log](~/.photo-content-os/evidence/R277-shot-visual-revision/targeted-pytest.log) |
| `.venv/bin/python -m pytest -q tests` | 1016 passed、36 skipped、9 failed、6 errors；2003 subtests passed；399.12 秒 | [pytest-all.log](~/.photo-content-os/evidence/R277-shot-visual-revision/pytest-all.log) |
| Core ui-copy-quality 检查两个新增/替换 JS | PASS，0 warnings；只代表词法检查 | [ui-copy-quality.log](~/.photo-content-os/evidence/R277-shot-visual-revision/ui-copy-quality.log) |
| 最后补充的轮询归属浏览器检查 | PASS：外层已停的 ready 镜补轮询 1 次，外层仍轮询的 writing 任务补轮询 0 次，避免双轮询 | [polling-ownership.log](~/.photo-content-os/evidence/R277-shot-visual-revision/polling-ownership.log) |
| R277 真实浏览器断言、数字公式、版本条件与请求 | PASS；严格合同仍有上述四项失败 | [frontend-gate.log](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend-gate.log) |

全量失败逐项（均未由本段修改修复）：

- `FAILED tests/test_bilingual_subtitles_r6.py::BilingualCaptionTests::test_real_two_layer_burn`
- `FAILED tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_chinese_glyphs_do_not_fall_back_to_identical_missing_glyph_boxes`
- `FAILED tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_real_cut_first_frames_80166667_and_122866667`
- `FAILED tests/test_direct_video_subtitles.py::RenderedSubtitleTests::test_white_text_has_a_dark_backplate_on_white_and_black`
- `FAILED tests/test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies`
- `FAILED tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_black_native_frames_fail_even_with_burned_subtitles`
- `FAILED tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_few_dots_is_not_a_black_frame`
- `FAILED tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_dark_design_with_a_small_white_header_is_not_a_black_frame`
- `FAILED tests/test_pf_video_pipeline.py::PreviewAndBlackFrameTests::test_uniform_deep_gray_has_no_content_and_fails`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_alpha_and_geometry_have_exact_pixel_bounds`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_changed_source_fails_projection`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_editable_document_structure_and_neutral_producers`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_every_frame_matches_retained_source_clock`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_projection_checks_preview_waveform_and_no_local_paths`
- `ERROR tests/test_pf_video_pipeline.py::FrameMappingTests::test_real_silence_envelope_has_no_simulated_peaks`

其中 14 项失败/错误是本机 ffmpeg 无 drawtext（与任务单交接 3 一致），包括双语烧字、直出字幕和 PF 测试初始化；1 项是未改动文档的 Obsidian 同步新旧时间检查。`check_obsidian_doc_sync.py` 的三个 source-newer 项分别指向协同规范、剪辑交接、历史剪映说明；`check_outline_contract.py` 被同一同步子检查阻断。没有改它们的文档、测试、基线或同步标记。

真实副本读取的额外观察：R276 外层“从点生成到出片用时”按 createdAt/updatedAt 算；旧任务迁移使副本 updatedAt 更新，最终完整图顶部出现 135:17，而原任务实际生成耗时不能据此重算。该数字位于本段禁止修改的 R276 外层/后端字段范围，只记录给总控/后端线程，不改字段含义，也不把它当作真实生成时间证据。

**需要的接口**

本段新增交互所需接口已齐，无另外新增接口请求。依赖 REPORT-A/A2 的 revise、current、look、PUT/DELETE sample、revision-log、samples、adopt/reject、code、版本化 poster。baseVersion 已按 3.4 写入全部夹具；来源未知的历史非首版不猜为 N−1、不出现对比。写请求均带同源凭据与 bootstrap CSRF。A2 实现/测试仍归后端线程；本段没有调整其字段或 schema。

**需要新文案**

R277 产品文案无新增申请，失败翻译使用 approved-extras，未知码沿用 R276 中文兜底。需要总控处理的跨合同引用是：让 R276 合同承认 R277 已批准的“画面问题记录”入口（10 份检查失败）；本段未自行加批准条目。

**稿外元素**

无新增稿外产品块或自造设计编号。待解决的是无草稿状态的 RV-PROPOSAL 必选冲突（四份检查失败），应由总控明确该块在对应状态的条件性，而非添加空提案块。关键帧说明 DV-PVNOTE 已获批准；稿里的 DV-SCRUB 按任务单不做，没有补播放/拖帧假功能。

**Git 状态与停止点**

业务 worktree 有本段未提交改动，同时保留开场已有的后端 A/A2、总控测试集合改动及预置文档；完整状态：[business-git-status.txt](~/.photo-content-os/evidence/R277-shot-visual-revision/business-git-status.txt)。Harness SSOT 仓库本来有其他工作区改动，本段未修改任何 Harness 文件；只读状态：[harness-git-status.txt](~/.photo-content-os/evidence/R277-shot-visual-revision/harness-git-status.txt)。没有创建或修改声明的 SSOT 开发包，本报告/截图属于普通交接证据，不触发 SSOT Obsidian 快照。

8768 临时服务均已关闭；8765/8766 未访问或操作。按本段要求在这里停止；不提交、不推送，交给总控审查上述合同缺口与交接结果。


## 第 2 轮

按 TASK.md「交接 5」只处理 B2-1～B2-4。本节是本轮结果；前文第 1 轮的合同缺口记录保留，现已由总控补齐批准后重新检查通过。本轮未修改两份 approved-extras.json，也未修改 A3 后端及其测试。

**B2-1：无块提示**

`direct-shot-detail.js` 在 boxes 为空时将 RV-INSPECT 标题改为已批准的「这一镜还没有可以点的块」，下一行使用独立 `btn btn--sm`「让 Opus 看一遍」。标题不再出现「在左边画面上点要改的地方」。沿用既有空态左对齐和间距；960 宽没有行内挤压或前置缩进。无块夹具、真实旧任务第 02 镜均重新截取 1440/960/390，见下表。新增布局断言核对准确标题、按钮类名、上下位置和相同左边界。

**B2-2：记录页说明**

`direct-revision-log.js` 将说明段落移到标题与返回操作之外，作为同一页头网格的整行；`direct-shot-detail.css` 让标题与「回到作品」同排，说明跨两列。保留原说明文案。实测 1440 宽说明为 1182px、960 宽为 718px，均大于 600px，均单行（高 20.625px）；390 宽为 300px，正常三行。门禁增加说明宽度、1440 单行和返回按钮位置断言；log-empty/proposal-running 一并验证。

**B2-3：960 对比顺序**

比较状态的 `.rv-head` 从右栏移为比较容器的独立子节点，只渲染一份。CSS 在 1440 保持标题位于两图右侧；960 和手机按「标题/样例 → 两图 → 退回/采用 → 这次改的 → 三个折叠」排列。compare 与 verify-running/missed/failed 全部重新截图，门禁按元素坐标检查先后次序，并检查桌面标题仍在右侧。

**B2-4：门禁、测试与截图**

本轮改动文件共 6 个：`studio/static/direct-shot-detail.js`、`studio/static/direct-shot-detail.css`、`studio/static/direct-revision-log.js`、`tests/test_r277_frontend.mjs`、`scripts/direct_video/revision_frontend_gate.mjs`、本报告。测试新增 `testB2Layout`，R277 门禁在截图前调用并将测量值写入 manifest 的 `layout_checks`。没有删状态、放宽原断言或扩展批准内容。

R276 的测试、受版本控制的 `frontend_gate.mjs` 本轮均未改；第 1 轮经批准的改动仍按前文记录。因该脚本固定使用 8767，本轮在仓库外生成执行副本，只将端口改为 8768，并适配 ROOT/import 的绝对路径后运行，同一份夹具、断言和合同不变。执行副本保存在本轮证据目录，便于复核。

| 检查 | 本轮结果 | 证据 |
| --- | --- | --- |
| R277 功能与设计合同 | 功能 PASS；38/38 合同 PASS；浏览器错误 0 | [运行日志](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/gate.log) · [合同逐项结果](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/contracts.json) |
| R276 回归与设计合同 | 功能 PASS；26/26 合同 PASS；31 份完整页捕获 | [运行日志](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/r276-gate.log) · [合同逐项结果](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2-r276/contracts.json) |
| 定向 pytest | 17 passed in 0.71s | [pytest.log](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/pytest.log) |
| Runtime contract | PASS（compileall/packages/encoding/safety） | [runtime.log](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/runtime.log) |
| Repository safety --base origin/main | PASS | [repository-safety.log](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/repository-safety.log) |
| Core UI 文案词法检查 | PASS，2 文件、0 warning | [copy-quality.log](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/copy-quality.log) |
| git diff --check | PASS | 最终执行无输出，退出 0 |

定向 pytest 文件为 `tests/test_r277_frontend.py`、`tests/test_r276_direct_frontend.py`、`tests/test_p2_frontend_contract.py`、`tests/test_r220_number_formulas.py`、`tests/test_checklist_remediation_static.py`。本轮未重跑全量 pytest；前文全量结果属于第 1 轮，不作为本轮重跑结果。A3 的语义和后端测试归 cdx 1，本轮未作其验收结论。

截图目录：~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/。R277 共 46 张最终交付图，均在最后一次视觉改动后捕获，并由本线程逐张打开查看至底部；实际视口、路由、时间、滚动范围、输出尺寸、SHA-256、逐张意见见 [screenshot-manifest.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/screenshot-manifest.json) 和 [personal-review.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/personal-review.json)。R276 的 31 张为机器回归捕获，不混入这 46 张个人看图结论。以下是本轮最终截图链接：

| 状态 | 1440 | 960 | 390 | 看图重点 |
| --- | --- | --- | --- | --- |
| no-boxes | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/no-boxes-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/no-boxes-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/no-boxes-390.png) | 无块标题准确；独立 btn btn--sm 在下一行左对齐，无矛盾引导；画面与底部折叠完整。 |
| real-worst-first-screen | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-first-screen-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-first-screen-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-first-screen-390.png) | 真实旧任务副本第 02 镜；画面为主，无块标题和独立小按钮可见，右栏层级清楚。 |
| real-worst-complete | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-complete-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-complete-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/real-worst-complete-390.png) | 真实旧任务副本整页至底部；无块提示、整镜改法、补一句和折叠完整，未裁切。 |
| log | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-390.png) | 说明充分利用页宽；1440/960 单行、回到作品与标题同排；390 表格可横向滚动，另两张覆盖右侧；样例至底部完整。 |
| compare | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/compare-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/compare-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/compare-390.png) | 1440 标题仍在图片右侧；960/390 标题在两图上方，后接退回/采用、改法、折叠，无重复标题。 |
| verify-running | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-running-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-running-960.png) | — | 标题顺序正确，正在核对状态可读；两图、选择按钮、改法、折叠完整。 |
| verify-missed | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-missed-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-missed-960.png) | — | 标题顺序正确，没做到与原因可读；两图、选择按钮、改法、折叠完整。 |
| verify-failed | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-failed-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/verify-failed-960.png) | — | 标题顺序正确，核对失败说明可读且仍可比较；两图与底部完整。 |
| log-empty | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-empty-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-empty-960.png) | — | 标题/返回同排，说明宽度足够；真实空记录和空样例提示完整，无空草稿占位。 |
| proposal-running | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/proposal-running-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/proposal-running-960.png) | — | 记录页说明宽度足够；正在起草状态完整，无假草稿，样例底部完整。 |
| review | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-960.png) | [390](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-390.png) | 关键帧为主，问题角标、改法入口和底部折叠完整；手机正常堆叠。 |
| review-expanded | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-expanded-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-expanded-960.png) | — | 口播、规则、代码三处展开内容均可读，长文换行，底部完整。 |
| select | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/select-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/select-960.png) | — | 选中块边框与建议角标清楚，改法按钮对齐；960 两列适配。 |
| picked | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/picked-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/picked-960.png) | — | 三条编号改法、补一句与 85/200 字清楚；按钮和底部折叠完整。 |
| rewriting2 | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/rewriting2-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/rewriting2-960.png) | — | 0:42 重写遮罩与右栏禁用清楚，样例文字未挤折，底部完整。 |
| kept-prev | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/kept-prev-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/kept-prev-960.png) | — | 退回说明、当前版与共两版信息完整，主画面/改法/底部折叠可读。 |
| saved | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/saved-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/saved-960.png) | — | 已存为样例状态清楚；画面、无发现说明、改法及底部折叠完整。 |
| review-failed | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-failed-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/review-failed-960.png) | — | 失败中文说明和重试入口可读，无热区角标误报，仍可选整镜改法，底部完整。 |
| look-running | [1440](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/look-running-1440.png) | [960](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/look-running-960.png) | — | 正在看画面提示清楚，无橙点；整镜改法和底部折叠完整。 |

390 记录表是同一页的连续横向分段：上表 log-390 是第 1 段（0–300）；[第 2 段](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-panel-part-2-390.png) 为 160–460，[第 3 段](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/log-panel-part-3-390.png) 为 320–620，重叠覆盖完整表宽。三张均含全页至样例底部。[分段捕获日志](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/phone-log-panel.log)。真实最差首屏是滚到选中镜头后的指定视口，另有完整页图，不以首屏代替完整页面。

真实状态读取自 `~/.photo-content-os/studio-r276/` 的临时副本；原件 8599 个文件哈希前后一致，见 [source-preservation.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/source-preservation.json)。两份批准文件本轮前后 SHA-256 一致，见 [approved-files-preservation.json](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/approved-files-preservation.json)。R277/R276 合同全部通过，无待补新文案、稿外元素或新增接口需求；B2-1 使用总控已批准标题。验证范围是本地 8768 Studio，未作生产发布或全站/人工验收声明。

业务 worktree 仍包含本段与并行线程的未提交改动，见 [business-git-status-final.txt](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/business-git-status-final.txt)；Harness SSOT 仓库仍有开场已存在的其他改动，本线程未写入 Harness，见 [harness-git-status-final.txt](~/.photo-content-os/evidence/R277-shot-visual-revision/frontend/b2/harness-git-status-final.txt)。本轮没有声明的 SSOT 开发包变更。8768 临时服务已退出（无监听）；8765/8766 未操作。未提交、未推送，按要求在此停止。
