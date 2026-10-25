"""HTTP integration on an ephemeral port, with isolated synthetic state."""
from __future__ import annotations

import http.client
import json
from pathlib import Path
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from studio.server import serve
from test_r276_direct_video import FakeMedia, FakeModel, wav


@pytest.fixture
def api(tmp_path):
    server = serve(state_dir=tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # serve exposes its application through its Handler closure.
    app = next(cell.cell_contents for cell in server.RequestHandlerClass._write_request.__closure__ if hasattr(cell.cell_contents, 'direct_video'))
    app.direct_video.generator.model_call = FakeModel()
    app.direct_video.generator.media = FakeMedia()
    host = f'127.0.0.1:{server.server_address[1]}'
    def request(path, method='GET', body=None, headers=None):
        connection = http.client.HTTPConnection(host, timeout=10)
        data = json.dumps(body).encode() if isinstance(body, dict) else body
        final_headers = {'Host': host, 'Content-Type': 'application/json', **(headers or {})}
        connection.request(method, path, data, final_headers)
        response = connection.getresponse()
        raw = response.read()
        result = (response.status, dict(response.getheaders()), json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw)
        connection.close()
        return result
    _, _, bootstrap = request('/api/bootstrap')
    csrf = {'X-Content-OS-CSRF': bootstrap['csrfToken']}
    _, _, created = request('/api/projects', 'POST', {'title': '合成测试'}, csrf)
    pid = created['project']['id']
    yield request, csrf, pid, app, host
    deadline = time.monotonic() + 10
    while app.direct_video.generator.active and time.monotonic() < deadline:
        time.sleep(.01)
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def create(api):
    request, csrf, pid, app, _ = api
    base = f'/api/projects/{pid}/direct/jobs'
    status, _, result = request(base, 'POST', {'script': '第一句。\n第二句。'}, csrf)
    assert status == 201
    job_id = result['job']['jobId']
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        _, _, state = request(base + '/' + job_id)
        if state['job']['status'] in {'ready', 'failed'}:
            break
        time.sleep(.01)
    assert state['job']['status'] == 'ready'
    return base + '/' + job_id, state['job']


def test_routes_csrf_origin_and_validation(api):
    request, csrf, pid, app, host = api
    base = f'/api/projects/{pid}/direct/jobs'
    assert request(base + '/latest')[2] == {'ok': True, 'job': None}
    assert request(base, 'POST', {'script': '一句话。'})[0] == 403
    for origin in ['https://evil.example', 'http://127.0.0.1:1', 'http://localhost:' + host.rsplit(':', 1)[1]]:
        assert request(base, 'POST', {'script': '一句话。'}, {**csrf, 'Origin': origin})[0] == 403
    assert request(base + '/unexpected/unknown')[0] == 404
    assert request(base + '/unexpected/unknown', 'POST', {}, csrf)[0] == 404
    assert request(base, 'POST', {'script': '话', 'model': 'other'}, csrf)[0] == 400
    assert request(base, 'POST', {'script': '话', 'storyboard': {}}, csrf)[0] == 400
    path, job = create(api)
    assert request(base + '/latest')[2]['job']['jobId'] == job['jobId']
    assert request(path + '/shots/01/rewrite', 'POST', {'instruction': ''}, csrf)[0] == 400
    assert request(path + '/shots/01/rewrite', 'POST', {'instruction': '字'*201}, csrf)[0] == 400
    assert request(path + '/shots/nope/code')[0] == 404
    assert request(path + '/shots/%2E%2E/code')[0] == 404
    assert request(path.replace(pid, 'missing'))[0] in {400, 404}
    assert str(app.store.state_dir) not in json.dumps(request(path)[2])


def test_code_posters_output_range_and_missing(api):
    request, csrf, pid, app, _ = api
    path, job = create(api)
    status, headers, code = request(path + '/shots/01/code')
    assert status == 200 and headers['Content-Type'] == 'text/plain; charset=utf-8'
    assert code.startswith(b'<!doctype html>')
    assert request(path + '/shots/01/poster.jpg')[0] == 200
    assert request(path + '/output.mp4')[0] == 409
    assert request(path + '/compose', 'POST', {}, csrf)[0] == 200
    deadline = time.monotonic() + 5
    while app.direct_video.generator.active and time.monotonic() < deadline:
        time.sleep(.01)
    assert request(path + '/output.mp4')[2] == b'synthetic-video'
    status, headers, data = request(path + '/output.mp4', headers={'Range': 'bytes=0-3'})
    assert status == 206 and data == b'synt' and headers['Content-Range'] == 'bytes 0-3/15'
    assert request(path + '/output.mp4', headers={'Range': 'bytes=-5'})[2] == b'video'
    assert request(path + '/output.mp4', headers={'Range': 'bytes=10-'})[2] == b'video'
    for value in ['bytes=999-', 'bytes=0-1,3-4', 'bytes=-0', 'bytes=5-1']:
        assert request(path + '/output.mp4', headers={'Range': value})[0] == 416


def test_binary_narration_and_rewrite(api):
    request, csrf, pid, app, _ = api
    path, job = create(api)
    assert request(path + '/narration', 'POST', b'bad', {**csrf, 'Content-Type': 'audio/wav'})[0] == 400
    assert request(path + '/narration', 'POST', wav(), csrf)[0] == 400
    assert request(path + '/narration', 'POST', wav(), {**csrf, 'Content-Type': 'audio/wav'})[0] == 200
    deadline = time.monotonic() + 5
    while app.direct_video.generator.active and time.monotonic() < deadline:
        time.sleep(.01)
    result = request(path)[2]['job']
    assert result['narration']['status'] == 'ready'
    assert all(s['timingSource'] == 'proportional' for s in result['shots'])
    untouched = result['shots'][1]
    assert request(path + '/shots/01/rewrite', 'POST', {'instruction': '放大'}, csrf)[0] == 200
    deadline = time.monotonic() + 5
    while app.direct_video.generator.active and time.monotonic() < deadline:
        time.sleep(.01)
    assert request(path)[2]['job']['shots'][1] == untouched


def test_openapi_projection_matches_real_job(api):
    from studio.api_contract import build_openapi
    import jsonschema
    request, csrf, pid, app, _ = api
    path, job = create(api)
    contract = build_openapi()
    schema = contract['components']['schemas']['DirectJob']
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(job, schema)
    spec = contract['paths']['/api/projects/{projectId}/direct/jobs']
    assert '201' in spec['post']['responses']
    audio = contract['paths']['/api/projects/{projectId}/direct/jobs/{jobId}/narration']['post']
    assert set(audio['requestBody']['content']) == {'audio/wav'}
