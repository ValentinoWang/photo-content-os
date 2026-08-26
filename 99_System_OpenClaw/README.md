# OpenClaw 系统区

这里是 Photo Content OS 的本地执行与产品化层。它保存规则、机器合同、脚本、本地 Studio、测试和与 OpenClaw Media 的兼容快照；**不保存真实照片、视频、编辑器工程或用户项目产物**。

## 目录职责

| 路径 | 作用 |
| --- | --- |
| `desktop/` | 只监听本机回环地址的 Photo Content OS Studio；管理 CreativeProject、文档区块、锁定、版本、差异与回滚 |
| `docs/` | 本地执行总纲、平台边界、使用指南和产品化补充说明 |
| `schemas/` | EDL、转写与上游 OpenClaw Media 兼容合同 |
| `scripts/` | 素材扫描、分层取证、转写、AI 分析、任务桥接、剪辑交接、预览与诊断 |
| `tests/` | 单元、协议、隐私、跨平台与前端合同测试 |
| `templates/` | 批次、项目、交付和归档模板 |
| `review_capabilities.registry.json` | 作品审核能力注册表事实源 |
| `AGENTS.md` | Codex / OpenClaw 修改约束 |

## 普通用户入口

```bash
python 99_System_OpenClaw/scripts/44_launch_desktop.py
```

Studio 默认监听 `127.0.0.1`，状态存入 `~/.photo-content-os/studio/`。Web 投影不会返回本地绝对路径或原始媒体字节。

## 跨平台分析入口

```bash
python 99_System_OpenClaw/scripts/run_analyze_project.py \
  "/path/to/project" --tier preview --audio --transcript-provider sidecar
```

- `metadata`：只做元数据盘点；
- `preview`：默认低成本关键帧与音频预算；
- `deep`：对候选素材进行更高预算取证。

Windows 使用同名 PowerShell 入口；本地核心能力支持 Windows，但云端设备配对仍服从上游 OpenClaw Media 的正式平台合同。

## 与 OpenClaw Media 的边界

`photo-content-os` 只实现白名单本地能力和兼容校验，不复制 OpenClaw Media 的配对、租约、任务状态机、归档和 readback。冻结兼容快照见：

```text
schemas/openclaw_media_contract_snapshot.json
```

详细说明见 [docs/09_桌面工作台_OpenClaw合同与隐私.md](docs/09_桌面工作台_OpenClaw合同与隐私.md)。

## 验证

macOS / Linux：

```bash
bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh
bash 99_System_OpenClaw/scripts/42_run_local_ci.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File 99_System_OpenClaw/scripts/41_setup_dev_environment.ps1
powershell -ExecutionPolicy Bypass -File 99_System_OpenClaw/scripts/42_run_local_ci.ps1
```
