# Machine evidence

- Run ID: org-cleanup-constants
- Status: PASS
- Source identity: 9d0a02fa836ff5644a25195aba9e17c5335c1a8d
- Layer: machine/unit

## Execution

Recorded at: 2026-11-28T16:15:43.550022+00:00

## Command 1

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m compileall -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/studio /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts
```

Exit code: 0

```

```

## Command 2

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env PYTHONPATH=/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup:/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_archive_location_config.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_chatcut_mcp.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_model_provider_config.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_onboarding_state.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_desktop_openapi_route_sync.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_full_checklist_acceptance.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_dreamverse_bridge.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_avatar_http_oss.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_edit_handoff_pack.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_music_library.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_pho_r05_recipe_library.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_media_common_io.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p0_edl_contract.py
```

Exit code: 0

```
.................................... [ 22%]
......................ssssssss................................ [ 60%]
.................................................................        [100%]
155 passed, 8 skipped, 46 subtests passed in 9.86s
```
