# Acceptance Contract: 2026-11-26-Pho_R18-concat-return

- Task ID: 2026-11-26-Pho_R18-concat-return
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 总控任务单 TASK-D 指定本需求及人工项 H-01、H-02 的操作和预期表现。
- Request source: acceptance/requests/2026-W48/2026-11-26-Pho_R18-concat-return/request.json
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.studio-concat-return
- AC budget: 1
- Baseline identity: 41016469e35e68cf1d255bf98c2b94d4604d26cd
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return

## User and scenario
制作台使用者在 Studio 项目页选 Concat 出第一版，在 Concat 里精修导出后，把成片拖回 Studio 检查。

## Problem
软件列表里选不到 Concat，回传时也不会读 Concat 工程，精修后的成片无法带着剪辑记录回到 Studio。

## Expected outcome
软件列表第一位是 Concat；回传时 Studio 读回 Concat 工程核对身份、字幕、时长和帧数，通过后出现候选；工程还开在 Concat 窗口里时提示先关闭再回传。

## Non-goals
不做断网可重试的本地提交队列，不做 Agent 租约，不改策划台页面，不启动真实 Concat 窗口。

## Normal path
读回工程的项目编号和版本与当前项目一致，时间线、字幕、时长和帧数与回传成片相符，候选记录生成。

## Exception paths
工程身份不符、读回被拒、窗口占用文件存在、动画编号无法还原、没有字幕记录时，一律给出检查失败，不生成候选。

## Invariants
其他剪辑软件的回传读回和软件列表文案、顺序保持原样。

## Data impact
只读回 Concat 工程，不改工程文件，不写用户素材。

## Permissions
任务委托人在本机 Studio 里独立核对。

## Performance and reliability
读回使用替身 Concat，不依赖真实应用和网络。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-02 | machine/unit | 读回成功生成候选记录，工程身份不符和读回被拒各自给出检查失败且读回被拒时提示先关闭工程 | Unit | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 在软件列表里看到并选中 Concat | acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/checklist.md#h-01 | 任务委托人 | No |
| H-02 | 用 Concat 精修导出后回传，候选出现且检查通过 | acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/checklist.md#h-02 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_concat_return.py | e7df4a1b80c6e6bd588d75e3259bdc0dbe86568bcc186e051b03c1c0f1976890 | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 运行 Concat 回传读回专项测试 | tests/test_concat_return.py | Automatic | Yes |
| H-01 | 核对软件列表 | acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/checklist.md#h-01 | Human | No |
| H-02 | 核对精修后回传 | acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/checklist.md#h-02 | Human | No |

## Exploratory testing
无。

## Production monitoring and rollback
需要回退时回退本次源码提交。

## Risks and open decisions
字幕位置不从 Concat 时间线读取，沿用 Concat 导出固定的字幕位置；真实 Concat 精修后回传留待任务委托人核对。
