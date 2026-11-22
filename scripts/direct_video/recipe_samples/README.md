# 镜头配方改写样例

把 `../shot_recipes/` 里的配方卡（video-shotcraft，Apache-2.0，上游提交 `3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d`）按直出渲染器的规矩改写成 `window.seekFrame` HTML 的样例。每个目录一张配方：`portrait.html`（1080×1920，口播竖屏）、`landscape.html`（1920×1080，宣传片横屏），`notes.md` 写改了配方哪里、做不到的地方。mp4 和末帧 jpg 是样张。

渲染：`render_recipe_sample.sh <id> portrait|landscape`，和风格库样张共用同一把渲染锁；需要 `VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER` 两个环境变量，写法同 `render_style_sample.sh`。

| 配方 | 类别 | 为什么挑它 |
| --- | --- | --- |
| `blur-slide` | 文字 | 口播开场、宣传片标题都能用的最基础字效 |
| `marker-underline-title` | 文字 | 一句话里点出一个关键词，口播最常见的强调 |
| `gauge-readout-moves` | 数据 | 数字跳动后停住，对应「数字落地」这种形态 |
| `beat-cut-moves` | 节奏 | 跟音乐重拍连推三次，宣传片按节拍图排镜的基本手法 |
| `product-card-progressive-assemble` | 界面入场 | 产品卡从骨架逐块装好，宣传片展示功能 |
| `list-reveal` | 界面入场 | 列表逐项展开，口播讲步骤、宣传片讲功能清单 |
| `circle-match-iris` | 转场 | 从按钮开圈切进下一屏，两镜之间有因果的转场 |
| `spotlight-hero-card` | 开场 | 聚光落在主卡上，宣传片开场 |

写新镜头时：风格（`../style_library/`）定颜色字号，配方定动作；配方里默认禁用的元素（霓虹、胶囊标签等）换成风格里的同等元素。
