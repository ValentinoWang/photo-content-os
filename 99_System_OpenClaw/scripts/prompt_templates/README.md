# Prompt 模板说明

这里保存素材库命名和结构处理的可复用 prompt。`04_generate_ai_prompt.py` 会把这些模板复制到项目的 `_ai_analysis/prompts/workflows/`，并替换项目路径等基础变量。

这些 prompt 只负责让 LLM 输出结构化建议；真正移动、重命名、合并仍由脚本执行并做路径校验。

如果某个素材有用户明确说过的创作意图，例如“这张不是普通候场，而是为了表达全景相机不便捷性”，应写入项目内 `_ai_analysis/user_intent_notes.md`。`04_generate_ai_prompt.py` 会把这份笔记注入单素材 prompt、项目总览 prompt 和 L3 结构 prompt。

命名时必须区分素材层和作品层：L3 源文件名写画面事实和素材特质，不被某一个作品风格锁死；当前项目的风格候选写入 summary、资产卡片、剪辑方案或输出成片名。只有风格化衍生物、发布成片、封面候选或交付副本，才把作品风格写进文件名。
