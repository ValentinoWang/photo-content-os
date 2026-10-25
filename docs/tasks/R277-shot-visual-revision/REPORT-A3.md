# R277 A3：元数据操作保留成片更新时间

日期：2026-10-26。已重读 TASK.md 末尾交接 5，本轮只做 A3-1。未修改并行 cdx 2 负责的前端、前端测试、frontend_gate 或 tests/fixtures。

## 修复

R276 旧任务第一次读取时补版本元数据，原先会调用统一 save()，把 `updatedAt` 改成读文件的时间。look 的后台登记、状态与结果写入、收尾，以及 sample/取消样例，也会刷新这个时间。这些动作不改变成片，却会放大页头按 updatedAt 计算的耗时。

本轮修改：

| 文件 | 改动 |
| --- | --- |
| `scripts/direct_video/generate.py` | save() 增加内部参数 touch_updated_at（默认 true）；读取迁移传 false。start() 把这个选择用于后台任务登记、异常落盘和收尾；只有看图命令传 false。恢复仅看图中断的任务也保留时间，真正生成/合成中断仍沿用原行为。 |
| `scripts/direct_video/revisions.py` | look 的接受、running、补渲帧/boxes、完成/失败结果和 sample/取消样例均用保留时间的写入。 |
| `tests/test_r277_revisions.py` | 补齐旧任务迁移、旧 baseVersion 元数据补齐、看图中断恢复的时间断言；新增看图成功/失败/补帧后的样例操作测试，覆盖命令返回、后台运行与最终落盘；新增 revise/rewrite/current 仍更新时间的反向保护。 |
| `tests/test_r277_api.py` | 实际 HTTP 验证 look 接受及完成、PUT sample、DELETE sample 的 updatedAt 保持一致。 |
| 本汇报与 A3 文本证据 | 保存修复前后测试结果和 git 状态。 |

revise、rewrite、current 的写入仍默认刷新 updatedAt；未改它们的时间语义。看图和样例操作继续落盘、更新自身状态，成片 output 内容保持不变。未新增接口、投影字段或错误码，OpenAPI 无需修改。

## 验证

先加断言再改实现，修复前运行：

```sh
.venv/bin/python -m pytest -q \
  tests/test_r277_revisions.py::test_legacy_job_upgrade_retains_original_files \
  tests/test_r277_revisions.py::test_metadata_actions_preserve_output_timestamp
```

**4 failed，13.87 秒**，全部在 updatedAt 不应变化的断言处复现。三个看图参数分别为 success、failed、rebuild-frames；日志 `evidence/2026-10-26/R277-shot-visual-revision/pytest-a3-red.log`。

修复后运行用户指定范围：

```sh
.venv/bin/python -m pytest -q \
  tests/test_r276_direct_video.py tests/test_r276_direct_api.py \
  tests/test_r276_direct_c.py tests/test_r276_direct_media.py \
  tests/test_r277_revisions.py tests/test_r277_api.py tests/test_r277_boxes.py \
  tests/test_desktop_openapi_route_sync.py \
  --junitxml=evidence/2026-10-26/R277-shot-visual-revision/pytest-a3.xml
```

**181 passed，268.29 秒，无失败、无跳过**。R276/R277 后端及 OpenAPI 同步全部通过。日志和 JUnit：`evidence/2026-10-26/R277-shot-visual-revision/pytest-a3.log`、`pytest-a3.xml`。

沿用任务单规定的固定 `.venv` 和 VIDEO_RENDER_PLAYWRIGHT_MODULE / VIDEO_RENDER_BROWSER；真实浏览器测试使用该环境，模型测试使用假可执行文件，没有真实调用 Opus。HTTP 测试在临时端口使用合成状态，没有操作 8765/8766。

另外：

- `git diff --check` 通过。
- `.venv/bin/python scripts/check_repository_safety.py --base origin/main` 通过。
- 总控此前修改的 `tests/test_r276_direct_video.py` 开场/收尾 SHA-256 一致，严格 16+5 字段集合断言保留；证据 `a3-protected-test.sha256`。

未运行前端测试或两份前端门禁，也未运行全量 pytest。本轮没有观察到需要列出的并行前端测试失败；没有修复或验收 cdx 2 的前端工作。

## 状态

A3-1 无剩余实现或待拍板事项。没有提交、推送、回退他人改动、改主目录/R276 worktree 或停止他人进程。未改人验记录，未代签 H-01–H-03；本报告是普通任务汇报，不创建 SSOT 包或 Obsidian 快照。

业务项目 git：本轮只写上述两个后端文件、两个后端测试文件、REPORT-A3 和 A3 文本证据；工作区另含 A/A2 与并行前端的改动，完整状态见 `a3-business-git-status.txt`，不将他人改动归为本轮。

Harness SSOT git：本轮零修改；其他会话已有的未提交内容保留，完整状态见 `a3-harness-git-status.txt`。

按 A3 约定停止。
