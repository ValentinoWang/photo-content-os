"""Disposable synthetic smoke: default paths, isolated HOME, actual MP4 decode."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from edit_backends.registry import get_backend

out = Path(__file__).resolve().parent
suffix = os.environ.get('R207_SMOKE_SUFFIX', '')
summary = out / ('smoke' + suffix + '.json')
inputs = out / 'inputs'
inputs.mkdir(exist_ok=True)
source = inputs / 'source.mp4'
if not source.exists():
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=320x180:r=30:d=4',
                    '-f', 'lavfi', '-i', 'sine=frequency=660:duration=4', '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(source)], check=True)
suggestions = inputs / 'suggestions.json'
suggestions.write_text(json.dumps({'suggestions': [{'type': 'silence', 'start': 1, 'end': 2, 'auto_cut_allowed': True}]}))
for key in ['CONTENT_OS_OPENCHATCUT_ROOT', 'CONTENT_OS_OPENCHATCUT_NODE', 'CONTENT_OS_OPENCHATCUT_BROWSER',
            'CONTENT_OS_OPENCHATCUT_REFINE_BROWSER', 'CONTENT_OS_OPENFILM_PACKAGE', 'CONTENT_OS_OPENFILM_NODE',
            'CONTENT_OS_CHROMIUM_SLOT', 'CONTENT_OS_CHROMIUM_SLOT_SCRIPT', 'PLAYWRIGHT_BROWSERS_PATH']:
    os.environ.pop(key, None)
results = json.loads(summary.read_text()) if summary.exists() else {}
with tempfile.TemporaryDirectory(prefix='r207-empty-home-') as home:
    os.environ['HOME'] = home
    os.environ['CONTENT_OS_OPENFILM_HEADLESS'] = '1'
    for name in os.environ.get('R207_SMOKE_BACKENDS', 'openfilm,openchatcut').split(','):
        backend = get_backend(name)
        item = results[name] = {'probe': backend.probe(), 'temporary_home': True, 'environment_overrides': False}
        try:
            assert item['probe']['runnable'], item['probe']
            result = backend.render(source=source, suggestions_path=suggestions, output_dir=out / (name + '-smoke' + suffix), timeout_seconds=240)
            item['render'] = result
            assert result['status'] == 'candidate', result
            output = Path(result['output'])
            subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'], check=True, timeout=30)
            item['decoded'] = True
            item['artifact'] = {'path': str(output), 'bytes': output.stat().st_size,
                                'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
        finally:
            item['cleanup'] = backend.close()
            summary.write_text(json.dumps(results, indent=2, ensure_ascii=False) + '\n')
        assert not item['cleanup']['remaining_pids'], item['cleanup']
print(json.dumps(results, indent=2, ensure_ascii=False))
