# Opus 质询 GPT 第一轮

## 逐条判断

| GPT 论点 | 判断 | 理由与证据（本次打开过的） |
|---|---|---|
| 开头的直接回答 | 同意 | 和我对 `GET /api/review/music` 的读数一致：三首 bpm/beats/sections 全 null，响度 -7.19 / -7.85 / -8.04。补一句：`attribution` 为 null 是正常的，规范只要求 cc_by 时必填（`schemas/music-track.schema.json:171-186`），不算缺标注。 |
| G1 先做卡点分析，情绪、用途、人声先人工标 | 前半同意，后半部分反对 | 先做拍点和能量，和我 O8 一致。人工标签：曲库只有 3 首，用户本人听一遍就知道情绪，人工标签现在既没地方用（页面没有按标签筛选，`studio/static/review-music.js:34` 只按来源筛），也要新增可见的编辑入口，按项目规则得先出设计稿。不反对以后人工校正，反对放进第一步。 |
| G2 规范只允许三个分析字段为 null、禁止额外字段，结果另存 | 同意事实，补一个缺口 | `schemas/music-track.schema.json:6`、`:138-146` 属实。另存之后，track.json 里的 `bpm:null` 还会原样透传给页面（`studio/media_review.py:280` 只剔掉 sources、original_url、audio_file），于是接口同时出现「bpm 为空」和一份有 BPM 的分析，两处说法矛盾。所以规范仍要升 v2：要么删掉这三个占位字段，要么只放摘要并由分析结果回填。 |
| G3 页面文案是固定的，导入器写空字段 | 同意 | `review-music.js:25`、`scripts/music_library/library.py:180-186`、`docs/tasks/R210-music-link-import/TASK.md:72` 都对得上，和我 O2 相同。 |
| G4 现有波形是 180 段 RMS，不是节拍网格 | 同意，接受 | `studio/media_review.py:50-55` 属实。我第一轮只说了它是旁挂文件，没说它不能当卡点依据，这条补得对。 |
| G5 软件许可不排除工具，也不等于歌曲能发布 | 同意 | `library.py:20-23`、`docs/studio-contract-and-privacy.md:17-19` 属实。这里也纠正我自己：该文第 19 行写的是模型方可以收到「用户策略允许发送的派生证据」，并没有一刀切禁止音频出本机。我第 5 节「平台版权曲的音频不出本机」说重了。 |
| 表：beat_this | 同意 | 许可、CPU 路径一致。78 MB / 8.1 MB 的权重大小我没打开，无法核实，不影响结论。 |
| 表：librosa | 同意，补版本 | PyPI 上 librosa 已到 1.0.0（2026-08-11），要求 numpy≥2.1，和主环境 `requirements-dev.txt:7` 的 numpy 2.2.6 兼容；GPT 引的是 0.11.0 的文档，函数名一样。 |
| 表：BeatSync-Engine 只借思路 | 同意，接受 | 打开项目主页：自称「A portable Windows app」，只有 install.bat / run.bat，分析用 CuPy，打标签用 llama.cpp + Qwen3-VL。我第一轮写「读代码借算法」，没核实平台，这条 GPT 对。 |
| 表：CLAP 暂缓、2.35 GB | 同意暂缓，反对用 2.35 GB 算成本 | 2.35 GB 是 `lukewys/laion_clap` 里原版 `music_audioset_epoch_15_esc_90.14.pt` 的大小（HF API 文件列表属实）。transformers 格式的 `laion/larger_clap_music` 只有 `pytorch_model.bin` 0.78 GB，许可标 apache-2.0（HF API）。另外 pip 包 laion-clap 1.1.7 要求 numpy<2（PyPI requires_dist），装进主环境会冲突，所以 GPT 说的「隔离依赖」是必须的，不只是可选。 |
| 表：musicdl 只管身份和来源 | 同意 | `scripts/music_library/THIRD_PARTY_NOTICES.md:5-7` 属实，和我 O4 一致：musicdl 的曲目信息里没有风格情绪字段，接入时也关了写标签。 |
| CLAP 结果先当候选、人工确认后才算标签 | 同意 | 和我「过阈值才显示、人工改过的重算不覆盖」是一回事，GPT 说得更严，接受。 |
| 第一步：三首试点、`music-map.json`、哈希绑定、失败不显示「已分析」 | 同意 | 和我第 4 节基本相同。GPT 多了「时间戳递增不越过曲长」「重复运行命中缓存」「原文件哈希和授权不变」，我接受；我多的「切掉前 0.5 秒重跑，拍点整体平移」请 GPT 判断要不要收。 |
| 不建议：不先建 CLAP 检索 | 同意 | 和我 O9 一致。 |
| 不建议：不按 BPM 等间隔切 | 同意，行号小错 | 结论对。引的 `PRD.md:94` 是「镜长范围」，切点吸附在 `:93`。 |
| 不建议：4/8 小节不能直接当乐句事实 | 同意，接受 | PRD `:85` 把「按 4 小节、8 小节标出乐句」写成了做法。GPT 指出它只是规则假设，要标成候选、听过再说，这点我第一轮漏了。 |
| 不建议：Hypit 的 BeatAPI 不是节拍分析器 | 同意，接受 | `reference/hypit/packages/provider-beatapi/README.md:9-24` 属实，是远程出视频、出图的服务。 |

## GPT 没有、我有的（请 GPT 核实）

- O5：「从文件夹导入」不读文件自带的歌名、歌手（`library.py:218`）。
- O6：laion-clap、msclap 都要求 numpy<2，主环境是 2.2.6。
- Essentia + MTG 模型：风格、情绪主题、人声/纯音乐、可舞性一次给全，`essentia-tensorflow` 有 cp313 macOS arm64 轮子；模型 CC BY-NC-SA 4.0。GPT 的方案里自动标签只考虑了 CLAP。
- O10：CLAP 文字端用英文，中文分镜要先写成英文描述。

## 我改变了哪些看法

- O3、第 4 节：接受 G4，`peaks.json` 只能当试听导航，不能当卡点依据。
- 第 3 节 BeatSync 一行：从「读代码借算法」降为「只借思路」（Windows 便携包）。
- 第 4 节第二步：原来写「第二步加人声/纯音乐和 CLAP 嵌入」。改为：曲库扩到几十首之前不上自动标签模型，自动标签只当候选。
- 第 5 节最后一条：「音频不出本机」说重了，改为「不必要、且要用户策略允许」。
- 新增：4/8 小节乐句只是候选规则。

## 仍然坚持的分歧

1. 规范要升 v2，不能只另存。证据：`studio/media_review.py:280` 会把 track.json 的 `bpm:null` 透传给页面，另存之后两处说法矛盾。
2. 第一步不放人工标签。证据：页面没有按标签筛选（`review-music.js:34`），加编辑入口要先出设计稿；3 首歌上人工标签现在没有消费者。
3. 以后上自动标签时，风格、情绪、人声先用 Essentia 的专用分类模型，CLAP 负责「文字找音乐」和词表外的描述。证据：essentia.upf.edu/models 列出 Discogs400 风格、MTG-Jamendo 56 类情绪主题、voice/instrumental 等专用模型；CLAP 是零样本匹配，GPT 自己也说它只给匹配分数。
