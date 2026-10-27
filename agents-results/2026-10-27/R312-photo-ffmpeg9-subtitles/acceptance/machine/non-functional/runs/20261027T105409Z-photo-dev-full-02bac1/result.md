# Acceptance Run: 20261027T105409Z-photo-dev-full-02bac1

- Run ID: 20261027T105409Z-photo-dev-full-02bac1
- Task ID: 2026-10-27-R312-photo-ffmpeg9-subtitles
- Lane: machine/non-functional
- Status: PASS
- Acceptance contract: agents-results/2026-10-27/R312-photo-ffmpeg9-subtitles/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: b97b39c75a9cb522846fe1fad7e2e2c7e96385409c01ccb7a2a51a71715144b7
- Source identity: 5d62356222028aa31083fc693845875b1acf5edd
- Runtime identity: photo-dev-fixed-venv-ffmpeg9-noto-melt7.4
- Executor or reviewer: Codex
- Started at: 2026-10-27T10:54:09.439977Z
- Completed at: 2026-10-27T11:07:00.543526+00:00
- Evidence directory: evidence/

## Scope

AC-02：TASK.md明确允许的限定回归条件。实际pytest：3 failed、1214 passed、36 skipped、1 warning、2005 subtests passed，287.91秒；原始退出码1，绝非全量全绿。三项失败精确等于预先冻结清单，零额外失败、零收集错误，36项跳过ID和原因逐项记录。共有1253个pytest用例，JUnit tests=3258包含2005个子测试，不能冒充3258个独立用例。

## Procedure

经项目技能rbox在photo-dev的heavy队列单次执行固定.venv：.venv/bin/python -m pytest -q -p no:cacheprovider -rfE tests；另加JUnit导出用于核对每项结果。完整参数、源码身份、环境信息、起止时间和原始退出码保存在evidence/command.json及pytest-full.log。本地只回收文本，不拉视频或原尺寸帧。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-02 | PASS | evidence/acceptance-assessment.json | 仅表示任务授权的无额外回归条件满足，不表示pytest全绿 |
| tests/test_obsidian_doc_sync.py::ObsidianDocSyncTest::test_document_contract_commands_run_with_system_python_without_media_dependencies | FAIL（允许的环境差异） | evidence/test-summary.json | 原始失败，不改成pytest通过 |
| tests/test_pf_video_pipeline.py::FrameMappingTests::test_every_frame_matches_retained_source_clock | FAIL（允许的环境差异） | evidence/test-summary.json | 原始失败，不改成pytest通过 |
| tests/test_pipeline_backends.py::MeltPipelineTests::test_overlay_and_subtitle_pixels_are_rendered | FAIL（允许的环境差异） | evidence/test-summary.json | 原始失败，不改成pytest通过 |

## Findings

失败1为系统python文档同步缺少开发机Obsidian目标；失败2为melt7.4的帧时钟结果与本机7.39不同；失败3为melt7.4叠层/字幕像素断言。完整消息与实际断言保留，不改环境、不改测试、不扩大清单。ffmpeg实测n9.0.2，STHeiti路径链接至Noto；1条Pillow弃用警告保留。36个跳过由当前源码条件产生，详列ID与原原因，未新增skip或修改断言。

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/acceptance-assessment.json | 2660337598cc428daaa0f44a5b089b9d4d3cd348a2e62e9989c46126946034e6 | 实际执行或精确边界核对 |
| evidence/command.json | 43281dbcef3621fd59878cddf02098d3462b6a999b6ddfc4ccce68837e44a7ec | 实际执行或精确边界核对 |
| evidence/launch.log | 2796f9311cc2c91e5c6f05a613bdf36439a46acfa35fa04b52e8cc61ffe39b57 | 实际执行或精确边界核对 |
| evidence/pytest-full.log | 226df5eb63248f7d9ef2577bd1bf10f6454619bee022e9a69e625a3cbac000df | 实际执行或精确边界核对 |
| evidence/test-summary.json | 6bbb2916371a6e048151106f173758582fcaa074602fd8d5d04b263c0a9681c1 | 实际执行或精确边界核对 |

## Unverified items

三项环境失败仍未修复；跳过项没有被本run执行，不能宣称这些行为已通过。开发机Noto/Liberation字体、melt版本、缺Obsidian库与本机不同；特定cp替身属于既有开发机环境，本轮不把它称作原生macOS等价运行。没有真实作品与人工字幕/口播验收，H-01仍PENDING。本run的PASS严格限于AC-02预先定义的允许环境差异回归条件。

## Conclusion

PASS：任务单允许的无额外回归边界满足；pytest原始结果仍为3失败、退出1，非全量全绿、非环境差异修复、非人工PASS。
