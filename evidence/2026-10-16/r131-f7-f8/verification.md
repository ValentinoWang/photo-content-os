# R131 F7–F8 机器验证

Request: 2026-10-15-R131-hiatus-habit-direct-video
Verify: 2026-10-15-R131-hiatus-habit-direct-video/H-02

## 变更和红绿

只改Photo直出compose与字幕规划，不重渲染、不改作者稿、不请求模型或配音、不操作Media候选采用。

F7：真实cut84/476帧先红后绿；红日志包括111个缺字幕帧（60+51）与两处首帧缺失。按帧比例拆原cue文字，在cut处结束旧区间并从cut启动新区间，不丢后半段；保持原文拼接不变、F3独占结束帧和F4–F6换行规则。无法划分的极短文字可按明确允许的整句重复策略建立新区间。全片逐帧回放有声区间检查无内部空档，原末帧量化规则允许最多一帧尾差，另断言实际有声帧空档不超过两帧。

F8：compose在调用render_shots与使用缓存之前生成animation-duration-checks.json。04镜31/30=1.033333秒 < 0.7×2.2=1.540000，抛animation_duration_too_short；报告镜号、实际与最低时长，candidate为空，不启动浏览器。等于门槛通过；未声明记not_declared、总体partial；无法读取/非法/多义声明记animation_duration_invalid，不能冒充未声明。只静态解析字面量，不执行作者JS。

冻结fixture来自candidate_8439d5780216b189646084579179a0b4的原始descriptor，测试不依赖其他仓库或机器素材路径。只读重放15镜时长检查仅04镜失败，其余14镜通过，见real-15-shot-duration-checks.json；real-fixture-green.json中两个切镜均立即续接、原话不变、缺字幕帧为0。

## 命令与结果

- 初始红测试：116个失败项/子断言、2 passed、1607 subtests passed；见red.log。没有修改原有测试来降低要求。
- 定向新旧回归：19 passed、1786 subtests passed，7.28秒；见green-focused.log。
- `.venv/bin/python -m pytest -q tests`：572 passed、32 skipped、1973 subtests passed，107.09秒；见pytest-full.log。跳过不算通过。
- `bash scripts/run_local_ci.sh`，显式使用已安装Playwright模块及其Chromium：Ran557 tests / OK(skipped=9)，173.649秒；其后outline/doc-sync、review registry、安全、公开入口和synthetic trial均通过，末行Local CI passed，见local-ci.log。8个BrowserRenderTests实际运行；只用临时合成素材，不渲染本篇作品。
- runtime-contract.log与doc-sync.log通过，git diff --check通过。

## CI运行时差异

首次CI使用系统Google Chrome：既有test_timeout_is_bounded_and_other_shots_continue耗时27.917秒超过20秒；同配置独跑38.549秒同样失败。该测试只调用未修改的multi_shot.render_shots，未经过F7/F8；原文件与断言均未改。

测试合同已支持VIDEO_RENDER_TEST_BROWSER。选择已安装Playwright Chromium后，同一20秒断言独跑8.863秒通过，随后完整CI通过。保留系统Chrome两份失败日志和该独跑绿日志，不把系统Chrome运行时差异说成已修复的代码缺陷，亦未放宽时间阈值、增加跳过、安装依赖或更改全局配置。

成功CI的局部环境：

`VIDEO_RENDER_TEST_BROWSER=/Users/vsiyo/Library/Caches/ms-playwright/chromium-1228/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`

`VIDEO_RENDER_PLAYWRIGHT_MODULE=/Users/vsiyo/Desktop/创业项目/自媒体创作Agent/apps/media/web/node_modules/playwright/index.js`

## 界限

既有OCM-Z1待人工验收涉及八个Surface，本次无UI改动，与其范围不相交，未替用户签署或改状态。旧候选、预览、字幕、音轨SHA均未变，正常Media写入0次、配音0次；8787/9081保持2318/2638，8765无服务。见existing-candidate-unchanged.json。

新检查将在下一次Photo原生compose子进程加载，不需要Media重启。保持旧候选不采用，等待作者按实测时长修订镜头代码后的新指令。
