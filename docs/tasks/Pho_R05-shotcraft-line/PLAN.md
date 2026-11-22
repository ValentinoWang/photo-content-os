# Pho_R05 把 video-shotcraft 收进制作台：镜头配方库、风格库合并、宣传片产线

用户 2026-11-22：「收束进制作台 形成新的产线 风格库也收束尽量 如果可以就请复用现有管线 如果不可以就算了」。

## 结论：复用现有直出管线，不引入第二套引擎

- shotcraft（上游 Vincentwei1021/video-shotcraft，Apache-2.0，固定在提交 `3ac67b75dd0b3bc2fd807c17f6b7ce35373eef3d`）用 Remotion（React）出片。Remotion 公司使用可能要付费，且会让制作台有两套渲染引擎，**不进制作台**。
- 制作台直出管线：每镜一个 HTML，`window.seekFrame(frame, fps)` 确定地画出该帧，`scripts/video_render/multi_shot.py` 逐帧截图，`compose.py` 合成。宽高任意偶数（横屏 1920×1080 可用）；音轨只要一条按排期对齐的 PCM WAV。
- shotcraft 真正可复用的是**镜头配方卡**（124 张，10 类：camera 10、data 5、effects 15、interaction 11、opening 11、outro 6、rhythm 8、transition 15、typography 22、ui-entrance 21），每张写意图、动作阶段与帧段、参数、已知坑——是「怎么动」的手法，与引擎无关，可照 R283 的做法改写成 seekFrame HTML。
- 先例：R283 已把 Moessif/code-video-showcase（MIT）的九种风格改写进 `scripts/direct_video/style_library/`，用同一渲染器出样张。

## 两层库，分工不重叠

| 层 | 管什么 | 位置 | 来源 |
|---|---|---|---|
| 风格（style） | 整片的色板、字号、视觉语法、运动规矩 | `scripts/direct_video/style_library/`（已有 9 种） | R283 九种 + 本次新增「产品界面」一种（取 shotcraft 的单色板体系与 Ink Press 模板观感） |
| 镜头配方（recipe） | 单镜怎么动：阶段、帧段、缓动、参数、坑 | 新建 `scripts/direct_video/shot_recipes/` | shotcraft 124 张配方卡 |

写镜头时：风格定颜色字号，配方定动作。口播直出线和宣传片线共用这两层库。

## 宣传片产线（新）

和口播直出的差别只在输入与音轨，渲染、合成、检查全部复用：

| 环节 | 口播直出（已有） | 宣传片（新） |
|---|---|---|
| 输入 | 已确认的口播稿和分镜 | 产品简报 + 真实页面截图（已有 browser-runtime 采集） |
| 画幅 | 1080×1920 | 1920×1080 为主，可选竖屏 |
| 节奏 | 配音句级时序 | 音乐节拍图（已有 music_analysis / R223 节拍图） |
| 音轨 | TTS 配音 | 音乐库选曲 + 音效，预混成一条 WAV 交给 compose |
| 镜头 | direct-video-shots 写 HTML | 同上，按配方选镜 |
| 渲染合成 | multi_shot.py + compose.py | 同（不改） |
| 终检 | lint + 黑帧 + 预览帧 | 同 + shotcraft 审美准则中可机判的条目 |

## 分段

| 段 | 内容 | 谁做 | 依赖 |
|---|---|---|---|
| P1 配方库入库 | 124 张卡 + 来源说明 + 许可原文进 `shot_recipes/`，生成 `index.json`（id、类别、一句话、适用、时长、能量、标签、竖屏是否适用），README 写上游提交和改写规则 | 执行方（机械） | 无 |
| P2 试点改写 | 挑 8 张适合口播和宣传片的配方，按 seekFrame 硬规则改写成 HTML 镜头样张，竖屏、横屏各渲一版，lint 通过、逐张看联系表 | 执行方（判断型） | 无（直接读上游卡） |
| P3 风格库合并 | 新增「产品界面（ui）」风格（html/json/jpg/mp4，照 R283 格式）；shotcraft `aesthetic-rules.md` 可机判条目并进 `scripts/direct_video/rules/` | 执行方（判断型） | 无 |
| P4 宣传片后端 | 音轨预混（音乐库 + 节拍对齐 + 音效）→ 一条 WAV；宣传片清单生成；横屏支持贯通 lint/预览检查 | 执行方 | P1–P3 合格后 |
| P5 Studio 入口 | 先出设计稿（当前会话模型画），用户认可后派执行方实现 | 总控出稿 | P4 |
| P6 收尾 | direct-video-shots 技能加「按配方写镜头」；删本机 video-shotcraft 克隆，父目录 README 改掉那一行 | 总控 | P1–P5 |

不搬：Remotion 模板与 Motion Workbench、demos/gallery 视频、shotcraft 的剪映导出（制作台已有 `create_jianying_roughcut_draft.py`，P4 比对后只留一套）。shotcraft 自带的 BGM、音效只在逐文件许可允许商用时才入制作台音乐库，否则不搬。

渲染一律在开发机 `photo-dev` 上跑。
