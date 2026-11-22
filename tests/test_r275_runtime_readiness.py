"""The confirmation must not offer folder moves without the native runtime."""
from unittest.mock import PropertyMock, patch

from studio.project_store import ProjectStore
from studio.work_trash import MacOSFolderTrashBackend


def test_unavailable_native_runtime_is_reported_before_delete(tmp_path, monkeypatch):
    root = tmp_path / 'media'; folder = root / 'work'; folder.mkdir(parents=True)
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(root))
    store = ProjectStore(tmp_path / 'state')
    p = store.create_project(title='synthetic', local_workspace=str(folder))
    with patch.object(MacOSFolderTrashBackend, 'available', new_callable=PropertyMock, return_value=False, create=True):
        preview = store.deletion_preview([p['id']])[0]
        assert not preview['can_move_folder'] and preview['reason_code'] == 'folder_runtime_unavailable'
        result = store.delete_projects([p['id']], expected_revisions={p['id']: p['revision']}, move_folders=True)
    assert result['results'][0]['code'] == 'folder_runtime_unavailable'
    assert store.get_project(p['id']) and folder.is_dir()
