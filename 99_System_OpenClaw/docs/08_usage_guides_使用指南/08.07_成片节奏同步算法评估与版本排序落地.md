# 08.07 成片节奏同步算法评估与版本排序落地

> 情形编号：`08.07`。  
> 适用情形：同一条内容已经从剪映导出多个 V1 / V2 / Final 候选版本，需要判断哪一版更适合发布，尤其是 BGM 卡点、步点、动作峰、切点、字幕和开头效果是否对齐。

## 这份指南解决什么

当前成片复核已经有本地入口：

```text
99_System_OpenClaw/scripts/19_review_output_video.py
```

它可以做：

```text
ffprobe 元数据
抽帧 contact sheet
场景变化图
黑场 / 白闪 / 边框 / 压缩 / 音量 / 静音 / 粗略 BGM 能量
多个版本的技术排序
```

但它现在主要回答：

```text
这个文件有没有技术问题？
哪个版本更少风险？
```

节奏同步算法要回答的是另一层问题：

```text
哪些画面事件应该卡点？
它们和哪些音乐事件对齐？
对齐是稳定的，还是偶然的？
按这个作品类型，哪个版本更值得发布或继续精修？
```

所以本指南不是替代 `08.05` 的成片复核，而是在成片复核后增加一个更细的“节奏 / 卡点 / 版本排序”评估层。

本能力已经登记在：

```text
99_System_OpenClaw/review_capabilities.registry.json
```

它的 canonical owner 是 `mac_openclaw`。远端服务器可以消费 `rhythm_sync_result.yaml` 做汇总和任务推进，但不能另写一套 rhythm analyzer。

## 推荐总架构

算法模块建议命名为：

```text
RhythmSyncAnalyzer(video, profile)
```

处理链路：

```text
输入成片版本
↓
AudioEventDetector 音频事件检测
↓
VisualEventDetector 画面事件检测
↓
StepMotionDetector 步点 / 身体起伏检测
↓
EventAligner 音画事件对齐
↓
ProfileWeightedScorer 按作品类型加权评分
↓
ReviewReportGenerator 输出版本排序和人工审看点
```

输入：

```text
video_path
profile 作品类型
optional_intent 人工意图
```

输出：

```text
总评分
步点同步评分
切点同步评分
动作同步评分
字幕同步评分
开头效果评分
可修复性评分
版本排序
问题时间点
人工审看点
```

## 和现有项目目录的衔接

成片仍然放：

```text
项目根/91_Output/V1/
项目根/91_Output/V2/
项目根/91_Output/Final/
```

节奏同步分析产物建议放：

```text
项目根/_ai_analysis/output_review/rhythm_sync/
```

建议结构：

```text
_ai_analysis/output_review/rhythm_sync/
├── rhythm_sync_metrics.json
├── rhythm_sync_result.yaml
├── rhythm_sync_report.md
├── version_a/
│   ├── audio_events.json
│   ├── visual_events.json
│   ├── matches.json
│   └── review_frames/
└── version_b/
    ├── audio_events.json
    ├── visual_events.json
    ├── matches.json
    └── review_frames/
```

原则：

```text
metrics.json = 机器可读
result.yaml = 给队列 / 上游任务读的结论
report.md = 给人读的解释和审看点
review_frames/ = 问题时间点截图证据
```

## V1：先落地到现有成片复核

第一步不要新开一条复杂系统。直接扩展 `19_review_output_video.py`，新增可选参数：

```bash
python3 99_System_OpenClaw/scripts/19_review_output_video.py \
  --task-id rhythm_sync_review \
  --project-id 20260625_第一视角体验清华毕业典礼 \
  --idea-id tsinghua_graduation_pov \
  --video "上下分屏=/path/to/a.mp4" \
  --compare-video "单人会场=/path/to/b.mp4" \
  --output-root "/path/to/project/_ai_analysis/output_review" \
  --report-output "/path/to/project/_ai_analysis/output_review/_output_review.md" \
  --metrics-output "/path/to/project/_ai_analysis/output_review/metrics.json" \
  --result-output "/path/to/project/_ai_analysis/output_review/result.yaml" \
  --rhythm-sync \
  --profile split_screen_comparison
```

如果暂时不改 CLI，也可以先做独立脚本：

```text
99_System_OpenClaw/scripts/36_analyze_rhythm_sync.py
```

但输出路径和 JSON / YAML / Markdown 口径要跟 `19_review_output_video.py` 保持一致，避免后续队列和文档层分叉。

## 音频事件线

音频不要只检测能量峰。至少拆成四类：

```text
energy_peak：音量 / 能量峰
onset_peak：瞬时起音点，如鼓点、拍手、音效
beat_grid：稳定节拍网格
accent_peak：强拍 / 重拍 / 情绪峰
```

V1 可用轻量实现：

```text
ffmpeg 抽 mono wav
↓
音量归一化
↓
短窗口 RMS 能量
↓
能量上升沿找峰
↓
粗估 BPM
↓
输出 suggested_cut_points
```

V2 再升级：

```text
RMS + spectral flux + onset strength
beat tracking
onset / beat / accent 合并去重
每个事件带 strength 和 confidence
```

音频事件结构：

```json
{
  "time": 1.6,
  "type": "accent_peak",
  "strength": 0.82,
  "confidence": 0.76,
  "source": "rms_flux_onset"
}
```

## 画面事件线

画面侧至少检测六类事件：

```text
scene_cut：硬切 / 大场景变化
global_motion_peak：整帧运动峰
step_motion_peak_proxy：ROI 步点 / 身体起伏代理
pose_keyframe：人体关键动作，V3 再做
text_overlay_change：字幕 / 标题出现或变化
intro_effect：开头虚焦、过曝、闪白、模糊转清晰
```

V1 先做三项：

```text
scene_cut：复用 ffmpeg scene select
global_motion_peak：低分辨率帧差 / 光流强度
step_motion_peak_proxy：下中部 ROI 光流峰值
```

画面事件结构：

```json
{
  "time": 2.14,
  "type": "step_motion_peak_proxy",
  "strength": 0.71,
  "confidence": 0.62,
  "source": "lower_center_roi_optical_flow",
  "notes": "下中部 ROI 出现周期性运动峰"
}
```

## 步点检测分阶段

V1 使用 ROI 光流代理：

```text
取画面下中部 ROI
↓
计算相邻帧运动强度
↓
平滑曲线
↓
找局部峰
↓
作为 step_motion_peak_proxy
```

适合：

```text
单人舞台走位
跑步第一视角
人物下半身或身体起伏明显
轻量批量比较多个版本
```

风险：

```text
手持横移、推拉、变焦会误判
多人画面会混在一起
主体不在下中部时失效
上下分屏会把两个画面混算
```

V2 增加相机运动补偿：

```text
估计全局运动
↓
估计 ROI 运动
↓
ROI motion - camera motion
↓
得到相对人体运动
```

V3 再上人体姿态：

```text
人体框 tracking
脚踝高度 / 速度
膝盖压缩
髋部上下起伏
左右脚交替
foot contact 事件
```

不要在 V1 就把工程复杂度推到人体姿态。先让事件线、匹配和报告稳定。

## 音画事件对齐

不要只用：

```text
abs(visual_time - audio_time) <= 0.18s
```

V1 可以保留阈值命中，但必须同时记录 signed delta：

```text
delta = visual_time - audio_time
```

推荐连续得分：

```text
alignment_score = exp(-(delta ** 2) / (2 * sigma ** 2))
```

不同事件使用不同容忍窗口：

| 事件类型 | 容忍窗口 |
| --- | ---: |
| scene_cut | 0.10s - 0.14s |
| intro flash / transition | 0.10s - 0.16s |
| step_motion_peak_proxy | 0.14s - 0.22s |
| global_motion_peak | 0.12s - 0.18s |
| text_overlay_change | 0.15s - 0.25s |
| intro_effect | 0.20s - 0.35s |

匹配要做一对一，避免一个音乐峰值匹配多个画面事件导致虚高：

```text
visual_events × audio_events
↓
生成 delta 小于阈值的候选边
↓
按 abs(delta) 从小到大排序
↓
每个 visual / audio 只允许匹配一次
↓
输出 matches
```

## 指标体系

不要只看 `matched / total`。至少输出这些指标：

```text
step_precision：检测到的步点里，有多少贴近音乐事件
beat_coverage：重要音乐事件里，有多少被画面响应
phase_consistency：匹配事件是否稳定提前 / 滞后
periodicity_score：步点是否有节奏周期，而不是随机噪声
weighted_sync：按画面事件强度和音频事件强度加权后的同步分
fixability_score：是否容易通过整体平移、变速或微调切点修复
```

核心诊断字段：

```json
{
  "matched_step_events": 17,
  "detected_step_events": 29,
  "matched_scene_cuts": 3,
  "detected_scene_cuts": 6,
  "median_delta_sec": 0.04,
  "mad_delta_sec": 0.07,
  "fixability": "medium"
}
```

解释规则：

```text
median_delta 稳定为 +0.08s，mad_delta 很小
= 整体晚了 80ms，容易统一平移或轻微变速修复

median_delta 接近 0，但 mad_delta 很大
= 有些早有些晚，节奏不稳定，修复成本高
```

## 作品类型 profile

同一个版本在不同作品目标下排序可能不同。必须按 profile 加权。

### single_person_stage_walk

适合单人舞台、走路、毕业袍走位：

```json
{
  "step_sync": 0.4,
  "motion_sync": 0.25,
  "cut_sync": 0.15,
  "intro_effect": 0.1,
  "subject_presence": 0.1
}
```

### pov_running

适合第一视角跑步：

```json
{
  "step_sync": 0.45,
  "global_motion_rhythm": 0.3,
  "cut_sync": 0.05,
  "intro_effect": 0.1,
  "stability": 0.1
}
```

### split_screen_comparison

适合上下分屏 / 翻拍对照：

```json
{
  "structural_match": 0.3,
  "action_node_sync": 0.25,
  "cut_sync": 0.15,
  "text_overlay_sync": 0.15,
  "step_sync": 0.1,
  "intro_effect": 0.05
}
```

这类视频不能只看步点。它的核心是：

```text
上下画面关系是否清楚
动作节点是否对应
站位变化是否对应
翻拍结构是否成立
```

### sports_highlight

适合运动高燃：

```json
{
  "action_burst_sync": 0.35,
  "speed_change_sync": 0.25,
  "cut_sync": 0.2,
  "impact_sync": 0.15,
  "intro_effect": 0.05
}
```

### talking_head

适合口播 / 知识类：

```json
{
  "semantic_pause_sync": 0.3,
  "text_overlay_sync": 0.25,
  "expression_change": 0.15,
  "cut_sync": 0.15,
  "intro_hook": 0.15
}
```

口播不能用步点评估。应该看字幕、语义停顿、表情变化、重音词和章节转折。

### general_bgm_edit

无法判断作品类型时使用：

```json
{
  "cut_sync": 0.25,
  "motion_sync": 0.25,
  "intro_effect": 0.15,
  "text_overlay_sync": 0.15,
  "beat_coverage": 0.1,
  "phase_consistency": 0.1
}
```

## 版本排序公式

最终分不要直接等于 `step_sync`。

推荐：

```text
final_score =
  w_step * step_sync
+ w_cut * cut_sync
+ w_motion * motion_sync
+ w_intro * intro_effect
+ w_text * text_overlay_sync
+ w_subject * subject_presence
+ w_consistency * phase_consistency
+ w_fixability * fixability_score
- penalties
```

penalties：

```text
开头 3 秒没有主体
开头虚焦 / 过曝持续过长
关键切点错拍
大量动作峰没有音乐响应
字幕遮挡主体
横屏直接投抖音竖屏导致有效画面过小
黑场 / 静音 / 爆音 / 压缩严重
```

注意：抖音发布判断还要叠加运营指标：

```text
首帧识别
前 3 秒钩子
主体关系
平台画幅
封面可读性
标题和评论区话题
```

节奏同步只负责“音画结构是否卡得上”，不单独决定是否发布。

## 当前清华毕业典礼项目如何解释

项目路径示例：

```text
/Users/vsiyo/Desktop/照片筛选/01_Project_Workspace/2026年清华毕业典礼内容创作/20260625_第一视角体验清华毕业典礼
```

若用 `single_person_stage_walk` 评估：

```text
单人会场舞台版 / 加长版的 step_sync 权重高
步点、身体起伏、走位和 BGM 对齐更重要
```

若用 `split_screen_comparison` 评估：

```text
上下分屏签到墙对照版不应该因为 step_sync 低就直接判差
它更重视上下对照结构、动作节点、主体关系和首帧信息
```

所以报告要写成：

```text
在 step_motion_peak_proxy + 音频峰贴近率这个技术指标下，某版本的步点同步更好。
但在抖音发布 profile 下，还要叠加竖屏适配、开头钩子、主体识别和封面可读性。
```

这能避免把“算法分最高”误写成“发布一定最好”。

## 报告格式

Markdown 报告必须包含：

```text
1. 本次 profile
2. 版本总排名
3. 各维度评分
4. 关键匹配事件
5. 关键错拍事件
6. 可修复性建议
7. 人工审看点
8. 发布判断边界
```

示例：

```markdown
# 成片节奏同步复核

- profile: split_screen_comparison
- preferred_version_by_rhythm: 上下分屏签到墙对照版_V1a
- human_decision_required: true

## 版本排名

| 排名 | 版本 | final_score | step_sync | cut_sync | intro | fixability |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | 上下分屏签到墙对照版_V1a | 0.76 | 0.31 | 0.68 | 0.82 | medium |
| 2 | 单人会场舞台版_V1a | 0.71 | 0.62 | 0.40 | 0.54 | high |

## 人工审看点

| 时间 | 类型 | 建议 |
| ---: | --- | --- |
| 0.5s | intro_hook | 看首帧人物和清华背景是否足够明确 |
| 6.8s | cut_sync | 看切点是否贴住音乐重拍 |
| 26.6s | black_tail | 如直接发布，裁掉结尾黑场 |
```

## JSON 合同草案

```json
{
  "schema_version": "rhythm_sync_review.v1",
  "profile": "split_screen_comparison",
  "preferred_version": "上下分屏签到墙对照版_V1a",
  "human_decision_required": true,
  "versions": [
    {
      "version_name": "上下分屏签到墙对照版_V1a",
      "path": "/abs/path/video.mp4",
      "scores": {
        "final_score": 0.76,
        "step_sync": 0.31,
        "cut_sync": 0.68,
        "motion_sync": 0.55,
        "intro_effect": 0.82,
        "text_overlay_sync": 0.5,
        "phase_consistency": 0.64,
        "fixability_score": 0.58
      },
      "diagnostics": {
        "detected_audio_events": 34,
        "detected_visual_events": 29,
        "matched_events": 16,
        "median_delta_sec": 0.04,
        "mad_delta_sec": 0.07
      },
      "review_points": [
        {
          "time": 0.5,
          "type": "intro_hook",
          "severity": "info",
          "reason": "首帧有人物、学位服和清华背景，适合人工确认封面。"
        }
      ]
    }
  ]
}
```

## 开发路线

### V1.0：可用优先

目标：在现有成片复核里跑出可解释的节奏报告。

```text
复用 19_review_output_video.py 的 ffprobe / ffmpeg / 抽帧 / 音频 wav
新增 audio_events.json
新增 visual_events.json
新增 matches.json
新增 rhythm_sync_report.md
支持 general_bgm_edit / single_person_stage_walk / split_screen_comparison 三个 profile
输出 preferred_version_by_rhythm
```

验收：

```text
同一目录下多个 mp4 可以批量比较
报告能说明为什么某版本在某个 profile 下更好
不会把节奏分数直接等同于发布结论
```

### V1.1：减少误判

目标：让分数从“有点像”变成“可用于剪辑决策”。

```text
一对一事件匹配
signed delta / median_delta / mad_delta
不同事件类型不同 tolerance
增加 fixability_score
输出可修复建议：整体平移、裁黑场、切点前后微调、局部变速
```

### V2.0：音频事件升级

目标：从能量峰升级到更可靠的节奏结构。

```text
onset / beat / accent 分离
节拍网格置信度
强拍优先级
音乐段落边界
```

可以引入第三方音频库，但要保持 ffmpeg fallback。

### V2.1：视觉事件升级

目标：更好地区分镜头运动和人物动作。

```text
全局运动补偿
上下分屏 ROI 分区
字幕 / 标题变化检测
开头虚焦 / 过曝持续时间检测
主体区域运动强度
```

### V3.0：人体姿态和自动改片建议

目标：从“评估版本”进入“指导改片”。

```text
人体关键点
foot contact 步点
左右脚交替
速度曲线
动态规划生成切点 / 变速建议
输出剪映人工操作清单
```

## 和人工审片的分工

算法负责：

```text
找出事件线
量化音画对齐
比较版本
指出问题时间点
判断是否容易修
```

人工负责：

```text
确认是否符合账号人设
确认第一眼是否有钩子
确认封面和标题
确认人物状态是否自然
确认是否能发 Final
```

最终口径：

```text
节奏同步评估最多推进到 output_reviewed / rhythm_reviewed。
是否 Final、是否发布，仍然由人确认。
```

## 下一步

```text
只有轻量反抄和 BGM 卡点需求
-> 看 08.06

已经有成片，需要基础技术复核
-> 看 08.05

需要比较多个导出版本哪一版更卡、更值得发
-> 用本指南扩展 output_review

需要自动生成剪映导入包
-> 看 08.04 和 08.05
```
