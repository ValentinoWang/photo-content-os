# Inbox 事件批次模板

把整个目录复制到：

```text
00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理/
```

复制后只改四件事：

1. 把目录名改成真实事件。
2. 填 `00_批次说明.md` 的云端项目引用区：Obsidian 项目ID、idea / brief / script / task 路径。
3. 把同一事件的素材放进来；不需要按 iPhone、DJI、录屏再拆第一层来源目录。
4. 如果暂时没有云端项目包，就把项目ID留空；Mac 会把该批次标成 `pending_cloud_brief`，不会要求腾讯云提前知道本地素材全路径。

素材可以平铺，也可以保留 AirDrop、SD 卡、网盘下载或 zip 解压自带的原始文件夹。

绑定到 Content OS 项目包时执行：

```bash
cd /Users/vsiyo/Desktop/照片筛选
python3 99_System_OpenClaw/scripts/31_link_batch_to_content_project.py \
  "00_Inbox_Mac_Intake/YYYYMMDD_事件名_待整理"
```
