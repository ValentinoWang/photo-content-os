# 直出动画时长与跨镜字幕检查

范围：Photo 原生直出 `video_render.compose`，不修改作者 HTML、口播或时间轴，不自动拉长镜头，不进行收费重试。字幕规划沿用实际口播句级时序和 30fps 切镜帧。

## F7 跨镜口播续接

根因：跨切镜 cue 只保留前半段时序，丢弃后半段，机器字幕格式检查无法识别有声无字幕的空档。

修复：以 cut 为独占结束帧和下一段的起始帧，按字数/帧比例选兼容现有换行规则的文字边界。通常逐字分区，保持原话拼接完全相等；文字太短不能合理拆分时，为每个独立区间重复原文，避免空档。旧 cue 的 endFrame 不包含 cut，禁止旧区间残留到下一镜。沿用至多两行、每行14字、均衡行长、不以关闭标点开行、不显示末尾句逗号等规则。

负例：R131 第二版真实切镜84/476帧。修复前分别丢60/51帧，修复后下一镜首帧立即接续。逐帧测试覆盖完整实测13句（57.28秒）；保留末帧独占规则造成的最多一帧尾部量化误差，任何口播期空档不得超过两帧。不把句内比例估计描述为词级实测。

## F8 动画时长前置检查

- 稳定失败码：`animation_duration_too_short`；声明或文件无法读取/解析时为 `animation_duration_invalid`。
- 触发：compose 在校验音轨后、调用 render_shots/浏览器前读取 HTML 中 JavaScript 的 `const D` 数值声明。
- 只解析正有限数值字面量（含科学计数），不执行作者脚本。声明表达式、非数值、多义声明均明确失败，不能混同为未声明。忽略 HTML 普通文本、非 JavaScript script、注释和字符串中的示例。常量列表中的 D 也检查。
- 实际镜头时长取 frames/fps；若严格小于 0.7·D 则阻止整片生成，等于边界时允许。使用有理数比较，不因浮点舍入误判边界。
- 结果：输出目录 `animation-duration-checks.json` 保留每镜 shotId、actualSeconds、declaredSeconds、minimumSeconds、status；失败 reason 含镜号、实际时长、0.7·D 和修复动作。`compose-status.json` 失败且 candidate 为空。
- 未声明 D：该镜 `status=not_declared`、reason“未声明 const D，跳过时长检查”；总结果为 partial，不能报全量通过，允许继续流程。
- 负例：本版04镜31/30=1.033333秒，D=2.2，门槛1.540000秒，必须在任何浏览器启动前阻止。
- 修复路径：作者按实测分配时长修订动画 D/内容，再从正常产品保存并重新交接。不自动修改作者稿、不掩盖失败、不跳过检查。

## 回归命令

`.venv/bin/python -m pytest -q tests/test_direct_video_f7_f8.py tests/test_direct_video_subtitles.py tests/test_video_subtitle_wrapping.py`

随后运行 `.venv/bin/python -m pytest -q tests` 与 `bash scripts/run_local_ci.sh`。测试 fixture 冻结自既有候选 descriptor，与作者正在修改的外部稿件独立；测试不引用其他仓库或用户机器的绝对素材路径。证据见 `evidence/2026-10-16/r131-f7-f8/`。

## 执行归属、开销与退役

所有者为 Photo 直出 compose；F8按本次用户要求处于 enforced / blocking，只阻止不符合动画时长合同的本轮生成，不拦截其他工程任务。静态读文与数值比较属于快速检查，无网络、模型、浏览器或视频编码开销；字幕回归纳入既有 tests 发现机制。无需另加跨项目静态扫描或人工截图门禁，本次不改产品UI。

若动画协议不再使用 const D，或有替代的可信动画时长元数据，须先修订该合同与相关负例，再替换或退役此检查；不得靠放宽比例、忽略失败码或将未声明改成通过来绕过。F7逐帧覆盖测试保留，除非字幕时钟合同整体替换并提供等价覆盖证明。
