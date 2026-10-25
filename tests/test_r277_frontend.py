"""R277's static edit boundary and fixture contract; browser assertions run in its gate."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_inline_styles_in_revision_frontend():
    for name in ('direct-shot-detail.js', 'direct-shot-detail.css', 'direct-revision-log.js'):
        text = (ROOT / 'studio/static' / name).read_text()
        assert not re.search(r'\bstyle\s*=', text), name
        assert not re.search(r'/Users/|/home/|undefined</|NaN</', text), name
    css = (ROOT / 'studio/static/direct-shot-detail.css').read_text()
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(', css)


def test_direct_view_hooks_the_revision_log():
    # The two-line boundary against R276 was reviewed at delivery; keep only the hooks durable.
    view = (ROOT / 'studio/static/direct-view.js').read_text()
    assert view.count('data-revision-log') == 2
    assert '<button class="btn rv-go-log" data-revision-log>画面问题记录</button>' in view
    assert "import('./direct-revision-log.js')" in view
    assert 'renderRevisionLog(root(),{api:ctx.api,onBack:' in view


def test_revision_fixtures_and_numeric_contract():
    subprocess.run(['node', 'tests/test_r277_frontend.mjs'], cwd=ROOT, check=True, capture_output=True)
    for path in (ROOT / 'tests/fixtures/r277-revise').glob('*.json'):
        payload = json.loads(path.read_text())
        for shot in payload['job']['shots']:
            for version in shot['versions']:
                assert 'baseVersion' in version
                assert version['baseVersion'] is None or version['baseVersion'] < version['version']


def test_single_detail_entry_and_log_entry():
    for name, entry in (('direct-shot-detail.js', 'renderShotDetail'), ('direct-revision-log.js', 'renderRevisionLog')):
        text = (ROOT / 'studio/static' / name).read_text()
        assert re.findall(r'export function (\w+)', text) == [entry]
