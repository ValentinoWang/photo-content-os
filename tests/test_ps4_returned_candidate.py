"""Upload provenance and saved-project cross-checks use actual media bytes."""
import io,json,os,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from edit_backends.kdenlive_adapter import Backend
from test_ps4_kdenlive_readback import saved_project
import test_ps_studio_handoff as fixture_module

class ReturnedProjectTests(unittest.TestCase):
    setUp=fixture_module.StudioHandoffTests.setUp
    write=staticmethod(fixture_module.StudioHandoffTests.write)
    projection=fixture_module.StudioHandoffTests.projection

    def test_native_duration_mismatch_is_failed_not_manual(self):
        source,directory,_=saved_project(self.media,self.project['id'])
        binding=self.root/'binding.json'
        self.write(binding,{'identity':{'project_id':self.project['id'],'project_revision':1,'job_id':self.identity['jobId']},'creative_store':str(self.app.store.path),'project_root':str(self.media),'source_refs':['source.mp4'],'steps':[]})
        os.environ['PHOTO_STUDIO_VIDEO_BINDING']=str(binding)
        ctx=self.app.video_workflow.context(self.project['id']);session=self.app.video_workflow._session(ctx)
        session.update(backend=Backend(),project_dir=directory)
        # A real 4-second upload mismatches the saved 3.6-second project.
        raw=source.read_bytes()
        data=self.app.video_workflow.receive(self.project['id'],io.BytesIO(raw),len(raw),{'identity':self.identity,'expectedRevision':1})
        assert data['state']=='check-failed'
        c=json.loads((self.run/'studio-candidate.json').read_text())['candidate']
        assert c['provenance']=='native_readback' and c['checks']['frameCount']=='fail'
        assert c['checks']['expectedFrames']==108 and c['checks']['actualFrames']==120
        assert next(self.run.glob('returned-*/returned.mp4')).read_bytes()==raw

    def test_matching_native_return_has_actual_saved_subtitle_and_cut(self):
        source,directory,_=saved_project(self.media,self.project['id'])
        backend=Backend();readback=backend.read_back(project_dir=directory)
        rendered=backend.render(**readback['render_kwargs'],output_dir=self.media/'saved-export')
        assert rendered['status']=='candidate' and rendered['frames']==108
        exported=Path(rendered['output'])
        binding=self.root/'binding.json'
        self.write(binding,{'identity':{'project_id':self.project['id'],'project_revision':1,'job_id':self.identity['jobId']},'creative_store':str(self.app.store.path),'project_root':str(self.media),'source_refs':['source.mp4'],'steps':[]})
        os.environ['PHOTO_STUDIO_VIDEO_BINDING']=str(binding)
        ctx=self.app.video_workflow.context(self.project['id']);self.app.video_workflow._session(ctx).update(backend=Backend(),project_dir=directory)
        raw=exported.read_bytes()
        data=self.app.video_workflow.receive(self.project['id'],io.BytesIO(raw),len(raw),{'identity':self.identity,'expectedRevision':1})
        assert data['state']=='returned'
        c=json.loads((self.run/'studio-candidate.json').read_text())['candidate']
        assert c['provenance']=='native_readback' and c['cutCount']==1
        assert c['checks']['subtitles']=='pass' and c['checks']['frameCount']=='pass'
        assert '00:00:03,600' in c['subtitles']
