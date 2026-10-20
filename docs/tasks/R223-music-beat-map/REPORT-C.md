# R223 阶段 C 汇报

## 两处修改和验证

重新分析接口已按 DESIGN 10.1 修正：非法 part 返回 HTTP 400 / `music_part_invalid`；曲目不存在返回 HTTP 404 / `music_track_not_found`；CSRF 与来源校验继续返回 HTTP 403 / `csrf_invalid`、`origin_forbidden`。错误体均为 `{"ok":false,"error":{"code":"…","message":"…"}}`。

修改 `studio/server.py`、`studio/api_contract.py`，按现有 `scripts/export_studio_openapi.py` 重新生成契约。JSON 语义对比确认只有 `reanalyzeMusic` 这一操作改变；生成器同时规范了 JSON 排序，没有修改其他接口。

```text
.venv/bin/python -m pytest -q tests/test_r223_music_analysis.py -k 'reanalyze_error_contract or http_projection' tests/test_desktop_openapi_route_sync.py
7 passed, 55 deselected in 4.58s

.venv/bin/python -m pytest -q tests/test_desktop_openapi_route_sync.py
1 passed in 0.07s

.venv/bin/python scripts/export_studio_openapi.py --check
exit 0
PASS OpenAPI: only reanalyzeMusic changed
```

错误契约覆盖三种非法 part 输入、未知曲目、错误令牌、非法来源，逐项断言 HTTP 状态、错误码、完整返回形状及生成后的 OpenAPI schema；拒绝请求不入队。

Claude 新增的 DESIGN 第 6 节「标签排列顺序」与现有实现一致：组内计数降序，同数沿 taxonomy 顺序。该行已提交；另在实际挂载页面中增加排序断言，反转 taxonomy 后仍按当前清单顺序排列。

```text
node scripts/verify_r223_interactions.mjs
PASS 7 music interaction checks
exit 0
```

本次不改页面样式或产品文案。B 阶段三个前端源文件与已获 Claude 复核的版本逐字节一致，133 张已审阅图像重新核对哈希。另抽看了本轮桌面和手机的工作台、镜头页、部分完成、音乐、诊断页面；不将抽样称为全站审计。

## 三张卡的交付状态

| 卡片 | 合同和机器证据 | handoff 与人工状态 |
|---|---|---|
| 音乐库：AI 给每首歌打标签，并显示节拍图 · 待验收（2026-10-20-R223-photo-music-beat-map） | 新建合同 v1；后端、模型、文案编号、共享模块与七项交互 PASS | ACTIVE、PENDING；H-01–H-03 原样照搬需求卡 |
| 汽水音乐、网易云音乐链接导入并入库 · 待验收（2026-10-19-R210-photo-music-link-import） | 合同 v3；89 项旧卡测试、复制品音频重测和禁止网络的真实 CLI 重复导入 PASS | rebaseline 后 handoff --replace；仍须单独人工验收 |
| Photo Studio 导航整理、挑镜头页和音乐库页 · 待验收（2026-10-20-R220-photo-studio-ia-preview） | 合同 v2；60 项及七个子测试、26 项浏览器走查、29 状态四宽、33 组公式及文案编号 PASS；夹具边界见下 | rebaseline 后 handoff --replace；仍须单独人工验收 |

三个工作区均保留 `未-` 前缀，没有写人工 PASS，没有修改 feedback、人工签署或 `human-operations.jsonl`。生成的验收日志、需求卡投影由管理器更新，未代替人工结论。隔离调度台预览中三张卡均为 ready/ACTIVE/PENDING。

G16 实际识别的重叠只有：

- 导入卡：`tests/test_music_library.py`。
- 导航预览卡：`tests/test_r220_number_formulas.mjs`。

两卡均使用管理器 `rebaseline --base origin/main --head <verified-head> --trigger-card 2026-10-20-R223-photo-music-beat-map --reason …`，保留新旧哈希、时间和旧绑定审计；准备后重跑旧合同完整机器范围，重新 handoff。本卡 `claims.protected_test_overlap` 对这两张卡各声明一次 `rebaseline`，没有加入门禁未识别的卡，也没有 supersede。

旧卡只删除需求卡已经取消的曲目授权要求，导入、去重、会员限制、导航、镜头决定和成片播放责任保持。每项召回关系均补齐 independent 理由；补齐音乐清单与子目录的 surfaces 映射，没有扩大测试豁免。

所有递交引用的机器 PASS、合同摘要、`source_identity`、`source_commit`、`baseline.head` 均绑定同一个最终 verified head。按 Core 定义，后续只包含验收物的提交不推进 verified head；range 的实际 head/tree 仍由交付检查单独记录。报告冻结后重新建立本批绑定和机器运行，不沿用旧源码身份的 PASS。

## check-delivery 原样输出

命令：

```text
python3 "$HARNESS_ROOT/Core/skills/acceptance-handoff/scripts/check_delivery.py" --project-root . --range origin/main..HEAD
exit 1
```

以下保留原样门禁行；完整含批次 head/tree 的最终输出保存在 `agents-results/2026-10-21/r223-delivery/check-delivery-final.log`：

```text
  G1 有卡  FAIL  2026-10-19-R210-photo-music-link-import 阻塞卡未获当前人工通过; 2026-10-20-R220-photo-studio-ia-preview 阻塞卡未获当前人工通过; 2026-10-20-R223-photo-music-beat-map 阻塞卡未获当前人工通过 → 为非豁免提交创建交付验收卡；阻塞卡需用户通过，并遵守切片额度 → python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py handoff <任务根> --project-root . --replace --baseline <基准文件> --claims <声明文件> <原递交参数>；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py repair retired <不可恢复的未通过卡目录> --project-root . --actor <执行者> --reason <原因>
  G2 基准一致  PASS  
  G3 机器先绿  PASS  
  G4 看得懂  PASS  
  G5 有入口  PASS  
  G6 去重已声明  PASS  
  G7 失效传播  PASS  
  G8 坏一条不连累  PASS  
  G9 页面可见  FAIL  2026-10-20-R223-photo-music-beat-map 没有出现在 ready/ACTIVE 投影中 → 重新生成调度台并确认新卡 ready/ACTIVE → python3 tools/console/generate_console.py；python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py check-project --project-root .
  G10 不自证  PASS  
  G11 有需求卡  PASS  
  G12 验收覆盖需求  PASS  
  G13 沿用已有卡  PASS  
  G14 已通过不可变  PASS  
  G15 自动替代完整  PASS  
  G16 不连累前面的卡  PASS  
  G17 真实链路没被替换  FAIL  2026-10-19-R210-photo-music-link-import: gate-unreadable: result_path must be agents-results/<date>/<task>/acceptance/…; 2026-10-20-R220-photo-studio-ia-preview: gate-unreadable: result_path must be agents-results/<date>/<task>/acceptance/…; 诊断与配置异常：缺工具和缺出口使用明确夹具，实际安装状态另有原始失败记录；重查仍请求真实服务。; 异常页面：部分完成、停止、失败、导入限制和空页使用状态夹具，不代表平台或模型曾真实产生这些异常。; 失败恢复与标签改名：使用接口投影和延迟失败夹具；真实播放及实际模型另有独立验证。; 多首节拍图：切点、换歌和淡出在独立宿主夹具中核验，没有生成真实成片。 → 在 handoff 声明 bypasses 并写清没实测的部分，或改为走产品自己的回执续跑路径 → python3 Core/skills/design-acceptance-contract/scripts/manage_acceptance_artifacts.py handoff <任务根> --project-root . --bypasses <声明.json> --replace <原递交参数>；python3 Core/skills/acceptance-handoff/scripts/check_delivery.py --project-root . --range <base>..<head> --read-only
结果：FAIL（本命令如实返回门禁状态；推送策略由调用方应用）
```

G16 已通过，但本批不能称为 READY：

- **G1**：三张 blocking 卡尚无当前人工通过，这是保留真实待验收状态的结果。修法是用户实际验收，执行者不能代签。
- **G9**：正式调度台仍读主目录，尚未整合的 worktree 新卡不在正式快照里。已单独生成 worktree 隔离预览，三卡均 ready/ACTIVE；预览位于 `$HARNESS_ROOT/tools/console/r223-delivery-preview/`。修法是在获准整合主目录后，用正式登记源运行 `python3 tools/console/generate_console.py`，再重跑交付检查。本轮没有为显示新卡而改写主目录或正式项目登记。
- **G17**：当前 Core 扫描器拒绝两张旧卡的 `evidence/.../delivery/acceptance/...` 机器证据根，要求 `agents-results/<date>/<task>/acceptance/...`。两张旧卡的历史根、合同和原运行都保留；没有手工搬动历史或修改 Core 来绕过。修法是由交付规则所有者明确旧目录适用的迁移/兼容路径，保留历史后按管理器重新绑定及递交。本卡自己的夹具替换已逐文件声明；不是未声明真实链路替换。

## 验证范围与已知限制

定向结果：R223 后端、分段和路由共 90 项通过，真实模型测试 1 项通过；旧导入卡七个测试模块共 89 项通过；旧导航预览卡完整受保护测试及相关 HTTP/存储范围共 60 项、七个子测试通过；R223 共享模块通过；58 份文案/编号清单通过；文案词法检查两文件零警告。命令、原样日志、哈希和运行记录随合同保存。

旧 R220 原样浏览器脚本在真实环境下固定要求“两处问题、8/10”的断言失败：本机工具已安装，实际为一处问题、10/11。未改产品或旧断言。另使用明确的“工具未安装”诊断夹具跑完原来的 26 项显示与交互断言；真实服务的诊断重查仍执行，媒体播放使用真实 H.264 文件及曲库复制品音频。该夹具不证明本机缺少工具，也不代替工具卡的实际安装验收。

本轮导航预览数据为隔离的合成作品、派生视频和图片，不是用户真实项目的重新分析。矩阵首次出现的 150% 进度来自合成夹具“完成 3、总数 2”，已修正为合法数据后补跑；没有放宽页面断言。完整矩阵现为 29 状态、四宽、33 组数字、零捕获错误，文案与编号检查通过。

项目 Required checks 均执行，原样命令、退出码和全量输出见 `required-checks.json` 与 `required-checks/`。既有 ffmpeg drawtext、工具软链接路径和 Obsidian 文档同步失败如实保留，不属于三卡局部机器 PASS；未修改相关产品、vault 或基线来凑绿。

**执行偏差**：首轮旧 HTTP 测试漏设 `LOCAL_MEDIA_ROOT`，启动时误读默认真实库的 v1 索引，在启动补队列之前被明确拒绝；会打开既有锁文件，但没有进入分析、迁移或曲目写入流程。不能声称本轮“全程未接触真实库”。此后所有相关命令显式绑定仓库外复制品并重跑。没有操作 8765，没有改写真实曲目的 track/index/analysis 文件，也没有对真实库运行迁移或模型。

## 推送与之后的步骤：只写，不执行

本轮没有 push、finish、合并、主目录同步、真实库迁移或 Studio 重启。以下由 Claude 在解决交付失败并问过用户后安排；任何一步失败都停止，不强推，不回退别人的改动。

1. 确认本批提交与机器绑定仍一致；远端若前移，先整合并重跑绑定和验证。获准后推送：

   ```bash
   git -C "$R223_WORKTREE" fetch origin
   git -C "$R223_WORKTREE" merge-base --is-ancestor origin/main HEAD
   git -C "$R223_WORKTREE" push origin HEAD:main
   ```

2. 确认远端已包含本批提交后，用脚本 finish。先仅移除 worktree 中已知的 `.venv`、`.tools` 软链接及本地交付缓存，不能删除它们的目标；它们若仍是未跟踪文件，finish 会拒绝。然后：

   ```bash
   python3 "$HARNESS_ROOT/Core/skills/task-worktree/scripts/task_worktree.py" finish "$R223_WORKTREE" --merged-into origin/main
   ```

3. 主目录由 Claude 核对其他会话未提交工作后同步；不 reset、不自动 stash 别人的内容。满足快进条件时运行 `git pull --ff-only`，核对源码、固定虚拟环境、分析工具与模型，再重建正式调度台和交付投影。
4. 安排维护窗口，先停止旧 Studio，备份真实库元数据和现有分析；迁移脚本自身会在首次写入前核验 metadata 备份。先预览，再决定 apply：

   ```bash
   .venv/bin/python scripts/migrate_music_library_v2.py --media-root "$LOCAL_MEDIA_ROOT"
   .venv/bin/python scripts/migrate_music_library_v2.py --media-root "$LOCAL_MEDIA_ROOT" --apply
   ```

   核对新 schema、已取消字段、曲目数及音频/peaks/attempts 不变；保留备份，失败停止并按备份恢复元数据，不覆盖原始音频。
5. 迁移通过后，在主目录按既有状态目录启动：

   ```bash
   .venv/bin/python scripts/launch_studio.py --port 8765 --no-browser
   ```

   核对音乐列表、已有 analysis 可读、三首状态、试听、重试和新导入补队列，再由用户执行三张卡的人工验收；不把启动成功当成人工通过。

## 提交、证据和工作区

改动在原 worktree 保存并提交，不推送。源码修改、Claude 的设计补充、三卡交付准备和机器证据均可审阅。主要证据根为 `agents-results/2026-10-21/r223-delivery/`，旧卡新机器运行仍按各自原交付根保存。图片、视频和曲库复制品均在仓库外 `~/.photo-content-os/evidence/R223-music-beat-map/phase-c/`。

业务 worktree 的已授权文件已提交；`.venv`、`.tools` 是共享软链接，本地交付缓存不提交。本轮没有改 Harness SSOT 源文件；仅通过公开生成器新增隔离调度台预览，正式项目登记未变，既有其他 Harness 改动未提交或回退。机器、人工作业保护及最终源码身份核对见本轮证据。本任务是交付证据包，不另建 SSOT 权威或 Obsidian 快照。
