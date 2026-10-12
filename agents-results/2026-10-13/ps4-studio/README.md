# PS4 本地证据（交接 28）

这是普通验证证据，不是 SSOT 或人验批准。运行材料均为本线程隔离合成资料；没有修改用户原片。

- pytest-terminal.log：552 passed、32 skipped、165 subtests passed。
- local-ci-terminal.log：Local CI passed。
- native-terminal.log：pinned openfilm 0.1.5 的真实 HTTP / 磁盘编辑和导出 / 收回两项通过；含重叠撤回、撤销栈、分割、CAS 冲突和源片保护。
- tests/test_ps4_kdenlive_readback.py / test_ps4_returned_candidate.py：保存 XML 中恢复 3 帧、真实 melt 导出、MP4 与工程 108/120 帧不一致、字幕位置 0.5 的负例。
- receipts 与 mc8-contract-readback.json：实际本地生产者的 native_readback / manual_export；替换为合法合成 wire 身份后验证 MC8 65b22da5 提交版 schema。未验证 Agent 认证、上传与云端采用。
- visual-progress.json：66 张最终完整运行图逐张查看及 SHA-256；输出在 Media fe-shots/ps4-*.png，画廊 ps4-comparison.html；52 张未变定稿对照复用 PS3 已审图。
- design-contract-result.json：严格文案/元素 guard 仍有 918 文案诊断（含动态字段、关闭 details 与交接 28 新文案尚未进旧表；未逐条归零）、34 缺 ID、16 额外 ID 诊断，不能报绿。34 缺 ID 为 26 个根节点 collector 不收集与 8 个按交接 28 移除左栏依据的 ID；新增右栏这一版/回退提醒也未同步旧表。未扩大允许列表或改合同。
- copy-source：源码词法检查 3 文件、0 warning；不等于文案语义或人验通过。
- occ-native-placement.json：OpenChatCut 字幕使用其 containerStyle 输出，未运行完整 OpenChatCut 环境；本机 tsx 依赖不可用。OCM-Z1 人验仍 PENDING。

当前 native 剪点 kind 合同只有 silence/retake；不能核验原因的任意新增剪点阻止成功回执，不能伪称静音。已向协调人提出增加 manual 的裁定问题；未代改 Media 合同。

复现：先在本线程自己的 Tools 目录安装 pinned openfilm 0.1.5 / playwright-core，设置 CONTENT_OS_OPENFILM_PACKAGE、CONTENT_OS_CHROMIUM_SLOT_SCRIPT。执行 pytest 与本地 CI 时 TMPDIR / basetemp 指向本线程目录。所有浏览器通过 withChromiumSlot.sh 默认参数；截图 Chromium cache 版本缺失时使用现有 Chrome channel，不另下载浏览器。用完清理该目录并关闭进程。
