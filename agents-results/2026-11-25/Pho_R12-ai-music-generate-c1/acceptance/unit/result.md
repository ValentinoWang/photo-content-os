# Machine evidence

- Run ID: 20261125T090634Z-local-204afee
- Status: PASS
- Source identity: 204afeea7f36a7135dc278169a41351ded300c7f
- Layer: machine/unit

## Execution

Recorded at: 2026-11-25T09:06:53.346551+00:00

## Command 1

```
PY="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)/.venv/bin/python" && UI_COPY_QUALITY_CHECKER="$HOME/.agents/skills/ui-copy-quality/scripts/check_ui_copy_quality.py" "$PY" -m pytest -q tests/test_music_ai_generate.py tests/test_music_library.py tests/test_musicdl_engine.py tests/test_music_failure_message.py tests/test_r223_music_analysis.py
```

Exit code: 0

```
........................................................................ [ 54%]
...........................................................              [100%]
131 passed in 16.64s
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
