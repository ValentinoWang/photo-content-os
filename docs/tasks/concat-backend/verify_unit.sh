#!/usr/bin/env bash
# 在开发机上跑 concat 后端和接口测试（rbox 后面的路径是开发机上工作区里的相对路径）。
set -euo pipefail
W=/Users/vsiyo/.local/share/task-worktrees/production-desk-concat-backend
cd "$W"
exec "$W/.agents/skills/photo-remote-dev-box/scripts/rbox" run "$W" -- .venv/bin/python -m pytest -q tests/test_concat_backend.py tests/test_edit_backend_interface.py
