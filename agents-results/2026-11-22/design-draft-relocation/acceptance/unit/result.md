# Machine evidence

- Run ID: 20261122-draft-relocation
- Status: PASS
- Source identity: e082818799c59ca5b96487bb05e289beb43b55b6
- Layer: machine/unit

## Execution

Recorded at: 2026-11-22T08:23:15.395505+00:00

## Command 1

```
'/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/.venv/bin/python3' -B -m unittest tests.test_checklist_remediation_static
```

Exit code: 0

```
....
----------------------------------------------------------------------
Ran 4 tests in 0.003s

OK
```

## Command 2

```
'/Users/vsiyo/Desktop/Opensource_Tool/Harness_Engineering/.venv/bin/python3' -B scripts/check_repository_safety.py --base origin/main
```

Exit code: 0

```
Repository safety check passed.
```
