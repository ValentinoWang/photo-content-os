# Photo Content OS Studio

`studio/` 是 Photo Content OS 的本地普通用户入口。它使用 Python 标准库提供只监听 loopback 的 HTTP 服务，并直接托管 `static/` 中的零构建依赖前端。

## 启动

```bash
python scripts/launch_studio.py
```

常用参数：

```bash
python scripts/launch_studio.py \
  --state-dir ~/.photo-content-os/studio \
  --port 8765 \
  --no-browser
```

## 状态与隐私

- 项目状态保存在本机 `creative-projects.json`；
- Studio HTTP API 不返回相机原片。服务器只在本机读取原片来生成派生预览；
- 编号媒体接口仅返回镜头 H.264/AAC 小样片、镜头帧图、已导出的成片及封面、音乐库音频和 state 目录中的素材预览。视频与音频支持单段 Range；未知编号或路径参数返回 404；
- 素材根中的新增派生写入限于镜头样片、成片封面、音乐波形 `peaks.json`、用户决定 `decisions.json` 和挑选进度；镜头分析的既有生成流程仍由 `select_shots.py` 负责。用户决定不写回 `shots.json`；
- Studio 启动时在后台补齐这些派生缓存；关闭 Studio 会停止它拥有的缓存准备和挑选进程；
- 用固定运行时执行 `.venv/bin/python scripts/prepare_studio_media.py --state-dir <state目录>` 可只补预览缓存，不重新挑选、不调用模型或音乐平台；
- 绝对 workspace path 只保存在本地状态文件，公开投影只包含 label、path digest 和 connected 状态；
- 写请求要求 loopback Host、同源 Origin 和 `X-Content-OS-CSRF`；
- 静态响应带 CSP、`X-Frame-Options: DENY` 和 `nosniff`。

## Live Draft 合同

- 文档拆成有稳定 ID 的 block；
- 手工保存和 AI 修改都必须显式提供 `selectedBlockIds`；
- 替换集合必须与选中集合完全一致；
- locked block 不能被保存或 AI 修改；
- rollback 创建新版本，不删除旧历史；
- Brief、Script、Storyboard、EDL 的变化会按依赖关系把下游标记为 stale。

## 文件职责

```text
project_store.py   CreativeProject、版本、锁、diff、rollback、审计
ai_patch.py        选中区块 AI 补丁输入/输出合同
server.py          loopback HTTP、CSRF、隐私投影、静态文件
static/            普通用户前端
```
