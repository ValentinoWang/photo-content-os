# 制作台接入 DreamVerse

这个插件适用于 DreamVerse Harness 源码实例。已对接上游 `ec0ac62760e3b7b2ba058941eaf6a15c3a16a3cf` 的 `video-harness` web profile。实例目录包含已构建的 `app/`，默认在 `state/` 保留 profile、项目配置和万相收据。

```bash
bash integrations/dreamverse/install.sh "$DREAMVERSE_INSTANCE"
```

如使用独立的 DSH_HOME，安装时传 `--dsh-home PATH`，启动服务时使用同一路径。脚本保留现有 profile 配置，连接仓库中的插件，并添加一段受管理的配置。重启服务后，在已认证的 `GET /api/dv/models` 中检查 `video/t2v/wanxiang/wan2.6-t2v`。如果是从 T8 试验升级，请先在这次使用的 profile 移除试验插件的注册。可选 `--max-submissions 2` 将该状态目录中每个已安装插件的提交尝试限制在两次，重启服务沿用计数。

只在本机启动 DreamVerse 的进程中，从 `~/.config/harness/speech-to-text.env` 读取 `SPEECH_TO_TEXT_API_KEY` 并传为 `DV_WAN_API_KEY`。百炼千问代理如使用同一个密钥，由启动器另传为 `DV_DEEPSEEK_API_KEY`。使用试验实例的启动器时，它已经处理这两个变量。服务应仅监听回环地址。桥接仅需要 DreamVerse 控制台的临时启动链接，可通过本次命令的 `DREAMVERSE_LAUNCH_URL` 环境变量完成 Cookie 交换。

```json
{
  "shots": [
    {"shot_id": "track", "prompt": "清晨空跑道慢推", "seconds": 5, "aspect_ratio": "9:16", "resolution": "720p"},
    {"shot_id": "blocks", "provider": "seedance", "prompt": "起跑器特写", "seconds": 5, "aspect_ratio": "9:16", "resolution": "720p"}
  ]
}
```

```bash
python3 scripts/aigc/dreamverse_bridge.py shots.json output --confirm track --confirm blocks
python3 scripts/aigc/dreamverse_bridge.py shots.json output
```

`--confirm` 可重复，每个参数确认清单中对应镜头的模型、时长、画幅、分辨率、提示词及万相控制项。省略 `resolution` 时桥接使用 720p，省略 `provider` 时使用万相。省略 `model` 时使用所选插件的默认模型（万相为 `wan2.6-t2v`）。万相时长为 2–15 秒整数，支持 16:9、9:16、1:1、4:3、3:4 及 720p、1080p。各组合的像素尺寸及参数规格来自[百炼万相文生视频 API 文档](https://help.aliyun.com/zh/model-studio/legacy-wan-text-to-video-api-reference)：

- `prompt_extend`（仅万相，`boolean`，默认 `true`）：控制是否开启百炼大模型提示词智能改写；需要严格按原句出空镜时，可在镜头里设为 `false`。关闭改写后模型按字面生成，不会自动补全语境，因此提示词要写全场景和材质（例：`清晨红色塑胶田径场空跑道慢推，画面里没有人`；只写「跑道」容易被按字面画成机场跑道）。
- `negative_prompt`（仅万相，`string`，长度不超过 500 字符）：映射到百炼请求体的 `input.negative_prompt`；省略时默认填入 `品牌标识、logo、商标、水印、文字`，可在单镜中覆盖为自定义中文/英文负面词，或传 `""` 清空。修改 `prompt_extend` 或 `negative_prompt` 都会改变规格哈希并要求重新 `--confirm`。

万相空镜关闭改写与自定义负面词的 `shots.json` 示例：

```json
{
  "shots": [
    {
      "shot_id": "empty_track",
      "prompt": "清晨红色塑胶田径场空跑道慢推，画面里没有人",
      "seconds": 5,
      "aspect_ratio": "9:16",
      "resolution": "720p",
      "prompt_extend": false
    },
    {
      "shot_id": "blocks_closeup",
      "prompt": "清晨红色塑胶田径场起跑器金属踏板特写，无人入镜",
      "seconds": 5,
      "aspect_ratio": "9:16",
      "resolution": "720p",
      "prompt_extend": false,
      "negative_prompt": "人物、运动员、品牌标识、logo、商标、水印、文字"
    }
  ]
}
```

每份输出目录对应一个 DreamVerse 项目。桥接确认之后，插件最多为该确认提交一次，生成的云任务 ID 先写入插件收据和 `ledger.json`，随后由桥接发起状态轮询。停止本地等待后，运行同一份清单可以继续查询；已完成的文件沿用既有的素材 ID。结果未知且无法读回云任务 ID 时，账本标为 `unknown`，命令以非零码退出，需核对服务收据和对应平台的任务记录。重复运行只检查收据。这一版本没有人工重提命令。

生成完成后，通过 DreamVerse 的 `shot.render` 写入素材池，桥接取回 MP4 和末帧 PNG，并按素材 ID 验证文件摘要。账本记录模型提供方、云任务、计费视频秒（平台未返回时为空）、DreamVerse 操作与素材 ID、本地文件路径。当前流程未编排时间线，因此片段 ID 为 `null`。应在[百炼任务与下载链接有效期](https://help.aliyun.com/zh/model-studio/legacy-wan-text-to-video-api-reference)内完成首次素材回收。

火山方舟 Seedance 2.0 插件和万相插件并列注册。Seedance 密钥只传给本机 DreamVerse 进程的 `DV_ARK_API_KEY`，不写入清单或账本。安装默认注册两个插件，`--provider wanxiang` 或 `--provider seedance` 只更新对应插件。模型规格以插件 facts 内标注的[火山方舟创建视频生成任务 API 文档](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh&redirect=1)为准：方舟官方接口不支持 `prompt_extend` 与 `negative_prompt` 参数，因此 `seedance` 镜头不允许传这两个字段（传入会被桥接拒绝），规避要求请直接写在正向 `prompt` 中。Seedance 的真实账号调用和生成效果尚待拿到密钥后验收。
