# R223 B 代理视觉复核

权威：TASK 第 3 节、DESIGN 第 3–6 和 10.1 节、mock/beat-map.html、当前 registry。角色为已有 R220 local-creator，音乐增量，不引入新 Surface 权威。

已查看：review-1440-1..5.jpg、review-1180-1..5.jpg、review-430-1..5.jpg；实际桌面全页、430 关闭/展开页；review-fixture-rails.jpg、review-real-rails.jpg；最终 real-* 四张右栏及 r226-module.png。截图来自隔离 Studio 的真实渲染，浏览器实际视口 1440×960、1180×860、430×932；R220 额外检查 900 宽。最终视觉编辑后已重载桌面和手机并查看。

检查结果：列表与侧栏层次清楚；过滤空态没有残留侧栏；队列不展示未完成数据；已知、未知、不可读失败的说明和入口对应；AI 标注按分组排布，长文案与底部信息可读；手机没有多余速度列、横向溢出或底部裁切。多首歌共享模块换歌按钮在宿主内可见，切点、淡出和歌名行不溢出。

完整覆盖：全页截图保留底部；实际 rail.scrollHeight 与 clientHeight 的观测记录在截图清单，没有需要分帧拼接的内部滚动溢出。手机展开页从顶至底的导入时间均可见。尺寸、时间、输出尺寸、SHA-256 绑定在 reviewed-screenshot-manifest.json；63 对左右图分别绑定源图哈希，图库 151 引用已核验。8 张早期截图已 SUPERSEDED，不计最终 PASS。

差异 D0–D4 详见 REPORT-B，不能声称像素完全一致。主要来自共享外壳的真实状态、波形时间定位、taxonomy 同数排序、精确柱高及真实模型数据。无其他新增产品块或未批准文案。

交互路径：夏日/有人声筛选→选歌→色带跳转→真实播放、白拍；两部分即时重试和失败回滚、同时重试互不覆盖、轮询停止均由真实挂载页面执行并留有断言。

范围：本地音乐页和共用模块，不是全站或生产审计；本记录是 Codex 代理复核，不能替代 Claude 看图和用户真人验收。

设计矩阵门禁：design.matrix.incomplete 表示缺少已声明场景或宽度；零输入负例必须失败。修复路径为重新采集缺失页面、恢复相应 inventory/extras，再运行 check_r223_design.py，不扩大批准文案或编号。现有 check_design_contract.py 的 copy.unapproved-text / design.unapproved-element / design.missing-element 负例均成功拦截。

测试日志已脱敏本机路径；Git 内 full-tests.log 仅去除行尾空白，未改失败内容，原始输出另保存在仓库外。
