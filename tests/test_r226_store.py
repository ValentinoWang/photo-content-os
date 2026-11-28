"""CAS, atomicity and corruption barriers for R226-owned local records."""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.test_r226_api import setup,arrange,body,check,put,PRESETS
from studio.roughcut_store import RoughcutError


@pytest.mark.parametrize('bad',['null','{}','[]','{','{"schema_version":"editing_presets_store_v1","revision":true,"presets":[]}'])
def test_bad_mine_preserves_builtins_and_blocks_save(setup,bad):
    service,app,identity,root=setup
    path=service.store.presets_path;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(bad)
    value=service.presets();check('library_response',value,PRESETS)
    assert value['mine_status']=='unreadable' and value['total']==6 and not value['can_save']
    assert next(c for c in value['categories'] if c['id']=='mine')['count'] is None
    with pytest.raises(RoughcutError) as exc:service.save_preset(dict(expectedRevision=1,piece_id=identity,roughcut_revision=1,base_preset_id='trip',overrides={}))
    assert exc.value.code=='preset_store_unreadable'
    assert path.read_text()==bad
    state=arrange(service,identity)
    assert state['plan'] is not None


def test_absent_and_valid_empty_mine_are_distinct(setup):
    service,app,identity,root=setup
    assert service.presets()['mine_status']=='absent'
    put(service.store.presets_path,dict(schema_version='editing_presets_store_v1',revision=4,presets=[]))
    value=service.presets();assert value['mine_status']=='readable' and value['revision']==4


@pytest.mark.parametrize('kind',['directory','broken_link','permission'])
def test_unreadable_mine_filesystem_shapes(setup,kind):
    service,app,identity,root=setup
    path=service.store.presets_path;path.parent.mkdir(parents=True,exist_ok=True)
    if kind=='directory':path.mkdir()
    elif kind=='broken_link':path.symlink_to(path.parent/'missing')
    else:path.write_text('{}');path.chmod(0)
    try:assert service.presets()['mine_status']=='unreadable'
    finally:
        if kind=='permission':path.chmod(0o600)


def save_request(service,identity,expected=1):
    state=service.state(identity)
    return dict(expectedRevision=expected,piece_id=identity,roughcut_revision=state['plan_revision'],base_preset_id='trip',overrides={'jcut':False})


def custom(service,identity):
    arrange(service,identity)
    return arrange(service,identity,dict(type='set_technique',id='jcut',enabled=False))


def test_multiple_mine_cross_piece_recipe_only_and_newest_first(setup):
    service,app,identity,root=setup
    custom(service,identity)
    a=service.save_preset(save_request(service,identity));check('create_response',a,PRESETS)
    b=service.save_preset(save_request(service,identity,2))
    assert a['preset']['id']!=b['preset']['id']
    value=service.presets();assert value['total']==8
    assert [p['id'] for p in value['presets'][:2]]==[b['preset']['id'],a['preset']['id']]
    raw=service.store.presets_path.read_text()
    assert identity not in raw and 'song-a' not in raw and str(root) not in raw
    other=app.store.create_project(title='另一件',local_workspace=str(root))['id']
    arrange(service,other)
    state=arrange(service,other,dict(type='apply_preset',preset_id=a['preset']['id'],preset_revision=a['preset']['revision']))
    assert 'jcut' not in next(p for p in service.presets()['presets'] if p['id']==a['preset']['id'])['recipe']['techniques']
    assert not next(t for t in state['plan']['techniques'] if t['id']=='jcut')['enabled']


def test_concurrent_save_one_wins_and_atomic_failure_preserves_bytes(setup,monkeypatch):
    service,app,identity,root=setup
    custom(service,identity)
    request=save_request(service,identity)
    def save(_):
        try:return service.save_preset(request)['revision']
        except RoughcutError as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,range(2)))
    assert sorted(map(str,results))==['2','revision_conflict']
    old=service.store.presets_path.read_bytes()
    import studio.roughcut_store as module
    original=module.os.replace
    def broken(source,dest):
        if Path(dest)==service.store.presets_path:raise OSError('simulated full disk')
        return original(source,dest)
    monkeypatch.setattr(module.os,'replace',broken)
    with pytest.raises(RoughcutError) as exc:service.save_preset(save_request(service,identity,2))
    assert exc.value.code=='preset_write_failed'
    assert service.store.presets_path.read_bytes()==old
    assert not list(service.store.presets_path.parent.glob('*.tmp'))


@pytest.mark.parametrize('target',['shots','manifest','decisions','state'])
@pytest.mark.parametrize('bad',['null','[]','{'])
def test_corrupt_inputs_are_not_pristine_state(setup,target,bad):
    service,app,identity,root=setup
    paths={'shots':root/'ai-analysis/shots/shots.json','manifest':root/'ai-analysis/media-manifest.json','decisions':root/'ai-analysis/shots/decisions.json','state':service.store.state_path(identity)}
    path=paths[target];path.parent.mkdir(parents=True,exist_ok=True);path.write_text(bad)
    with pytest.raises(RoughcutError) as exc:service.state(identity)
    assert exc.value.code in ('roughcut_state_unreadable','shots_invalid')


def test_transcript_corruption_and_missing_are_distinct(setup):
    service,app,identity,root=setup
    state=arrange(service,identity)
    mid=state['warnings']['missing_word_media_ids'][0]
    path=root/'ai-analysis/transcripts'/f'{mid}.transcript.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('null')
    with pytest.raises(RoughcutError) as exc:service.state(identity)
    assert exc.value.code=='transcript_unreadable'


def test_record_symlink_is_not_followed(setup):
    service,app,identity,root=setup
    path=service.store.state_path(identity);path.parent.mkdir(parents=True,exist_ok=True)
    target=root/'private.json';target.write_text('{}');path.symlink_to(target)
    with pytest.raises(RoughcutError):service.state(identity)
    assert target.read_text()=='{}'


def test_two_processes_share_the_preset_cas_lock(setup):
    import subprocess
    import sys
    service,app,identity,root=setup
    custom(service,identity)
    request=save_request(service,identity)
    worker='''import json,sys,time
from pathlib import Path
from studio.server import StudioApplication
from studio.project_store import ProjectStore
from studio.roughcut import RoughcutService
from studio.roughcut_store import RoughcutError
app=StudioApplication(ProjectStore(Path(sys.argv[1])));service=RoughcutService(app,start_jobs=False)
original=service.store.mine
def delayed():
    result=original();time.sleep(.1);return result
service.store.mine=delayed
print('ready',flush=True);sys.stdin.readline()
try: print(json.dumps({'revision':service.save_preset(json.loads(sys.argv[2]))['revision']}),flush=True)
except RoughcutError as exc: print(json.dumps({'code':exc.code}),flush=True)
finally: service.close();app.review_jobs.close();app.video_workflow.close()
'''
    children=[subprocess.Popen([sys.executable,'-c',worker,str(app.store.state_dir),json.dumps(request)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    try:
        for child in children:
            ready=child.stdout.readline().strip()
            assert ready=='ready',child.stderr.read() if not ready else ready
        for child in children:child.stdin.write('\n');child.stdin.flush()
        results=[]
        for child in children:
            output,error=child.communicate(timeout=15);assert child.returncode==0,error
            results.append(json.loads(output))
        assert sorted(r.get('code',str(r.get('revision'))) for r in results)==['2','revision_conflict']
        assert service.presets()['total']==7
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(timeout=5)


@pytest.mark.parametrize('value',[[],True,{},dict(schema_version='editing_presets_v1',settings={},presets=[])])
def test_builtin_config_corruption_is_typed(setup,monkeypatch,value):
    service,app,identity,root=setup
    original=service.reader.read
    def fake(path,*a,**kwargs):
        return value if Path(path).name=='editing_presets.json' else original(path,*a,**kwargs)
    monkeypatch.setattr(service.reader,'read',fake)
    with pytest.raises(RoughcutError) as exc:service.presets()
    assert exc.value.code=='builtin_presets_invalid'
