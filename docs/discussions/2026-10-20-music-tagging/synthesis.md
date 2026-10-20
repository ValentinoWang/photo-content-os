# 综合稿：音乐库的标签现状，以及怎样和开源项目配合

## 共识（双方都同意，证据已核实）

| 编号 | 结论 | 证据 | 来源 |
|---|---|---|---|
| C1 | 现在没有选曲用的标签。3 首只有来源（local / netease / qishui）和授权（unknown / platform_copyrighted）两类标注；`bpm`、`beats`、`sections` 全是 null；风格、情绪、乐器、人声字段不存在。已测的只有时长、采样率、响度（-7.19 / -7.85 / -8.04 LUFS）和波形 | `GET /api/review/music`；`scripts/music_library/library.py:180-186` | O、G |
| C2 | 曲目规范把三个分析字段锁成 null，并禁止额外字段；分析结果不能直接写回 track.json | `schemas/music-track.schema.json:6`、`:138-146`；`library.py:37-41` | O1、G2 |
| C3 | 页面「节拍：还没分析，第一次用来配乐时自动分析」是写死的文案，音乐库这条线上没有分析 | `studio/static/review-music.js:25`；`docs/tasks/R210-music-link-import/TASK.md:72` | O2（收窄后）、G3 |
| C4 | 现有波形是整曲切 180 段的 RMS，只能当试听导航，不能当卡点依据 | `studio/media_review.py:50-55`、`:286-295` | G4 |
| C5 | 先做卡点要的硬数据（拍、重拍、BPM、能量），风格情绪的**自动标签**往后放；两者在 R208 规划里本来就分开（人工标签要不要现在做，见分歧） | `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:72`、`:84-86` | O8、G1 |
| C6 | 分析结果先放每首一份、按音频哈希绑定的 `music-map.json`，记工具、版本、权重、成功或失败状态；旁挂做法和现有 `peaks.json` 一致 | `media_review.py:279-295`；`library.py:75` | O3、G2 |
| C7 | 第一步拍点用 beat_this（代码和权重 MIT，2026-04 发 1.1.0），能量用 librosa（ISC，1.0.0 要求 numpy≥2.1，和主环境 numpy 2.2.6 兼容）。beat_this 还要 torchaudio（要和 torch 2.8.0 配对），librosa 还要 SciPy、Numba、scikit-learn，主环境现在都没装 | PyPI 元数据；`requirements-dev.txt:7`、`:10` | O、G |
| C8 | 平台曲的识别信息继续由 musicdl 管，它不负责分析 | `scripts/music_library/THIRD_PARTY_NOTICES.md:5-7` | O4、G |
| C9 | 当前不优先建设 CLAP 检索系统。将来上时用 transformers 的 `ClapModel`；pip 包 laion-clap 1.1.7、msclap 1.3.4 要求 numpy<2，和主环境冲突，而且 numpy 1.26.4 没有 cp313 轮子，独立环境还得换 Python 版本 | PyPI 元数据；`requirements-dev.txt:7` | O6、G |
| C10 | CLAP 给的是向量相似度乘缩放系数，不是概率；结果只当「模型候选」，阈值要用本曲库校准，人工改过的标签重算不覆盖 | transformers `modeling_clap.py` | O、G |
| C11 | 以后上自动标签，有两条候选：Essentia + MTG 预训练模型做固定类别（风格 Discogs400、情绪主题 56 类、人声/纯音乐、可舞性等），CLAP 做「文字找音乐」和词表外的描述。Essentia 库是 AGPL，MTG 模型是 CC BY-NC-SA 4.0，`essentia-tensorflow` 2.1b6.dev1389 有 cp313 macOS arm64 轮子；都没在本机跑过 | essentia.upf.edu/models；PyPI | O 提出，G 接受 |
| C12 | 软件许可不排除工具（课程项目、不商用），但工具许可不等于歌曲能发布；分析在本机做 | PRD `:137`；`library.py:20-23`；`docs/studio-contract-and-privacy.md:17-19` | O、G5 |
| C13 | BeatSync-Engine 的完整包是 Windows 便携应用（CuPy、llama.cpp + Qwen3-VL）；只借它按拍算能量、切点密度、段落候选的算法，要抄代码就保留 AGPL 声明；它的段落名是聚类加规则得出的，只算候选 | 上游 README、`src/auto_mode/stage3_sections.py` | O、G |
| C14 | 「按 4 小节、8 小节标乐句」是规划里的假设，产出要标成候选，听过才算数 | PRD `:85` | G |
| C15 | 不按 BPM 等间隔切，用实测拍点 | PRD `:35`（不按 BPM 平均分配切点）、`:94`（切点吸附） | G |
| C16 | 不接 beets 当曲库（autobpm 本质是 librosa，xtractor 本质是 Essentia）；allin1 暂缓（依赖 NATTEN、Demucs、GitHub 版 madmom，最近一次发版 2023-10）；Hypit 的 BeatAPI 是远程出视频、出图的服务，不是节拍分析器 | 上游文档；`reference/hypit/packages/provider-beatapi/README.md:9-24` | O、G |

## 分歧与裁决

| 议题 | Opus 的看法与证据 | GPT 的看法与证据 | 裁决 | 理由 |
|---|---|---|---|---|
| 试点前要不要先把曲目规范升 v2 | 要。另存之后 track.json 的 `bpm:null` 会原样透传给页面，和分析结果矛盾（`media_review.py:280`） | 不必。限制只管曲目对象，不管旁挂文件；升 v2 还要动索引版本检查和一致性检查（`library.py:64-75`） | 试点不改规范；接到页面之前必须处理三个 null 占位字段（删掉，或投影时以 `music-map.json` 为准） | 试点结果不上页面，矛盾还不会出现；GPT 第一轮 G2 也写了「接入页面前明确投影合同」。两边证据都成立，只是时间点不同 |
| 第一步要不要同时人工标情绪、用途、人声 | 不放。页面没有按标签筛选（`review-music.js:34` 只按来源筛），加编辑入口要先出设计稿，3 首上现在没有用处 | 放。3 首足以开始人工标签，可以给推荐理由用（PRD `:72`） | 交给用户拍板 | 两边都只有优先级推断，没有决定性证据 |
| CLAP 的大小 | 用 transformers 格式的 `laion/larger_clap_music`，0.78 GB，apache-2.0 | 原版音乐权重 2.35 GB | 按 0.78 GB 算 | 两个数都对（HF 文件列表），但我们会走 transformers 路线，所以按它算；GPT 质询时也接受了 transformers 路线 |

## 单方发现

| 编号 | 结论 | 来源 | 核实了没有 | 收不收 |
|---|---|---|---|---|
| S1 | 仓库里已有启发式的音频分析：`scripts/review_output_video.py:777-831` 按 1 秒窗口算能量、估 BPM（压到 70–180），`:944-1040` 从起音和能量峰估 BPM，再从 0 秒开始铺**等间隔**节拍网格，给成片自检用；它没接音乐库 | G | 已核实（Opus 打开过） | 收。推论（Opus，推断）：有了 `music-map.json` 以后，成片自检要改用实测拍点，否则自检用的正是 C15 说不该用的等间隔网格 |
| S2 | CLAP 的模型卡写的是 `language: en`；用英文提示，固定中文词表可以人工对应好英文提示，不必每次调用大模型 | G 纠正 O10 | 已核实（模型卡） | 收，替换 O10 原来的说法 |
| S3 | musicdl 的曲目信息有开放的 `raw_data`；平台接口里有没有风格或标签，现在没查过 | G 纠正 O4 | 已核实 `raw_data` 字段存在；平台有没有标签未核实 | 收，O4 降为「当前适配器没取，平台有没有未核实」 |
| S4 | 0.5 秒平移检查要排除边界、带容差：beat_this 推理有分块、补齐、边界裁剪 | G | 已核实（GPT 打开过 `beat_this/inference.py`，Opus 没开） | 收 |
| S5 | Last.fm、MusicBrainz 现在不接：要联网发查询；「中文曲覆盖差」没测过 | O 提出，G 降级 | 联网已核实，覆盖未核实 | 收「现在不接」，理由只留联网和没必要 |

## 弃用

| 编号 | 结论 | 为什么不要 |
|---|---|---|
| O2 原说法 | 「仓库里没有任何节拍分析代码」 | 错。S1 有反例，Opus 当时的搜索词没覆盖到实际函数名 |
| O5 | 「从文件夹导入不读文件自带的歌名歌手」 | 错。Studio 文件夹入口走 `import_folder` → `import_client_file`，会读内嵌标签（`scripts/import_music.py:28-35`、`studio/review_jobs.py:103-105`、`library.py:237-241`）；`library.py:218` 的 `import_local` 只在 `tests/test_music_library.py:158` 用到 |
| O9 原说法 | 「按标签筛选已核实没用」 | 接口只能核实 3 首，「没用」是优先级推断，「几十首」这个门槛也没有证据 |
| O10 原说法 | 「CLAP 只认英文，要大模型每次翻译」 | 被 S2 替换 |
| O 第 5 节 | 「Essentia 和 CLAP 一样有 numpy 冲突」 | Essentia 只要求 numpy≥1.25，没有上限；要不要隔离 Essentia 是工程选择（TensorFlow 重），冲突本身不成立 |
| O 第 5 节 | 「平台版权曲音频不出本机」当规则 | `studio-contract-and-privacy.md:19` 写的是「用户策略允许发送的派生证据」，不是一刀切；本次只保留「分析在本机做」 |

## Opus 推翻自己的地方

- O2 → 改成「音乐库这条线没有分析；成片自检里有启发式 BPM 和等间隔网格」（G 的 S1 反例）。
- O5 → 撤回（G 指出入口搞混了）。
- O4 → 降为「当前适配器没取，平台有没有未核实」（G 指出 `raw_data`）。
- O9、O10 → 降为推断、换说法（G 的反驳）。
- O1 的时间点 → 试点不先升 v2（G 的 `library.py:64-75`）。
- 第 4 节第二步 → 曲库扩充前不上自动标签（G1 的优先级）。
- O3 → 波形只当试听导航（G4）。
- BeatSync 定位、4/8 小节乐句、CLAP 分数不是概率、平移检查加容差 → 都接受 GPT 的说法。

## Opus 驳回 GPT 的地方

- G 第一轮「CLAP 音乐权重 2.35 GB」当作接入成本 → 按 0.78 GB 算（HF `laion/larger_clap_music` 文件列表，apache-2.0），GPT 质询时已接受 transformers 路线。

## 需要用户拍板

1. 第一步要不要顺便给现有 3 首人工标情绪、用途、人声有无。不标：第一步只做拍点和能量。标：先写进旁挂文件，页面暂不显示，不用先出设计稿。
2. 第一步之后，先扩曲库（PRD §4.3 的补充来源），还是先把节拍图接到页面（先定页面投影合同、处理三个 null 占位字段，是否升曲目规范另定；页面改动先出设计稿）。

## GPT 异议的处理

- 异议 1（C5、C9 扩大了 G1 的立场）：接受。C5 限定为「自动标签」往后放；C9 改为「当前不优先建设检索系统」，「3 首建不起检索」是 O9 的说法，不归 GPT。
- 异议 2（拍板第 2 项又把升 v2 写成必经步骤）：接受。改为先定页面投影合同、处理 null 占位字段，是否升曲目规范另定。
- 异议 3（C15 行号）：接受。PRD 第 93 行是表格分隔线，第 35 行是「不按 BPM 平均分配切点」，第 94 行是切点吸附。Opus 质询时说 GPT 引的 `:94` 是「镜长范围」，是 Opus 自己数错了行，GPT 原引用正确。
