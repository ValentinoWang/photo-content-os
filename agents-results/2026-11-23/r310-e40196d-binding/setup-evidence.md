# R310 开发机装机运行记录

- 历史提交 `e40196d47b1edb7adcebc0422f420f2bacc1f3c9`。
- 开发机 `photo-dev`，装机时连接 `223.109.239.11:15548`。
- 对应脚本 `.agents/skills/photo-remote-dev-box/scripts/setup_remote.sh`，提交内 SHA-256 为 `f8e2711efb66e38d6177d25b6b923c33a7321d69628e844e9fab8f7fef55aa4a`。

## 包名解析

从装机工作区的脚本提取包名解析段，经 SSH 在开发机运行。工具输出记录于 2026-11-24T03:09:37.086Z，回执 `9feb153c-b141-4a1c-804f-22a0e0a78a0f`。

```text
libatk1.0-0t64
libatk-bridge2.0-0t64
libcups2t64
libasound2t64
libatspi2.0-0t64
libglib2.0-0t64
total=31
syntax-ok
```

旧脚本包清单有 31 项。新脚本在开发机解析出 31 项，其中 6 项切换为 t64 包名。

## 完整装机

原操作从同一工作区运行 `rbox setup`。工具完成回执为 `20c9e717-a626-4827-98b2-68acd16cf2b1`，时间 2026-11-24T03:35:33.872Z。留存原始日志的 SHA-256 为 `203c7e0a419872f5078670d2af2f34184bf43075c5bdcc44e5a6552d78620e9a`。

```text
[rbox] 开发机上已有传好的 ffmpeg 包
[rbox] setup 用了 1455 秒
[exited with code 0]
```

此记录覆盖装机和包名解析。R310 合同另有浅色界面专项与同步清单检查，H-01、H-02 等待任务委托人验收。
