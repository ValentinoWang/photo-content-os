# R277 A2：版本来源字段

日期：2026-10-26。按 TASK.md 第 3.4 节和交接 4，只补 `versions[].baseVersion`，没有扩展前端或其他功能。保留总控已批准的 `tests/test_r276_direct_video.py`「16 个旧字段 + 5 个新字段」严格集合断言；开场与收尾 SHA-256 一致，未回退该改动。

## 实现

`baseVersion` 随版本记录写入 job.json，并在每个 versions[] 投影项中返回。首次写好版本是 null；revise/rewrite 的来源是发起操作时选中的 currentVersion；配音重渲的来源是重渲前选中的版本。现有任务互斥从接受操作保持到后台处理结束，currentVersion 在保存新版本之前保持不变，因此保存版本时可准确读取来源。`current` 只切换当前版，不修改任何版本的 baseVersion。

实际链路：

```json
[
  {"version": 1, "baseVersion": null},
  {"version": 2, "baseVersion": 1},
  {"version": 3, "baseVersion": 1}
]
```

其中 v3 是退回 v1 后再次修改所得；revise 和 rewrite 都已分别验证。退回 v2 后，上面三项保持原样。配音变长、使用 v1 原代码重渲出的 v3，同样记录 baseVersion=1。

R276 旧任务迁移出的第一版为 null。A2 前已经保存了 versions[]、但没有记录来源的条目，会补存 null，表示无法恢复的旧来源；不会猜成 version−1。OpenAPI 描述明确了这种历史未知值，新建的非首版使用实际来源。

| 本轮文件 | 改动 |
| --- | --- |
| `scripts/direct_video/revisions.py` | 保存版本时记录 baseVersion；补齐已有元数据缺失字段。 |
| `studio/direct_video.py` | versions[] 白名单追加 baseVersion。 |
| `studio/direct_revision_contract.py` | 增加 required 的 baseVersion，类型 integer 或 null，整数最小 1。 |
| `schemas/studio-openapi.json` | 用 build_openapi() 重新生成，保持 sort_keys/indent 格式。 |
| `tests/test_r277_revisions.py` | revise/rewrite 退回后再修改、落盘、退回不改来源、配音重渲、R276 迁移和旧来源未知的覆盖。 |
| `tests/test_r277_api.py` | 实际 HTTP：v2 来源 1，退回 v1 再 revise 得 v3 来源 1，之后退回不改历史来源。 |
| `evidence/2026-10-26/R277-shot-visual-revision/api-examples.json` | 重跑原 capture_api.py 更新；initial 的第一版为 null，revised 的第二版为 1，reverted 保留来源。 |
| 本汇报及 A2 文本证据 | 记录本次验证与边界。 |

本轮没有修改 generate.py、模型入口、捕获脚本或现有路由。没有写入并行线程负责的 `studio/static/`、`tests/test_r277_frontend.*`、`tests/test_r276_direct_frontend.*`、`scripts/direct_video/*frontend_gate.mjs`、`tests/fixtures/r277-revise/`。

## 验证

使用固定 `.venv/bin/python`；真实渲染测试沿用 TASK.md 交接 3 的 VIDEO_RENDER_PLAYWRIGHT_MODULE 和 VIDEO_RENDER_BROWSER，模型均使用假可执行文件，不真调 Opus。

```sh
.venv/bin/python -m pytest -q \
  tests/test_r276_direct_video.py tests/test_r276_direct_api.py \
  tests/test_r276_direct_c.py tests/test_r276_direct_media.py \
  tests/test_r277_revisions.py tests/test_r277_api.py tests/test_r277_boxes.py \
  tests/test_desktop_openapi_route_sync.py \
  --junitxml=evidence/2026-10-26/R277-shot-visual-revision/pytest-a2.xml
```

**174 passed，143.02 秒，无失败、无跳过**。总控修改的严格字段集合断言通过，真实浏览器测试也通过。日志及 JUnit：`pytest-a2.log`、`pytest-a2.xml`。

补充旧版本缺失字段测试是在主批次收集后加入，单独运行：

```sh
.venv/bin/python -m pytest -q \
  tests/test_r277_revisions.py::test_pre_field_version_metadata_keeps_unknown_base_null
```

**1 passed，5.50 秒**，见 `pytest-a2-migration.log`。覆盖历史来源未知时保留 null 且写回版本元数据。

另外执行：

- `.venv/bin/python evidence/2026-10-26/R277-shot-visual-revision/capture_api.py`：通过，临时端口实际 HTTP 响应含新字段；临时服务与合成状态清理完成，见 `capture-api-a2.log`。人工检查 api-examples.json 的 initial/revised/reverted，分别为 `(1,null)`、`(1,null)+(2,1)`、退回后保留同样两项。
- OpenAPI 由 `json.dumps(build_openapi(), ensure_ascii=False, sort_keys=True, indent=2)` 生成；同步回归已包含在主批次。
- `git diff --check`：通过。
- `.venv/bin/python scripts/check_repository_safety.py --base origin/main`：通过。
- 总控修改的 R276 Python 测试 SHA-256 校验：通过，见 `a2-protected-test.sha256`。

没有运行前端测试、全量 pytest 或前端门禁；本次没有观察到需要列出的前端测试失败，也没有代替并行线程进行前端验收。A 段旧汇报所列的字段集合冲突已由总控在本阶段开始前解决，本轮保留其严格断言。

## 状态与停止

本轮无未完成实现或待拍板事项；历史缺失来源只能保留 null，前端应按任务合同不展示未知来源的两版对比。已有 PENDING 人验记录未修改，不代签 H-01–H-03。

业务项目 git：本次后端及测试改动保留未提交，完整状态见 `a2-business-git-status.txt`；该状态同时可能含 A 段和并行 B 段的改动，不把它们归到 A2。未提交、未推送、未回退他人改动，未操作 8765/8766 或他人进程。

Harness SSOT git：本轮零修改；保留其他会话原有未提交内容，状态见 `a2-harness-git-status.txt`。本报告属于普通任务汇报，不创建 SSOT 包或 Obsidian 快照。

按 A2 约定停止。
