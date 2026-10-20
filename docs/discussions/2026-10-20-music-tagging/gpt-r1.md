**有来源、授权等管理标注，但还没有完成选曲标签和节拍分析（已核实）。** 本次 [GET 实际数据](http://127.0.0.1:8765/api/review/music) 中，CRUSH VIBE 的 `platform=local、license_status=unknown`；Turn Back Time 和 Fever Pitch 分别来自 `netease、qishui`，均为 `platform_copyrighted`。三首的 `bpm、beats、sections、attribution` 全是 `null`，没有风格、情绪、乐器、人声标签；已有响度，分别为 −7.19、−7.85、−8.04 LUFS。

**论点表（按价值排序）**

| 编号 | 结论 | 证据（仓库相对路径:行号 / URL） | 把握 | 建议 |
|---|---|---|---|---|
| G1 | 值得先补“能卡点”的分析，再考虑自动描述标签；现有规划也把两者分开 | `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:72`、`:84–86`；上述实际接口 | 推断 | 先做三首的拍子、重拍、能量曲线；情绪、用途、人声先人工标 |
| G2 | 不能直接把分析结果填进现有曲目：schema 明确只允许三个分析字段为 `null`，并禁止额外字段 | `schemas/music-track.schema.json:6`、`:138–145`；`scripts/music_library/library.py:37–41` | 已核实 | 建独立、版本化的分析记录，以音频哈希关联；接入页面前明确投影合同 |
| G3 | 页面“第一次用来配乐时自动分析”不能证明能力已经实现，它是固定文案；导入器实际写入空分析字段 | `studio/static/review-music.js:25`；`scripts/music_library/library.py:180–186`；`docs/tasks/R210-music-link-import/TASK.md:72` | 已核实 | 将“已规划”与“已分析”分开验收 |
| G4 | 已有波形是整曲分成180段后归一化的 RMS，不是节拍网格，也不能直接当精细卡点依据 | `studio/media_review.py:50–55`、`:286–295` | 已核实 | 保留作试听导航，另算带时间戳的分析曲线 |
| G5 | 项目前提允许复用 AGPL、非商用代码；歌曲仍须遵守现有授权和本地边界 | `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:137`；`scripts/music_library/library.py:20–23`；`docs/studio-contract-and-privacy.md:17–19` | 已核实 | 不因软件许可排除工具，也不把安装工具视为获得歌曲发布授权 |

**配合方案表**

以下能力和许可来自已打开的文档或源码；本次未安装、未执行分析，Mac 耗时与峰值内存均未实测。

| 开源项目 | 负责哪类标签或分析 | 接入方式 | 许可 | Mac 能否跑、资源 | 把握 |
|---|---|---|---|---|---|
| [beat_this](https://raw.githubusercontent.com/CPJKU/beat_this/main/README.md) | 拍子、重拍；据拍间隔推导 BPM | **依赖调用**，复用模型实例，显式指定本地权重 | 代码及权重 MIT | 有 CPU 推理路径；主模型约78 MB，小模型8.1 MB，另需 PyTorch | 能力/许可已核实；Mac 可行性为推断 |
| [librosa](https://librosa.org/doc/0.11.0/generated/librosa.feature.rms.html) | RMS 能量、[起音强度](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_strength.html)，进一步按拍汇总、辅助分段 | **依赖调用**，和 beat_this 共用解码结果 | [ISC](https://raw.githubusercontent.com/librosa/librosa/main/LICENSE.md) | CPU 计算，无模型权重；内存取决于音频长度、采样率和频谱规模 | 能力/许可已核实；本机运行未核实 |
| [BeatSync-Engine](https://github.com/Merserk/BeatSync-Engine) | 能量驱动切点密度、段落候选、帧量化规则 | **先只借思路**；课程前提允许之后抽取代码 | AGPL-3.0 | 完整包面向 Windows，包含 CUDA、Vulkan及便携运行时；不能视为 Mac 即装即用 | 平台定位已核实；移植成本为推断 |
| [LAION CLAP](https://github.com/LAION-AI/CLAP) | 文字找音乐；用受控候选词比较风格、情绪、乐器、人声描述 | **暂缓；需要时子进程调用**，隔离依赖并缓存向量 | 仓库及所选权重标注 CC0-1.0 | [源码有 CPU 路径](https://raw.githubusercontent.com/LAION-AI/CLAP/main/src/laion_clap/hook.py)；[音乐权重2.35 GB](https://huggingface.co/lukewys/laion_clap/blob/main/music_audioset_epoch_15_esc_90.14.pt)，不等于峰值内存 | 能力/许可/文件大小已核实；Mac 性能未核实 |
| musicdl | 继续承担歌曲身份、来源等导入信息 | **保留现有依赖调用** | PolyForm Noncommercial 1.0.0 | 已用于本机导入；不承担新增音乐分析 | 已核实：`scripts/music_library/THIRD_PARTY_NOTICES.md:5–7` |

CLAP 给的是描述与音频的匹配分数，建议保存为“模型候选”，经人工确认后再成为标签。BeatSync 的[段落源码](https://raw.githubusercontent.com/Merserk/BeatSync-Engine/main/src/auto_mode/stage3_sections.py)使用聚类和阈值规则，其主歌、副歌等名称也应视为候选判断。

**建议的第一步**

做一个**仅覆盖现有三首歌的本地分析试点**，先验证价值，不先扩大曲库或接入整套编辑器。

- **做什么：** beat_this 测拍子和重拍，librosa 算按拍能量；人工补少量情绪、用途、人声标签。全程保留原音频、来源和授权记录。
- **产出什么：** 每首一份哈希绑定的 `music-map.json`，记录 BPM、拍点、重拍、能量、算法及权重版本、成功或失败状态；另有人工标签表和耗时、峰值内存记录。这是建议的新合同。
- **怎么验收：** 时间戳递增且不越过曲长；三首分别试听开头、中段、结尾，检查漏拍、半速/倍速和重拍错位；失败不得显示“已分析”；重复运行命中缓存；原文件哈希和授权不变。之后再决定是否把结果接到 Studio。

**不建议做的**

- **不先建 CLAP 向量检索系统：** 目前只有三首，收益不足以优先承担模型和依赖成本（推断，依据实际接口）。
- **不只用 BPM 等间隔生成切点：** 拍子与重拍时间才是卡点输入，现有规划也要求如此，见 `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:85`、`:94`。
- **不把每4/8小节直接当成已识别乐句：** 应作为待校验规则，不能把规划中的假设输出成音乐事实。
- **不把 Hypit 的 BeatAPI 当节拍分析器：** 已读适配器描述的是远程生成任务，见 `reference/hypit/packages/provider-beatapi/README.md:9–24`。

本次仅只读取证，无文件写入、提交、安装或服务启动；业务仓库存在既有改动，Harness SSOT 工作区干净。
