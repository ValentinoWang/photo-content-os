"""Media-first provenance contract, frozen legacy output and real consumers."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from edl_contract import EDLContractError, normalise_edl, write_edl
from edit_backends import handoff_pack
from edit_backends.editors.kdenlive_adapter import Backend
from studio.edl_bridge import EDLBridgeError, read_edl_bridge

SCHEMA = json.loads((ROOT / 'schemas/edit-decision-list.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def media_first(*, audio=False):
    raw = json.loads((ROOT / 'tests/fixtures/r227-audio-legacy/v1.expected.json').read_text())
    raw.pop('generation_model')
    raw.pop('generation_reasoning')
    raw.update(source_script_used=False, project_id='r227-e', project_revision=1,
               provenance=dict(kind='media_first_planner', planner='roughcut_planner', planner_version='1.0',
                               preset_id='trip', preset_name='轻快旅行', input_digest='aB' * 32))
    raw['clips'][0].update(source_file='scene.mkv', candidate_files=['scene.mkv'], source_start_sec=0)
    if audio:
        raw['clips'][0]['audio_mute'] = True
        raw['schema_version'] = 'edit_decision_list_v2'
    return raw


@pytest.mark.parametrize('audio', [False, True])
def test_media_first_preserves_truth_and_is_read_only(tmp_path, audio):
    raw = media_first(audio=audio)
    original = copy.deepcopy(raw)
    result = normalise_edl(raw)
    assert raw == original
    assert result['source_script_used'] is False
    assert result['provenance'] == raw['provenance']
    assert 'generation_model' not in result and 'generation_reasoning' not in result
    assert normalise_edl(result) == result
    VALIDATOR.validate(result)
    source = tmp_path / '06_edit_decision_list.json'
    write_edl(source, result)
    before = source.read_bytes()
    bridge = read_edl_bridge(tmp_path)
    assert bridge['content'] == result
    assert bridge['source']['content_digest'] == 'sha256:' + hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before


BAD_PROVENANCE = [None, {}, [], 'media_first_planner',
                  *[dict(media_first()['provenance'], kind=v) for v in ('ai', '', True)],
                  *[dict(media_first()['provenance'], input_digest=v)
                    for v in ('', 'a'*63, 'a'*65, 'g'*64, 'a'*63+'\n', 'sha256:'+'a'*64, 1, None)],
                  *[dict(media_first()['provenance'], **{key: value})
                    for key in ('planner', 'planner_version', 'preset_id', 'preset_name')
                    for value in ('', '  ', 1, None)],
                  dict(media_first()['provenance'], invented=True)]
BAD_PROVENANCE += [{k: v for k, v in media_first()['provenance'].items() if k != field}
                   for field in ('kind', 'planner', 'planner_version', 'preset_id', 'input_digest')]


@pytest.mark.parametrize('bad', BAD_PROVENANCE)
def test_invalid_provenance_rejected_by_contract_schema_and_bridge(tmp_path, bad):
    raw = media_first()
    # Keep legacy fields valid so a missing provenance validator cannot pass this test.
    raw.update(provenance=bad, source_script_used=True, generation_model='legacy', generation_reasoning='high')
    with pytest.raises(EDLContractError, match='provenance_invalid'):
        normalise_edl(raw)
    raw['source_script_used'] = False
    assert not VALIDATOR.is_valid(raw)
    write_edl(tmp_path / '06_edit_decision_list.json', raw)
    with pytest.raises(EDLBridgeError) as error:
        read_edl_bridge(tmp_path)
    assert error.value.state['validation']['code'] == 'provenance_invalid'


@pytest.mark.parametrize('script_used', [True, 0, 1, None, 'false', 'missing'])
def test_media_first_requires_explicit_false(script_used):
    raw = media_first()
    raw.update(generation_model='legacy', generation_reasoning='high')
    if script_used == 'missing':
        raw.pop('source_script_used')
    else:
        raw['source_script_used'] = script_used
    with pytest.raises(EDLContractError, match='provenance_script_conflict'):
        normalise_edl(raw)
    assert not VALIDATOR.is_valid(raw)


@pytest.mark.parametrize('field', ['generation_model', 'generation_reasoning'])
def test_optional_generation_metadata_is_preserved_but_not_fabricated(field):
    raw = media_first()
    raw[field] = 'declared metadata'
    assert normalise_edl(raw)[field] == raw[field]
    for value in ('', '  ', 1, None):
        raw[field] = value
        with pytest.raises(EDLContractError, match=f'{field}_invalid'):
            normalise_edl(raw)
        assert not VALIDATOR.is_valid(raw)


def test_preset_name_is_optional_and_identifier_stays_authoritative():
    raw = media_first()
    raw['provenance'].pop('preset_name')
    VALIDATOR.validate(normalise_edl(raw))
    assert normalise_edl(raw)['provenance'] == raw['provenance']


@pytest.mark.parametrize('field,code', [('generation_model', 'generation_model_missing'),
                                      ('generation_reasoning', 'generation_reasoning_missing'),
                                      ('source_script_used', 'source_script_required')])
def test_legacy_requirements_stay_unchanged(tmp_path, field, code):
    raw = json.loads((ROOT / 'tests/fixtures/r227-audio-legacy/v1.expected.json').read_text())
    raw.pop(field)
    with pytest.raises(EDLContractError, match=code):
        normalise_edl(raw)
    assert not VALIDATOR.is_valid(raw)
    write_edl(tmp_path / '06_edit_decision_list.json', raw)
    with pytest.raises(EDLBridgeError) as error:
        read_edl_bridge(tmp_path)
    assert error.value.state['validation']['code'] == f'{field}_missing'


@pytest.mark.parametrize('name', ['v1', 'v2'])
def test_additional_legacy_normalization_bytes_frozen(tmp_path, name):
    fixtures = ROOT / 'tests/fixtures/r227-provenance-legacy'
    freeze = json.loads((fixtures / 'freeze.json').read_text())
    expected = (fixtures / f'{name}.expected.json').read_bytes()
    assert hashlib.sha256(expected).hexdigest() == freeze['cases'][name]
    raw = json.loads((fixtures / f'{name}.input.json').read_text())
    output = tmp_path / 'output.json'
    write_edl(output, normalise_edl(raw))
    assert output.read_bytes() == expected


@pytest.fixture(scope='module')
def media(tmp_path_factory):
    root = tmp_path_factory.mktemp('r227-provenance')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=160x90:r=30:d=5',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=5',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', str(root / 'scene.mkv')],
                   check=True, capture_output=True)
    return root


@pytest.mark.parametrize('audio', [False, True])
def test_three_consumers_accept_media_first_and_handoff_binds_source(media, tmp_path, audio):
    raw = media_first(audio=audio)
    source = media / ('audio.json' if audio else 'plain.json')
    write_edl(source, raw)
    storyboard = tmp_path / 'storyboard.md'
    storyboard.write_text('确定性编排的合成素材')
    kdenlive = Backend().generate_from_edl(edl_path=source, output_dir=tmp_path / 'kdenlive', media_root=media,
                                         project_id='r227-e', project_revision=1)
    assert kdenlive['status'] == 'done'
    assert (tmp_path / 'kdenlive/timeline.kdenlive').is_file()
    subprocess.run([sys.executable, str(ROOT / 'scripts/creative/render_preview.py'), str(media), '--edl', str(source),
                    '--output', str(tmp_path / 'preview.mp4'), '--width', '160', '--height', '90', '--execute'],
                   check=True, capture_output=True, timeout=30)
    assert (tmp_path / 'preview.mp4').stat().st_size > 0
    result = handoff_pack.generate(project_id='r227-e', project_revision=1, edl_path=source,
                                   storyboard_path=storyboard, output_root=tmp_path / 'packs',
                                   materials_path=media, revision_basis_path=None)
    manifest_path = Path(result['manifest'])
    assert handoff_pack.validate(manifest_path)['status'] == 'passed'
    note_path = manifest_path.parent / '剪辑交接说明.md'
    sentence = '按素材和拍子自动排出（剪辑预设：轻快旅行）'
    assert sentence in note_path.read_text()
    # Rehashing a note with the source declaration removed cannot hide the omission.
    note_path.write_text(note_path.read_text().replace(sentence, '来源已删除'))
    manifest = json.loads(manifest_path.read_text())
    manifest['artifact_checksums']['handoff_note'] = hashlib.sha256(note_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(handoff_pack.HandoffError, match='来源|声音'):
        handoff_pack.validate(manifest_path)


def test_handoff_rejects_invalid_provenance_without_audio(media, tmp_path):
    raw = media_first()
    raw['provenance']['input_digest'] = 'bad'
    source = tmp_path / 'bad.json'; write_edl(source, raw)
    storyboard = tmp_path / 'storyboard.md'; storyboard.write_text('合成镜头')
    with pytest.raises(handoff_pack.HandoffError) as error:
        handoff_pack.generate(project_id='r227-e', project_revision=1, edl_path=source,
                              storyboard_path=storyboard, output_root=tmp_path / 'packs',
                              materials_path=media, revision_basis_path=None)
    assert error.value.code == 'provenance_invalid'
