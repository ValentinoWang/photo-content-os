"""R277 real loopback HTTP, isolated state and fake executable model."""
import json
import time
import pytest

from test_r276_direct_api import api, create
from test_r277_revisions import image_claude, ImageMedia
import llm_common


def idle(app):
    gen = app.direct_video.generator
    deadline = time.monotonic() + 10
    while gen.active and time.monotonic() < deadline:
        time.sleep(.01)
    assert not gen.active


def test_revision_routes_artifacts_samples_and_privacy(api, image_claude):
    request, csrf, pid, app, host = api
    app.direct_video.generator.model_call = llm_common.generate_text
    app.direct_video.generator.media = ImageMedia()
    base, job = create(api)
    shot = base + '/shots/01/'
    for method, suffix, body in [('POST', 'revise', {'lines': [{'text': '变灰', 'boxId': 'b3', 'action': 'dim'}]}),
                                 ('POST', 'current', {'version': 1}), ('POST', 'look', {}),
                                 ('PUT', 'sample', {}), ('DELETE', 'sample', {})]:
        assert request(shot + suffix, method, body)[0] == 403
        assert request(shot + suffix, method, body, {**csrf, 'Origin': 'http://127.0.0.1:1'})[0] == 403
    assert request(shot + 'revise', 'POST', {'lines': [{'text': '变灰', 'boxId': 'b3', 'action': 'dim'}]}, csrf)[0] == 200
    idle(app)
    status, _, payload = request(base)
    assert status == 200 and payload['job']['shots'][0]['currentVersion'] == 2
    assert [v['baseVersion'] for v in payload['job']['shots'][0]['versions']] == [None, 1]
    assert payload['job']['shots'][0]['versions'][1]['verify']['status'] == 'done'
    assert request(shot + 'poster.jpg?version=1')[0] == 200
    assert request(shot + 'poster.jpg?version=2')[2] != request(shot + 'poster.jpg?version=1')[2]
    old = request(shot + 'code?version=1')[2]
    assert request(shot + 'current', 'POST', {'version': 1}, csrf)[2]['job']['shots'][0]['currentVersion'] == 1
    assert request(shot + 'code')[2] == old
    assert request(shot + 'poster.jpg?version=999')[0] == 404
    assert request(shot + 'current', 'POST', {'version': True}, csrf)[0] == 404
    assert request(shot + 'current', 'POST', {'version': 999}, csrf)[2]['error']['code'] == 'version_not_found'
    assert request(shot + 'revise', 'POST', {'lines': [{'text': '字'*201, 'own': True}]}, csrf)[2]['error']['code'] == 'instruction_too_long'
    updated_at = request(base)[2]['job']['updatedAt']
    looked = request(shot + 'look', 'POST', {}, csrf)
    assert looked[0] == 200 and looked[2]['job']['updatedAt'] == updated_at
    idle(app)
    assert request(base)[2]['job']['updatedAt'] == updated_at
    sampled = request(shot + 'sample', 'PUT', {}, csrf)[2]['job']
    assert sampled['shots'][0]['sample'] and sampled['updatedAt'] == updated_at
    status, _, samples = request('/api/direct/samples')
    assert status == 200 and samples['samples'][0]['projectTitle'] == '合成测试'
    assert request(samples['samples'][0]['posterUrl'])[0] == 200
    assert str(app.store.state_dir) not in json.dumps(samples)
    assert request('/api/direct/samples?poster=../bad')[0] == 404
    unsampled = request(shot + 'sample', 'DELETE', {}, csrf)[2]['job']
    assert unsampled['shots'][0]['sample'] is False and unsampled['updatedAt'] == updated_at
    assert request('/api/direct/samples')[2]['samples'] == []
    assert request('/api/direct/unknown')[0] == 404
    assert request(shot + 'sample', 'POST', {}, csrf)[0] == 404
    assert request(shot + 'revise', 'PUT', {}, csrf)[0] == 404
    assert request(shot + 'revise', 'POST', {'lines': [{'text': '第三版', 'own': True}]}, csrf)[0] == 200
    idle(app)
    versions = request(base)[2]['job']['shots'][0]['versions']
    assert [v['version'] for v in versions] == [1, 2, 3]
    assert [v['baseVersion'] for v in versions] == [None, 1, 1]
    reverted = request(shot + 'current', 'POST', {'version': 2}, csrf)[2]['job']['shots'][0]
    assert reverted['versions'] == versions


def test_log_proposal_adopt_reject_http(api, image_claude):
    request, csrf, pid, app, host = api
    app.direct_video.generator.model_call = llm_common.generate_text
    app.direct_video.generator.media = ImageMedia()
    base, job = create(api)
    lines = [{'text': '柱子变灰', 'boxId': 'b3', 'action': 'dim'}]*3
    assert request(base + '/shots/01/revise', 'POST', {'lines': lines}, csrf)[0] == 200
    idle(app)
    log = request('/api/direct/revision-log')[2]
    assert log['rulesRevision'] == 0
    category = log['categories'][0]
    assert category['count'] == 3 and category['sources'][0]['projectTitle'] == '合成测试'
    proposal = category['proposals'][0]
    path = '/api/direct/rules/proposals/' + proposal['proposalId']
    for action in ('adopt', 'reject'):
        assert request(path + '/' + action, 'POST', {})[0] == 403
        assert request(path + '/' + action, 'POST', {}, {**csrf, 'Origin': 'http://evil.example'})[0] == 403
    assert request(path + '/adopt', 'POST', {}, csrf)[2]['proposal']['status'] == 'adopted'
    assert request('/api/direct/revision-log')[2]['rulesRevision'] == 1
    assert request(path + '/reject', 'POST', {}, csrf)[0] == 409
    assert request('/api/direct/rules/proposals/missing/adopt', 'POST', {}, csrf)[0] == 404
    assert request(base + '/shots/01/revise', 'POST', {'lines': lines}, csrf)[0] == 200
    idle(app)
    proposal = request('/api/direct/revision-log')[2]['categories'][0]['proposals'][1]
    path = '/api/direct/rules/proposals/' + proposal['proposalId'] + '/reject'
    assert request(path, 'POST', {}, csrf)[2]['proposal']['status'] == 'rejected'
    assert request('/api/direct/revision-log')[2]['categories'][0]['count'] == 6
