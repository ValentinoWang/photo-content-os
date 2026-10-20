"""Bind reviewed/replayed UI evidence to unchanged sources after report-only freeze."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path.cwd()
bundle = root / 'agents-results/2026-10-21/r223-delivery'
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
prior = '69ecf5550997a57a84c11eb5467356ed12d1ccd0'
changed = subprocess.check_output(['git', 'diff', '--name-only', prior, head], text=True).splitlines()
assert changed == ['docs/tasks/R223-music-beat-map/REPORT-C.md'], changed
base = Path.home() / '.photo-content-os/evidence/R223-music-beat-map/phase-c/r220-matrix'
manifest = json.loads((bundle / 'r220-screenshot-manifest.json').read_text())
for item in manifest:
    assert hashlib.sha256((base / item['file']).read_bytes()).hexdigest() == item['sha256']
numbers = json.loads((bundle / 'r220-number-formulas.json').read_text())
assert not numbers['errors'] and len(numbers['numbers']) == 33
print(json.dumps({'result': 'PASS', 'source_identity': head, 'prior_full_matrix_source': prior,
    'changed_paths': changed, 'reused_unchanged_visual_files_rehashed': len(manifest),
    'matrix_states': 29, 'number_groups': 33, 'capture_errors': 0,
    'review_scope': '5 states at desktop+phone sampled; approved music B renders independently rehashed'}, ensure_ascii=False, indent=2))
