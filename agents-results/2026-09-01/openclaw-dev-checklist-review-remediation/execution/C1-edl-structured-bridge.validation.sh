#!/usr/bin/env bash
set -euo pipefail
export LOCAL_MEDIA_ROOT="/Users/vsiyo/Desktop/照片筛选"
99_System_OpenClaw/.venv-content-os/bin/python -m unittest discover -s 99_System_OpenClaw/tests -p 'test_ssot_edl_bridge.py'
