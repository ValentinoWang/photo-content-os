# 音乐分析清单校验

- 失败类：`music-analysis-registry`；项目级阻塞静态检查，成本快速、无网络。
- 输入：`music-analysis.registry.json`、对应 JSON Schema、`origin/main` 上的已发布版本，以及 Core 文案检查器。
- 命令：设置 `UI_COPY_QUALITY_CHECKER` 指向 Core 的 `ui-copy-quality/scripts/check_ui_copy_quality.py`，运行 `.venv/bin/python scripts/validate_music_analysis_registry.py`。
- 拦截：重复编号、启用标签无中文名、未知类别或模型、越界阈值、模型缺哈希/许可、删除或复用已发布编号、版本不加一、改写或遗漏改动记录、界面文案不合格。
- 读不到文件、解析失败、零类别、读不到 Git 基底或文案检查器均失败。首版由成功读取的 Git 树确认清单尚未发布。
- 修复：按报错字段改清单或规范；已发布编号只下线，修改版本并追加记录，修正文案；不可更换基底或扩大豁免。
- 红绿证明：`tests/test_r223_music_analysis.py` 的 registry 用例。合法首版、改名和下线为绿；上述结构与治理错误为红。
- 范围：只约束本清单及其展示中文，不检查历史讨论、模型原始类别名称或软件许可证全文。
- 退役：清单被正式替代且调用方移除后，连同 schema、检查命令和适配项一起删除。
