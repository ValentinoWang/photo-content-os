# 数字人口播片段

`python scripts/video_tools/generate_avatar_clip.py --video 底片.mp4 --audio 配音.wav --out-dir 输出目录 --material public-sample` 只计算分段和费用，不调用云端。加 `--live` 才提交；本人素材用 `--material self --owner-consent "本人同意原话"`。密钥从 `DASHSCOPE_API_KEY` 或 `--env-file` 读取。

程序接口为 `generate_avatar_clip(video, audio, out_dir, *, material, owner_consent, api_key, live, max_seconds=110, wait_seconds=900, transport=None)`，路径使用 `Path`，返回分段计划及输出路径。失败抛出 `AvatarError`，可读取 `code` 和经筛选的 `provider_code`。transport 使用与 requests Session 兼容的 get/post。

账本保存在输出目录。提交收到 HTTP 4xx 后记为 `rejected`，下次运行会重新上传并提交。收到 `avatar_account_arrears` 时，先到阿里云控制台处理账号再重试。

没有任务号且结果未知时，先核实百炼是否已创建任务。确认没有任务后，运行 `python scripts/video_tools/generate_avatar_clip.py --out-dir 输出目录 --forget-unknown 0 --reason "已核实云端没有创建任务"`。段号从 `0` 开始，与 `segment-0000.mp4` 的数字一致。这条命令只更新账本并记录操作原话，随后可重新运行原生成命令。

完成片旁的 JSON 标记为 AI 生成。制作台入口另行实现。
