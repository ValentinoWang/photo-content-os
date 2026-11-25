# Machine evidence

- Run ID: 20261125T091452Z-local-unit-05b105
- Status: PASS
- Source identity: 05b10524014c2106915393db14293b3f5a5bad18
- Layer: machine/unit

## Execution

Recorded at: 2026-11-25T09:14:59.661500+00:00

## Command 1

```
PATH="/Users/vsiyo/.local/share/dreamverse-trial/tools/node-v22.22.2-darwin-arm64/bin:$PATH" /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q tests/test_dreamverse_bridge.py tests/test_seedance_provider.py tests/test_dreamverse_shot_controls.py
```

Exit code: 0

```
...............                                                          [100%]
15 passed in 5.11s
```

## Command 2

```
PYTHON_BIN=/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python bash scripts/check_runtime_contract.sh
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
