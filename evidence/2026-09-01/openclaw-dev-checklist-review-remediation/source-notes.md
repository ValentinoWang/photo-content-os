# 当前源码证据

本文件记录 2026-09-02 对提交 `76222628c637ecbd63953d9cd5716dfa33e43526` 的可复查事实。它是 A1 的证据交付物，不替代机器节点或生成的主视图。

| 关键发现 | 当前文件和行号证据 | 复查命令 |
|---|---|---|
| Studio 核心功能可独立运行 | `README.md:116` 明确说明核心分析、Studio 和本机 CI 不依赖 `openclaw-media` | `nl -ba README.md | sed -n '110,122p'` |
| 图片尚未采集定位字段 | `99_System_OpenClaw/scripts/01_scan_media_manifest.py:180-184` 初始化照片定位字段为空，`189-192` 只读图片尺寸 | `nl -ba 99_System_OpenClaw/scripts/01_scan_media_manifest.py | sed -n '162,195p'` |
| 媒体编号不是内容校验值 | `99_System_OpenClaw/scripts/media_common.py:176-177` 以相对路径计算 SHA-1；内容 SHA-256 在 `188-193` 的独立函数中 | `nl -ba 99_System_OpenClaw/scripts/media_common.py | sed -n '171,194p'` |
| Studio 仅声明本机健康状态 | `99_System_OpenClaw/desktop/server.py:139-141` 的健康响应为 `localOnly: true` | `nl -ba 99_System_OpenClaw/desktop/server.py | sed -n '125,146p'` |
| R2 原冻结命令不满足测试导入合同 | `99_System_OpenClaw/tests/test_p2_photo_remaining.py:7` 与 `test_project_structure_v2.py:8` 同级导入 `_support` | `python3 -m unittest 99_System_OpenClaw.tests.test_p2_photo_remaining 99_System_OpenClaw.tests.test_project_structure_v2` |
| 发现式命令可执行 | 项目虚拟环境下 `test_p2_photo_remaining.py` 为 4 个测试、`test_project_structure_v2.py` 为 1 个测试 | 见主视图“验收命令和证据边界” |
| Inbox 提升会移动并删除来源批次 | `99_System_OpenClaw/scripts/35_promote_inbox_batch_to_project.py:74-78` 移动路径，`198-228` 执行提升并尝试删除来源目录 | `99_System_OpenClaw/.venv-content-os/bin/python -m unittest discover -s 99_System_OpenClaw/tests -p 'test_promote_inbox_batch_to_project.py'` |

证据只能证明源码和临时夹具行为。它不证明上游身份、ChatCut、云盘、移动硬盘、系统回收站或物理设备已经完成。
