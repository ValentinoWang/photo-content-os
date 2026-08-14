# Photo Content OS

Photo Content OS 是一套面向照片和视频项目的本地整理、分析、剪辑交接与归档工具链。仓库只保存代码、协议文档、模板和自动化测试，不保存任何真实照片、视频、剪辑工程或个人项目产物。

## 五分钟试用

需要 Python 3.11 或更高版本。基础 demo 不需要 OpenClaw、Obsidian、剪映或云端账号。

```bash
git clone https://github.com/ValentinoWang/photo-content-os.git
cd photo-content-os
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python 99_System_OpenClaw/scripts/39_create_demo_project.py
```

成功后，命令会输出 demo 项目和素材清单的绝对路径。默认试用目录是 `demo_workspace/`，其中会生成三张合成示例图片，并完成：

1. 创建标准项目目录；
2. 扫描示例素材；
3. 识别可分析图片；
4. 写出 `_ai_analysis/media_manifest.json`。

`demo_workspace/` 已被 Git 忽略，可以反复创建不同名称的试用项目，不会进入提交。

## 开发验证

```bash
python -m unittest discover -s 99_System_OpenClaw/tests
python 99_System_OpenClaw/scripts/06_check_outline_contract.py . --skip-obsidian-sync
python 99_System_OpenClaw/scripts/36_validate_review_capability_registry.py
python 99_System_OpenClaw/scripts/40_check_repository_safety.py
```

本机生产环境还有 Obsidian 文档同步、固定 OTIO/Kdenlive 运行时和真实媒体工具门禁。这些检查依赖仓库所有者的本机环境，不属于首次试用的前置条件；相关环境存在时，测试会自动覆盖对应集成。

## 仓库边界

- `99_System_OpenClaw/scripts/`：素材扫描、项目结构、任务队列、剪辑交接和审核脚本。
- `99_System_OpenClaw/tests/`：自动化与协议测试。
- `99_System_OpenClaw/docs/`：本地执行规则和使用指南。
- `99_System_OpenClaw/templates/`：批次、项目、交付和归档模板。
- `99_System_OpenClaw/schemas/`：机器可读结构约束。

真实媒体和项目工作区必须留在每位开发者自己的电脑上。不要使用 `git add -f` 绕过媒体忽略规则。

## 协作方式

从 `main` 创建短分支，提交前运行上述开发验证，再通过 Pull Request 合并。具体约束见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [99_System_OpenClaw/AGENTS.md](99_System_OpenClaw/AGENTS.md)。
