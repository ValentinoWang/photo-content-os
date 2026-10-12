"""Native revision and image hooks in the locked Agent environment."""
from __future__ import annotations
import copy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import test_pf_agent_runtime as native_tests
adapter = native_tests.adapter
contract = native_tests.contract


@unittest.skipUnless(native_tests.AGENT_AVAILABLE and os.getenv('VIDEO_RENDER_PLAYWRIGHT_MODULE'), 'Requires locked Agent and pinned browser')
class Stage5RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.f = native_tests.NativeRuntimeTests('test_native_composition_projection_and_replay')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.addCleanup(self.assert_browsers_closed)
        self.base = copy.deepcopy(self.f.descriptor)

    def assert_browsers_closed(self):
        groups = {s['browser_pid'] for path in self.f.workspace.glob('runs/**/shot-status.json') for s in json.loads(path.read_text()).get('shots', []) if 'browser_pid' in s}
        for group in groups:
            self.assertEqual(subprocess.run(['pgrep', '-g', str(group)], capture_output=True, text=True).stdout.strip(), '')
        if os.getenv('PF_BROWSER_PID_LOG'):
            with open(os.environ['PF_BROWSER_PID_LOG'], 'a') as log:
                log.write(json.dumps({'test': self.id(), 'owned_groups': sorted(groups), 'remaining': 0}) + '\n')

    def job(self, job_id, **extra):
        f = self.f; descriptor = copy.deepcopy(self.base)
        descriptor.update(extra)
        mx = descriptor['mxHandoff']; mx['identity']['job_id'] = job_id
        mx['identity']['confirmation_ref'] = 'confirm_' + job_id
        mx['handoff_digest'] = contract.video_digest({k: v for k, v in mx.items() if k != 'handoff_digest'})
        descriptor['identity'].update(jobId=job_id, confirmationRef=mx['identity']['confirmation_ref'])
        frozen = {k: descriptor[k] for k in ('script', 'shots', 'animations', 'documentRef')}
        frozen['narrationCacheKey'] = descriptor['narration']['cacheKey'] if descriptor['narration'] else None
        for key in ('shotImageInputs', 'shotImageTask', 'renderShotIds', 'previousJobId'):
            if descriptor.get(key): frozen[key] = descriptor[key]
        descriptor['identity']['confirmedContentDigest'] = contract.video_digest(frozen)
        directory = f.workspace / 'video-inputs' / job_id; directory.mkdir(parents=True)
        (directory / 'handoff.json').write_text(json.dumps(mx))
        (directory / 'video.json').write_text(json.dumps(descriptor))
        binding = json.loads(f.binding_path.read_text())
        binding.update(identity=mx['identity'], handoff_digest=mx['handoff_digest'])
        f.binding_path.write_text(json.dumps(binding))
        return descriptor, 'runs/' + hashlib.sha256(job_id.encode()).hexdigest()[:32], {'workspace_ref': str((directory / 'handoff.json').relative_to(f.workspace))}

    def start(self, run_ref, inputs):
        f = self.f
        outcome = f.runtime.create_run('media.edit.handoff.v1', '1.0.0', f.catalog.manifest['catalog_digest'], run_ref=run_ref, inputs=inputs)
        self.assertEqual(outcome.status, 'created', outcome)
        return f.runtime.execute(run_ref, inputs=inputs)

    def test_revision_only_renders_target_preserves_old_run_and_returns_poster(self):
        f = self.f
        f.receipt_payload(f.runtime.execute(f.run_ref, inputs=f.inputs))
        old_frame = f.workspace / f.run_ref / 'compose/render/01/frames/frame-000000.png'
        old_status = (f.workspace / f.run_ref / 'compose/render/shot-status.json').read_bytes()
        old_hash = adapter.file_sha256(old_frame)
        shots = copy.deepcopy(self.base['shots'])
        code = '<html><body style="background:yellow">confirmed AI code</body></html>'
        shots[1]['renderCode'] = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        descriptor, run_ref, inputs = self.job('job_pf2_revision', shots=shots, renderShotIds=['02'], previousJobId=self.base['identity']['jobId'])
        result = f.runtime.render_video_revision(run_ref, shot_ids=['02'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
        payload = f.receipt_payload(result); f.assert_schema(payload)
        native = json.loads((f.workspace / run_ref / 'native-compose.json').read_text())
        self.assertEqual([s['attempts'] for s in native['shots']], [1, 2])
        self.assertEqual([s['cached'] for s in native['shots']], [True, False])
        new_frame = f.workspace / run_ref / 'compose/render/01/frames/frame-000000.png'
        self.assertEqual(new_frame.stat().st_ino, old_frame.stat().st_ino)
        self.assertEqual(adapter.file_sha256(old_frame), old_hash)
        old_segment = f.workspace / f.run_ref / 'compose/segments/01.mp4'
        self.assertEqual(old_segment.stat().st_ino, (f.workspace / run_ref / 'compose/segments/01.mp4').stat().st_ino)
        self.assertEqual((f.workspace / f.run_ref / 'compose/render/shot-status.json').read_bytes(), old_status)
        progress = payload['progress']; self.assertEqual(progress['waveformSource'], 'narration')
        self.assertEqual([s['shotId'] for s in progress['shotProgress']], ['02'])
        from video_derivatives import inspect_jpeg
        self.assertEqual(inspect_jpeg(f.workspace / progress['shotProgress'][0]['poster_ref'])['shortEdge'], 64)
        with patch.object(f.runtime.node_registry, '_invoke', side_effect=AssertionError('Replay rendered')):
            replay = f.runtime.render_video_revision(run_ref, shot_ids=['02'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
        self.assertEqual(replay.code, 'already_succeeded')

    def test_source_frame_and_code_render_and_normalized_retry(self):
        f = self.f; source = f.project / 'source.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=640x360:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
        binding = json.loads(f.binding_path.read_text()); binding['source_refs'].append('source.mp4'); f.binding_path.write_text(json.dumps(binding))
        task = {'action': 'source_frame', 'shotId': '01', 'sourceTimeSeconds': .25}
        descriptor, run_ref, inputs = self.job('job_pf2_frame', shotImageTask=task)
        try:
            output = f.runtime.create_video_shot_image(run_ref, task=task, inputs=inputs)
        except import_module('openclaw_media.remote_client').RemoteError:
            self.fail((f.workspace / run_ref / 'shot_image.log').read_text())
        from video_derivatives import inspect_jpeg
        measured = inspect_jpeg(f.workspace / output['image_ref']); self.assertEqual(measured['shortEdge'], 360)
        receipt = json.loads((f.workspace / run_ref / 'shot_image/image-receipt.json').read_text())
        self.assertEqual(receipt['requestedSourceTimeSeconds'], .25)
        self.assertNotIn('sourceTimeSeconds', receipt)
        # The server's retry_image emits a new job with the same original task.
        descriptor, retry_ref, retry_inputs = self.job('job_pf2_image_retry', shotImageTask=task)
        retry = f.runtime.create_video_shot_image(retry_ref, task=task, inputs=retry_inputs)
        self.assertEqual(adapter.file_sha256(f.workspace / retry['image_ref']), adapter.file_sha256(f.workspace / output['image_ref']))
        shots = copy.deepcopy(self.base['shots']); code = '<body style="background:green">static controlled HTML</body>'
        shots[0]['renderCode'] = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        task = {'action': 'code_render', 'shotId': '01'}
        descriptor, run_ref, inputs = self.job('job_pf2_code_image', shots=shots, shotImageTask=task)
        image = f.runtime.create_video_shot_image(run_ref, task=task, inputs=inputs)
        self.assertEqual(inspect_jpeg(f.workspace / image['image_ref'])['shortEdge'], 64)
        self.assertNotIn(str(f.root), json.dumps(image))
        with patch.object(f.runtime.node_registry, '_invoke', side_effect=AssertionError('Mismatched task rendered')):
            with self.assertRaises(import_module('openclaw_media.remote_client').RemoteError):
                f.runtime.create_video_shot_image(run_ref, task={**task, 'shotId': '02'}, inputs=inputs)
        # Confirmed inline code can see its controlled JPEG slot, not other
        # project assets that happen to have a guessable filename.
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=red:s=96x64', '-frames:v', '1', str(f.project / 'assets/private.png')], check=True)
        code = '<body><img src="../../private.png"></body>'
        shots[0]['renderCode'] = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        descriptor, run_ref, inputs = self.job('job_pf2_code_private_asset', shots=shots, shotImageTask=task)
        with self.assertRaises(import_module('openclaw_media.remote_client').RemoteError):
            f.runtime.create_video_shot_image(run_ref, task=task, inputs=inputs)

    def test_revision_rejects_digest_identity_and_unselected_changes(self):
        f = self.f
        f.receipt_payload(f.runtime.execute(f.run_ref, inputs=f.inputs))
        shots = copy.deepcopy(self.base['shots']); shots[0]['dialogue'] = 'unselected mutation'
        descriptor, run_ref, inputs = self.job('job_pf2_wrong_scope', shots=shots, renderShotIds=['02'], previousJobId=self.base['identity']['jobId'])
        with patch.object(f.runtime.node_registry, '_invoke', side_effect=AssertionError('Invalid revision rendered')):
            rejected = f.runtime.render_video_revision(run_ref, shot_ids=['02'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
            self.assertEqual(rejected.code, 'photo_unselected_shot_changed')
            rejected = f.runtime.render_video_revision(run_ref, shot_ids=['01'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
            self.assertEqual(rejected.code, 'photo_shot_revision_rejected')
            descriptor['shots'][1]['renderCode'] = {'language': 'html', 'code': 'tampered', 'contentDigest': 'sha256:' + '0' * 64}
            path = f.workspace / inputs['workspace_ref']; path.with_name('video.json').write_text(json.dumps(descriptor))
            rejected = f.runtime.render_video_revision(run_ref, shot_ids=['02'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
            self.assertEqual(rejected.code, 'video_identity_rejected')

    def test_teaching_revision_reuses_other_animation_and_exports_kdenlive(self):
        f = self.f; source = f.project / 'source.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=640x360:r=30:d=1', '-i', str(f.project / 'voice.wav'), '-c:v', 'libx264', '-c:a', 'aac', '-pix_fmt', 'yuv420p', str(source)], check=True)
        (f.project / 'suggestions.json').write_text('{"precision":"word","suggestions":[]}')
        (f.project / 'source.srt').write_text('1\n00:00:00,100 --> 00:00:00,900\n测试字幕\n')
        binding = json.loads(f.binding_path.read_text()); binding['source_refs'] = ['source.mp4']
        binding['steps'] = [
            {'action': 'teaching_clips', 'function': 'teaching_clips', 'kwargs': {'manifest_path': {'local_ref': 'manifest.json'}, 'output': '$output_root'}},
            {'action': 'kdenlive', 'function': 'render', 'kwargs': {'source': {'local_ref': 'source.mp4'}, 'suggestions_path': {'local_ref': 'suggestions.json'}, 'subtitles': {'local_ref': 'source.srt'}, 'output_dir': '$output_root'}}]
        f.binding_path.write_text(json.dumps(binding))
        animations = []
        for index in range(2):
            animations.append({'animationId': f'animation_{index}', 'shotId': f'{index+1:02}', 'requirement': 'fixture', 'dialogue': '口播',
                'dialogueStartSeconds': index*.5, 'dialogueEndSeconds': (index+1)*.5, 'suggestedStartSeconds': index*.5, 'durationSeconds': .5,
                'layouts': ['full_screen', 'pip_right', 'split_screen'], 'selectedLayout': 'pip_right', 'resolution': 'hold_after_dialogue'})
        descriptor, old_ref, inputs = self.job('job_pf2_teaching', animations=animations)
        f.receipt_payload(self.start(old_ref, inputs))
        self.base = copy.deepcopy(descriptor)
        shortened = copy.deepcopy(animations); shortened[0].update(durationSeconds=.25, resolution='speed_to_dialogue')
        descriptor, speed_ref, speed_inputs = self.job('job_pf2_teaching_speed', animations=shortened, renderShotIds=['01'], previousJobId=self.base['identity']['jobId'])
        speed_result = f.runtime.render_video_revision(speed_ref, shot_ids=['01'], previous_job_id=self.base['identity']['jobId'], inputs=speed_inputs)
        f.receipt_payload(speed_result)
        prepared = json.loads((f.workspace / speed_ref / 'confirmed-teaching_clips.json').read_text())
        self.assertEqual(prepared['shots'][0]['frame_clock_scale'], 2)
        image = f.workspace / speed_ref / 'teaching_clips/render/01/frames/frame-000001.png'
        pixel = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(image), '-vf', 'crop=1:1:4:5', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
        self.assertEqual(pixel, b'\xff\xff\xff')
        self.base = copy.deepcopy(descriptor); animations = shortened
        shots = copy.deepcopy(descriptor['shots']); code = '<body style="background:orange">new animation</body>'
        shots[0]['renderCode'] = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        animations = copy.deepcopy(animations); animations[0]['selectedLayout'] = 'full_screen'
        descriptor, run_ref, inputs = self.job('job_pf2_teaching_revision', shots=shots, animations=animations, renderShotIds=['01'], previousJobId=self.base['identity']['jobId'])
        result = f.runtime.render_video_revision(run_ref, shot_ids=['01'], previous_job_id=self.base['identity']['jobId'], inputs=inputs)
        payload = f.receipt_payload(result); f.assert_schema(payload)
        native = json.loads((f.workspace / run_ref / 'native-teaching_clips.json').read_text())
        self.assertEqual([s['attempts'] for s in native['shots']], [3, 1])
        self.assertEqual([s['cached'] for s in native['shots']], [False, True])
        self.assertEqual([p['shotId'] for p in payload['progress']['shotProgress']], ['01'])
        self.assertEqual(payload['progress']['waveformSource'], 'source')
        self.assertTrue(all(a['timeBasis'] == 'edited' for a in payload['candidate']['animations']))

    def test_controlled_narration_is_consumed_and_hash_checked_on_replay(self):
        f = self.f; voice = f.workspace / 'voice.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=48000:duration=1', '-c:a', 'pcm_s16le', str(voice)], check=True)
        narration = {'cacheKey': 'sha256:' + hashlib.sha256(b'confirmed-narration').hexdigest(),
                     'artifact': {'mimeType': 'audio/wav', 'sha256': 'sha256:' + adapter.file_sha256(voice), 'sizeBytes': voice.stat().st_size}}
        descriptor, run_ref, inputs = self.job('job_pf2_narration', narration=narration)
        result = self.start(run_ref, inputs); f.receipt_payload(result)
        manifest = json.loads((f.workspace / run_ref / 'confirmed-compose.json').read_text())
        self.assertEqual(Path(manifest['narration_wav']).resolve(), voice.resolve())
        import array
        output = f.workspace / run_ref / 'compose/candidate.mp4'
        pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-map', '0:a:0', '-ac', '1', '-ar', '48000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
        samples = array.array('h', pcm)[:48000]
        frequency = sum(a <= 0 < b for a, b in zip(samples, samples[1:]))
        self.assertGreater(frequency, 800); self.assertLess(frequency, 960)
        voice.write_bytes((f.project / 'voice.wav').read_bytes())
        with patch.object(f.runtime.node_registry, '_invoke', side_effect=AssertionError('Changed narration rendered')):
            rejected = f.runtime.execute(run_ref, inputs=inputs)
        self.assertEqual(rejected.code, 'photo_narration_digest_rejected')

if __name__ == '__main__': unittest.main()
