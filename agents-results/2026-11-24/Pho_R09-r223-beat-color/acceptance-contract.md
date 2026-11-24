# Acceptance Contract: 2026-11-24-Pho_R09-r223-beat-color

- Task ID: 2026-11-24-Pho_R09-r223-beat-color
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 2026-11-24 总控裁定按页面根令牌及同轨颜色区别复验，要求同一环境运行深浅两版，保留 R223 已签人工记录。
- Request source: acceptance/requests/2026-W48/2026-11-24-Pho_R09-r223-beat-color/request.json
- SSOT path: none
- SSOT node: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: music.beat-playback
- AC budget: 1
- Baseline identity: 6039932a362cd1fd503aa5c860ebb84692a1e4fd
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-24-Pho_R09-r223-beat-color

## User and scenario

在制作台音乐库播放一首有节拍图的音乐，观察当前拍点。

## Problem

R280 将制作台切换为浅色主题，R223 的交互检查仍固定期望深色主题的白色。

## Expected outcome

当前拍点与主题主文字同色，并且和同一轨的其他拍点区分。深浅两版使用同一份断言。

## Non-goals

产品或主题改版、R223 历史验收重签、真实音乐分析模型复验。

## Normal path

播放合成音频并定位到 4.18 秒，读取真实 Studio 页面中的拍点和根令牌。

## Exception paths

根令牌不能解析为颜色、同轨没有其他拍点、当前拍点颜色和其他任一拍点颜色相同，均使检查失败。

## Invariants

R223 既有人工结果保持有效。颜色对照和其余六项交互使用同一测试入口。

## Data impact

音频和 Studio 状态使用开发机临时目录，退出时回收。

## Permissions

执行方运行机器检查。新卡的人工作业为抽查，由任务委托人决定和签署。

## Performance and reliability

在同一开发机和同一浏览器运行两版，Studio 自动分配环回端口。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/unit | 两版均通过七项音乐交互，当前拍点颜色等于根令牌解析值且区别于同轨其他拍点；当前源码同时通过节拍图模块和 58 份设计清单检查。 | Browser and unit | Automatic | Yes |

## Human acceptance

新卡提供可选的视觉抽查，范围只涵盖当前拍点高亮。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 观察播放时的当前拍点高亮 | acceptance/human/2026-W48/2026-11-24-Pho_R09-r223-beat-color/checklist.md#h-01 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| scripts/verify_r223_interactions.mjs | dd83698afc9514b96386a30d3271b83922efc8b4933476ab0f006550ef621b7e | AC-01 |
| docs/tasks/r223-beat-color/run_browser_check.sh | b61101f9f89af2f43972325bb2a92d7811ad0c887eed1e09957fcd88dbb9a54d | AC-01 |
| tests/test_r223_beat_map.mjs | 1d6fa412d672a86dd0e2e5b6828236f67ac8817f25d3d32fb5e17bd391e6fa01 | AC-01 |
| scripts/check_r223_design.py | 7f2b48d69ff50d097e0b9fc4d2f2981b41ab291aa3f1a5ada5570a409180d705 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 两版对照和当前源码检查 | docs/tasks/r223-beat-color/run_browser_check.sh | Automatic | Yes |
| H-01 | 观察播放中的当前拍点 | acceptance/human/2026-W48/2026-11-24-Pho_R09-r223-beat-color/checklist.md#h-01 | Human | No |

## Exploratory testing

未安排补充探索。

## Production monitoring and rollback

仅更新检查和验收登记。开发机运行记录保留源码及命令结果。

## Risks and open decisions

浏览器使用合成音频与 R223 接口夹具。设计检查复核既有导出的 58 份清单。
