"""Native Photo/Agent runtime tests in the already installed locked Agent environment."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from _support import load_script
adapter=load_script('openclaw_video_execution','pf_runtime_adapter',register=True)
contract=load_script('openclaw_product_contract','pf_runtime_contract',register=True)
AGENT_AVAILABLE=importlib.util.find_spec('openclaw_media') is not None


@unittest.skipUnless(AGENT_AVAILABLE and os.getenv('VIDEO_RENDER_PLAYWRIGHT_MODULE'),'Requires locked Agent and pinned Playwright environment')
class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        InstalledCatalog=import_module("openclaw_media.catalog").InstalledCatalog
        from test_video_render import create_fixture
        self.temp=tempfile.TemporaryDirectory(prefix='pf-runtime-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        media_env=patch.dict(os.environ,{'LOCAL_MEDIA_ROOT':str(self.root)})
        media_env.start();self.addCleanup(media_env.stop)
        self.workspace=self.root/'workspace';self.workspace.mkdir()
        self.project=self.root/'project';self.project.mkdir()
        self.manifest=create_fixture(self.project,shots=2)
        manifest=json.loads(self.manifest.read_text())
        for i,s in enumerate(manifest['shots']):s['id']=f'{i+1:02}'
        self.manifest.write_text(json.dumps(manifest))
        self.catalog=InstalledCatalog();digest=self.catalog.manifest['catalog_digest']
        identity={'job_id':'job_pf_native','tenant_id':'11111111-1111-4111-8111-111111111111','work_id':'variant_pf','work_revision':1,
                  'project_id':'project_pf','project_revision':1,'catalog_digest':digest,'confirmation_ref':'confirm_pf'}
        self.shots=[]
        for i in range(2):
            self.shots.append({'shot':{'shotId':f'{i+1:02}','startSeconds':i*.5,'endSeconds':(i+1)*.5},
                              'visual':{'text':'fixture','image':None},'dialogue':'口播','subtitle':'测试字幕','camera':'全屏',
                              'audio':'配音','saveStatus':'saved','failureCode':None})
        payload={'identity':identity,'script':'口播','storyboard':[{'shot':r['shot']['shotId'],'visual':r['visual']['text'],
                 'dialogue':r['dialogue'],'subtitle':r['subtitle'],'camera':r['camera'],'audio':r['audio']} for r in self.shots],
                 'animations':[],'tts_ref':'voice.wav'}
        handoff={**payload,'handoff_digest':contract.video_digest(payload)}
        mc_identity={'jobId':identity['job_id'],'publicTenantId':'tenant_pf','publicContentId':'content_pf','publicVariantId':'variant_pf',
                     'workRevision':1,'photoProjectId':'project_pf','photoProjectRevision':1,'catalogDigest':digest,'confirmationRef':'confirm_pf'}
        frozen={'script':'口播','shots':self.shots,'animations':[],'documentRef':{},'narrationCacheKey':None}
        mc_identity['confirmedContentDigest']=contract.video_digest(frozen)
        self.descriptor={'scope':'video_handoff_v1','identity':mc_identity,'script':'口播','shots':self.shots,'animations':[],
                         'documentRef':{},'narration':None,'mxHandoff':handoff}
        (self.workspace/'handoff.json').write_text(json.dumps(handoff));self.write_descriptor()
        shutil.copyfile(self.project/'voice.wav',self.workspace/'voice.wav')
        store=self.root/'store.json';store.write_text(json.dumps({'schema_version':'creative_project_store_v1','projects':[{'id':'project_pf','revision':1}]}))
        binding={'identity':identity,'handoff_digest':handoff['handoff_digest'],'creative_store':str(store),'project_root':str(self.project),
                 'steps':[{'action':'compose','function':'compose','kwargs':{'manifest_path':{'local_ref':'manifest.json'},'output':'$output_root'}}],
                 'candidate_ref':'candidate.json','source_refs':['voice.wav']}
        if self._testMethodName == 'test_native_kdenlive_projection_uses_explicit_backend':
            source=self.project/'source.mp4'
            subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=30:d=1',
                            '-i',str(self.project/'voice.wav'),'-c:v','libx264','-c:a','aac','-pix_fmt','yuv420p',str(source)],check=True)
            (self.project/'suggestions.json').write_text(json.dumps({'precision':'word','suggestions':[]}))
            (self.project/'source.srt').write_text('1\n00:00:00,100 --> 00:00:00,900\n测试字幕\n')
            binding['source_refs']=['source.mp4']
            binding['steps']=[{'action':'kdenlive','function':'render','kwargs':{
                'source':{'local_ref':'source.mp4'},'suggestions_path':{'local_ref':'suggestions.json'},
                'subtitles':{'local_ref':'source.srt'},'output_dir':'$output_root'}}]
        self.binding_path=self.root/'binding.json';self.binding_path.write_text(json.dumps(binding))
        self.runtime=adapter.runtime_factory(self.binding_path,for_agent=True)(self.workspace,self.catalog)
        self.run_ref='runs/'+hashlib.sha256(identity['job_id'].encode()).hexdigest()[:32]
        self.inputs={'workspace_ref':'handoff.json'}
        created=self.runtime.create_run('media.edit.handoff.v1','1.0.0',digest,run_ref=self.run_ref,inputs=self.inputs)
        self.assertEqual(created.status,'created',created)
    def write_descriptor(self):
        (self.workspace/'video.json').write_text(json.dumps(self.descriptor))
    def receipt_payload(self,result):
        self.assertEqual(result.status,'succeeded',result)
        refs=[a.artifact_ref for n in result.receipt.node_receipts for a in n.artifacts if a.mime_type=='application/json']
        self.assertEqual(len(refs),1)
        return json.loads((self.workspace/refs[0]).read_text())
    def assert_schema(self,payload):
        import yaml
        import jsonschema
        path=Path(os.environ['PF_MC_OPENAPI'])
        doc=yaml.safe_load(path.read_text())
        validator=jsonschema.Draft202012Validator(doc['components']['schemas']['CreationVideoCandidate'],resolver=jsonschema.RefResolver.from_schema(doc))
        errors=list(validator.iter_errors(payload['candidate']))
        self.assertEqual(errors,[],str(errors))
        validator=jsonschema.Draft202012Validator(doc['components']['schemas']['CreationVideoShotProgress'],resolver=jsonschema.RefResolver.from_schema(doc))
        for shot in payload['progress']['shotProgress']:self.assertEqual(list(validator.iter_errors(shot)),[])
    def test_native_composition_projection_and_replay(self):
        result=self.runtime.execute(self.run_ref,inputs=self.inputs)
        payload=self.receipt_payload(result);self.assert_schema(payload)
        self.assertEqual(payload['candidate']['status'],'candidate')
        self.assertEqual(payload['candidate']['identity'],self.descriptor['identity'])
        self.assertEqual(payload['candidate']['checks']['actualFrames'],12)
        self.assertNotIn(str(self.root),json.dumps(payload))
        with patch.object(self.runtime.node_registry,'_invoke',side_effect=AssertionError('Replay executed native renderer')):
            replay=self.runtime.execute(self.run_ref,inputs=self.inputs)
        self.assertEqual(replay.code,'already_succeeded')
    def test_native_kdenlive_projection_uses_explicit_backend(self):
        result=self.runtime.execute(self.run_ref,inputs=self.inputs)
        payload=self.receipt_payload(result);self.assert_schema(payload)
        self.assertEqual(payload['candidate']['status'],'candidate')
        self.assertEqual(payload['candidate']['checks']['actualFrames'],30)
        self.assertTrue(payload['progress']['exported'])
        self.assertEqual(payload['progress']['precutCount'],0)
        with patch.object(self.runtime.node_registry,'_invoke',side_effect=AssertionError('Spoken retry chose another backend')):
            self.descriptor['retryShotId']='02';self.write_descriptor()
            rejected=self.runtime.retry_video_shot(self.run_ref,shot_id='02',inputs=self.inputs)
        self.assertEqual(rejected.code,'photo_shot_retry_unavailable')

    def test_failed_shot_retry_preserves_other_frames_voice_and_run(self):
        html=self.project/'assets/shot-2.html';original=html.read_text();html.write_text('<img src="missing.png">'+original)
        result=self.runtime.execute(self.run_ref,inputs=self.inputs);self.assertEqual(result.status,'pending_manual')
        native=json.loads((self.workspace/self.run_ref/'native-compose.json').read_text())
        self.assertEqual([s['status'] for s in native['shots']],['completed','failed'])
        frame=self.workspace/self.run_ref/'compose/render/01/frames/frame-000000.png'
        timestamp=frame.stat().st_mtime_ns;voice=contract.video_digest({'hash':adapter.file_sha256(self.workspace/'voice.wav')})
        html.write_text(original)
        self.descriptor['retryShotId']='02';self.write_descriptor()
        result=self.runtime.retry_video_shot(self.run_ref,shot_id='02',inputs=self.inputs)
        payload=self.receipt_payload(result);self.assert_schema(payload)
        self.assertEqual(frame.stat().st_mtime_ns,timestamp)
        self.assertEqual(contract.video_digest({'hash':adapter.file_sha256(self.workspace/'voice.wav')}),voice)
        native=json.loads((self.workspace/self.run_ref/'native-compose.json').read_text())
        self.assertEqual([s['attempts'] for s in native['shots']],[1,2])
        self.assertEqual(result.receipt.run_ref,self.run_ref)
    def test_wrong_retry_and_tampered_full_descriptor_do_not_execute(self):
        self.descriptor['retryShotId']='02';self.write_descriptor()
        with patch.object(self.runtime.node_registry,'_invoke',side_effect=AssertionError('Invalid retry executed')):
            result=self.runtime.retry_video_shot(self.run_ref,shot_id='01',inputs=self.inputs)
            self.assertEqual(result.code,'photo_shot_retry_rejected')
            self.descriptor['shots'][0]['dialogue']='tampered';self.write_descriptor()
            result=self.runtime.execute(self.run_ref,inputs=self.inputs)
            self.assertEqual(result.status,'pending_manual')

if __name__=='__main__':unittest.main()
