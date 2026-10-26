# R283 风格库前端汇报

2026-10-27。前端任务单范围完成，未提交、未推送。结论覆盖本地 Studio 的前端、只读风格库接口、夹具合同和截图；不代表真实模型生成七镜、生产部署或人工验收通过。

## 1. 文件与设计依据

以 `docs/tasks/R278-direct-rescript/design/spec.html`、`draft.js`、`draft.css`、`lib-data.js` 和最新 `contract.json` 为设计依据，沿用 `studio/static/styles.css` 令牌、现有 `.dv-sw-card`、`.dv-sw-cards`、按钮和分段控件。没有重写设计稿或添加稿外文字。

本段修改：

- `studio/static/direct-style.js`：两组成片/库卡片共享画法和单选状态；库视频、空选择预览、生成载荷与来源文字；返回媒体清理函数。
- `studio/static/direct-view.js`：读取 `library`，保留库选择，移除无成片时强制从头定的分支；管理预览媒体的切换与离页释放。
- `studio/static/direct-rescript.css`：现有预览尺寸规则覆盖视频；≤620 宽时预览与元数据上下排。
- `tests/test_r283_frontend.mjs`、`tests/test_r283_frontend.py`：新功能、媒体生命周期、手机布局、合同相关和静态检查。
- `tests/fixtures/r283-direct/`：`first-lib.json`、`first-none.json`、`library.json`。
- R278 的 19 份状态夹具、`tests/test_r278_direct_rescript.mjs`、`scripts/direct_video/rescript_frontend_gate.mjs`；R276 的 `scripts/direct_video/frontend_gate.mjs`。具体增量见第 5 节。
- 本报告。没有暂存本段改动。

## 2. 功能完成情况

| 任务项 | 实现与验证 |
| --- | --- |
| 两组现成风格 | 有成片时上方为这台电脑上做过的，下方固定显示风格库九张卡；顺序与接口一致。复用同一张卡组件，库卡没有时间行。九次选库卡与切回成片卡均断言全屏仅一张选中。 |
| 库预览 | 右侧使用对应 `clipUrl`、`posterUrl`，180×320，静音、循环、进屏自动播放、出屏暂停；减少动态效果时停住，媒体错误回退样张图。标题、样张说明、四色、字号、动作规矩和不用完整。复用 `direct-storyboard.js` 的 `bindClips`，切卡、切分段、生成后和离页时清理观察器与播放。 |
| 调整与生成条 | 库卡同样保留「在这个风格上改哪里」；生成条为库名称，可追加调整文字。切到从头定再回来，库选择与调整文字仍在。 |
| 生成请求 | 未调整发送 `styleBase:{kind:'library',id:'flat'}`、`style:''`；有调整时发送相同库来源和原调整文字。均由真实页面点击生成后检查拦截到的载荷；不触发真实生成。 |
| 全片设计来源 | `design.source.kind==='library'` 显示「用风格库「扁平插画」的风格」，纯函数与实际页面均验证。 |
| 没有本机成片 | 默认选现成风格，分段可点；最近成片组换成批准提示，九张库卡不预选；空预览与警示生成条正确，生成禁用。选库卡后才可生成；旧 `first-none-r278` 已删除，由 `first-none` 取代。 |
| CSP、颜色和窄屏 | 无新增内联 `style=`，色块由既有 CSSOM 写令牌变量，CSS 无新硬编码颜色。390 宽度发现原预览固定双栏挤出元数据，已改为手机上下排并通过反例回归、截图目检；1440、960 的设计布局保留。 |

## 3. 先红后绿与检查结果

证据根：`~/.photo-content-os/evidence/R283-direct-style-library/frontend/`。本节日志名均相对该目录。

- 实现前新增 Node 测试失败：旧实现将库对象错发为 `kind:'job'`，并带未定义的项目/任务字段，见 `red-node.log`。
- 实现前静态检查 2 项失败：没有库组件/共享播放接入，夹具仍有旧空状态，见 `red-pytest.log`。
- 手机反例失败：预览色板和「不用」标签越过元数据区域。保留失败记录 `red-phone.log`；修复后同时断言实际视口、页面滚动宽和元数据子元素边界。
- 初次浏览器测试另修正了一条测试自身的 URL 比较：共享回退函数写 `Image.src` 会规范化为绝对 URL，现在与页面基址解析后的同一目标比较，产品回退逻辑未改。

| 检查 | 最终结果 | 证据 |
| --- | --- | --- |
| `node tests/test_r283_frontend.mjs` | PASS | `node-r283.log` |
| `node tests/test_r278_direct_rescript.mjs` | PASS | `node-r278.log` |
| 前端 pytest：R283、R278、R276、R277 | **15 passed** | `pytest.log` |
| `rescript_frontend_gate.mjs --checks-only` | **44/44** 合同；22 状态 × 1440/960，216 块；R283/R278 真实页面挂载交互通过，另含两种 390 手机状态布局检查 | `checks.log`、`checks-contracts.json` |
| R276 `frontend_gate.mjs --checks-only` | **26/26** 合同，既有公式及交互通过 | `r276-checks.log` |
| R277 `revision_frontend_gate.mjs --checks-only` | **42/42** 合同；详情、版本、日志、标记、轮询检查通过 | `r277-checks.log` |
| `check_repository_safety.py --base HEAD` | PASS，当前工作区与暂存区 | `safety.log` |
| 工作区、暂存区 `git diff --check` | PASS | 收尾工具记录 |

合同使用 Core 原版 `collect_design_inventory.js` 的 `options.states` 逐块采集，运行原版 `check_design_contract.py`。门禁额外断言：采集块集合必须与最新合同排除 `rescript-newer`、`first-handoff` 后的全部块严格相等。未修改判据、合同或 `approved-extras`。

临时 Studio 的**真实只读接口**还做了核对：`GET /api/direct/styles` 的九种库元数据与夹具逐字段相同，九张 JPG 各返回 200 并与源文件哈希相同，九段 MP4 各验证 `bytes=0-63` 的 206 Range 内容。记录在 `real-library-api.json`。这证明当前 S/B 已就位的读取链路；未把 B 段历史报告中的缺媒体失败当作当前通过证据，也未代跑模型或七镜生成。

R277 设置 `R277_SOURCE_STATE=~/.photo-content-os/studio-r278`，沿用 APFS `cp -cR` 临时克隆，结束删除；源目录 8,670 个文件前后哈希一致，见 `r277/source-preservation.json`。本段没有跑全量 pytest。所有浏览器均无头，同一时间一个，门禁串行，端口 8768，用完关闭。

## 4. 截图清单与看图结论

图库为证据根的 [gallery.html](~/.photo-content-os/evidence/R283-direct-style-library/frontend/gallery.html)。以下 14 张任务截图均在最后视觉改动后重新拍摄，实际视口 1440×900、960×900；捕获时间为 2026-10-27 02:27:19–02:27:45（台北）。每张都从页面顶部滚到真实底部再拍完整页面，并已本人逐张查看至底部。

所有文件位于 `~/.photo-content-os/evidence/R283-direct-style-library/frontend/`。

| 状态 | 1440 截图 | 960 截图 | 两张分别目检后的结论 |
| --- | --- | --- | --- |
| `first-lib` | [first-lib-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-lib-1440.png) | [first-lib-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-lib-960.png) | 九张库卡顺序清楚、首卡单独高亮；1440 右侧真实样张与元数据对齐，960 上下排后预览、禁用项和底部生成条完整。 |
| `first-none` | [first-none-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-none-1440.png) | [first-none-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-none-960.png) | 没有最近成片卡，库卡均未选；两张均能辨认空预览、选择说明和警示生成条，生成禁用；960 只在表格内横滚。 |
| `library` | [library-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/library-1440.png) | [library-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/library-960.png) | 两张全片设计均显示库来源、四色、动作规矩和不用，邻近进度、镜头列表和详情完整；960 来源换行可读。 |
| `rescript` | [rescript-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-1440.png) | [rescript-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-960.png) | 默认当前成片单选，九张库卡常驻且未选；两张分镜仍无来源标签，预览和页底完整；960 风格编辑与预览上下排。 |
| `rescript-adjust` | [rescript-adjust-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-adjust-1440.png) | [rescript-adjust-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-adjust-960.png) | 两张九张库卡完整；成片选择、调整说明、第一步解释和生成条保持一致，没有新增裁切。 |
| `rescript-other` | [rescript-other-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-other-1440.png) | [rescript-other-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/rescript-other-960.png) | 两张均仅另一条成片高亮，预览与生成条同步；库仍完整显示，长表和页底正常。 |
| `first` | [first-1440.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-1440.png) | [first-960.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-960.png) | 两张默认最近成片高亮，库卡常驻；无图分镜、画面占位、风格和生成条完整，960 只有表格内部横滚。 |

输出尺寸：`library` 为 1440×1667、960×2103；`first-none` 为 1440×2472、960×3030；其余五种均为 1440×2575、960×3149。

另补拍并逐张查看实际手机视口 390×900 的 [first-lib-390.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-lib-390.png)、[first-none-390.png](~/.photo-content-os/evidence/R283-direct-style-library/frontend/first-none-390.png)，完整输出分别为 390×4482、390×3991。卡片单列，已选样张与元数据上下排、四色和禁用项不再挤出；未选态的说明和禁用生成按钮完整，长表格保留内部横滚。两张为手机补查，不计入任务要求的 14 张。

`screenshot-manifest.json`、`visual-review.json` 记录全部 16 张的路由、实际视口、时间、滚动覆盖、输出尺寸、SHA-256 和本人逐张结论，均已核验最终文件与图库链接。截图采用减少动态效果模式，视频停在样张图；真实播放与进出屏行为另由浏览器测试验证，含实际播放时间前进。页面业务任务使用接口夹具，样张媒体为 S 段真实文件，不是本段新生成的成片。

## 5. R276 / R277 / R278 同步增量

- **R278 夹具**：19 个保留状态的 `/api/direct/styles` 均加 `library`，元数据形状、顺序和公共 URL 与后端一致。删除 `first-none-r278.json`，没有改其他原有任务字段。
- **R278 测试**：旧无成片断言改为 `first-none` 的默认现成模式、可点分段和无预选；旧生成、拆并镜、输入法、导入、风格样张流程和媒体测试保留。旧状态合同组合测试额外要求 R283 的「风格库」与 `DV-STYLE-LIB`。
- **共用 R278/R283 门禁**：状态集合为 19+3；新状态从 R283 夹具读取；分镜之外的库媒体请求读取真实库文件，绝不写入。`rescript-other` 只点最近成片组的最后一张，避免新增库卡后误点代码风。支持首次定向截图无旧 manifest，以及 `--widths=390`；重拍合并按状态与宽度替换，保留其他宽度。接入 R283 挂载测试、全合同块集合断言和上述真实只读 API 检查。
- **R276**：原 `composeLegacyContract` 从更新后的批准 `first-style` 合同自动合入库组文案和编号，无需手填文案。新增库媒体路由夹具分支，保证合同页面中新出现的九张卡实际读到正确媒体。没有改判据、允许列表或旧业务交互。
- **R277**：文件无需修改。仍通过同一合同组合函数读取更新后的设计合同；本门禁覆盖的详情/日志画面没有新增库卡块。使用指定状态源执行完整回归，42/42 通过。

## 6. 规则卡落实与边界

| 本轮触发的规则 | 落点与实测结果 |
| --- | --- |
| 同一事实共用实现与集合 | 两组共用 `card` 和同一 `base`；`testLibraryBrowser` 九次选择逐次检查仅一张高亮，36 个库色块，名字顺序与接口相同。 |
| 媒体/监听随组件释放 | 复用 `bindClips`，父视图持有清理函数；实际播放时间前进、出屏/减少动态效果暂停、失败回退、生成后旧视频暂停、离页暂停均通过。 |
| 状态以真实选择为准 | `testLibraryFormulas`、`testLibraryBrowser` 验证无成片不预选、警示文案、按钮锁与选后载荷；旧空状态和其实现分支已删除。 |
| 绑定在组件内，入口到目标页验证 | 库卡和输入事件只查当前组件；挂载 Studio 后经分段/卡片/生成/项目导航验证。单选立即更新界面，没有新增模型调用。 |
| 测试分层、失败不放过 | 新 Node 与静态测试先红；手机反例修复后绿；15 个前端 pytest、44+26+42 合同与点名检查通过，未跑全量 pytest。 |
| 服务边界与结论范围 | 只占用 8768 临时服务，一个无头浏览器；8769 原 PID 10819 保持。读取链路是真接口，建任务是拦截测试，不声称模型生成或人工通过。 |

没有需要新增的接口、文案或稿外元素。没有修改后端 `.py`、`schemas/`、`scripts/direct_video/style_library/`、`acceptance/`、`agents-results/` 或设计稿；覆盖这些保护目录、源文件与设计文件的 651 个文件前后哈希一致，见 `protected-after.json`。R276/R277/R278 人工记录仍为 PENDING，未修改验收物。

业务项目 HEAD 仍为 `130c931c8250368205165ef8c59d19b2796d55d4`。前端、夹具、测试和本报告未暂存；worktree 另有开工前的 S/B、设计、需求卡产物，以及其他线程的媒体允许列表改动，不归本段。完整状态见 `business-before.log`、`business-after.log`。Harness SSOT 本段零修改，收尾仓库有其他工作留下的 85 条状态记录，原样保留，见 `harness-after.log`。

本段临时目录与浏览器已关闭，8768 无监听；8769 未停止或重启。磁盘开工约 5.9 GiB、收尾约 4.4 GiB，观察期间未低于 3 GiB。未改全局配置、未创建 worktree、未暂存、提交、推送或改写历史。本报告是实施汇报，不是声明式 SSOT 包。写完停止。
