# 直出双语字幕

Photo 先用 `video_subtitles.subtitle_translation_plan` 按F1–F8规则切出将实际显示的每条中文字幕，冻结30fps的 `text/startFrame/endFrame`，生成 `subtitlePlan`。Media 在配音ready后，通过既有本机翻译入口接收该计划，校验中文、句级时序、帧范围及当前切镜点，再对每个显示段生成一条完整意群英文。来源句只作上下文，不先翻整句再按字数/时长切词。

英文存入 `narration.subtitleCues[].englishText`，与该条中文和帧范围绑定。Photo逐条核对冻结计划与实际中文排版相同后直接烧录，不拆分、拼凑或自行翻译英文；改了中文字幕切分点或切镜点须重新准备翻译计划。旧的 `sentenceTimings[].englishText` 不会再被比例切分：未提供显示段翻译时明确报 `photo_subtitle_translation_plan_required`，由正常翻译入口重新生成。历史数据保留可读；全无英文仍支持中文单层。

每条英文须自成意群，不留下孤立代词、未完成动词或悬空连词，不以标点开头；语义由翻译模型负责，程序校验条数、顺序、中文原文、帧范围及非空纯文本，不用词语黑名单代替翻译判断。Photo不联网取译文、不合成英文配音，也不重新合成已有中文音轨。

中文保留每行14字/最多两行及禁则。英文与中文共用75%不透明黑底框、紧贴中文下方，默认中文字号58%；超宽先缩到45%下限，再按词折成至多两行。放不下明确报 `photo_subtitle_english_too_long`，不截断译文。英文#cfcfcf，整体底框保持底部20%安全区；不满足报 `photo_subtitle_layout_rejected`。

SRT及帧侧车逐cue保留完整中文、完整英文和精确帧区间；烧录以帧侧车为准。`.subtitle-style.json`记录实际字号、折行和底框几何。缺失/过期翻译不可静默退回单层。

回归运行 `test_subtitle_display_translation_r8.py`、`test_bilingual_subtitles_r6.py`、中文/F7–F8、Photo全量pytest与本地CI。测试中的合成视频用于检查渲染器，不代表作品重渲染或用户采用。
