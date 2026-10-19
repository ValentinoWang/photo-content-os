# 仓库剪辑运行时路径门禁

- 失败类：`machine-runtime-path`；项目层静态阻塞检查，快速、无网络。
- 命令：`.venv/bin/python scripts/check_repository_safety.py --runtime-paths-only`；已由 `check_runtime_contract.sh` 调用。
- 范围：Git 跟踪的 `scripts/`、`studio/` 下 Python、Shell、PowerShell、JS/TS、HTML/CSS、JSON/YAML/TOML 源文件。禁止用户绝对路径、桌面开源工具目录和其他业务仓库名称。
- 排除：Markdown 等非运行源码；名为 `fixtures` 的路径分段和 `test_` 文件（仅用于测试夹具/负例）；仓库外 `tests/` 与文档历史记录不扫描。新增脚本暂存后检查，读不到源码同样失败。
- 修复：改用仓库根下 `.tools/`、本仓库脚本或显式环境配置；勿扩充排除项绕过真实依赖。
- 校准：仅检查源码里的完整字面量；不声称能证明所有动态路径拼接。零运行源码输入或读不到源文件同样失败。
- 红绿证据：`tests/test_edit_tools_runtime.py` 构造机器路径、不可读源码与合法仓库路径；既有适配器是历史失败例。
- 退役条件：运行工具全部由可校验的安装包入口寻址，且静态字符串检查不再提供独立覆盖时重新评估。
