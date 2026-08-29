---
SSOT_DEPTH: L1
SSOT_SCHEMA_VERSION: 1
SSOT_PLANNING_COMPILER: .ssot/planning-compiler.json
SSOT_MACHINE_SOURCE: .ssot/manifest.json
---

# AI 辅助作品归档能力落地路径

## 业务结论与范围

本次交付闭合本地归档准入和证据清单：项目具备最终成片、同步清单已完成且没有待增加内容时，工具生成带内容校验值的归档清单和索引卡。工具不上传、不删除、不修改真实剪映草稿。

阿里云盘和移动硬盘的真实回读仍需要外部或设备证据；本地代码已经提供统一的目标目录校验、回执、恢复演练和瘦身计划门禁，但不会把本地模拟目标升级为真实冷归档完成。

## 并行拆解

| 节点 | 交付物 | 依赖 | 可并行性 |
| --- | --- | --- | --- |
| N1 | 规则、模板、脚本和测试缺口审计 | 无 | 可先行 |
| N2 | 本地归档工具（`45_archive_project.py`） | N1 事实边界 | N1 完成后执行 |
| N3 | 归档回归测试（`test_archive_project.py`）与文档入口 | N2 接口 | 与 N2 的最终汇编串行 |
| N4 | 目标副本逐项回读与回执 | N2 | 可独立验收 |
| N5 | 按清单恢复到新目录并校验 | N2 | 可独立验收 |
| N6 | Mac 瘦身计划阻断门禁 | N2、N4、N5 | 依赖证据汇总 |

N1 的审计、N2 的工具、N4 的回读和 N5 的恢复可以由独立执行者在隔离目录并行；N3/N6 与共享 SSOT 主视图、机器清单（`manifest`）和最终状态由主协调者汇编。当前工作区已完成全部代码节点，保留 N1 的独立审计回执作为依据。

## 验收

- 归档工具（`45_archive_project.py`）默认只读；写入选项（`--write`）只写项目内归档清单（`archive_manifest.json`）和索引卡。
- 纳入文件按稳定路径排序并记录大小、内容校验值（算法标识（SHA-256））；排除分析目录（`_ai_analysis`）、临时加工目录（`App_WorkCache`）、待增加目录（`待增加`）和精选临时目录。
- 缺少最终成片、同步清单仍有未完成项或待增加非空时返回阻断状态。
- 目标副本可按归档清单逐项检查路径、大小和内容校验值，并可写入回读回执。
- 恢复目标必须是不存在的新目录；恢复完成后再次按清单校验。
- 瘦身计划在缺少准入、索引卡、回读回执或恢复证据时阻断，且不自动删除文件。
- 归档测试通过；保护测试不修改；差异空白检查（`git diff --check`）通过。

## 当前状态

R1：已实现并已验证（`IMPLEMENTED / VERIFIED`，本地静态与运行证据）。

R2（目标副本回读、恢复、瘦身计划）：已实现并已验证（`IMPLEMENTED / VERIFIED`）。真实阿里云盘/移动硬盘回读仍需外部设备证据，不能由本地测试替代。

## 工程执行附录

- 代码：`99_System_OpenClaw/scripts/45_archive_project.py`
- 测试：`99_System_OpenClaw/tests/test_archive_project.py`
- 差距说明：`99_System_OpenClaw/docs/10_AI辅助作品归档能力差距说明.md`
- 本地验证：`99_System_OpenClaw/.venv-content-os/bin/python -m unittest 99_System_OpenClaw.tests.test_archive_project`
- 回读：`45_archive_project.py --verify-target TARGET --manifest MANIFEST --write-receipt RECEIPT.json`
- 恢复：`45_archive_project.py --restore-from TARGET --restore-to NEW_DIR --manifest MANIFEST`
- 瘦身计划：`45_archive_project.py PROJECT --prune-plan --receipt RECEIPT.json`
