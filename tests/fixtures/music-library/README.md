# 离线夹具

全部编号、歌名、歌手和 CDN 域名均为合成数据，无真实歌曲、账号、Cookie、Token 或个人信息。JSON/HTML 响应结构来自公开参考源码里的字段读取约定，并非本阶段从真实歌曲链接录制。真实响应覆盖须留到阶段 2 的单次冒烟。

- 汽水：公开分享页 `_ROUTER_DATA` 的 `trackInfo` 和 `audioWithLyricsOption`（musicdl 只读参考字段含义，无源码复制或依赖）。
- 抖音：视频实体 `aweme_id` → `music.id/title/author/play_url.url_list`。
- 网易云：`songs[].id/name/ar/al/dt/fee` 与 `data[].id/code/url/type/freeTrialInfo`。
- `synthetic.ncm`：由 `make_ncm_fixture.py` 生成，载荷是 ffmpeg 生成的 3 秒正弦波 MP3；公开 NCM 容器格式，非真实歌曲。生成脚本只运行本地 ffmpeg，不联网。
