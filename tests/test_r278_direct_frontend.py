"""R278 frontend scope and design contract checks; no user media access."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / 'studio/static'


def test_rescript_modules_and_csp():
    for name in ('direct-view.js', 'direct-storyboard.js', 'direct-style.js', 'direct-rescript.css'):
        text = (STATIC / name).read_text()
        assert not re.search(r'\bstyle\s*=', text), name
        assert not re.search(r'/Users/|/home/|undefined</|NaN</', text), name
    css = (STATIC / 'direct-rescript.css').read_text()
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(', css)
    assert 'line-through' not in css


def test_names_and_dependencies():
    view = (STATIC / 'direct-view.js').read_text()
    assert '口播稿' not in view
    assert 'direct-storyboard.js' in view
    assert 'direct-style.js' in view
    index = (STATIC / 'index.html').read_text()
    assert 'href="/direct-rescript.css"' in index


def test_table_and_generate_regions():
    view = (STATIC / 'direct-view.js').read_text()
    table = (STATIC / 'direct-storyboard.js').read_text()
    assert 'DV-SB-TABLE' in table
    assert 'dv-lines' not in view
    assert 'DV-GENBAR' in view
    assert 'motionSummary' in (STATIC / 'direct-style.js').read_text()
