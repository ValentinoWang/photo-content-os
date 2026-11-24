# Acceptance Run: 20261124T133023Z-photo-dev-befb0c

- Run ID: 20261124T133023Z-photo-dev-befb0c
- Task ID: 2026-11-24-Pho_R11-seedance-provider
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-24/Pho_R11-seedance-provider/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 45e5f7a5719f2191c8566d6fa3e10398ea56deb443ceaf155e7bf72aa229234a
- Source identity: 73de32703362f761e90bd67294264d7fe70e846f
- Runtime identity: photo-dev / rbox / pytest / 回环 HTTP 替身
- Executor or reviewer: Codex
- Started at: 2026-11-24T13:29:21Z
- Completed at: 2026-11-24T13:29:37Z
- Evidence directory: evidence/

## Scope

在 photo-dev 执行 U1、U2 专项。原万相 6 项随同运行。所有生成 API 均使用替身。

## Procedure

执行 bash /Users/vsiyo/.local/share/task-worktrees/production-desk-seedance-provider/docs/tasks/seedance-provider/verify_unit.sh。
工作区源码 HEAD 与 Source identity 相同。命令退出码 0。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/verify-unit-output.txt | 受管块重跑字节一致；回环 HTTP 创建、查询、失败、超时 |
| AC-02 | PASS | evidence/verify-unit-output.txt | 换提供方确认；Seedance 路由；旧账本按万相恢复 |

## Findings

12 项通过，其中 6 项为原样的万相测试。

按冻结源码范围复算，改动仅涉及 DreamVerse 插件、桥接、新增专项测试和本需求登记。
旧万相测试 Git blob 相同。通用测试与验收物分类命中的旧剪辑工具和音乐库，其运行代码、专项测试和人工记录未改。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/verify-unit-output.txt | 71c153635c18b0bf6e2aefcd359904bf7a378c5f1f351073baad41ab4fdabb16 | 命令输出末尾与远端日志位置 |
| evidence/scope-receipt.txt | 06c39e6ec509e8fd58ba75281893a1f571789da4072477725f8d8b938ab0ef74 | 冻结范围、旧测试 Git blob、引用及人工记录差异 |

## Unverified items

真实方舟账号、实际视频下载和成片效果留待 H-01。

## Conclusion

开发机替身专项通过。人工验收待完成。
