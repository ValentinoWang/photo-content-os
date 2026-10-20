"""R223 migration, registry governance, projection, and queue failure contracts."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from music_library.library import MusicLibrary, validate_track
from music_library.errors import MusicError
from music_library.cache import write_json
from migrate_music_library_v2 import migrate
from validate_music_analysis_registry import validate, check_copy, published_registry
from studio.music_analysis import AnalysisQueue, derive, registry, failure, read_analysis, validate_analysis, read_rhythm, run_worker
from studio.media_review import MediaReview

CHECKER = Path(os.environ.get('UI_COPY_QUALITY_CHECKER', '/nonexistent'))


@pytest.fixture
def library(tmp_path):
    library = MusicLibrary(tmp_path, measure=lambda _:dict(duration_seconds=24.0, sample_rate_hz=22050,loudness_lufs=-12,loudness_status='measured'))
    audio = tmp_path / 'synthetic.wav'; audio.write_bytes(b'synthetic-audio')
    library.import_local(audio)
    return library


def v1(library):
    tracks=library.list_tracks()
    for track in tracks:
        track.update(schema_version=1,license_status='unknown',attribution=None,bpm=None,beats=None,sections=None)
        write_json(library.root/track['file_sha256']/'track.json',track)
    write_json(library.root/'index.json',dict(schema_version=1,tracks=tracks))
    return {p.relative_to(library.root):p.read_bytes() for p in library.root.rglob('*') if p.is_file() and p.name!='.lock'}


def test_migration_preview_backup_apply_idempotence(library,tmp_path):
    before=v1(library)
    with pytest.raises(MusicError,match='先运行迁移'):library.list_tracks()
    assert migrate(tmp_path)['state']=='preview'
    assert before=={p: (library.root/p).read_bytes() for p in before}
    result=migrate(tmp_path,apply=True,backup_root=tmp_path/'backups')
    backup=Path(result['backup'])
    assert result['state']=='applied'
    assert (backup/'index.json').read_bytes()==before[Path('index.json')]
    for p,b in before.items():
        if p.name=='track.json':assert (backup/p).read_bytes()==b
        elif p.name!='index.json':assert (library.root/p).read_bytes()==b
    track=library.list_tracks()[0];validate_track(track)
    assert track['schema_version']==2
    assert not {'license_status','attribution','bpm','beats','sections'}&track.keys()
    after={p:p.read_bytes() for p in library.root.rglob('*.json')}
    assert migrate(tmp_path,apply=True,backup_root=tmp_path/'backups')['state']=='unchanged'
    assert after=={p:p.read_bytes() for p in after}
    assert len(list((tmp_path/'backups').iterdir()))==1


def test_backup_failure_never_writes(library,tmp_path,monkeypatch):
    import migrate_music_library_v2 as migration
    before=v1(library)
    def fail(*args):raise OSError('backup disk full')
    monkeypatch.setattr(migration.shutil,'copy2',fail)
    with pytest.raises(OSError):migrate(tmp_path,apply=True,backup_root=tmp_path/'backups')
    assert before=={p:(library.root/p).read_bytes() for p in before}


def test_migration_preserves_derived_files_and_rolls_back(library,tmp_path,monkeypatch):
    import migrate_music_library_v2 as migration
    track=library.list_tracks()[0];folder=library.root/track['file_sha256'];(folder/'peaks.json').write_text('[0.1]')
    (library.root/'.attempts').mkdir();(library.root/'.attempts/a.json').write_text('{}')
    before=v1(library);write=migration.write_json
    def fail_index(path,value):
        if path.name=='index.json':raise OSError('write failure')
        write(path,value)
    monkeypatch.setattr(migration,'write_json',fail_index)
    with pytest.raises(OSError):migrate(tmp_path,apply=True,backup_root=tmp_path/'backups')
    assert before=={p:(library.root/p).read_bytes() for p in before}


@pytest.mark.parametrize('edit',[
 lambda r:r['tag_categories'][0]['tags'].append(copy.deepcopy(r['tag_categories'][0]['tags'][0])),
 lambda r:r['tag_categories'][0]['tags'][0].update(name=None),
 lambda r:r['display']['panel_order'].append('missing'),
 lambda r:r['tag_categories'][1]['rules'].update(min_score=1.1),
 lambda r:r['analyzers']['tags']['models'][0].pop('sha256'),
 lambda r:r['analyzers']['tags']['models'][0].pop('license'),
 lambda r:r['tag_categories'].clear(),
 lambda r:r['tag_categories'][0].update(model='missing'),
])
def test_registry_red_structure(edit):
    r=registry();edit(r);assert validate(r)


def test_registry_history_red_green():
    old=registry();r=copy.deepcopy(old)
    r['tag_categories'][0]['tags'][0]['name']='蓝调'
    assert any('registry_version' in e for e in validate(r,old))
    r['registry_version']+=1
    assert any('changelog' in e for e in validate(r,old))
    r['changelog'].append(dict(registry_version=2,date='2026-10-21',request='test',change='改名'))
    assert validate(r,old)==[]
    r['tag_categories'][0]['tags'].pop(0)
    assert any('deleted' in e for e in validate(r,old))
    r=copy.deepcopy(old);r['registry_version']=2;r['changelog'].append(dict(registry_version=2,date='2026-10-21',request='test',change='下线'))
    r['tag_categories'][0]['tags'][0]['status']='deprecated'
    assert validate(r,old)==[]
    r['tag_categories'][0]['tags'][0]['source_label']='Reused'
    assert any('reused' in e for e in validate(r,old))


def test_registry_unreadable_zero_and_bad_base(tmp_path):
    assert validate({})
    path=tmp_path/'bad.json';path.write_text('{')
    for file in [path,tmp_path/'missing.json']:
        result=subprocess.run([sys.executable,str(ROOT/'scripts/validate_music_analysis_registry.py'),'--registry',str(file)],capture_output=True)
        assert result.returncode!=0
    with pytest.raises(subprocess.CalledProcessError):published_registry('does-not-exist')
    with pytest.raises(ValueError):check_copy(registry(),None)


def test_registry_copy_red_green():
    if not CHECKER.is_file():pytest.skip('UI_COPY_QUALITY_CHECKER required for external Core copy check')
    check_copy(registry(),str(CHECKER))
    r=registry();r['tag_categories'][0]['tags'][0]['name']='测试TODO'
    with pytest.raises(ValueError,match='copy check failed'):check_copy(r,str(CHECKER))


def test_derive_design_fixtures_and_live_registry(tmp_path):
    fixtures=json.loads((ROOT/'tests/fixtures/r223/scores.json').read_text())
    expected={
      'Turn Back Time':dict(style='Tropical House',mood=['mood.deep','mood.happy'],scene=['scene.summer'],voice=['voice.voice'],voice_uncertain=False,instrument=['instrument.bass','instrument.synthesizer','instrument.keyboard']),
      'Fever Pitch':dict(style='House',mood=['mood.deep'],scene=['scene.summer'],voice=[],voice_uncertain=True,instrument=['instrument.bass','instrument.synthesizer','instrument.keyboard']),
      'CRUSH VIBE':dict(style=None,mood=['mood.melodic','mood.space','mood.dark'],scene=[],voice=['voice.instrumental'],voice_uncertain=False,instrument=['instrument.synthesizer','instrument.sampler'])}
    for title,expect in expected.items():
        actual=derive(fixtures[title]);assert actual['genre']==['genre.electronic']
        for k,v in expect.items():assert actual[k]==v,(title,k,actual[k])
    r=registry();path=tmp_path/'registry.json';write_json(path,r)
    before=derive(fixtures['Turn Back Time'],registry(path))
    r['tag_categories'][1]['rules']['min_score']=1
    r['tag_categories'][4]['tags'][3]['status']='deprecated'
    r['tag_categories'][0]['tags'][4]['name']='电音'
    write_json(path,r);fresh=registry(path);after=derive(fixtures['Turn Back Time'],fresh)
    assert before['mood'] and after['mood']==[]
    assert 'instrument.bass' not in after['instrument']
    assert fresh['tag_categories'][0]['tags'][4]['name']=='电音'


def done(track):
    reg=registry();lock=json.loads((ROOT/'third_party/edit-tools.lock.json').read_text())['music_analysis']
    scores={}
    for head,model in lock['heads'].items():
        count={'genre':400,'moodtheme':56,'instrument':40,'voice':2}[head]
        scores[head]=[['Synthetic '+str(i),.1] for i in range(count)]
    return dict(schema_version=1,file_sha256=track['file_sha256'],duration_seconds=track['duration_seconds'],registry_version=1,
                beat=dict(status='done',beats=[float(x)/2 for x in range(48)],downbeats=[float(x)*2 for x in range(12)],beat_energy=[.5]*48,sections=[dict(start=0,end=24.0,kind='quiet')],package_versions={'beat-this':'1.1.0'},models=['beat-this-final0'],registry_version=1),
                tags=dict(status='done',scores=scores,package_versions={'essentia-tensorflow':'2.1b6.dev1389'},models=list(lock['heads'].values()),registry_version=1))


def review_for(library):
    review=object.__new__(MediaReview);review.music=library;review.analysis_queue=AnalysisQueue(library);return review


@pytest.mark.parametrize('part,code',[(None,None),('beat','worker_error'),('tags','worker_error'),('beat','audio_unreadable'),('tags','future_failure_123')])
def test_projection_status_and_unknown_codes(library,part,code):
    track=library.list_tracks()[0];data=done(track)
    if part:data[part]=failure(code)
    write_json(library.root/track['file_sha256']/'analysis.json',data)
    review=review_for(library);payload=review.music_payload();row=payload['tracks'][0]
    assert payload['registry_version']==1 and payload['taxonomy']['display']
    assert 'scores' not in json.dumps(row)
    if part:assert row[part]['failure']==dict(code=code,retryable=code!='audio_unreadable')
    else:
        assert row['beat']['bpm']==120 and row['beat']['meter']==4
        assert read_rhythm(library,track['file_sha256'])['bars']==data['beat']['downbeats']


def test_invalid_sidecars_fail_loudly(library):
    track=library.list_tracks()[0];path=library.root/track['file_sha256']/'analysis.json'
    path.write_text('{')
    with pytest.raises(MusicError):review_for(library).music_payload()
    data=done(track);data['beat']['beats'][1]=999;write_json(path,data)
    with pytest.raises(MusicError):read_analysis(path.parent,track)


def test_queue_serial_dedup_status_and_partial_reanalysis(library):
    track=library.list_tracks()[0];data=done(track);folder=library.root/track['file_sha256']
    entered=threading.Event();release=threading.Event();calls=[]
    def worker(track,folder,part):
        calls.append(part);entered.set();assert release.wait(5)
        return {p:data[p] for p in ('beat','tags') if part in ('all',p)}
    queue=AnalysisQueue(library,worker=worker)
    queue.enqueue(track['file_sha256'],'all');queue.enqueue(track['file_sha256'],'beat')
    assert len(queue.pending)==1
    assert queue.state(track['file_sha256'])['beat']['status']=='queued'
    queue.start();assert entered.wait(5)
    queue.enqueue(track['file_sha256'],'all');assert not queue.pending
    assert queue.state(track['file_sha256'])['beat']['status']=='analyzing'
    release.set();assert queue.wait_idle(10)
    assert calls==['all']
    old=read_analysis(folder,track);queue.enqueue(track['file_sha256'],'tags');assert queue.wait_idle(10)
    assert read_analysis(folder,track)['beat']==old['beat'];assert calls==['all','tags']
    queue.close()


def test_queue_crashing_worker_survives_and_import_callback(library):
    track=library.list_tracks()[0]
    def worker(*args):raise RuntimeError('synthetic crash')
    queue=AnalysisQueue(library,worker=worker);queue.start();assert queue.wait_idle(5)
    assert queue.thread.is_alive() and read_analysis(library.root/track['file_sha256'],track)['beat']['failure']['code']=='worker_error'
    queue.close()
    seen=[];library.on_import=lambda track:seen.append(track['file_sha256'])
    library.import_local(library.root/track['file_sha256']/track['audio_file'])
    assert seen==[track['file_sha256']]


def test_timeout_and_unknown_failure_preserved(library,monkeypatch):
    import studio.music_analysis as analysis
    track=library.list_tracks()[0]
    def timeout(*a,**k):raise subprocess.TimeoutExpired('worker',.01)
    monkeypatch.setattr(analysis.subprocess,'run',timeout)
    assert run_worker(track,library.root/track['file_sha256'],'tags',timeout=.01)['tags']['failure']['code']=='timeout'


def test_http_projection_all_states_and_retry_contract(library,tmp_path,monkeypatch):
    from http.server import ThreadingHTTPServer
    import urllib.request
    import urllib.error
    from studio.server import StudioApplication
    from studio.project_store import ProjectStore
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(tmp_path))
    app=StudioApplication(ProjectStore(tmp_path/'state'))
    app.media_review=review_for(library)
    server=ThreadingHTTPServer(('127.0.0.1',0),app.handler())
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_address[1]}'
    track=library.list_tracks()[0];identifier=track['file_sha256'];path=library.root/identifier/'analysis.json';queue=app.media_review.analysis_queue
    def get():return json.load(urllib.request.urlopen(base+'/api/review/music'))['tracks'][0]
    try:
        for part,code in [('beat','worker_error'),('tags','worker_error'),('beat','audio_unreadable'),('tags','future_model_failure')]:
            data=done(track);data[part]=failure(code);write_json(path,data)
            assert get()[part]['failure']['code']==code
        write_json(path,done(track));assert get()['beat']['status']=='done'
        queue.enqueue(identifier,'all');assert get()['tags']['status']=='queued'
        with queue.condition:queue.active=queue.pending.popleft()
        assert get()['beat']['status']=='analyzing'
        body=json.dumps({'part':'tags'}).encode()
        req=urllib.request.Request(base+f'/api/review/music/{identifier}/reanalyze',data=body,headers={'Content-Type':'application/json','X-Content-OS-CSRF':app.csrf_token,'Origin':base})
        assert json.load(urllib.request.urlopen(req))['ok']
        assert not queue.pending # currently analyzing all, duplicate is coalesced
        req=urllib.request.Request(base+f'/api/review/music/{identifier}/reanalyze',data=json.dumps({'part':'other'}).encode(),headers={'Content-Type':'application/json','X-Content-OS-CSRF':app.csrf_token,'Origin':base})
        with pytest.raises(urllib.error.HTTPError) as exc:urllib.request.urlopen(req)
        assert exc.value.code==400
    finally:
        server.shutdown();server.server_close();thread.join(5)


def test_unreadable_sidecar_never_means_missing(library,monkeypatch):
    track=library.list_tracks()[0];folder=library.root/track['file_sha256'];path=folder/'analysis.json'
    assert read_analysis(folder,track) is None
    path.symlink_to(folder/'missing-result')
    with pytest.raises(MusicError):read_analysis(folder,track)
    path.unlink();write_json(path,done(track))
    read=Path.read_text
    def denied(self,*args,**kwargs):
        if self==path:raise PermissionError('unreadable result')
        return read(self,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',denied)
    with pytest.raises(MusicError):read_analysis(folder,track)


def test_queue_reports_position_ahead_and_continues_after_crash(library,tmp_path):
    first=library.list_tracks()[0]
    for i in (2,3):
        audio=tmp_path/f'synthetic-{i}.wav';audio.write_bytes(f'synthetic-{i}'.encode());library.import_local(audio)
    tracks=library.list_tracks();calls=[]
    def worker(track,folder,part):
        calls.append(track['file_sha256'])
        if track==first:raise RuntimeError('synthetic failure')
        data=done(track);return {p:data[p] for p in ('beat','tags')}
    queue=AnalysisQueue(library,worker=worker)
    for track in tracks:queue.enqueue(track['file_sha256'],'all')
    assert [queue.state(t['file_sha256'])['beat']['queue_position'] for t in tracks]==[0,1,2]
    queue.start();assert queue.wait_idle(10);assert len(calls)==3
    assert read_analysis(library.root/tracks[2]['file_sha256'],tracks[2])['beat']['status']=='done'
    queue.close()
