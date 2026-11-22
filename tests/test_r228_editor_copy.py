"""R228 editor preference projection and frontend regression gate."""
import hashlib
import http.client
import json
from pathlib import Path
import shutil
import subprocess
import threading
from http.server import ThreadingHTTPServer

import pytest

from studio.project_store import ProjectStore
from studio.server import StudioApplication


def test_editor_copy_frontend():
    subprocess.run([shutil.which('node'), str(Path(__file__).with_suffix('.mjs'))], check=True)


@pytest.fixture
def application(tmp_path):
    app = StudioApplication(ProjectStore(tmp_path / 'state'))
    project = app.store.create_project(title='校园')
    yield app, project['id']
    app.review_jobs.close()


def choice_path(app, identity):
    return app.settings_dir / 'video-editors' / (hashlib.sha256(identity.encode()).hexdigest() + '.json')


def test_catalog_choice_projection_and_live_update(application):
    app, identity = application
    def choice():
        return app.review_catalog_projection()['pieces'][0]['editorChoice']
    assert choice() == {'editor': 'otio_kdenlive', 'method': 'external', 'revision': 1}
    app.video_editor_choice(identity, {'editor': 'chatcut', 'revision': 1})
    assert choice()['editor'] == 'chatcut'
    assert str(app.settings_dir) not in json.dumps(app.review_catalog_projection())
    app.video_editor_choice(identity, {'editor': 'openfilm', 'revision': 2})
    assert choice()['editor'] == 'openfilm'


@pytest.mark.parametrize('raw', ['{', '[]', '{}', 'null', '{"editor":"other","revision":1}', '{"editor":"chatcut","revision":true}', '{"editor":"chatcut","revision":1,"method":"other"}'])
def test_unreadable_choice_not_default(application, raw):
    app, identity = application
    path = choice_path(app, identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw)
    item = app.review_catalog_projection()['pieces'][0]
    assert item['editorChoice'] == {'error': {'code': 'editor_choice_unreadable', 'message': '无法读取本机记录'}}
    assert item['title'] == '校园'
    assert str(path) not in json.dumps(item)


def test_catalog_does_not_reload_store_per_choice(application, monkeypatch):
    app, _ = application
    app.store.create_project(title='另一件作品')
    def unexpected(*args):
        pytest.fail('catalog choices must reuse the validated project list')
    monkeypatch.setattr(app.store, 'get_project', unexpected)
    assert len(app.review_catalog_projection()['pieces']) == 2


def test_choice_projection_excludes_private_extra_keys(application):
    app, identity = application
    path = choice_path(app, identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'editor': 'chatcut', 'revision': 1, 'localPath': str(app.settings_dir)}))
    assert app.review_catalog_projection()['pieces'][0]['editorChoice'] == {'editor': 'chatcut', 'method': 'external', 'revision': 1}


def test_unreadable_choice_directory_and_broken_link(application):
    app, identity = application
    path = choice_path(app, identity)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    assert 'error' in app.review_catalog_projection()['pieces'][0]['editorChoice']
    path.rmdir()
    path.symlink_to(path.parent / 'absent')
    assert 'error' in app.review_catalog_projection()['pieces'][0]['editorChoice']


def test_catalog_http_exposes_choice(application):
    app, identity = application
    app.video_editor_choice(identity, {'editor': 'chatcut', 'revision': 1})
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection(*server.server_address)
        conn.request('GET', '/api/review/catalog')
        response = conn.getresponse()
        data = json.loads(response.read())
        conn.close()
        assert response.status == 200
        assert data['pieces'][0]['editorChoice']['editor'] == 'chatcut'
        assert str(app.settings_dir) not in json.dumps(data)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
