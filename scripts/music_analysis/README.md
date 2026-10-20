# 本机音乐分析

安装：`MUSIC_ANALYSIS_PYTHON=python3.12 python3 scripts/setup_edit_tools.py --music-analysis`。Shell / PowerShell 包装入口将同一参数交给 Python 安装器。环境位于 `.tools/music-analysis/`，不会安装进 Studio 的 `.venv`。固定包版本、beat 权重和四个分类头类别元数据的哈希见 `third_party/edit-tools.lock.json`；五个 MTG 图文件的地址、哈希和许可见根目录音乐清单。

`worker.py` 用一行 JSON 从标准输入读 `audio`（本地文件）、`duration_seconds`、`part`（`all`、`beat` 或 `tags`），向标准输出写 JSON；诊断写标准错误。只有安装器联网，worker 禁止 socket 连接，并在加载前校验本地权重及类别元数据的哈希。Studio 用专用解释器启动子进程，整首超时 180 秒；音频解码上限 60 秒。

每首曲目目录的 `analysis.json` 是唯一分析结果，按 `schemas/music-analysis.schema.json` 验证并原子替换；`track.json` 和索引只接受 v2。节拍和标签独立成功或失败。排队与分析中状态由 Studio 的串行队列投影；处理失败的结果持久保存，缺失结果在启动时补排。未知失败代号原样返回。损坏或不可读的结果报错，不能当作缺失。

拍点取 beat-this 的实测输出。每拍 RMS 使用 librosa，按整曲 5%–95% 分位归一到 0–1。小节为相邻实测重拍之间的半开区间，能量是其中各拍能量的平均。第一个重拍之前有拍则单列前奏小节，没有拍则将这段时间并入第一小节。

段落规则只读清单 `sections.rules`：`smooth_bars` 和 `min_bars` 必须是正整数。以本小节为中心做 `smooth_bars` 小节滑动平均，首尾截短窗口；偶数窗口多取前侧一个邻居（4 小节即前 2、本节、后 1）。按平滑值的本曲三分位分档，低于下分位为 quiet，高于上分位为 peak，其余为 build。

短于 `min_bars` 的段每次选择最短者，等长取靠前者；按小节数加权的平滑能量平均值，选择能量更接近的邻段，距离相同选更长者，再相同选前段。合并后沿用接收段的类型，连起相邻同类型段后再选下一段。内部边界落在小节开头，第一段从 0 开始，最后到曲长结束。段名只读清单。

四个分类头保存全部原始分数，按片段平均后降序存储，数量依次为 genre 400、moodtheme 56、instrument 40、voice 2。显示标签通过 `studio.music_analysis.derive` 按当前清单现算；不会因为改中文名、阈值或状态重跑模型。新增分类头或更换模型后的整库重算由清单治理流程安排。

`GET /api/review/music` 提供当前 `registry_version`、`taxonomy` 和每首的 `beat` / `tags`。`taxonomy.sections` 是清单的 `sections.kinds` 数组，`tag_categories` 保留编号、名字、状态及空/不确定文案，`display` 原样提供。列表不返回原始分数。

`POST /api/review/music/<trackId>/reanalyze` 的 JSON 请求体为 `{"part":"beat"}` 或 `{"part":"tags"}`，沿用 Studio 的 Origin 与 CSRF 保护。同一部分重复点击合并；只重跑请求的部分。队列位置从 0 起，表示前面还有多少首。

R226 的后端只读接口严格遵循 `docs/tasks/R223-music-beat-map/DESIGN.md` 第 10.1 节：

```python
def load_beat_map(track_id: str, *, media_root: Path | None = None) -> dict: ...
class BeatMapUnavailable(Exception):
    code: str          # unknown_track | queued | analyzing | beat_failed | result_unreadable
    track_id: str
    failure_code: str | None   # code == "beat_failed" 时是分析记下的失败码，原样给出
```

返回字段为 `track_id`、`title`、`duration_seconds`、`bpm`、`meter`、`beats`、`downbeats`、`beat_energy`、`sections`、`registry_version`，不带标签、状态、包信息或额外字段。时间是歌曲自身的秒数，保留 3 位小数；能量取值为 0–1。第 k 小节从 `downbeats[k-1]` 开始；重拍是拍点子集；能量长度等于拍点长度；段落首尾相接，从 0 覆盖到曲长。BPM 用相邻拍间隔中位数，拍号用相邻重拍之间拍数的众数。

函数只读取曲目身份/标题/时长和分析文件，并观察进程内已有队列状态；不创建目录或写锁、不排队、不启动 worker。缺失分析结果报 `queued`，已有队列处理中报 `analyzing`，分析记录的节拍失败报 `beat_failed` 并原样带出 `failure_code`。未知曲目报 `unknown_track`；文件无法解析、字段不全、没有足够重拍、时间形状损坏或取 3 位小数后形状失效报 `result_unreadable`。不会返回空数组或缺字段的半成品；标签失败不阻碍读取完整节拍。


验证：普通回归运行 `tests/test_r223_music_analysis.py`；安装模型后用 `R223_RUNTIME_TESTS=1 .venv/bin/python -m pytest -q tests/test_r223_music_analysis_runtime.py` 验证真实点击音轨。完整 HTTP 路径用 `.venv/bin/python scripts/music_analysis/verify_runtime.py --evidence-dir evidence/<日期>/<任务>`，只生成和读取自己的合成音频，服务端口自动分配，不使用 8765。
