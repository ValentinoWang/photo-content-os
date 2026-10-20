"""Check the complete R223 rendered-state matrix with the existing design gate."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
EVIDENCE = ROOT / 'evidence/2026-10-21/R223-music-beat-map/phase-b'
CHECKER = Path(os.environ['DESIGN_CONTRACT_CHECKER'])
STATES = ('music', 'music-beats-analyzing', 'music-beats-failed',
          'music-beats-failed-unknown', 'music-beats-failed-unreadable',
          'music-beats-queued', 'music-filter-empty', 'music-tags-failed')
SCENARIOS = STATES + ('music-playing', 'music-intro', 'music-end', 'music-filtered',
                      'real-queued-projection', 'real-normal-projection')
expected = {f'{state}-{width}{suffix}' for state in SCENARIOS
            for width in (1440, 1180, 430)
            for suffix in (('', '-open') if width == 430 and state != 'music-filter-empty' else ('',))}
expected.update(('optimistic-beat', 'optimistic-tags', 'optimistic-concurrent'))
items = json.loads((EVIDENCE / 'inventory-index.json').read_text())
if len(items) != len(expected) or {item['key'] for item in items} != expected:
    sys.exit('design.matrix.incomplete: expected 47 mock, 8 copied-library and 3 optimistic inventories')
summary = []
for item in items:
    key = item['key']
    command = [sys.executable, str(CHECKER), 'check', '--contract',
               'docs/tasks/R223-music-beat-map/mock/design-contract.json',
               '--inventory', str(EVIDENCE / (key + '-inventory.json')),
               '--approved-extras', str(EVIDENCE / (key + '-extras.json')), '--json']
    result = subprocess.run(command, capture_output=True, text=True)
    summary.append(dict(key=key, exit_code=result.returncode, **json.loads(result.stdout)))
(EVIDENCE / 'design-checks.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
failures = [item for item in summary if item['exit_code']]
print('Inventories:', len(summary), 'failing:', len(failures))
print(json.dumps(failures[:4], ensure_ascii=False, indent=2))
sys.exit(bool(failures))
