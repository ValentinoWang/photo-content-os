#!/bin/bash
cd /Users/vsiyo/.local/share/task-worktrees/production-desk-shotcraft-line && python3 scripts/direct_video/recipe_library.py --check --upstream /Users/vsiyo/Desktop/创业项目/内容创作/video-shotcraft/references/shots && .venv/bin/python -m pytest -q tests/test_pho_r05_recipe_library.py
