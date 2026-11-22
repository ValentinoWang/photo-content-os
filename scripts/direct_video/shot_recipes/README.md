# 镜头配方库

来源：Vincentwei1021/video-shotcraft，提交 `3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d`，Apache-2.0。手法卡、画廊封面、动画源码原样搬入，`recipe_library.py --check --upstream <克隆>/references/shots` 逐字节核对。

## 封面、样片、动画源码

| 字段 | 内容 | 位置 |
| --- | --- | --- |
| `poster` / `poster_source` | 上游画廊封面 50 张（`upstream`）；其余有动画源码的 72 张，用上游自己的 `workbench/scripts/render-demos.mjs` 渲染后取 90% 处一帧（`render`，和 50 张官方封面比最接近）；卡里列了几个镜头的取第一个；上游没有源码的 2 张为空 | `media/posters/` |
| `clip` | 上游画廊样片 87 个，共 62 MB，不进 git；`python3 scripts/direct_video/recipe_library.py --fetch-clips` 按 `media/clips.json` 的 SHA-256 下载到 `~/.photo-content-os/media/shot_recipes/clips/`（可用 `SHOT_RECIPE_CLIP_DIR` 改） | 本机 |
| `demo` | 上游 Remotion 动画源码：122 张卡有，另有 2 个上游没配卡的镜头。连同共用组件 `_fixtures`、贴图 `_textures`、旧版 `_legacy` 一起原样搬入，可以直接渲染（见下节）。只作写镜头时的参照，不进制作台的出片管线 | `demos/<类别>/<id>/` |

上游画廊的样片有一部分比封面旧（例如 blur-slide 的样片还是占位文案），选镜以封面为准。

## 上游原样代码（`upstream/`）

`upstream/` 保留上游的目录结构，不用另找克隆就能跑上游自己的脚本：

| 目录 | 内容 |
| --- | --- |
| `workbench/` | Remotion 工作台和批量渲染脚本 `scripts/render-demos.mjs` |
| `template/` | 上游的 Remotion 成片模板 |
| `references/` | 美学规则、流程、音效设计、卡点、终审、镜头序列等文档（`shots` 就是本目录各类别下的配方卡，不重复存） |
| `shot-polish/` | 上游逐镜打磨的笔记和对照脚本 |
| `gallery/api/library.json`、`gallery/translations.js` | 工作台用来取中文名和时长的画廊数据 |
| `demos` | 链接到本目录的 `demos/`，动画源码只存一份 |

没搬的部分：`ClipCardLooping` 镜头（要真实视频素材，上游自己的批量渲染也跳过它，还依赖上游 `assets/lib`）；上游的背景音乐，以及 `template/public/audio` 里的音效（许可没核实，只留 `ATTRIBUTION.md`）；画廊网站、剪映导出、发布脚本（制作台有自己的剪映导出）；README 的各语种译本。

重新渲染（150 个镜头约 30 分钟）：

```bash
cd scripts/direct_video/shot_recipes/upstream/workbench
npm ci
node scripts/render-demos.mjs --out <目录>        # 只渲几个：--only BlurSlide,MultiplaneReal
```

渲染完成后，再跑 `python3 scripts/direct_video/recipe_library.py --posters-from-renders <目录>` 和 `python3 scripts/direct_video/recipe_library.py`，重新生成 `render` 封面。

`npm ci`（会顺带跑 `scripts/gen-index.mjs`）会生成 `node_modules/`、`public/` 下的链接和 `src/cards/*-index.ts`，上游的 `.gitignore` 已把它们排除。

## 类别数量

| 类别 | 数量 |
| --- | ---: |
| camera | 10 |
| data | 5 |
| effects | 15 |
| interaction | 11 |
| opening | 11 |
| outro | 6 |
| rhythm | 8 |
| transition | 15 |
| typography | 22 |
| ui-entrance | 21 |

## 竖屏适用

逐卡对照动作阶段、构图及节奏。可在 9:16 内重设坐标或使用短文案，且能保留主要动作与节奏的配方标为 `true`。需要重排多区构图、重标运镜或复核可读性的配方标为 `null`。这些判断用于选镜，实际镜头仍须检查字是否读得清、字幕区是否留空。

| 结论 | 数量 |
| --- | ---: |
| 可用于竖屏（`true`） | 75 |
| 待判断（`null`） | 49 |

| 待判断配方 | 需要复核的内容 |
| --- | --- |
| [basic-3d-scene](camera/basic-3d-scene.md) | 三站姿态和末站俯瞰按宽卡与世界坐标反解。 |
| [cursor-flyover](camera/cursor-flyover.md) | 原卡明确说明换成竖屏需重标整张相机表。 |
| [depth-layer-moves](camera/depth-layer-moves.md) | 三层横移巡览依赖不同宽度的卡组和掠屏距离。 |
| [graze-face-tour](camera/graze-face-tour.md) | 低机位路线沿侧栏、顶栏和列表展开，需重新对位。 |
| [overhead-camera-moves](camera/overhead-camera-moves.md) | 桌面卡阵一式需要同框横排并依次横扫。 |
| [space-camera-moves](camera/space-camera-moves.md) | 爆炸分解一式需要在主物体左右同时展示注释。 |
| [steep-tilt-glide](camera/steep-tilt-glide.md) | 强透视侧立后的 UI 仍需沿长横向轨迹掠过。 |
| [terminal-3d](camera/terminal-3d.md) | 需兼顾终端窗可读性与拉远后三窗同框。 |
| [chart-live-moves](data/chart-live-moves.md) | 示波流线的横向读数窗口及跟拍需在窄画幅重新量定。 |
| [gauge-readout-moves](data/gauge-readout-moves.md) | 开机自检一式需要并排三块表盘且保留刻度。 |
| [timeline-travel](data/timeline-travel.md) | 水平时间轴要同时交代多个版本刻度和停靠点。 |
| [assemble-then-type-flyin](effects/assemble-then-type-flyin.md) | 组件到位位置取决于原生 12 栏画板。 |
| [brand-frame-snap](effects/brand-frame-snap.md) | 固定宽幅录屏窗、切换控件与两版布局须一起重排。 |
| [radial-ripple-phone-chips](effects/radial-ripple-phone-chips.md) | 中央手机两侧需要同时显示可读的说明胶囊。 |
| [scanline-annotate-focus](effects/scanline-annotate-focus.md) | 扫描、逐区框选和注释依赖具体宽窗的六区布局。 |
| [scanline-assemble-flyin](effects/scanline-assemble-flyin.md) | 每个组件的落位帧由画板槽位下缘推算，重排会改节奏。 |
| [autolayout-gap-dial](interaction/autolayout-gap-dial.md) | 多枚控件在同一排随间距数值实时撑开。 |
| [canvas-materialize-moves](interaction/canvas-materialize-moves.md) | 面板行转成画布卡的一式依赖跨容器路线。 |
| [chip-grid-single-select-blackout](interaction/chip-grid-single-select-blackout.md) | 固定尺寸的 3+2 选项需一同出现，缩窄后有可读性风险。 |
| [collab-cursor-moves](interaction/collab-cursor-moves.md) | 五个带名牌光标需要在画布驻留并聚拢，窄屏易遮住内容。 |
| [type-and-filter](interaction/type-and-filter.md) | 真实界面要展示搜索结果网格到详情的连续变形。 |
| [crane-rise-reveal](opening/crane-rise-reveal.md) | 近景条目退到整面看板，末帧的看板列宽需复查。 |
| [dataviz-landscape-open](opening/dataviz-landscape-open.md) | 支流、主干与标签需要在低空飞越中保持分布和可读性。 |
| [magician-card-flourish](opening/magician-card-flourish.md) | 卡片占画高 86%，落位后右侧仍要逐行显示文案。 |
| [orbit-ring-title-open](opening/orbit-ring-title-open.md) | 八张横版卡要绕宽椭圆运行，并给居中标题留空间。 |
| [text-as-mask](opening/text-as-mask.md) | 粗体标题字窗既要容纳可识别的看板画面，又要接管全屏。 |
| [neon-triple-marquee](outro/neon-triple-marquee.md) | 三条对滚巨字需要保留完整可读词段，同时维持相位。 |
| [outro-group-photo-launch](outro/outro-group-photo-launch.md) | 全片元素要在字标周围同框合影，终帧密度需重算。 |
| [panel-grid-moves](rhythm/panel-grid-moves.md) | 多个斜格要同时容纳同一主体的三个机位。 |
| [quad-split-parallel-scenes](rhythm/quad-split-parallel-scenes.md) | 四路场景并行，窄画幅分格难保每路都清楚。 |
| [card-flip-reveal](transition/card-flip-reveal.md) | 依次翻牌需要在同一排保留三张可读卡片。 |
| [card-flock-tumble](transition/card-flock-tumble.md) | 三张页卡需同框成阶梯，末拍还要保留横贯巨字。 |
| [line-carry-transition](transition/line-carry-transition.md) | 横移时笔头固定在画面右侧，线速和镜头位移绑定。 |
| [mosaic-reframe](transition/mosaic-reframe.md) | 12 张瓦片在三套宽屏坐标布局之间插值。 |
| [transition-hidden-cut](transition/transition-hidden-cut.md) | 对撞一式的两侧对比海报和斜缝需要重新构图。 |
| [countdown-arc-scatter](typography/countdown-arc-scatter.md) | 九个数字共享一条大弧，改窄后需确认弧端与标题换位。 |
| [document-typewriter-reveal](typography/document-typewriter-reveal.md) | 正文与侧栏都要在撤到全窗时可读。 |
| [lead-word-zoom-assemble](typography/lead-word-zoom-assemble.md) | 首词缩回、整行左滑及右侧词槽在同一时窗卡位。 |
| [pill-chip-slot-cycle-handled](typography/pill-chip-slot-cycle-handled.md) | 句干、动态宽度胶囊和句尾必须始终同排。 |
| [text-column-converge](typography/text-column-converge.md) | 两词固定在左右边缘、零收缩，较长特性词可能占满间距。 |
| [word-relay-filmstrip](typography/word-relay-filmstrip.md) | 左侧滚动卡列要和右侧大词保持精确垂直对齐。 |
| [bezier-source-converge-merge](ui-entrance/bezier-source-converge-merge.md) | 左四源到右侧单点的布线和包裹飞行都依赖横向空间。 |
| [card-stack](ui-entrance/card-stack.md) | 九卡以固定横移展成扇面，再抽中心卡。 |
| [carousel-3d](ui-entrance/carousel-3d.md) | 八卡圆环至少要保留侧卡、正前卡和环下字幕。 |
| [deck-deal-flyin](ui-entrance/deck-deal-flyin.md) | 牌堆、相邻面板与最后的满板俯瞰构成完整路线。 |
| [doc-park-left-pill-deal](ui-entrance/doc-park-left-pill-deal.md) | 左部文档要持续可见，右部还要排药丸和字幕。 |
| [integration-hub-map](ui-entrance/integration-hub-map.md) | 五条光管和五枚图标都要可辨且同时连入中枢。 |
| [page-waterfall-wall](ui-entrance/page-waterfall-wall.md) | 3–4 列截图需各自反向滚动，保留可辨的页面密度。 |
| [wall-reveal-moves](ui-entrance/wall-reveal-moves.md) | 整墙点亮和蓝图描线依赖多区网格和长边轮廓。 |

## 标签与校验

上游 50 张卡提供标签，索引保留其标签并标记 `tags_source: "upstream"`。另外 74 张卡的索引记录为空数组和 `tags_source: "missing"`。名称、一句话、适用、时长和能量都是必填字段。

从仓库根目录运行 `python3 scripts/direct_video/recipe_library.py` 可重建索引。运行 `python3 scripts/direct_video/recipe_library.py --check --upstream <上游克隆目录>/references/shots` 可检查索引、卡片、来源说明及许可。来源文件见 [ATTRIBUTION.md](ATTRIBUTION.md) 与 [Apache-2.0 许可原文](LICENSE-video-shotcraft.txt)。
