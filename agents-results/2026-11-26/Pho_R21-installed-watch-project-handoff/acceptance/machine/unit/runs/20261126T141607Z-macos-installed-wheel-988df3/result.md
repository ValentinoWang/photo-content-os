# Acceptance Run: 20261126T141607Z-macos-installed-wheel-988df3

- Run ID: 20261126T141607Z-macos-installed-wheel-988df3
- Task ID: 2026-11-26-Pho_R21-installed-watch-project-handoff
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-26/Pho_R21-installed-watch-project-handoff/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: df9364c12d8479c5c37579a0fa3395afa3297760808cf4c9a087633c34eb386a
- Source identity: 15c2b90ef2dee7bb7dd85d01b1f67aa1b7ab0dad
- Runtime identity: macos-isolated-venv
- Executor or reviewer: codex
- Started at: 2026-11-26T14:13:51.018497+00:00
- Completed at: 2026-11-26T14:14:30.332216+00:00
- Evidence directory: evidence/

## Scope

在 macOS 上用从固定 U13 提交构建的 wheel 运行点名测试。测试将 wheel 安装到隔离环境，读取既有第三方依赖。数据为临时合成项目，Media、Studio 确认和渲染均使用替身。

## Procedure

```sh
P1A_AGENT_WHEEL=/tmp/p1a-u13-codex.EXeOto/openclaw_media-0.2.0-py3-none-any.whl P1A_AGENT_WHEEL_SHA256=0d941234d52733fdc13ec089f6d968b43221eed96afe73eb1734ca6331357117 P1A_AGENT_SOURCE_SHA=ef90bf8b31aed390d11602a5bac300ac4e6f6ecf P1A_EVIDENCE_PATH=/tmp/p1a-u13-codex.EXeOto/wheel-evidence.json "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u13-p/.venv/bin/python" -m pytest -v -p no:cacheprovider --basetemp "/tmp/p1a-u13-codex.EXeOto/pytest" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u13-p/tests/test_p1a_installed_watch.py" "/Users/vsiyo/.local/share/task-worktrees/production-desk-p1a-u13-p/tests/test_r282_handoff.py"
```

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest.txt | 100 passed in 38.94s，退出码 0。安装态核心案例及 OpenAPI 一致性用例均执行。 |

## Findings

安装位置位于测试创建的独立环境，42 个 Python 文件逐个与 wheel 对照通过。OpenAPI 快照按现有生成器重导出后检查通过。确认、重启恢复和错配拒绝均有实测。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/pytest.txt | 0eba85ee4355e65414389d6070d6ab66b7795e9ea4e79f04e7bc8b1650682660 | 点名测试原始行，移除行末空格 |
| evidence/wheel-provenance.json | 4aa720f19b87991c9a45d137f8264b0cd66d5a25fdf8155ba3093247276e8e92 | 固定源提交、wheel 摘要、导入位置和依赖版本 |
| evidence/check-exits.txt | d21921f10ba87c04b8cb189d5aab403cbfd157e06f4fb4539037f93a3f109dd3 | 导出和测试真实退出码 |
| evidence/file-overlap.txt | a3c8ab030c77f6a0e6a030fe349f9c0da870d0ea2657b03af1a102e40db5240e | 已通过旧卡的冻结范围与受保护测试比较 |

## Unverified items

正式选择界面、真实素材和生产运行未验证。H-01 尚待人工查看。

## Conclusion

AC-01 通过。
