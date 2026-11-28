"""Synthetic end-to-end draft checks; no private material or running Studio."""
import copy
import csv
import re
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from creative.roughcut_planner import plan_roughcut
from studio.roughcut.drafts import DraftError, compile_roughcut_edl, generate_draft, readback_video


def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr.decode(errors='replace')[-2000:]
    return result.stdout


@pytest.fixture(scope='module')
def case(tmp_path_factory):
    root = tmp_path_factory.mktemp('r226-drafts')
    config = json.loads((ROOT/'scripts/editing_presets.json').read_text())
    spec = json.loads((ROOT/'tests/fixtures/r226-editing-techniques/drafts/synthetic.json').read_text())
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=160x90:r=30:d=90',
         '-f','lavfi','-i','sine=frequency=440:duration=90','-c:v','libx264','-preset','ultrafast','-c:a','pcm_s16le',root/'source.mkv'])
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=red:s=160x90','-frames:v','1',root/'photo.png'])
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=900:duration=120',root/'music.wav'])
    shots = [dict(id=f's{i}',media_id='photo' if i in spec['photo_indices'] else 'video',
                  kind='photo' if i in spec['photo_indices'] else 'video',
                  scene='travel' if i<14 else 'sports-meet' if i<21 else 'selfie-moments',
                  start_sec=2,end_sec=90,has_audio=i not in spec['photo_indices']) for i in range(27)]
    beats = [i*.5 for i in range(240)]
    beat = dict(track_id='one',title='Synthetic',duration_seconds=120,bpm=120,meter=4,beats=beats,
                downbeats=beats[::4],beat_energy=[.5]*240,sections=[dict(start=0,end=10,kind='quiet'),dict(start=10,end=120,kind='build')],registry_version=1)
    inputs = dict(shots=shots,beat_maps={'one':beat,'two':dict(beat,track_id='two')},
                  playlist=[dict(id='a',track_id='one'),dict(id='b',track_id='two')],
                  preset=config['presets'][0],settings=config['settings'],transcripts={})
    # Trusted word times are explicit, never inferred from an entire selfie.
    inputs['transcripts']['video'] = dict(status='ok',precision='word',auto_cut_allowed=True,
        segments=[dict(start_sec=2,end_sec=8,precision='word',words=[dict(start=2,end=3,text='甲'),dict(start=3.5,end=5,text='乙'),dict(start=6.5,end=8,text='丙')])])
    plan = plan_roughcut(**inputs)
    return dict(workspace=root,media_root=root,plan=plan,planner_inputs=inputs,
                sources_by_media={'video':root/'source.mkv','photo':root/'photo.png'},
                music_sources={'one':root/'music.wav','two':root/'music.wav'},
                project_id='synthetic',project_revision=7,plan_revision=2)


def test_compile_provenance_audio_and_tail(case):
    args = {k:v for k,v in case.items() if k not in ('workspace','media_root','plan_revision')}
    value = compile_roughcut_edl(**args)
    assert value['source_script_used'] is False
    assert value['provenance']['kind'] == 'media_first_planner'
    assert len(value['provenance']['input_digest']) == 64
    assert 'generation_model' not in value
    assert len(value['clips']) == 27
    assert value['clips'][-1]['time_range'].endswith(f"{case['plan']['metrics']['duration_sec']:.3f}")
    assert case['plan']['metrics']['duration_sec'] - case['plan']['metrics']['last_cut_sec'] == pytest.approx(1.6)
    assert value['audio_beds'] and value['music'][1]['source_start_sec'] >= 8
    assert any('audio_lead_sec' in c for c in value['clips'])
    assert any(m['duck_regions'] for m in value['music'])
    changed = copy.deepcopy(args)
    changed['planner_inputs']['settings']['duck_db'] = -10
    with pytest.raises(DraftError, match='roughcut_inputs_stale'):
        compile_roughcut_edl(**changed)


@pytest.mark.parametrize('choice',[dict(editor='chatcut',method='external'),dict(editor='openchatcut',method='external'),dict(editor='openfilm',method='self')])
def test_unsupported_no_output_or_fallback(case,choice):
    before = set(case['workspace'].rglob('*'))
    with pytest.raises(DraftError,match='draft_backend_unsupported'):
        generate_draft(**case,editor_choice=choice,width=160,height=90)
    assert set(case['workspace'].rglob('*')) == before


@pytest.fixture(scope='module')
def generated(case):
    result = generate_draft(**case,editor_choice=dict(editor='otio_kdenlive',method='external'),width=160,height=90)
    return result


def test_real_kdenlive_readback_27_sources_and_cuts(case,generated):
    receipt = json.loads(Path(generated['receipt_path']).read_text())
    assert receipt['status'] == 'done'
    from jsonschema import Draft202012Validator
    schema=json.loads((ROOT/'schemas/roughcut-api.schema.json').read_text())
    Draft202012Validator({**schema,'$ref':'#/$defs/draft_result'}).validate(generated['result'])
    for artifact in generated['artifacts']:
        Draft202012Validator({**schema,'$ref':'#/$defs/artifact'}).validate(artifact)
        indexed=generated['artifact_index'][artifact['id']]
        assert (case['workspace']/indexed['relative_path']).is_file()
    assert all(c['status']=='passed' for c in generated['result']['checks'])
    rows = readback_video(Path(generated['directory'])/'kdenlive/timeline.kdenlive')
    assert len(rows) == 27
    for row, clip, binding in zip(rows,case['plan']['clips'],receipt['shot_bindings']):
        assert row['source'] == binding['edl_source']
        assert abs(row['start']-clip['start']) <= 1/30+.002
        assert abs(row['end']-clip['end']) <= 1/30+.002
        assert abs(row['source_start']-(clip['source_start'] or 0)) <= 1/30+.002
        assert abs(row['source_end']-((clip['source_start'] or 0)+clip['end']-clip['start'])) <= 1/30+.002
    preview = next(a for a in generated['artifacts'] if a['kind']=='preview')
    path = case['workspace']/generated['artifact_index'][preview['id']]['relative_path']
    data=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',path]))
    assert abs(float(data['format']['duration'])-case['plan']['metrics']['duration_sec']) <= 1/30+.02
    # Decode the last frame too: an image packet cannot masquerade as a held photo.
    frame=run(['ffmpeg','-v','error','-sseof','-0.10','-i',path,'-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
    assert len(frame)==160*90*3
    assert sum(frame[0::3])/len(frame[0::3])>200
    assert sum(frame[1::3])/len(frame[1::3])<20
    assert {s['codec_type'] for s in data['streams']} >= {'audio','video'}


def test_readback_rejects_modified_picture(generated):
    path=Path(generated['directory'])/'kdenlive/timeline.kdenlive'
    tree=ET.parse(path)
    entry=next(p for p in tree.getroot().findall('playlist') if p.findtext("property[@name='content_os:layer']")=='primary').find('entry')
    entry.set('in',str(int(entry.get('in'))+3))
    altered=path.with_name('tampered.kdenlive');tree.write(altered)
    assert readback_video(altered) != readback_video(path)


def test_guide_validated_package_and_same_edl_preview(case):
    result=generate_draft(**case,editor_choice=dict(editor='otio_kdenlive',method='guide'),width=160,height=90)
    from edit_backends.handoff_pack import validate
    validate(Path(result['directory'])/'edit-handoff/7/manifest.json')
    receipt=json.loads(Path(result['receipt_path']).read_text())
    assert receipt['status']=='done'
    statuses={c['id']:c['status'] for c in result['result']['checks']}
    assert statuses['readback']=='manual' and statuses['audio']=='manual'
    assert len(receipt['shot_bindings'])==27
    assert any(a['kind']=='preview' for a in result['artifacts'])
    directory=Path(result['directory'])
    package=directory/'edit-handoff/7'
    assert not (package/'captions.srt').exists()
    manifest=json.loads((package/'manifest.json').read_text())
    assert 'captions_srt' not in manifest['artifacts']
    assert '这份粗剪没有字幕' in (package/'剪辑交接说明.md').read_text()
    with (package/'clips.csv').open(newline='') as handle:
        rows=list(csv.DictReader(handle))
    assert len(rows)==27
    assert all(row['caption']=='' for row in rows)
    # Machine identities remain in the private audit receipt, never in editable
    # captions, the handoff package, its source EDL or its storyboard.
    paths=[p for p in package.rglob('*') if p.is_file()]
    paths += [directory/'06_edit_decision_list.json',directory/'05_storyboard.md']
    assert_no_shot_placeholders(paths,[c['shot_id'] for c in case['plan']['clips']])


def assert_no_shot_placeholders(paths, shot_ids):
    for path in paths:
        text=path.read_text(encoding='utf-8')
        assert '需人工替换' not in text and '请人工替换' not in text, path
        for shot_id in shot_ids:
            assert re.search(r'(?<![A-Za-z0-9_])'+re.escape(shot_id)+r'(?![A-Za-z0-9_])',text) is None, (path,shot_id)


def test_compiled_edl_has_no_subtitle_placeholders(case):
    args={k:v for k,v in case.items() if k not in ('workspace','media_root','plan_revision')}
    edl=compile_roughcut_edl(**args)
    assert all(c['caption']=='' for c in edl['clips'])
    for clip in edl['clips']:
        assert '替换' not in clip['edit_note']
        assert not any(s['shot_id'] in clip['edit_note'] for s in case['plan']['clips'])


def test_failure_receipt_never_success(case,monkeypatch):
    import studio.roughcut.drafts as drafts
    def failed(*args,**kwargs): raise RuntimeError('synthetic render failure')
    monkeypatch.setattr(drafts,'execute_plan',failed)
    with pytest.raises(DraftError,match='preview_failed') as caught:
        generate_draft(**case,editor_choice=dict(editor='otio_kdenlive',method='guide'),width=160,height=90)
    receipt=json.loads(Path(caught.value.receipt_path).read_text())
    assert receipt['status']=='failed' and not receipt['artifacts']


def test_outside_media_root_rejected(case,tmp_path):
    with pytest.raises(DraftError,match='draft_failed'):
        generate_draft(**dict(case,workspace=tmp_path,media_root=case['workspace']),editor_choice=dict(editor='otio_kdenlive',method='guide'))


def test_picture_tampering_blocks_success(case,monkeypatch):
    import studio.roughcut.drafts as drafts
    original=drafts.Backend.generate_from_edl
    def corrupt(self,**kwargs):
        value=original(self,**kwargs)
        path=kwargs['output_dir']/'timeline.kdenlive'
        tree=ET.parse(path)
        playlist=next(p for p in tree.getroot().findall('playlist') if p.findtext("property[@name='content_os:layer']")=='primary')
        entry=playlist.find('entry');entry.set('in',str(int(entry.get('in'))+4));tree.write(path)
        return value
    monkeypatch.setattr(drafts.Backend,'generate_from_edl',corrupt)
    with pytest.raises(DraftError,match='draft_failed') as caught:
        generate_draft(**case,editor_choice=dict(editor='otio_kdenlive',method='external'),width=160,height=90)
    receipt=json.loads(Path(caught.value.receipt_path).read_text())
    assert receipt['status']=='failed' and receipt['artifacts']==[]


def test_fractional_source_times_quantize_inside_selected_range(case):
    args={k:copy.deepcopy(v) for k,v in case.items() if k not in ('workspace','media_root','plan_revision')}
    for shot in args['planner_inputs']['shots']:
        if shot['kind']=='video':shot['start_sec']=2.000333
    args['plan']=plan_roughcut(**args['planner_inputs'])
    edl=compile_roughcut_edl(**args)
    shots={s['id']:s for s in args['planner_inputs']['shots']}
    for clip,row in zip(edl['clips'],args['plan']['clips']):
        if row['kind']=='photo':continue
        a,b=map(float,clip['time_range'].split('-'))
        assert clip['source_start_sec']>=shots[row['shot_id']]['start_sec']
        assert clip['source_start_sec']+b-a<=shots[row['shot_id']]['end_sec']+1e-6
        assert abs(clip['source_start_sec']*1000-round(clip['source_start_sec']*1000))<1e-6


def test_nonframe_cuts_use_explicit_editor_tolerance(case):
    args=copy.deepcopy(case)
    inputs=args['planner_inputs']
    inputs['shots']=inputs['shots'][:3]
    inputs['playlist']=inputs['playlist'][:1]
    for beat in inputs['beat_maps'].values():
        beat['beats']=[round(i*.507,6) for i in range(236)]
        beat['downbeats']=beat['beats'][::4]
        beat['beat_energy']=[.5]*len(beat['beats'])
    args['plan']=plan_roughcut(**inputs)
    result=generate_draft(**args,editor_choice=dict(editor='otio_kdenlive',method='external'),width=160,height=90)
    receipt=json.loads(Path(result['receipt_path']).read_text())
    audio=receipt['readback']['audio']
    assert audio['audio_mismatches']==[]
    assert abs(audio['duration']-audio['nominal_duration_sec'])<=1/30


def test_heic_photo_is_prepared_without_rewriting_original(case,monkeypatch):
    import pillow_heif
    import hashlib
    def no_parent_encoding(*args,**kwargs):
        pytest.fail('Generate HEIC fixtures in a subprocess, not with pillow_heif in pytest')
    monkeypatch.setattr(pillow_heif,'from_pillow',no_parent_encoding)
    heic=case['workspace']/'synthetic.heic'
    run(['sips','-s','format','heic',case['workspace']/'photo.png','--out',heic])
    digest=hashlib.sha256(heic.read_bytes()).hexdigest()
    args=copy.deepcopy(case)
    args['planner_inputs']['shots']=[dict(id='still',media_id='photo',kind='photo',scene='travel')]
    args['planner_inputs']['playlist']=args['planner_inputs']['playlist'][:1]
    args['plan']=plan_roughcut(**args['planner_inputs'])
    args['sources_by_media']={'photo':heic}
    result=generate_draft(**args,editor_choice=dict(editor='otio_kdenlive',method='external'),width=160,height=90)
    assert hashlib.sha256(heic.read_bytes()).hexdigest()==digest
    receipt=json.loads(Path(result['receipt_path']).read_text())
    assert receipt['shot_bindings'][0]['original_source']==str(heic)
    assert receipt['readback']['pictures'][0]['source'].endswith('.mp4')


def test_preview_only_renders_without_editor_or_handoff(case,monkeypatch):
    import studio.roughcut.drafts as drafts
    import hashlib
    def forbidden(*args,**kwargs): pytest.fail('Preview invoked a draft exporter')
    monkeypatch.setattr(drafts.Backend,'generate_from_edl',forbidden)
    monkeypatch.setattr(drafts.handoff_pack,'generate',forbidden)
    paths=[*case['sources_by_media'].values(),*case['music_sources'].values()]
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    result=drafts.generate_preview(**case,width=160,height=90)
    directory=Path(result['directory'])
    assert not (directory/'kdenlive').exists()
    assert not (directory/'edit-handoff').exists()
    assert not list(directory.rglob('*.kdenlive'))
    assert not list(directory.rglob('*.otio'))
    assert not list(directory.rglob('captions.srt'))
    assert [a['kind'] for a in result['artifacts']]==['preview']
    assert set(result['artifact_index'])=={a['id'] for a in result['artifacts']}
    preview=result['artifacts'][0]
    item=result['artifact_index'][preview['id']]
    assert item['content_type']==preview['content_type']=='video/mp4'
    assert case['workspace']/item['allowed_root']==directory
    path=case['workspace']/item['relative_path']
    assert path.is_file() and path.is_relative_to(directory)
    assert abs(result['duration_sec']-case['plan']['metrics']['duration_sec'])<=1/30+.02
    receipt=json.loads(Path(result['receipt_path']).read_text())
    assert receipt['status']=='done'
    assert 'editor' not in receipt and 'method' not in receipt
    assert len(receipt['shot_bindings'])==27
    edl=json.loads((directory/'06_edit_decision_list.json').read_text())
    assert all(c['caption']=='' for c in edl['clips'])
    preview_plan=json.loads((directory/'preview-plan.json').read_text())
    assert preview_plan['audio_plan']['source_validation']=='passed'
    assert {c['source'] for c in preview_plan['clips']}=={c['source_file'] for c in edl['clips']}
    frame=run(['ffmpeg','-v','error','-sseof','-0.10','-i',path,'-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
    assert len(frame)==160*90*3 and sum(frame[0::3])/len(frame[0::3])>200
    assert {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}==before


@pytest.mark.parametrize('method',['external','guide'])
def test_draft_calls_public_preview_once(case,monkeypatch,method):
    import studio.roughcut.drafts as drafts
    original=drafts.generate_preview
    render=drafts.execute_plan
    generated=[];renders=[]
    def preview(**kwargs):
        value=original(**kwargs)
        generated.append((kwargs,value))
        return value
    def counted_render(plan):
        renders.append(plan)
        return render(plan)
    monkeypatch.setattr(drafts,'generate_preview',preview)
    monkeypatch.setattr(drafts,'execute_plan',counted_render)
    result=drafts.generate_draft(**case,editor_choice=dict(editor='otio_kdenlive',method=method),width=160,height=90)
    assert len(generated)==len(renders)==1
    kwargs,preview_result=generated[0]
    assert 'editor_choice' not in kwargs
    assert result['directory']==preview_result['directory']
    assert [a for a in result['artifacts'] if a['kind']=='preview']==preview_result['artifacts']
    directory=Path(result['directory'])
    assert (directory/('kdenlive/timeline.kdenlive' if method=='external' else 'edit-handoff/7/manifest.json')).is_file()
    receipt=json.loads(Path(result['receipt_path']).read_text())
    assert receipt['status']=='done' and receipt['method']==method


def test_preview_failure_has_no_publishable_artifacts(case,monkeypatch):
    import studio.roughcut.drafts as drafts
    def failed(*args,**kwargs): raise RuntimeError('synthetic preview failure')
    monkeypatch.setattr(drafts,'execute_plan',failed)
    with pytest.raises(DraftError,match='preview_failed') as caught:
        drafts.generate_preview(**case,width=160,height=90)
    receipt=json.loads(Path(caught.value.receipt_path).read_text())
    assert receipt['status']=='failed' and not receipt['artifacts']
    directory=Path(caught.value.receipt_path).parent
    assert not (directory/'kdenlive').exists() and not (directory/'edit-handoff').exists()


def test_preview_rejects_source_change_during_render(case,monkeypatch):
    import studio.roughcut.drafts as drafts
    original=drafts.execute_plan
    source=case['music_sources']['one']
    data=source.read_bytes()
    def changed(plan):
        original(plan)
        source.write_bytes(data+b'synthetic-change')
    monkeypatch.setattr(drafts,'execute_plan',changed)
    try:
        with pytest.raises(DraftError,match='roughcut_inputs_stale') as caught:
            drafts.generate_preview(**case,width=160,height=90)
        receipt=json.loads(Path(caught.value.receipt_path).read_text())
        assert receipt['status']=='failed' and not receipt['artifacts']
    finally:
        source.write_bytes(data)
