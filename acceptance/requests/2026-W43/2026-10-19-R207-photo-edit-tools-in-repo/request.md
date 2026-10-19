# 剪辑工具装进 photo-content-os，不再依赖桌面 Opensource_Tool

状态：待确认

## 我的理解

1. OpenChatCut、OpenFilm 这些剪辑后端，以及它们要用的 Node、无头浏览器和浏览器排队脚本，改为按 photo-content-os 里的一份锁定清单装进仓库自己的工具目录（不提交进 Git），代码默认只在仓库内找。
2. 不再读桌面 Opensource_Tool、Codex 缓存里的 Node、Playwright 缓存或 自媒体创作Agent 仓库里的脚本；环境变量仍可覆盖。
3. 工具没装或装坏时，doctor 和后端明确报出缺什么、用哪条命令装，不悄悄改用别的后端。

## 不做的

- 不删除、不改动桌面 Opensource_Tool 里的任何文件
- Kdenlive、剪映、ChatCut 这类系统里安装的应用照旧从系统找

## 验收标准

### H-01

怎么操作：
1. 打开终端，进入 Photo 软件所在的文件夹。
2. 输入 README 里写的剪辑工具安装命令，再输入环境检查命令。

应该看到：环境检查的剪辑工具一栏列出 OpenChatCut、OpenFilm 和各自版本，位置都在 Photo 软件文件夹里面，没有一处指向桌面的开源工具文件夹或自媒体创作 Agent 仓库。

### H-02

怎么操作：
1. 打开 Photo Studio，进入一个分镜已确认的项目。
2. 点击生成剪辑候选。

应该看到：用 OpenChatCut 生成出能播放的候选视频。

<details><summary>查看原话</summary>

能不能把这个路径解耦？放在我们photo-content-os里面

</details>
