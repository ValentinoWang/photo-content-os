#!/bin/bash
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line || exit 1
for f in scripts/direct_video/recipe_samples/*/*.html; do bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/lint-one.sh "$f" || { echo "LINT FAIL $f"; exit 1; }; done
n=$(ls scripts/direct_video/recipe_samples/*/landscape.mp4 scripts/direct_video/recipe_samples/*/portrait.mp4 2>/dev/null | wc -l | tr -d ' ')
echo "mp4=$n"; test "$n" -eq 16
