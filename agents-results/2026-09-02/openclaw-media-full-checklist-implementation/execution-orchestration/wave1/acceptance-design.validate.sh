set -euo pipefail
cd /Users/vsiyo/Desktop/照片筛选
99_System_OpenClaw/.venv-content-os/bin/python agents-results/2026-09-02/openclaw-media-full-checklist-implementation/build_ssot.py
99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/report-to-ssot-development-paths/scripts/validate_ssot_bundle.py agents-results/2026-09-02/openclaw-media-full-checklist-implementation --skip-archive
for contract in agents-results/2026-09-02/openclaw-media-full-checklist-implementation/acceptance-fragments/OCM-*/acceptance-contract.md; do
  99_System_OpenClaw/.venv-content-os/bin/python .agents/skills/design-acceptance-contract/scripts/check_acceptance_contract.py "$contract" --project-root /Users/vsiyo/Desktop/照片筛选
done
99_System_OpenClaw/.venv-content-os/bin/python -m py_compile 99_System_OpenClaw/tests/test_full_checklist_acceptance.py
