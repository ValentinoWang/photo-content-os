"""Project grouping, immutable shot evidence and ID-addressed derived media."""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import threading
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from studio.project_store import ProjectStoreError, _atomic, _thread_lock
from runtime_paths import local_media_root
from music_library.library import MusicLibrary

SCENE_NAMES = json.loads((Path(__file__).parent / 'static/scene-names.json').read_text())
STATES = ('selected', 'usable', 'unused', 'rejected')
DECISIONS = {'精选': 'selected', '可用': 'usable', '不用': 'unused'}


def read_json(path, *, optional=False):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        if optional and not Path(path).is_symlink():
            return None
        raise ProjectStoreError('review_unreadable', '无法读取本机记录')
    except (OSError, ValueError, UnicodeError) as exc:
        raise ProjectStoreError('review_unreadable', '无法读取本机记录') from exc


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def waveform(samples, segments=180):
    import numpy as np
    samples = np.asarray(samples, dtype=float)
    values = [float(np.sqrt(np.mean(part * part))) if len(part) else 0.0 for part in np.array_split(samples, segments)]
    maximum = max(values, default=0)
    return [v / maximum if maximum else 0 for v in values]


def scene_name(scene):
    return ' · '.join('待选素材' if part == 'raw-pending' else SCENE_NAMES.get(part, part) for part in scene.split('/'))


def piece_display_name(title):
    """The catalog owns display names; every browser surface consumes this projection."""
    match = re.match(r'^(\d{4})(\d{2})(\d{2})_(.*)$', title)
    if not match:
        return dict(title=title.replace('_', ' · '), date=None)
    year, month, day, name = match.groups()
    try:
        date = datetime(int(year), int(month), int(day))
    except ValueError as exc:
        raise ProjectStoreError('review_unreadable', '无法读取作品日期') from exc
    return dict(title=name.replace('_', ' · '), date=f'{date.year}/{date.month}/{date.day}')


def safe_file(path, root):
    # A derived locator must never follow a symlink back to a camera original.
    path, root = Path(path), Path(root).resolve()
    if path.is_symlink() or not path.is_file():
        return None
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
        relative = path.relative_to(root)
        if any((root / Path(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts))):
            return None
        return resolved
    except ValueError:
        return None


@contextmanager
def directory_lock(path):
    path.mkdir(parents=True, exist_ok=True)
    with _thread_lock(path):
        fd = os.open(path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


class MediaReview:
    def __init__(self, store):
        self.store = store
        self.music = MusicLibrary()
        self._evidence_cache = {}
        self._evidence_lock = threading.RLock()

    def workspace(self, identity):
        path = self.store.local_workspace_path(identity)
        try:
            path.relative_to(local_media_root())
        except ValueError as exc:
            raise ProjectStoreError('workspace_outside_media', '素材位置不在素材根内') from exc
        return path

    def evidence_document(self, folder):
        path = folder / 'shots.json'
        try:
            stat = path.stat()
        except FileNotFoundError:
            return read_json(path, optional=True)
        key = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        with self._evidence_lock:
            cached = self._evidence_cache.get(path)
            if cached and cached[0] == key:
                return cached[1]
            document = read_json(path)
            self._evidence_cache[path] = (key, document)
            return document

    def shots(self, identity):
        root = self.workspace(identity)
        folder = root / 'ai-analysis/shots'
        document = self.evidence_document(folder)
        decisions = read_json(folder / 'decisions.json', optional=True) or {'version': 0, 'shots': {}, 'confirmation': None}
        if not isinstance(decisions, dict) or type(decisions.get('version')) is not int or not isinstance(decisions.get('shots'), dict):
            raise ProjectStoreError('review_unreadable', '无法读取镜头决定')
        if decisions['version'] < 0 or any(not isinstance(entry, dict) or entry.get('status') not in STATES[:3]
                                          or not isinstance(entry.get('decided_at'), str) for entry in decisions['shots'].values()):
            raise ProjectStoreError('review_unreadable', '无法读取镜头决定')
        confirmation_record = decisions.get('confirmation')
        if confirmation_record is not None and (not isinstance(confirmation_record, dict)
                or any(not isinstance(confirmation_record.get(key), str) for key in ('confirmed_at', 'selection_digest', 'evidence_digest'))):
            raise ProjectStoreError('review_unreadable', '无法读取确认信息')
        if document is not None and (not isinstance(document, dict) or not isinstance(document.get('shots'), list)):
            raise ProjectStoreError('review_unreadable', '无法读取挑镜头结果')
        document = document or {'shots': [], 'hook_candidates': [], 'run_status': 'not_started'}
        manifest = read_json(root / 'ai-analysis/media-manifest.json', optional=True) or {'items': []}
        capture_times = {item.get('relative_path'): item.get('created_at') for item in manifest['items']}
        rows = []
        by_scene = {}
        for row in document['shots']:
            by_scene.setdefault(row['scene'], set()).add(Path(row['source_relative_path']).stem)
        prefixes = {scene: os.path.commonprefix(sorted(names)) if len(names) > 1 else '' for scene, names in by_scene.items()}
        partial = document['run_status'] not in ('complete', 'not_started')
        for row in document['shots']:
            status = row['status']
            if status != 'rejected':
                status = decisions['shots'].get(row['id'], {}).get('status')
                if not status and (row.get('model_decision') or not partial):
                    status = row['status'] if row['status'] in STATES else None
            if status not in (*STATES, None):
                raise ProjectStoreError('review_unreadable', '无法读取镜头结论')
            name = Path(row['source_relative_path']).stem
            prefix = prefixes[row['scene']]
            if len(prefix) >= 3 and len(name) > len(prefix):
                name = name[len(prefix):].lstrip('_ -')
            identifier = row['id']
            frame_ids = [f'/api/review/pieces/{identity}/media/frame/{identifier}-{i}' for i in range(len(row['frames']))]
            source = root / row['source_relative_path']
            try:
                timestamp = capture_times.get(row['source_relative_path'])
                captured = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp() if timestamp else source.stat().st_mtime
            except FileNotFoundError:
                captured = 0
            rows.append({**{key: value for key, value in row.items() if key not in ('frames', 'source_relative_path')},
                         'status': status, 'name': name.replace('_', ' · '), 'scene_name': scene_name(row['scene']),
                         'filename': Path(row['source_relative_path']).name, 'captured': captured,
                         'frames': frame_ids, 'duration': 2.5 if row['kind'] == 'photo' else (row.get('duration_sec') or 0),
                         'preview': f'/api/review/pieces/{identity}/media/shot/{identifier}' if row['kind'] == 'video' else (frame_ids[0] if frame_ids else None)})
        earliest = {scene: min(r['captured'] for r in rows if r['scene'] == scene) for scene in by_scene}
        rows.sort(key=lambda r: (earliest[r['scene']], r['scene'], r['filename'], r.get('start_sec') or 0))
        selected = [row['id'] for row in rows if row['status'] == 'selected']
        selection_digest = digest(selected)
        confirmation = decisions.get('confirmation')
        confirmed = bool(confirmation and confirmation.get('selection_digest') == selection_digest and confirmation.get('evidence_digest') == digest(document))
        return dict(shots=rows, counts={s: sum(r['status'] == s for r in rows) for s in STATES},
                    duration=sum(r['duration'] for r in rows if r['status'] == 'selected'),
                    selected=selected, version=decisions['version'], confirmed=confirmed,
                    confirmation=confirmation if confirmed else None, partial=partial,
                    run_status=document['run_status'], hook_candidates=document.get('hook_candidates', []),
                    median=document.get('blur_project_median'), model_progress={'completed': sum(c.get('status') == 'ok' and c.get('id', '').startswith('select-') for c in document.get('model_calls', [])), 'total': len(document.get('sheets', []))}, selection_digest=selection_digest,
                    evidence_digest=digest(document), progress=read_json(folder / 'progress.json', optional=True))

    def decide(self, identity, value):
        folder = self.workspace(identity) / 'ai-analysis/shots'
        with directory_lock(folder):
            current = self.shots(identity)
            if type(value.get('expectedVersion')) is not int or value['expectedVersion'] != current['version']:
                raise ProjectStoreError('revision_conflict', '镜头决定已变动，请刷新后再试')
            decisions = read_json(folder / 'decisions.json', optional=True) or {'schema_version': 1, 'version': 0, 'shots': {}}
            if value.get('confirm'):
                if current['partial'] or not current['shots']:
                    raise ProjectStoreError('review_incomplete', '看图做完之前不能确认。已看完的部分可以先播一遍。')
                decisions['confirmation'] = dict(confirmed_at=now(), selection_digest=current['selection_digest'], evidence_digest=current['evidence_digest'])
            else:
                row = next((r for r in current['shots'] if r['id'] == value.get('shotId')), None)
                if row is None or row['status'] == 'rejected' or value.get('status') not in STATES[:3]:
                    raise ProjectStoreError('review_decision_invalid', '这个镜头不能修改结论')
                decisions['shots'][row['id']] = dict(status=value['status'], decided_at=now())
                decisions['confirmation'] = None
            decisions['version'] += 1
            _atomic(folder / 'decisions.json', decisions)
        return self.shots(identity)

    def outputs(self, identity):
        root = self.workspace(identity)
        result = []
        for path in sorted((root / 'output').glob('v*/*.mp4'), key=lambda p: (int(p.parent.name[1:]) if p.parent.name[1:].isdigit() else float('inf'), p.parent.name, p.name)):
            if safe_file(path, root / 'output'):
                result.append(dict(id=digest(path.relative_to(root).as_posix())[:24], version=path.parent.name, name=path.stem))
        return result

    def piece(self, project):
        identity = project['id']
        piece = dict(id=identity, **piece_display_name(project['title']), connected=bool(project.get('local_workspace', {}).get('connected')), updated_at=project.get('updated_at'), videos=0, photos=0,
                     outputs=[], versions=0, cover=None, pending=False, group_id='other', status='not_started')
        if not project.get('local_workspace', {}).get('connected'):
            return piece
        root = self.workspace(identity)
        work_manifest = read_json(root / 'project-manifest.json', optional=True)
        if work_manifest is not None:
            if not isinstance(work_manifest, dict) or not isinstance(work_manifest.get('title'), str) or not work_manifest['title'].strip():
                raise ProjectStoreError('review_unreadable', '无法读取作品名称')
            piece.update(piece_display_name(work_manifest['title']))
        piece['workspace_key'] = root.name
        parent = read_json(root.parent / 'project-manifest.json', optional=True)
        if parent is not None:
            if not isinstance(parent, dict) or not isinstance(parent.get('title'), str) or not parent['title'].strip():
                raise ProjectStoreError('review_unreadable', '无法读取项目名称')
            piece.update(group_id=digest(str(root.parent))[:20], group_title=parent['title'])
        manifest = read_json(root / 'ai-analysis/media-manifest.json', optional=True)
        if manifest is not None:
            if not isinstance(manifest, dict) or not isinstance(manifest.get('items'), list):
                raise ProjectStoreError('review_unreadable', '无法读取素材清单')
            items = manifest['items']
            piece.update(videos=sum(x.get('media_type', x.get('type')) == 'video' for x in items), photos=sum(x.get('media_type', x.get('type')) == 'image' for x in items))
        shots = self.shots(identity)
        outputs = self.outputs(identity)
        running = (shots['progress'] or {}).get('status') == 'running'
        piece.update(outputs=outputs, versions=len({o['version'] for o in outputs}),
                     pending=bool(shots['shots'] and not shots['partial'] and not shots['confirmed'] and not running),
                     status='running' if running else 'confirmed' if shots['confirmed'] else 'partial' if shots['partial'] else 'review' if shots['shots'] else 'not_started',
                     selected=shots['counts']['selected'])
        hook = next((r for h in shots['hook_candidates'] for r in shots['shots'] if r['id'] == h['id'] and r['frames']), None)
        if hook:
            piece['cover'] = hook['frames'][len(hook['frames']) // 2]
        elif outputs:
            piece['cover'] = f'/api/review/pieces/{identity}/media/poster/{outputs[-1]["id"]}'
        elif manifest:
            photo = next((x for x in manifest['items'] if x.get('media_type', x.get('type')) == 'image'), None)
            if photo:
                piece['cover'] = f'/api/review/pieces/{identity}/media/photo/{digest(photo)[:24]}'
        return piece

    def catalog(self):
        pieces = [self.piece(p) for p in self.store.list_projects()]
        groups = {}
        for piece in pieces:
            group = groups.setdefault(piece['group_id'], dict(id=piece['group_id'], title=piece.get('group_title', '其他作品'), pieces=[]))
            group['pieces'].append(piece)
        for group in groups.values():
            group.update(count=len(group['pieces']), pending=sum(p['pending'] for p in group['pieces']), produced=sum(p['versions'] > 0 for p in group['pieces']))
        return dict(pieces=pieces, groups=sorted(groups.values(), key=lambda g: g['id'] == 'other'))

    def tracks(self):
        return [{**{k: v for k, v in track.items() if k not in ('sources', 'original_url', 'audio_file')},
                 'original_url': track['original_url'] if track['original_url'].startswith(('https://', 'http://')) else None,
                 'audio': f'/api/review/music/{track["file_sha256"]}/audio',
                 'peaks': read_json(self.music.root / track['file_sha256'] / 'peaks.json', optional=True)}
                for track in self.music.list_tracks()]

    def prepare_peaks(self):
        import numpy as np
        for track in self.music.list_tracks():
            folder = self.music.root / track['file_sha256']
            path = folder / 'peaks.json'
            if path.exists():
                read_json(path)
                continue
            result = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(folder / track['audio_file']), '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'], capture_output=True, check=True)
            _atomic(path, waveform(np.frombuffer(result.stdout, dtype='<f4')))

    def media(self, identity, kind, identifier):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', identifier):
            return None
        root = self.workspace(identity)
        folder = root / 'ai-analysis/shots'
        if kind in ('frame', 'shot'):
            document = self.evidence_document(folder) or {'shots': []}
            for row in document['shots']:
                if kind == 'shot' and row['id'] == identifier and row['kind'] == 'video':
                    return safe_file(folder / 'previews' / (identifier + '.mp4'), folder / 'previews')
                if kind == 'frame':
                    for i, frame in enumerate(row['frames']):
                        if identifier == f'{row["id"]}-{i}':
                            return safe_file(root / frame, folder / 'frames')
        if kind in ('output', 'poster'):
            for path in sorted((root / 'output').glob('v*/*.mp4')):
                if digest(path.relative_to(root).as_posix())[:24] == identifier and safe_file(path, root / 'output'):
                    if kind == 'output':
                        return path
                    return safe_file(root / 'ai-analysis/output-posters' / (identifier + '.jpg'), root / 'ai-analysis/output-posters')
        if kind == 'photo':
            manifest = read_json(root / 'ai-analysis/media-manifest.json', optional=True) or {'items': []}
            if not any(item.get('media_type', item.get('type')) == 'image' and digest(item)[:24] == identifier for item in manifest['items']):
                return None
            return safe_file(self.store.state_dir / 'media-previews' / (identity + '-' + identifier + '.jpg'), self.store.state_dir / 'media-previews')
        return None

    def music_audio(self, identifier):
        for track in self.music.list_tracks():
            if track['file_sha256'] == identifier:
                return safe_file(self.music.root / identifier / track['audio_file'], self.music.root / identifier)
        return None

    def asset_preview(self, asset):
        return safe_file(self.store.state_dir / 'media-previews' / (asset['asset_id'] + '.mp4'), self.store.state_dir / 'media-previews')

    def prepare_asset(self, asset):
        project = next((p for p in self.store.list_projects() if p['local_workspace']['connected']
                        and self.workspace(p['id']).name == asset['source_project']), None)
        if project is None:
            return
        root = self.workspace(project['id'])
        source = (root / asset['source_relative_path']).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            return
        output = self.store.state_dir / 'media-previews' / (asset['asset_id'] + '.mp4')
        if output.exists():
            return
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, staging = tempfile.mkstemp(dir=output.parent, suffix='.mp4')
        os.close(fd)
        try:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-vf', 'scale=540:-2',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', staging], check=True, capture_output=True)
            os.replace(staging, output)
        finally:
            Path(staging).unlink(missing_ok=True)

    def prepare_posters(self, *, rebuild=False):
        from PIL import Image
        from pillow_heif import register_heif_opener
        register_heif_opener()
        for project in self.store.list_projects():
            if not project.get('local_workspace', {}).get('connected'):
                continue
            identity = project['id']; root = self.workspace(identity)
            for path in (root / 'output').glob('v*/*.mp4'):
                if not safe_file(path, root / 'output'):
                    continue
                out = root / 'ai-analysis/output-posters' / (digest(path.relative_to(root).as_posix())[:24] + '.jpg')
                if rebuild or not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                            '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
                                           check=True, capture_output=True, text=True)
                    duration = float(probe.stdout.strip())
                    if not math.isfinite(duration) or duration <= 0:
                        raise ProjectStoreError('review_unreadable', '无法读取成片时长')
                    fd, staging = tempfile.mkstemp(dir=out.parent, suffix='.jpg')
                    os.close(fd)
                    try:
                        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(duration / 3), '-i', str(path),
                                        '-frames:v', '1', '-vf', 'scale=540:-2', staging], check=True, capture_output=True)
                        os.replace(staging, out)
                    finally:
                        Path(staging).unlink(missing_ok=True)
            manifest = read_json(root / 'ai-analysis/media-manifest.json', optional=True)
            if not manifest:
                continue
            for item in manifest['items']:
                if item.get('media_type', item.get('type')) != 'image':
                    continue
                source = root / (item.get('relative_path') or item.get('path') or '')
                if not source.is_file() or not source.resolve().is_relative_to(root):
                    continue
                out = self.store.state_dir / 'media-previews' / (identity + '-' + digest(item)[:24] + '.jpg')
                if not out.exists():
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with Image.open(source) as image:
                        image.thumbnail((540, 540)); image.convert('RGB').save(out)
                break
