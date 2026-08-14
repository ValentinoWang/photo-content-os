# 08.08 GitHub 单一事实源：作品审核能力管理

> 情形编号：`08.08`。  
> 适用情形：本机 Mac OpenClaw、远端服务器、Obsidian 任务队列或 GitHub CI 中，任何一处要新增、修改、迁移作品审核能力。

## 当前版本边界

这一版先收敛视频评分和判断算法本身：

```text
技术门禁
策略评分
VLM 语义融合
节奏同步评分
版本倾向
返修建议
人工判断边界
```

远端服务器也需要收敛，但不能被削弱成只有任务编排。当前边界是：远端发任务、看 Mac 结果、推进状态，同时保留 `【作品验收】` 和 `【数据复盘】` 这类策略评价层；它不在远端实现第二套视频文件评分算法。

算法路线图见：

```text
99_System_OpenClaw/docs/08_usage_guides_使用指南/08.09_视频评分判断算法收敛路线图.md
```

## 核心原则

作品审核能力只允许有一个事实源：

```text
GitHub repo
└── 99_System_OpenClaw/review_capabilities.registry.json
```

所有算法实现、评分口径、输出 schema、任务协议、文档、测试都必须围绕这份 registry 更新。不能因为本机能跑、远端也能跑，就各自维护一套判断口径。

## 当前权责边界

| 能力 | 单一实现位置 | 远端服务器能做什么 | 远端服务器不能做什么 |
| --- | --- | --- | --- |
| `local_output_review` | `99_System_OpenClaw/scripts/19_review_output_video.py` | 派发 `local_output_review` 任务，读取 Mac 回写结果 | 另写 ffprobe、抽帧、黑白场、压缩、构图评分 |
| `rhythm_sync_review` | `99_System_OpenClaw/scripts/19_review_output_video.py --rhythm-sync` | 读取 `rhythm_sync_result.yaml`，用于版本选择和返修建议 | 另写音画事件检测、卡点评分、版本排序 |
| `vlm_semantic_output_review` | `99_System_OpenClaw/scripts/19_review_output_video.py --run-vlm-review` | 读取 VLM 语义结果 | 用另一套提示词直接覆盖 Mac 侧语义结论 |
| `remote_review_orchestration` | `mac_openclaw_runner.py` + 队列脚本 | 创建任务、校验 task、推进状态、消费 result | 直接接触 Mac 私有素材并形成最终审核结论 |

## 变更流程

1. 先改 `99_System_OpenClaw/review_capabilities.registry.json`，尤其是对应能力的 `algorithm_contract`。
2. 再改对应实现、Runner 协议、文档或测试。
3. 本机运行：

```bash
python3 99_System_OpenClaw/scripts/36_validate_review_capability_registry.py
python3 -m unittest 99_System_OpenClaw/tests/test_review_capability_registry.py
python3 -m unittest 99_System_OpenClaw/tests/test_output_video_review.py
python3 -m unittest 99_System_OpenClaw/tests/test_mac_openclaw_runner.py
```

4. 通过 GitHub PR 提交，PR 使用 `.github/PULL_REQUEST_TEMPLATE/review-capability-change.md`。
5. 合并后，本机和远端都从 GitHub 拉取同一份 registry、脚本和文档。

## GitHub 仓库落地

当前本地工作区如果还没有 Git 远端，先由人确认仓库名和可见性，再做一次性初始化：

```bash
cd "/Users/vsiyo/Desktop/照片筛选"
git init
git add 99_System_OpenClaw .github 00_START_HERE_今天看这里.md
git commit -m "Add review capability SSOT registry"
git branch -M main
git remote add origin git@github.com:<owner>/<repo>.git
git push -u origin main
```

远端服务器只 clone / pull 这个 GitHub 仓库中的系统区；真实素材、剪映草稿、项目大文件仍按现有 Mac 本地和归档规则管理，不进 GitHub。

## 新增审核能力的判定

只有满足以下条件，才算新增能力：

```text
新的输入合同
新的输出 schema
新的执行责任主体
新的评分口径
新的状态推进规则
```

如果只是增加一个检测维度、profile 权重、提示词字段或报告段落，优先扩展现有能力，不新增 capability。

## 禁止的重复造轮子

```text
远端另写一个 output_review.py
远端另写一个 rhythm_sync_analyzer.py
远端直接抽 Mac 视频帧做主观评分
本机另开一个不写 registry 的 review 脚本
文档里新增审核术语但 registry 不登记
测试只测新脚本、不测 Runner 和 registry
```

## 合法的扩展方式

```text
在 local_output_review 下新增风险项
在 rhythm_sync_review 下新增事件类型或 profile
在 vlm_semantic_output_review 下新增 VLM 维度
在 remote_review_orchestration 下新增 task 字段或 allowed_actions
在 registry 中新增 proposed 能力并先写清楚 canonical_owner
```

## 交接口径

Mac 回写才是远端可继续使用的本地事实：

```text
metrics.json
output_review_result.yaml
_output_review.md
rhythm_sync/rhythm_sync_result.yaml
```

远端服务器的职责是把这些结果汇总到项目包、发布包、复盘或飞书/Obsidian 文档；不是重新解释原始素材、重新计算成片质量，或替人做最终发布判断。
