"""Synthetic negative cases for shot selection; no network or model weights."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from shot_quality import frame_metrics, motion_metrics, split_long_scene
from select_shots import (DEFAULT_CONFIG, apply_quality, deduplicate, validate_model_answer,
                          run_selection, make_sheets)


@pytest.fixture(scope='module')
def clips(tmp_path_factory):
    root = tmp_path_factory.mktemp('synthetic-shots')
    filters = {
        'sharp': 'testsrc2=size=320x240:rate=12:duration=3',
        'blur': 'testsrc2=size=320x240:rate=12:duration=3,gblur=sigma=12',
        'white': 'color=white:size=320x240:rate=12:duration=3',
        'pan': "testsrc2=size=420x340:rate=12:duration=3,loop=loop=-1:size=1:start=0,trim=duration=3,crop=320:240:x='30+t*12':y=40",
        'shake': "testsrc2=size=420x340:rate=12:duration=3,loop=loop=-1:size=1:start=0,trim=duration=3,crop=320:240:x='24+32*random(42)':y='24+32*random(23)'",
    }
    for name, source in filters.items():
        subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',source,
                        '-c:v','libx264','-threads','1',str(root/f'{name}.mp4')], check=True)
    return root


def test_blurred_and_overexposed_are_rejected(clips):
    import cv2
    def read(name):
        cap=cv2.VideoCapture(str(clips/f'{name}.mp4'))
        ok, frame=cap.read(); cap.release(); assert ok
        return frame_metrics(frame, DEFAULT_CONFIG)
    sharp,blur,white=map(read,['sharp','blur','white'])
    assert blur['blur_variance'] < sharp['blur_variance'] * .4
    row={'kind':'video','duration_sec':3,'metrics':blur,'unknown_reasons':[], 'rejection_reasons':[]}
    apply_quality(row,sharp['blur_variance'],DEFAULT_CONFIG)
    assert 'blur' in row['rejection_reasons']
    row.update(metrics=white,rejection_reasons=[])
    apply_quality(row,sharp['blur_variance'],DEFAULT_CONFIG)
    assert 'all_white' in row['rejection_reasons']


def test_shake_distinct_from_smooth_pan(clips):
    import cv2
    results={}
    for name in ['pan','shake']:
        cap=cv2.VideoCapture(str(clips/f'{name}.mp4')); frames=[]
        while True:
            ok,f=cap.read()
            if not ok: break
            frames.append(f)
        cap.release()
        results[name]=motion_metrics(frames,12,DEFAULT_CONFIG)
    assert results['pan']['shake_high_frequency'] < DEFAULT_CONFIG['shake_threshold']
    assert results['shake']['shake_high_frequency'] > DEFAULT_CONFIG['shake_threshold']


def test_unknown_never_becomes_selected(tmp_path,monkeypatch):
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'project'; project.mkdir()
    (project/'broken.mp4').write_bytes(b'not a video')
    doc=run_selection(project,skip_llm=True,aesthetic_model='none')
    assert doc['shots'][0]['status']=='unknown'
    assert doc['shots'][0]['metrics']['blur_variance'] is None
    assert doc['shots'][0]['unknown_reasons']
    assert doc['hook_candidates']==[]


def test_partial_frame_read_is_unknown(clips,tmp_path,monkeypatch):
    import select_shots as selector
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'p'; project.mkdir()
    import shutil
    shutil.copyfile(clips/'sharp.mp4',project/'clip.mp4')
    real=selector.read_frame
    monkeypatch.setattr(selector,'read_frame',lambda p,t,c: None if t>1 else real(p,t,c))
    doc=run_selection(project,skip_llm=True,aesthetic_model='none')
    assert all(r['status']=='unknown' for r in doc['shots'])
    assert any('frame' in e for r in doc['shots'] for e in r['unknown_reasons'])


def test_similar_shots_reuse_hash_groups(tmp_path,clips):
    import cv2
    cap=cv2.VideoCapture(str(clips/'sharp.mp4')); ok,f=cap.read(); cap.release(); assert ok
    rows=[]
    for i,score in enumerate([5.,7.]):
        p=tmp_path/f'{i}.jpg'; cv2.imwrite(str(p),f)
        rows.append({'id':f'S{i}','scene':'same','frames':[p.name], 'status':'usable',
                     'total_score':score,'duplicate_group':None,'duplicate_of':None,
                     'rejection_reasons':[]})
    deduplicate(rows,tmp_path,DEFAULT_CONFIG)
    assert rows[0]['duplicate_group']==rows[1]['duplicate_group']
    assert rows[0]['duplicate_of']=='S1'
    assert rows[0]['status']=='unused'
    assert rows[1]['status']=='usable'


def test_hallucinated_and_missing_ids_fail():
    with pytest.raises(ValueError,match='编号'):
        validate_model_answer({'decisions':[{'id':'S999','decision':'精选','reason':'好','has_title_or_sticker':False,'has_watermark':False,'has_occlusion':False}]}, {'S1'})
    with pytest.raises(ValueError):
        validate_model_answer({'decisions':[]},{'S1'})
    with pytest.raises(ValueError):
        validate_model_answer({'decisions':[{'id':'S1','decision':'精选','reason':''}]},{'S1'})


def test_long_scene_motion_boundaries():
    segments=split_long_scene(0,21,[(i/12,10. if i==54 else 0.) for i in range(252)],DEFAULT_CONFIG)
    assert segments[0][0]==0 and segments[-1][1]==21
    assert all(2<=b-a<=6 for a,b in segments)
    assert any(abs(b-4.5)<.1 for a,b in segments)
    assert all(a[1]==b[0] for a,b in zip(segments,segments[1:]))


def test_photos_have_no_motion_and_skip_llm_is_offline(tmp_path,monkeypatch):
    import select_shots as selector
    from PIL import Image
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'p'; project.mkdir()
    rng=np.random.default_rng(4)
    Image.fromarray(rng.integers(0,255,(120,160,3),dtype=np.uint8)).save(project/'photo.png')
    monkeypatch.setattr(selector,'generate_text',lambda **kw:pytest.fail('network forbidden'))
    doc=run_selection(project,skip_llm=True,aesthetic_model='none')
    row=doc['shots'][0]
    assert row['kind']=='photo' and row['start_sec'] is None
    assert row['metrics']['blur_variance'] is not None
    assert row['metrics']['shake_high_frequency'] is None
    assert row['metrics']['motion_mean'] is None
    assert doc['model_calls']==[] and doc['run_status']=='local_only'


def test_sample_is_directory_balanced_and_derived_excluded(tmp_path):
    from select_shots import discover_media
    for dirname in ['travel','sports','selfie','ai-analysis','output','raw-vault','draft-project']:
        folder=tmp_path/dirname; folder.mkdir()
        for index in range(4):
            (folder/f'{index}.mp4').touch()
    files,counts=discover_media(tmp_path,3,0)
    assert {p.parent.name for _,p in files}=={'travel','sports','selfie'}
    assert counts['video']==12


def test_project_escape_and_empty_batch_fail(tmp_path,monkeypatch):
    from select_shots import resolve_project,discover_media
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path/'allowed'))
    with pytest.raises(ValueError):resolve_project(tmp_path)
    with pytest.raises(ValueError):discover_media(tmp_path,0,0)


def test_schema_refuses_unknown_selected():
    from select_shots import validate_document
    from jsonschema import Draft202012Validator
    schema=json.loads((Path(__file__).resolve().parents[1]/'schemas/shots.schema.json').read_text())
    row_schema=schema['properties']['shots']['items']
    from select_shots import empty_row
    row=empty_row('S0123456789','photo','scene/x.jpg')
    row.update(status='selected',model_decision='精选',unknown_reasons=['cannot_read'])
    assert list(Draft202012Validator(row_schema).iter_errors(row))


def fake_scores(rows,*args,**kwargs):
    for row in rows:
        n=len(row['frames'])
        row['aesthetic']={'model':'offline-test-double','score':7. if n else None,
                          'frame_scores':[7.]*n,'frame_seconds':[0.]*n}
    return {'name':'offline-test-double'},[]


def test_two_videos_pipeline_keeps_one_and_preserves_sources(clips,tmp_path,monkeypatch):
    import select_shots as selector
    import shutil,hashlib
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'p'; project.mkdir()
    for name in ['a.mp4','b.mp4']:shutil.copyfile(clips/'pan.mp4',project/name)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in project.iterdir()}
    monkeypatch.setattr(selector,'score_aesthetics',fake_scores)
    doc=run_selection(project,skip_llm=True)
    assert len(doc['shots'])==2
    assert sum(r['status']=='usable' for r in doc['shots'])==1
    assert sum(r['duplicate_of'] is not None for r in doc['shots'])==1
    for name,digest in before.items():assert hashlib.sha256((project/name).read_bytes()).hexdigest()==digest
    assert all(not Path(r['source_relative_path']).is_absolute() for r in doc['shots'])


def test_llm_receives_images_medium_and_checks_ids(clips,tmp_path,monkeypatch):
    import select_shots as selector
    import shutil
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'p'; project.mkdir()
    shutil.copyfile(clips/'pan.mp4',project/'a.mp4')
    monkeypatch.setattr(selector,'score_aesthetics',fake_scores)
    calls=[]
    def answer(**kwargs):
        calls.append(kwargs)
        assert kwargs['reasoning_effort']=='medium'
        assert kwargs['image_paths'] and all(p.is_file() for p in kwargs['image_paths'])
        return json.dumps({'decisions':[{'id':'S999','decision':'精选','reason':'bad reference','has_title_or_sticker':False,'has_watermark':False,'has_occlusion':False}]})
    monkeypatch.setattr(selector,'generate_text',answer)
    with pytest.raises(ValueError,match='不存在的编号'):run_selection(project)
    assert len(calls)==1
    doc=json.loads((project/'ai-analysis/shots/shots.json').read_text())
    assert doc['run_status']=='failed'
    assert not any(r['status']=='selected' for r in doc['shots'])
    assert doc['model_calls'][0]['status']=='invalid_answer'


def test_scene_detection_and_long_split_real_ffmpeg(tmp_path,monkeypatch):
    import select_shots as selector
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    project=tmp_path/'p';project.mkdir()
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',
        'testsrc2=size=320x240:rate=12:duration=12',
        '-vf','loop=loop=-1:size=1:start=0,trim=duration=12',
        '-c:v','libx264','-threads','1',str(project/'long.mp4')],check=True)
    monkeypatch.setattr(selector,'score_aesthetics',fake_scores)
    doc=run_selection(project,skip_llm=True)
    rows=doc['shots']
    assert len(rows)>=2
    assert all(2<=r['duration_sec']<=6 for r in rows)
    assert rows[0]['start_sec']==0 and abs(rows[-1]['end_sec']-12)<.1
    assert all(len(r['frame_measurements'])==3 for r in rows)
