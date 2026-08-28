# Photo Content OS

Photo Content OS 是一套 **local-first（本地优先）** 的照片与视频创作工作台：它把本地素材变成可验证的内容证据、脚本匹配、分镜、剪辑方案和人工精剪交接包，同时避免把原始媒体、编辑器工程和绝对路径暴露到 Web 控制面。

仓库只保存代码、机器合同、模板和自动化测试，不保存真实照片、视频或个人项目产物。

## 当前能力

```text
创建 CreativeProject
→ 连接本地素材目录
→ 扫描媒体与技术元数据
→ 按 metadata / preview / deep 分层取证
→ 提取关键帧与可选带时间码转写
→ 多模态 AI 生成证据化摘要
→ 对照 Brief / Script 匹配素材
→ 生成 Storyboard 与 canonical EDL
→ 生成剪辑交接包
→ 可选生成本地无声预览粗剪
→ 人工精剪、发布和复盘
```

当前稳定交付边界是 **经过机器校验的剪辑方案和交接包**。预览粗剪与可编辑时间线属于可选本地能力，不等同于自动完成审美精剪。

## 普通用户入口

Photo Content OS Studio 是零前端构建依赖的本地工作台，提供：

- 项目、Brief、脚本、素材、剪辑方案、交付和发布复盘的统一视图；
- 选中区块修改与单区块锁定；
- AI 只修改选中且未锁定的区块；
- 文档版本、差异查看和非破坏性回滚；
- Brief → Script → Storyboard → EDL → Delivery 的下游失效提示；
- 本地素材描述符、任务状态和隐私边界，不显示绝对路径。

### macOS / Linux

需要 Python 3.11 或更新版本，以及 `ffmpeg` / `ffprobe`。

```bash
git clone https://github.com/ValentinoWang/photo-content-os.git
cd photo-content-os
bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh
99_System_OpenClaw/.venv-content-os/bin/python \
  99_System_OpenClaw/scripts/44_launch_desktop.py
```

### Windows 11

在 PowerShell 中运行：

```powershell
git clone https://github.com/ValentinoWang/photo-content-os.git
cd photo-content-os
powershell -ExecutionPolicy Bypass `
  -File 99_System_OpenClaw/scripts/41_setup_dev_environment.ps1

99_System_OpenClaw\.venv-content-os\Scripts\python.exe `
  99_System_OpenClaw\scripts\44_launch_desktop.py
```

工作台只监听 `127.0.0.1`，项目状态默认保存在：

```text
~/.photo-content-os/studio/
```

## 命令行分析

跨平台编排入口：

```bash
python 99_System_OpenClaw/scripts/run_analyze_project.py \
  "/path/to/project" \
  --tier preview \
  --audio \
  --transcript-provider sidecar
```

常用层级：

| 层级 | 行为 | 适用情形 |
| --- | --- | --- |
| `metadata` | 只记录元数据，不调用语义模型 | 快速盘点、大批量导入 |
| `preview` | 少量均匀关键帧与受限音频预算 | 默认初筛 |
| `deep` | 更高视觉预算与项目相关证据 | 已选候选、准备剪辑 |

转写 Provider：

- `pending`：明确记录“尚未听懂”，不伪造音频语义；
- `sidecar`：读取相邻 `.srt`、`.json` 或 `.txt`；
- `openai_api`：使用配置的转写模型，要求 `OPENAI_API_KEY`。

## P0：正确性与跨平台合同

本轮核心正确性约束：

- 所有文本子进程显式使用 UTF-8；
- 视觉模型收到的是实际图片附件，而不是提示词里的路径文字；
- AI、预览和交接后端共用 `edit_decision_list_v1`；
- legacy `timeline_in/timeline_out` 只做确定性格式修复；
- `slot` 必须是唯一正整数，时间精确到毫秒；
- 没有真实来源的缺失镜头只能进入 `missing_materials`；
- Windows 使用 `.venv-content-os\Scripts\python.exe`；
- `43_content_os_doctor.py` 提供只读环境诊断。

机器合同位于：

```text
99_System_OpenClaw/schemas/edit_decision_list.schema.json
99_System_OpenClaw/schemas/audio_transcript.schema.json
```

## P1：与 OpenClaw Media 的可选关系

Photo Content OS 的核心分析、Studio 和本机 CI 可独立安装运行，不依赖 `openclaw-media` 包。只有主动使用云端配对或任务桥接时，才需要另行安装兼容版本的 `openclaw-media`；Photo Content OS **不复制**它的配对、租约、确认、运行、结果回传和归档状态机。

```text
OpenClaw Media Web / Control Plane
→ canonical pipeline / device / job / archive contract
→ openclaw-media outbound local agent
→ Photo Content OS 本地白名单能力
→ result_refs / artifact_refs / readback
```

当前冻结兼容基线：

```text
repository: ValentinoWang/openclaw-media
commit: f0460b4ce84ca7efc7eb6d2f05c77d20eef68aaf
contract: openclaw_media_product_v1
catalog digest: sha256:931dba97f9d9ed3fa1a03da4e15783f5d449ead7a56ff0919f3e0087efbf6967
```

薄桥入口：

```bash
python 99_System_OpenClaw/scripts/openclaw_media_agent.py contract
python 99_System_OpenClaw/scripts/openclaw_media_agent.py status
python 99_System_OpenClaw/scripts/openclaw_media_agent.py run match \
  --workspace /local/workspace \
  --workspace-ref projects/demo
```

上游设备合同当前正式声明 `macos`。Windows / Linux 可以运行本地核心流水线，但云端配对会保持 fail-closed，直到上游合同正式加入对应平台。

## 隐私边界

| 数据 | 默认位置 | Web 投影 |
| --- | --- | --- |
| 原始照片、视频、音频 | 本地设备 | 禁止上传 |
| 剪映/Kdenlive/OTIO 工程 | 本地设备 | 仅状态或描述符 |
| 本地绝对路径 | 本地设备 | 移除 |
| Brief、Script、Summary、EDL、SRT | 本地或经授权同步 | `content` |
| 媒体时长、尺寸、哈希、状态 | 本地生成 | `descriptor_only` |
| 关键帧代理 | 本地；模型分析需明确 Provider | 按策略授权 |

模型分析与云端归档是两个不同边界。即使控制面不接收原始媒体，用户选择的关键帧或音频片段仍可能发送给所配置的模型 Provider。

## 开发验证

macOS / Linux：

```bash
bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh
bash 99_System_OpenClaw/scripts/42_run_local_ci.sh
```

Windows：

```powershell
powershell -ExecutionPolicy Bypass `
  -File 99_System_OpenClaw/scripts/41_setup_dev_environment.ps1
powershell -ExecutionPolicy Bypass `
  -File 99_System_OpenClaw/scripts/42_run_local_ci.ps1
```

本机 CI 会执行运行时合同、完整单元测试、文档合同、审核能力注册表、仓库安全边界、公共入口和合成 Demo。未安装本地 Obsidian 自媒体库时，只跳过该项机器集成，并明确打印原因。

## 仓库结构

```text
99_System_OpenClaw/
├── desktop/                 # 本地 Studio 与静态前端
├── docs/                    # 执行规则和使用指南
├── schemas/                 # EDL、转写和上游兼容合同
├── scripts/                 # 扫描、分析、任务、交接、预览和诊断
├── templates/               # 批次、项目、交付和归档模板
└── tests/                   # 单元、协议、隐私和前端合同测试
```

真实媒体和项目工作区必须留在每位开发者自己的电脑上。不要使用 `git add -f` 绕过媒体忽略规则。

## 协作方式

从 `main` 创建短分支，提交前运行本机 CI，再通过 Pull Request 合并。详细约束见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [99_System_OpenClaw/AGENTS.md](99_System_OpenClaw/AGENTS.md)。
