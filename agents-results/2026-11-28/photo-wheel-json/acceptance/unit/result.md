# Machine evidence

- Run ID: photo-wheel-json-unit
- Status: PASS
- Source identity: fb1082b1be5da443a7893d585c6cf58252947d5a
- Layer: machine/unit

## Execution

Recorded at: 2026-11-28T14:19:17.643016+00:00

## Command 1

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_queue_identity.py'
```

Exit code: 0

```
.....                                                                 [100%]
5 passed, 3 subtests passed in 0.10s
```

## Command 2

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_enqueue_openclaw_queue_job.py'
```

Exit code: 0

```
........                                                                 [100%]
8 passed in 0.31s
```

## Command 3

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_openclaw_queue.py'
```

Exit code: 0

```
...............                                                          [100%]
15 passed in 0.26s
```

## Command 4

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_edit_handoff_pack.py'
```

Exit code: 0

```
......                                                                   [100%]
6 passed in 2.12s
```
