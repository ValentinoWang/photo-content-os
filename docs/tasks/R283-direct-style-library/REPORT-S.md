# R283 S 样张段汇报

完成范围：TASK.md 第 0 节与 S 样张段。九种当前版本均已真渲染并逐张查看六帧联系表、1080×1920 原尺寸末帧，按 S 合格线判为合格。此结论只覆盖样张数据与渲染脚本，不代表 B 后端、前端接入、模型生成七镜或 H-01–H-03 人工验收通过。

## 文件与边界

- 数据：`scripts/direct_video/style_library/` 共 39 个文件，九种各有 HTML、JSON、JPG、MP4，另有 `index.json`、`README.md`、`LICENSE-code-video-showcase.txt`。
- 新渲染脚本：`scripts/direct_video/render_style_sample.sh`。用 worktree `.venv`、现有 `lint.py` 和 `multi_shot.py`；Playwright、浏览器由 `VIDEO_RENDER_PLAYWRIGHT_MODULE`、`VIDEO_RENDER_BROWSER` 必填配置。字体可由 `VIDEO_RENDER_FONT` 指定，默认 macOS 华文黑体 Medium。
- 风格顺序固定为 `flat, math, launch, whiteboard, cyber, ink, dataviz, pixel, code`。
- README 已注明「改写自 Moessif/code-video-showcase 的风格配方（MIT），上游提交 2a5fb1f」，逐种改写说明与 JSON `adapted` 一致；许可全文与 reference 原件逐字节相同。
- 未编辑 B 段文件、R278 设计稿与 lib-data、需求卡、人工验收记录、主检出、Studio 状态目录、真实素材或剪映草稿；未使用 8765–8769 端口，未启动服务，未联网取资源。
- 开工读取人工队列，相关 R276、R277、R278 仍为 PENDING，未改写或代签。项目 `develop/harness/fullstack-ai-harness.md` 在此 worktree 缺失，已读 Core 同名权威规则及项目 adapter；没有修补此范围外文件。

## 逐种结果

九份规则检查均为 **0 ERROR、0 WARN**。全部保留统一台词、页眉、约 50% 与约 25% 的比较，并加「示意图，非原始数据」声明。技术替代均在现有渲染限制内完成，没有待拍板的样张缺口。

| id／名字 | S 合格线 | lint WARN | 对原配方的改写 | 限制内替代／做不到的部分 |
| --- | --- | --- | --- | --- |
| flat／扁平插画 | 合格 | 无 | 配方是横屏 3 秒的四季太阳系卡点片；改成竖屏后把太阳系构图放大占满内容区上半，数字和胶囊标签移到下方；去掉卡点冲击、常驻旋转和标题扫光，改成跟口播逐句弹出；ZCOOL 快乐体换成锁定的华文黑体，靠黄色胶囊和珊瑚高光条保留活泼感。 | 无阻塞缺口；星点和光锥是固定种子画布图形，未使用外部图片。 |
| math／数学动画 | 合格 | 无 | 配方是横屏 3 秒、用圆链画心形的傅里叶片；改成竖屏后作图区放大到内容区上部，公式从右侧挪到下方；圆链改成画结论区域的边，只在出场时转一圈；公式排版库换成普通文字加矢量画的约等号；去掉右侧实时读数、底部等化器和公式呼吸发光。 | 无阻塞缺口；没有 KaTeX，约等号用内联 SVG，保留圆链画边。 |
| launch／极简发布会 | 合格 | 无 | 配方是横屏 3 秒的戒指发布片，用 Three.js 金属戒指；改成竖屏后戒指用画布网格自己着色画出来，放在上半屏，下方放两栏大数字；巨字从三句口号改成「以为」「实际」两个数字；戒指侧面的变色细环改成跟数字同步亮到一半和四分之一；去掉卡点重低音式的逐拍闪字，只留一次扫光。 | 无阻塞缺口；没有 Three.js，金属反射为画布面片着色近似，并非真实三维渲染。 |
| whiteboard／手绘白板 | 合格 | 无 | 保留暖纸、马克笔、逐笔画和沸腾线；横屏三步骤改为竖屏课堂实验加比例对照。滤镜改成固定种子的路径抖动，手写字体改为锁定黑体的轻微固定歪斜，去掉跟笔缩放和镜头移动，结尾冻结抖动。 | 无阻塞缺口；没有手写字库或 SVG 滤镜，以锁定字体的固定歪斜和种子路径抖动替代。 |
| cyber／赛博故障 | 合格 | 无 | 保留紫粉天空、条纹日落、城市、透视网格与扫描线；将横屏展示片改成竖屏十六格比例图。去掉 HUD、时间码、滚动和每拍故障，改为出场一次短错位与顺序亮格，不用外部字体。 | 无阻塞缺口；原配方反复通道故障改为出场一次水平错位，扫描线与网格不滚动。 |
| ink／水墨国风 | 合格 | 无 | 保留宣纸纤维、层峦、浓淡墨迹、竖排和朱印；将横屏山水景观改成竖屏上下两条笔痕的比例对照。以多频率固定山脊替代动态 fbm，以排版替代书法字体，去掉舟鸟、漂移云雾和砸章。 | 无阻塞缺口；没有书法字体，以竖排、毛边墨迹和朱印替代；山脊为固定多频率曲线。 |
| dataviz／数据可视化 | 合格 | 无 | 保留暗底紫红光雾、发光柱、玻璃注释和轻透视；横屏七条竞速改成竖屏两根同标尺对照柱，去掉年份大字、排名和年份脉冲，数字顺序落定，粒子和背景静止。 | 无阻塞缺口；去掉年份与排名竞速，背景光雾和粒子固定，透视角度不动。 |
| pixel／8-bit 像素 | 合格 | 无 | 保留 FC 有限色板、低分辨率整数精灵、分层地面和逐格移动；横屏跑酷改成竖屏课堂和同学注意比例，去掉金币、分数、生命、倒计时与常驻跑动。数字自行画点阵，中文使用锁定黑体。 | 无阻塞缺口；大数字自行画点阵，中文仍是锁定字体，没有专用像素字体。 |
| code／代码录屏 | 合格 | 无 | 保留深色编辑器、语法色、行号、逐字输入和实时预览观感；将横屏文件树加左右双栏改为竖屏上代码下预览，代码压缩为五行实验数据。去掉跟光标镜头、时间轴、无关文件树和运动圆，展示代码不执行。 | 无阻塞缺口；这是生成的编辑器视觉样例，不启动 IDE、不执行展示中的代码。 |

## 逐张查看记录

以下是本人看过当前联系表和原尺寸末帧后的具体发现，详细记录保存在仓库外 `visual-notes.json`。

- **flat**：补充示意图声明后的最终版已重渲染并复看，页眉、3/12亮起、两组近似数字与声明完整，最终版没有裁切或重叠。
- **math**：首帧有完整点阵方框；4秒青色半区，6秒圆链正画金色实际区域；末帧九个金点占三十六点四分之一，区域和算式一致。两行算式、来源声明未重叠，底部安全留白清楚。
- **launch**：首帧金属环和反射成立；环面缓慢转正、银色半环先亮、四分之一渐变环后亮。最终大数字两栏与结论清楚，来源声明完整；保留画布面片近似金属，未使用Three.js。
- **whiteboard**：首帧有教室门、地面与柱底线；人物、聚光灯、同学逐笔出现，后半段先黑柱再红柱。末帧柱高400与200对应一半，红色双箭头和旁注可读，标签与来源完整，画完笔尖消失。
- **cyber**：紫粉条纹落日、城市剪影、透视网格和霓虹切角格一眼可辨。16格先亮8格洋红，再剩4格青，前后数字对应，最后比较符与来源不重叠。出场仅短暂横向错位，非持续闪屏。
- **ink**：宣纸纤维、分层淡山、朱红方印与右侧竖排清楚；第一帧有两条灰墨参照，最后上黑笔痕700、下红笔痕350，红色曲线与「半」相呼应，出处留在安全区。底部景物为固定示意，未声称真实书法或原始图。
- **dataviz**：首帧有玻璃槽与底线，4秒先长以为柱，6秒实际柱出现且前提退灰。末帧同基线两柱高低关系、差值虚框和「一半」注释清楚，轻透视未使文字裁切，来源安全。
- **pixel**：首帧有门、人物、八名同学与分层地面，4秒四位黄同学，末帧两位黄同学占八人的四分之一。大数字自绘点阵可读，中文标签和出处未压住数字，硬像素边一致。
- **code**：首帧编辑器与起始代码成立，逐行写入50和25后出现对应预览。末帧五行代码、两列大数字和出处清楚，修复容器后没有越界，结尾光标与高亮消失，节点复用使最终停留稳定。

## 渲染与复现证据

证据根目录：`$HOME/.photo-content-os/evidence/R283-direct-style-library/`。以下路径均相对此根；联系表与末帧是最终输出，没有以旧截图代替当前版本。

- 实际浏览器 viewport 为 1080×1920，deviceScaleFactor 为 1；帧画布同尺寸。导出 JPG、MP4 为 360×640。样张是完整固定视频画布，不涉及长页面滚动或 Studio 桌面／手机页面验收。
- 每种由项目渲染器实际生成 360 帧、30 fps；FFprobe 确认 12.000 秒、H.264、只有一条视频流、无音轨，九段均通过完整 FFmpeg 解码。
- 联系表为 1620×480，六格取帧 0、60、120、180、250、359，对应 0、2、4、6、8.333、11.967 秒；最后一格是 12 秒片段的末帧，并非额外第 361 帧。
- 每种第 252–359 帧的原始 PNG 哈希只有一个取值，证明 8.4 秒后完全静止。补充无头检查还验证了六个时点的文字边界、0→359 反向跳帧后的同帧一致性；修复后的九种均无页面错误、无文字越界、同帧相同。
- `verification.json` 记录每套 HTML／JSON／JPG／MP4 的 SHA-256、联系表与末帧哈希、完整解码结果和捕获时间；这些哈希均与当前文件匹配。`work/<id>/capture.json`、`shot-status.json`、`lint.json`、`render.log` 保留逐种记录与运行时身份。
- `qa-layout.initial.json` 保留初次检查，`qa-layout-code.json` 与汇总 `qa-layout.json` 保存代码风修复后的结果；没有覆盖原失败记录来假报通过。
- 所有浏览器均无头；渲染和补充检查共用 `.render.lock` 内核锁。实测并发入口被锁阻挡；运行结束锁可立即获取，无头浏览器残留为 0。浏览器用完即关闭。
- 原尺寸临时帧目录 `work/<id>/out/` 已全部删除，仅保留末帧、联系表与小样等复核文件。采样可用磁盘最低约 4.1 GiB，收尾约 6.22 GiB；脚本每秒检查运行中空间，未触发低于 3 GiB 停止阈值。

| id | 最终联系表 | 最终原尺寸末帧 | 最终导出完成时间（台北时间） |
| --- | --- | --- | --- |
| flat | `work/flat/sheet.png` | `work/flat/last.png` | 2026-10-27 02:04:00 |
| math | `work/math/sheet.png` | `work/math/last.png` | 2026-10-27 01:53:15 |
| launch | `work/launch/sheet.png` | `work/launch/last.png` | 2026-10-27 01:56:02 |
| whiteboard | `work/whiteboard/sheet.png` | `work/whiteboard/last.png` | 2026-10-27 02:01:50 |
| cyber | `work/cyber/sheet.png` | `work/cyber/last.png` | 2026-10-27 02:04:43 |
| ink | `work/ink/sheet.png` | `work/ink/last.png` | 2026-10-27 02:07:56 |
| dataviz | `work/dataviz/sheet.png` | `work/dataviz/last.png` | 2026-10-27 02:09:36 |
| pixel | `work/pixel/sheet.png` | `work/pixel/last.png` | 2026-10-27 02:10:06 |
| code | `work/code/sheet.png` | `work/code/last.png` | 2026-10-27 02:10:36 |

完整相对路径示例：`$HOME/.photo-content-os/evidence/R283-direct-style-library/work/flat/sheet.png`。库卡片、预览片段分别是软件内 `scripts/direct_video/style_library/<id>.jpg`、`<id>.mp4`。

## 修复与轮次

- flat 第一次在第 237 帧触发渲染器默认 120 秒超时，脚本返回非零，没有把部分帧当完成。单镜预算显式改为 600 秒后完整渲染；补统一示意图声明后又完整渲染并复看最终版。合计三次调用，其中两次完整成功。
- whiteboard 保留出场沸腾线，但将抖动时钟在 8.3 秒冻结，结束后不再动。
- ink 使用配方内更深的印章红 `#b03a2e`、墨灰 `#4a4640`，使纸底上的文字达到对比度要求。
- code 预检先发现来源容器未闭合，修复后又发现每帧重建节点带来 38 个像素的结尾变化；改为复用节点、只写变化的字符，再检查同帧与停留均相同，随后才完整渲染。预检三轮、完整渲染一次。
- 其余风格各完整渲染一次。所有风格修改与复看均在每种最多三轮预算内。

## 检查结果与交接事项

| 检查 | 结果 |
| --- | --- |
| 九套当前文件、JSON 字段、顺序、README 改写文字与许可比对 | 通过 |
| 九份 HTML 的现有 `lint.py` | 0 ERROR、0 WARN |
| 当前源／输出哈希、实际帧数、尺寸、静止尾段、无声音轨与完整解码 | 全部通过，见 `verification.json` |
| 六时点文字边界、同帧复现与 8.4 秒后停留 | 九种通过，见 `qa-layout.json` |
| `bash -n scripts/direct_video/render_style_sample.sh`、最终脚本 Python 解析与非法 id 拒绝 | 通过 |
| 缺 Playwright／缺浏览器环境变量、非法 id、真实超时错误传播、并发锁 | 均实测失败退出或阻挡，未启动替代浏览器／渲染路线 |
| 新渲染脚本及库 HTML／JSON 的运行时本机路径检查 | 20 个文件、0 命中，见 `new-file-safety.json` |
| `bash scripts/check_runtime_contract.sh` | 通过 |
| `validate_music_analysis_registry.py`（显式配置 Core UI_COPY_QUALITY_CHECKER） | 通过：126 ids、121 copy entries |
| `check_repository_safety.py --base origin/main` | 已跟踪文件范围通过；见下方新媒体范围限制 |
| `check_obsidian_doc_sync.py`（显式设置 OBSIDIAN_ROOT） | 失败：3 项 source-newer-than-target |
| `check_outline_contract.py .`（显式设置 OBSIDIAN_ROOT） | 被同一 Obsidian 同步失败阻断，见 `outline-check.log` |
| `validate_content_os_task.py --help`、`validate_jianying_draft.py --help` | 通过 |
| pytest 全量、模型／配音调用、生产接入／七镜生成、人工 H-01–H-03 | 未执行；本段按任务预算不跑全量 pytest，也不代做 B／前端／人工验收 |

需要总控处理的两项范围外问题：

1. **新媒体安全规则冲突**：库里的 9 JPG＋9 MP4 均为本任务代码生成的合成样张，按任务放在指定目录。它们尚未跟踪；直接对这 18 个新路径应用现有安全规则均命中媒体扩展名限制（`new-file-safety.json`）。上面的 tracked-only 安全检查通过不能代表这些新媒体已获提交许可。S 段没有修改安全规则、媒体白名单、基线或暂存区；后续提交前需总控按现行安全规则解决这个真实冲突。
2. **原执行文档同步失败**：`local_execution_to_obsidian_collaboration_v2`、`local_execution_to_obsidian_editing_handoff_v2`、`historical_jianying_evidence_is_not_production` 报本地源时间晚于 Obsidian 目标。涉及未改动的 `scripts/README.md`、`docs/execution-rules.md` 等，相关本地文档 diff 为空。S 不改 Obsidian 或范围外执行文档，不降低同步标记；不能据此声称全局质量检查全绿。

B 段现在可使用真实九套完整文件；S 无需 B 修改样张。未运行或更改 B 的实现／测试，不以本报告替代 REPORT-B。

## Git 与收工状态

- **业务项目**：HEAD 仍为 `130c931`。S 变更留在当前 worktree：`scripts/direct_video/style_library/`、新脚本和本汇报。收尾 `git status --short` 共 13 行；其中后端 7 个已跟踪修改文件及 `tests/test_r283_style_library.py` 属并行 B 线程，未触碰；`.venv`、需求卡及任务资料原已未跟踪。完整状态保存在仓库外 `business-git-status.txt`。
- **Harness SSOT**：本线程未编辑任何 Harness SSOT；开工与收尾均存在其他工作产生的脏状态，收尾共 85 行，记录在仓库外 `harness-git-status.txt`。不把这些改动计入 S。
- 未创建 worktree，未改写提交，未暂存、提交或推送。未创建或实质更新声明的开发 SSOT 包，因此不产生 Obsidian SSOT 快照或提醒。
- S 样张完成；全项目发布、前端接入和人工验收不在本结论内。写完本报告后停止。
