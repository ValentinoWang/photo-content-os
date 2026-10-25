"""Frontend boundary and regressions, without loading user media."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'studio/static'


def test_no_inline_styles_or_private_runtime_strings():
    for name in ('direct-view.js', 'direct.css', 'direct-shot-detail.js', 'direct-shot-detail.css'):
        text = (STATIC / name).read_text()
        assert not re.search(r'\bstyle\s*=', text), name
        for forbidden in ('/Users/', '/home/', 'undefined</', 'NaN</'):
            assert forbidden not in text


def test_failure_codes_are_translated_before_rendering():
    text = (STATIC / 'direct-view.js').read_text()
    assert 'FAILURE_COPY[code]' in text
    assert 'esc(s.failureCode)' not in text
    assert 'esc(job.failureCode)' not in text
    assert 'failureMessage(job.failureCode)' in text
    assert '读不到这件作品的直出任务' in text
    assert 'if(readError)' in text


def test_router_and_styles():
    view = (STATIC / 'review-view.js').read_text()
    assert "['vlog','script','direct'].includes(tab)" in view
    assert "['direct','脚本直出']" in view
    assert 'direct.stop()' in view
    assert 'direct.render(p,tabs)' in view
    index = (STATIC / 'index.html').read_text()
    for name in ('direct.css', 'direct-shot-detail.css'):
        assert f'href="/{name}"' in index


def test_detail_module_boundary_and_reduced_motion():
    text = (STATIC / 'direct-shot-detail.js').read_text()
    assert re.findall(r'export function (\w+)', text) == ['renderShotDetail']
    assert 'setSelectionRange' in text
    assert 'state.key===key' in text
    assert 'if(!details.open||loading)return' in text
    css = (STATIC / 'direct.css').read_text()
    assert '@media(prefers-reduced-motion:reduce)' in css
    assert 'repeat(7,minmax(0,1fr))' in css
    assert 'repeat(4,minmax(0,1fr))' in css
    assert 'repeat(3,minmax(0,1fr))' in css


def test_numeric_contract():
    subprocess.run(['node', 'tests/test_r276_direct_frontend.mjs'], cwd=ROOT, check=True, capture_output=True)


def test_f2_fixtures_match_nullable_write_clock_and_output_kinds():
    import json
    names = ('empty', 'read-error', 'filled', 'unavailable', 'designing', 'writing', 'failed-shot', 'ready', 'rewriting', 'composing', 'composing-silent', 'done', 'done-silent')
    for name in names:
        payload = json.loads((ROOT / 'tests/fixtures/r276-direct' / f'{name}.json').read_text())
        if payload.get('job'):
            assert all('writingStartedAt' in shot for shot in payload['job']['shots'])
        if name.endswith('-silent'):
            assert payload['job']['output']['kind'] == 'silent'
            assert payload['job']['narration']['status'] == 'none'
    assert 'layout_bottom_gap' in (ROOT / 'tests/fixtures/r276-direct/ready.json').read_text()
