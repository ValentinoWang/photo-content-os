"""Studio reads identity-bound PF results and stores an explicit local preference."""
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from studio.project_store import ProjectStore, ProjectStoreError
from studio.server import StudioApplication


class StudioHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ps-studio-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.media.mkdir()
        self.app = StudioApplication(ProjectStore(self.root / 'state'))
        self.project = self.app.store.create_project(title='交接测试', local_workspace=str(self.media))
        self.identity = {'jobId': 'job_ps', 'photoProjectId': self.project['id'], 'photoProjectRevision': 1}
        self.write(self.media / 'video.json', {'scope': 'video_handoff_v1', 'identity': self.identity, 'shots': [], 'animations': []})
        self.run = self.media / 'runs' / hashlib.sha256(b'job_ps').hexdigest()[:32]
        self.run.mkdir(parents=True)
        self.write(self.run / 'native-suggest.json', {'duration': 10, 'precision': 'word', 'auto_cut_allowed': True, 'suggestions': [
            {'type':'repetition', 'start':1, 'end':2, 'evidence_text':'重说', 'auto_cut_allowed':True},
            {'type':'repetition', 'start':3, 'end':4, 'evidence_text':'只复核', 'auto_cut_allowed':False}]})
        self.env = patch.dict(os.environ, {'LOCAL_MEDIA_ROOT': str(self.media), 'PHOTO_STUDIO_VIDEO_WORKSPACE': str(self.media), 'PHOTO_STUDIO_VIDEO_BINDING':'', 'OPENCLAW_MEDIA_VIDEO_TOOLS_REPORT':''})
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def projection(self):
        return self.app.video_handoff_projection(self.project['id'])

    def tool_report(self, **changes):
        now = datetime.now(timezone.utc)
        editor = {'toolId':'chatcut', 'installed':True, 'version':'0.6.9', 'status':'unavailable', 'reasonCode':'not_logged_in', 'evidenceKind':'none', 'checkedAt':now.isoformat(), 'expiresAt':(now+timedelta(minutes=5)).isoformat()}
        editor.update(changes)
        path=self.root/'tools.json'
        self.write(path, {'editor':editor})
        os.environ['OPENCLAW_MEDIA_VIDEO_TOOLS_REPORT']=str(path)

    def test_installation_does_not_prove_login_or_handshake(self):
        data=self.projection()
        self.assertIsNone(data['tools']['chatcut']['login'])
        self.assertFalse(data['tools']['chatcut']['handshake'])
        self.assertIsNone(data['tools']['chatcut']['projectUrl'])

    def test_five_tool_levels_and_expiry(self):
        self.tool_report(installed=False)
        self.assertFalse(self.projection()['tools']['chatcut']['installed'])
        self.tool_report()
        self.assertFalse(self.projection()['tools']['chatcut']['login'])
        self.tool_report(reasonCode='logged_in', evidenceKind='command_probe')
        self.assertTrue(self.projection()['tools']['chatcut']['login'])
        self.assertFalse(self.projection()['tools']['chatcut']['handshake'])
        self.tool_report(status='online', reasonCode='probe_ok', evidenceKind='mcp_handshake')
        self.assertEqual(self.projection()['state'],'connected')
        self.assertIsNone(self.projection()['tools']['chatcut']['projectRef'])
        self.tool_report(status='online', evidenceKind='process_probe')
        self.assertFalse(self.projection()['tools']['chatcut']['handshake'])
        self.tool_report(status='online', evidenceKind='mcp_handshake', expiresAt='2000-01-01T00:00:00+00:00')
        self.assertFalse(self.projection()['tools']['chatcut']['handshake'])

    def test_review_only_and_sentence_precision(self):
        data=self.projection()
        self.assertEqual([s['automatic'] for s in data['suggestions']],[True,False])
        self.write(self.run/'native-suggest.json', {'duration':10,'precision':'sentence','suggestions':[{'type':'repetition','start':1,'end':2,'auto_cut_allowed':True}]})
        self.assertFalse(self.projection()['suggestions'][0]['automatic'])

    def test_choice_persists_without_changing_project_or_receipts(self):
        before=self.app.store.get_project(self.project['id'])
        self.write(self.run/'handoff_manifest.json', {'private':'unchanged'})
        old=(self.run/'handoff_manifest.json').read_bytes()
        self.assertEqual(self.app.video_editor_choice(self.project['id']), {'editor':'chatcut','revision':1})
        chosen=self.app.video_editor_choice(self.project['id'], {'editor':'kdenlive','revision':1})
        self.assertEqual(chosen, {'editor':'kdenlive','revision':2})
        restarted=StudioApplication(ProjectStore(self.root/'state'))
        self.assertEqual(restarted.video_editor_choice(self.project['id']),chosen)
        self.assertEqual(before,self.app.store.get_project(self.project['id']))
        self.assertEqual(old,(self.run/'handoff_manifest.json').read_bytes())
        with self.assertRaises(ProjectStoreError):
            self.app.video_editor_choice(self.project['id'],{'editor':'chatcut','revision':1})
        with self.assertRaises(ProjectStoreError):
            self.app.video_editor_choice(self.project['id'],{'editor':'unknown','revision':2})

    def test_candidate_identity_and_waveform_source_are_required(self):
        def candidate(identity,source='source',peaks=None):
            self.write(self.media/'candidate.json', {'candidate':{'identity':identity,'durationSeconds':9,'sourceDurationSeconds':10,'frameCount':270,'checks':{'playable':'pass'}}, 'progress':{'waveformSource':source,'waveformPeaks':[0,.5,1] if peaks is None else peaks}})
        candidate(self.identity)
        self.assertEqual(self.projection()['state'],'returned')
        self.assertEqual(self.projection()['waveformPeaks'],[0,.5,1])
        candidate(self.identity,'narration')
        self.assertEqual(self.projection()['waveformPeaks'],[])
        candidate(self.identity,peaks=[1.2])
        self.assertEqual(self.projection()['waveformPeaks'],[])
        candidate({**self.identity,'photoProjectRevision':2})
        self.assertEqual(self.projection()['candidate'],{})

    def test_uploaded_requires_existing_agent_journal(self):
        self.write(self.media/'candidate.json', {'candidate':{'identity':self.identity,'sourceDurationSeconds':10}})
        self.assertFalse(self.projection()['uploaded'])
        self.write(self.run/'video-result-1.json', {'result_status':'succeeded','video_result':{'identity':self.identity,'candidateArtifact':{'artifactId':'c'},'previewArtifact':{'artifact':{'artifactId':'p'}},'subtitleArtifact':{'artifactId':'s'}}})
        self.assertTrue(self.projection()['uploaded'])

    def test_stale_project_and_symlink_escape_fail_closed(self):
        self.app.store.update_project(self.project['id'],{'title':'新版本'},expected_revision=1)
        self.assertIsNone(self.projection())
        outside=self.root/'outside.json'
        self.write(outside,{'private':'secret'})
        link=self.media/'leak.json';link.symlink_to(outside)
        self.assertEqual(self.app._video_json(self.media,'leak.json'),{})
        self.assertNotIn(str(self.root),json.dumps(self.app.video_editor_choice(self.project['id'])))


if __name__ == '__main__':
    unittest.main()
