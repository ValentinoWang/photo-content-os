# Machine evidence

- Run ID: 20261125T090709Z-local-c934a94
- Status: PASS
- Source identity: c934a944d04f7ebff4373c299ff96b0d071fdc4c
- Layer: machine/unit

## Execution

Recorded at: 2026-11-25T09:07:32.753880+00:00

## Command 1

```
PY="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)/.venv/bin/python" && UI_COPY_QUALITY_CHECKER="$HOME/.agents/skills/ui-copy-quality/scripts/check_ui_copy_quality.py" "$PY" -m pytest -q tests/test_music_ai_generate.py tests/test_music_library.py tests/test_musicdl_engine.py tests/test_music_failure_message.py tests/test_r223_music_analysis.py
```

Exit code: 0

```
........................................................................ [ 53%]
...............................................................          [100%]
135 passed in 21.08s
```

## Command 2

```
PY="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)/.venv/bin/python" && PYTHON_BIN="$PY" bash scripts/check_runtime_contract.sh
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

## Command 3

```
PY="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)/.venv/bin/python" && UI_COPY_QUALITY_CHECKER="$HOME/.agents/skills/ui-copy-quality/scripts/check_ui_copy_quality.py" "$PY" scripts/validate_music_analysis_registry.py
```

Exit code: 0

```
music-analysis-registry OK: 126 ids; 121 copy entries
```
