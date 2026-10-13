"""Direct receipts keep measured failures and completed-shot artwork public."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
import os
import hashlib
import subprocess
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import threading
import urllib.request
import urllib.error

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from video_candidate import failed_shot_progress
from studio.project_store import ProjectStore, ProjectStoreError
from studio.server import StudioApplication


class DirectReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ps7-receipt-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frames = self.root / 'frames'
        self.frames.mkdir()
        Image.new('RGB', (108, 192), (30, 90, 70)).save(self.frames / 'frame-000000.png')
        self.native = {'shots': [
            {'id': '01', 'status': 'completed', 'progress_frames': 2, 'total_frames': 2, 'frames_dir': str(self.frames)},
            {'id': '02', 'status': 'failed', 'progress_frames': 0, 'total_frames': 3,
             'code': 'missing_asset', 'line': 14, 'file': '/Users/private/assets/figure.svg',
             'reason': 'private stack /Users/private/shot.html', 'source': 'private source'}]}
        self.descriptor = {'shots': [{'shot': {'shotId': sid}} for sid in ('01', '02')]}

    def test_partial_failure_keeps_real_poster_and_redacts_diagnostics(self):
        before = copy.deepcopy(self.native)
        result = failed_shot_progress(self.native, self.descriptor, 30, output_dir=self.root, workspace=self.root)
        complete, failed = result['shotProgress']
        self.assertEqual(result['failedShotId'], '02')
        self.assertEqual((failed['failedLine'], failed['missingAsset']), (14, 'figure.svg'))
        self.assertNotIn('/Users', json.dumps(result))
        self.assertNotIn('private source', json.dumps(result))
        self.assertNotIn('frames_dir', complete)
        with Image.open(self.root / complete['poster_ref']) as poster:
            self.assertEqual(poster.format, 'JPEG')
            self.assertEqual((poster.width, poster.height), (complete['poster_width'], complete['poster_height']))
            self.assertLessEqual(min(poster.size), 360)
        self.assertLessEqual((self.root / complete['poster_ref']).stat().st_size, 200000)
        self.assertEqual(self.native, before)

    def test_missing_diagnostics_are_unknown_and_retry_filters_unaffected_shot(self):
        descriptor = {**self.descriptor, 'retryShotId': '02'}
        for line, asset in [(None, None), (True, 'bad\nname.svg'), (-1, '..'), (14.2, 'image.svg?secret=x'), (2147483648, 'a' * 121)]:
            with self.subTest(line=line, asset=asset):
                self.native['shots'][1].update(line=line, file=asset)
                result = failed_shot_progress(self.native, descriptor, 30, output_dir=self.root, workspace=self.root)
                self.assertEqual([s['shotId'] for s in result['shotProgress']], ['02'])
                self.assertNotIn('failedLine', result['shotProgress'][0])
                self.assertNotIn('missingAsset', result['shotProgress'][0])
        self.native['shots'][1].update(line=14, file=r'C:\private\figure.svg')
        result = failed_shot_progress(self.native, descriptor, 30)
        self.assertEqual(result['shotProgress'][0]['missingAsset'], 'figure.svg')


class DirectStudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ps7-studio-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.media.mkdir()
        self.app = StudioApplication(ProjectStore(self.root / 'state'))
        self.project = self.app.store.create_project(title='直出测试', local_workspace=str(self.media))
        self.identity = {'jobId': 'ps7_direct', 'photoProjectId': self.project['id'], 'photoProjectRevision': 1}
        self.run = self.media / 'runs' / hashlib.sha256(b'ps7_direct').hexdigest()[:32]
        self.run.mkdir(parents=True)
        self.binding = self.root / 'binding.json'
        self.write(self.root / 'creative.json', {'projects': [self.project]})
        self.write(self.binding, {'identity': {'project_id': self.project['id'], 'project_revision': 1, 'job_id': 'ps7_direct'},
            'project_root': str(self.media), 'creative_store': str(self.root / 'creative.json'), 'source_refs': [],
            'steps': [{'action': 'compose', 'kwargs': {}}]})
        self.write(self.media / 'video.json', {'scope': 'video_handoff_v1', 'identity': self.identity, 'shots': [], 'animations': []})
        self.payload = {'candidate': {'identity': self.identity, 'publicCandidateId': 'candidate_ps7', 'status': 'candidate',
            'durationSeconds': 50.233333, 'sourceDurationSeconds': 50.233333, 'frameCount': 1507, 'cutCount': 0}, 'preview_ref': 'preview.mp4'}
        self.write(self.run / 'handoff_manifest.json', self.payload)
        (self.media / 'preview.mp4').write_bytes(b'bounded preview fixture')
        self.env = patch.dict(os.environ, {'LOCAL_MEDIA_ROOT': str(self.media), 'PHOTO_STUDIO_VIDEO_WORKSPACE': str(self.media),
            'PHOTO_STUDIO_VIDEO_BINDING': str(self.binding), 'OPENCLAW_MEDIA_VIDEO_TOOLS_REPORT': ''})
        self.env.start()
        self.addCleanup(self.env.stop)

    @staticmethod
    def write(path, data):
        path.write_text(json.dumps(data))

    def test_bound_direct_candidate_uses_existing_preview_without_editor_probe(self):
        before = (self.run / 'handoff_manifest.json').read_bytes()
        with patch.object(self.app.video_workflow, 'editors', side_effect=AssertionError('direct must not probe editors')):
            data = self.app.video_handoff_projection(self.project['id'])
        self.assertEqual(data['line'], 'direct')
        self.assertEqual(data['editorName'], '本机逐帧渲染')
        self.assertEqual(len(data['candidates']), 1)
        self.assertEqual(data['candidates'][0]['previewUrl'], f'/api/projects/{self.project["id"]}/video-preview/candidate_ps7')
        self.assertEqual(self.app.video_workflow.preview(self.project['id'], 'candidate_ps7'), (self.media / 'preview.mp4').resolve())
        self.assertEqual((self.run / 'handoff_manifest.json').read_bytes(), before)
        self.assertFalse((self.run / 'studio-candidates.json').exists())
        self.assertNotIn('selectedEditing', data)

    def test_preview_rejects_other_identity_outside_workspace_and_missing_file(self):
        for change in ['identity', 'outside', 'missing']:
            with self.subTest(change=change):
                payload = copy.deepcopy(self.payload)
                if change == 'identity':
                    payload['candidate']['identity']['jobId'] = 'stale_job'
                else:
                    payload['preview_ref'] = '../secret.mp4' if change == 'outside' else 'missing.mp4'
                    (self.root / 'secret.mp4').write_bytes(b'private')
                self.write(self.run / 'handoff_manifest.json', payload)
                data = self.app.video_handoff_projection(self.project['id'])
                self.assertFalse(any(c['previewUrl'] for c in data['candidates']))
                with self.assertRaises(ProjectStoreError):
                    self.app.video_workflow.preview(self.project['id'], 'candidate_ps7')

    def test_real_renderer_omits_editing_controls_for_direct_candidates(self):
        module = (Path(__file__).resolve().parents[1] / 'studio/static/handoff.js').as_uri()
        data = self.app.video_handoff_projection(self.project['id'])
        code = r'''
import assert from 'node:assert/strict';
const {renderHandoff}=await import(MODULE);
globalThis.location={origin:'http://127.0.0.1:8765'};
globalThis.window={addEventListener(){},removeEventListener(){}};
const target={querySelector(){return null},querySelectorAll(){return []}};
const data=DATA;
for(const state of ['returned','check-failed']){
 data.state=state;
 if(state==='check-failed'){data.candidate.checks={playable:'fail'};data.candidates=[];}
 renderHandoff(target,data,{photoOrigin:location.origin});
 assert(target.innerHTML.includes('脚本直出'));
 assert(target.innerHTML.includes('本机逐帧渲染'));
 for(const forbidden of ['data-method=','Kdenlive','0 处预剪','剪辑建议','return-input','software-disclosure'])assert(!target.innerHTML.includes(forbidden),forbidden);
 if(state==='returned')assert(target.innerHTML.includes('/video-preview/candidate_ps7'));
 else assert(target.innerHTML.includes('检查失败，这一版不能采用'));
}
'''.replace('MODULE', json.dumps(module)).replace('DATA', json.dumps(data))
        result = subprocess.run(['node', '--input-type=module', '-e', code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_http_preview_serves_byte_ranges_and_rejects_invalid_ranges(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), self.app.handler())
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/projects/{self.project["id"]}/video-preview/candidate_ps7'
            body = (self.media / 'preview.mp4').read_bytes()
            for value, expected in [(None, body), ('bytes=0-3', body[:4]), ('bytes=5-', body[5:]), ('bytes=-4', body[-4:]), ('bytes=5-999', body[5:])]:
                with self.subTest(range=value):
                    request = urllib.request.Request(url, headers={'Range': value} if value else {})
                    with urllib.request.urlopen(request) as response:
                        self.assertEqual(response.status, 206 if value else 200)
                        self.assertEqual(response.headers['Accept-Ranges'], 'bytes')
                        self.assertEqual(response.read(), expected)
            for value in ['bytes=999-', 'bytes=5-3', 'bytes=-0', 'bytes=-', 'bytes=0-1,3-4', 'bytes='+'9'*5000+'-']:
                with self.subTest(range=value):
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(urllib.request.Request(url, headers={'Range': value}))
                    self.assertEqual(error.exception.code, 416)
                    self.assertEqual(error.exception.headers['Content-Range'], f'bytes */{len(body)}')
                    error.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
