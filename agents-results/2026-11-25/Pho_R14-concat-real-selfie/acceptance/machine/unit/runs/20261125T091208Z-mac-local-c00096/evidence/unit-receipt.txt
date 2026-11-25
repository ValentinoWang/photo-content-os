# Machine evidence

- Run ID: 20261125T091129Z-mac-unit
- Status: PASS
- Source identity: c00096f796ffeb9534674f48b324ab8e47cdfeec
- Layer: machine/unit

## Execution

Recorded at: 2026-11-25T09:11:34.479530+00:00

## Command 1

```
PY="$(git rev-parse --git-common-dir)/../.venv/bin/python" && "$PY" -m pytest -q tests/test_transcript_to_srt.py tests/test_concat_real_selfie.py tests/test_concat_backend.py tests/test_edit_backend_interface.py tests/test_word_timing_and_spoken_edit.py
```

Exit code: 0

```
.....................................................................                                              [100%]
69 passed, 30 subtests passed in 3.67s
```

## Command 2

```
PYTHON_BIN="$(git rev-parse --git-common-dir)/../.venv/bin/python" bash scripts/check_runtime_contract.sh
```

Exit code: 0

```
Repository safety check passed.
python=3.12.14
compileall=ok
packages=ok
encoding_contract=ok
Runtime contract check passed.
```
