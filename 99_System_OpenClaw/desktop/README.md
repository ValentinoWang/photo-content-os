# Photo Content OS Studio

`desktop/` 是 Photo Content OS 的本地普通用户入口。它使用 Python 标准库提供只监听 loopback 的 HTTP 服务，并直接托管 `static/` 中的零构建依赖前端。

## 启动

```bash
python 99_System_OpenClaw/scripts/44_launch_desktop.py
```

常用参数：

```bash
python 99_System_OpenClaw/scripts/44_launch_desktop.py \
  --state-dir ~/.photo-content-os/studio \
  --port 8765 \
  --no-browser
```

## 状态与隐私

- 项目状态保存在本机 `creative-projects.json`；
- 原始媒体不由 Studio HTTP API 读取或返回；
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
