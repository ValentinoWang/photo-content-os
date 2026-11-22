#!/bin/bash
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line || exit 1
.venv/bin/python -m pytest -q tests/test_pho_r05_aesthetic_lint.py tests/test_r283_style_library.py || exit 1
for f in scripts/direct_video/style_library/*.html; do bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/lint-one.sh "$f" >/dev/null || { echo "LINT FAIL $f"; exit 1; }; done
echo lint-ok
