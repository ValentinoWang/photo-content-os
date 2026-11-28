"""Work deletion in the project CAS store; folder receipts stay in that same store."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from functools import cached_property
from datetime import datetime, timezone
from pathlib import Path

from studio.project_store import ProjectStoreError
from studio.media_review import media_counts, piece_display_name, read_json
from runtime_paths import local_media_root
from media_ops.media_trash_flow import MacOSSystemTrashBackend, MediaTrashFlowError, _MACOS_TRASH_TIMEOUT_SECONDS


# Use the same Foundation trashItem operation with a typed out-URL receipt.
_FOLDER_TRASH_SCRIPT = r'''
import Foundation
var result: NSURL?
do {
    try FileManager.default.trashItem(at: URL(fileURLWithPath: CommandLine.arguments[1]), resultingItemURL: &result)
    guard let result = result, let path = result.path else { exit(2) }
    let data = try JSONSerialization.data(withJSONObject: ["trash_path": path])
    FileHandle.standardOutput.write(data)
} catch { exit(1) }
'''


if __package__:
    from .constants import (
        ELIGIBILITY_CODES,
        RESULT_CODES,
        UNRECOVERABLE,
    )
else:
    try:
        from studio.constants import (
            ELIGIBILITY_CODES,
            RESULT_CODES,
            UNRECOVERABLE,
        )
    except ImportError:
        from constants import (
            ELIGIBILITY_CODES,
            RESULT_CODES,
            UNRECOVERABLE,
        )


def fail(code):
    # HTTP clients consume codes; no unapproved operator copy is manufactured here.
    raise ProjectStoreError(code, code)


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def rename_exclusive(source, destination):
    """Atomic no-replace rename, including against a concurrent destination creator."""
    libc = ctypes.CDLL(None, use_errno=True)
    source, destination = os.fsencode(source), os.fsencode(destination)
    if sys.platform == 'darwin':
        result = libc.renamex_np(ctypes.c_char_p(source), ctypes.c_char_p(destination), ctypes.c_uint(4))  # RENAME_EXCL
    elif sys.platform == 'linux':
        result = libc.renameat2(-100, ctypes.c_char_p(source), -100, ctypes.c_char_p(destination), 1)
    else:
        raise OSError(errno.ENOTSUP, 'exclusive rename unavailable')
    if result:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


class MacOSFolderTrashBackend:
    """Reuse the file backend's Foundation call without changing its file semantics."""
    def __init__(self, runner=None):
        self.runner = runner or MacOSSystemTrashBackend._run_foundation_trash

    @cached_property
    def available(self):
        if sys.platform != 'darwin' or not os.access('/usr/bin/swift', os.X_OK):
            return False
        try:
            selected = subprocess.run(['/usr/bin/xcode-select', '--print-path'], capture_output=True,
                                      text=True, timeout=2, check=False)
            if selected.returncode:
                return False
            developer = Path(selected.stdout.strip())
            return any(os.access(path, os.X_OK) for path in (
                developer / 'usr/bin/swift',
                developer / 'Toolchains/XcodeDefault.xctoolchain/usr/bin/swift',
            ))
        except (OSError, subprocess.SubprocessError):
            return False

    def move(self, source):
        if sys.platform != 'darwin':
            raise OSError('system trash unavailable')
        result = self.runner(('/usr/bin/swift', '-e', _FOLDER_TRASH_SCRIPT, str(source)),
                             _MACOS_TRASH_TIMEOUT_SECONDS)
        if MacOSSystemTrashBackend._returncode(result) != 0:
            raise OSError('system trash failed')
        path = MacOSSystemTrashBackend._trash_path_from_result(result)
        return {'id': 'work-trash-' + uuid.uuid4().hex, 'path': str(path)}

    def location(self, receipt):
        return Path(receipt['path'])

    def restore(self, receipt, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        rename_exclusive(self.location(receipt), destination)


def has_symlink(path):
    return any(parent.is_symlink() for parent in (path, *path.parents))


def fingerprint(folder):
    """Sorted relative file path, size and nanosecond mtime; never follow links."""
    if has_symlink(folder):
        fail('folder_symlink')
    if not stat.S_ISDIR(folder.lstat().st_mode):
        fail('folder_unreadable')
    rows = []
    def unreadable(error):
        raise error
    for base, directories, files in os.walk(folder, followlinks=False, onerror=unreadable):
        for name in directories + files:
            path = Path(base) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                fail('folder_symlink')
            if stat.S_ISREG(info.st_mode):
                rows.append((path.relative_to(folder).as_posix(), info.st_size, info.st_mtime_ns))
            elif not stat.S_ISDIR(info.st_mode):
                fail('folder_unreadable')
    return hashlib.sha256(json.dumps(sorted(rows), ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def ids(value):
    from studio.project_store import SAFE_ID
    if (not isinstance(value, list) or not value or len(value) > 500
            or any(not isinstance(p, str) or not SAFE_ID.fullmatch(p) for p in value)
            or len(set(value)) != len(value)):
        fail('project_ids_invalid')
    return value


def revisions(project_ids, expected):
    if (not isinstance(expected, dict) or set(expected) != set(project_ids)
            or any(type(v) is not int or v < 1 for v in expected.values())):
        fail('revision_invalid')


class WorkTrash:
    def __init__(self, store):
        self.store = store
        self.backend = getattr(store, 'work_trash_backend', None) or MacOSFolderTrashBackend()

    @staticmethod
    def paths(data):
        # Resolve references once for the whole batch; include deleted/dismissed records.
        shared, descendants, unreadable = {}, {}, False
        for project in data['projects']:
            raw = project.get('local_workspace', {}).get('local_path')
            if not raw:
                continue
            try:
                path = Path(raw).resolve()
                if has_symlink(path):
                    unreadable = True
                    continue
            except (OSError, RuntimeError):
                unreadable = True
                continue
            shared.setdefault(path, set()).add(project['id'])
            for parent in path.parents:
                descendants.setdefault(parent, set()).add(project['id'])
        return shared, descendants, unreadable

    @staticmethod
    def snapshot(project):
        raw = project.get('local_workspace', {}).get('local_path')
        root = Path(raw) if raw else None
        display = piece_display_name(project['title'])
        group_title = '其他作品'
        if root and root.is_dir():
            manifest = read_json(root / 'project-manifest.json', optional=True)
            parent = read_json(root.parent / 'project-manifest.json', optional=True)
            for record in (manifest, parent):
                if record is not None and (not isinstance(record, dict) or not isinstance(record.get('title'), str) or not record['title'].strip()):
                    fail('review_unreadable')
            if manifest:
                display = piece_display_name(manifest['title'])
            if parent:
                group_title = parent['title']
        return dict(id=project['id'], title=display['title'], revision=project['revision'],
                    created_at=project['created_at'], folder_name=root.name if root else '', group_title=group_title)

    def eligibility(self, project, paths):
        raw = project.get('local_workspace', {}).get('local_path')
        if not raw:
            return 'folder_not_connected', None
        root = Path(raw)
        media = local_media_root()
        try:
            connection = Path(project['local_workspace'].get('connection_path', raw))
            if has_symlink(root) or has_symlink(connection):
                return 'folder_symlink', None
            resolved = root.resolve()
            if resolved == media:
                return 'folder_is_media_root', None
            if not resolved.is_relative_to(media):
                return 'folder_outside_media_root', None
            if not root.is_dir():
                return 'folder_missing', None
            if os.path.lexists(root / 'project-manifest.json'):
                return 'folder_formal_project', None
            counts = media_counts(root)
            if counts['videos'] or counts['photos']:
                return 'folder_has_media', None
            shared, descendants, unreadable = paths
            if unreadable:
                return 'folder_unreadable', None
            if shared.get(resolved, set()) - {project['id']}:
                return 'folder_shared', None
            if descendants.get(resolved, set()) - {project['id']}:
                return 'folder_contains_work', None
            if getattr(self.backend, 'available', True) is False:
                return 'folder_runtime_unavailable', None
            return None, fingerprint(root)
        except ProjectStoreError as exc:
            return ('folder_unreadable' if exc.code == 'review_unreadable' else exc.code), None
        except (OSError, RuntimeError):
            return 'folder_unreadable', None

    def preview(self, project_ids):
        project_ids = ids(project_ids)
        data = self.store._load()
        by_id = {p['id']: p for p in data['projects'] if not p.get('deletion')}
        paths = self.paths(data)
        result = []
        for identity in project_ids:
            project = by_id.get(identity)
            if project is None:
                fail('project_not_found')
            code, _ = self.eligibility(project, paths)
            result.append({**self.snapshot(project), 'can_move_folder': code is None, 'reason_code': code})
        return result

    @contextmanager
    def transaction(self):
        # File operations precede the JSON commit. Roll them back if that commit fails.
        rollback = []
        try:
            with self.store._transaction() as data:
                yield data, rollback
        except Exception:
            for source, destination in reversed(rollback):
                rename_exclusive(source, destination)
            raise

    def delete(self, project_ids, *, expected_revisions, move_folders=False, folder_project_ids=None):
        project_ids = ids(project_ids)
        revisions(project_ids, expected_revisions)
        if type(move_folders) is not bool:
            fail('move_folders_invalid')
        folder_ids = set(project_ids) if move_folders else set()
        if folder_project_ids is not None:
            if (not move_folders or not isinstance(folder_project_ids, list)
                    or any(not isinstance(p, str) for p in folder_project_ids)
                    or len(set(folder_project_ids)) != len(folder_project_ids)
                    or not set(folder_project_ids).issubset(project_ids)):
                fail('folder_project_ids_invalid')
            folder_ids = set(folder_project_ids)
        batch_id = 'delete-' + uuid.uuid4().hex
        results = []
        with self.transaction() as (data, rollback):
            by_id = {p['id']: p for p in data['projects']}
            paths = self.paths(data) if folder_ids else None
            for identity in project_ids:
                project = by_id.get(identity)
                try:
                    if project is None or project.get('deletion'):
                        fail('project_not_found')
                    self.store._revision(project, expected_revisions[identity])
                    snapshot = self.snapshot(project)
                    deletion = dict(snapshot, deleted_at=timestamp(), batch_id=batch_id,
                                    folder_status='original', dismissed_at=None, trash_location=None,
                                    original_path=project.get('local_workspace', {}).get('local_path') or '', fingerprint=None)
                    if identity in folder_ids:
                        code, digest = self.eligibility(project, paths)
                        if code:
                            fail(code)
                        root = Path(deletion['original_path'])
                        try:
                            receipt = self.backend.move(root)
                        except (OSError, subprocess.SubprocessError, MediaTrashFlowError):
                            fail('folder_trash_failed')
                        location = self.backend.location(receipt)
                        rollback.append((location, root))
                        try:
                            matches = not os.path.lexists(root) and fingerprint(location) == digest
                        except (OSError, ProjectStoreError):
                            matches = False
                        if not matches:
                            rename_exclusive(location, root)
                            rollback.pop()
                            fail('folder_fingerprint_mismatch')
                        deletion.update(folder_status='trash', trash_location=receipt, fingerprint=digest)
                    project['deletion'] = deletion
                    project['revision'] += 1
                    results.append(dict(id=identity, ok=True, code=None, revision=project['revision']))
                except ProjectStoreError as exc:
                    results.append(dict(id=identity, ok=False, code=exc.code))
        successful = [r for r in results if r['ok']]
        return {**self.result(results), 'batch_id': batch_id,
                'undo': dict(project_ids=[r['id'] for r in successful],
                             expected_revisions={r['id']: r['revision'] for r in successful}, batch_id=batch_id)}

    @staticmethod
    def result(results):
        succeeded = sum(r['ok'] for r in results)
        return dict(results=results, succeeded=succeeded, failed=len(results) - succeeded)

    def restore_reason(self, deletion, *, verify_fingerprint=False):
        if deletion['folder_status'] != 'trash':
            return None
        destination = Path(deletion['original_path'])
        location = self.backend.location(deletion['trash_location'])
        try:
            # A missing item and an unreadable item are different outcomes.
            location.lstat()
        except FileNotFoundError:
            return 'trash_item_missing'
        except OSError:
            return 'folder_unreadable'
        if os.path.lexists(destination):
            return 'restore_target_occupied'
        if has_symlink(destination.parent) or not destination.resolve().is_relative_to(local_media_root()) or destination.resolve() == local_media_root():
            return 'folder_restore_unsafe'
        try:
            if not location.is_dir():
                return 'folder_unreadable'
            if verify_fingerprint and fingerprint(location) != deletion['fingerprint']:
                return 'folder_fingerprint_mismatch'
        except (OSError, ProjectStoreError):
            return 'folder_unreadable'
        return None

    def deleted(self):
        result = []
        for project in self.store._load()['projects']:
            deletion = project.get('deletion')
            if not deletion or deletion.get('dismissed_at'):
                continue
            code = self.restore_reason(deletion)
            result.append(dict(id=project['id'], title=deletion['title'], group_title=deletion['group_title'],
                               folder_name=deletion['folder_name'], created_at=deletion['created_at'],
                               deleted_at=deletion['deleted_at'], revision=project['revision'],
                               folder_status='unrecoverable' if code in UNRECOVERABLE else deletion['folder_status'],
                               reason_code=code, can_restore=code is None, can_dismiss=code in UNRECOVERABLE))
        return sorted(result, key=lambda r: (r['deleted_at'], r['id']), reverse=True)

    def restore(self, project_ids, *, expected_revisions, batch_id=None):
        project_ids = ids(project_ids)
        revisions(project_ids, expected_revisions)
        results = []
        with self.transaction() as (data, rollback):
            by_id = {p['id']: p for p in data['projects']}
            for identity in project_ids:
                try:
                    project = by_id.get(identity)
                    if project is None or not project.get('deletion') or project['deletion'].get('dismissed_at'):
                        fail('deleted_work_not_found')
                    self.store._revision(project, expected_revisions[identity])
                    deletion = project['deletion']
                    if batch_id is not None and deletion['batch_id'] != batch_id:
                        fail('deletion_batch_conflict')
                    code = self.restore_reason(deletion, verify_fingerprint=True)
                    if code:
                        fail(code)
                    if deletion['folder_status'] == 'trash':
                        destination = Path(deletion['original_path'])
                        location = self.backend.location(deletion['trash_location'])
                        try:
                            self.backend.restore(deletion['trash_location'], destination)
                        except FileNotFoundError:
                            fail('trash_item_missing')
                        except FileExistsError:
                            fail('restore_target_occupied')
                        except (OSError, subprocess.SubprocessError, MediaTrashFlowError):
                            fail('folder_restore_failed')
                        try:
                            matches = fingerprint(destination) == deletion['fingerprint']
                        except (OSError, ProjectStoreError):
                            matches = False
                        if not matches:
                            rename_exclusive(destination, location)
                            fail('folder_fingerprint_mismatch')
                        rollback.append((destination, location))
                    del project['deletion']
                    project['revision'] += 1
                    results.append(dict(id=identity, ok=True, code=None, revision=project['revision']))
                except ProjectStoreError as exc:
                    results.append(dict(id=identity, ok=False, code=exc.code))
        return self.result(results)

    def dismiss(self, project_id, *, expected_revision):
        ids([project_id]); revisions([project_id], {project_id: expected_revision})
        with self.store._transaction() as data:
            project = self.store._find(data, project_id, include_deleted=True)
            deletion = project.get('deletion')
            if not deletion or deletion.get('dismissed_at'):
                fail('deleted_work_not_found')
            self.store._revision(project, expected_revision)
            code = self.restore_reason(deletion)
            if code not in UNRECOVERABLE:
                fail(code or 'deleted_work_recoverable')
            deletion['dismissed_at'] = timestamp()
            project['revision'] += 1
            return dict(id=project_id, revision=project['revision'])
