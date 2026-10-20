# R223 阶段 A3 汇报

**当前为部分完成，未达到 A3 通过条件。** 已实现指定的平滑、三分位和最短段合并算法，三首真实歌曲重算、保护核验、导出均通过；两个指定合成红例在严格执行算法后仍失败。原因是等值分位与验收期望冲突，详见下文，未放宽断言或添加清单之外的切段规则。

工作在原 R223 worktree，基于 A2 提交 `02a9606`。未推送、未合并，未访问、启动或停止 8765，未迁移真实曲库，未做阶段 B。

## 实现与清单

修改 `scripts/music_analysis/worker.py`：

- 相邻重拍之间按半开区间取各拍 `beat_energy` 平均；首个重拍前有拍则单列前奏小节，无拍则并入第一小节。
- 从清单读 `smooth_bars`，以本节为中心平均，首尾缩短窗口。偶数窗口多取前侧一个邻居：4 小节为前 2、本节、后 1。
- 按平滑值的本曲三分位，严格低于下分位为 quiet，严格高于上分位为 peak，其余为 build。
- 从清单读 `min_bars`，每次选最短段，等长选靠前；按小节数加权的平滑平均能量选更近的邻段，距离相同选更长者，再相同选前段；沿用接收段类型，每次合并后连起相邻同类型段。
- 内部边界在小节开头，首段从 0 开始，末段到曲长。数字 4 未写死在 worker 中。

`music-analysis.registry.json` 保持未发布的 v1，修订第一条 changelog，`sections.rules` 为：

```json
{"levels":"按平滑后的小节能量在本曲内三等分","smooth_bars":4,"min_bars":4,"merge":"先并最短的段，并入能量更接近的相邻段"}
```

清单 schema 和校验器要求两项计数为正整数，覆盖缺失、零、负数、小数、布尔、字符串和 null；连 `4.0` 也拒绝。分析 README 同步说明算法。设计稿快照已用以下命令重新生成：

```text
.venv/bin/python docs/tasks/R223-music-beat-map/mock/make_registry_js.py
exit 0
```

## 红例与未解决的冲突

先创建 `tests/test_r223_sections.py`，在修改生产算法前运行两个红例：

```text
.venv/bin/python -m pytest -q tests/test_r223_sections.py -k 'synthetic_audio or alternating_bars'
exit 1
2 failed, 15 deselected in 0.60s
```

结构例实际生成并读取临时 WAV，安静、响、中等、响各 16 小节；断言仍为 `[quiet, peak, build, peak]`、内部边界误差不超过 1 小节。交替例仍断言最长段不超过全曲 60%。覆盖、首尾相接、类型和边界断言全部保留。另有前奏、小节均值、窗口首尾缩短、清单参数生效、最短优先、能量距离、等距选长段及合并类型测试。

严格实现后的结果：

```text
.venv/bin/python -m pytest -q tests/test_r223_sections.py
exit 1
2 failed, 20 passed in 2.52s
```

两项失败不能仅靠修正合并顺序消除：

1. 四段恒定小节能量 `[0.1×16, 0.9×16, 0.5×16, 0.9×16]` 经 4 小节平滑，上分位为 0.9，所有值均不高于 0.9。严格 `>` 得不到 peak，输出 quiet、build，无法满足四段类型期望。
2. `[0.2, 0.8]×32` 经平滑后，内部全部为 0.5，上下分位均为 0.5，平滑标准差为 0.017678。短暂边缘段合并后为一个 build，占全曲 100%，无法同时满足“同类型相邻段连起来”和“任何段不超过 60%”。原始小节标准差为 0.3，不能混同平滑标准差。

已提出两项取舍，尚未收到答复：非恒定曲目是否采用包含等号的分档，并在上下分位相同时统一 build；交替例是否允许平滑标准差 <0.05 的均匀曲目为单段，或授权额外切段规则。在答复前保留明确指定的严格算法与原断言，不把失败报告为通过。数值复现见 `a3/equal-energy-conflicts.json`，旧算法红例及新算法日志均保留。

## 真实曲库结果与保护核验

三首均使用修改后的阶段 A worker 完整重跑 beat 和 tags，先暂存仓库外，校验后原子覆盖每首目录的 `analysis.json`。三首 beat、tags 全为 done，derive 显示标签与既有分数夹具期望 3/3 一致。

写前记录曲库全部 86 个文件的 SHA-256 和 `mtime_ns`，分析完成写入前再次核对；写入、导出后再次核对：**83 个受保护文件哈希及修改时间全部未变，没有新增或删除文件，只有三份 analysis.json 被覆盖。** `track.json`、`index.json`、`peaks.json`、音频及 `.attempts/` 均未改动。完整前后快照和旧分析备份在仓库外 `~/.photo-content-os/r223/a3/`。

原始及导出拍点、重拍均严格递增，重拍为拍点子集；能量长度与范围、连续覆盖、内部边界及导出 10 字段/3 位小数形状通过。所有原始小节能量标准差都大于 0.05，三首最长段仍均小于 50%，没有使用低标准差例外。

下列平均能量均为段内各小节原始归一化拍能量均值的算术平均；合并决策使用平滑能量，不混淆两者。

| 歌曲 | BPM / 每小节拍数 | 段数 | quiet 均值 | peak 均值 | 原始 / 平滑小节标准差 | 最长段占比 |
| --- | --- | --- | --- | --- | --- | --- |
| Turn Back Time | 115 / 4 | 10 | 0.498529 | 0.821753 | 0.243160 / 0.193476 | 16.48% |
| Fever Pitch | 125 / 4 | 10 | 0.290323 | 0.864987 | 0.333748 / 0.286275 | 18.57% |
| CRUSH VIBE | 143 / 4 | 9 | 0.306742 | 0.851347 | 0.314749 / 0.273542 | 17.21% |

### Turn Back Time

| 类型 | 开始（秒） | 结束（秒） | 平均能量 |
| --- | --- | --- | --- |
| quiet | 0.000 | 20.880 | 0.270427 |
| build | 20.880 | 37.560 | 0.814982 |
| quiet | 37.560 | 54.280 | 0.511478 |
| peak | 54.280 | 70.960 | 0.860133 |
| build | 70.960 | 89.740 | 0.783640 |
| peak | 89.740 | 106.420 | 0.797547 |
| quiet | 106.420 | 121.060 | 0.553042 |
| peak | 121.060 | 137.740 | 0.862414 |
| quiet | 137.740 | 158.620 | 0.678111 |
| peak | 158.620 | 189.924 | 0.797382 |

### Fever Pitch

| 类型 | 开始（秒） | 结束（秒） | 平均能量 |
| --- | --- | --- | --- |
| quiet | 0.000 | 21.300 | 0.449957 |
| peak | 21.300 | 29.040 | 0.906396 |
| build | 29.040 | 36.800 | 0.804356 |
| peak | 36.800 | 48.400 | 0.849616 |
| quiet | 48.400 | 71.640 | 0.236048 |
| build | 71.640 | 83.240 | 0.600830 |
| peak | 83.240 | 108.400 | 0.878428 |
| build | 108.400 | 116.140 | 0.721759 |
| peak | 116.140 | 127.760 | 0.823630 |
| quiet | 127.760 | 135.484 | 0.069388 |

### CRUSH VIBE

| 类型 | 开始（秒） | 结束（秒） | 平均能量 |
| --- | --- | --- | --- |
| quiet | 0.000 | 16.520 | 0.222246 |
| peak | 16.520 | 29.760 | 0.838508 |
| build | 29.760 | 44.640 | 0.760666 |
| peak | 44.640 | 56.220 | 0.858524 |
| build | 56.220 | 62.840 | 0.822486 |
| quiet | 62.840 | 69.460 | 0.607842 |
| peak | 69.460 | 76.080 | 0.865882 |
| build | 76.080 | 89.340 | 0.782541 |
| quiet | 89.340 | 96.000 | 0.238008 |

Turn Back Time 的开头 quiet 从原来的约 162.8 秒缩到 20.88 秒；CRUSH VIBE 从约 47.9 秒缩到 16.52 秒。上述检查证明本次三首数据的能量与边界条件，不代表未解决的恒定能量测试已通过。

导出由 `load_beat_map` 生成，已覆盖并重新读回核对；不进入仓库：

- Turn Back Time：`~/.photo-content-os/r223/beat-maps/2bdff650a03a4e1f25ee07b00d034474aaa9c48c45834dd6f8ff306b4e1128af.json`
- Fever Pitch：`~/.photo-content-os/r223/beat-maps/891759d6a9fc3c501f15c643026d272c602b4d1878daada6f0e5bf74ad061d0b.json`
- CRUSH VIBE：`~/.photo-content-os/r223/beat-maps/e60863568554f0fe6feec9ce1d9c8999dfd10ed8d2b0662d32d872fecd277256.json`

分析、发布一次性脚本均在仓库外，未新增仓库内真实曲库批处理入口。数值、侧车及导出哈希见 `evidence/2026-10-21/R223-music-beat-map/a3/real-library-verification.json`。

## 测试与检查

普通回归使用临时 `LOCAL_MEDIA_ROOT`，显式设置 `OBSIDIAN_ROOT` 和 `UI_COPY_QUALITY_CHECKER`。命令、退出码及输出保存在同目录 `a3/` 日志，仅替换本机路径。

| 命令 | 退出码 | 原样结果摘要 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r223_sections.py` | 1 | `2 failed, 20 passed in 2.52s` |
| `.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_p1_openclaw_bridge.py tests/test_desktop_openapi_route_sync.py` | 0 | `63 passed, 4 subtests passed in 9.60s` |
| `R223_RUNTIME_TESTS=1 .venv/bin/python -m pytest -q tests/test_r223_music_analysis_runtime.py` | 0 | `1 passed in 79.78s (0:01:19)` |
| `bash scripts/check_runtime_contract.sh` | 0 | `Runtime contract check passed.` |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 0 | `music-analysis-registry OK: 126 ids; 121 copy entries` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 0 | `Repository safety check passed.` |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 1 | 三组 `source doc is newer than Obsidian target; sync required` |
| `.venv/bin/python scripts/check_outline_contract.py .` | 1 | 同一 Obsidian 检查非零退出 |
| `.venv/bin/python -m pytest -q tests` | 1 | `12 failed, 820 passed, 33 skipped, 6 errors, 2003 subtests passed in 317.78s (0:05:17)` |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 0 | help 正常 |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 0 | help 正常 |

全量结果中两项为本次尚未解决的等值能量红例；其余 10 failed / 6 errors 与 A2 相同：FFmpeg 缺少 drawtext、既有工具软链接路径断言、三组 Obsidian 同步时间检查。未修改这些范围外实现或门禁，未宣称全局 READY。

真实分析、保护检查、导出一次性命令及原样输出见 `a3/real-analysis.log`、`a3/publish.log`。未重新执行 A 阶段的 HTTP 全链路合成曲库验证；A3 未改接口、队列或 HTTP 路由，已运行相关专项回归与离线真实模型回归。

## 提交与停止

本次改动和证据在原 worktree 内提交，Request / Verify 末两行沿用任务单；未推送、未运行 finish，保留 worktree。业务仓库提交后仅余未跟踪的 `.venv`、`.tools` 环境软链接。`task_worktree.py check` 因用户要求保留未合并提交及本地环境链接而退出 1，未为清除提示而合并或移除环境。

Harness SSOT 未修改；其仓库仍有 11 项既有改动/未跟踪项，状态记录在 `a3/harness-status.txt`。人工验收记录未改，本次没有创建或修改声明式 SSOT 开发包。

按要求停止。A3 尚需决定两处等值能量规则，才能让两个指定红例转绿。
