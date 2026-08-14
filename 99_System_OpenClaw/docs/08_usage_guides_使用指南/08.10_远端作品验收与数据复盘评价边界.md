# 08.10 远端作品验收与数据复盘评价边界

> 情形编号：`08.10`。  
> 适用情形：讨论服务器端评价体系是否保留、如何与 Mac 本地视频评分协作。

## 结论

不能完全去掉服务器端评价体系。

正确边界是：

```text
Mac 本地 = 视频文件本体评分
远端服务器 = 作品要求验收、发布策略评价、发布后数据复盘
```

也就是说，远端不应另写一套 ffprobe、抽帧、音画同步或 VLM contact sheet 视频评分器；但远端必须保留对创作要求、平台机制、发布包、复盘数据和账号记忆的评价能力。

## 已知远端评价来源

当前协作文档记录的远端来源：

```text
/home/ubuntu/selfmedia-tools/openclaw-tag-router/openclaw_app/router/work_acceptance.py
/home/ubuntu/selfmedia-tools/tools/data_review/workflow.py
```

对应能力：

```text
【作品验收】
【数据复盘】
```

## 分工表

| 层级 | 主体 | 能评价什么 | 不能做什么 |
| --- | --- | --- | --- |
| 视频技术门禁 | Mac | 分辨率、黑场、白闪、音频、压缩、黑边、技术状态 | 判断账号策略和发布后表现 |
| 音画节奏 | Mac | BGM/步点/切点/动作峰/字幕变化对齐 | 替人自动改剪映时间线 |
| VLM 观感 | Mac | contact sheet 上的人物状态、构图、开头钩子、选题表达 | 替代完整逐帧观看 |
| 作品验收 | 远端 | 成稿/成片说明是否满足创作要求，证据缺口和修改建议 | 重算视频技术分、覆盖 Mac technical_status |
| 数据复盘 | 远端 | 发布后截图指标、趋势、内容和发布策略调整 | 用不可见数据编造结论 |
| Final 判断 | 人 | 是否发布、是否返修、封面/BGM/标题最终取舍 | 被任一自动分数替代 |

## 为什么不能删远端评价

如果把远端评价体系完全去掉，会损失三类能力：

```text
1. 创作要求对照：作品是否满足 brief、脚本、发布包要求。
2. 平台/账号策略：标题、正文、封面、话题、发布时间、账号记忆是否一致。
3. 发布后复盘：抖音/小红书后台数据截图中的指标解释和下一步动作。
```

这些不是 Mac 本地视频探测擅长的事。

## 正确的数据流

```text
Mac 生成 metrics/result/report
↓
远端读取 Mac 证据摘要
↓
远端做作品验收 / 发布策略评价 / 数据复盘
↓
人结合两边结论做 Final 判断
```

远端评价必须引用明确证据：

```text
作品正文
创作要求
最近对话上下文
Mac 回写 metrics / result / report
发布后数据截图
```

没有证据时输出“不确定”，不能脑补。

## Registry 口径

本能力登记为：

```text
remote_work_acceptance_review
```

它的角色是：

```text
remote_strategy_evaluation
```

不是：

```text
scoring_core
semantic_judgement_fusion
```

这表示它是远端策略评价层，不是视频文件本体评分核心。
