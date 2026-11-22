#!/bin/bash
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line || exit 1
for id in blur-slide marker-underline-title; do for o in portrait landscape; do
  f=scripts/direct_video/recipe_samples/$id/$o.html; test -f $f || { echo "MISSING $f"; exit 1; }
  bash /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line/docs/tasks/Pho_R05-shotcraft-line/lint-one.sh $f >/dev/null || { echo "LINT FAIL $f"; exit 1; }
  test -s scripts/direct_video/recipe_samples/$id/$o.mp4 || { echo "NO MP4 $id/$o"; exit 1; }
done; done; echo "ok blur-slide marker-underline-title"
