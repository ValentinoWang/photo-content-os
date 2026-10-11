#!/usr/bin/env bash
set -euo pipefail
99_System_OpenClaw/.venv-content-os/bin/python -m unittest discover -s 99_System_OpenClaw/tests -p 'test_media_trash_flow.py'
