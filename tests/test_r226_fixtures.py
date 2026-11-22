"""The UI fixtures follow the real wire contracts, not a presentation-only DTO."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/r226-editing-techniques/api'
SCHEMA = json.loads((ROOT / 'schemas/roughcut-api.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)
PATHS = sorted(FIXTURES.glob('cut-*.json'))
STATES = json.loads((ROOT / 'docs/tasks/R226-editing-techniques/mock/design-contract.json').read_text())['states']
assert {path.stem for path in PATHS} == set(STATES), 'fixtures must cover every approved state'
TRACK_KEYS = {
    'schema_version', 'title', 'artist', 'album', 'platform', 'platform_id',
    'imported_at', 'file_sha256', 'duration_seconds', 'sample_rate_hz',
    'loudness_lufs', 'loudness_status', 'original_url', 'audio', 'peaks', 'beat', 'tags',
}


@pytest.mark.parametrize('path', PATHS, ids=lambda p: p.stem)
def test_ui_fixture_uses_wire_contract(path):
    fixture = json.loads(path.read_text())
    assert fixture['synthetic'] is True
    VALIDATOR.validate(fixture['roughcut'])
    music = fixture['music']
    assert set(music) == {'ok', 'tracks', 'registry_version', 'taxonomy'}
    assert set(music['taxonomy']) == {'sections', 'tag_categories', 'display'}
    assert music['taxonomy']['sections'] == [
        {'id': 'quiet', 'name': '安静'}, {'id': 'build', 'name': '推进'},
        {'id': 'peak', 'name': '高潮'},
    ]
    assert music['tracks']
    for track in music['tracks']:
        assert set(track) == TRACK_KEYS
        assert track['schema_version'] == 2
        assert isinstance(track['beat']['models'], list)
        assert set(track['beat']['package_versions']) == {'beat-this', 'librosa', 'torch', 'torchaudio'}
        assert track['beat']['bpm'] > 0
        assert track['duration_seconds'] > 0
