"""The real Studio routes and installed watch share a durable project selection."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import subprocess
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
import test_p1a_installed_watch as watch
from test_p1a_installed_watch import installed, world  # noqa: F401

import media_ops.media_project_selection as selection
from studio.server import serve


ROOT = '/api/project-selections'


def read_request(**fields):
    return {
        'request_id': 'request_local',
        'public_variant_id': 'variant_local',
        'public_account_id': 'account_local',
        'public_session_id': 'session_local',
        'expected_work_revision': 3,
        'revision': 1,
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        **fields,
    }


@contextmanager
def studio(world):
    server = serve(state_dir=world.state_dir, port=0)
    thread = Thread(target=server.serve_forever)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    csrf = None

    def call(path, body=None):
        kwargs = {}
        if body is not None:
            kwargs = {'data': json.dumps(body).encode(), 'headers': {
                'Content-Type': 'application/json', 'X-Content-OS-CSRF': csrf, 'Origin': origin,
            }}
        try:
            with urlopen(Request(origin + path, **kwargs), timeout=5) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    try:
        csrf = call('/api/bootstrap')[1]['csrfToken']
        yield call
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def agent_port(world):
    inbox = selection.StudioConfirmationStore(selection.selection_root(world.media))
    return selection.StudioSelectionPort(world.store, device_id=watch.DEVICE, workspace=world.workspace,
                                         confirm=inbox.provider, media_root=world.media)


def test_project_id_is_kept_for_each_same_named_project_after_studio_restart(world, monkeypatch):
    anchor = datetime(2026, 11, 26, 3, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(selection, '_now', lambda: anchor)
    first = read_request(expires_at=(anchor + timedelta(minutes=15)).isoformat())
    second = read_request(request_id='request_local_two', expected_work_revision=4,
                          expires_at=(anchor + timedelta(minutes=16)).isoformat())
    port = agent_port(world)
    assert port.select_project(first) == port.select_project(second) == {'status': 'pending'}
    with studio(world) as call:
        status, inbox = call(ROOT)
        assert status == 200
        assert [item['requestId'] for item in inbox['requests']] == [second['request_id'], first['request_id']]
        assert inbox['requests'][1]['defaultTitle'] == '策划台作品 11-26 11:05'
        assert inbox['requests'][1]['workRevision'] == 3
        assert inbox['projects'][0]['updatedAt'] >= inbox['projects'][1]['updatedAt']
        assert world.project['title'] == world.twin['title']
        for item, project in ((first, world.project), (second, world.twin)):
            assert call(f"{ROOT}/{item['request_id']}/confirm", world.decision(project))[0] == 200
        assert call(f"{ROOT}/{first['request_id']}/confirm", world.decision(world.twin))[0] == 409
        assert call(ROOT)[1]['requests'] == []
    with studio(world) as call:
        port = agent_port(world)
        for item, project in ((first, world.project), (second, world.twin)):
            result = port.select_project(item)['local_selection']
            assert result['project_id'] == project['id']
            assert call(f"/api/projects/{project['id']}")[1]['planningSource'] == {
                'workRevision': item['expected_work_revision'],
            }


def test_double_submit_and_parallel_watch_create_one_project(world):
    item = read_request()
    assert agent_port(world).select_project(item) == {'status': 'pending'}
    decision = {'confirmed': True, 'selection_mode': 'created', 'title': '新项目'}
    with studio(world) as call, ThreadPoolExecutor(max_workers=2) as workers:
        path = f"{ROOT}/{item['request_id']}/confirm"
        assert list(workers.map(lambda _: call(path, decision)[0], range(2))) == [200, 200]
        results = list(workers.map(lambda _: agent_port(world).select_project(item), range(2)))
    assert results[0] == results[1]
    assert agent_port(world).select_project(item) == results[0]
    assert [p['id'] for p in world.store.list_projects() if p['title'] == '新项目'] == [
        results[0]['local_selection']['project_id'],
    ]


def test_expired_request_is_hidden_and_confirmation_is_rejected(world):
    item = read_request(expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())
    assert agent_port(world).select_project(item) == {'status': 'pending'}
    with studio(world) as call:
        assert call(ROOT)[1]['requests'] == []
        status, body = call(f"{ROOT}/{item['request_id']}/confirm", world.decision())
        assert status == 409
        assert body['error']['code'] == 'video_selection_expired'
        assert call(f"/api/projects/{world.project['id']}")[1]['planningSource'] is None


@pytest.mark.parametrize('contents', ['{', 'null'])
def test_damaged_request_is_a_read_failure(world, contents):
    item = read_request()
    port = agent_port(world)
    port.select_project(item)
    (port.root / 'pending' / f"{item['request_id']}.json").write_text(contents)
    with studio(world) as call:
        status, body = call(ROOT)
        assert status == 500
        assert body['error']['code'] == 'video_selection_store_invalid'


def test_installed_watch_confirms_the_real_studio_decision(installed, world, monkeypatch):
    # Reuse the installed-wheel harness and its Media/render doubles, without
    # supplying its confirmation substitute to the production CLI.
    # The project page probes the handed-off source, so give it a playable
    # synthetic clip. The older watch tests use placeholder bytes instead.
    source = world.store.local_workspace_path(world.twin['id']) / 'source.mp4'
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi',
                    '-i', 'color=c=black:s=32x32:r=30', '-t', '1', '-c:v', 'mpeg4', str(source)],
                   check=True, capture_output=True)
    call_with_double = 'wrapper.main(argv, confirmation_provider=provider)'
    assert watch._DRIVER.count(call_with_double) == 1
    monkeypatch.setattr(watch, '_DRIVER', watch._DRIVER.replace(call_with_double, 'wrapper.main(argv)'))
    started = world.watch(installed, cycles=1)
    assert started.returncode == 0, started.stderr
    assert world.lines('codes.jsonl') == ['video_selection_pending']
    with studio(world) as call:
        pending = call(ROOT)[1]['requests']
        assert [item['requestId'] for item in pending] == [world.request['request_id']]
        assert call(f"{ROOT}/{pending[0]['requestId']}/confirm", world.decision(world.twin))[0] == 200
        assert call(ROOT)[1]['requests'] == []
    confirmed = world.watch(installed, cycles=3)
    assert confirmed.returncode == 0, confirmed.stderr
    remote = world.remote()
    assert remote['consumed'] is True and len(remote['confirmations']) == 1
    assert remote['confirmations'][0]['project_id'] == world.twin['id']
    with studio(world) as call:
        status, project = call(f"/api/projects/{world.twin['id']}")
        assert status == 200, project
        assert project['planningSource']['workRevision'] == pending[0]['workRevision']
