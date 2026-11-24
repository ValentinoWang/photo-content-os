# U1 OpenMotion 单镜验收记录

配方库共 175 张。video-shotcraft 原有 124 张，OpenMotion 收录 51 张。十类数量与 199 条排除记录见 [导入清单](excluded.md)。两套来源各自保留原许可证和来源说明，OpenMotion 卡片与演示由导入清单逐条核对。

- A｜开发机断网打开 51 个演示，每页正向和反向定位 7 帧。同帧画面一致，每页至少出现两种不同画面，未发现页面异常或网络请求。
- A｜制作台 `multi_shot.py` 在开发机加载固定字体后渲染「颗粒聚成字形」，输出 8/8 帧，退出码 0。
- A｜本机 Chrome 逐张看过下表 3 张演示。每张拍了 1000×600 桌面宽度和 390×844 手机宽度，整页画布无滚动，截图输出尺寸与视口相同。手机按原始横幅缩放，检查范围为能否打开、画面是否裁切以及有无横向溢出。
- A｜任务单专项 `verify_unit.sh` 尾行为 `17 passed in 0.54s`，真实退出码 0。运行时用 rbox 的 `RBOX_LOCAL_ROOT` 传入当前任务工作区，开发机解释器链接指向项目已有运行环境。
- A｜`recipe_library.py --check --upstream <video-shotcraft>/references/shots` 退出码 0。原 124 张卡与对应上游文件的 SHA-256 核对通过，新 51 张卡的致谢、许可证和演示清单核对通过。重建前后的 124 条旧索引内容相同。

| 演示 | 文件路由（相对配方库） | 本机截图（相对媒体证据目录） | 抽看结果 |
| --- | --- | --- | --- |
| 栅格玻璃折射 | `demos/openmotion/om-1f1a40cc-f473-46f7-badb-953b2fb140c2-clip-1/index.html` | `om-recipes/glass-grid-desktop.png`、`om-recipes/glass-grid-phone.png` | 第 44 帧，固定格线和错位轮廓均清楚可见。 |
| 按钮扩成面板 | `demos/openmotion/om-be0354b4-c4d9-4c81-bb67-ac16dc065184-clip-2/index.html` | `om-recipes/button-to-panel-desktop.png`、`om-recipes/button-to-panel-phone.png` | 第 82 帧，面板边界完整，正文处于淡入阶段。 |
| 椭圆阵列波动 | `demos/openmotion/om-cbe77bbc-94d8-4035-9507-103deaa025bc-clip-1/index.html` | `om-recipes/ellipse-wave-desktop.png`、`om-recipes/ellipse-wave-phone.png` | 第 55 帧，椭圆阵列和中心文字完整。 |

截图均为 30 FPS 帧定位后采集。采集时间、视口、全画布覆盖及 SHA-256 写在截图目录的 `preview.json`。

替总控定的取舍：沿用上游 Canvas 动作和每镜时间区间，换用中性示例、用系统字体提供离线预览、用制作台指定字体渲染视频，并把原秒数定位接到制作台逐帧入口。原样张和视频保存在库外，新卡暂不标记为竖屏适用。按同一视觉动作与现有配方去重，对素材替换或单镜一致性无法验证的候选记录原因。
