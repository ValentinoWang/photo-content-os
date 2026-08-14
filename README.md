# Photo Content OS

Photo Content OS 是一套面向照片和视频项目的本地整理、分析、剪辑交接与归档工具链。仓库只保存代码、协议文档、模板和自动化测试，不保存任何真实照片、视频、剪辑工程或个人项目产物。

## 五分钟试用

需要 Python 3.11 或更高版本。基础 demo 不需要 OpenClaw、Obsidian、剪映或云端账号。

```bash
git clone https://github.com/ValentinoWang/photo-content-os.git
cd photo-content-os
bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh
bash 99_System_OpenClaw/scripts/42_run_local_ci.sh
99_System_OpenClaw/.venv-content-os/bin/python 99_System_OpenClaw/scripts/39_create_demo_project.py
```

如果系统的 `python3` 低于 3.11，请先安装新版 Python，再把安装命令写成 `PYTHON_BIN=python3.13 bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh`（版本号按本机实际命令调整）。

成功后，命令会输出 demo 项目和素材清单的绝对路径。默认试用目录是 `demo_workspace/`，其中会生成三张合成示例图片，并完成：

1. 创建标准项目目录；
2. 扫描示例素材；
3. 识别可分析图片；
4. 写出 `_ai_analysis/media_manifest.json`。

`demo_workspace/` 已被 Git 忽略，可以反复创建不同名称的试用项目，不会进入提交。

## 开发验证

```bash
bash 99_System_OpenClaw/scripts/41_setup_dev_environment.sh
bash 99_System_OpenClaw/scripts/42_run_local_ci.sh
```

安装脚本会创建仓库内固定的开发运行时并安装锁定版本的依赖。本机 CI 会执行运行时契约、全部单元测试、文档大纲契约、作品审核能力注册表、安全边界、命令入口和合成 demo。检测到本机 Obsidian 自媒体库时还会执行完整文档同步门禁；同学电脑没有该库时，只跳过这一项本机集成并明确打印原因。

仓库已关闭 GitHub Actions，以本机 CI 结果作为 Pull Request 的合并门禁。

## 仓库边界

- `99_System_OpenClaw/scripts/`：素材扫描、项目结构、任务队列、剪辑交接和审核脚本。
- `99_System_OpenClaw/tests/`：自动化与协议测试。
- `99_System_OpenClaw/docs/`：本地执行规则和使用指南。
- `99_System_OpenClaw/templates/`：批次、项目、交付和归档模板。
- `99_System_OpenClaw/schemas/`：机器可读结构约束。

真实媒体和项目工作区必须留在每位开发者自己的电脑上。不要使用 `git add -f` 绕过媒体忽略规则。

## 协作方式

从 `main` 创建短分支，提交前运行上述开发验证，再通过 Pull Request 合并。具体约束见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [99_System_OpenClaw/AGENTS.md](99_System_OpenClaw/AGENTS.md)。
