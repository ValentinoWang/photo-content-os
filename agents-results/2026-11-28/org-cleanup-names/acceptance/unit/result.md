# Machine evidence

- Run ID: org-cleanup-names
- Status: PASS
- Source identity: bd13e35f3fb75d932038a83d6b3c3901e4825dd9
- Layer: machine/unit

## Execution

Recorded at: 2026-11-28T16:06:34.157096+00:00

## Command 1

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m compileall -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/studio /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts
```

Exit code: 0

```

```

## Command 2

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env PYTHONPATH=/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup:/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_media_common_io.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p0_llm_and_evidence.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p2_photo_remaining.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p5_local_prompts.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p5b_storyboard_contracts.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_migrate_content_os_v2.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_material_match_report_contract.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_bridge_contracts.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_desktop_openapi_route_sync.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_full_checklist_acceptance.py
```

Exit code: 0

```
............................................................ [100%]
60 passed, 12 subtests passed in 3.41s
```
