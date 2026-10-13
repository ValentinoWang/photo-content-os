# PS7 交接 33 验证

Photo 源提交：f01c990 / 3290946 / a9d88d7 / 864e1a0；MC11 合同 0805f7fac。

- receipt-tests-green.log：2 passed / 4 subtests；部分失败中已完成镜的第一帧生成真实 JPEG，检查尺寸、大小、脱敏与重试范围。
- direct-tests-green.log：30 passed / 11 subtests；真实绑定投影、现有预览读取、身份/越界/缺文件拒绝，以及实际 JS 渲染器的直出展示。
- range-tests.log：32 passed / 22 subtests；真实 HTTP 200/206/416，闭区间、开放区间、后缀、无效范围与超长输入。测试服务器 shutdown 并 join；OpenAPI 先改源再生成。
- pytest.log：根目录全量 561 passed / 32 skipped / 187 subtests，131.08 秒。原生浏览器条件测试按现有条件 skip，不宣称本段重新原生渲染。最后仅 CSS 缺视频空列修正，受影响两图随后重拍并看。
- tsc-results.json / tsc-after-range.json / tsc-final.json：两套 TypeScript 各次均退出 0，最后一次在 MC11 提交后执行。
- p5-failed-projected.json：真实 P5 失败回执离线读回第 14 行 / figure.svg，MC11 逐镜 schema 零错误。P5 帧已由其线程清理，本段不重渲；原已完成 01 海报链由 P5 / MC11 证据承接，本段失败海报生成由合成第一帧回归验证。
- visual-progress.json：6 张最终整页已逐张看到底部，实际 1440×1000 / 430×1000；2 张真实 P5 页面，4 张缺预览/检查失败展示夹具。现有低清 MP4 能加载、播放及 seek 到第 5 秒。没有生成新成片、ASR、TTS、上传或采用。
- Media 的 agents-results/2026-10-13/ps7-studio/：截图驱动及原始失败、最终日志。最初 seek 到 0 秒，补 Range 后保持第 5 秒断言通过，没有减弱断言。最终 PNG 位于 Media fe-shots/ps7-*.png；画廊、manifest 链接/哈希/覆盖/reviewRef 均核对。
- copy-source/ 与 copy-review.md：两文件词法 PASS、0 warning；新名称按交接 33，没有宣称完整旧文案/元素 guard 通过。
- cleanup.json / pytest-run.json：所有自开浏览器与两次串行 Studio 退出；8765 无监听，共享 Claude 的 22496/23999 不变。专属 pytest 目录和新测试 pyc 已删；本次测试写入 OCC 的 PID 差异保留后恢复原字节。

没有下载、安装或大逐帧生成；df 约 6.1–7.2 GiB，使用已有依赖、P5 成片/预览和小测试夹具。普通报告与证据不是 SSOT 包；Harness 未改，OCM-Z1 人验仍 PENDING，未推送。最终报告见 Media PS3-REPORT 第五段。
