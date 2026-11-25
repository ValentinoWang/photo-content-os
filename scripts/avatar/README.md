# 数字人口播片段

`python scripts/generate_avatar_clip.py --video 底片.mp4 --audio 配音.wav --out-dir 输出目录 --material public-sample` 只计算分段和费用，不调用云端。加 `--live` 才提交；本人素材用 `--material self --owner-consent "本人同意原话"`。密钥从 `DASHSCOPE_API_KEY` 或 `--env-file` 读取。

程序接口为 `generate_avatar_clip(video, audio, out_dir, *, material, owner_consent, api_key, live, max_seconds=110, wait_seconds=900, transport=None)`，路径使用 `Path`，返回分段计划及输出路径，失败抛出 `AvatarError`（消息为失败码）。transport 使用与 requests Session 兼容的 get/post。

账本保存在输出目录。提交中断且没有任务号时会停止并报 `avatar_submit_unknown`，须先人工核实云端任务及费用，不要直接删除账本重试。完成片旁的 JSON 标记为 AI 生成；制作台入口另行实现。
