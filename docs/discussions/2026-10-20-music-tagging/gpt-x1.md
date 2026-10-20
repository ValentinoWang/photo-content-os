现状判断一致；但 **O2、O5 有直接反例，O1、O4、O9、O10 的结论超出了证据支持范围**。以下判断针对原表述；文档或依赖存在，不代表本机运行已验证。

**逐条质询论点**

| 论点 | 判断 | 核查结果与证据 |
|---|---|---|
| O1 | **反对“必须先改规范”** | 字段锁为 `null` 属实；`additionalProperties:false` 实际在 `schemas/music-track.schema.json:6`，不是第7行。但它约束曲目对象，不禁止新增独立分析文件。只有决定把 BPM 写回曲目时才必须改曲目合同。升 v2 还要处理 `library.py:64` 的索引版本检查及 `:75` 的索引与文件一致性，不能只改字段类型。 |
| O2 | **反对** | 固定文案属实，但“仓库没有任何节拍分析代码”错误。`scripts/review_output_video.py:777–831` 已计算能量和 BPM；`:922–1040` 已有起音事件、BPM估计及节拍网格。它们是启发式估计，**不证明已接入音乐库**。原搜索词漏掉了实际函数名。 |
| O3 | **同意** | `studio/media_review.py:279–295` 确实读取旁挂 `peaks.json`；`scripts/music_library/library.py:75` 确实逐首比对索引。旁挂分析合理，但还应绑定音频哈希、预处理及合同版本；“这样更适合”属于设计推断。 |
| O4 | **反对** | `.venv/lib/python3.13/site-packages/musicdl/modules/utils/data.py:23` 保留了开放的 `raw_data`；没有独立 genre/mood 属性，不能推出平台拿不到。`scripts/music_library/musicdl_engine.py:190–193` 只证明当前适配器没有投影它们；`:223–228` 关闭下载补全，也不证明平台无标签。“只能分析音频”还漏掉人工标签。 |
| O5 | **反对** | 混淆了入口。Studio 文件夹入口在 `studio/review_jobs.py:103–105` 调用 `import_folder`；后者在 `scripts/import_music.py:28–35` 调用 `import_client_file`，再由 `scripts/music_library/library.py:237–241` 读取内嵌元数据。`:218` 是另一条 `import_local` 路径，不能据此要求修复“从文件夹导入”。 |
| O6 | **同意** | [laion-clap 1.1.7 元数据](https://pypi.org/pypi/laion-clap/1.1.7/json)、[msclap 1.3.4 元数据](https://pypi.org/pypi/msclap/1.3.4/json) 均要求 NumPy＜2，与 `requirements-dev.txt:7` 冲突。新增成本：当前是 Python 3.13，而 [NumPy 1.26.4](https://pypi.org/pypi/numpy/1.26.4/json) 没有 cp313 轮子，独立环境也应选择合适的 Python 版本。 |
| O7 | **同意，限重型组件** | `third_party/edit-tools.lock.json:46–79` 和 PRD `:137` 支持沿用锁定工具环境的方式，但没有规定所有分析都必须子进程化。隔离应解决明确的依赖冲突，并补超时、失败状态及输出校验。 |
| O8 | **同意** | `docs/tasks/R208-vlog-aesthetic-layer/PRD.md:72`、`:84–86` 直接区分检索描述与卡点数据。 |
| O9 | **反对“已核实无用”** | [接口](http://127.0.0.1:8765/api/review/music) 只能核实三首，不能核实标签没有用途，也不能证明“几十首”这个门槛。暂缓自动筛选系统合理；人工标注人声、情绪、用途仍可服务选曲说明，参见 PRD `:72`。 |
| O10 | **反对绝对表述** | 示例全是英文不能证明“只认英文”。[fused 模型卡](https://huggingface.co/laion/clap-htsat-fused/raw/main/README.md) 标注 `language: en`，支持优先使用英文提示，但不证明中文效果为零。固定中文词表可以人工映射英文提示，不必每次调用大模型。接受通过网关处理必要的生成调用。 |

另外，我通过 [CRUSH VIBE 音频 GET](http://127.0.0.1:8765/api/review/music/e60863568554f0fe6feec9ce1d9c8999dfd10ed8d2b0662d32d872fecd277256/audio) 后用 ffprobe 检查，确实没有歌手标签：**接受这项新增发现，但它不能挽救 O5 的入口判断。**

**配合方案表及词表方案**

| 项目 | 判断 | 核查与遗漏 |
|---|---|---|
| beat_this | **同意** | [1.1.0 元数据](https://pypi.org/pypi/beat-this/1.1.0/json) 确认2026年4月发布，依赖还包括 torchaudio；不能仅凭“已有 torch”认定环境齐备。[torchaudio 2.8.0](https://pypi.org/pypi/torchaudio/2.8.0/json) 明确绑定 torch 2.8.0。BPM需从拍点推导，不是把接口输出照搬即可。 |
| librosa 1.0.0 | **同意** | [元数据](https://pypi.org/pypi/librosa/1.0.0/json) 确认 NumPy≥2.1、Python≥3.12；但还要求较新的 SciPy、Numba、scikit-learn。NumPy满足只是一项条件。“能量曲线→段落”仍需要自建规则和验收。 |
| Essentia＋MTG | **同意列为后续候选** | [官方模型目录](https://essentia.upf.edu/models.html) 支持所列风格、情绪、乐器、人声等任务及模型许可；[指定版本元数据](https://pypi.org/pypi/essentia-tensorflow/2.1b6.dev1389/json) 确有 cp313、macOS 15＋arm64 轮子，约115 MB。**接受我首轮漏列的候选**；但轮子不是所有模型均可运行的证明，模型权重、共享骨干、内存及阈值仍须验证。 |
| transformers CLAP | **同意替代路线，纠正许可写法** | [Transformers 元数据](https://pypi.org/pypi/transformers/json) 没有 NumPy＜2限制；所选 [fused](https://huggingface.co/laion/clap-htsat-fused)、[unfused](https://huggingface.co/laion/clap-htsat-unfused) 模型卡均标 Apache-2.0。应记录实际运行库和具体权重许可，不能以原 laion-clap 的 CC0 代替。 |
| BeatSync | **同意借算法** | 已复核[上游](https://github.com/Merserk/BeatSync-Engine)及[段落源码](https://raw.githubusercontent.com/Merserk/BeatSync-Engine/main/src/auto_mode/stage3_sections.py)：完整包面向 Windows；段落名称来自聚类和启发式分类，不能当人工确认的曲式。 |
| allin1 | **同意暂缓** | [上游安装说明](https://github.com/mir-aidj/all-in-one)确有 NATTEN、Demucs、GitHub版 madmom；[PyPI记录](https://pypi.org/pypi/allin1/json)确认最近发布于2023年10月。依赖成本足够支持暂缓；旧发布日期本身不等于完全停止维护。 |

对受控中文词表、人工修改不被覆盖：**同意**。对“原始分数和置信度”的表述：**反对混用**；[CLAP实现](https://raw.githubusercontent.com/huggingface/transformers/main/src/transformers/models/clap/modeling_clap.py)计算的是归一化向量相似度乘缩放系数，不是经本曲库校准的正确概率。

**对“第一步”的判断：同意核心试点，反对绑定过多改动**

接受先对三首生成音乐地图；不认为试点必须同时完成曲目v2迁移、页面改造和新模型接入。先交独立结果及资源测量，更容易判断分析是否值得继续。

“裁掉0.5秒”可作辅助检查，但应明确匹配内部事件满足 `新时间≈旧时间−0.5秒`，排除边界并给容差。[beat_this推理源码](https://raw.githubusercontent.com/CPJKU/beat_this/main/beat_this/inference.py)存在分块、补齐和边界裁除，不能预设所有输出严格平移。还应补查重拍、半速/倍速、原音频不变、缓存及失败重试。

**对“不建议做的”逐条判断**

| 项目 | 判断与依据 |
|---|---|
| Last.fm／MusicBrainz | **无法核实完整理由**。[Last.fm接口](https://www.last.fm/api/show/track.getTopTags)和[MusicBrainz文档](https://musicbrainz.org/doc/MusicBrainz_API)支持在线查询会发送查询信息；没有证据证明当前曲目的覆盖差。暂不接可以，不能把未测试覆盖写成事实。 |
| 不接 beets | **同意**。已有曲库合同；[autobpm](https://beets.readthedocs.io/en/stable/plugins/autobpm.html)本质调用 librosa，[xtractor](https://github.com/adamjakab/BeetsPluginXtractor)另需 Essentia提取器及模型，没必要再引入整套库管理。 |
| 不先上 allin1 | **同意**，依据上表依赖及 PRD `:37` 的当前选择；不以“许可不允许”为理由。 |
| 三类工具都不进主环境 | **反对统一理由**。两个 CLAP 包有明确 NumPy冲突；[Essentia元数据](https://pypi.org/pypi/essentia-tensorflow/2.1b6.dev1389/json)仅声明 NumPy≥1.25，没有同样上限。Essentia隔离可作为工程选择，不能说冲突已核实。 |
| 不让远程大模型直接听歌 | **同意当前方案保持本地分析**；但不要把项目边界泛化为所有大模型都不能本地听音频。`docs/studio-contract-and-privacy.md:17–19` 区分本地媒体与允许发送的派生证据。 |

**我改变了哪些看法**

- **G1补充实施顺序：**先盘点已有审片分析代码，再确定复用和替换边界；不能按全仓从零开始估算。
- **G3收窄措辞：**固定页面文案没有证明自动分析已实现；全仓已有启发式分析是另一项事实。
- **G1配合方案补充：**接受 Essentia和 transformers CLAP 两条候选；两个原始 CLAP包的依赖冲突，比我首轮说明得更具体。

**仍然坚持的分歧**

- **旁挂试点不必先升级曲目v2。**约束只作用于曲目对象；升级还涉及索引读取与一致性。证据：`schemas/music-track.schema.json:6`；`scripts/music_library/library.py:64–75`。
- **综合稿必须删除“全仓无分析代码”和“文件夹入口不读标签”。**反例：`scripts/review_output_video.py:922–1040`；`scripts/import_music.py:28–35`。
- **三首足以开始人工标签和分析试点，尚不足以证明自动标签系统值得建设。**这是优先级推断，不能写成“标签没有实际用处”的已核实事实。证据：[当前接口](http://127.0.0.1:8765/api/review/music)；PRD `:72`。

本轮无文件修改、安装或服务启动；业务仓库保留既有改动，Harness SSOT 工作区干净。