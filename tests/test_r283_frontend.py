from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_library_shared_components_and_csp():
    style = (ROOT / 'studio/static/direct-style.js').read_text()
    assert 'DV-STYLE-LIB' in style
    assert 'bindClips' in style
    assert not re.search(r'\bstyle\s*=\s*["\']', style)
    assert not re.search(r'/Users/|/home/', style)
    css = (ROOT / 'studio/static/direct-rescript.css').read_text()
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b|rgba?\(', css)


def test_library_fixtures_and_retired_empty_state():
    import json
    folder = ROOT / 'tests/fixtures/r278-direct'
    assert len(list(folder.glob('*.json'))) == 19
    for path in [*folder.glob('*.json'), *(ROOT / 'tests/fixtures/r283-direct').glob('*.json')]:
        data = json.loads(path.read_text())
        assert len(data['styles']['library']) == 9, path.name
    assert not (folder / 'first-none-r278.json').exists()
