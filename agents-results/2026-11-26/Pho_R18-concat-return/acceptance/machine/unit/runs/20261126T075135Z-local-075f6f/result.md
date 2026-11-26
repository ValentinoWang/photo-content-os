# Acceptance Run: 20261126T075135Z-local-075f6f

- Run ID: 20261126T075135Z-local-075f6f
- Task ID: 2026-11-26-Pho_R18-concat-return
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R18-concat-return/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: f60b606d4a07b18c75a9ad8e275b12a4d0e9992119bb80123d990b6e00e21716
- Source identity: 4189a26e832aa89af453d2a3e36c263813e0f53f
- Runtime identity: macos-production-desk-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T07:51:35.857561Z
- Completed at: 2026-11-26T07:51:48Z
- Evidence directory: evidence/

## Scope

AC-01 中 D3 的部分：候选下载路径 downloadPath 跟随契约快照 api_base 前缀（scripts/video_candidate.py）。本机运行，替身测试，不调付费接口。D1 的 Concat 读回、回传、后端相关测试在 HEAD 上同批重跑，较早一次运行 20261126T071842Z-local-18fd1e（32 passed、16 passed）留作参考。

## Procedure

```sh
/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q tests/test_candidate_download_path.py
/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q tests/test_concat_return.py tests/test_ps4_returned_candidate.py tests/test_ps3_video_workflow.py tests/test_concat_backend.py tests/test_candidate_download_path.py
```

两条命令退出码均为 0。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-d3.txt, evidence/pytest-d1-d3.txt | 2 passed in 2.64s；五个文件合跑 34 passed in 26.20s。 |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest-d3.txt | ce9ff91a0cfeb6afb348c639c95cac6dfb2bdc68a28706735720fc065c0512d5 | D3 下载路径测试输出 |
| evidence/pytest-d1-d3.txt | b2a1c93f20f8f397169c0e6cbf4f53efcabc30cb8170b6c54d6027d83ea44fb2 | Concat 回传、候选、视频工作流、Concat 后端与 D3 五个文件合跑输出 |

## Unverified items

人工 H-02 待任务委托人核对；没有启动真实 Concat 窗口，没有实跑付费服务；全量测试未跑（基线已有 7 个失败，见总控核对）。

## Conclusion

D3 下载路径在快照 api_base 为 /media/api 时以该前缀开头，替身测试通过。
