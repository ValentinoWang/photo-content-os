# R223 阶段 A2 汇报

四项已完成：读取接口对齐、Git 跟踪文件扫描修正、真实三首歌曲分析和导出、worktree 内提交。未推送，未迁移曲库，未启动、停止或访问 8765，未做阶段 B。

工作区：`/private/tmp/task-worktrees/photo-content-os-r223-music-beat-map`。开工已重读其中更新后的 `DESIGN.md` 第 10.1 节和 `TASK.md`；输入文件哈希记录在 `evidence/2026-10-21/R223-music-beat-map/a2/inputs.json`。

## 1. 读取接口按约定修正

修改 `studio/music_analysis.py`、`tests/test_r223_music_analysis.py`、`scripts/music_analysis/README.md`：

```python
def load_beat_map(track_id: str, *, media_root: Path | None = None) -> dict: ...
class BeatMapUnavailable(Exception):
    code: str          # unknown_track | queued | analyzing | beat_failed | result_unreadable
    track_id: str
    failure_code: str | None
```

- 只返回 `track_id`、`title`、`duration_seconds`、`bpm`、`meter`、`beats`、`downbeats`、`beat_energy`、`sections`、`registry_version`，不带标签或额外字段。
- 时间是歌曲自身秒数，取 3 位小数；能量为 0–1。第 k 小节从 `downbeats[k-1]` 开始；重拍为拍点子集；能量数组长度等于拍点数；段落首尾相接，覆盖 0 到曲长。BPM 和拍号按设计第 6 节计算。
- 缺失结果及排队报 `queued`，处理中报 `analyzing`，节拍失败报 `beat_failed` 并原样保留未知 `failure_code`；未知曲目报 `unknown_track`，结果损坏或不完整报 `result_unreadable`。
- 取小数前后都检查形状，不返回空数组、缺字段或精度处理后损坏的半成品。标签失败不阻挡完整节拍读取。
- 只读曲目身份/标题/时长及分析文件，观察已有进程内队列；不写文件、不建曲库锁、不排队、不启动 worker。曲库一般读写入口仍只认 v2，此函数不迁移元数据。
- 已删除 `read_rhythm`，没有别名。当前代码只剩证明旧入口不存在的负例断言；历史 REPORT-A 保留。

五种异常 code 均有测试，另覆盖只读、损坏 JSON、缺字段、空数组、错误时间/能量/重拍/段落、3 位小数导致拍点重合，以及标签失败时仍可读取节拍。

## 2. 扫描只针对 Git 跟踪的 Python 文件

修改 `tests/test_p1_openclaw_bridge.py`：使用 `git ls-files -t -z -- '*.py'` 取得输入。稀疏检出中未落盘的跟踪文件读取 Git 索引内容，不直接跳过；普通文件读不到、Git 出错或零输入仍失败。

负例在临时 Git 仓库中创建真实目录 `.tools/music-analysis/`，放入未跟踪的 Python 2 语法 `.py`：单独解析会报 `SyntaxError`，新扫描不受影响。随后向跟踪文件加入禁止的导入，扫描仍能检出；稀疏检出情形也能检出，没有削弱原断言。

还用新扫描函数只读检查了主目录：`.tools` 确认为真实目录，267 个 Git 跟踪 Python 文件扫描通过，无强制 `openclaw_media` 导入。记录见 `a2/main-source-scan.json`。

## 3. 真实曲库分析结果

使用未改动的阶段 A `scripts/music_analysis/worker.py`，专用环境离线分析三首音频；校验后用同阶段的原子 JSON 写法新增每首目录的 `analysis.json`。

写前记录曲库原有 83 个文件的 SHA-256 和修改时间；分析、导出后再次核对，83 个全部未变，仅多出三份 `analysis.json`。音频只读，`track.json`、`index.json`、`peaks.json`、`.attempts/` 均未改动；曲库仍为 v1，没有运行迁移。

三首 `beat`、`tags` 全为 `done`。原始和导出时间戳均递增且不超曲长，重拍为拍点子集，能量长度/范围及段落连续覆盖通过；每首保存 400 / 56 / 40 / 2 个完整原始分类分数。

| 歌曲 | BPM | 每小节拍数 | 段落数 | 拍点 / 重拍数 |
| --- | --- | --- | --- | --- |
| Turn Back Time | 115 | 4 | 2 | 369 / 94 |
| Fever Pitch | 125 | 4 | 6 | 280 / 71 |
| CRUSH VIBE | 143 | 4 | 4 | 239 / 61 |

这里的 BPM 来自 beat-this 的实测拍点，未沿用设计稿的 librosa 临时估算值。

显示标签：

| 歌曲 | 风格与细分 | 情绪 | 场景 | 人声 | 乐器 |
| --- | --- | --- | --- | --- | --- |
| Turn Back Time | 电子 / Tropical House | 深沉、欢快 | 夏日 | 有人声 | 贝斯、合成器、键盘 |
| Fever Pitch | 电子 / House | 深沉 | 夏日 | 拿不准 | 贝斯、合成器、键盘 |
| CRUSH VIBE | 电子，无细分 | 旋律优美、太空感、暗黑 | 空 | 纯音乐 | 合成器、采样器 |

`derive()` 的显示结果与 `tests/fixtures/r223/scores.json` 的期望 **3/3 完全一致**。原始分数并非逐值相等：对夹具保留的 genre / moodtheme / instrument 各 8 项、voice 2 项逐项比较，最大绝对差如下（0–1 分数，表中保留 6 位小数）：

| 歌曲 | genre | moodtheme | instrument | voice |
| --- | --- | --- | --- | --- |
| Turn Back Time | 0.006004 | 0.003641 | 0.009051 | 0.004051 |
| Fever Pitch | 0.009485 | 0.004009 | 0.015237 | 0.009639 |
| CRUSH VIBE | 0.003017 | 0.004000 | 0.002658 | 0.005142 |

使用相同的五份模型及校验值。本次沿用阶段 A 的 FFmpeg 单声道 22050 Hz 解码、再重采样至 16000 Hz 的标签链路，未重放夹具生成环境；没有把差值归结为已经验证过的单一原因，也未修改分数或阈值来凑期望。完整差值和验证记录见 `a2/real-library-verification.json`。

## 4. 给 R226 的一次性导出

直接调用新的 `load_beat_map` 导出，逐份重新读回并核对全部 10 个字段、3 位小数、BPM/拍号公式及形状。导出 JSON 不含标签，均在仓库外：

- Turn Back Time：`~/.photo-content-os/r223/beat-maps/2bdff650a03a4e1f25ee07b00d034474aaa9c48c45834dd6f8ff306b4e1128af.json`
- Fever Pitch：`~/.photo-content-os/r223/beat-maps/891759d6a9fc3c501f15c643026d272c602b4d1878daada6f0e5bf74ad061d0b.json`
- CRUSH VIBE：`~/.photo-content-os/r223/beat-maps/e60863568554f0fe6feec9ce1d9c8999dfd10ed8d2b0662d32d872fecd277256.json`

分析和导出为一次性命令，没有新增仓库内批处理脚本，也没有把音频、完整分析文件或导出 JSON 加入 Git。导出文件哈希和大小记录在 `a2/real-library-verification.json`。

## 5. 测试命令和结果

普通检查使用临时 `LOCAL_MEDIA_ROOT`，显式设置 `OBSIDIAN_ROOT`、`UI_COPY_QUALITY_CHECKER`。日志保留命令结果，仅替换本机路径；位于 `evidence/2026-10-21/R223-music-beat-map/a2/`。

专项原样输出：

```text
.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_p1_openclaw_bridge.py tests/test_desktop_openapi_route_sync.py
exit 0
63 passed, 4 subtests passed in 8.18s
```

真实分析一次性命令及输出：

```text
.venv/bin/python /tmp/r223-a2-analyze-once.py
exit 0
Turn Back Time beat=done tags=done labels_match=True elapsed=17.43
Fever Pitch beat=done tags=done labels_match=True elapsed=19.1
CRUSH VIBE beat=done tags=done labels_match=True elapsed=16.19
existing files unchanged: 83 new analysis.json: 3
```

导出后的独立校验原样输出：

```text
.venv/bin/python -
exit 0
3/3 beat+tags done; labels match; exported shape verified; original 83 files unchanged; only 3 analysis.json added
```

| 命令 | 退出码 | 结果 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_p1_openclaw_bridge.py tests/test_desktop_openapi_route_sync.py` | 0 | `63 passed, 4 subtests passed in 8.18s` |
| `bash scripts/check_runtime_contract.sh` | 0 | `Runtime contract check passed.` |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 0 | `music-analysis-registry OK: 126 ids; 121 copy entries` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 0 | `Repository safety check passed.` |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 1 | `3 组 source doc is newer than Obsidian target` |
| `.venv/bin/python scripts/check_outline_contract.py .` | 1 | `因同一 Obsidian 检查非零退出` |
| `.venv/bin/python -m pytest -q tests` | 1 | `10 failed, 800 passed, 33 skipped, 6 errors, 2003 subtests passed in 230.83s (0:03:50)` |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 0 | `help 正常` |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 0 | `help 正常` |

全局失败仍为阶段 A 已记录的范围外问题：FFmpeg 缺少 `drawtext` 的字幕/视频测试、既有剪辑后端解析工具软链接后的路径断言、三组 Obsidian 文档时间检查。未修改这些实现、测试、协议或门禁；不宣称全局 READY。

## 6. 提交与停止

本次仅修改四个实现/文档/测试文件，另补 `REPORT-A2.md` 和 A2 文字证据；已在同一 worktree 提交，Request / Verify 尾行与阶段 A 相同。未推送，worktree 保留；本地 `.venv`、`.tools` 软链接不提交。

Harness SSOT 未修改；检查时存在 11 项既有改动/未跟踪项，记录在 `a2/harness-status.txt`。既有人工验收记录未变，未创建声明式 SSOT 开发包。

阶段 A2 汇报至此，停止，等待 Claude 复核。
