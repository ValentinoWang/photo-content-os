# 直出双语字幕

Media 在配音 ready 之后显式用本机模型生成英文翻译，逐句写入交接 descriptor 的 `narration.sentenceTimings[].englishText`。Photo 不翻译、不联网取译文、不合成英文配音。无英文保持原中文单层；部分句子有英文但其余缺失会明确拒绝，避免静默漏字幕。

中文仍按 F1–F8 的帧边界、跨镜续接、每行14字/最多两行及标点规则排版。英文跟随同句中文片段，按词边界及片段时长比例分配；不能精确分配的极短译文会在续接片段重复，仍是本镜新 cue，不延用旧 cue 的时间范围。英语不是词级实测对齐。

英文与中文共用一个75%不透明黑底框，紧贴中文下方。英文默认中文字号58%，单行超宽先缩到45%下限，再折成至多两行；超长明确报 `photo_subtitle_english_too_long`，不截断译文。英文 #cfcfcf 比中文白字更暗，最差白背景上对比度超过4.5:1。整体底框保持画面底部20%安全区；不满足时报 `photo_subtitle_layout_rejected`。

`subtitles.srt` 含中文与对应英文；帧侧车逐 cue 保留 `text`、`englishText` 和精确帧区间，烧录以帧侧车为准。`.subtitle-style.json` 的 bilingualLayouts 记录各片段实际字号、折行和底框几何。缺失或不一致的时序/译文不通过单层回退掩盖。

运行 `tests/test_bilingual_subtitles_r6.py`、中文字幕/换行/F7–F8回归、Photo全量pytest和 `bash scripts/run_local_ci.sh`。合成黑白测试视频只检验渲染器，不是实际作品或人工采用证明。
