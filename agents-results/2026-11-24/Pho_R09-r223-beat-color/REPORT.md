# R223 当前拍点颜色复验

A｜`git show e26ec2f -- studio/static` 显示，R280 提交 `e26ec2f19d5e1136577873beb932f537a2a0037f` 将根令牌 `--ink` 从 `#E4EBEB` 改为 `#152021`。前后 `.bm-lane .bc.hit` 均为 `background:var(--ink)`。R280 的用户认可设计稿和需求卡 `2026-10-26-R280-photo-studio-light` 支持此令牌变化。R223 H-02 历史清单写的是“变白”，总控本轮裁定复验高亮与同轨颜色区别，保留旧清单和签署记录。

A｜检查读取真实 Studio 页面根令牌，经浏览器解析颜色，再与当前拍点背景比较。另要求同轨存在普通拍点，且当前色与每个普通拍点背景都不同。产品文件无差异。

## 两版对照原始输出

同一 `photo-dev`、合成音频生成方式、浏览器、Node 和新版断言。脚本接收 `e26ec2f^` 和对照时的 `origin/main` SHA，并分别启动隔离 Studio。两版均返回 0。

```text
v24.13.0
Google Chrome for Testing 149.0.7827.55
Studio source: a28a991210b72f0be38aca786ec32c3e93208c3e
PASS 7 music interaction checks
Studio source: 308eb2e86d264118514261a45db987632dc3cb4e
PASS 7 music interaction checks
[rbox] 退出码 0，完整日志 /root/.prbox/run-025009-5768.log
```

## 任务单验证原始末尾

`/bin/bash <任务工作区>/docs/tasks/r223-beat-color/verify_unit.sh`，退出码 0。首次验证在交互检查通过后因节拍图模块缺失隔离 Studio URL 退出 1，将模块移到同一个 Studio 生命周期内后复跑。

```text
v24.13.0
Google Chrome for Testing 149.0.7827.55
Studio source: 6039932a362cd1fd503aa5c860ebb84692a1e4fd
PASS 7 music interaction checks
PASS beat map: signature lifecycle, cuts, fade, offsets, multi-song swap, lane:false, seek, stable overview, formulas, visible swap, no overflow
Inventories: 58 failing: 0
[]
[rbox] 退出码 0，完整日志 /root/.prbox/run-025057-25312.log
```

## 验收登记

- `request_cards.py --project-root <任务工作区> new --input <本轮需求输入.json>` 退出 0，返回 `2026-11-24-Pho_R09-r223-beat-color`，相近参考为空。
- `manage_acceptance_artifacts.py rebaseline <R223 卡目录> --project-root <任务工作区> --base 308eb2e86d264118514261a45db987632dc3cb4e --head 6039932a362cd1fd503aa5c860ebb84692a1e4fd --trigger-card 2026-11-24-Pho_R09-r223-beat-color --reason '<R280 令牌依据>'` 退出 2，返回“已通过的卡不可修改，请开新卡并声明复验”。
- 新卡的声明使用 `reverify` 指向 R223/H-02。新测试摘要绑定在 Pho_R09 合同内，新卡人工作业为抽查。

## 验收图

在 photo-dev 运行真实 Studio 音乐库 `#view=music`，使用 R223 接口夹具和合成音频，将播放定位在 4.18 秒。桌面实际视口 1440×960，整页图 1440×1070。手机实际视口 390×960，详情面板展开，面板的可见高度与总高度均为 711。两张图已打开查看至页面和详情底部，当前拍点为深色，同轨其他拍点为浅色，两端均无横向溢出。

- 桌面图 SHA-256 `7e460daf8fd7911e908d86bdd25e468740654e17390f3dc550dda6e1e9cff5c7`
- 手机图 SHA-256 `5a88c1fb1cffa35da7421698fb0797c484d764fbfee62f40c432cb7139e33a03`
- 截图及采集清单位于仓库外 `~/.photo-content-os/evidence/r223-beat-color-pho-r09/`。

总控批准单张合成截图入库。正式登记图为 `acceptance/shots/H-01-1.jpg`，540×401，30,283 字节。SHA-256 为 `8b891f1e05611e7d887596a1558e41f6dfce779a51481255bb4eaff56dc89ebc`。原图留在仓库外。

`manage_acceptance_artifacts.py shots add` 将批准的照片和哈希附到 H-01，退出 0。随后以当前冻结源码和两版对照的机器 PASS 执行 `manage_acceptance_artifacts.py handoff`，指定 `--request-id 2026-11-24-Pho_R09-r223-beat-color --non-blocking --baseline <baseline.json> --claims <claims.json>`，退出 0，写入本卡的 `handoff.json`。H-01 为待验收抽查。R223/H-02 的既有签署和合同保持原字节。

## 同范围旧卡复核

发布门禁 G7 召回四项旧人工结果。已在本次冻结源码核对 Studio、既有剪辑和音乐测试路径无差异，并复跑剪辑工具、音乐分析和分段，共 `109 passed in 7.19s`，退出 0。范围证据进入 `20261124T075340Z-photo-dev-scope-603993`；四项声明 `unaffected`，R223/H-02 保留 `reverify`。

独立仓库安全检查退出 1。去重后有 243 条既有媒体和 18 条既有本机路径诊断；和本轮提交的变更路径交集为空。获准的截图通过单文件路径和哈希检查。
