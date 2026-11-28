"""Owned background work, dependency waiting, cancellation and transcription."""
import copy
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from tests.test_r226_api import setup,arrange,body,check,put,FIXTURE,fake_generated
from studio.roughcut.application import RoughcutService
from studio.roughcut.store import RoughcutError


class Unavailable(Exception):
    def __init__(self,code):self.code=code;self.track_id='song-a';self.failure_code='worker_error' if code=='beat_failed' else None


def draft_request(state,choice_revision=1):
    return dict(expectedRevision=state['revision'],projectRevision=state['project_revision'],editorChoiceRevision=choice_revision,edlDigest=state['plan_input_binding']['edl_digest'])


def test_preview_is_published_and_invalidated_at_command_acceptance(setup):
    service,app,identity,root=setup
    state=arrange(service,identity)
    assert state['playback']['status']=='ready'
    asset=state['playback']['preview_artifact_id']
    assert service.media(identity,asset,'bytes=0-8').length==9
    pending=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.code=='roughcut_inputs_stale' and exc.value.http_status==409
    service.jobs.run(pending['job_id'])
    assert service.state(identity)['playback']['preview_artifact_id']!=asset
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.http_status==409


def test_default_preview_delegates_to_b3_entry_without_editor_fallback(setup,monkeypatch):
    from studio.roughcut.application import drafts as roughcut_drafts
    service,app,identity,root=setup
    calls=[]
    def generate_preview(**kwargs):
        calls.append(kwargs)
        assert 'editor_choice' not in kwargs
        return fake_generated(**kwargs)
    monkeypatch.setattr(roughcut_drafts,'generate_preview',generate_preview,raising=False)
    service.preview_renderer=None
    state=arrange(service,identity)
    assert state['playback']['status']=='ready' and len(calls)==1
    assert sum(s['kind']=='photo' for s in calls[0]['planner_inputs']['shots'])==2


@pytest.mark.parametrize('command',[
    dict(type='set_technique',id='jcut',enabled=False),
    dict(type='apply_preset',preset_id='race',preset_revision=1),
    dict(type='select_music',track_ids=['song-b']),
])
def test_default_preview_entry_rerenders_changes_without_generating_draft(setup,monkeypatch,command):
    """Run the preview compiler/indexer with a synthetic renderer/probe boundary."""
    from studio.roughcut.application import drafts as roughcut_drafts
    service,app,identity,root=setup
    service.preview_renderer=None
    renders=[]
    def build_plan(edl,*,project,output,width,height):
        return dict(output=str(output),duration=roughcut_drafts.parse_time_range(edl['clips'][-1]['time_range'])[1])
    def execute_plan(plan):
        renders.append(plan)
        Path(plan['output']).write_bytes(b'synthetic-preview-video')
    def probe(command,**kwargs):
        assert command[0]=='ffprobe'
        return SimpleNamespace(stdout=json.dumps(dict(format=dict(duration=renders[-1]['duration']),streams=[dict(codec_type='video')])))
    monkeypatch.setattr(roughcut_drafts,'build_plan',build_plan)
    monkeypatch.setattr(roughcut_drafts,'execute_plan',execute_plan)
    monkeypatch.setattr(roughcut_drafts,'_run',lambda command:Path(command[-1]).write_bytes(b'synthetic-photo-proxy'))
    monkeypatch.setattr(roughcut_drafts.subprocess,'run',probe)
    state=arrange(service,identity)
    assert state['playback']['status']=='ready'
    assert state['draft']['status']=='none' and len(renders)==1
    asset=state['playback']['preview_artifact_id']
    assert service.media(identity,asset,'bytes=0-8').length==9
    accepted=service.command(identity,body(service,identity,command))
    assert service.state(identity)['playback']['status']=='unavailable'
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.http_status==409
    service.jobs.run(accepted['job_id'])
    assert service.job(accepted['job_id'])['status']=='done'
    state=service.state(identity)
    assert state['playback']['status']=='ready' and len(renders)==2
    assert state['playback']['preview_artifact_id']!=asset
    assert state['draft']['status']=='none'
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.http_status==409
    receipts=list((root/'draft-project/roughcut').glob('*/*/receipt.json'))
    assert len(receipts)==2
    for path in receipts:
        receipt=json.loads(path.read_text())
        assert receipt['schema_version']=='roughcut_preview_receipt_v1' and receipt['status']=='done'
        assert [a['kind'] for a in receipt['artifacts']]==['preview']
        assert not (path.parent/'kdenlive').exists()
        assert not list(path.parent.glob('*.srt'))


def test_missing_preview_entry_fails_without_publishing_fake_video(setup,monkeypatch):
    from studio.roughcut.application import drafts as roughcut_drafts
    service,app,identity,root=setup
    monkeypatch.delattr(roughcut_drafts,'generate_preview',raising=False)
    service.preview_renderer=None
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    service.jobs.run(accepted['job_id'])
    state=service.state(identity)
    assert service.job(accepted['job_id'])['failure']['code']=='preview_failed'
    assert state['plan']['metrics']['shot_count']==27 and state['playback']['status']=='unavailable'
    assert state['playback']['failure']['code']=='preview_failed'
    assert service.job(accepted['job_id'])['progress']['determinate'] is False


def test_wrong_preview_duration_is_not_published(setup):
    service,app,identity,root=setup
    def wrong(**kwargs):
        result=fake_generated(**kwargs);result['duration_sec']+=5;return result
    service.preview_renderer=wrong
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    service.jobs.run(accepted['job_id'])
    assert service.job(accepted['job_id'])['failure']['code']=='preview_failed'
    assert service.state(identity)['playback']['status']=='unavailable'
    assert service.state(identity)['plan']['metrics']['shot_count']==27


@pytest.mark.parametrize('method,design',[('external','cut-drafted'),('guide','cut-drafted-guide')])
def test_draft_states_saved_choice_and_stale_after_rearrangement(setup,method,design):
    service,app,identity,root=setup
    app.video_editor_choice(identity,dict(editor='otio_kdenlive',method=method,revision=1))
    state=arrange(service,identity)
    accepted=service.draft(identity,draft_request(state,2));check('draft_response',accepted)
    assert service.state(identity)['draft']['design_state']=='cut-drafting'
    service.jobs.run(accepted['job_id'])
    state=service.state(identity);check('state_response',state)
    assert state['draft']['design_state']==design
    assert state['draft']['plan_revision']==state['plan_revision']
    assert state['draft']['editor_choice_revision']==2
    note=service.media(identity,state['draft']['guide_artifact_id'])
    assert note.content_type=='text/plain; charset=utf-8' and note.headers['Content-Disposition']=='inline'
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    assert service.state(identity)['draft']['design_state']=='cut-draft-stale'
    service.jobs.run(accepted['job_id'])
    assert service.state(identity)['draft']['design_state']=='cut-draft-stale'


def test_draft_failure_keeps_ready_plan_and_preview(setup):
    service,app,identity,root=setup
    state=arrange(service,identity)
    def fail(**kwargs):raise RoughcutError('draft_failed')
    service.draft_generator=fail
    accepted=service.draft(identity,draft_request(state));service.jobs.run(accepted['job_id'])
    result=service.state(identity)
    assert result['status']=='ready' and result['plan_revision']==state['plan_revision']
    assert result['draft']['status']=='failed' and result['draft']['design_state'] is None
    assert result['draft']['failure']['code']=='draft_failed'
    assert result['draft']['failure']['retryable'] is True
    assert result['display']['draft_allowed'] is True
    assert result['playback']==state['playback']


def test_guide_with_placeholder_subtitle_file_is_not_published(setup):
    service,app,identity,root=setup
    app.video_editor_choice(identity,dict(editor='otio_kdenlive',method='guide',revision=1))
    state=arrange(service,identity)
    def placeholder(**kwargs):
        value=fake_generated(**kwargs)
        from pathlib import Path
        (Path(value['directory'])/'captions.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nS123\n')
        return value
    service.draft_generator=placeholder
    accepted=service.draft(identity,draft_request(state,2));service.jobs.run(accepted['job_id'])
    result=service.state(identity)
    assert result['draft']['status']=='failed'
    assert result['draft']['guide_artifact_id'] is None
    assert service.job(accepted['job_id'])['failure']['code']=='draft_failed'


@pytest.mark.parametrize('field',['expectedRevision','projectRevision','editorChoiceRevision','edlDigest'])
def test_draft_preflight_cas_and_input_digest(setup,field):
    service,app,identity,root=setup
    state=arrange(service,identity);request=draft_request(state)
    request[field]='a'*64 if field=='edlDigest' else 999
    with pytest.raises(RoughcutError) as exc:service.draft(identity,request)
    assert exc.value.code in ('revision_conflict','roughcut_inputs_stale')
    assert service.state(identity)['revision']==state['revision']
    with pytest.raises(RoughcutError):service.draft(identity,{**draft_request(state),'editor':'chatcut','path':'/client/project'})


@pytest.mark.parametrize('editor,method',[('chatcut','external'),('openchatcut','external'),('openfilm','self')])
def test_draft_unsupported_never_calls_another_generator(setup,editor,method):
    service,app,identity,root=setup
    app.video_editor_choice(identity,dict(editor=editor,method=method,revision=1))
    state=arrange(service,identity)
    service.draft_generator=lambda **k:pytest.fail('unsupported editor invoked generator')
    with pytest.raises(RoughcutError) as exc:service.draft(identity,draft_request(state,2))
    assert exc.value.code in ('draft_backend_unsupported','editor_not_ready')


@pytest.mark.parametrize('change',['stop','selection','choice'])
def test_late_draft_result_cannot_publish_after_stop_or_change(setup,change):
    service,app,identity,root=setup
    state=arrange(service,identity)
    entered=threading.Event();release=threading.Event()
    def generate(**kwargs):
        entered.set();assert release.wait(10);return fake_generated(**kwargs)
    service.draft_generator=generate
    accepted=service.draft(identity,draft_request(state))
    worker=threading.Thread(target=service.jobs.run,args=(accepted['job_id'],));worker.start();assert entered.wait(5)
    if change=='stop':service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    elif change=='selection':service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    else:app.video_editor_choice(identity,dict(editor='otio_kdenlive',method='guide',revision=1))
    release.set();worker.join(15);assert not worker.is_alive()
    assert service.state(identity)['draft']['status']!='ready'
    assert service.job(accepted['job_id'])['status'] in ('stopped','failed')


def test_open_draft_uses_only_current_owned_project(setup):
    service,app,identity,root=setup
    state=arrange(service,identity)
    accepted=service.draft(identity,draft_request(state));service.jobs.run(accepted['job_id'])
    state=service.state(identity);calls=[]
    def opened(**kwargs):calls.append(kwargs['project_dir']);return dict(editor_backend='otio_kdenlive',opened=True,local_only=True)
    service.editor_opener=opened
    request=dict(expectedRevision=state['revision'],projectRevision=state['project_revision'],editorChoiceRevision=1,edlDigest=state['draft']['edl_digest'])
    value=service.open_draft(identity,request);check('open_draft_response',value)
    assert len(calls)==1 and calls[0].is_relative_to(root/'draft-project/roughcut')
    assert (calls[0]/'timeline.kdenlive').is_file()
    with pytest.raises(RoughcutError):service.open_draft(identity,{**request,'path':'/not-owned/timeline.kdenlive'})
    assert len(calls)==1
    service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    request['expectedRevision']+=1
    with pytest.raises(RoughcutError) as exc:service.open_draft(identity,request)
    assert exc.value.http_status==409 and len(calls)==1


def test_music_and_beat_changes_expire_preview(setup):
    service,app,identity,root=setup
    state=arrange(service,identity);asset=state['playback']['preview_artifact_id']
    source=root/'music/song-a.wav';source.write_bytes(b'changed-audio')
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.http_status==409
    assert service.state(identity)['playback']['status']=='unavailable'
    state=arrange(service,identity);asset=state['playback']['preview_artifact_id']
    original=service.beat_loader
    def newer(*a,**k):
        beat=original(*a,**k);beat['registry_version']+=1;return beat
    service.beat_loader=newer
    with pytest.raises(RoughcutError) as exc:service.media(identity,asset)
    assert exc.value.http_status==409


@pytest.mark.parametrize('code,state',[('queued','cut-beat-queued'),('analyzing','cut-beat-analyzing')])
def test_waiting_beat_has_no_fake_progress_and_resumes(setup,code,state):
    service,app,identity,root=setup
    ready=threading.Event();waiting=threading.Event()
    def load(track_id,*,media_root=None):
        if not ready.is_set():waiting.set();raise Unavailable(code)
        return copy.deepcopy(FIXTURE['beat_maps'][track_id])
    service.beat_loader=load
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    worker=threading.Thread(target=service.jobs.run,args=(accepted['job_id'],));worker.start()
    assert waiting.wait(2)
    deadline=time.monotonic()+2
    while service.state(identity)['display']['base_state']!=state and time.monotonic()<deadline:time.sleep(.01)
    value=service.job(accepted['job_id']);check('job_response',value)
    assert value['progress']['determinate'] is False and value['progress']['total'] is None
    assert service.state(identity)['display']['base_state']==state
    ready.set();worker.join(5);assert not worker.is_alive()
    assert service.job(accepted['job_id'])['status']=='done'


@pytest.mark.parametrize('code,state,status',[('beat_failed','cut-failed',422),('result_unreadable','cut-failed-unreadable',503),('unknown_track','cut-failed-missing',422)])
def test_beat_failures_preserve_source_codes(setup,code,state,status):
    service,app,identity,root=setup
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable(code))
    request=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    with pytest.raises(RoughcutError) as exc:service.command(identity,request)
    assert exc.value.code==code and exc.value.http_status==status
    assert exc.value.failure['design_state']==state
    assert service.state(identity)['selection']['playlist']==[]


@pytest.mark.parametrize('refresh_revision',[False,True])
def test_repeated_inflight_command_reuses_one_job(setup,refresh_revision):
    service,app,identity,root=setup
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('queued'))
    request=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    accepted=service.command(identity,request)
    if refresh_revision:request['expectedRevision']=accepted['revision']
    again=service.command(identity,request)
    assert again==accepted
    assert len(list((service.store.root/'roughcut/jobs').glob('*.json')))==1
    assert service.state(identity)['revision']==accepted['revision']


def test_concurrent_retries_do_not_start_duplicate_jobs(setup):
    from concurrent.futures import ThreadPoolExecutor
    service,app,identity,root=setup
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('analyzing'))
    request=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:service.command(identity,copy.deepcopy(request)),range(4)))
    assert all(result==results[0] for result in results)
    assert len(list((service.store.root/'roughcut/jobs').glob('*.json')))==1


def test_retries_still_check_sources_and_cas(setup):
    service,app,identity,root=setup
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('queued'))
    request=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    accepted=service.command(identity,request)
    with pytest.raises(RoughcutError) as exc:
        service.command(identity,{**request,'expectedRevision':accepted['revision']+1})
    assert exc.value.code=='revision_conflict'
    doc=json.loads((root/'ai-analysis/shots/shots.json').read_text())
    doc['shots'][0]['end_sec']+=1;put(root/'ai-analysis/shots/shots.json',doc)
    with pytest.raises(RoughcutError) as exc:service.command(identity,request)
    assert exc.value.code in ('selection_not_confirmed','roughcut_inputs_stale')
    assert len(list((service.store.root/'roughcut/jobs').glob('*.json')))==1


def test_reanalysis_retry_after_failed_job_creates_one_new_job(setup):
    service,app,identity,root=setup
    request=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    first=service.command(identity,request)
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('beat_failed'))
    service.jobs.run(first['job_id'])
    assert service.job(first['job_id'])['status']=='failed'
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('queued'))
    request['expectedRevision']=first['revision']
    second=service.command(identity,request)
    assert second['job_id']!=first['job_id'] and second['revision']==first['revision']+1
    assert service.command(identity,request)==second


def test_stop_interrupts_beat_wait_and_does_not_cancel_shared_analysis(setup):
    service,app,identity,root=setup
    service.poll_interval=30
    waiting=threading.Event();calls=[]
    def load(*a,**k):
        calls.append(a[0]);waiting.set();raise Unavailable('analyzing')
    service.beat_loader=load
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    waiting.clear()
    worker=threading.Thread(target=service.jobs.run,args=(accepted['job_id'],));worker.start()
    assert waiting.wait(3)
    service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    worker.join(5);assert not worker.is_alive()
    assert service.job(accepted['job_id'])['status']=='stopped'
    assert calls==['song-a','song-a']


def test_pending_beats_back_off_and_timeout_at_thirty_minutes(setup,monkeypatch):
    import studio.roughcut.application as module
    service,app,identity,root=setup
    service.poll_interval=.5
    now=[0.];delays=[]
    monkeypatch.setattr(module.time,'monotonic',lambda:now[0])
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('queued'))
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    class ClockEvent:
        def is_set(self):return False
        def wait(self,seconds):delays.append(seconds);now[0]+=seconds;return False
    service._run_job(accepted['job_id'],ClockEvent())
    job=service.job(accepted['job_id'])
    assert job['status']=='failed' and job['failure']['code']=='beat_failed'
    assert job['failure']['details']['upstream_failure_code']=='analysis_timeout'
    assert now[0]==1800 and delays[:4]==[.5,1,2,4] and max(delays)==30
    assert service.state(identity)['plan'] is None


@pytest.mark.parametrize('code',['beat_failed','result_unreadable','unknown_track'])
def test_pending_beats_end_with_original_failure_code(setup,code):
    service,app,identity,root=setup
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable('queued'))
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    service.beat_loader=lambda *a,**k:(_ for _ in ()).throw(Unavailable(code))
    service.jobs.run(accepted['job_id'])
    failure=service.job(accepted['job_id'])['failure']
    assert failure['code']==code
    if code=='beat_failed':assert failure['details']['upstream_failure_code']=='worker_error'


def test_missing_reader_is_not_missing_song(setup,monkeypatch):
    service,app,identity,root=setup
    import studio.roughcut.application as module
    def missing(name,*args,**kwargs):raise ImportError('not merged')
    monkeypatch.setattr(module.importlib,'import_module',missing)
    service.beat_loader=None
    with pytest.raises(RoughcutError) as exc:service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    assert exc.value.code=='beat_analysis_unavailable'
    assert exc.value.failure['message']=='拍子分析还不能用'


def test_stop_is_idempotent_and_late_result_cannot_publish(setup):
    service,app,identity,root=setup
    old=arrange(service,identity)
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    stopped=service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    again=service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    assert stopped==again
    service.jobs.run(accepted['job_id'])
    value=service.state(identity)
    assert value['plan']==old['plan'] and value['plan_revision']==old['plan_revision']
    assert service.job(accepted['job_id'])['status']=='stopped'


def test_superseded_job_cannot_overwrite_newer_result(setup):
    service,app,identity,root=setup
    a=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    b=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    service.jobs.run(b['job_id']);service.jobs.run(a['job_id'])
    value=service.state(identity)
    assert value['plan_revision']==b['revision']
    assert not next(t for t in value['plan']['techniques'] if t['id']=='jcut')['enabled']
    assert service.job(a['job_id'])['status']=='stopped'


def test_inputs_changed_while_running_prevent_publish(setup):
    service,app,identity,root=setup
    accepted=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    doc=json.loads((root/'ai-analysis/shots/shots.json').read_text());doc['shots'][0]['end_sec']+=.5;put(root/'ai-analysis/shots/shots.json',doc)
    service.jobs.run(accepted['job_id'])
    assert service.job(accepted['job_id'])['status'] in ('stopped','failed')
    assert service.state(identity)['plan'] is None


def test_no_cross_piece_job_or_stopping_other_piece(setup):
    service,app,identity,root=setup
    other=app.store.create_project(title='另一件',local_workspace=str(root))['id']
    a=service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    b=service.command(other,body(service,other,dict(type='select_music',track_ids=['song-b'])))
    service.stop(a['job_id'],dict(action='stop',expectedRevision=a['revision']))
    service.jobs.run(b['job_id'])
    assert service.state(other)['plan_revision']==b['revision']
    assert service.state(identity)['plan'] is None


def test_transcription_dedupes_media_and_only_explicit_post(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    missing=value['warnings']['missing_word_shot_ids'];calls=[]
    class Local:
        def run(self,context,media_ids,cancelled):
            from pipeline.transcribe_audio import transcript_document
            calls.append(list(media_ids))
            for mid in media_ids:
                document=transcript_document(media_id=mid,audio_ref=f'ai-analysis/audio/{mid}.wav',provider='funasr',model='synthetic',language='zh',segments=[dict(start_sec=0,end_sec=100,text='甲乙',words=[dict(start=2,end=3,text='甲'),dict(start=4,end=5,text='乙')])])
                put(root/'ai-analysis/transcripts'/f'{mid}.transcript.json',document)
    service.transcriber=Local()
    service.state(identity);service.presets();assert calls==[]
    accepted=service.transcribe(identity,dict(expectedRevision=value['revision'],selectionDigest=value['source_summary']['selection_digest'],shot_ids=missing));check('transcription_response',accepted)
    service.jobs.run(accepted['job_id'])
    result=service.job(accepted['job_id']);check('job_response',result)
    assert result['status']=='done' and len(calls)==1
    assert len(calls[0])==len(set(accepted['media_ids']))
    follow=result['result']['transcription']['rearrange_job_id'];assert follow
    service.jobs.run(follow)
    assert service.state(identity)['warnings']['missing_word_count']==0


def test_photo_transcription_and_corrupt_job_are_rejected(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    photo=next(c['shot_id'] for c in value['plan']['clips'] if c['kind']=='photo')
    with pytest.raises(RoughcutError) as exc:service.transcribe(identity,dict(expectedRevision=value['revision'],selectionDigest=value['source_summary']['selection_digest'],shot_ids=[photo]))
    assert exc.value.code=='transcript_selection_invalid'
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='bed',enabled=False)))
    service.store.job_path(accepted['job_id']).write_text('null')
    with pytest.raises(RoughcutError) as exc:service.job(accepted['job_id'])
    assert exc.value.code=='roughcut_job_unreadable'


def test_stop_during_computation_rejects_late_publication(setup):
    service,app,identity,root=setup
    old=arrange(service,identity)
    entered=threading.Event();release=threading.Event();original=service.planner
    def blocked(**kwargs):
        entered.set();assert release.wait(5)
        return original(**kwargs)
    service.planner=blocked
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    worker=threading.Thread(target=service.jobs.run,args=(accepted['job_id'],));worker.start();assert entered.wait(3)
    stopped=service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    assert stopped['status']=='stopping'
    release.set();worker.join(5);assert not worker.is_alive()
    assert service.job(accepted['job_id'])['status']=='stopped'
    assert service.state(identity)['plan']==old['plan']


def test_local_transcriber_uses_existing_funasr_builder_and_preserves_cancel(setup):
    from studio.roughcut.transcription import LocalTranscriber
    from pathlib import Path
    service,app,identity,root=setup
    context=service._context(identity,transcripts=True)
    mid=next(s['media_id'] for s in context['shots'] if s['scene']=='selfie-moments')
    calls=[]
    class Provider:
        name='funasr';model='synthetic-local'
        def transcribe(self,audio_path,*,language=None):
            calls.append(('transcribe',audio_path,language))
            return dict(language='zh',segments=[dict(start_sec=0,end_sec=3,text='甲乙',words=[dict(start=.1,end=.5,text='甲'),dict(start=1.2,end=1.5,text='乙')])])
    def extract(args,**kwargs):
        assert args[0]=='ffmpeg' and str(context['sources_by_media'][mid]) in args
        Path(args[-1]).write_bytes(b'synthetic-wav')
    worker=LocalTranscriber(provider_factory=Provider,run=extract)
    worker.run(context,[mid],lambda:False)
    document=json.loads(context['transcript_paths'][mid].read_text())
    assert document['precision']=='word' and document['auto_cut_allowed'] is True
    assert len(document['words'])==2 and document['provider']=='funasr'
    old=context['transcript_paths'][mid].read_bytes()
    worker.run(context,[mid],lambda:True)
    assert len(calls)==1 and context['transcript_paths'][mid].read_bytes()==old


def test_chunk_transcription_remains_missing_and_provider_failure_is_explicit(setup):
    from pipeline.transcribe_audio import transcript_document
    service,app,identity,root=setup
    value=arrange(service,identity)
    class Chunk:
        def run(self,context,media_ids,cancelled):
            for mid in media_ids:
                put(context['transcript_paths'][mid],transcript_document(media_id=mid,audio_ref=f'ai-analysis/audio/{mid}.wav',provider='funasr',model='synthetic',language='zh',segments=[dict(start_sec=0,end_sec=10,text='甲乙',precision='chunk')]))
    service.transcriber=Chunk()
    accepted=service.transcribe(identity,dict(expectedRevision=value['revision'],selectionDigest=value['source_summary']['selection_digest'],shot_ids=value['warnings']['missing_word_shot_ids']))
    service.jobs.run(accepted['job_id']);result=service.job(accepted['job_id'])
    assert result['result']['transcription']['word_ready_shot_ids']==[]
    service.jobs.run(result['result']['transcription']['rearrange_job_id'])
    value=service.state(identity)
    assert value['warnings']['missing_word_count']==6
    assert not any(o['technique']=='duck' for o in value['plan']['occurrences'])
    class Broken:
        def run(self,*args):raise RoughcutError('transcript_failed')
    service.transcriber=Broken()
    accepted=service.transcribe(identity,dict(expectedRevision=value['revision'],selectionDigest=value['source_summary']['selection_digest'],shot_ids=value['warnings']['missing_word_shot_ids']))
    service.jobs.run(accepted['job_id'])
    assert service.job(accepted['job_id'])['failure']['code']=='transcript_failed'
    assert not any(n['code']=='rearrange_failed' for n in service.state(identity)['display']['notices'])


def test_stop_write_failure_does_not_cancel_an_uncommitted_stop(setup,monkeypatch):
    service,app,identity,root=setup
    arrange(service,identity)
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    with monkeypatch.context() as patch:
        patch.setattr(service.store,'write_state',lambda *a:(_ for _ in ()).throw(RoughcutError('roughcut_state_unreadable')))
        with pytest.raises(RoughcutError):service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    assert service.state(identity)['revision']==accepted['revision']
    assert service.job(accepted['job_id'])['status']=='queued'
    service.jobs.run(accepted['job_id'])
    result=service.job(accepted['job_id'])
    assert result['status']=='done',result
    assert service.state(identity)['plan_revision']==accepted['revision']


def test_failed_stop_and_waiting_worker_are_serialized(setup,monkeypatch):
    service,app,identity,root=setup
    arrange(service,identity)
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    original=service.store.write_state
    worker=None;entered=threading.Event()
    read_job=service.store.read_job
    def observe_stop(job_id):
        result=read_job(job_id)
        if threading.current_thread() is worker and result['public']['status']=='stopped':
            entered.set()
        return result
    monkeypatch.setattr(service.store,'read_job',observe_stop)
    def fail_stop(piece,record):
        nonlocal worker
        if record['status']=='stopped':
            def run():
                service.jobs.run(accepted['job_id'])
            worker=threading.Thread(target=run)
            worker.start();assert entered.wait(3)
            raise RoughcutError('roughcut_state_unreadable')
        return original(piece,record)
    monkeypatch.setattr(service.store,'write_state',fail_stop)
    with pytest.raises(RoughcutError):
        service.stop(accepted['job_id'],dict(action='stop',expectedRevision=accepted['revision']))
    worker.join(10);assert not worker.is_alive()
    result=service.job(accepted['job_id'])
    assert result['status']=='done',result
    assert service.state(identity)['plan_revision']==accepted['revision']


def test_local_model_cache_is_explicit_and_not_an_implicit_download(setup,monkeypatch,tmp_path):
    from studio.roughcut.transcription import LocalTranscriber
    from pipeline import transcribe_audio
    cache=tmp_path/'models'
    monkeypatch.setenv('MODELSCOPE_CACHE',str(cache))
    calls=[]
    class Provider:
        def __init__(self,model):calls.append(model);self.model=model
    monkeypatch.setattr(transcribe_audio,'FunASRProvider',Provider)
    worker=LocalTranscriber()
    with pytest.raises(RoughcutError) as exc:worker._provider()
    assert exc.value.code=='transcription_unavailable' and calls==[]
    model=cache/'models/iic--speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/snapshots/master'
    model.mkdir(parents=True)
    for name in ('model.pt','config.yaml'):(model/name).write_text('synthetic')
    provider=worker._provider()
    assert calls==[str(model)] and provider is worker._provider()
    assert provider.model==transcribe_audio.DEFAULT_FUNASR_MODEL
