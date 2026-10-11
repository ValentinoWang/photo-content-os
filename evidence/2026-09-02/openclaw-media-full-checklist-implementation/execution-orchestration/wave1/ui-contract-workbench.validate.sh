set -euo pipefail
cd /Users/vsiyo/Desktop/照片筛选
test -s 99_System_OpenClaw/visual-workbench.html
test -s 99_System_OpenClaw/visual-workbench.json
99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/visual-collaboration-contract/scripts/validate_visual_collaboration.py workbench 99_System_OpenClaw/visual-workbench.json
test -d 99_System_OpenClaw/contracts/ui
