# Photo Content OS Studio、OpenClaw Media 合同与隐私边界

## 1. 产品对象

系统以 `CreativeProject` 为中心，而不是以某个素材文件夹为中心。一个项目串联：

```text
研究与参考 → Brief → Script → 本地素材 → Storyboard / EDL → Delivery → 发布与复盘
```

Studio 允许按区块修改和锁定文档，AI 只能修改本次明确选中的未锁定区块。每次修改产生不可覆盖的版本；回滚会生成新版本，并将依赖当前内容的下游产物标记为失效，避免旧交付物继续冒充最新结果。

## 2. 本地与云端职责

| 层 | 权威内容 | 禁止事项 |
| --- | --- | --- |
| Photo Content OS 本地设备 | 原始媒体、关键帧、音频、转写缓存、预览、编辑器工程、本地绝对路径 | 不把原始媒体和绝对路径投影到普通 Web 页面 |
| OpenClaw Media 控制面 | pipeline、device、job、业务状态、允许同步的 artifact、archive receipt | 不假装能直接浏览或编辑设备上的本地媒体 |
| 模型 Provider | 用户策略允许发送的派生证据 | 不把“控制面不保存原媒体”误写成“任何证据都不会发送给模型” |

## 3. P0 机器合同

AI 生成器、预览渲染器和剪辑交接后端共享 `edit_decision_list_v1`：

- `slot` 是唯一正整数；
- `time_range` 使用 `0.000-4.000` 字符串；
- 时间精确到毫秒；
- 每个可执行片段必须有真实来源和 `source_start_sec`；
- 缺失镜头进入 `missing_materials`，不能伪造候选文件；
- 时间线片段不能重叠。

视觉分析必须把实际图片附件交给模型。提示词里出现一个本地路径，不构成模型已经看到图片的证据。

## 4. P1 上游兼容

冻结审阅基线：

```text
ValentinoWang/openclaw-media
f0460b4ce84ca7efc7eb6d2f05c77d20eef68aaf
openclaw_media_product_v1
sha256:931dba97f9d9ed3fa1a03da4e15783f5d449ead7a56ff0919f3e0087efbf6967
```

薄桥只做：

1. 校验上游 package/catelog 版本和摘要；
2. 将用户语言映射到冻结白名单 pipeline；
3. 校验工作区引用为安全相对 POSIX 路径；
4. 调用上游 `openclaw-media` CLI。

配对、心跳、lease、ack、start、result、archive 和 readback 都由上游唯一实现。

当前上游设备合同正式声明 `macos`。Windows/Linux 本地能力可运行，但云端配对保持 fail-closed，直到上游合同增加对应平台并重新冻结快照。

## 5. P3 分层分析与转写

- `metadata` 不调用语义模型；
- `preview` 对大量素材做受限初筛；
- `deep` 只用于项目相关候选；
- 缓存键包含素材哈希、模型、Prompt、策略和层级，防止重复付费；
- 音频未转写时明确记录 `pending`，不能被摘要层描述成“AI 已听懂”；
- 预览粗剪默认只生成执行计划，只有显式 `--execute` 才调用本地 FFmpeg。

## 6. 安全要求

- Studio 只监听回环地址；
- 所有写请求要求 CSRF；
- 浏览器 Origin 必须是本地工作台；
- 服务端输出使用 CSP 与 `nosniff`；
- 路径必须先解析并验证仍位于项目根目录；
- Web 投影只返回稳定 ID、相对引用和描述符；
- 原始媒体、凭据和绝对路径一律 fail closed。
