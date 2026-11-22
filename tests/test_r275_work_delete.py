"""R275 G1–G4: temporary workspaces and an injected, recoverable trash."""
import copy
import http.client
import json
import os
import shutil
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from studio.media_review import MediaReview
from studio.project_store import ProjectStore, ProjectStoreError
from studio.server import StudioApplication


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


class FakeTrash:
    def __init__(self, root):
        self.root = root
        self.failed = set()
        self.calls = []

    def move(self, source):
        self.calls.append(source)
        if source.name in self.failed:
            raise OSError('injected move failure')
        self.root.mkdir(exist_ok=True)
        destination = self.root / (str(len(self.calls)) + '-' + source.name)
        source.rename(destination)
        return {'id': destination.name, 'path': str(destination)}

    def location(self, receipt):
        return Path(receipt['path'])

    def restore(self, receipt, destination):
        source = self.location(receipt)
        if not source.exists():
            raise FileNotFoundError(source)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)


@pytest.fixture
def env(tmp_path, monkeypatch):
    media = tmp_path / 'media'
    media.mkdir()
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(media))
    monkeypatch.setenv('MUSIC_LIBRARY_ROOT', str(tmp_path / 'music'))
    store = ProjectStore(tmp_path / 'state')
    backend = FakeTrash(tmp_path / 'trash')
    store.work_trash_backend = backend
    return store, backend, media


def work(env, name='work', *, root=None, items=None, pending=False):
    store, _, media = env
    root = root or media / name
    root.mkdir(parents=True, exist_ok=True)
    (root / 'notes.txt').write_bytes(b'local notes\n')
    if items is not None:
        put(root / 'ai-analysis/media-manifest.json', {'items': items})
    if pending:
        put(root / 'ai-analysis/shots/shots.json', {
            'shots': [{'id': 'S1', 'kind': 'video', 'scene': 'travel', 'source_relative_path': 'clip.mp4',
                       'start_sec': 0, 'duration_sec': 3, 'frames': [], 'status': 'selected'}],
            'run_status': 'complete', 'hook_candidates': []})
    return store.create_project(title='同名作品', local_workspace=str(root)), root


def delete(env, projects, move=False, **kwargs):
    store, _, _ = env
    return store.delete_projects([p['id'] for p in projects],
                                 expected_revisions={p['id']: p['revision'] for p in projects},
                                 move_folders=move, **kwargs)


def restore(env, result):
    return env[0].restore_projects(**result['undo'])


def test_g1_hidden_everywhere_restore_preserves_documents_audit_and_folder_bytes(env):
    store, _, media = env
    parent = media / 'group'
    put(parent / 'project-manifest.json', {'title': '原项目'})
    p, folder = work(env, root=parent / 'work', pending=True)
    before = copy.deepcopy(store.get_project(p['id']))
    files = {f.relative_to(folder): f.read_bytes() for f in folder.rglob('*') if f.is_file()}
    review = MediaReview(store)
    assert review.catalog()['pieces'][0]['pending']
    result = delete(env, [p])
    assert result['succeeded'] == 1 and result['failed'] == 0
    assert store.list_projects() == []
    assert review.catalog() == {'pieces': [], 'groups': []}
    with pytest.raises(ProjectStoreError, match='project_not_found'):
        store.get_project(p['id'])
    with pytest.raises(ProjectStoreError, match='project_not_found'):
        store.local_workspace_path(p['id'])
    with pytest.raises(ProjectStoreError, match='project_not_found'):
        store.update_project(p['id'], {'title': 'cannot edit deleted'})
    recent = store.deleted_projects()
    assert recent[0]['group_title'] == '原项目'
    assert recent[0]['folder_name'] == folder.name and recent[0]['folder_status'] == 'original'
    assert restore(env, result)['succeeded'] == 1
    after = store.get_project(p['id'])
    assert after['documents'] == before['documents'] and after['audit'] == before['audit']
    assert {k: v for k, v in after.items() if k != 'revision'} == {k: v for k, v in before.items() if k != 'revision'}
    assert {f.relative_to(folder): f.read_bytes() for f in folder.rglob('*') if f.is_file()} == files
    assert review.catalog()['pieces'][0]['pending']
    assert review.catalog()['groups'][0]['title'] == '原项目'


@pytest.mark.parametrize('case,code', [
    ('video', 'folder_has_media'), ('photo', 'folder_has_media'),
    ('manifest', 'folder_formal_project'), ('outside', 'folder_outside_media_root'),
    ('symlink', 'folder_symlink'), ('inside_symlink', 'folder_symlink'),
    ('shared', 'folder_shared'), ('deleted_shared', 'folder_shared'),
    ('child', 'folder_contains_work'), ('root', 'folder_is_media_root'),
])
def test_g2_unsafe_folder_refused_without_any_mutation(env, tmp_path, case, code):
    store, backend, media = env
    root = tmp_path / 'outside' if case == 'outside' else media if case == 'root' else media / 'work'
    p, folder = work(env, root=root, items=[{'media_type': 'image' if case == 'photo' else 'video'}] if case in ('video', 'photo') else None)
    if case == 'manifest':
        put(folder / 'project-manifest.json', {'title': '正式项目'})
    if case == 'inside_symlink':
        (folder / 'link').symlink_to(folder / 'notes.txt')
    if case == 'symlink':
        # Older records may retain a symlink path; create/connect otherwise resolve it.
        alias = media / 'alias'; alias.symlink_to(folder, target_is_directory=True)
        with store._transaction() as data:
            data['projects'][0]['local_workspace']['local_path'] = str(alias)
    if case in ('shared', 'deleted_shared'):
        other = store.create_project(title='另一个', local_workspace=str(folder))
        if case == 'deleted_shared':
            delete(env, [other])
    if case == 'child':
        work(env, root=folder / 'child')
    before = store.path.read_bytes()
    result = delete(env, [p], True)
    assert result['results'][0]['code'] == code and result['failed'] == 1
    assert store.get_project(p['id'])['revision'] == p['revision']
    assert (folder / 'notes.txt').read_bytes() == b'local notes\n'
    assert not backend.calls
    # Only the store-wide CAS revision may advance on a failed batch.
    a, b = json.loads(before), json.loads(store.path.read_bytes())
    assert a['projects'] == b['projects']


def test_g3_batch_failure_isolated_and_undo_only_contains_successes(env):
    store, backend, _ = env
    projects = [work(env, name)[0] for name in ('first', 'failure', 'last')]
    backend.failed.add('failure')
    result = delete(env, projects, True)
    assert [r['ok'] for r in result['results']] == [True, False, True]
    assert result['results'][1]['code'] == 'folder_trash_failed'
    assert (result['succeeded'], result['failed']) == (2, 1)
    assert [p['id'] for p in store.list_projects()] == [projects[1]['id']]
    assert set(result['undo']['project_ids']) == {projects[0]['id'], projects[2]['id']}
    assert restore(env, result)['succeeded'] == 2
    assert len(store.list_projects()) == 3


def test_g4_restore_folder_and_fingerprint_after_store_reload(env):
    store, backend, media = env
    p, folder = work(env)
    (folder / 'nested').mkdir(); (folder / 'nested/data.bin').write_bytes(b'1234')
    stat = (folder / 'notes.txt').stat()
    result = delete(env, [p], True)
    assert not folder.exists()
    recent = store.deleted_projects()[0]
    assert recent['folder_status'] == 'trash' and recent['can_restore']
    with pytest.raises(ProjectStoreError, match='deleted_work_recoverable'):
        store.dismiss_deleted_project(p['id'], expected_revision=recent['revision'])
    reloaded = ProjectStore(store.state_dir); reloaded.work_trash_backend = backend
    assert reloaded.restore_projects(**result['undo'])['succeeded'] == 1
    assert (folder / 'nested/data.bin').read_bytes() == b'1234'
    assert (folder / 'notes.txt').stat().st_mtime_ns == stat.st_mtime_ns
    assert reloaded.deleted_projects() == []


@pytest.mark.parametrize('failure,code', [('missing', 'trash_item_missing'), ('occupied', 'restore_target_occupied')])
def test_g4_unrecoverable_distinct_reasons_and_dismiss_keeps_record(env, failure, code):
    store, backend, _ = env
    p, folder = work(env)
    result = delete(env, [p], True)
    if failure == 'missing':
        shutil.rmtree(next(backend.root.iterdir()))
    else:
        folder.mkdir(); (folder / 'do-not-overwrite').write_bytes(b'keep')
    recent = store.deleted_projects()[0]
    assert not recent['can_restore'] and recent['reason_code'] == code
    assert recent['folder_status'] == 'unrecoverable'
    assert restore(env, result)['results'][0]['code'] == code
    store.dismiss_deleted_project(p['id'], expected_revision=recent['revision'])
    assert store.deleted_projects() == [] and store.list_projects() == []
    assert json.loads(store.path.read_text())['projects'][0]['deletion']['dismissed_at']
    if failure == 'occupied':
        assert (folder / 'do-not-overwrite').read_bytes() == b'keep'


def test_g4_changed_fingerprint_never_restores_record(env):
    store, backend, _ = env
    p, folder = work(env)
    result = delete(env, [p], True)
    (next(backend.root.iterdir()) / 'notes.txt').write_bytes(b'tampered')
    assert restore(env, result)['results'][0]['code'] == 'folder_fingerprint_mismatch'
    assert not store.list_projects() and not folder.exists()


def test_preview_is_lazy_batch_reads_are_bounded_and_cas_is_per_item(env):
    store, _, _ = env
    projects = [work(env, f'work-{i}')[0] for i in range(20)]
    with patch('os.walk', side_effect=AssertionError('catalog must not scan folder trees')):
        catalog = MediaReview(store).catalog()
    assert catalog['pieces'][0]['created_at'] and catalog['pieces'][0]['folder_name']
    preview = store.deletion_preview([p['id'] for p in projects[:2]])
    assert len(preview) == 2 and all(p['can_move_folder'] for p in preview)
    changed = store.update_project(projects[0]['id'], {'title': 'new'})
    with patch.object(store, '_load', wraps=store._load) as read:
        result = delete(env, projects[:2])
    assert read.call_count == 2
    assert result['results'][0]['code'] == 'revision_conflict'
    assert result['results'][1]['revision'] == projects[1]['revision'] + 1
    assert store.get_project(changed['id'])['title'] == 'new'


def test_stale_undo_cannot_restore_a_later_deletion(env):
    p, _ = work(env)
    first = delete(env, [p])
    restore(env, first)
    p = env[0].get_project(p['id'])
    second = delete(env, [p])
    assert restore(env, first)['results'][0]['code'] == 'revision_conflict'
    assert restore(env, second)['succeeded'] == 1


def test_http_routes_csrf_deleted_reads_and_single_restore(env):
    store, _, _ = env
    p, _ = work(env)
    app = StudioApplication(store, csrf_token='test-csrf')
    server = ThreadingHTTPServer(('127.0.0.1', 0), app.handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    def request(method, path, body=None, csrf=True):
        conn = http.client.HTTPConnection(*server.server_address)
        headers = {'Content-Type': 'application/json'}
        if csrf: headers['X-Content-OS-CSRF'] = 'test-csrf'
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse(); value = json.loads(response.read()); conn.close()
        return response.status, value
    try:
        body = {'projectIds': [p['id']], 'expectedRevisions': {p['id']: p['revision']}, 'moveFolders': False}
        assert request('POST', '/api/projects/delete', body, False)[0] == 403
        assert request('POST', '/api/projects/delete-preview', {'projectIds': [p['id']]})[1]['items'][0]['can_move_folder']
        status, result = request('POST', '/api/projects/delete', body)
        assert status == 200 and result['succeeded'] == 1
        assert request('GET', f"/api/projects/{p['id']}")[1]['error']['code'] == 'project_not_found'
        status, recent = request('GET', '/api/projects/deleted')
        assert status == 200 and len(recent['items']) == 1
        assert request('POST', f"/api/projects/{p['id']}/dismiss", {'expectedRevision': recent['items'][0]['revision']})[1]['error']['code'] == 'deleted_work_recoverable'
        status, restored = request('POST', f"/api/projects/{p['id']}/restore", {'expectedRevision': recent['items'][0]['revision']})
        assert status == 200 and restored['succeeded'] == 1
        assert request('POST', '/api/projects/delete', {'projectIds': []})[0] == 400
        assert request('POST', '/api/projects/delete', {**body, 'moveFolder': True})[0] == 400
        current = store.get_project(p['id'])
        body['expectedRevisions'][p['id']] = current['revision']
        status, deleted = request('POST', '/api/projects/delete', body)
        assert status == 200
        assert request('GET', '/api/review/catalog')[1]['pieces'] == []
        assert request('GET', '/api/bootstrap')[1]['projects'] == []
        assert request('POST', '/api/projects/restore', deleted['undo'])[1]['succeeded'] == 1
        body['expectedRevisions'][p['id']] = store.get_project(p['id'])['revision']
        body['moveFolders'] = True
        deleted = request('POST', '/api/projects/delete', body)[1]
        recent = request('GET', '/api/projects/deleted')[1]
        assert str(env[2]) not in json.dumps(recent) and 'trash_location' not in json.dumps(recent)
        shutil.rmtree(next(env[1].root.iterdir()))
        recent = request('GET', '/api/projects/deleted')[1]['items'][0]
        assert recent['reason_code'] == 'trash_item_missing'
        assert request('POST', f"/api/projects/{p['id']}/dismiss", {'expectedRevision': recent['revision']})[0] == 200
        assert request('GET', '/api/projects/deleted')[1]['items'] == []
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_g2_connection_through_symlink_never_trashes_the_resolved_target(env):
    store, backend, media = env
    target = media / 'target'; target.mkdir(); (target / 'keep.txt').write_bytes(b'keep')
    alias = media / 'alias'; alias.symlink_to(target, target_is_directory=True)
    p = store.create_project(title='alias', local_workspace=str(alias))
    result = delete(env, [p], True)
    assert result['results'][0]['code'] == 'folder_symlink'
    assert (target / 'keep.txt').read_bytes() == b'keep' and alias.is_symlink()
    assert not backend.calls


def test_delete_verifies_move_before_soft_delete(env):
    store, backend, _ = env
    p, folder = work(env)
    original_move = backend.move
    def corrupt(source):
        receipt = original_move(source)
        (backend.location(receipt) / 'notes.txt').write_bytes(b'changed during move')
        return receipt
    backend.move = corrupt
    result = delete(env, [p], True)
    assert not result['results'][0]['ok']
    assert result['results'][0]['code'] == 'folder_fingerprint_mismatch'
    assert store.get_project(p['id']) and folder.is_dir()


def test_json_commit_failure_rolls_back_folder_moves_and_restores(env):
    store, backend, _ = env
    p, folder = work(env)
    before = store.path.read_bytes()
    with patch.object(store, '_save', side_effect=OSError('commit failed')):
        with pytest.raises(OSError): delete(env, [p], True)
    assert folder.is_dir() and store.path.read_bytes() == before
    result = delete(env, [p], True)
    before = store.path.read_bytes()
    with patch.object(store, '_save', side_effect=OSError('commit failed')):
        with pytest.raises(OSError): restore(env, result)
    assert not folder.exists() and store.path.read_bytes() == before
    assert store.deleted_projects()[0]['can_restore']
    assert restore(env, result)['succeeded'] == 1


def test_restore_verifies_after_move_and_keeps_deleted_record_on_mismatch(env):
    store, backend, _ = env
    p, folder = work(env)
    result = delete(env, [p], True)
    original_restore = backend.restore
    def corrupt(receipt, destination):
        original_restore(receipt, destination)
        (destination / 'notes.txt').write_bytes(b'changed during restore')
    backend.restore = corrupt
    assert restore(env, result)['results'][0]['code'] == 'folder_fingerprint_mismatch'
    assert not folder.exists() and not store.list_projects()


def test_mixed_folder_selection_and_batch_restore_isolation(env):
    store, backend, _ = env
    first, folder = work(env, 'first')
    second, kept = work(env, 'second', items=[{'type': 'image'}])
    result = delete(env, [first, second], True, folder_project_ids=[first['id']])
    assert result['succeeded'] == 2 and not folder.exists() and kept.is_dir()
    folder.mkdir()
    restored = restore(env, result)
    assert [r['ok'] for r in restored['results']] == [False, True]
    assert restored['results'][0]['code'] == 'restore_target_occupied'
    assert [p['id'] for p in store.list_projects()] == [second['id']]


def test_catalog_and_recent_counts_and_newest_first(env):
    store, _, _ = env
    projects = [work(env, f'work-{i}')[0] for i in range(8)]
    review = MediaReview(store)
    first = delete(env, projects[:2])
    assert review.catalog()['groups'][0]['count'] == 6
    assert len(store.deleted_projects()) == 2
    recent = store.deleted_projects()[0]
    store.restore_projects([recent['id']], expected_revisions={recent['id']: recent['revision']})
    assert review.catalog()['groups'][0]['count'] == 7
    assert len(store.deleted_projects()) == 1
    p = store.get_project(recent['id'])
    delete(env, [p])
    assert store.deleted_projects()[0]['id'] == p['id']
    remaining = store.list_projects()
    delete(env, remaining)
    assert review.catalog()['groups'] == [] and len(store.deleted_projects()) == 8


@pytest.mark.parametrize('changes,code', [
    ({'project_ids': []}, 'project_ids_invalid'),
    ({'project_ids': ['bad']}, 'project_ids_invalid'),
    ({'expected_revisions': {}}, 'revision_invalid'),
    ({'move_folders': 'false'}, 'move_folders_invalid'),
    ({'folder_project_ids': []}, 'folder_project_ids_invalid'),
])
def test_invalid_batch_inputs_do_not_mutate(env, changes, code):
    store, backend, _ = env
    p, _ = work(env)
    args = dict(project_ids=[p['id']], expected_revisions={p['id']: p['revision']})
    args.update(changes)
    before = store.path.read_bytes()
    with pytest.raises(ProjectStoreError, match=code): store.delete_projects(**args)
    assert store.path.read_bytes() == before and not backend.calls


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS Foundation adapter')
def test_native_folder_adapter_reuses_foundation_and_exclusive_restore(env):
    from types import SimpleNamespace
    from studio.work_trash import MacOSFolderTrashBackend, fingerprint
    store, backend, _ = env
    p, folder = work(env)
    digest = fingerprint(folder)
    def runner(command, timeout):
        assert 'FileManager.default.trashItem' in command[command.index('-e') + 1] and timeout > 0
        receipt = backend.move(Path(command[-1]))
        return SimpleNamespace(returncode=0, stdout=json.dumps({'trash_path': receipt['path']}))
    native = MacOSFolderTrashBackend(runner)
    store.work_trash_backend = native
    result = delete(env, [p], True)
    assert result['succeeded'] == 1 and not folder.exists()
    assert restore(env, result)['succeeded'] == 1
    assert fingerprint(folder) == digest
    # No registry file is needed to recover a folder after process restart.
    assert sorted(f.name for f in store.state_dir.iterdir()) == ['creative-projects.json', 'creative-projects.lock']


def test_unresolvable_reference_refuses_folder_move_but_keeps_batch_record_only_item(env):
    store, backend, media = env
    first, folder = work(env, 'first')
    second, kept = work(env, 'second')
    other, _ = work(env, 'other')
    loop = media / 'loop'; loop.symlink_to(loop)
    with store._transaction() as data:
        record = next(p for p in data['projects'] if p['id'] == other['id'])
        record['local_workspace']['local_path'] = str(loop)
    result = delete(env, [first, second], True, folder_project_ids=[first['id']])
    assert [r['ok'] for r in result['results']] == [False, True]
    assert result['results'][0]['code'] == 'folder_unreadable'
    assert folder.is_dir() and kept.is_dir() and not backend.calls


@pytest.mark.parametrize('unrelated', [0, 20])
def test_json_read_budget_and_folder_scan_scope_do_not_grow_per_item(env, unrelated):
    store, _, _ = env
    selected = [work(env, f'selected-{i}')[0] for i in range(2)]
    for i in range(unrelated):
        work(env, f'unrelated-{i}')
    with patch.object(store, '_load', wraps=store._load) as read, patch('os.walk', wraps=os.walk) as walk:
        store.deletion_preview([p['id'] for p in selected])
    assert read.call_count == 1
    assert {Path(call.args[0]).name for call in walk.call_args_list} == {'selected-0', 'selected-1'}
    with patch.object(store, '_load', wraps=store._load) as read, patch('os.walk', side_effect=AssertionError('record-only delete must not walk folders')):
        result = delete(env, selected)
    assert read.call_count == 2 and result['succeeded'] == 2


@pytest.mark.skipif(sys.platform != 'darwin' or os.environ.get('R275_NATIVE_TRASH_TESTS') != '1',
                    reason='opt-in Foundation Trash roundtrip with temporary synthetic data only')
def test_native_foundation_trash_roundtrip_with_temporary_folder(env):
    from studio.work_trash import MacOSFolderTrashBackend, fingerprint
    store, _, _ = env
    store.work_trash_backend = MacOSFolderTrashBackend()
    p, folder = work(env)
    expected = fingerprint(folder)
    result = delete(env, [p], True)
    assert result['succeeded'] == 1, result
    try:
        assert not folder.exists()
    finally:
        restored = restore(env, result)
        assert restored['succeeded'] == 1, restored
    assert folder.is_dir() and fingerprint(folder) == expected
