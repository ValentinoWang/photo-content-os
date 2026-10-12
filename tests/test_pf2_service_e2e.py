"""Opt-in real Media service + PostgreSQL + native Photo synthetic round trip."""
from __future__ import annotations
import copy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

ENABLED = os.getenv('PF2_POSTGRES_E2E') == '1'
if ENABLED:
    from test_creation_video_mc import video, key
    from test_workspace_identity_acceptance import identity_database_url, scenario


@pytest.mark.skipif(not ENABLED, reason='Requires disposable PostgreSQL and locked Agent environment')
def test_source_frame_save_confirmed_rewrite_target_render_and_real_posters(video, tmp_path, monkeypatch):
    from _support import load_script
    from test_video_render import create_fixture
    exchange = import_module('openclaw_media.video_exchange')
    catalog = import_module('openclaw_media.catalog').InstalledCatalog()
    adapter = load_script('openclaw_video_execution', 'pf2_service_adapter', register=True)
    # Media and Photo have independent modules named media_common. The Photo
    # renderer keeps its module instance, and the service cache is restored.
    old_common = sys.modules.pop('media_common', None)
    photo_common = load_script('media_common', 'media_common', register=True)
    if old_common is not None: sys.modules['media_common'] = old_common
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path))
    workspace = tmp_path / 'photo-workspace'; workspace.mkdir()
    project = tmp_path / 'photo-project'; project.mkdir()
    manifest_path = create_fixture(project, shots=2)
    manifest = json.loads(manifest_path.read_text())
    for index, shot in enumerate(manifest['shots']): shot['id'] = f'{index+1:02}'
    manifest_path.write_text(json.dumps(manifest))
    source = project / 'source.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=640x360:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True)
    original = {p.name: adapter.file_sha256(p) for p in (source, project / 'voice.wav')}
    store = tmp_path / 'creative-store.json'
    store.write_text(json.dumps({'schema_version': 'creative_project_store_v1', 'projects': [{'id': 'project_fixture', 'revision': 2}]}))
    binding_path = tmp_path / 'photo-binding.json'
    v = video; service = v['service']; state = v['state']
    shots = []
    for index in range(2):
        row = copy.deepcopy(state['shots'][0]); row['shot'].update(shotId=f'{index+1:02}', startSeconds=index*.5, endSeconds=(index+1)*.5)
        code = '<body style="background:orange">initial</body>' if index else '<body style="background:blue"><img src="shot-image.jpg"></body>'
        row['renderCode'] = {'language': 'html', 'code': code, 'contentDigest': 'sha256:' + hashlib.sha256(code.encode()).hexdigest()}
        shots.append(row)
    animation = {'animationId': 'animation_pf2', 'shotId': '02', 'requirement': 'code animation', 'dialogue': state['script'],
        'dialogueStartSeconds': .5, 'dialogueEndSeconds': 1, 'suggestedStartSeconds': .5, 'durationSeconds': .5,
        'layouts': ['pip_right', 'full_screen', 'split_screen'], 'selectedLayout': 'full_screen', 'resolution': 'hold_after_dialogue'}
    def save(state, shots):
        return service.save_creation_video_storyboard(v['ctx'], v['variant'], dict(expectedWorkRevision=state['workRevision'], expectedVideoRevision=state['revision'], expectedDocumentRef=state['documentRef'], shots=shots, animations=[animation]), idempotency_key=key())['video']
    state = save(state, shots)

    class Remote:
        progress_receipts = []
        def video_artifact_download(self, job_id, artifact_id):
            return service.download(job_id, artifact_id, credential=v['credential'])
        def video_artifact_upload(self, job_id, **body):
            assert not any(str(project) in str(value) or str(workspace) in str(value) for value in body.values())
            return service.upload(job_id, v['credential'], body, idempotency_key=key())
        def video_progress(self, job_id, **body):
            self.progress_receipts.append(copy.deepcopy(body))
            return service.progress(job_id, v['credential'], body, idempotency_key=key())
    remote = Remote()
    def claim(job_id):
        d = v['devices']; credential = v['credential']; job = d.get_job(v['ctx'].tenant_id, job_id)
        job = d.lease_job(job_id, credential, lease_seconds=300, idempotency_key=key(), expected_revision=job['revision'])
        job = d.ack_job(job_id, credential, ack_ref='ack_pf2', idempotency_key=key(), expected_revision=job['revision'])
        return d.start_job(job_id, credential, start_ref='start_pf2', idempotency_key=key(), expected_revision=job['revision'])
    def photo(job):
        descriptor, input_ref = exchange.prepare(remote, workspace, job)
        binding_path.write_text(json.dumps({'identity': descriptor['mxHandoff']['identity'], 'handoff_digest': descriptor['mxHandoff']['handoff_digest'],
            'creative_store': str(store), 'project_root': str(project), 'steps': [{'action': 'compose', 'function': 'compose', 'kwargs': {'manifest_path': {'local_ref': 'manifest.json'}, 'output': '$output_root'}}],
            'candidate_ref': 'candidate.json', 'source_refs': ['voice.wav', 'source.mp4']}))
        runtime = adapter.runtime_factory(binding_path, for_agent=True)(workspace, catalog)
        return runtime, descriptor, 'runs/' + hashlib.sha256(job['job_id'].encode()).hexdigest()[:32], {'workspace_ref': input_ref}
    def receive(job, result):
        v['devices'].result_job(job['job_id'], v['credential'], result_status='succeeded', result_refs=[], artifact_refs=[], failure_code=None,
            expected_revision=job['revision'], video_result=result, idempotency_key=key())

    request = dict(action='source_frame', expectedWorkRevision=state['workRevision'], expectedVideoRevision=state['revision'], shotId='01', sourceTimeSeconds=.25,
        deviceId=v['device']['device_id'], binding=v['handoff']['binding'])
    state = service.retry_creation_video_shot(v['ctx'], v['variant'], request, idempotency_key=key())['video']
    image_job = claim(state['imageJobs'][-1]['identity']['jobId'])
    runtime, descriptor, run_ref, inputs = photo(image_job)
    hidden = source.with_suffix('.offline'); source.rename(hidden)
    try:
        with patch.dict(sys.modules, {'media_common': photo_common}):
            with pytest.raises(import_module('openclaw_media.remote_client').RemoteError) as failed:
                runtime.create_video_shot_image(run_ref, task=descriptor['shotImageTask'], inputs=inputs)
        vr = exchange.failure(image_job, failed.value.code)
        v['devices'].result_job(image_job['job_id'], v['credential'], result_status='blocked', result_refs=[], artifact_refs=[], failure_code=failed.value.code,
            expected_revision=image_job['revision'], video_result=vr, idempotency_key=key())
    finally:
        hidden.rename(source)
    state = service.get_creation_video(v['ctx'], v['variant'])['video']
    assert state['imageJobs'][-1]['status'] == 'failed'
    original_task = descriptor['shotImageTask']
    state = service.retry_creation_video_shot(v['ctx'], v['variant'], {**request, 'action': 'retry_image', 'expectedVideoRevision': state['revision']}, idempotency_key=key())['video']
    image_job = claim(state['imageJobs'][-1]['identity']['jobId'])
    runtime, descriptor, run_ref, inputs = photo(image_job)
    assert descriptor['shotImageTask'] == original_task
    with patch.dict(sys.modules, {'media_common': photo_common}):
        image = runtime.create_video_shot_image(run_ref, task=descriptor['shotImageTask'], inputs=inputs)
    receive(image_job, exchange.image_result(remote, workspace, image_job, descriptor, image))
    state = service.get_creation_video(v['ctx'], v['variant'])['video']
    assert state['shots'][0]['visual']['image']['status'] == 'unsaved'
    assert state['shots'][0]['visual']['image']['sourceTimeSeconds'] is None
    shots = copy.deepcopy(state['shots']); shots[0]['saveStatus'] = 'saved'; shots[0]['visual']['image']['status'] = 'saved'
    state = save(state, shots)
    handoff = {**v['handoff'], 'line': 'direct', 'expectedVideoRevision': state['revision']}
    state = service.create_creation_video_handoff(v['ctx'], v['variant'], handoff, idempotency_key=key())['video']
    job = claim(state['identity']['jobId'])
    runtime, descriptor, run_ref, inputs = photo(job)
    assert descriptor['shotImageInputs'][0]['shotId'] == '01'
    with patch.dict(sys.modules, {'media_common': photo_common}):
        created = runtime.create_run(job['pipeline_id'], job['pipeline_version'], job['catalog_digest'], run_ref=run_ref, inputs=inputs)
        assert created.status == 'created'
        result = runtime.execute(run_ref, inputs=inputs)
    assert result.status == 'succeeded', result
    receive(job, exchange.upload_outputs(remote, workspace, job, result, descriptor))
    state = service.get_creation_video(v['ctx'], v['variant'])['video']
    assert state['candidate']['status'] == 'candidate'
    assert remote.progress_receipts[-1]['waveformSource'] == 'narration'
    frame = workspace / run_ref / 'compose/render/01/frames/frame-000000.png'
    old_hash = adapter.file_sha256(frame); old_inode = frame.stat().st_ino
    old_segment_inode = (workspace / run_ref / 'compose/segments/01.mp4').stat().st_ino
    image_input = workspace / 'video-inputs' / job['job_id'] / 'shot-images/01.jpg'
    image_bytes = image_input.read_bytes(); image_input.write_bytes(image_bytes + b'?')
    try:
        with patch.dict(sys.modules, {'media_common': photo_common}):
            rejected = runtime.execute(run_ref, inputs=inputs)
        assert rejected.code == 'photo_image_digest_rejected'
    finally:
        image_input.write_bytes(image_bytes)
    old_posters = {s['shotId']: s['poster']['artifact']['sha256'] for s in state['shotProgress']}
    from contextlib import contextmanager
    class Gateway:
        @contextmanager
        def bind(self, *args, **kwargs): yield
    service.model_gateway = Gateway()
    from common.llm_settings import LLMProviderSettings
    monkeypatch.setattr('common.llm_settings.load_profile_llm_settings', lambda _: LLMProviderSettings(model='fixture', base_url='http://fixture.invalid', api_key='fixture-only', api_type='codex_responses', timeout=5))
    code = '<body style="background:yellow">confirmed replacement</body>'
    service.model_generate = lambda *args, **kwargs: {'code': code, 'durationSeconds': .25}
    pending = service.update_creation_video_overlay(v['ctx'], v['variant'], dict(action='ai_replace_image', expectedWorkRevision=state['workRevision'], expectedVideoRevision=state['revision'], animationId='animation_pf2'), idempotency_key=key())['video']
    assert pending['shots'] == state['shots']
    revision = pending['planRevision']
    state = service.update_creation_video_overlay(v['ctx'], v['variant'], dict(action='confirm_revision', expectedWorkRevision=pending['workRevision'], expectedVideoRevision=pending['revision'], planRevisionId=revision['publicRevisionId'], planRevisionDigest=revision['revisionDigest']), idempotency_key=key())['video']
    revised_job = claim(state['identity']['jobId'])
    runtime, descriptor, revised_ref, inputs = photo(revised_job)
    with patch.dict(sys.modules, {'media_common': photo_common}):
        result = runtime.render_video_revision(revised_ref, shot_ids=descriptor['renderShotIds'], previous_job_id=descriptor['previousJobId'], inputs=inputs)
    assert result.status == 'succeeded', result
    native = json.loads((workspace / revised_ref / 'native-compose.json').read_text())
    assert [s['attempts'] for s in native['shots']] == [1, 2]
    assert frame.stat().st_ino == old_inode and adapter.file_sha256(frame) == old_hash
    assert (workspace / revised_ref / 'compose/segments/01.mp4').stat().st_ino == old_segment_inode
    receive(revised_job, exchange.upload_outputs(remote, workspace, revised_job, result, descriptor))
    final = service.get_creation_video(v['ctx'], v['variant'])['video']
    assert final['candidate']['status'] == 'candidate'
    assert final['candidate']['animations'][0]['timeBasis'] == 'edited'
    assert final['candidate']['animations'][0]['durationSeconds'] == .25
    final_posters = {s['shotId']: s['poster']['artifact']['sha256'] for s in final['shotProgress']}
    assert final_posters['01'] == old_posters['01'] and final_posters['02'] != old_posters['02']
    for shot in final['shotProgress']:
        poster = shot['poster']; assert poster['source'] == 'code_render' and poster['shortEdge'] <= 360
        download = service.download(revised_job['job_id'], poster['artifact']['artifactId'], tenant_id=v['ctx'].tenant_id)
        assert download['artifact']['sha256'] == poster['artifact']['sha256']
    assert {p.name: adapter.file_sha256(p) for p in (source, project / 'voice.wav')} == original
    groups = {s['browser_pid'] for path in workspace.glob('runs/**/shot-status.json') for s in json.loads(path.read_text()).get('shots', []) if 'browser_pid' in s}
    for group in groups:
        assert not subprocess.run(['pgrep', '-g', str(group)], capture_output=True, text=True).stdout.strip()
    if os.getenv('PF_BROWSER_PID_LOG'):
        with open(os.environ['PF_BROWSER_PID_LOG'], 'a') as log:
            log.write(json.dumps({'test': 'pf2-service-e2e', 'owned_groups': sorted(groups), 'remaining': 0}) + '\n')
