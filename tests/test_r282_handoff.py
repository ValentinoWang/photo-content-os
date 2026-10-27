"""Identity-bound direct handoff contracts; synthetic files and model/media doubles."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from test_r276_direct_api import api
from test_r276_direct_video import wav
from test_r278_style_base import idle
from studio.api_contract import build_openapi
from studio.direct_video import projection


@pytest.fixture
def handoff(api, tmp_path, monkeypatch):
    request, csrf, pid, app, _ = api
    media = tmp_path / 'media'
    media.mkdir()
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(media))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_WORKSPACE', str(media))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING', '')
    project = app.store.connect_workspace(pid, str(media))
    descriptor = {'scope': 'video_handoff_v1', 'identity': {'jobId': 'job_handoff',
        'photoProjectId': pid, 'photoProjectRevision': project['revision'], 'workRevision': 70},
        'storyboardRevision': 7, 'handedAt': '2026-10-27T00:00:00Z',
        'shots': [{'shot': {'shotId': '01', 'startSeconds': 0, 'endSeconds': 1},
                   'visual': {'text': '画一条线', 'image': {'source': 'source_frame', 'rightsStatus': 'pending', 'sourceTimeSeconds': 3}},
                   'dialogue': '第一句。', 'subtitle': '字', 'camera': '近景', 'audio': '轻音'},
                  {'shot': {'shotId': '02', 'startSeconds': 1, 'endSeconds': 2},
                   'visual': {'text': '画第二条线', 'image': {'source': 'code_render', 'rightsStatus': 'confirmed'}},
                   'dialogue': '第二句。', 'subtitle': '', 'camera': '', 'audio': ''}],
        'animations': [], 'narration': None, 'mxHandoff': {'tts_ref': None}, 'documentRef': {'revision': 3}}
    path = media / 'video.json'
    def write():
        path.write_text(json.dumps(descriptor, ensure_ascii=False))
    write()
    return api, media, descriptor, write


def get(handoff):
    api, _, _, _ = handoff
    request, _, pid, _, _ = api
    status, _, body = request(f'/api/projects/{pid}/direct/handoff')
    assert status == 200
    return body['handoff']


def test_projection_columns_local_image_and_read_only(handoff):
    api, media, descriptor, write = handoff
    request, _, pid, app, _ = api
    images = media / 'video-inputs/job_handoff/shot-images'
    images.mkdir(parents=True)
    (images / '01.jpg').write_bytes(b'\xff\xd8\xffsynthetic')
    before = {p: p.read_bytes() for p in media.rglob('*') if p.is_file()}
    value = get(handoff)
    assert value['jobId'] == 'job_handoff' and value['revision'] == 7
    assert value['title'] == app.store.get_project(pid)['title']
    assert value['handedAt'] == descriptor['handedAt']
    shot = value['shots'][0]
    assert {k: shot[k] for k in ('shotId', 'startSeconds', 'endSeconds', 'dialogue', 'visual', 'subtitle', 'camera', 'audio')} == {
        'shotId': '01', 'startSeconds': 0, 'endSeconds': 1, 'dialogue': '第一句。', 'visual': '画一条线',
        'subtitle': '字', 'camera': '近景', 'audio': '轻音'}
    assert shot['image']['sourceTimeSeconds'] == 3 and shot['image']['rightsStatus'] == 'pending'
    url = shot['image']['url']
    assert url.startswith(f'/api/projects/{pid}/direct/handoff/images/01?v=')
    assert request(url)[2] == b'\xff\xd8\xffsynthetic'
    assert value['shots'][1]['image']['url'] is None
    (images / '01.jpg').unlink()
    assert request(url)[0] == 404
    assert get(handoff)['shots'][0]['image']['url'] is None
    assert (media / 'video.json').read_bytes() == before[media / 'video.json']


@pytest.mark.parametrize('change', ['project', 'revision', 'scope', 'broken', 'identity', 'traversal'])
def test_invalid_inputs_match_video_projection(handoff, change):
    api, media, descriptor, write = handoff
    if change == 'project': descriptor['identity']['photoProjectId'] = 'other-project'
    if change == 'revision': descriptor['identity']['photoProjectRevision'] += 1
    if change == 'scope': descriptor['scope'] = 'wrong'
    if change == 'identity': descriptor['identity'] = []
    if change == 'traversal': descriptor['identity']['jobId'] = '..'
    write()
    if change == 'broken': (media / 'video.json').write_text('{')
    assert get(handoff) is None
    assert api[3]._video_handoff_projection(api[2]) is None


def test_bound_descriptor_and_canonical_revision(handoff, monkeypatch, tmp_path):
    api, media, descriptor, write = handoff
    _, _, pid, app, _ = api
    bound = media / 'video-inputs/job_handoff/video.json'
    bound.parent.mkdir(parents=True)
    bound.write_bytes((media / 'video.json').read_bytes())
    binding = tmp_path / 'binding.json'
    binding.write_text(json.dumps({'identity': {'project_id': pid, 'project_revision': 2, 'job_id': 'job_handoff'},
                                  'project_root': str(media), 'creative_store': str(app.store.path)}))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING', str(binding))
    descriptor['scope'] = 'wrong'
    write()
    assert get(handoff)['revision'] == 7
    app.store.update_project(pid, {'title': '改名'}, expected_revision=2)
    assert get(handoff) is None


def test_external_image_symlink_not_served(handoff, tmp_path):
    _, media, _, _ = handoff
    images = media / 'video-inputs/job_handoff/shot-images'
    images.mkdir(parents=True)
    outside = tmp_path / 'outside.jpg'
    outside.write_bytes(b'private')
    (images / '01.jpg').symlink_to(outside)
    assert get(handoff)['shots'][0]['image']['url'] is None


@pytest.mark.parametrize('reference', [{'jobId': 'job_handoff', 'revision': 6},
                                     {'jobId': 'other', 'revision': 7}, None, {'jobId': 'job_handoff', 'revision': True}])
def test_create_rejects_changed_handoff_before_work(handoff, reference):
    api, _, _, _ = handoff
    request, csrf, pid, app, _ = api
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST',
                              {'script': '一句话', 'style': '浅色', 'handoff': reference}, csrf)
    assert status == 409 and body['error']['code'] == 'handoff_changed'
    assert app.direct_video.generator.latest(pid) is None


def test_handoff_narration_alignment_shortening_and_composition(handoff):
    api, media, descriptor, write = handoff
    request, csrf, pid, app, _ = api
    audio = media / 'video-inputs/job_handoff/narration.wav'
    audio.parent.mkdir(parents=True)
    audio.write_bytes(wav(.4))
    descriptor['narration'] = {'voiceId': 'Cherry', 'durationSeconds': .4, 'status': 'ready'}
    descriptor['mxHandoff']['tts_ref'] = str(audio.relative_to(media))
    # Long initial animations must go through the same shortening path as upload.
    descriptor['shots'][0]['dialogue'] = '第一句话很长很长。'
    descriptor['shots'][1]['dialogue'] = '第二句话也很长很长。'
    write()
    assert get(handoff)['narration'] == {'voice': 'Cherry', 'durationSeconds': .4}
    gen = app.direct_video.generator
    gen.media.transcript = {'words': [{'text': descriptor['shots'][0]['dialogue'], 'start': 0, 'end': .2},
                                      {'text': descriptor['shots'][1]['dialogue'], 'start': .2, 'end': .4}]}
    original_transcribe = gen.media.transcribe
    gen.media.transcribe = Mock(side_effect=original_transcribe)
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST', {
        'storyboard': {'shots': [{'shotId': r['shot']['shotId'], 'dialogue': r['dialogue']} for r in descriptor['shots']]},
        'style': '浅色', 'handoff': {'jobId': 'job_handoff', 'revision': 7}}, csrf)
    assert status == 201
    jid = body['job']['jobId']
    idle(gen)
    job = request(f'/api/projects/{pid}/direct/jobs/{jid}')[2]['job']
    assert job['handoff'] == {'jobId': 'job_handoff', 'revision': 7}
    assert job['handoffNewer'] is False
    assert job['narration'] == {'status': 'ready', 'durationSeconds': .4}
    assert all(s['timingSource'] == 'narration' and s['measuredSeconds'] == .2 for s in job['shots'])
    assert len([c for c in gen.model_call.calls if c.get('instruction')]) == 2
    gen.media.transcribe.assert_called_once()
    assert (gen.path(pid, jid) / 'narration.wav').read_bytes() == audio.read_bytes()
    assert request(f'/api/projects/{pid}/direct/jobs/{jid}/compose', 'POST', {}, csrf)[0] == 200
    idle(gen)
    assert gen.media.composed[-1]['output']['kind'] == 'narrated'
    descriptor['storyboardRevision'] = 8
    write()
    assert request(f'/api/projects/{pid}/direct/jobs/{jid}')[2]['job']['handoffNewer'] is True


def test_missing_handoff_audio_blocks_instead_of_silent_output(handoff):
    api, _, descriptor, write = handoff
    request, csrf, pid, app, _ = api
    descriptor['narration'] = {'voiceId': 'Cherry', 'durationSeconds': 1}
    descriptor['mxHandoff']['tts_ref'] = 'video-inputs/job_handoff/missing.wav'
    write()
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST', {'script': '一句话', 'style': '浅色',
        'handoff': {'jobId': 'job_handoff', 'revision': 7}}, csrf)
    assert status == 400 and body['error']['code'] == 'narration_invalid'
    assert app.direct_video.generator.latest(pid) is None


@pytest.mark.parametrize(('bound', 'handed', 'expected'), [
    ({'jobId': 'old', 'revision': 6}, None, True),
    ({'jobId': 'old', 'revision': 7}, '2026-10-28T00:00:00Z', False),
    (None, '2026-10-27T00:00:01Z', True),
    (None, '2026-10-27T08:00:00+08:00', False),
    (None, None, False), (None, 'bad', False),
])
def test_newer_handoff_conditions(handoff, bound, handed, expected):
    api, _, _, _ = handoff
    gen, pid = api[3].direct_video.generator, api[2]
    job = gen.create(pid, {'script': '一句话', 'style': '浅色'}, background=False)
    job.update(handoff=bound, createdAt='2026-10-27T00:00:00Z')
    current = {'jobId': 'new', 'revision': 7, 'handedAt': handed}
    assert projection(job, current_handoff=current)['handoffNewer'] is expected


def test_openapi_handoff_contract():
    contract = build_openapi()
    paths = contract['paths']
    base = '/api/projects/{projectId}/direct/handoff'
    assert 'get' in paths[base]
    assert 'get' in paths[base + '/images/{shotId}']
    create = paths['/api/projects/{projectId}/direct/jobs']['post']
    assert 'handoff' in create['requestBody']['content']['application/json']['schema']['properties']
    assert '409' in create['responses']
    assert {'handoff', 'handoffNewer'} <= contract['components']['schemas']['DirectJob']['properties'].keys()
    assert json.loads((Path(__file__).resolve().parents[1] / 'schemas/studio-openapi.json').read_text()) == contract


def test_create_handoff_without_audio_and_frozen_source(handoff):
    api, _, descriptor, write = handoff
    request, csrf, pid, app, _ = api
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST', {
        'script': '本机改过的台词。', 'style': '浅色', 'handoff': {'jobId': 'job_handoff', 'revision': 7}}, csrf)
    assert status == 201
    idle(app.direct_video.generator)
    jid = body['job']['jobId']
    descriptor['storyboardRevision'] = 8
    descriptor['shots'][0]['dialogue'] = '中台后来改的。'
    write()
    job = request(f'/api/projects/{pid}/direct/jobs/{jid}')[2]['job']
    assert job['handoff'] == {'jobId': 'job_handoff', 'revision': 7}
    assert job['shots'][0]['dialogue'] == '本机改过的台词。'
    assert job['narration']['status'] == 'none' and job['handoffNewer'] is True


@pytest.mark.parametrize('fault', ['invalid-wav', 'symlink', 'traversal', 'malformed-mx'])
def test_unusable_narration_never_starts_job(handoff, tmp_path, fault):
    api, media, descriptor, write = handoff
    request, csrf, pid, app, _ = api
    descriptor['narration'] = {'voiceId': 'Cherry', 'durationSeconds': 1}
    audio = media / 'video-inputs/job_handoff/narration.wav'
    audio.parent.mkdir(parents=True)
    descriptor['mxHandoff']['tts_ref'] = str(audio.relative_to(media))
    if fault == 'invalid-wav': audio.write_bytes(b'not-a-wav')
    elif fault == 'symlink':
        outside = tmp_path / 'outside.wav'
        outside.write_bytes(wav())
        audio.symlink_to(outside)
    elif fault == 'traversal': descriptor['mxHandoff']['tts_ref'] = '../outside.wav'
    else: descriptor['mxHandoff'] = None
    write()
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST', {'script': '一句话', 'style': '浅色',
        'handoff': {'jobId': 'job_handoff', 'revision': 7}}, csrf)
    assert status == 400 and body['error']['code'] == 'narration_invalid'
    assert app.direct_video.generator.latest(pid) is None


def test_get_missing_project_and_unreadable_descriptor_return_null(handoff, monkeypatch):
    api, media, _, _ = handoff
    request, _, _, _, _ = api
    assert request('/api/projects/missing-project/direct/handoff')[2]['handoff'] is None
    original = Path.read_text
    def denied(path, *args, **kwargs):
        if path == media / 'video.json':
            raise PermissionError('synthetic denied')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', denied)
    assert get(handoff) is None


def test_job_poll_does_not_read_images_or_scan_other_handoffs(handoff, monkeypatch):
    api, media, _, _ = handoff
    request, _, pid, app, _ = api
    gen = app.direct_video.generator
    job = gen.create(pid, {'script': '一句话', 'style': '浅色'}, background=False)
    from studio import direct_handoff_contract
    calls, reads = [], []
    original = Path.read_bytes
    original_json = direct_handoff_contract.read_json
    def observed(path):
        calls.append(path)
        return original(path)
    def observed_json(root, ref):
        reads.append((root, ref))
        return original_json(root, ref)
    monkeypatch.setattr(Path, 'read_bytes', observed)
    monkeypatch.setattr(direct_handoff_contract, 'read_json', observed_json)
    route = f'/api/projects/{pid}/direct/jobs/{job["jobId"]}'
    assert request(route)[0] == 200
    baseline = list(reads)
    reads.clear()
    for n in range(10):
        path = media / f'video-inputs/other-job-{n}/video.json'
        path.parent.mkdir(parents=True)
        path.write_text('{bad')
    assert request(route)[0] == 200
    assert reads == baseline and len(reads) == 1
    assert calls == []


@pytest.mark.parametrize(('fields', 'revision', 'handed'), [
    ({'storyboardRevision': 9, 'handedAt': '2026-10-27T01:02:03.123Z'}, 9, '2026-10-27T01:02:03.123Z'),
    ({'storyboardRevision': 1, 'handedAt': '2026-10-27T01:02:03+00:00'}, 1, '2026-10-27T01:02:03+00:00'),
    ({}, None, None),
    ({'storyboardRevision': 8}, 8, None),
    ({'handedAt': '2026-10-27T01:02:03Z'}, None, '2026-10-27T01:02:03Z'),
    ({'storyboardRevision': '8', 'handedAt': 'not-a-time'}, None, None),
    ({'storyboardRevision': '8', 'handedAt': '2026-10-27T01:02:03Z'}, None, '2026-10-27T01:02:03Z'),
    ({'storyboardRevision': 8, 'handedAt': 'not-a-time'}, 8, None),
    ({'storyboardRevision': True, 'handedAt': '2026-02-30T01:02:03Z'}, None, None),
    ({'storyboardRevision': 0, 'handedAt': '2026-10-27T01:02:03'}, None, None),
    ({'storyboardRevision': -1, 'handedAt': '2026-10-27T09:02:03+08:00'}, None, None),
    ({'storyboardRevision': 1.5, 'handedAt': []}, None, None),
    ({'storyboardRevision': None, 'handedAt': '2026-10-27'}, None, None),
    ({'storyboardRevision': [], 'handedAt': '2026-10-27 01:02:03Z'}, None, None),
])
def test_supplement_optional_metadata_keeps_package_usable(handoff, fields, revision, handed):
    _, _, descriptor, write = handoff
    descriptor.pop('storyboardRevision')
    descriptor.pop('handedAt')
    descriptor.update(fields)
    write()
    value = get(handoff)
    assert value is not None
    assert value['revision'] == revision and value['handedAt'] == handed
    assert len(value['shots']) == 2 and value['shots'][0]['dialogue'] == '第一句。'


@pytest.mark.parametrize(('package_revision', 'submitted_revision', 'job_id', 'expected_status'), [
    (None, None, 'job_handoff', 201),
    (7, None, 'job_handoff', 201),
    (None, None, 'different-job', 409),
    (None, 7, 'job_handoff', 409),
    (7, 6, 'job_handoff', 409),
    (7, True, 'job_handoff', 409),
    (7, '7', 'job_handoff', 409),
])
def test_supplement_nullable_revision_creation(handoff, package_revision, submitted_revision, job_id, expected_status):
    api, _, descriptor, write = handoff
    request, csrf, pid, app, _ = api
    if package_revision is None:
        descriptor.pop('storyboardRevision')
        descriptor.pop('handedAt')
    else:
        descriptor['storyboardRevision'] = package_revision
    write()
    reference = {'jobId': job_id, 'revision': submitted_revision}
    status, _, body = request(f'/api/projects/{pid}/direct/jobs', 'POST', {
        'script': '本机的台词。', 'style': '浅色', 'handoff': reference}, csrf)
    assert status == expected_status
    if status == 409:
        assert body['error']['code'] == 'handoff_changed'
        assert app.direct_video.generator.latest(pid) is None
    else:
        idle(app.direct_video.generator)
        job = request(f'/api/projects/{pid}/direct/jobs/{body["job"]["jobId"]}')[2]['job']
        assert job['handoff'] == reference


@pytest.mark.parametrize(('bound_revision', 'current_revision', 'handed', 'created', 'expected'), [
    (None, 7, '2026-10-27T00:00:01Z', '2026-10-27T00:00:00Z', True),
    (6, None, '2026-10-27T00:00:01Z', '2026-10-27T00:00:00Z', True),
    (None, None, '2026-10-27T00:00:01Z', '2026-10-27T00:00:00Z', True),
    (None, None, '2026-10-27T00:00:00Z', '2026-10-27T00:00:00Z', False),
    (None, 7, None, '2026-10-27T00:00:00Z', False),
    (6, None, '2026-10-27T00:00:01Z', None, False),
    (6, 7, None, None, True),
    (7, 7, '2026-10-28T00:00:00Z', '2026-10-27T00:00:00Z', False),
])
def test_supplement_newer_uses_time_when_either_revision_unknown(bound_revision, current_revision, handed, created, expected):
    from studio.direct_handoff_contract import newer_handoff
    job = {'handoff': {'jobId': 'old', 'revision': bound_revision}, 'createdAt': created}
    current = {'jobId': 'new', 'revision': current_revision, 'handedAt': handed}
    assert newer_handoff(job, current) is expected


def test_supplement_newer_fallback_in_job_endpoint(handoff):
    api, _, descriptor, write = handoff
    request, _, pid, app, _ = api
    job = app.direct_video.generator.create(pid, {'script': '一句话。', 'style': '浅色'}, background=False)
    job.update(handoff={'jobId': 'old', 'revision': None}, createdAt='2026-10-26T00:00:00Z')
    app.direct_video.generator.save(app.direct_video.generator.path(pid, job['jobId']), job)
    descriptor.pop('storyboardRevision')
    write()
    assert request(f'/api/projects/{pid}/direct/jobs/{job["jobId"]}')[2]['job']['handoffNewer'] is True
    descriptor.pop('handedAt')
    write()
    assert request(f'/api/projects/{pid}/direct/jobs/{job["jobId"]}')[2]['job']['handoffNewer'] is False


def test_supplement_openapi_allows_nullable_revision():
    contract = build_openapi()
    create = contract['paths']['/api/projects/{projectId}/direct/jobs']['post']
    reference = create['requestBody']['content']['application/json']['schema']['properties']['handoff']
    assert reference['properties']['revision']['type'] == ['integer', 'null']
    job_ref = contract['components']['schemas']['DirectJob']['properties']['handoff']['anyOf'][0]
    assert job_ref['properties']['revision']['type'] == ['integer', 'null']
    response = contract['paths']['/api/projects/{projectId}/direct/handoff']['get']['responses']['200']
    assert response['content']['application/json']['schema']['properties']['handoff']['properties']['revision']['type'] == ['integer', 'null']
