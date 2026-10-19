# R207 剪辑工具装进 photo-content-os，不再依赖桌面 Opensource_Tool

需求卡：`acceptance/requests/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/`（先读 request.md）。
用户原话：「能不能把这个路径解耦？放在我们photo-content-os里面」。

## 背景：现在的硬编码

| 位置 | 默认值 | 问题 |
|---|---|---|
| `scripts/edit_backends/openfilm_adapter.py` `DEFAULT_PACKAGE` | `~/Desktop/Opensource_Tool/openfilm-oa/runtime/node_modules/openfilm` | 该目录现在是**空的**，默认值已经失效；之前的运行时清单在 `~/Desktop/Opensource_Tool/embed-editor-es/openfilm-runtime/package.json`（openfilm 0.1.5） |
| `scripts/edit_backends/openchatcut_adapter.py` `CONTENT_OS_OPENCHATCUT_ROOT` | `~/Desktop/Opensource_Tool/OpenChatCut` | 外部源码目录，上游 https://github.com/0xsline/OpenChatCut ，本机副本提交 `2e6f4a2`，版本 0.2.16，AGPL-3.0-or-later |
| 同上 `CONTENT_OS_OPENCHATCUT_NODE` | Codex 缓存里的 node | 机器私有路径 |
| 同上 `CONTENT_OS_OPENCHATCUT_BROWSER` / `..._REFINE_BROWSER` | `~/Library/Caches/ms-playwright/...-1234/...` | 机器私有、版本号写死 |
| 同上 Chromium 排队脚本 | `自媒体创作Agent/apps/media/web/scripts/qa/withChromiumSlot.sh` | **跨仓库运行时依赖** |

## 要的效果

1. 仓库里新增一份**锁定清单**（建议 `third_party/edit-tools.lock.json`），逐个工具写：名字、来源（git 地址 + 提交，或 npm 包 + 版本）、许可证、安装步骤、运行时需要的 Node 版本、浏览器版本。OpenChatCut 钉在本机现用的提交 `2e6f4a2`，openfilm 钉 0.1.5（以 `openfilm-runtime/package-lock.json` 为准）。
2. 新增一条安装命令（Python 脚本，配一个 `.sh` / `.ps1` 薄入口，和现有 `setup_dev_environment` 同风格），按清单把工具装进**仓库内被 git 忽略的工具目录**（建议 `.tools/`，和 `.venv` 同级）：源码克隆到指定提交、`npm ci`、Playwright 浏览器装到 `.tools/` 下（`PLAYWRIGHT_BROWSERS_PATH`）。Node 优先用清单里钉的版本装进 `.tools/`；只有系统 `node` 版本满足清单时才可直接用系统的。重复运行是幂等的；装好的版本和清单不一致时报出来并重装。
3. 适配器默认值全部改成「仓库根下的 `.tools/...`」，相对仓库根计算（不要写死 `/Users/...`）。环境变量照旧可以覆盖。
4. Chromium 排队脚本复制一份进本仓库（例如 `scripts/qa/with_chromium_slot.sh`），**锁目录默认值保持 `/tmp/openclaw-media-chromium-slots` 和 `MEDIA_CHROMIUM_*` 变量名不变**，这样 Photo 和 Media 两个仓库的浏览器仍然共用同一组并发槽（这是防止 Mac 卡死的机制，不能拆成两组）。
5. `scripts/doctor.py` 增加「剪辑工具」一栏：每个工具显示版本、是否装好、所在位置（相对仓库根显示）；缺了或版本不对就明确说缺什么、用哪条命令装。**读不到/没装不许当成没问题**，也不许悄悄改用别的后端（项目已有规矩：ChatCut 未连接不会暗中改用 Kdenlive）。
6. README 和 `docs/video-pipeline-pf.md` 里写清安装命令；`.gitignore` 加 `.tools/`。
7. 加一条门禁或测试：`scripts/`、`studio/` 下的代码不许出现 `/Users/`、`Opensource_Tool`、`自媒体创作Agent` 这类机器路径（测试夹具和文档里的历史记录除外，要列清楚排除规则并带负例）。可以并进现有 `scripts/check_repository_safety.py`。

## 不要动

- 桌面 `~/Desktop/Opensource_Tool/` 下的任何文件都不删、不改（用户自己的收藏）。
- Kdenlive / melt、剪映、ChatCut Desktop 是系统里装的应用，照旧从系统找，不进 `.tools/`。
- 不改素材根 `~/Desktop/照片筛选` 下的任何东西。
- 不往 Git 里提交第三方源码或 `node_modules`。

## 共享工作区

`photo-content-os` 主目录 `main` 上有**别的会话没提交的改动**（`openclaw_video_execution.py`、`video_candidate.py`、`video_subtitles.py`、黑帧相关文件等，部分已暂存）。不许碰、不许暂存、不许还原它们。

- 一律在任务 worktree 里干活：`python3 /Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/skills/task-worktree/scripts/task_worktree.py create ...`（先看 `--help`），基于 `origin/main`。
- 用完按同一脚本 `finish` 合并并删除 worktree，不留未合并的。
- 别人造成的测试失败只列出、不修。

## 先读

- 仓库 `AGENTS.md`（必跑检查在 Required checks 一节）
- `docs/video-pipeline-pf.md`、`scripts/edit_backends/registry.py`、`interface.py`
- Core 规则：`/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/Core/harnesses/consumer-runtime-dependency-guard-card.md`、`unreadable-is-not-absent-guard-card.md`、`delivery-handoff-harness.md`

## 验证

1. 在 worktree 里真跑一遍安装命令，再跑 doctor，贴出剪辑工具那一栏的原文。
2. 用一个临时 `HOME` 或把相关环境变量清空的方式，证明适配器**不读** `~/Desktop/Opensource_Tool`：例如 `env -u CONTENT_OS_OPENCHATCUT_ROOT ...` 下 `probe()` 返回 `.tools/` 里的路径。
3. 跑 OpenChatCut 和 OpenFilm 后端各自已有的测试；能做真实渲染冒烟的（短片，几秒），各做一次，产物放 `evidence/2026-10-19/R207-edit-tools-in-repo/`，不进 Git 的大文件只记路径和大小。
4. AGENTS.md 的 Required checks 全部跑一遍，失败的逐条写清是不是本次造成的。

## 收尾（做完验证后自己完成，不停下来问）

1. 提交：信息末尾两行
   ```
   Request: 2026-10-19-R207-photo-edit-tools-in-repo
   Verify: 2026-10-19-R207-photo-edit-tools-in-repo/H-01, 2026-10-19-R207-photo-edit-tools-in-repo/H-02
   ```
   并加 `Co-Authored-By: Codex <noreply@openai.com>`。只提交本任务的文件。
2. 按 `delivery-handoff-harness.md` 递交验收卡（`acceptance/human/2026-W43/未-2026-10-19-R207-photo-edit-tools-in-repo/` 下 binding.md、checklist.md、handoff.json v2），验收步骤照需求卡的 H-01、H-02，跑 check-delivery。
3. `git fetch` 后推送 `main`（不 force、不 rebase 别人的提交）。推送前看 `origin/main..HEAD` 有没有别人的本地提交，有就停下写进汇报。
4. `finish` 删除 worktree；关掉本任务起的所有进程和浏览器。

## 遇到要拍板的事

先做不受影响的部分，把问题写进汇报后停下。例如：OpenChatCut 在钉住的提交上 `npm ci` 失败、需要换提交；openfilm 0.1.5 已从 npm 下架。

## 汇报

写到 `docs/tasks/R207-edit-tools-in-repo/REPORT.md`（主目录这份；worktree 里的同名文件不算），包括：改了哪些文件、锁定清单内容、doctor 原文、各项测试结果、提交号、推送结果、没做完的。
