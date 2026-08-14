# OpenClaw 系统区

这里放 OpenClaw 的制度细则、自动化脚本、测试、schema、运行器和改造审计。它不是素材库，也不是剪映工程区。

## 内容

| 目录 / 文件 | 作用 |
| --- | --- |
| `docs/` | 本地执行总纲、SOP 子文档和决策表 |
| `templates/` | 新批次、新项目、资产卡片、交付包、归档包的复制模板 |
| `scripts/` | 自动化脚本和 Mac OpenClaw Runner 实现 |
| `tests/` | 自动化测试 |
| `schemas/` | JSON schema |
| `review_capabilities.registry.json` | GitHub 管理的作品审核能力单一事实源 |
| `AGENTS.md` | Codex / OpenClaw 工作约束 |
| `mac_openclaw_runner.py` | Mac OpenClaw Runner 入口 |
| `restructure_audit/` | 每次改造前后的文件清单、哈希和体积统计 |

## 和根目录文件的关系

| 路径 | 作用 |
| --- | --- |
| `../00_START_HERE_今天看这里.md` | 日常导航：告诉人先看哪里、素材放哪里 |
| `docs/00_本地素材与剪映HyperFrames流转总纲.md` | 本地素材系统执行总纲 |
| `docs/` | 执行总纲和详细执行细则 |
| `templates/` | 每次开新内容时可直接复制的目录和说明文件 |
| `99_System_OpenClaw/scripts/` | 把规则落地成可重复运行的脚本 |
| `99_System_OpenClaw/tests/` | 防止脚本和规则漂移的测试 |
| `99_System_OpenClaw/schemas/` | 自动化产物的结构约束 |

根目录只保留日常入口和素材业务目录；OpenClaw 制度、脚本、测试、schema 和运行器都收进本目录。
