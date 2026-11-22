"""Caption-free media-first handoff, without relaxing script-driven packages."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from edl_contract import EDLContractError, normalise_edl, write_edl
from edit_backends import handoff_pack as hp

FIXTURES = ROOT / 'tests/fixtures/r227-caption-legacy'
SCHEMA = json.loads((ROOT / 'schemas/edit-decision-list.schema.json').read_text())
VALIDATOR = Draft202012Validator(SCHEMA)


def document(captions=('missing', '')):
    raw = json.loads((FIXTURES / 'media-first.expected.json').read_text())
    for clip, caption in zip(raw['clips'], captions):
        if caption == 'missing':
            clip.pop('caption', None)
        else:
            clip['caption'] = caption
    return raw


def pack(tmp_path, raw=None):
    raw = document() if raw is None else raw
    (tmp_path / 'scene.mkv').write_bytes(b'non-private handoff fixture')
    edl_path = tmp_path / 'edl.json'; write_edl(edl_path, raw)
    storyboard = tmp_path / 'storyboard.md'; storyboard.write_text('合成镜头')
    result = hp.generate(project_id='r227-e2', project_revision=1, edl_path=edl_path,
                         storyboard_path=storyboard, output_root=tmp_path / 'packs',
                         materials_path=tmp_path, revision_basis_path=None)
    return result, Path(result['manifest'])


def rehash(manifest_path, artifact, path):
    manifest = json.loads(manifest_path.read_text())
    manifest['artifact_checksums'][artifact] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_edl(manifest_path, manifest)


@pytest.mark.parametrize('caption', ['missing', '', '  \n  '])
def test_media_first_normalizes_absent_or_blank_caption_to_empty(caption):
    raw = document((caption, caption))
    before = copy.deepcopy(raw)
    normalized = normalise_edl(raw)
    assert raw == before
    assert [clip['caption'] for clip in normalized['clips']] == ['', '']
    assert normalise_edl(normalized) == normalized
    VALIDATOR.validate(normalized)
    assert not any('slot' in clip['caption'] for clip in normalized['clips'])


@pytest.mark.parametrize('caption', ['missing', '', '  '])
def test_legacy_missing_caption_still_fails_contract_schema_and_handoff(tmp_path, caption):
    raw = document((caption, caption))
    raw.pop('provenance')
    raw.update(source_script_used=True, generation_model='fixture', generation_reasoning='high')
    with pytest.raises(EDLContractError, match='caption_missing'):
        normalise_edl(raw)
    if caption != '  ':
        assert not VALIDATOR.is_valid(raw)
    with pytest.raises(hp.HandoffError) as error:
        pack(tmp_path, raw)
    assert error.value.code == 'caption_missing'


def test_empty_caption_does_not_bypass_provenance_validation():
    raw = document()
    raw['provenance']['input_digest'] = 'bad'
    with pytest.raises(EDLContractError):
        normalise_edl(raw)
    assert not VALIDATOR.is_valid(raw)


def test_subtitle_alias_is_preserved_without_inventing_text():
    raw = document()
    raw['clips'][0]['subtitle'] = '真实字幕'
    assert [clip['caption'] for clip in normalise_edl(raw)['clips']] == ['真实字幕', '']


@pytest.mark.parametrize('audio', [False, True])
def test_no_caption_package_omits_srt_and_keeps_csv_blank(tmp_path, audio):
    raw = document()
    if audio:
        for clip in raw['clips']:
            clip['audio_mute'] = True
    result, path = pack(tmp_path, raw)
    manifest = json.loads(path.read_text())
    assert 'captions_srt' not in result['artifacts']
    assert 'captions_srt' not in manifest['artifacts']
    assert 'captions_srt' not in manifest['artifact_checksums']
    assert not (path.parent / 'captions.srt').exists()
    with (path.parent / 'clips.csv').open() as handle:
        assert [row['caption'] for row in csv.DictReader(handle)] == ['', '']
    for name in ('剪辑交接说明.md', '预览说明.md'):
        note = (path.parent / name).read_text()
        assert '这份粗剪没有字幕' in note
        assert 'captions.srt' not in note
    checked = hp.validate(path)
    assert checked['status'] == 'passed' and checked['caption_count'] == 0
    assert checked['clip_count'] == 2


def test_partially_captioned_handoff_keeps_one_per_clip_requirement(tmp_path):
    raw = document(('保留真实字幕', ''))
    normalized = normalise_edl(raw)
    VALIDATOR.validate(normalized)
    with pytest.raises(hp.HandoffError) as error:
        pack(tmp_path, raw)
    assert error.value.code == 'caption_missing'


@pytest.mark.parametrize('tamper', ['file', 'declaration', 'csv', 'timeline', 'timing', 'source', 'note'])
def test_caption_free_validation_still_rejects_tampering(tmp_path, tamper):
    _, path = pack(tmp_path)
    manifest = json.loads(path.read_text())
    if tamper in ('file', 'declaration'):
        srt = path.parent / 'captions.srt'
        srt.write_text('1\n00:00:00,000 --> 00:00:04,000\nslot_1\n')
        if tamper == 'declaration':
            manifest['artifacts']['captions_srt'] = srt.name
            manifest['artifact_checksums']['captions_srt'] = hashlib.sha256(srt.read_bytes()).hexdigest()
    elif tamper == 'timeline':
        manifest['timeline'][0]['caption'] = 'slot_1'
    elif tamper in ('csv', 'timing'):
        csv_path = path.parent / 'clips.csv'
        with csv_path.open() as handle:
            reader = csv.DictReader(handle); fields = reader.fieldnames; rows = list(reader)
        if tamper == 'csv':
            rows[0]['caption'] = 'slot_1'
            manifest['timeline'][0]['caption'] = 'slot_1'
        else:
            rows[0]['timeline_end_sec'] = '3.0'
        with csv_path.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        manifest['artifact_checksums']['clips_csv'] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    elif tamper == 'source':
        (tmp_path / 'scene.mkv').unlink()
    else:
        note = path.parent / '剪辑交接说明.md'
        note.write_text(note.read_text().replace('这份粗剪没有字幕', '字幕已生成'))
        manifest['artifact_checksums']['handoff_note'] = hashlib.sha256(note.read_bytes()).hexdigest()
    write_edl(path, manifest)
    with pytest.raises(hp.HandoffError):
        hp.validate(path)


def test_captioned_package_cannot_drop_its_srt(tmp_path):
    _, path = pack(tmp_path, document(('第一镜', '第二镜')))
    manifest = json.loads(path.read_text())
    manifest['artifacts'].pop('captions_srt'); manifest['artifact_checksums'].pop('captions_srt')
    (path.parent / 'captions.srt').unlink()
    write_edl(path, manifest)
    with pytest.raises(hp.HandoffError):
        hp.validate(path)


def test_captioned_media_first_outputs_are_byte_frozen(tmp_path):
    freeze = json.loads((FIXTURES / 'freeze.json').read_text())
    for name, digest in freeze['files'].items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == digest
    raw = json.loads((FIXTURES / 'media-first.input.json').read_text())
    write_edl(tmp_path / 'normalized.json', normalise_edl(raw))
    assert (tmp_path / 'normalized.json').read_bytes() == (FIXTURES / 'media-first.expected.json').read_bytes()
    timeline = json.loads((FIXTURES / 'timeline.json').read_text())['timeline']
    hp.write_clips_csv(tmp_path / 'clips.csv', timeline)
    hp.write_srt(tmp_path / 'captions.srt', timeline)
    hp.write_handoff_note(tmp_path / 'handoff.md', project_id='r227-e2', revision=1,
                          timeline=timeline, provenance=raw['provenance'])
    hp.write_preview_note(tmp_path / 'preview.md', timeline=timeline)
    for actual, expected in [('clips.csv','clips.expected.csv'), ('captions.srt','captions.expected.srt'),
                             ('handoff.md','handoff.expected.md'), ('preview.md','preview.expected.md')]:
        assert (tmp_path / actual).read_bytes() == (FIXTURES / expected).read_bytes()
