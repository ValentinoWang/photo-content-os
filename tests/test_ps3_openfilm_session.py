"""Real native HTTP edits and disk readback; explicit pinned runtime is required."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from unittest.mock import patch
import pytest
from studio.project_store import ProjectStore, ProjectStoreError
from studio.server import StudioApplication
from edit_backends.registry import describe_backends


@pytest.mark.skipif(not os.environ.get('CONTENT_OS_OPENFILM_PACKAGE'),reason='explicit pinned openfilm runtime required')
def test_native_accept_retract_split_undo_redo_and_conflict(tmp_path,monkeypatch):
    media=tmp_path/'media';media.mkdir()
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(media))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_WORKSPACE',str(media))
    source=media/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x25516b:s=288x512:r=30:d=6','-f','lavfi','-i','sine=frequency=660:duration=6','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
    app=StudioApplication(ProjectStore(tmp_path/'state'))
    app.video_workflow.origin='http://127.0.0.1:8765'
    app.video_workflow.probes=[{**r,'probe':{'id':r['id'],'installed':True,'version':'fixture','runnable':True,'status':'online','reason':None}} for r in describe_backends()]
    p=app.store.create_project(title='原生 HTTP 回读',local_workspace=str(media))
    identity={'photoProjectId':p['id'],'photoProjectRevision':1,'jobId':'ps3-native'}
    descriptor={'scope':'video_handoff_v1','identity':identity,'animations':[], 'shots':[{'shot':{'shotId':'01','startSeconds':0,'endSeconds':6},'subtitle':'原生 HTTP 回读'}]}
    (media/'video.json').write_text(json.dumps(descriptor))
    binding=tmp_path/'binding.json'
    binding.write_text(json.dumps({'identity':{'project_id':p['id'],'project_revision':1,'job_id':'ps3-native'},'creative_store':str(app.store.path),'project_root':str(media),'steps':[],'source_refs':['source.mp4'],'candidate_ref':'candidate.json'}))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING',str(binding))
    run=media/'runs'/hashlib.sha256(b'ps3-native').hexdigest()[:32];run.mkdir(parents=True)
    (run/'native-suggest.json').write_text(json.dumps({'duration':6,'precision':'word','auto_cut_allowed':True,'suggestions':[{'type':'repetition','start':1,'end':2,'auto_cut_allowed':True},{'type':'silence','start':1.5,'end':2.5,'auto_cut_allowed':True},{'type':'review','start':3,'end':4,'auto_cut_allowed':False}]}))
    app.video_editor_choice(p['id'],{'editor':'openfilm','method':'self','revision':1})
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    ctx=app.video_workflow.context(p['id'])
    base={'identity':identity,'expectedRevision':1}
    def command(op,**kw):
        pub=app.video_workflow._session(ctx)['public']
        return app.video_workflow.command(p['id'],{**base,'op':op,'engineRevision':pub.get('engineRevision'),**kw})
    def times(data):
        return [c['time'] for t in data['film']['tracks'] for c in t['clips'] if c['src']=='assets/source.mp4']
    try:
        data=command('self-open');assert times(data)==[[0,6]]
        module=urllib.request.urlopen(data['hostModule'])
        assert module.headers.get_content_type()=='text/javascript'
        assert b'renderHandoff' in module.read()
        painter=urllib.request.urlopen(data['hostModule'].replace('handoff.js','film-subtitle.js'))
        assert painter.headers.get_content_type()=='text/javascript'
        assert b'export function filmSubtitleFrameHtml' in painter.read()
        configuration=json.load(urllib.request.urlopen(data['hostModule'].replace('handoff.js','session.json')))
        assert set(configuration)=={'photoOrigin','projectId'}
        # The host URL is authenticated; its key never becomes a cloud field.
        origin=app.video_workflow._session(ctx)['engine']['origin']
        with pytest.raises(urllib.error.HTTPError): urllib.request.urlopen(origin+'/api/projects')
        assert times(command('accept',suggestionId=0))==[[0,1],[2,6]]
        assert times(command('accept',suggestionId=1))==[[0,1],[2.5,6]]
        assert times(command('retract',suggestionId=0))==[[0,1.5],[2.5,6]]
        assert times(command('undo'))==[[0,1],[2.5,6]]
        assert times(command('redo'))==[[0,1.5],[2.5,6]]
        data=command('split',time=.5);assert times(data)==[[0,.5],[.5,1.5],[2.5,6]]
        assert times(command('undo'))==[[0,1.5],[2.5,6]]
        data=command('redo');assert times(data)==[[0,.5],[.5,1.5],[2.5,6]]
        rev=data['engineRevision'];snapshot=json.loads(json.dumps(data['film']))
        with pytest.raises(ProjectStoreError,match='工程已有新修改'):
            command('save',engineRevision='stale')
        session=app.video_workflow._session(ctx)
        assert session['backend']._state(session['project_dir']/'openfilm-project')['doc']==snapshot
        assert session['public']['engineRevision']==rev
        with pytest.raises(ProjectStoreError,match='只供复核'): command('accept',suggestionId=2)
        # An independent native HTTP edit invalidates even the latest local view.
        state=session['backend']._state(session['project_dir']/'openfilm-project')
        session['backend'].studio_edit(base=state['rev'],ops=[{'op':'set','clip':state['doc']['tracks'][0]['clips'][0]['id'],'field':'volume','value':.8}])
        history=len(session['undo'])
        with pytest.raises(ProjectStoreError,match='工程已有新修改'): command('split',time=.25)
        assert len(session['undo'])==history
        assert command('reload')['engineRevision']!=rev
        session=app.video_workflow._session(ctx)
        old_history=len(session['undo']);old_redo=len(session['redo']);old_accepted=set(session['accepted'])
        with patch.object(session['backend'],'studio_edit',side_effect=ValueError('openfilm_revision_conflict')):
            with pytest.raises(ProjectStoreError,match='工程已有新修改'): command('accept',suggestionId=0)
        assert (len(session['undo']),len(session['redo']),set(session['accepted']))==(old_history,old_redo,old_accepted)
        before=times(command('reload'))
        assert times(command('self-open'))==before
        assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    finally:
        app.video_workflow.close()
        assert all(s['backend'].close()['remaining_pids']==[] for s in app.video_workflow.sessions.values() if s.get('backend'))


@pytest.mark.skipif(not os.environ.get('CONTENT_OS_OPENFILM_PACKAGE'),reason='explicit pinned openfilm runtime required')
def test_native_export_projects_only_actual_selected_animations(tmp_path,monkeypatch):
    media=tmp_path/'media';media.mkdir()
    monkeypatch.setenv('LOCAL_MEDIA_ROOT',str(media));monkeypatch.setenv('PHOTO_STUDIO_VIDEO_WORKSPACE',str(media))
    source=media/'source.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x25516b:s=288x512:r=30:d=4','-f','lavfi','-i','sine=frequency=660:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
    (media/'source.srt').write_text('1\n00:00:00,000 --> 00:00:04,000\n真实工程导出验证\n')
    app=StudioApplication(ProjectStore(tmp_path/'state'));app.video_workflow.origin='http://127.0.0.1:8765'
    app.video_workflow.probes=[{**r,'probe':{'installed':True,'runnable':True,'version':'fixture'}} for r in describe_backends()]
    p=app.store.create_project(title='真实工程导出',local_workspace=str(media));identity={'photoProjectId':p['id'],'photoProjectRevision':1,'jobId':'ps3-export-native'}
    descriptor={'scope':'video_handoff_v1','identity':identity,'shots':[{'shot':{'shotId':'01','startSeconds':0,'endSeconds':4},'subtitle':'真实工程导出验证'}], 'animations':[{'animationId':'pending-animation','shotId':'01','requirement':'待采纳动画','dialogue':'验证','suggestedStartSeconds':0,'durationSeconds':4}]}
    (media/'video.json').write_text(json.dumps(descriptor))
    binding=tmp_path/'binding.json';binding.write_text(json.dumps({'identity':{'project_id':p['id'],'project_revision':1,'job_id':identity['jobId']},'creative_store':str(app.store.path),'project_root':str(media),'source_refs':['source.mp4','source.srt'],'candidate_ref':'candidate.json','steps':[]}));monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING',str(binding))
    run=media/'runs'/hashlib.sha256(identity['jobId'].encode()).hexdigest()[:32];run.mkdir(parents=True)
    (run/'native-suggest.json').write_text(json.dumps({'duration':4,'precision':'word','auto_cut_allowed':True,'suggestions':[{'type':'repetition','start':1,'end':2,'auto_cut_allowed':True}]}))
    app.video_editor_choice(p['id'],{'editor':'openfilm','method':'self','revision':1})
    base={'identity':identity,'expectedRevision':1}
    try:
        d=app.video_workflow.command(p['id'],{**base,'op':'self-open'})
        d=app.video_workflow.command(p['id'],{**base,'op':'accept','suggestionId':0,'engineRevision':d['engineRevision']})
        old_host=d['host']
        d=app.video_workflow.command(p['id'],{**base,'op':'export','engineRevision':d['engineRevision']})
        assert d['state']=='returned',d
        candidate=json.loads((media/'candidate.json').read_text())['candidate']
        assert candidate['status']=='candidate' and candidate['frameCount']==90
        assert candidate['durationSeconds']==3 and candidate['removedSeconds']==1
        assert candidate['animations']==[] and candidate['cutCount']==1
        assert candidate['editingMethod']=='software_workflow'
        assert d['host']!=old_host
    finally:
        app.video_workflow.close()
