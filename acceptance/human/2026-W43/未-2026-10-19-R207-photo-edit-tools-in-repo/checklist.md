# 人工验收清单：2026-10-19-R207-photo-edit-tools-in-repo

<!-- 内部绑定信息，不向用户展开。
- 任务编号：2026-10-19-R207-photo-edit-tools-in-repo
- 人工验收绑定：acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/binding.md
- 验收合同：evidence/2026-10-19/R207-edit-tools-in-repo/acceptance-contract.md
- 合同版本：1
- 清单状态：已批准
- 清单可独立执行版本：1
- 所需人工角色：产品负责人
- 清单负责人：用户
- 批准证据：用户要求按既有需求卡执行 TASK
- 执行结果：acceptance/human/2026-W43/2026-10-19-R207-photo-edit-tools-in-repo/runs/<run-id>/result.md
-->

## H-01

- 验收步骤：
  1. 打开终端，进入 Photo 软件所在的文件夹。
  2. 输入 README 里写的剪辑工具安装命令，再输入环境检查命令。
- 预期表现：环境检查的剪辑工具一栏列出 OpenChatCut、OpenFilm 和各自版本，位置都在 Photo 软件文件夹里面，没有一处指向桌面的开源工具文件夹或自媒体创作 Agent 仓库。

## H-02

- 验收步骤：
  1. 打开 Photo Studio，进入一个分镜已确认的项目。
  2. 点击生成剪辑候选。
- 预期表现：用 OpenChatCut 生成出能播放的候选视频。
