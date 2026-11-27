# 人工验收清单：2026-11-26-Pho_R18-concat-return

<!-- 内部绑定信息，不向用户展开。
- 任务编号：2026-11-26-Pho_R18-concat-return
- 人工验收绑定：acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/binding.md
- 验收合同：agents-results/2026-11-26/Pho_R18-concat-return/acceptance-contract.md
- 合同版本：1
- 清单状态：已批准
- 清单可独立执行版本：1
- 所需人工角色：任务委托人
- 清单负责人：任务委托人
- 批准证据：总控任务单 TASK-D 指定本卡 H-01、H-02 的操作和预期表现。
- 执行结果：acceptance/human/2026-W48/2026-11-26-Pho_R18-concat-return/runs/<run-id>/result.md
-->

## H-01

- 验收步骤：
  1. 打开 Studio 项目页，查看「剪辑软件」列表。
  2. 点 Concat 一行的「选择」。
- 预期表现：Concat 排在列表第一位，附官网、源码、下载链接，点选择后显示「已选择」。

## H-02

- 验收步骤：
  1. 选择 Concat 并点「自动出第一版」，再打开生成的工程精修、导出，然后关闭 Concat 里的这个工程。
  2. 拖入导出的成片到「把导出的成片拖回这里」，点「检查这份成片」。
- 预期表现：候选成片出现且检查通过；如果工程还开在 Concat 窗口里，提示「请先关闭 Concat 里的这个工程再回传」，不出现候选。
