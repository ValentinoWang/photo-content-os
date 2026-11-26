# Acceptance Run: 20261126T071842Z-local-18fd1e

- Run ID: 20261126T071842Z-local-18fd1e
- Task ID: 2026-11-26-Pho_R18-concat-return
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R18-concat-return/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: f60b606d4a07b18c75a9ad8e275b12a4d0e9992119bb80123d990b6e00e21716
- Source identity: d4a31f871a76779b2207a7af1547d268f679a5b0
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T07:18:42.729672Z
- Completed at: 2026-11-26T07:18:58+00:00
- Evidence directory: evidence/

## Scope

AC-01，开发机判定为本机（任务单要求本机替身测试）。核对 Concat 回传读回：成功生成候选、工程身份不符、读回被拒、窗口占用文件存在。全部使用替身 Concat，不启动真实窗口，不调付费接口。

## Procedure

```sh
/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q tests/test_concat_return.py tests/test_ps4_returned_candidate.py tests/test_ps3_video_workflow.py tests/test_concat_backend.py
/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q tests/test_ps3_video_workflow.py
```

两条命令退出码均为 0。新测试对改前代码（studio/returned_candidate.py、studio/video_workflow.py 暂存还原）4 项全部失败，退出码 1。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-d1.txt, evidence/pytest-d2.txt, evidence/pytest-red-on-old-code.txt | 32 passed in 46.42s；16 passed in 3.97s；改前代码 4 failed in 14.35s。 |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-d1.txt | 0381e049e7895841f52baf8bde89d2e91be192bdb3517883d7e9ccaec41a5cff | D1 四个测试文件的输出 |
| evidence/pytest-d2.txt | 81a726f6ef509cda1b7d9942c400d6c66c9d1f3c315f78a87e21bc66b6fc1896 | D2 视频工作流测试输出 |
| evidence/pytest-red-on-old-code.txt | a0ca2425d8d358bb64853b8aa0c0d89b89cab4904a1004653562d4f624473913 | 新测试对改前代码失败的输出 |

## Unverified items

人工 H-01、H-02 待任务委托人核对。字幕位置不从 Concat 时间线读取；没有启动真实 Concat 窗口，没有实跑付费服务。

## Conclusion

Concat 回传读回的四种情形在替身 Concat 下行为符合合同，其他剪辑软件的既有回传测试保持通过。
