"""R226 service/HTTP contracts, isolated synthetic media and injected beat reader."""
import copy
import hashlib
import http.client as http_client
import json
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from studio.project_store import ProjectStore
from studio.server import StudioApplication
from studio.media_review import digest
from studio.roughcut import RoughcutService
from studio.roughcut_store import RoughcutError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/roughcut-api.schema.json').read_text())
PRESETS = json.loads((ROOT / 'schemas/editing-presets.schema.json').read_text())
FIXTURE = json.loads((ROOT / 'tests/fixtures/r226-editing-techniques/synthetic.json').read_text())


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


def check(name, value, schema=SCHEMA):
    Draft202012Validator({**schema, '$ref': '#/$defs/' + name}).validate(value)


def fake_generated(**kwargs):
    """Only the renderer boundary is synthetic; service binding checks remain real."""
    from studio.roughcut_drafts import compile_roughcut_edl
    edl=compile_roughcut_edl(**{k:kwargs[k] for k in ('plan','planner_inputs','sources_by_media','music_sources','project_id','project_revision')})
    directory=kwargs['workspace']/'draft-project/roughcut'/str(kwargs['plan_revision'])/uuid.uuid4().hex
    directory.mkdir(parents=True)
    put(directory/'06_edit_decision_list.json',edl)
    (directory/'preview.mp4').write_bytes(b'synthetic-preview-video')
    specs=[('preview.mp4','preview','video/mp4'),('06_edit_decision_list.json','draft','application/json')]
    choice=kwargs.get('editor_choice')
    if choice:
        if choice['method']=='external':
            (directory/'kdenlive').mkdir();(directory/'kdenlive/timeline.kdenlive').write_text('<mlt/>')
            specs.append(('kdenlive/timeline.kdenlive','draft','application/xml'))
        (directory/'剪辑交接说明.md').write_text('剪辑交接说明\n')
        specs.append(('剪辑交接说明.md','guide','text/markdown; charset=utf-8'))
    artifacts=[];index={}
    for name,kind,mime in specs:
        aid='test-'+uuid.uuid4().hex
        artifacts.append(dict(id=aid,kind=kind,content_type=mime,revision=kwargs['plan_revision'],shot_id=None,url=f'/api/review/pieces/{kwargs["project_id"]}/roughcut/media/{aid}'))
        index[aid]=dict(relative_path=(directory/name).relative_to(kwargs['workspace']).as_posix(),allowed_root=directory.relative_to(kwargs['workspace']).as_posix(),content_type=mime)
    result=dict(editor=(choice or {}).get('editor','otio_kdenlive'),method=(choice or {}).get('method','external'),project_revision=kwargs['project_revision'],edl_digest=hashlib.sha256((directory/'06_edit_decision_list.json').read_bytes()).hexdigest(),artifact_ids=[a['id'] for a in artifacts],checks=[dict(id='source_ranges',status='passed')])
    return dict(result=result,artifacts=artifacts,artifact_index=index,directory=str(directory),receipt_path=str(directory/'receipt.json'),duration_sec=kwargs['plan']['metrics']['duration_sec'])


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path / 'media'))
    root = tmp_path / 'media/trip/work'
    root.mkdir(parents=True)
    rows, items = [], {}
    for i, shot in enumerate(FIXTURE['shots']):
        shot = copy.deepcopy(shot)
        mid = shot.get('media_id', shot['id'])
        relative = f'{shot["scene"]}/{mid}.mp4' if shot['kind'] == 'video' else f'{shot["scene"]}/{mid}.jpg'
        src = root / relative
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b'synthetic-media')
        frame = f'ai-analysis/shots/frames/{shot["id"]}.jpg'
        (root / frame).parent.mkdir(parents=True, exist_ok=True)
        (root / frame).write_bytes(b'0123456789')
        shot.update(media_id=mid, source_relative_path=relative, frames=[frame], status='selected', model_decision='精选')
        rows.append(shot)
        items[relative] = dict(media_id=mid, relative_path=relative, media_type='video' if shot['kind']=='video' else 'image', created_at='2026-01-01T00:00:00Z')
    put(root / 'ai-analysis/media-manifest.json', dict(items=list(items.values())))
    put(root / 'ai-analysis/shots/shots.json', dict(shots=rows, run_status='complete', hook_candidates=[]))
    app = StudioApplication(ProjectStore(tmp_path / 'state'))
    project = app.store.create_project(title='合成旅程', local_workspace=str(root))
    view = app.media_review.shots(project['id'])
    put(root / 'ai-analysis/shots/decisions.json', dict(version=1, shots={}, confirmation=dict(confirmed_at='2026-01-01T00:00:00Z',selection_digest=view['selection_digest'],evidence_digest=view['evidence_digest'])))
    app.doctor_checks = [dict(id='kdenlive',status='ready'),dict(id='edit_tool_openchatcut',status='ready'),dict(id='jianying',status='missing')]
    app.doctor_checked_at='2026-10-21T00:00:00Z'
    def beats(track_id, *, media_root=None):
        return copy.deepcopy(FIXTURE['beat_maps'][track_id])
    service = RoughcutService(app, beat_loader=beats, start_jobs=False, poll_interval=.01)
    for track in FIXTURE['beat_maps']:
        path=root/'music'/f'{track}.wav';path.parent.mkdir(exist_ok=True);path.write_bytes(b'synthetic-audio')
    app.media_review.music_audio=lambda track:root/'music'/f'{track}.wav'
    service.preview_renderer=fake_generated
    service.draft_generator=fake_generated
    service.music_resolver=app.media_review.music_audio
    app.roughcut = service
    yield service, app, project['id'], root
    service.close()
    app.review_jobs.close()
    app.video_workflow.close()


def body(service, identity, command):
    state=service.state(identity)
    return dict(expectedRevision=state['revision'],projectRevision=state['project_revision'],selectionDigest=state['source_summary']['selection_digest'],command=command)


def arrange(service, identity, command=None):
    accepted=service.command(identity,body(service,identity,command or dict(type='select_music',track_ids=['song-a'])))
    check('command_response',accepted)
    service.jobs.run(accepted['job_id'])
    state=service.state(identity)
    check('state_response',state)
    assert state['status']=='ready',state.get('failure')
    return state


def test_initial_prerequisite_and_no_music_are_distinct(setup):
    service,app,identity,root=setup
    value=service.state(identity);check('state_response',value)
    assert value['status']=='no_music' and value['plan'] is None
    put(root/'ai-analysis/shots/decisions.json',dict(version=2,shots={},confirmation=None))
    value=service.state(identity);check('state_response',value)
    assert value['status']=='prerequisite'
    with pytest.raises(RoughcutError) as exc:service.command(identity,body(service,identity,dict(type='select_music',track_ids=['song-a'])))
    assert exc.value.code=='selection_not_confirmed'


def test_plan_projection_and_all_card_numbers(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    assert value['plan']['metrics']['shot_count']==27
    assert value['warnings']==value['plan']['warnings']
    assert value['customization']==value['plan']['customization']
    assert len(value['preset_previews'])==6
    assert len({p['duration_sec'] for p in value['preset_previews']})>1
    assert value['plan_revision']==value['revision']
    assert value['display']['draft_allowed'] is True
    assert value['display']['draft_blockers']==[]
    assert value['warnings']['bed_short_count']>=0
    assert value['warnings']['missing_word_count']==6  # This synthetic fixture has six selfie videos.
    assert not any(o['technique'] in ('pause','duck') for o in value['plan']['occurrences'])
    assert str(root) not in json.dumps(value)
    assert all('license' not in k for a in value['analysis'] for k in a.get('beat_map',{}))


def test_every_preset_preview_projects_its_own_timeline(setup):
    service,app,identity,root=setup
    plans={};original=service.planner
    def capture(**kwargs):
        result=original(**kwargs)
        plans[result['preset_id']]=copy.deepcopy(result)
        return result
    service.planner=capture
    value=arrange(service,identity)
    for preview in value['preset_previews']:
        own=plans[preview['preset_id']]
        assert preview['cuts']==own['cuts']
        assert preview['mapped_sections']==own['mapped_sections']
        assert all(c['position']==pytest.approx(c['t']/preview['duration_sec'],abs=1e-6) for c in preview['cuts'])
        assert all(0<=s['start']<s['end']<=preview['duration_sec'] for s in preview['mapped_sections'])
    assert len({json.dumps(p['cuts'],sort_keys=True) for p in value['preset_previews']})>1


def test_failed_preset_preview_has_no_other_presets_timeline(setup):
    service,app,identity,root=setup
    original=service.planner
    def fail_one(**kwargs):
        if kwargs['preset']['id']=='race':raise RoughcutError('song_too_short')
        return original(**kwargs)
    service.planner=fail_one
    preview=next(p for p in arrange(service,identity)['preset_previews'] if p['preset_id']=='race')
    assert preview['status']=='failed'
    assert preview['cuts']==[] and preview['mapped_sections']==[]


def test_preset_preview_schema_requires_own_timeline(setup):
    service,app,identity,root=setup
    preview=arrange(service,identity)['preset_previews'][0]
    validator=Draft202012Validator({**SCHEMA,'$ref':'#/$defs/preset_preview'})
    for field in ('cuts','mapped_sections'):
        bad=copy.deepcopy(preview);del bad[field]
        assert not validator.is_valid(bad)
    queued={**preview,'status':'queued','duration_sec':None,'preview_shot_ids':[],'cuts':[],'mapped_sections':[]}
    validator.validate(queued)
    assert not validator.is_valid({**queued,'cuts':preview['cuts']})


def test_builtin_schema_requires_duck_silence_gap():
    config=json.loads((ROOT/'scripts/editing_presets.json').read_text())
    check('builtin_config',config,PRESETS)
    assert config['settings']['duck_silence_gap_sec']==1.0
    for invalid in (None,0,-1,True):
        bad=copy.deepcopy(config)
        if invalid is None:del bad['settings']['duck_silence_gap_sec']
        else:bad['settings']['duck_silence_gap_sec']=invalid
        assert not Draft202012Validator({**PRESETS,'$ref':'#/$defs/builtin_config'}).is_valid(bad)


@pytest.mark.parametrize('command',[
 dict(type='select_music',track_ids=[]),dict(type='select_music',track_ids=['song-a']*2),
 dict(type='select_music',track_ids=['a','b','c','d']),dict(type='delete_all'),
 dict(type='set_technique',id='missing',enabled=True),dict(type='set_technique',id='bed',enabled=1),
 dict(type='reset_customization',path='/private/source')])
def test_invalid_commands_do_not_mutate_state(setup,command):
    service,app,identity,root=setup
    before=service.state(identity)
    with pytest.raises(RoughcutError):service.command(identity,body(service,identity,command))
    after=service.state(identity)
    assert (before['revision'],before['selection'])==(after['revision'],after['selection'])


def test_project_and_roughcut_cas_are_separate(setup):
    service,app,identity,root=setup
    state=arrange(service,identity)
    for key in ('expectedRevision','projectRevision','selectionDigest'):
        req=body(service,identity,dict(type='set_technique',id='jcut',enabled=False))
        req[key]='0'*64 if key=='selectionDigest' else 987
        with pytest.raises(RoughcutError) as exc:service.command(identity,req)
        assert exc.value.code in ('revision_conflict','roughcut_inputs_stale')
    assert service.state(identity)['revision']==state['revision']


def test_customization_occurrence_and_reset(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    occurrence=next(o for o in value['plan']['occurrences'] if o['technique']=='jcut')
    value=arrange(service,identity,dict(type='set_occurrence',id=occurrence['id'],enabled=False))
    assert occurrence['id'] in value['customization']['skipped_occurrence_ids']
    value=arrange(service,identity,dict(type='set_technique',id='jcut',enabled=False))
    assert 'jcut' in value['customization']['disabled']
    value=arrange(service,identity,dict(type='reset_customization'))
    assert value['customization']==dict(changed=False,disabled=[],enabled=[],skipped_occurrence_ids=[])


def test_music_add_replace_remove_and_swap(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    value=arrange(service,identity,dict(type='add_song',track_id='song-b'))
    assert value['plan']['metrics']['song_count']==2
    second=value['selection']['playlist'][1]['id']
    swap=value['plan']['swaps'][0]
    if swap['alternatives']:
        value=arrange(service,identity,dict(type='move_swap',swap_id=swap['id'],before_shot_id=swap['alternatives'][0]['before_shot_id']))
        assert value['selection']['swap_positions'][second]==swap['alternatives'][0]['before_shot_id']
    value=arrange(service,identity,dict(type='replace_song',song_instance_id=second,track_id='song-c'))
    assert value['selection']['playlist'][1]['id']==second
    value=arrange(service,identity,dict(type='remove_song',song_instance_id=second))
    assert value['plan']['metrics']['song_count']==1 and second not in value['selection']['swap_positions']


def test_failed_rearrange_keeps_old_plan_and_binding(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    accepted=service.command(identity,body(service,identity,dict(type='set_technique',id='jcut',enabled=False)))
    service.planner=lambda **kwargs: (_ for _ in ()).throw(RoughcutError('shot_too_short',dict(shot_ids=['s0'],short_shot_count=1)))
    service.jobs.run(accepted['job_id'])
    failed=service.state(identity);check('state_response',failed)
    assert failed['status']=='failed'
    assert failed['plan']==value['plan'] and failed['plan_input_binding']==value['plan_input_binding']
    assert failed['plan_revision']==value['plan_revision']<failed['revision']
    assert failed['failure']['design_state']=='cut-rearrange-failed'


def test_caps_reuse_choice_and_unique_matrix(setup):
    service,app,identity,root=setup
    for editor,method in [('otio_kdenlive','external'),('chatcut','external'),('openchatcut','external'),('otio_kdenlive','guide'),('openfilm','self')]:
        choice=app._video_editor_choice(identity)
        app.video_editor_choice(identity,dict(editor=editor,method=method,revision=choice['revision']))
        value=service.capabilities(identity);check('capabilities_response',value)
        assert value['choice']['method']==method
        if editor in ('chatcut','openchatcut') or method=='self':assert not value['selected']['can_generate']
        if method=='guide':assert value['selected']['can_generate']
        if method=='self':assert value['selected_option_id'] is None
    path=app.settings_dir/'video-editors'/(hashlib.sha256(identity.encode()).hexdigest()+'.json')
    path.write_text('null')
    value=service.capabilities(identity);check('capabilities_response',value)
    assert value['selected'] is None and value['choice']['error']['code']=='editor_choice_unreadable'


def test_draft_rejects_unbound_edl_digest(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    with pytest.raises(RoughcutError) as exc:service.draft(identity,dict(expectedRevision=value['revision'],projectRevision=value['project_revision'],editorChoiceRevision=1,edlDigest='a'*64))
    assert exc.value.code=='roughcut_inputs_stale' and exc.value.http_status==409
    check('error_response',exc.value.response())


def test_media_range_expiry_and_wrong_piece(setup):
    service,app,identity,root=setup
    value=arrange(service,identity)
    artifact=next(a for a in value['artifacts'] if a['kind']=='thumbnail')
    result=service.media(identity,artifact['id'],'bytes=2-5')
    with result.path.open('rb') as f:f.seek(result.start);assert f.read(result.length)==b'2345'
    assert result.status==206 and result.headers['Content-Range']=='bytes 2-5/10'
    for bad in ('bytes=99-','bytes=0-1,4-6','bytes=-0','no-range'):
        with pytest.raises(RoughcutError) as exc:service.media(identity,artifact['id'],bad)
        assert exc.value.http_status==416
    assert service.media(identity,artifact['id'],'bytes=-3').length==3
    other=app.store.create_project(title='另一件',local_workspace=str(root))['id']
    with pytest.raises(RoughcutError) as exc:service.media(other,artifact['id'])
    assert exc.value.code=='roughcut_media_not_found'
    document=json.loads((root/'ai-analysis/shots/shots.json').read_text());document['shots'][0]['end_sec']+=1;put(root/'ai-analysis/shots/shots.json',document)
    with pytest.raises(RoughcutError) as exc:service.media(identity,artifact['id'])
    assert exc.value.code=='roughcut_inputs_stale'


@pytest.fixture
def http(setup):
    service,app,identity,root=setup
    server=ThreadingHTTPServer(('127.0.0.1',0),app.handler())
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def call(method,path,value=None,headers=None):
        conn=http_client.HTTPConnection(*server.server_address,timeout=5)
        payload=json.dumps(value) if value is not None else None
        conn.request(method,path,payload,headers or {})
        response=conn.getresponse();data=response.read();status=response.status;metadata=dict(response.getheaders());conn.close()
        return status,json.loads(data) if metadata.get('Content-Type','').startswith('application/json') else data,metadata
    yield call
    server.shutdown();server.server_close();thread.join()


def test_http_inventory_schema_csrf_origin_host_and_draft(setup,http):
    service,app,identity,root=setup
    from studio.api_contract import is_registered_route,build_openapi
    for route in SCHEMA['x-routes']:
        concrete=route['path'].replace('{id}',identity).replace('{jobId}','job-demo').replace('{artifactId}','asset-demo')
        assert is_registered_route(route['method'],concrete)
        assert route['path'] in build_openapi()['paths']
    path=f'/api/review/pieces/{identity}/roughcut'
    status,value,_=http('GET',path);assert status==200;check('state_response',value)
    req=body(service,identity,dict(type='select_music',track_ids=['song-a']))
    for headers,code in [({},'csrf_invalid'),({'X-Content-OS-CSRF':app.csrf_token,'Origin':'https://elsewhere.invalid'},'origin_forbidden'),({'X-Content-OS-CSRF':app.csrf_token,'Host':'elsewhere.invalid'},'host_forbidden')]:
        status,value,_=http('POST',path+'/commands',req,headers);assert status==403;check('error_response',value);assert value['error']['code']==code
    headers={'X-Content-OS-CSRF':app.csrf_token}
    status,value,_=http('POST',path+'/commands',req,headers);assert status==202;check('command_response',value)
    service.jobs.run(value['job_id'])
    status,value,_=http('GET','/api/review/roughcut-jobs/'+value['job_id']);assert status==200;check('job_response',value)
    state=service.state(identity)
    status,value,_=http('POST',path+'/drafts',dict(expectedRevision=state['revision'],projectRevision=state['project_revision'],editorChoiceRevision=1,edlDigest='f'*64),headers)
    assert status==409 and value['error']['code']=='roughcut_inputs_stale'
    status,value,_=http('GET','/api/review/editing-presets');assert status==200;check('library_response',value,PRESETS)


def test_http_draft_preview_guide_and_open_roundtrip(setup,http):
    service,app,identity,root=setup
    state=arrange(service,identity);headers={'X-Content-OS-CSRF':app.csrf_token}
    base=f'/api/review/pieces/{identity}/roughcut'
    preview=next(a for a in state['artifacts'] if a['id']==state['playback']['preview_artifact_id'])
    status,data,metadata=http('GET',preview['url'],headers={'Range':'bytes=0-8'})
    assert status==206 and data==b'synthetic' and metadata['Content-Type']=='video/mp4'
    request=dict(expectedRevision=state['revision'],projectRevision=state['project_revision'],editorChoiceRevision=1,edlDigest=state['plan_input_binding']['edl_digest'])
    status,accepted,_=http('POST',base+'/drafts',request,headers)
    assert status==202;check('draft_response',accepted)
    service.jobs.run(accepted['job_id'])
    status,state,_=http('GET',base);assert status==200;check('state_response',state)
    assert state['draft']['design_state']=='cut-drafted'
    note=next(a for a in state['artifacts'] if a['id']==state['draft']['guide_artifact_id'])
    status,data,metadata=http('GET',note['url'])
    assert status==200 and metadata['Content-Type']=='text/plain; charset=utf-8' and metadata['Content-Disposition']=='inline'
    assert '要你在剪辑软件里做' in data.decode() and '镜头标识' not in data.decode()
    request.update(expectedRevision=state['revision'],edlDigest=state['draft']['edl_digest'])
    service.editor_opener=lambda **k:dict(editor_backend='otio_kdenlive',opened=True,local_only=True)
    status,data,_=http('POST',base+'/drafts/open',request);assert status==403
    status,data,_=http('POST',base+'/drafts/open',{**request,'path':'/client/timeline.kdenlive'},headers);assert status==400
    status,data,_=http('POST',base+'/drafts/open',request,headers);assert status==200;check('open_draft_response',data)
    status,data,_=http('GET',base+'/drafts/open');assert status==404


def test_performance_target_inputs_shared_by_six_and_unrelated_growth(setup,monkeypatch):
    service,app,identity,root=setup
    calls=[];original=service.planner
    def counted(**kwargs):calls.append(kwargs);return original(**kwargs)
    service.planner=counted
    arrange(service,identity)
    assert len(calls)==6
    assert len({id(c['shots']) for c in calls})==1
    before=len(calls)
    for _ in range(3):service.state(identity);service.presets();service.capabilities(identity)
    assert len(calls)==before
    monkeypatch.setattr(app.store,'list_projects',lambda:pytest.fail('must not scan catalog'))
    for i in range(100):
        folder=root.parent/f'unrelated-{i}'/'ai-analysis';put(folder/'media-manifest.json',dict(items=[{'large':'x'*1000}]*10))
    metrics=copy.deepcopy(service.io_stats)
    service.state(identity)
    assert service.io_stats['bytes']==metrics['bytes']
    assert service.io_stats['reads']==metrics['reads']


def reconfirm(app, identity, root, document, manifest=None):
    put(root/'ai-analysis/shots/shots.json',document)
    if manifest is not None:put(root/'ai-analysis/media-manifest.json',manifest)
    view=app.media_review.shots(identity)
    put(root/'ai-analysis/shots/decisions.json',dict(version=2,shots={},confirmation=dict(confirmed_at='2026-01-02T00:00:00Z',selection_digest=view['selection_digest'],evidence_digest=view['evidence_digest'])))


def test_shared_missing_transcript_is_read_once_per_snapshot(setup,monkeypatch):
    service,app,identity,root=setup
    document=json.loads((root/'ai-analysis/shots/shots.json').read_text())
    selfie=[s for s in document['shots'] if s['scene']=='selfie-moments']
    selfie[1].update(media_id=selfie[0]['media_id'],source_relative_path=selfie[0]['source_relative_path'])
    reconfirm(app,identity,root,document)
    calls=[];original=service.reader.read
    def counted(path,*a,**kw):
        if Path(path).parent.name=='transcripts':calls.append(Path(path))
        return original(path,*a,**kw)
    monkeypatch.setattr(service.reader,'read',counted)
    service._context(identity,transcripts=True)
    assert len(calls)==len(set(calls))==5


def test_photo_is_excluded_from_missing_word_count(setup):
    service,app,identity,root=setup
    document=json.loads((root/'ai-analysis/shots/shots.json').read_text())
    row=next(s for s in document['shots'] if s['id']=='selfie-05')
    old=row['source_relative_path'];new=old.removesuffix('.mp4')+'.jpg'
    (root/old).rename(root/new);row.update(kind='photo',source_relative_path=new)
    manifest=json.loads((root/'ai-analysis/media-manifest.json').read_text())
    item=next(x for x in manifest['items'] if x['relative_path']==old)
    item.update(relative_path=new,media_type='image')
    reconfirm(app,identity,root,document,manifest)
    value=arrange(service,identity)
    assert value['warnings']['missing_word_count']==5
    assert 'selfie-05' not in value['warnings']['missing_word_shot_ids']
    assert value['display']['speech']['eligible_video_count']==5


def test_all_other_http_routes_and_media_errors(setup,http):
    service,app,identity,root=setup
    value=arrange(service,identity)
    base=f'/api/review/pieces/{identity}'
    headers={'X-Content-OS-CSRF':app.csrf_token}
    status,data,_=http('GET',base+'/editor-capabilities');assert status==200;check('capabilities_response',data)
    artifact=next(a for a in value['artifacts'] if a['kind']=='thumbnail')
    status,data,metadata=http('GET',artifact['url'],headers={'Range':'bytes=0-2'});assert (status,data)==(206,b'012');assert metadata['Content-Range']=='bytes 0-2/10'
    status,data,metadata=http('GET',artifact['url'],headers={'Range':'bytes=100-'});assert status==416;check('error_response',data);assert metadata['Content-Range']=='bytes */10'
    value=arrange(service,identity,dict(type='set_technique',id='jcut',enabled=False))
    req=dict(expectedRevision=1,piece_id=identity,roughcut_revision=value['plan_revision'],base_preset_id='trip',overrides={'jcut':False})
    status,data,_=http('POST','/api/review/editing-presets',req,headers);assert status==201;check('create_response',data,PRESETS)
    status,data,_=http('POST',base+'/roughcut/transcriptions',dict(expectedRevision=value['revision'],selectionDigest=value['source_summary']['selection_digest'],shot_ids=value['warnings']['missing_word_shot_ids']),headers)
    assert status==202;check('transcription_response',data)
    job=data['job_id']
    status,data,_=http('POST','/api/review/roughcut-jobs/'+job,dict(action='stop',expectedRevision=data['revision']),headers);assert status==202;check('stop_response',data)
    status,data,_=http('GET','/api/review/roughcut-jobs/'+job);assert status==200 and data['status']=='stopped'
    status,data,_=http('GET','/api/review/roughcut-jobs/absent');assert status==404;check('error_response',data)
    status,data,_=http('POST',base+'/roughcut/commands',[],headers);assert status==400 and data['error']['code']=='body_invalid'
    status,data,_=http('GET',base+'/roughcut',headers={'Host':'elsewhere.invalid'});assert status==403;check('error_response',data)


def test_override_changes_binding_and_card_digest_without_changing_sources(setup):
    service,app,identity,root=setup
    before=arrange(service,identity)
    after=arrange(service,identity,dict(type='set_technique',id='jcut',enabled=False))
    assert before['plan_input_binding']['shots_digest']==after['plan_input_binding']['shots_digest']
    assert before['plan_input_binding']['preset_digest']!=after['plan_input_binding']['preset_digest']
    a=next(p for p in before['preset_previews'] if p['preset_id']=='trip')
    b=next(p for p in after['preset_previews'] if p['preset_id']=='trip')
    assert a['input_digest']!=b['input_digest']


def test_track_identity_cannot_be_a_private_path(setup):
    service,app,identity,root=setup
    path='../../private-camera/source.mp4'
    with pytest.raises(RoughcutError) as exc:
        service.command(identity,body(service,identity,dict(type='select_music',track_ids=[path])))
    assert path not in json.dumps(exc.value.response())
    assert exc.value.code=='roughcut_command_invalid'
