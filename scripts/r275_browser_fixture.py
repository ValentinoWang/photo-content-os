#!/usr/bin/env python3
"""Isolated R275 browser fixture, controlled only through the owning process stdin."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import tempfile
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from studio.project_store import ProjectStore
from studio.server import StudioApplication

base = Path(os.environ['R275_FIXTURE_ROOT']).resolve()
assert base.is_relative_to(Path(tempfile.gettempdir()).resolve()) and base.name.startswith('r275-browser-'), 'fixture must use its own temporary directory'
media = base / 'media'
os.environ['LOCAL_MEDIA_ROOT'] = str(media)
state_dir = base / 'state'


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False))


class FixtureTrash:
    def __init__(self):
        self.failed = set()
        self.serial = 0
    def move(self, source):
        assert source.resolve().is_relative_to(media) and source.resolve() != media
        if source.name in self.failed:
            raise OSError('fixture move failure')
        self.serial += 1
        target = base / 'trash' / str(self.serial)
        target.parent.mkdir(exist_ok=True)
        source.rename(target)
        return {'id': str(self.serial), 'path': str(target)}
    def location(self, receipt):
        target = Path(receipt['path'])
        assert target.is_relative_to(base / 'trash')
        return target
    def restore(self, receipt, destination):
        assert destination.is_relative_to(media)
        if destination.exists(): raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.location(receipt).rename(destination)


backend = FixtureTrash()
store = ProjectStore(state_dir)
store.work_trash_backend = backend
app = StudioApplication(store)
# Test diagnostics are deterministic; no external model, tool installation or media job runs.
app.diagnostics_projection = lambda **kwargs: {'checks': [], 'checked_at': '2026-10-25T13:40:00Z', 'checking': False}
port = int(os.environ['STUDIO_PORT'])
assert port != 8765
server = ThreadingHTTPServer(('127.0.0.1', port), app.handler())
app.video_workflow.origin = f'http://127.0.0.1:{server.server_port}'
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()


def command(value):
    action = value['action']
    if action == 'reset':
        for directory in (media, base / 'trash'):
            if directory.exists(): shutil.rmtree(directory)
        media.mkdir()
        backend.failed.clear()
        with store._transaction() as data: data['projects'] = []
        records = []
        for group, rows in value['data'].items():
            parent = media / ('lzu' if group == 'LZU' else 'other')
            if group == 'LZU': put(parent / 'project-manifest.json', {'title': '2026年重回兰州大学内容创作'})
            for index, row in enumerate(rows):
                folder = parent / row['folder']; folder.mkdir(parents=True, exist_ok=True)
                (folder / 'notes.txt').write_text('R275 synthetic browser fixture only\n')
                if group == 'LZU':
                    put(folder / 'project-manifest.json', {'title': '20260514_' + row['title']})
                    from PIL import Image
                    cover = folder / 'cover.jpg'
                    Image.new('RGB', (320, 200), (44 + index * 13, 72 + index * 9, 75)).save(cover)
                    items = [{'type': 'video'} for _ in range(row['videos'])] + [{'type': 'image', 'relative_path': 'cover.jpg'} for _ in range(row['photos'])]
                    put(folder / 'ai-analysis/media-manifest.json', {'items': items})
                    if index == 1:
                        put(folder / 'ai-analysis/shots/shots.json', {'shots': [{'id': 'S1', 'kind': 'photo', 'scene': 'travel', 'source_relative_path': 'cover.jpg', 'frames': [], 'status': 'selected', 'duration_sec': 3}], 'run_status': 'complete', 'hook_candidates': []})
                record = store.create_project(title=row['title'], local_workspace=str(folder))
                records.append((record['id'], row))
        with store._transaction() as data:
            rows = dict(records)
            for project in data['projects']:
                row = rows[project['id']]
                day = int(row['made'].split('月')[1].split('日')[0])
                project['created_at'] = f'2026-10-{day:02}T04:00:00Z'
        app.media_review.prepare_posters()
        return app.media_review.catalog()
    if action == 'set_media':
        p = next(p for p in store._load()['projects'] if p['id'] == value['id'])
        put(Path(p['local_workspace']['local_path']) / 'ai-analysis/media-manifest.json', {'items': [{'type': 'video'}]})
        return {'ok': True}
    if action == 'fail':
        backend.failed = set(value['folders']); return {'ok': True}
    if action == 'missing':
        p = next(p for p in store._load()['projects'] if p['id'] == value['id'])
        shutil.rmtree(backend.location(p['deletion']['trash_location'])); return {'ok': True}
    if action == 'occupied':
        p = next(p for p in store._load()['projects'] if p['id'] == value['id'])
        target = Path(p['deletion']['original_path']); target.mkdir(); return {'ok': True}
    if action == 'folder_names':
        return sorted(p.name for p in media.rglob('*') if p.is_dir())
    if action == 'stop': return {'ok': True}
    raise ValueError(action)


print(json.dumps({'ready': True, 'url': app.video_workflow.origin}), flush=True)
try:
    for line in sys.stdin:
        value = json.loads(line)
        try: result = command(value)
        except Exception as error: result = {'fixture_error': str(error)}
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if value['action'] == 'stop': break
finally:
    server.shutdown(); server.server_close(); thread.join()
    app.review_jobs.close(); app.video_workflow.close()
