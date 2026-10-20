# 音乐导入来源与许可

## musicdl 2.14.2

本课程项目使用并适配 [CharlesPikachu/musicdl](https://github.com/CharlesPikachu/musicdl)，锁定为 PyPI `musicdl==2.14.2`。Copyright (c) 2018–2026 CharlesPikachu。**PolyForm Noncommercial 1.0.0** 许可证全文见 [musicdl.LICENSE](musicdl.LICENSE)。

汽水调用 `SodaMusicClient._parsewithofficialnonvipapiv1`；网易云调用 `NeteaseMusicClient._getsongmetainfo` 并改写其官方音源解析器；单曲文件写入调用 musicdl `_download`。适配位于 `musicdl_engine.py`：固定标准音质、移除音质轮询/歌词/封面/第三方解析；请求由持久缓存托管，下载不补标签或歌词。不使用会员限制绕过接口。

## 本地文件与可选扫码

- `client_files.py` 的 NCM 容器和密钥盒算法根据 [taurusxin/ncmdump](https://github.com/taurusxin/ncmdump/blob/main/src/ncmcrypt.cpp) 改写，MIT 许可全文见 [ncmdump.LICENSE](ncmdump.LICENSE)。上游版权行使用 `[year] [fullname]` 占位，原样保留。没有复制上游测试歌曲。
- 可选二维码登录的 Linux API 协议参考 [api-enhanced](https://github.com/neteasecloudmusicapienhanced/api-enhanced)，独立实现，MIT 许可全文见 [api-enhanced.LICENSE](api-enhanced.LICENSE)。

## 抖音与浏览器 Cookie

- 抖音直接复用 [jiji262/douyin-downloader](https://github.com/jiji262/douyin-downloader/tree/ed863617aa52353821aca8fdebcfad4e916ebff5) 的 `utils/abogus.py`（原样放入 `vendor/douyin_abogus.py`）和 `core/api_client.py` 的单次详情参数/签名流程（`vendor/douyin_query.py`、`douyin_api.py`）。固定来源提交 `ed863617aa52353821aca8fdebcfad4e916ebff5`，MIT 全文见 [douyin-downloader.LICENSE](douyin-downloader.LICENSE)。去掉重试、登录、浏览器回退、多 aid 轮询及 msToken 网络服务，图文采用 aid=6383。匿名 msToken 仅复用该提交 `auth/ms_token_manager.py` 的本地随机生成函数，不访问令牌服务；查询与匿名 Cookie 使用同一值。
- 上游签名文件注明 JohnserfSeed / F2、Apache-2.0，原版权头完整保留。上游该提交没有匿名 ttwid 注册实现；`douyin_api.py` 的单次匿名注册请求直接改编 [F2 TokenManager.gen_ttwid](https://github.com/Johnserf-Seed/f2/blob/main/f2/apps/douyin/utils.py) 及 `f2/conf/conf.yaml` 的公开协议，移除全局客户端和重试，使用私有缓存及响应 Cookie。Apache-2.0 全文见 [f2-Apache.LICENSE](f2-Apache.LICENSE)。不复用上游配置中的任何现成 Token。
- 输入识别与只读浏览器 Cookie 由用户指明的旧本地工具重写纳入本项目，无跨仓 import，没有迁入网页服务。

## Offline music analysis

Analysis runs in `.tools/music-analysis/`, installed with `python3 scripts/setup_edit_tools.py --music-analysis`. It uses no large language model and cannot open network connections. Python 3.12 is selected for matching macOS arm64 wheels of torch/torchaudio 2.8.0, Essentia TensorFlow and librosa 1.0.0. Package pins and model metadata hashes are in `third_party/edit-tools.lock.json`; transitive package versions are in `third_party/music-analysis.requirements.lock.txt`.

| Component | License | Full text | Source |
| --- | --- | --- | --- |
| beat-this 1.1.0 and final0 weights | MIT | `beat-this-MIT.LICENSE` | https://github.com/CPJKU/beat_this/blob/main/LICENSE |
| librosa 1.0.0 | ISC | `librosa-ISC.LICENSE` | https://github.com/librosa/librosa/blob/1.0.0/LICENSE.md |
| essentia-tensorflow 2.1b6.dev1389 | AGPL-3.0-only | `essentia-AGPL-3.0.LICENSE` | https://github.com/MTG/essentia and https://www.gnu.org/licenses/agpl-3.0.txt |
| MTG Discogs EffNet embedding and four classification heads | CC BY-NC-SA 4.0 | `MTG-CC-BY-NC-SA-4.0.LICENSE` | https://essentia.upf.edu/models.html and https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode |

The MTG artifacts, authors and publications are identified in each authenticated model metadata JSON downloaded next to its graph. The graph URLs and SHA-256 values come from the project music registry; installation also authenticates the class-name metadata and beat checkpoint. All files remain local; do not package model binaries in Git.
