# Opus 第一轮：音乐库的标签现状与开源配合

## 1. 直接回答

没有打选曲用的标签。真实数据 3 首里，只有两类「标注」：来源（`platform`：local / netease / qishui）和授权（`license_status`：unknown / platform_copyrighted），页面把授权显示成标签。`bpm`、`beats`、`sections` 三首全是 `null`，而且曲目规范把这三个字段的类型锁成 `null`、不允许额外字段，所以现在连写进去的位置都没有；风格、情绪、能量、人声有无这类字段根本不存在。已测好的只有时长、采样率、响度（-7.19 / -7.85 / -8.04 LUFS）和波形峰值。

## 2. 论点表

| 编号 | 结论 | 证据 | 把握 | 建议 |
|---|---|---|---|---|
| O1 | 规范把 bpm/beats/sections 锁成 null，且 `additionalProperties:false`；要打标签必须先改规范 | `schemas/music-track.schema.json:7`、`:138-146`；入库时写死 `scripts/music_library/library.py:186` | 已核实 | 规范升 v2：bpm 改成数字或 null；完整分析放旁挂文件 |
| O2 | 页面「节拍：还没分析，第一次用来配乐时自动分析」是写死的文案，仓库里没有任何节拍分析代码 | `studio/static/review-music.js:25`；`rg beat_this\|librosa\|music-map scripts studio` 无结果（只命中无关的 `scripts/edit_backends/openchatcut_adapter.py`） | 已核实 | 第一步先兑现这句话 |
| O3 | 波形峰值已经是旁挂文件 `<曲目>/peaks.json`，不进索引；分析结果照这个做法放 `music-map.json`、`tags.json`，不必每次列表都读整段拍点数组 | `studio/media_review.py:279-295`；`library.py:75` 列表时逐首比对 track.json 与索引 | 已核实 | 旁挂文件里写工具名、版本、模型、生成时间，换模型能重算 |
| O4 | 平台那边拿不到风格、情绪：musicdl 的曲目信息没有这类字段，我们接 musicdl 时还关掉了歌词、封面、写标签 | `.venv/.../musicdl/modules/utils/data.py:23-53`；`scripts/music_library/musicdl_engine.py:5`、`:223-228` | 已核实 | 标签只能靠本机分析音频，不指望平台 |
| O5 | 「从文件夹导入」不读文件自带的歌名、歌手，一律用文件名和「未知歌手」；网易云客户端文件才读 | `library.py:218`；对照 `scripts/music_library/client_files.py:111-113`。真实那首 CRUSH VIBE 文件本身没有歌手标签，所以现有数据没受影响 | 已核实（现有数据无影响） | 顺手改：先读 ID3/MP4 标签，读不到再兜底 |
| O6 | 主环境钉了 numpy 2.2.6；laion-clap 1.1.7 和 msclap 1.3.4 都要求 numpy<2，装进主环境会冲突 | `requirements-dev.txt:7`；PyPI `laion-clap`、`msclap` 的 requires_dist | 已核实 | CLAP 用 transformers 的 `ClapModel`（同一套 LAION 权重），或放独立环境 |
| O7 | 重的分析件要和 Studio 主环境隔开，沿用 R207 的锁定清单加 `.tools/`，用子进程调用、JSON 进出 | `third_party/edit-tools.lock.json`；PRD §7 `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:137` | 推断 | 一个 `music-analysis` 工具目录，版本和许可写进锁定清单 |
| O8 | 卡点要的是硬数据（拍、重拍、段落、能量），不是风格情绪；R208 推荐主线用 CLAP「文字找音乐」，标签主要服务人工浏览和推荐理由 | PRD `:72`、`:84-86` | 推断 | 先做节拍图，再做标签 |
| O9 | 曲库只有 3 首，按标签筛选现在没有实际用处；曲库扩到几十首才有意义 | 接口 `GET /api/review/music` 返回 3 首 | 已核实 | 标签和曲库扩充（PRD §4.3 补充来源）一起排 |
| O10 | CLAP 文字端只认英文，中文分镜描述要先由大模型写成英文音乐描述；这一步走 AI 网关、只发文字不发音频 | HF transformers CLAP 文档示例全是英文文本；Core `ai-egress-ownership-guard-card.md` | 推断 | 大模型只出英文描述，音频和嵌入都留本机 |

## 3. 配合方案

| 开源项目 | 负责 | 接入方式 | 许可 | Mac 上 | 把握 |
|---|---|---|---|---|---|
| beat_this 1.1.0（2026-04 发版） | 拍、重拍、BPM | 依赖调用，放分析工具环境 | 代码和权重 MIT | 要 torch≥2，无 CUDA 自动走 CPU；主环境已有 torch 2.8 | 已核实许可和依赖，未实跑 |
| librosa 1.0.0 | 按拍算响度、起音、亮度 → 能量曲线、段落 | 依赖调用 | ISC | 要求 numpy≥2.1，和主环境兼容 | 已核实依赖，未实跑 |
| Essentia + MTG 预训练模型 | 风格（Discogs400）、情绪主题（MTG-Jamendo 56 类）、乐器、可舞性、人声/纯音乐、唤醒度/愉悦度 | 子进程，独立环境（带 TensorFlow）；部分模型有 ONNX | 库 AGPL-3.0；模型 CC BY-NC-SA 4.0，非商用前提下可用 | `essentia-tensorflow` 有 cp313 macOS arm64 轮子（2.1b6.dev1389） | 已核实轮子和许可，未实跑 |
| CLAP（transformers `ClapModel`，权重 laion/clap-htsat-*） | 每首一个音频嵌入；文字找音乐；自定义词表零样本打标签 | 依赖调用，嵌入存旁挂文件 | laion-clap CC0；权重以模型卡为准（未核实） | torch 已有；transformers 未装 | 推断 |
| BeatSync-Engine（AGPL） | 按拍的冲击分、乐句锚点的算法 | 读代码借算法，按需复制并保留许可 | AGPL | — | PRD 已列，未复核 |
| all-in-one（allin1） | 直接给 intro/verse/chorus 段落标签 | 不建议先用，见第 5 节 | MIT | 依赖 natten、demucs、GitHub 版 madmom | 已核实依赖和发版时间 |

词表：中文受控词表二三十个（情绪、风格、能量档、人声有无、BPM 档），由上面模型的原始分数映射过来；原始分数和置信度留在 `tags.json`，页面只显示过阈值的中文标签；用户手改的标签记为「人工」，重算不覆盖。

## 4. 第一步

做 R208 阶段 B 的「音乐地图」：beat_this + librosa 对库里 3 首产出 `music-map.json`（BPM、拍、重拍、段落、能量曲线），规范升 v2 让 bpm 能写数字，页面「节拍」一栏显示真实 BPM 和段落数，波形上标重拍。验收：三首各抽 2 段 10 秒，人工听拍点对不对；一首切掉前 0.5 秒重跑，拍点整体平移约 0.5 秒；分析失败时页面显示「分析失败」，不显示「还没分析」。第二步再加人声/纯音乐和 CLAP 嵌入，第三步随曲库扩充加风格情绪标签。

## 5. 不建议做的

- 不用 Last.fm / MusicBrainz 的众包标签：要联网，中文平台曲覆盖差，还要把曲目信息发出去。
- 不接 beets 当曲库：我们已有自己的库和授权规则，只借它 autobpm、xtractor 插件的思路。
- 不先上 allin1：最近一次发版是 2023-10，依赖 natten、demucs 和 GitHub 版 madmom，PRD 已定不用 madmom（`PRD.md:37`）。
- 不把 laion-clap、msclap、Essentia 装进 Studio 主环境：numpy 版本冲突，TensorFlow 太重。
- 不让大模型直接听歌打标签：平台版权曲的音频不出本机。
