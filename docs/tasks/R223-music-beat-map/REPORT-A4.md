# R223 阶段 A4 汇报

A4 的分档修正、段落测试、真实三首核算已完成。`tests/test_r223_sections.py` 全绿，A3 表中的全部检查已重跑；全局检查仍有下文列出的既有范围外失败。已在原 worktree 提交，未推送、未合并，未访问、启动或停止 8765，未迁移曲库，未做阶段 B。

## 修改内容

`worker.py` 按新规格分档：平滑值不高于下分位为 quiet，不低于上分位为 peak，其余为 build；上下分位之差小于 `1e-9` 时整曲为 build。小节、平滑窗口、最短段合并及边界规则保持不变。

清单保持 v1，更新第一条 changelog，`sections.rules.levels` 为：

> 按平滑后的小节能量在本曲内三等分：不高于下分位为安静，不低于上分位为高潮，其余为推进；上下分位相同时全曲为推进

分析 README 同步更新，并用 `make_registry_js.py` 重新生成设计稿清单快照。

两个矛盾期望已替换，没有 skip 或 xfail。测试覆盖：

- 三个平台各 16 小节，振幅 0.1、0.9、0.5；实际生成并读取 WAV，期望 quiet、peak、build，内部边界误差不超过 1 小节。
- 全曲等响、分位差小于 `1e-9` 均为一个 build；分位等值明确验证包含等号。
- `[0.2, 0.8]×32` 的内部平滑值为 0.5，整曲一个 build。
- 四个平台各 20 小节，0.15、0.85、0.5、0.85，加 ±0.1 均匀抖动，固定种子 `20261021`：新算法最长段占 **27.5%**，首段 quiet，包含 **3 段 peak**，满足不超过 40% 的断言。
- 同一数据运行 A2 算法，最长段占 **41.25%**，明确违反 40% 上限。旧函数保存为仅供测试的 `tests/fixtures/r223/section_map_a2.py`，已核对与 A2 提交 `02a9606` 的函数源码完全一致；测试不依赖运行时 Git 历史。
- 其余覆盖、首尾相接、类型、小节边界、清单正整数校验及合并断言保留。

## 真实曲库是否变化

仅使用已有拍点及能量重算 sections，**没有重跑真实歌曲模型，拍点、重拍、beat_energy、标签分数及其他分析字段全部不变**。

| 歌曲 | 段落是否变化 | 段数 | analysis.json | beat-maps 导出 |
| --- | --- | --- | --- | --- |
| Turn Back Time | 有：第一处边界 20.88 → 22.96 秒 | 10 | 原子覆盖 | 更新 |
| Fever Pitch | 不变 | 10 | 未写入 | 未写入 |
| CRUSH VIBE | 不变 | 9 | 未写入 | 未写入 |

Turn Back Time 新段落如下。平均能量为段内各小节原始归一化拍能量均值的算术平均，时间单位为秒。

| 类型 | 开始 | 结束 | 平均能量 |
| --- | --- | --- | --- |
| quiet | 0.000 | 22.960 | 0.329601 |
| build | 22.960 | 37.560 | 0.799788 |
| quiet | 37.560 | 54.280 | 0.511478 |
| peak | 54.280 | 70.960 | 0.860133 |
| build | 70.960 | 89.740 | 0.783640 |
| peak | 89.740 | 106.420 | 0.797547 |
| quiet | 106.420 | 121.060 | 0.553042 |
| peak | 121.060 | 137.740 | 0.862414 |
| quiet | 137.740 | 158.620 | 0.678111 |
| peak | 158.620 | 189.924 | 0.797382 |

写前、写后核对曲库 86 个文件的 SHA-256 和 `mtime_ns`：仅 Turn Back Time 的 `analysis.json` 改变，**其余 85 个文件全部不变**；没有新增或删除文件。包括另外两首 `analysis.json`，以及所有音频、track.json、index.json、peaks.json、.attempts。另外两份仓库外导出的哈希与修改时间也均不变。

三首的 beat、tags 仍为 done。导出重新读回与 `load_beat_map` 相等，10 字段及递增拍点/重拍子集检查通过。每首 peak 小节平均能量仍高于 quiet，最长段均小于全曲 50%：

| 歌曲 | quiet 均值 | peak 均值 | 小节能量标准差 | 最长段占比 |
| --- | --- | --- | --- | --- |
| Turn Back Time | 0.510273 | 0.821753 | 0.243160 | 16.48% |
| Fever Pitch | 0.290323 | 0.864987 | 0.333748 | 18.57% |
| CRUSH VIBE | 0.306742 | 0.851347 | 0.314749 | 17.21% |

导出路径：

- Turn Back Time：`~/.photo-content-os/r223/beat-maps/2bdff650a03a4e1f25ee07b00d034474aaa9c48c45834dd6f8ff306b4e1128af.json`
- Fever Pitch：`~/.photo-content-os/r223/beat-maps/891759d6a9fc3c501f15c643026d272c602b4d1878daada6f0e5bf74ad061d0b.json`
- CRUSH VIBE：`~/.photo-content-os/r223/beat-maps/e60863568554f0fe6feec9ce1d9c8999dfd10ed8d2b0662d32d872fecd277256.json`

一次性命令为 `.venv/bin/python /tmp/r223-a4-recompute-sections.py`，退出码 0。完整前后文件快照及被覆盖文件的备份在仓库外 `~/.photo-content-os/r223/a4/`；仓库内数值与保护证据见 `evidence/2026-10-21/R223-music-beat-map/a4/real-library-verification.json`、`recompute.log`。

## 全部检查结果

先确认段落专项全绿，再执行其余检查。普通回归使用临时 `LOCAL_MEDIA_ROOT`，显式设置 `OBSIDIAN_ROOT` 和 `UI_COPY_QUALITY_CHECKER`。离线模型回归只使用临时合成点击音轨。

以下为命令、退出码及原样输出中的结果行；完整 stdout/stderr 在 `a4/<检查名>.log`，仅替换本机路径。

| 命令 | 退出码 | 结果行 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/test_r223_sections.py` | 0 | `28 passed in 0.46s` |
| `.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py tests/test_p1_openclaw_bridge.py tests/test_desktop_openapi_route_sync.py` | 0 | `63 passed, 4 subtests passed in 5.35s` |
| `R223_RUNTIME_TESTS=1 .venv/bin/python -m pytest -q tests/test_r223_music_analysis_runtime.py` | 0 | `1 passed in 35.76s` |
| `bash scripts/check_runtime_contract.sh` | 0 | `Runtime contract check passed.` |
| `.venv/bin/python scripts/validate_music_analysis_registry.py` | 0 | `music-analysis-registry OK: 126 ids; 121 copy entries` |
| `.venv/bin/python scripts/check_repository_safety.py --base origin/main` | 0 | `Repository safety check passed.` |
| `.venv/bin/python scripts/check_obsidian_doc_sync.py` | 1 | `Obsidian 文档同步检查失败：` |
| `.venv/bin/python scripts/check_outline_contract.py .` | 1 | `subprocess.CalledProcessError: Command '['$HOME/Desktop/创业项目/photo-content-os/.venv/bin/python', '$WORKTREE/scripts/check_obsidian_doc_sync.py', '--local-root', '$WORKTREE']' returned non-zero exit status 1.` |
| `.venv/bin/python -m pytest -q tests` | 1 | `10 failed, 828 passed, 33 skipped, 6 errors, 2003 subtests passed in 176.31s (0:02:56)` |
| `.venv/bin/python scripts/validate_content_os_task.py --help` | 0 | `usage: validate_content_os_task.py [-h] --task TASK --vault-root VAULT_ROOT` |
| `.venv/bin/python scripts/validate_jianying_draft.py --help` | 0 | `usage: validate_jianying_draft.py [-h] [--plan PLAN] [--result RESULT]` |

Obsidian 三组既有失败对应：

```text
local_execution_to_obsidian_collaboration_v2: source doc is newer than Obsidian target; sync required
local_execution_to_obsidian_editing_handoff_v2: source doc is newer than Obsidian target; sync required
historical_jianying_evidence_is_not_production: source doc is newer than Obsidian target; sync required
```

全量失败与 A2 的 10 failed / 6 errors 相同：FFmpeg 缺少 drawtext 导致字幕/视频检查失败，既有工具软链接路径断言失败，以及 Obsidian 时间检查失败。A3 两个矛盾期望已消除，段落专项 28 项全部通过。未改动范围外实现、基线或人工记录，不宣称全局 READY。

补充验证：生成 `mock/registry.js` 的命令退出 0；源码及结构化文件的 `git diff --check` 通过；分位等值负例在修正前为 `1 failed, 27 deselected in 0.53s`，修正后纳入全绿专项。防滚雪球的新旧数字与旧函数来源核对见 `a4/snowball-proof.json`。

## 提交与状态

在原 worktree 提交本次实现、测试、快照、证据及 REPORT-A4.md，提交末两行为任务指定的 Request / Verify（H-01、H-02、H-03）。未推送、未运行 finish；业务 worktree 仅保留未跟踪的 `.tools`、`.venv` 环境软链接。`task_worktree.py check` 因按要求保留未合并提交及环境链接返回 1。

本次未编辑 Harness SSOT 源码或规则。其仓库开工记录 11 项改动/未跟踪项，收尾记录 33 项，增加的是控制台生成物；两次状态见 `a4/harness-status.txt`、`a4/harness-status-final.txt`。既有人工验收日志未改；本次没有声明式 SSOT 开发包，不涉及 Obsidian SSOT 快照。

按要求停止。
