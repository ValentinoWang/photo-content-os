# Machine evidence

- Run ID: photo-wheel-time-unit
- Status: PASS
- Source identity: c87d7124573a12c07a6184fd772c0c02d1f1a723
- Layer: machine/unit

## Execution

Recorded at: 2026-11-28T14:20:50.934111+00:00

## Command 1

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_music_ai_generate.py'
```

Exit code: 0

```
...................                                                      [100%]
19 passed in 17.58s
```

## Command 2

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env 'PYTHONPATH=/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/scripts' '/Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python' -m pytest -q '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_studio_review.py::test_utc_timestamp_uses_same_format_in_music_and_review' '/Users/vsiyo/.local/share/task-worktrees/production-desk-photo-wheel-consolidate/tests/test_studio_review.py::test_merge_cas_confirmation_and_invalidation'
```

Exit code: 0

```
..                                                                       [100%]
2 passed in 0.28s
```
