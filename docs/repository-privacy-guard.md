# 仓库私人媒体与本机路径门禁

项目门禁，enforced / blocking，成本为快速静态检查。真实事故是未推送提交曾夹带 864 张私人帧图、拼图；GitHub 发布前必须拦截。所有截图、帧图、视频和音频存放在 `~/.photo-content-os/evidence/<任务>/`。文本引用用相对素材根路径；不扫描未跟踪文件，提交前先暂存明确的文件路径。

```bash
.venv/bin/python scripts/check_repository_safety.py --base origin/main
.venv/bin/python -m pytest -q tests/test_repository_privacy.py tests/test_repository_safety.py tests/test_edit_tools_runtime.py
```

默认 base 是 origin/main；没有该 ref 时使用 HEAD。显式冻结 base SHA 可在推送后复核同一范围。检查范围包含 Git 索引、工作区已跟踪文件和 base..HEAD 每笔提交的完整文件快照，包含中间版本，稀疏检出缺省文件从 Git 对象读取。检查前 fetch 远端；基线需为 HEAD 的祖先。无法解析 Git、清单或文本时退出 1，不当作无违规。`--runtime-paths-only` 只检查原有运行时源码规则，不代表隐私检查通过。

| 失败类别 | 范围与修复 |
| --- | --- |
| `repository-private-media` | 所有已跟踪媒体扩展名，大小写不敏感。包括 jpg/jpeg/png/heic/webp/gif/mp4/mov/m4a/mp3/wav/aac，并保留原门禁其他媒体扩展名。将媒体移到上述仓库外目录，执行 `git rm --cached -- <文件>` 后重跑。已进入未推送提交的媒体必须先备份并净化该范围历史；仅在后续提交删除仍会失败。已推送历史不由此门禁删除。 |
| `repository-local-path` | evidence/、acceptance/、docs/tasks/ 文本中的 `/Users/`、`/private/var/`、`/home/`。改成相对素材根的路径，执行 `git add -- <文件>` 后重跑。存量仅允许原文件、原违规行散列和原出现次数，追加相同行或改写违规行均不允许。 |
| `repository-path-baseline-stale` | 存量违规行减少或文件消失时，从 `scripts/repository-safety-path-baseline.json` 删掉对应条目或减少计数；将文本修复与清单缩减一起暂存后重跑。清单只许变短，不许新增、改写来源或恢复已移除条目。 |
| `repository-privacy-input` | 清单、Git 基线/对象或文本不可读。运行 `git fetch origin` 并确认 `git rev-parse --verify <base>^{commit}`；从 Git 恢复被报错的清单或修复文本编码，再运行检查。 |

唯一媒体白名单为 `scripts/repository-safety-media-allowlist.json`，仅认逐文件路径、非空理由及内容 SHA-256；不认目录、通配符或“机器证据”声明。现有四张图已逐张查看，均为无人像文字排版合成测试帧。替换文件内容会失去豁免。白名单不得用来准许私人媒体。

本机路径存量首次绑定门禁实施前的 source_commit。清单仅存违规行散列及计数，不复制敏感路径原文。相对检查基线、范围内每笔提交、暂存区及工作区逐步校验缩减；不修改已推送的历史证据。未来提交必须在推送前检查实际未推送范围；在 origin/main 已前进后检查空范围不能替代此前的范围验证。

负例与边界：`tests/test_repository_privacy.py` 在临时 Git 仓库生成假 PNG 与假路径 JSON，验证新增、重复违规行、暂存泄露被工作区掩盖、中间提交先加后删、清单膨胀、清单格式损坏与失效基线。绿例覆盖精确白名单、清单缩减与范围外文本。所有测试媒体均由测试生成，不写入正式证据。

不涉及界面或运行时产品行为，无需视觉或人工体验验收。现有人工验收不由本门禁代签。门禁接入现有本地 CI 与 GitHub CI 的安全检查，AGENTS Required checks 与项目适配器列出完整范围命令。退役条件：被覆盖同等范围并有负例证明的提交/发布安全检查替代；届时同时更新脚本、清单、测试与入口。
