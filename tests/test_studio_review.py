"""R220 derived-media and review contracts; no platform network."""
import json
import threading
import http.client
from pathlib import Path
from http.server import ThreadingHTTPServer

import pytest

from studio.project_store import ProjectStore, ProjectStoreError
from studio.media_review import MediaReview, waveform, read_json
from studio.server import StudioApplication


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


@pytest.fixture
def review(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path / 'media'))
    root = tmp_path / 'media/projects/trip/work'; root.mkdir(parents=True)
    put(root.parent / 'project-manifest.json', {'title': '旅程'})
    put(root / 'ai-analysis/media-manifest.json', {'items': [{'type':'video'}, {'type':'image'}]})
    rows = [dict(id=f'S{i}', kind='photo' if i==2 else 'video', scene='travel',
                 source_relative_path=f'travel/clip_{i}.mp4', start_sec=0, end_sec=3, duration_sec=3,
                 frames=[f'ai-analysis/shots/frames/S{i}.jpg'], status=status, model_decision=decision,
                 rejection_reasons=['too_short'] if i==3 else [], model_reason='画面清楚')
            for i, status, decision in [(1,'selected','精选'),(2,'usable','可用'),(3,'rejected',None),(4,'usable',None)]]
    put(root / 'ai-analysis/shots/shots.json', {'shots': rows, 'run_status':'failed', 'hook_candidates':[{'id':'S1'}]})
    for row in rows:
        f=root/row['frames'][0]; f.parent.mkdir(exist_ok=True); f.write_bytes(b'jpeg')
    p=root/'ai-analysis/shots/previews/S1.mp4'; p.parent.mkdir(); p.write_bytes(b'0123456789')
    store=ProjectStore(tmp_path/'state'); project=store.create_project(title='作品',local_workspace=str(root))
    return MediaReview(store), project['id'], root


def test_grouping_and_counts(review):
    service, identity, root=review
    result=service.catalog(); assert result['groups'][0]['title']=='旅程'
    piece=result['pieces'][0]; assert (piece['videos'],piece['photos'])==(1,1)
    (root.parent/'project-manifest.json').unlink()
    assert service.catalog()['groups'][0]['title']=='其他作品'
    put(root.parent/'project-manifest.json', {'no_title': True})
    with pytest.raises(ProjectStoreError): service.catalog()


def test_manifest_display_name_date_and_version_order(review):
    service, identity, root = review
    put(root / 'project-manifest.json', {'title': '20260514_校园_奔赴与运动会'})
    for version in ['v10', 'v2', 'v1']:
        path = root / 'output' / version / '成片.mp4'
        path.parent.mkdir(parents=True); path.write_bytes(b'preview')
    piece = service.piece(service.store.get_project(identity))
    assert piece['title'] == '校园 · 奔赴与运动会'
    assert piece['date'] == '2026/5/14'
    assert [o['version'] for o in piece['outputs']] == ['v1', 'v2', 'v10']
    evidence = json.loads((root / 'ai-analysis/shots/shots.json').read_text())
    evidence['hook_candidates'] = []
    put(root / 'ai-analysis/shots/shots.json', evidence)
    assert service.piece(service.store.get_project(identity))['cover'].endswith(piece['outputs'][-1]['id'])
    assert service.catalog()['groups'][-1]['title'] == '旅程'


def test_partial_result_is_not_workbench_review(review):
    service, identity, _ = review
    assert not service.catalog()['pieces'][0]['pending']


def test_output_poster_rebuild_seeks_one_third(review, monkeypatch):
    from types import SimpleNamespace
    from studio.media_review import digest
    service, identity, root = review
    output = root / 'output/v1/preview.mp4'
    output.parent.mkdir(parents=True); output.write_bytes(b'video')
    poster = root / 'ai-analysis/output-posters' / (digest(output.relative_to(root).as_posix())[:24] + '.jpg')
    poster.parent.mkdir(); poster.write_bytes(b'old')
    put(root / 'ai-analysis/media-manifest.json', {'items': []})
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[0] == 'ffprobe':
            return SimpleNamespace(stdout='12.0\n')
        Path(args[-1]).write_bytes(b'new')
        return SimpleNamespace()
    monkeypatch.setattr('studio.media_review.subprocess.run', run)
    service.prepare_posters()
    assert calls == [] and poster.read_bytes() == b'old'
    service.prepare_posters(rebuild=True)
    ffmpeg = next(c for c in calls if c[0] == 'ffmpeg')
    assert float(ffmpeg[ffmpeg.index('-ss') + 1]) == 4.0
    assert poster.read_bytes() == b'new'


def test_merge_cas_confirmation_and_invalidation(review):
    service, identity, root=review
    value=service.shots(identity); assert value['counts']==dict(selected=1,usable=1,unused=0,rejected=1)
    assert value['duration']==3
    with pytest.raises(ProjectStoreError): service.decide(identity, dict(expectedVersion=0,shotId='S3',status='selected'))
    # A partial result cannot be confirmed.
    with pytest.raises(ProjectStoreError): service.decide(identity, dict(expectedVersion=0,confirm=True))
    doc=json.loads((root/'ai-analysis/shots/shots.json').read_text()); doc['run_status']='complete'; put(root/'ai-analysis/shots/shots.json', doc)
    confirmed=service.decide(identity, dict(expectedVersion=0,confirm=True)); assert confirmed['confirmed']
    with pytest.raises(ProjectStoreError): service.decide(identity, dict(expectedVersion=0,shotId='S1',status='unused'))
    changed=service.decide(identity, dict(expectedVersion=1,shotId='S1',status='unused'))
    assert not changed['confirmed']; assert changed['counts']['selected']==0
    assert json.loads((root/'ai-analysis/shots/shots.json').read_text())==doc


def test_unreadable_is_not_empty(tmp_path):
    assert read_json(tmp_path/'absent', optional=True) is None
    f=tmp_path/'bad'; f.write_text('{')
    with pytest.raises(ProjectStoreError): read_json(f, optional=True)


def test_waveform_rms():
    import numpy as np
    result=waveform(np.array([0.,0.,1.,1.]), segments=2)
    assert result==[0,1]
    assert waveform(np.zeros(4), segments=2)==[0,0]
    assert len(waveform(np.ones(200)))==180


def test_id_only_media_range_and_origin(review):
    service, identity, root=review
    app=StudioApplication(service.store); app.media_review=service
    server=ThreadingHTTPServer(('127.0.0.1',0), app.handler())
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    def request(path,headers=None):
        conn=http.client.HTTPConnection(*server.server_address); conn.request('GET',path,headers=headers or {})
        res=conn.getresponse(); data=res.read(); result=(res.status,dict(res.getheaders()),data); conn.close(); return result
    try:
        path=f'/api/review/pieces/{identity}/media/shot/S1'
        status, headers, data=request(path,{'Range':'bytes=2-5'}); assert status==206; assert data==b'2345'
        assert headers['Content-Range']=='bytes 2-5/10'; assert "media-src 'self'" in headers['Content-Security-Policy']
        assert request(path,{'Range':'bytes=-2'})[2]==b'89'
        assert request(path,{'Range':'bytes=99-'})[0]==416
        assert request(path,{'Host':'evil.example'})[0]==403
        for tail in ['unknown','%2e%2e','%2e%2e%2fS1','S1?path=raw.mp4']:
            assert request(f'/api/review/pieces/{identity}/media/shot/{tail}')[0]==404
        assert request(f'/api/review/pieces/{identity}/media/raw/S1')[0]==404
        (root/'ai-analysis/shots/previews/S1.mp4').unlink(); (root/'raw.mp4').write_bytes(b'private')
        (root/'ai-analysis/shots/previews/S1.mp4').symlink_to(root/'raw.mp4')
        assert request(path)[0]==404
    finally:
        server.shutdown();server.server_close();thread.join()


def test_jobs_stop_resume_and_exclusion(review):
    from studio.review_jobs import ReviewJobs
    service, identity, root=review
    calls=[]
    class Process:
        def __init__(self): self.done=threading.Event();self.code=None
        def poll(self): return self.code
        def wait(self,timeout=None): self.done.wait(timeout);return self.code
        def terminate(self): self.code=-15;self.done.set()
        def kill(self): self.terminate()
    def spawn(args,**kwargs): calls.append(args);return Process()
    jobs=ReviewJobs(service,spawn=spawn)
    try:
        assert jobs.shots(identity,'resume')['status']=='running'
        assert '--resume' in calls[0]
        with pytest.raises(ProjectStoreError): jobs.shots(identity,'start')
        jobs.shots(identity,'stop')
    finally: jobs.close()
    assert json.loads((root/'ai-analysis/shots/progress.json').read_text())['status']=='stopped'


@pytest.mark.parametrize('outcome,expected', [('duplicate','duplicate'),('member','member'),('douyin','error'),('error','error')])
def test_import_outcomes_are_library_owned_and_offline(review,outcome,expected):
    from studio.review_jobs import ReviewJobs
    from music_library.errors import MemberRequired, MusicError, DOUYIN_IMPORT_FAILURE_MESSAGE
    service, identity, root=review
    def fake(text,**kwargs):
        if outcome=='member': raise MemberRequired('测试歌','测试歌手')
        if outcome in ('error','douyin'): raise MusicError('测试失败')
        return '已在库里', {'file_sha256':'a'*64,'title':'测试歌'}
    service.music.import_link=fake
    service.prepare_peaks=lambda: None
    jobs=ReviewJobs(service)
    result=jobs.import_music({'text':'https://v.douyin.com/test/' if outcome=='douyin' else 'https://music.163.com/song?id=123'})
    jobs.close()
    status=jobs.import_status(result['id'])
    assert status['state']==expected
    if outcome=='douyin': assert status['reason']==DOUYIN_IMPORT_FAILURE_MESSAGE


def test_music_unreadable_does_not_report_logged_out(review,monkeypatch):
    import studio.review_jobs as module
    from music_library.errors import MusicError
    service,_,_=review
    def broken(): raise MusicError('无法读取')
    monkeypatch.setattr(module,'read_session',broken)
    result=module.ReviewJobs(service).music_settings()
    assert result['account']=={'state':'unreadable','reason':'无法读取'}


def test_ai_final_quality_demotions_are_not_undone(review):
    service,identity,root=review
    f=root/'ai-analysis/shots/shots.json';doc=json.loads(f.read_text())
    doc['shots'][0].update(status='usable',model_decision='精选',visual_flags={'has_watermark':True})
    put(f,doc)
    value=service.shots(identity)
    assert value['counts']['selected']==0
    assert value['counts']['usable']==2


def test_corrupt_decisions_are_reported_as_unreadable(review):
    service,identity,root=review
    put(root/'ai-analysis/shots/decisions.json',{'version':1,'shots':{'S1':None},'confirmation':None})
    with pytest.raises(ProjectStoreError,match='review_unreadable'):
        service.shots(identity)


def test_same_workspace_cannot_run_twice_through_two_piece_ids(review):
    from studio.review_jobs import ReviewJobs
    service,identity,root=review
    alias=service.store.create_project(title='同一作品的别名',local_workspace=str(root))['id']
    class Process:
        def __init__(self): self.done=threading.Event();self.code=None
        def poll(self): return self.code
        def wait(self,timeout=None): self.done.wait(timeout);return self.code
        def terminate(self): self.code=-15;self.done.set()
        def kill(self): self.terminate()
    jobs=ReviewJobs(service,spawn=lambda *a,**k:Process())
    try:
        jobs.shots(identity,'start')
        with pytest.raises(ProjectStoreError,match='revision_conflict'):
            jobs.shots(alias,'start')
    finally: jobs.close()
