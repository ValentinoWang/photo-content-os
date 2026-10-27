# Acceptance Contract: 2026-10-27-R310-photo-devbox

- Task ID: 2026-10-27-R310-photo-devbox
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户2026-10-27原话「照它给 R310 准备交付验收卡」；总控 TASK.md 要求原样沿用已登记两项并用非阻塞卡，不追称实现前已锁合同，不代表人工PASS
- Request source: acceptance/requests/2026-W44/2026-10-27-R310-photo-devbox/request.json; docs/tasks/R310-photo-devbox/TASK.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: photo.devbox-execution, photo.devbox-transfer
- AC budget: 2
- Baseline identity: 40cf307c41490b8c4dccf586185e9f37eca0eb14，见baseline.json
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W44/2026-10-27-R310-photo-devbox

## User and scenario

任务委托人让总控运行 photo-content-os 的测试、门禁和渲染；本机运行 AI 和 Git，执行命令交给项目专用开发机。

## Problem

本机重活占用资源；开发机执行要明确源码身份、同步边界与在线状态，不能把缺失状态当成离线。

## Expected outcome

浅色专项可经项目远端入口通过；默认代码同步清单排除私人素材、证据和凭据；禁止向开发机发送 AI 命令和凭据。人工原两项原样保留。

## Non-goals

不改产品、测试、开发工具实现或需求标准；不修全量既有失败；不重装环境、不传真实数据、不起常驻服务、不推送 Git 远端。此次为既有实现补齐交付物，不追称已有实现前测试锁定。

## Normal path

Given 源码为冻结提交且开发机在线；When 经 rbox 运行浅色专项；Then 远端返回九项通过；When 列出默认同步清单；Then 只包含允许的仓库文件。

## Exception paths

在线判定为本机或不可读时在同步前停止，并区分原因；AI 命令与凭据拒绝发送。网络和依赖不可用须报告失败，不以本机测试替代。

## Invariants

不修改原始媒体、作品和真实剪映草稿；不传 AI 凭据；人工作业仅由任务委托人签署。开发机素材根独立于软件根，当前指向空目录。

## Data impact

本轮只新增验收证据和生成投影、补同步范围映射；旧卡和需求卡不变。默认同步不含 agents-results。已获准的真实 Studio 数据是总控既有单独操作，不属于默认代码同步，也不是本轮操作。

## Permissions

执行者可准备验收物和运行获准检查；任务委托人独立验收，执行者不代签。

## Performance and reliability

全量、门禁和渲染通过 heavy 队列串行；本轮不运行这些重任务。浅色专项通过前台远端单项命令运行，不新增性能阈值。

## Acceptance criteria

| ID | Class | Source requirement refs | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | H-01 | machine/integration-contract | 冻结源码的浅色专项经项目开发机入口执行并返回九项通过 | Integration | Automatic | Yes |
| AC-02 | behavior | H-02 | machine/unit | 默认清单排除私人媒体、证据和凭据，拒绝AI执行与凭据传输，在线判定区分不可读与离线 | Unit | Automatic | Yes |

## Human acceptance

两项由需求卡直接沿用，用户真实活动监视器观察与对话交接体验保留为非阻塞抽查；机器测试不冒充真人签署。

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 测试交接与本机负荷观察 | acceptance/human/2026-W44/2026-10-27-R310-photo-devbox/checklist.md#h-01 | 任务委托人 | No |
| H-02 | 同步文件清单可理解且无私人文件 | acceptance/human/2026-W44/2026-10-27-R310-photo-devbox/checklist.md#h-02 | 任务委托人 | No |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| scripts/devbox/test_push_rules.sh | f2eb65355390d3811725c5b1093ebce36679cbb9cf3641e66c23bf53141bdc57 | AC-02 |
| scripts/devbox/test_ai_guard.sh | 7d8000cd154bc48aab6e3e3a047151f1ffed8e693110e9a021e57148dd010161 | AC-02 |
| scripts/devbox/test_where.sh | d74e04b68d0da6af9df274d93b77d9cb7306b475f4c0d514da709216d2895720 | AC-02 |
| tests/test_r280_light.py | e98f6199f0f0a897e3a94fa53fa57d5b70b369225e2803e67259e1e1ffa585ef | AC-01 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 远端浅色专项 | tests/test_r280_light.py | Automatic | Yes |
| AC-02 | 三份既有自测 | scripts/devbox/test_push_rules.sh; scripts/devbox/test_ai_guard.sh; scripts/devbox/test_where.sh | Automatic | Yes |
| H-01 | 原样人工观察 | acceptance/human/2026-W44/2026-10-27-R310-photo-devbox/checklist.md#h-01 | Human | No |
| H-02 | 原样清单检查 | acceptance/human/2026-W44/2026-10-27-R310-photo-devbox/checklist.md#h-02 | Human | No |

## Exploratory testing

本轮不补造浏览器或渲染证据；已有全量与门禁结果只作带来源的历史背景，见 evidence 的限制说明。

## Production monitoring and rollback

不部署，不修改开发机数据和环境；异常保留失败并交总控处理，不自行回滚别人提交。

## Risks and open decisions

人工未签署。总控全量报告1204通过、12失败、36跳过，不能宣称全绿：9项本机同样红，3项开发机环境差异。开发机中文字体与Arial使用链接替身，特定复制命令使用cp替身，melt版本不同；R277字体度量不一致仍留本机，不由本卡证明等价渲染。R278和R276既有门禁PASS并非本轮重跑。此根是验收证据包，无SSOT声明，不创建Obsidian快照。
