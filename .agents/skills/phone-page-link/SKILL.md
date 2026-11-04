---
name: phone-page-link
description: 用户在手机上看这个项目的对话（消息带「[手机回复]」），要给设计稿、报告这类页面时用：让手机对话页出现能点开的链接。写清哪些路径会变成链接、页面要做成什么样、发之前查什么。只给图片路径不会出链接。
---

# 给手机能点开的页面

手机对话页只显示路径的文件名。**只有 `.html` 路径会变成链接**，点开是上传好的网页包。

## 回复怎么写

- 写 `.html` 的绝对路径，单独一行，前后不贴中文。
- 一条回复最多放 2 个页面。
- **不要指望图片路径出链接。** `.png`、`.jpg` 在对话页只是一行文件名，点不开（2026-11-04 Pho 组件稿实测）。要给图，把图放进 HTML 页面。
- 文字先说结论，再放路径。

## 页面怎么做

- 单列，390 宽不横向滚动，宽表格包一层左右滑。
- 优先做成单文件：样式写在页面里，图片用 `data:` 内嵌。单文件不需要在电脑上起服务，用 `file://` 打开也能检查。
- 用真实页面当底座的稿子，发给手机前先定格：`iframe` 换成截图，脚本模块去掉，样式内嵌。样例见 `agents-results/2026-11-04/frontend-component-redesign/phone.html`（本机证据，不进 Git）。
- 不要根路径引用（`/app.js`），不要请求本机服务。
- 单文件不超过 5 MB，整包不超过 20 MB。

## 发之前查

在 Harness Engineering 仓库根目录运行，`<页面>` 换成绝对路径：

```bash
PYTHONPATH=. python3 -c "
from pathlib import Path
from tools.console.phone_bundles import collect_bundle
e = Path('<页面>')
r = collect_bundle(e, cwd=e.parent, limits={})
print('fallback', r['fallback'], 'pages', len(r['pages']), 'files', len(r['files']))
"
```

`fallback` 必须是 `None`，`pages` 不能为 0。再跑 `page.py check` 看 390 宽截图，里面有切换就实点一次。

发出后可以查网页包登记了没有（`<会话号>` 用完整号）：

```bash
PYTHONPATH=. python3 -c "
import time
from tools.console.phone_bundle_index import lookup
print(lookup('<会话号>', [(0, '<页面>', time.time())]))
"
```

有结果说明链接有内容可开。

## 这些检查证明不了的

上面都是在电脑上查的，证明不了手机上真的能点开。没有用户回话或手机截图之前，只能说「网页包已登记」，不说「手机上能看」。用户说看不了，先要一张手机截图再判断，不要换一种发法再试。

从对话里的链接点开时，页面没有截图可以兜底：领票或加载失败后会反复重试，看到的是一直停在「正在打开页面」，不显示原因（`services/phone-reply/page/app.js` 的 `openHtmlViewer`，在 Harness Engineering 仓库）。

现状（2026-11-04）：用户在手机上还打不开 Pho 组件稿，原因未查明。这份技能写清了怎么出链接，还不能保证点开一定成功。
