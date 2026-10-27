# Acceptance Run: 20261027T105409Z-photo-dev-target-709114

- Run ID: 20261027T105409Z-photo-dev-target-709114
- Task ID: 2026-10-27-R312-photo-ffmpeg9-subtitles
- Lane: machine/integration-contract
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R312-photo-ffmpeg9-subtitles/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: b97b39c75a9cb522846fe1fad7e2e2c7e96385409c01ccb7a2a51a71715144b7
- Source identity: 5d62356222028aa31083fc693845875b1acf5edd
- Runtime identity: photo-dev-fixed-venv-ffmpeg9
- Executor or reviewer: Codex
- Started at: 2026-10-27T10:54:09.108973Z
- Completed at: 2026-10-27T11:01:17.989655+00:00
- Evidence directory: evidence/

## Scope

AC-01：在photo-dev heavy队列、固定.venv执行TASK指定五组定向：38 passed、2 subtests passed、0 failed、0 skipped，27.12秒。JUnit为40项（含两个子测试），不能说成40个独立pytest用例。

## Procedure

经 .agents/skills/photo-remote-dev-box/scripts/rbox bg <唯一任务名> <任务 worktree> -- bash -c <remote_script> 执行；完整脚本、pytest参数、时间和原始退出码见evidence/command.json。JUnit只追加结果导出与读取，不改测试选择、断言或失败码。源码为5d62356222028aa31083fc693845875b1acf5edd，远端回读五份保护测试摘要与本机一致。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/pytest-target.log; evidence/test-summary.json | 字幕/双语、预览黑帧、场景切换帧和令牌定向全部通过 |

## Findings

真实ffmpeg版本n9.0.2、melt7.4.0；STHeiti路径实际链接到NotoSansCJK-Bold。场景抽帧的新增回归实际执行。Pillow getdata有一条弃用警告，未隐藏。该运行不是旧2c4ff30或其他任务证据的复用。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/command.json | 873aa7432cb0b34f3e70d0ffe00dd6cc77c38af549e803970acdc7945a7fc989 | 实际执行记录 |
| evidence/launch.log | 98f6880582b9c0456e7415047982e0a0185463345d6872bbb19ec5f0c5bbfe2f | 实际执行记录 |
| evidence/pytest-target.log | 939247f3e891c4879a7dab85fe1b941f11bf44afd2caf9e85383bb8635ac41ff | 实际执行记录 |
| evidence/test-summary.json | 40a0ecf2382984666d72e36b104259c036799d5e43bd393bb528205b67721214 | 实际执行记录 |

## Unverified items

本机未跑pytest或浏览器。未操作真实作品、Studio数据或媒体根，无视频或原尺寸帧拉回本机。合成渲染断言不等于真人作品的字幕口播对齐；原H-01仍未签。字体Noto/Liberation、melt版本、缺Obsidian库的差异保留；不能由本run宣称全量全绿或两机等价渲染。

## Conclusion

PASS：仅当前冻结源码的任务单定向范围；全量另有独立run，人工判断独立保留。
