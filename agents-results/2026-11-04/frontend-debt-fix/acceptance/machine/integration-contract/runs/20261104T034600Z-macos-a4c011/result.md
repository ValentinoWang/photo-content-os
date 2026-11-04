# Acceptance Run: 20261104T034600Z-macos-a4c011

- Run ID: 20261104T034600Z-macos-a4c011
- Task ID: 2026-11-04-Pho_R01-frontend-debt-fix
- Lane: machine/integration-contract
- Status: FAIL
- Acceptance contract: agents-results/2026-11-04/frontend-debt-fix/acceptance-contract-v1.md
- Contract version: 1
- Contract SHA-256: 7fea37247520a99580b784d0ba51d2fc9461b2dfc0b39a882c46fb4ba0db0968
- Source identity: dd8096ed8fc3ccbb838b9a890e8112d653dcc64e
- Runtime identity: local-macos-chrome-python
- Executor or reviewer: Codex
- Started at: 2026-11-04T03:58:01.057883Z
- Completed at: 2026-11-04T03:59:25Z
- Evidence directory: evidence/

## Scope

AC-01 和 AC-02：任务单指定定向测试、Node 纯函数检查和 macOS 本机 Studio 的合成素材回收站操作。此 run 时间为证据整理时间；定向 pytest 实际为 03:45:49–03:45:54 UTC，H-02 浏览器实测为 03:46:07–03:46:21 UTC。

## Procedure

开发机 SSH 连接被拒。按本机预算串行运行任务单列出的 pytest 定向，结果 49 passed、2 subtests passed；执行五条 Node 命令结果均为 0，工具输出见 node-results.txt。Chrome 本地隔离 Studio 选择两份合成素材，检查取消、真实确认、回执和按哈希恢复；桌面及手机截图已检查，路径和摘要见任务根 TASK-4-visual-verification.md。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | FAIL | evidence/targeted.log; evidence/node-results.txt; ../../../../shots/H-01-1.png | 定向检查及 Node 测试通过，但截图与样式核查发现超限输入框红边被覆盖 |
| AC-02 | PASS | evidence/targeted.log; evidence/h02.log; evidence/node-results.txt | 真 macOS 系统废纸篓及部分失败处理通过；截图的失败响应为模拟 |

## Findings

先前 JXA 测试在文件已移走后 rc=-11、无回执，见任务根 TASK-2-STOP.md；本轮 ctypes 真实系统调用通过。H-01 桌面截图中，超限提示已显示但边框是青色；分镜表的 `.dv-form .dv-sb textarea` 和 `:focus` 规则优先级高于共享 `textarea.is-over`，分别覆盖红边为透明或青色。H-01 手机截图显示分镜表左侧而非台词列；该表存在水平滚动，尚未在手机视口补拍输入框及提示。手机相邻「取消全选」按钮文字竖向折行，未扩大样式改动。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/targeted.log | 1bfb064ed46ff8793a412dc79210b2269b0c86179edc066d940b0c1569f97e00 | pytest 原始输出 |
| evidence/h02.log | 4b58bb4f691efbd943fc91f9373f6905011e1d4dd4c5d762ec60fe595ccbb20e | 浏览器真实及模拟流程输出 |
| evidence/node-results.txt | 531c26e92569dea75624389d9d3e1efa79033ddd3c17d31845de30e9e444299a | 五条 Node 命令输出的工具记录转录 |

## Unverified items

人工验收、生产部署和真实素材未验证；H-01 手机输入状态未核验。模拟失败响应不能代替真实失败调用。Linux 无定时 macOS 真实测试层，欠着交总控。

## Conclusion

FAIL：AC-01 的输入框红边未通过视觉核查；AC-02 上述机器范围通过，不代表人工验收通过。已撤回机器绿灯生成的 handoff，保留原件供审计。
