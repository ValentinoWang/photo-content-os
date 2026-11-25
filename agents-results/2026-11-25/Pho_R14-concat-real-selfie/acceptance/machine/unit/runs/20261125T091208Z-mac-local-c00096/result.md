# Acceptance Run: 20261125T091208Z-mac-local-c00096

- Run ID: 20261125T091208Z-mac-local-c00096
- Task ID: 2026-11-25-Pho_R14-concat-real-selfie
- Lane: machine/unit
- Status: PASS
- Acceptance contract: agents-results/2026-11-25/Pho_R14-concat-real-selfie/acceptance-contract.md
- Contract version: 1
- Contract SHA-256: 472005d5c6ea99b7c33a943cf8c7b4335ae88fba7fdd6bf63a197c1309a91477
- Source identity: c00096f796ffeb9534674f48b324ab8e47cdfeec
- Runtime identity: mac-local
- Executor or reviewer: Antigravity
- Started at: 2026-11-25T09:12:08Z
- Completed at: 2026-11-25T09:12:08Z
- Evidence directory: evidence/

## Scope

验证 AC-01（`scripts/transcript_to_srt.py` 词级/段级转 SRT 与异常拒绝）和 AC-02（`scripts/edit_backends/concat_adapter.py` 旋转竖屏显示宽高、既有剪辑后端与口播删减测试、运行契约检查）。本运行基于提交 `c00096f796ffeb9534674f48b324ab8e47cdfeec` 在本机 `.venv` 执行，不包含任务委托人人工验收项 H-01。

## Procedure

```bash
PY="$(git rev-parse --git-common-dir)/../.venv/bin/python" && "$PY" -m pytest -q tests/test_transcript_to_srt.py tests/test_concat_real_selfie.py tests/test_concat_backend.py tests/test_edit_backend_interface.py tests/test_word_timing_and_spoken_edit.py
PYTHON_BIN="$(git rev-parse --git-common-dir)/../.venv/bin/python" bash scripts/check_runtime_contract.sh
```

两条命令退出码均为 0（69 passed, 30 subtests passed；Runtime contract check passed）。

## Requirement disposition

| Requirement | Result | Evidence | Notes |
| --- | --- | --- | --- |
| AC-01 | PASS | evidence/unit-receipt.txt | `tests/test_transcript_to_srt.py` 覆盖词级切条、中文去空格、英文留空格、无词回退、非法输入与拒绝覆盖输入 |
| AC-02 | PASS | evidence/unit-receipt.txt | `tests/test_concat_real_selfie.py` 5 组旋转/非旋转画幅回归 + `test_concat_backend.py` + `test_edit_backend_interface.py` + `test_word_timing_and_spoken_edit.py` + `check_runtime_contract.sh` 全过 |

## Findings

None

## Evidence manifest

| Artifact | SHA-256 | Meaning |
| --- | --- | --- |
| evidence/unit-receipt.txt | dbc9d10c89d7adf5119ec2a054a904bbe8b12f3fcf364904a2bf9363f5ca3a9a | 提交 `c00096f` 的 pytest（69 passed, 30 subtests passed）与 `check_runtime_contract.sh` 原始执行回执 |

## Unverified items

H-01（任务委托人亲眼核对 `~/.photo-content-os/evidence/concat-real-run/clip1-campus/concat-run/candidate.mp4` 成片与 Concat 工程打开改存）留待人工验收；3 分钟以上真人口播视频待用户拍摄后补充实测。

## Conclusion

提交 `c00096f796ffeb9534674f48b324ab8e47cdfeec` 在 `machine/unit` 泳道下 AC-01、AC-02 全部 PASS（69 passed, 30 subtests passed，运行契约检查通过），可进入人工验收交接。
