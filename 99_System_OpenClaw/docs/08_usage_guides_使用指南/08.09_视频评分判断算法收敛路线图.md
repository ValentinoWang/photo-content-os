# 08.09 视频评分判断算法收敛路线图

> 情形编号：`08.09`。  
> 适用情形：要讨论、修改、校准或复盘“哪一版视频更好、为什么更好、该不该发布”的算法本身。

## 当前算法版本

```text
video_scoring_judgement.v3
creative_strategy_weights.v3
```

V3 的核心变化：降低平台画幅的直接占比，提高开头钩子和构图代理的占比，让算法更贴近短视频发布时“第一眼是否抓人、画面是否成立”的判断。

## 这一版收敛什么

这一版只收敛视频评分和判断算法本身：

```text
输入视频与项目上下文
↓
技术门禁
↓
策略评分
↓
VLM 语义融合
↓
节奏同步评分
↓
版本倾向、返修建议、人工审看点
```

远端服务器也要被纳入视野。本路线图只收敛视频文件本体的评分算法；远端的 `【作品验收】` 和 `【数据复盘】` 仍作为策略评价层保留，详见 `08.10_远端作品验收与数据复盘评价边界.md`。远端不能成为第二套视频评分器，但也不应被削弱成只有任务编排。

## 单一事实源

算法事实源登记在：

```text
99_System_OpenClaw/review_capabilities.registry.json
```

算法实现入口是：

```text
99_System_OpenClaw/scripts/19_review_output_video.py
```

校验入口是：

```bash
python3 99_System_OpenClaw/scripts/36_validate_review_capability_registry.py
```

## 算法层 1：技术门禁

技术门禁回答：

```text
这个视频有没有硬伤？
```

核心函数：

```text
risk_flags_for
technical_status_for
```

主要输入：

```text
ffprobe 元数据
Pillow 抽帧统计
ffmpeg loudness / silence / volume
黑场、白闪、黑边、压缩、分辨率、时长、音频风险
```

主要输出：

```text
risk_flags
technical_status = pass / warning / fail / unknown
```

原则：

```text
fail 只处理硬性不可用风险。
warning 不等于不能发，只表示需要人工看。
技术门禁不评价“内容好不好看”。
```

## 算法层 2：策略评分

策略评分回答：

```text
在当前平台和选题目标下，哪个版本更值得继续精修或优先看？
```

核心函数：

```text
creative_review_for_version
platform_format_score
composition_score
hook_score
rhythm_score
topic_strategy_score
```

当前权重：`creative_strategy_weights.v3`

| 维度 | 权重 | 当前依据 |
| --- | ---: | --- |
| rhythm | 0.35 | 外部 BGM/步点/切点审阅报告 |
| platform_format | 0.10 | 目标平台 + 画幅 |
| opening_hook | 0.23 | 前 3 秒事件和开头效果代理 |
| composition | 0.20 | 抽帧技术构图代理 |
| topic_strategy | 0.12 | 文件名和项目目标字面标签 |

缺失维度不硬填分；有缺失或人物状态未自动判断时，confidence 降为 `low`。

V3 调整意图：

```text
platform_format 从 0.20 降到 0.10：横竖屏是发布适配问题，不应过度压过内容观感。
opening_hook 从 0.18 升到 0.23：前 3 秒钩子对抖音/小红书更关键。
composition 从 0.15 升到 0.20：毕业典礼、人物状态、分屏对照类内容更依赖第一眼画面成立。
rhythm 保持 0.35：卡点和动作节奏仍是版本排序主轴。
topic_strategy 保持 0.12：文件名/项目目标只做弱策略信号。
```

## 算法层 3：VLM 语义融合

VLM 语义融合回答：

```text
contact sheet 里能看到的人物状态、构图美感、开头钩子和选题表达是否支持发布？
```

核心函数：

```text
run_vlm_semantic_review
apply_vlm_semantic_review
```

融合规则：

```text
creative_score_after_vlm = rule_score * 0.55 + vlm_overall_score * 0.45
```

VLM 输出维度：

```text
overall_score
person_state_score
composition_aesthetic_score
opening_hook_score
topic_expression_score
platform_publish_fit_score
manual_review_focus
```

限制：

```text
VLM 只看 contact sheet。
VLM 不等同于完整逐帧观看。
VLM 不能覆盖技术门禁和人工 Final 判断。
```

## 算法层 4：节奏同步评分

节奏同步评分回答：

```text
画面事件有没有和音乐事件对齐？
哪个版本卡点更稳定？
哪些时间点更适合人工返修？
```

核心函数：

```text
detect_audio_events
detect_visual_events
align_audio_visual_events
score_rhythm_sync
compare_rhythm_sync_versions
```

事件线：

| 事件线 | 当前事件 |
| --- | --- |
| 音频 | `energy_peak`、`onset_peak`、`beat_grid`、`accent_peak` |
| 画面 | `scene_cut`、`global_motion_peak`、`step_motion_peak_proxy`、`pose_keyframe`、`text_overlay_change`、`intro_effect` |

评分维度：

```text
step_sync
cut_sync
motion_sync
text_overlay_sync
beat_coverage
phase_consistency
fixability_score
periodicity_score
weighted_sync
```

profile 权重由 `PROFILE_WEIGHTS` 管理，例如：

```text
general_bgm_edit
single_person_stage_walk
pov_running
split_screen_comparison
sports_highlight
talking_head
```

节奏同步分单独输出 `rhythm_preferred_version`，不直接覆盖 `preferred_version`。它用于说明“卡点更好”，不是唯一发布判断。

## 最终判断输出

`review_output_video` 当前会输出四类版本倾向：

| 字段 | 含义 |
| --- | --- |
| `preferred_version` | 技术门禁优先的综合候选 |
| `strategy_preferred_version` | 策略评分更高的候选 |
| `rhythm_preferred_version` | 音画节奏同步更好的候选 |
| `vlm_preferred_version` | VLM 语义观感更好的候选 |

这些字段允许不一致。不一致时，不要强行合并成一个“唯一答案”，而是把差异交给人工审看：

```text
技术最好，但节奏一般
节奏最好，但横屏直发风险高
VLM 观感最好，但技术有 warning
策略分高，但人物状态需要人工确认
```

## 推荐值边界

核心函数：

```text
map_recommendation
```

当前推荐值：

```text
reject
recut
small_fix
publish
```

原则：

```text
fail -> reject
brief_fit low -> recut
unknown 或 warning -> small_fix
publish 只在技术 pass、brief_fit high、且不需要人工确认时出现
```

当前系统默认仍要求人工确认，所以多数结果不会自动给 `publish_as_final: true`。

## 迭代路线

| 阶段 | 要收敛的内容 | 不做什么 |
| --- | --- | --- |
| V1 | 评分字段、权重、schema、版本倾向、人工边界 | 不把远端做成第二套评分器 |
| V2 | VLM 语义融合、节奏同步评分、registry `algorithm_contract` | 不用单一总分掩盖分歧 |
| V3 当前 | 策略评分权重调优：platform 0.10、opening 0.23、composition 0.20 | 不把远端治理展开成第二套算法实现 |
| V3.1 下一步 | 用人工标注样本校准阈值和权重稳定性 | 不引入无法复现的主观描述 |
| V4 候选 | 接入 OCR / ASR / pose 模型，提高语义和动作判断 | 不取消 contact sheet 和 review points 证据 |

## 与远端评价层的关系

V3 不删除远端评价。远端保留：

```text
【作品验收】= 对照创作要求、作品文本和 Mac 结果，判断满足/不满足/不确定。
【数据复盘】= 读取发布后数据截图，形成内容调整和发布策略建议。
```

V3 禁止的是：

```text
远端重新实现 ffprobe / 抽帧 / 节奏同步 / VLM contact sheet 视频评分。
```

## 每次改算法必须回答

```text
改的是哪个评分维度？
输入证据是什么？
输出字段是什么？
是否改变权重或阈值？
是否改变人工判断边界？
是否需要迁移历史 metrics？
远端只是消费结果，还是任务协议也要变？
```

如果答案涉及新的评分口径，先改 registry 的 `algorithm_contract`，再改代码。
