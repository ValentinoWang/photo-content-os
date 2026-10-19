# 本地音乐导入

抖音匿名取不到，2026-10-20 用户定不再处理。

课程项目使用固定运行时和锁定的 `musicdl==2.14.2`：

```bash
.venv/bin/python scripts/import_music.py "分享文字或单曲链接" "另一条链接"
.venv/bin/python scripts/import_music.py --list
.venv/bin/python scripts/import_music.py --from-folder
.venv/bin/python scripts/import_music.py --from-folder "/客户端下载目录"
.venv/bin/python scripts/import_music.py "网易云链接" --search-elsewhere
.venv/bin/python scripts/import_music.py --login netease
```

汽水和网易云单曲由 musicdl 解析、下载；链接没有直接单曲入口时先识别编号，再构造它需要的曲目信息。只使用官方音源与标准音质，不调用第三方会员接口、音质轮询、歌词或封面服务。抖音音乐页、视频和图文作品提取目标作品使用的原声。平台返回访问验证或无法确认完整音源时停止，避免自动重抓。

网易云按用户已确认的非会员状态处理：会员曲明确提示「这首需要网易云会员，你的账号不是会员；可以换一首，或者加 --search-elsewhere 在汽水音乐里找同名的歌」。只有显式加参数才按歌名和歌手在汽水搜索一次；歌名和歌手都相同才取第一个匹配结果，对不上显示「没找到同一首」。不会自动用近似作品或其他平台替换。

素材只经 `runtime_paths.local_media_root()` 解析：`LOCAL_MEDIA_ROOT`，默认 `~/Desktop/照片筛选`，库位于 `library/music/`。原文件只读复制。客户端目录只扫描直接子文件，完全离线；`.ncm` 在临时目录解密并保存音频，原文件不动。文件没有歌曲编号时按音频哈希去重，来源记「网易云客户端下载」。

每首一个 SHA-256 目录，包含音频和 `track.json`，总索引保存完整条目。同平台/编号先查库，相同音频只存一份，`sources` 保留各来源。平台曲只用于本地预览与定切点；本地文件授权未知，不能默认为可发布。时长、采样率和 LUFS 入库时测量，无法完整解析不入库；BPM、节拍、段落留空，由 R208 后续处理。

每个入口只尝试一次，成功、失败与中断都保留记录。请求在发出前写入持久缓存占用，响应（含 HTTP 错误）缓存到素材根私有目录；后续只读缓存。HTTP 按实际 URL 和载荷独立缓存，短链跳转逐跳保存；已取得的歌曲页作为 musicdl 解析输入复用，曲目身份去重留在入库层；媒体 GET 的响应复用于 musicdl 的探测和文件写入，不另发 HEAD 或范围请求。请求失败后不会因 musicdl 的异常处理再次发出网络请求。

网易云会员失败缓存保留歌名和歌手；之后加 `--search-elsewhere` 可以单独触发一次汽水搜索，无需再次访问网易云。搜索失败也记录，重复命令不重搜。请勿自行删除 `.attempts` 和 `.http-cache` 反复重试；需要新请求时由负责人安排。`CachedHTTP(..., allow_network=False)` 可用于严格离线排查，缓存不足就失败。

抖音视频和图文作品使用 iPhone Safari UA 读取 iesdouyin 分享页的服务端 JSON，不跟随该页面跳转，也不回退到签名作品详情接口。音乐页保留上游签名音乐接口及新注册的匿名 ttwid。两条路线均不读取浏览器 Cookie；无法确认作品音乐或需要登录时停止。匿名 ID 和签名请求计划只保留在仓库外的私有请求缓存。`--browser` 是可选浏览器读取接口，不用于抖音匿名导入。

扫码是独立可选命令，不在非会员导入主流程里。只有显式 `--login netease` 才访问登录服务，最多等待三分钟。凭据保存在仓库外 `$XDG_CONFIG_HOME/photo-content-os/music/netease-session.json`（默认 `~/.config`），文件权限 600、目录 700，不打印登录态或账号资料。不可读、损坏、未登录分别报告；没有短信、密码、签到、刷歌或上传功能。

完整许可证和代码来源见 `THIRD_PARTY_NOTICES.md`。

## 网络地区与可选音乐代理

网易云权限中的 `st=-100` 或 `freeTrialPrivilege.cannotListenReason=1` 会明确显示：

> 网易云限制了你当前所在地区播放这首（你现在的网络不在大陆），需要从大陆网络导入

这与会员限制分别处理，不会自动切换网络。汽水网络失败记录超时、连接重置、TLS、DNS 等异常类型；网络异常本身不能证明地区限制。

用户可在仓库外 `$XDG_CONFIG_HOME/photo-content-os/music/egress.json`（默认 `~/.config`）配置 SSH 出口，文件权限必须为 600，只包含以下字段（替换示例值）：

```json
{"ssh_target": "用户名@服务器域名"}
```

导入网易云或汽水时，命令按需启动 `ssh -T -N -D 127.0.0.1:<空闲端口>` 动态转发，用 `socks5h://` 连接并由出口解析 DNS；不执行远端命令、不安装软件或写远端文件。要求已配置免密 SSH 和受信任的主机密钥，不会交互询问密码或修改主机信任。成功、失败、Ctrl-C 或 SIGTERM 后关闭隧道。配了出口但启动失败或断开就明确报错，不退回直连，也不重启隧道重试。

抖音保持直连，忽略音乐代理和通用代理变量。未配置 SSH 出口时，网易云、汽水默认直连，也可用 `CONTENT_OS_MUSIC_PROXY` 指向自行管理的音乐代理；支持 socks5h/socks5/http/https。只有网易云和汽水使用此代理，配置错误或失败不退回直连。配置了 SSH 出口时以 SSH 出口为准。

按 SSH 目标的摘要隔离 IP 相关响应缓存，不将出口地址写入仓库或曲目信息。请求前先查库和导入记录；已入库的原分享文字第二次导入不会发请求或启动隧道。新出口不会自行清除失败记录，需要负责人授权后保留旧记录并安排一次新的尝试。
