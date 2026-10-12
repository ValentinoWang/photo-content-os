# PS5 本地验证（交接 29）

这是普通证据，不是 SSOT 或人工验收结论。

- 剪点修复 `770ce59`：Kdenlive 保存 XML / openfilm 原生保存工程读回，无法证明原因的删除区间标 `manual`；已知重说仍为 `retake`。不改变速、重排、未批准素材或字幕检查规则。
- 界面修复 `d0d98b7`：self 依据回左栏、guide 时长与 chip 同行、重说删除线/降低不透明度、读不回说明的宽度/平衡折行、单候选视频与事实两列。
- `manual-targeted.log`：22 passed。`native-manual-green.log`：openfilm 0.1.5 原生 HTTP/磁盘、导出/拖回 2 passed（41.02 秒），含半秒新增手剪、75 帧与 retake/manual 混合回执；原重叠撤回/撤销/分割/版本冲突断言保留。`native-manual.log.gz` 与原始 SHA 保留首轮已知原因归类失败。
- `pytest-root.log`：553 passed、32 skipped、165 subtests passed（75.42 秒）。初轮仅 tests 子目录的 545 passed 也保留；最终验证使用仓库全量发现范围。
- `local-ci.log`：Local CI passed。`tsc-demo.log` / `tsc-media-u12b.log`：MC9 到位后两套 TypeScript 均退出 0；未启动或更改 Media dev。
- `mc9-contract-readback.json`：实际 native_readback 75 帧回执对齐 MC9 `30511ace` schema；为验证 schema 添加合成 wire 身份，不证明云端认证、上传和采用。
- `visual-progress.json`：42 张最终运行 PNG 逐张看至底部，30 夹具图 + 12 真实 API / 原生交互图。实际 viewport 1440×1000 / 430×900，完整页面非放大截图。单张超长 430 图另用 original 复核。
- Media `fe-shots/ps5-comparison.html` / `ps5-capture-manifest.json`：42 张本地最终 PNG、28 张复用 PS3 已审定稿对照。PNG 沿用仓库忽略策略仅本地保留；画廊、manifest 和逐图 SHA 提交。`gallery-links.json` 核验所有链接实际存在。
- `design-contract-result.json`：14 个本段影响状态在 1440 的原始严格 guard **仍为 RED**，621 文案、16 缺元素、8 稿外元素诊断。14 个根 ID 未被 collector 采集，另 2 个左栏依据按交接 28 删除；稿外元素为既有 guide-export / 回退说明。未改合同或扩允许表。
- `design-diagnostic-delta.json`：对同状态 PS4 诊断去重后，新增 18 项（12 项 guide 行内分隔符/数字，6 项按稿依据换回 suggestion-basis ID），均对应交接 29 的批准修正/动态值；仍不能把完整文案 guard 报绿。正文没有新增提示文案。
- `copy-source-final/`：HTML/JS/CSS 词法检查 2 文件、0 warning；初轮把 Python 错误码误当 UI 文案的诊断保留 `copy-source/`。Python 中错误码伴有中文 message，前端显示 message；未为此更改词表。
- 截图的 self-applied 430 在 t=0 无可见字幕，因此不把该图当字幕绘制通过证据；原生导出/字幕证明来自实际工程测试和其他原生预览图。多候选失败展开的旧说明重复保留，非本段新增。
- `cleanup.json`：截图 Studio 只起一次，浏览器由默认 withChromiumSlot.sh 串行管理，finally 已关闭；Photo 与 Node 服务 PID 消失。仅清理本线程依赖、合成资料、pytest/CI 临时目录，以及重复设计截图；未删除其他线程文件。

复现：在自己的隔离运行时目录安装 openfilm@0.1.5 / playwright-core@1.58.2（不下载浏览器）；`PS5_RUNTIME_ROOT=<自己的目录>` 执行 seed.py / preview-fixtures.py。Photo 固定 .venv、Studio 8765/--no-browser；浏览器脚本设 PS5_LAYOUT_VERIFY=1，使用 Media withChromiumSlot.sh 默认参数及现有 Chrome channel。没有新建软件 checkout 或开发库。
