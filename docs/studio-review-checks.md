# Studio 派生预览与数字检查

失败类别 `studio-number-formula-drift`：精选、备选、时长、场景、项目、工作台、音乐或诊断数字与 R220 TASK 公式不一致。

- 范围：本地 Studio 的 R220 状态；不代替原片质量、平台联网或真人可用性验收。
- 常规入口：`.venv/bin/python -m pytest -q tests` 包含 Node 数字公式正反例；缺少 Node 时以 `studio-number-formula-runtime` 失败，不按跳过处理。
- 页面证据入口：设置 `PW_REQ` 为已安装 Playwright 的 package.json 路径，运行 `node scripts/capture_r220.mjs`。仅访问本机 Studio，拦截全部非本机请求；确认、未完成、运行中和音乐导入结果用真实媒体数据的内存夹具，不写真实决定、不启动模型任务。
- 负例：`tests/test_r220_number_formulas.mjs` 故意提供错误的精选数量，必须得到差异；Python 合同另覆盖 AI 质量降级不能被原始模型建议覆盖。
- 修复：修正对应数据合并或页面消费者，再运行 pytest 数字检查及完整截图矩阵；不修改预期数字来消除差异。
- 页面门禁同时记录 `number-formulas.json`、`design-inventory.json` 和带散列的截图清单。其结论必须检查每条 failure、异常和状态身份；采集成功不等于验收通过。
- `ONLY_STATES` 只允许在非受影响证据仍有效时补拍指定状态；它保留其余状态原有的散列及失败，不清零其他状态的错误。

原始素材仍通过 `runtime_paths.local_media_root()` 定位。Studio 的媒体路由只使用编号，单个有效 Range 返回 206，缺失编号和路径参数返回 404。`decisions.json` 使用原子写及期望版本；镜头证据不被决定覆盖。

设计稿目录及私人媒体不得复制或加入 Git。截图只留在本地任务 evidence 目录。真实 state 的副本与派生缓存准备不代表改变用户的原始决定。
