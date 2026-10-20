"""Read analysis sidecars, derive display tags, and serialize the local analysis queue."""
from __future__ import annotations

import copy
import json
import math
import re
import statistics
import subprocess
import threading
import weakref
from collections import Counter, deque
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from music_library.cache import read_json, write_json
from music_library.errors import MusicError
from runtime_paths import local_media_root

ROOT = Path(__file__).resolve().parents[1]
_analysis_queues = weakref.WeakSet()
_analysis_queues_lock = threading.Lock()


def registry(path=None):
    from validate_music_analysis_registry import validate
    data = read_json(Path(path) if path else ROOT / 'music-analysis.registry.json', '音乐分析清单')
    errors = validate(data)
    if errors:
        raise MusicError('音乐分析清单不符合规范：' + '; '.join(errors))
    return data


def derive(scores, reg=None):
    reg = registry() if reg is None else reg
    categories = {c['id']: c for c in reg['tag_categories']}
    def pairs(head):
        values = scores[head]
        return sorted(values, key=lambda p: -p[1])
    def pick(category, head):
        c = categories[category]
        tags = {t['source_label']: t for t in c['tags'] if t['status'] == 'active'}
        return [tags[label]['id'] for label, score in pairs(head) if label in tags and score >= c['rules']['min_score']][:c['rules']['max_tags']]
    aggregate = {}
    for label, score in pairs('genre'):
        major = label.split('---')[0]
        aggregate[major] = aggregate.get(major, 0) + score
    top = max(aggregate, key=aggregate.get)
    genre = next((t for t in categories['genre']['tags'] if t['source_label'] == top and t['status'] == 'active'), None)
    best_label, best_score = pairs('genre')[0]
    style = best_label.split('---', 1)[1] if '---' in best_label and best_score >= categories['genre']['rules']['style_passthrough']['min_score'] else None
    voice_label, voice_score = pairs('voice')[0]
    voice = next((t for t in categories['voice']['tags'] if t['source_label'] == voice_label and t['status'] == 'active'), None)
    sure = voice is not None and voice_score >= categories['voice']['rules']['sure_score']
    return dict(registry_version=reg['registry_version'], genre=[genre['id']] if genre else [], style=style,
                mood=pick('mood', 'moodtheme'), scene=pick('scene', 'moodtheme'), instrument=pick('instrument', 'instrument'),
                voice=[voice['id']] if sure else [], voice_uncertain=not sure)


def taxonomy(reg):
    return {'sections': copy.deepcopy(reg['sections']['kinds']), 'tag_categories': [{k: copy.deepcopy(v) for k, v in c.items() if k in ('id', 'name', 'tags', 'empty_text', 'uncertain_text')} for c in reg['tag_categories']], 'display': copy.deepcopy(reg['display'])}


def validate_analysis(data):
    schema = read_json(ROOT / 'schemas/music-analysis.schema.json', '分析结果规范')
    try:
        Draft202012Validator(schema).validate(data)
        duration = data['duration_seconds']
        beat = data['beat']
        if beat['status'] == 'done':
            beats, downs = beat['beats'], beat['downbeats']
            for times in (beats, downs):
                if any(not math.isfinite(t) or t < 0 or t > duration for t in times) or any(a >= b for a, b in zip(times, times[1:])):
                    raise ValueError('timestamps must increase within duration')
            if not set(downs) <= set(beats) or len(beats) != len(beat['beat_energy']):
                raise ValueError('beat alignment mismatch')
            if any(not math.isfinite(v) for v in beat['beat_energy']):
                raise ValueError('non-finite energy')
            sections = beat['sections']
            if not sections or sections[0]['start'] != 0 or sections[-1]['end'] != duration or any(s['start'] >= s['end'] for s in sections) or any(a['end'] != b['start'] for a, b in zip(sections, sections[1:])):
                raise ValueError('sections must cover duration without gaps')
        if data['tags']['status'] == 'done':
            for scores in data['tags']['scores'].values():
                if len({label for label, _ in scores}) != len(scores) or any(not math.isfinite(score) for _, score in scores):
                    raise ValueError('invalid raw scores')
    except Exception as exc:
        raise MusicError('分析结果无法读取或已损坏：' + str(exc)) from exc


def read_analysis(folder, track=None):
    path = Path(folder) / 'analysis.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        if Path(folder).is_dir() and not path.is_symlink():
            return None
        raise MusicError('音乐分析结果位置无法读取') from exc
    except (OSError, ValueError) as exc:
        raise MusicError('音乐分析结果无法读取或已损坏') from exc
    validate_analysis(data)
    if track and (data['file_sha256'] != track['file_sha256'] or data['duration_seconds'] != track['duration_seconds']):
        raise MusicError('分析结果与曲目不一致')
    return data


def beat_metrics(beat):
    beats, downbeats = beat['beats'], beat['downbeats']
    intervals = [b - a for a, b in zip(beats, beats[1:])]
    positions = {t: i for i, t in enumerate(beats)}
    counts = [positions[b] - positions[a] for a, b in zip(downbeats, downbeats[1:])]
    return dict(bpm=math.floor(60 / statistics.median(intervals) + .5) if intervals else None,
                meter=Counter(counts).most_common(1)[0][0] if counts else None)


class BeatMapUnavailable(Exception):
    code: str
    track_id: str
    failure_code: str | None

    def __init__(self, code: str, track_id: str, failure_code: str | None = None):
        if code not in ('unknown_track', 'queued', 'analyzing', 'beat_failed', 'result_unreadable'):
            raise ValueError('invalid beat map availability code')
        self.code = code
        self.track_id = track_id
        self.failure_code = failure_code
        super().__init__(f'beat map unavailable: {code} ({track_id})')


def _check_beat_map_shape(beat_map):
    duration = beat_map['duration_seconds']
    beats, downbeats = beat_map['beats'], beat_map['downbeats']
    if not math.isfinite(duration) or duration <= 0 or len(beats) < 2 or len(downbeats) < 2:
        raise ValueError('incomplete rhythm')
    for times in (beats, downbeats):
        if any(not math.isfinite(t) or not 0 <= t <= duration for t in times) or any(a >= b for a, b in zip(times, times[1:])):
            raise ValueError('invalid beat timestamps')
    if not set(downbeats) <= set(beats):
        raise ValueError('downbeats must be a subset of beats')
    energy = beat_map['beat_energy']
    if len(energy) != len(beats) or any(not math.isfinite(e) or not 0 <= e <= 1 for e in energy):
        raise ValueError('invalid beat energy')
    sections = beat_map['sections']
    if not sections or sections[0]['start'] != 0 or sections[-1]['end'] != duration:
        raise ValueError('incomplete sections')
    if any(not math.isfinite(s['start']) or not math.isfinite(s['end']) or not 0 <= s['start'] < s['end'] <= duration for s in sections):
        raise ValueError('invalid section interval')
    if any(a['end'] != b['start'] for a, b in zip(sections, sections[1:])):
        raise ValueError('sections must join without gaps')


def load_beat_map(track_id: str, *, media_root: Path | None = None) -> dict:
    """Read the complete R226 beat contract without writing or starting analysis."""
    if not isinstance(track_id, str) or not re.fullmatch(r'[a-f0-9]{64}', track_id):
        raise BeatMapUnavailable('unknown_track', track_id)
    library_root = local_media_root(media_root) / 'library/music'
    folder = library_root / track_id
    try:
        metadata = json.loads((folder / 'track.json').read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        if (folder / 'track.json').is_symlink():
            raise BeatMapUnavailable('result_unreadable', track_id) from exc
        raise BeatMapUnavailable('unknown_track', track_id) from exc
    except (OSError, ValueError) as exc:
        raise BeatMapUnavailable('result_unreadable', track_id) from exc
    try:
        if metadata['file_sha256'] != track_id or not isinstance(metadata['title'], str) or not metadata['title'].strip():
            raise ValueError('invalid track identity or title')
        if isinstance(metadata['duration_seconds'], bool) or not math.isfinite(metadata['duration_seconds']) or metadata['duration_seconds'] <= 0:
            raise ValueError('invalid track duration')
        with _analysis_queues_lock:
            queues = list(_analysis_queues)
        for queue in queues:
            if queue.library.root == library_root:
                beat_state = queue.state(track_id).get('beat', {})
                if beat_state.get('status') in ('queued', 'analyzing'):
                    raise BeatMapUnavailable(beat_state['status'], track_id)
                if beat_state.get('status') == 'failed':
                    raise BeatMapUnavailable('beat_failed', track_id, beat_state['failure']['code'])
        path = folder / 'analysis.json'
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError as exc:
            if path.is_symlink():
                raise BeatMapUnavailable('result_unreadable', track_id) from exc
            raise BeatMapUnavailable('queued', track_id) from exc
        if data['file_sha256'] != track_id or data['duration_seconds'] != metadata['duration_seconds']:
            raise ValueError('analysis does not match track')
        beat = data['beat']
        status = beat['status']
        if status in ('queued', 'analyzing'):
            raise BeatMapUnavailable(status, track_id)
        if status == 'failed':
            code = beat['failure']['code']
            if not isinstance(code, str) or not code:
                raise ValueError('missing beat failure code')
            raise BeatMapUnavailable('beat_failed', track_id, code)
        # Tags are deliberately outside this read contract; their failure cannot hide a good beat map.
        schema = read_json(ROOT / 'schemas/music-analysis.schema.json', '分析结果规范')['properties']
        required = ('schema_version', 'file_sha256', 'duration_seconds', 'registry_version', 'beat')
        Draft202012Validator({'type': 'object', 'required': list(required),
                             'properties': {k: schema[k] for k in required}}).validate(data)
        _check_beat_map_shape(dict(duration_seconds=data['duration_seconds'], **beat))
        result = dict(track_id=track_id, title=metadata['title'], duration_seconds=round(data['duration_seconds'], 3),
                      **beat_metrics(beat), beats=[round(t, 3) for t in beat['beats']],
                      downbeats=[round(t, 3) for t in beat['downbeats']], beat_energy=list(beat['beat_energy']),
                      sections=[dict(start=round(section['start'], 3), end=round(section['end'], 3), kind=section['kind']) for section in beat['sections']],
                      registry_version=data['registry_version'])
        _check_beat_map_shape(result)
        return result
    except BeatMapUnavailable:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError, MusicError, ValidationError) as exc:
        raise BeatMapUnavailable('result_unreadable', track_id) from exc


def failure(code):
    return {'status': 'failed', 'failure': {'code': code, 'retryable': code != 'audio_unreadable'}}


def run_worker(track, folder, part, *, timeout=180):
    python = ROOT / '.tools/music-analysis' / ('Scripts/python.exe' if __import__('os').name == 'nt' else 'bin/python')
    request = {'audio': str(folder / track['audio_file']), 'part': part, 'duration_seconds': track['duration_seconds']}
    try:
        result = subprocess.run([str(python), str(ROOT / 'scripts/music_analysis/worker.py')], input=json.dumps(request), capture_output=True, text=True, timeout=timeout, check=True)
        data = json.loads(result.stdout)
        if not isinstance(data, dict) or not all(p in data for p in (('beat', 'tags') if part == 'all' else (part,))):
            raise ValueError('incomplete worker response')
        return data
    except subprocess.TimeoutExpired:
        return {p: failure('timeout') for p in (('beat', 'tags') if part == 'all' else (part,))}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {p: failure('worker_error') for p in (('beat', 'tags') if part == 'all' else (part,))}


class AnalysisQueue:
    def __init__(self, library, *, worker=run_worker):
        self.library, self.worker = library, worker
        self.condition = threading.Condition(threading.RLock())
        self.pending = deque()
        self.active = None
        self.errors = {}
        self.thread = None
        self.stopping = False
        with _analysis_queues_lock:
            _analysis_queues.add(self)

    def start(self, server=None):
        with self.condition:
            if self.thread:
                return
            self.enqueue_missing()
            self.thread = threading.Thread(target=self._loop, name='music-analysis', daemon=True)
            self.thread.start()
        if server is not None:
            original_close = server.server_close
            def close():
                self.close()
                original_close()
            server.server_close = close

    def enqueue_missing(self):
        for track in self.library.list_tracks():
            self.enqueue_if_missing(track)

    def enqueue_if_missing(self, track):
        with self.condition:
            if read_analysis(self.library.root / track['file_sha256'], track) is None:
                self.enqueue(track['file_sha256'], 'all')

    def enqueue(self, identifier, part):
        if part not in ('beat', 'tags', 'all'):
            raise MusicError('分析部分必须是 beat 或 tags')
        if not any(t['file_sha256'] == identifier for t in self.library.list_tracks()):
            raise MusicError('曲目不存在')
        with self.condition:
            # Merge queued requests; never run the same part twice on repeated clicks.
            if self.active and self.active[0] == identifier:
                if self.active[1] in (part, 'all'):
                    return self.state(identifier)
                if part == 'all':
                    part = 'tags' if self.active[1] == 'beat' else 'beat'
            for i, (key, oldpart) in enumerate(self.pending):
                if key == identifier:
                    self.pending[i] = (key, oldpart if oldpart == part else 'all')
                    return self.state(identifier)
            self.errors.pop(identifier, None)
            self.pending.append((identifier, part))
            self.condition.notify_all()
            return self.state(identifier)

    def state(self, identifier):
        with self.condition:
            result = {}
            if self.active and self.active[0] == identifier:
                result.update({p: {'status': 'analyzing', 'queue_position': 0} for p in (('beat', 'tags') if self.active[1] == 'all' else (self.active[1],))})
            for i, (key, part) in enumerate(self.pending):
                if key == identifier:
                    result.update({p: {'status': 'queued', 'queue_position': i + int(self.active is not None and self.active[0] != identifier)} for p in (('beat', 'tags') if part == 'all' else (part,))})
            result.update(copy.deepcopy(self.errors.get(identifier, {})))
            return result

    def _loop(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.pending or self.stopping)
                if self.stopping:
                    return
                self.active = self.pending.popleft()
                identifier, part = self.active
                self.errors.pop(identifier, None)
            parts = ('beat', 'tags') if part == 'all' else (part,)
            try:
                track = next(t for t in self.library.list_tracks() if t['file_sha256'] == identifier)
                folder = self.library.root / identifier
                old = read_analysis(folder, track)
                data = old or dict(schema_version=1, file_sha256=identifier, duration_seconds=track['duration_seconds'], beat=failure('analysis_missing'), tags=failure('analysis_missing'))
                try:
                    output = self.worker(track, folder, part)
                    for p in parts:
                        data[p] = output[p]
                    data['registry_version'] = registry()['registry_version']
                    validate_analysis(data)
                except Exception:
                    for p in parts:
                        data[p] = failure('worker_error')
                    data['registry_version'] = registry()['registry_version']
                    validate_analysis(data)
                write_json(folder / 'analysis.json', data)
            except Exception:
                # Keep Studio alive, but do not disguise a failed read/write as missing analysis.
                with self.condition:
                    self.errors[identifier] = {p: failure('worker_error') for p in parts}
            finally:
                with self.condition:
                    self.active = None
                    self.condition.notify_all()

    def wait_idle(self, timeout=180):
        with self.condition:
            return self.condition.wait_for(lambda: not self.pending and self.active is None, timeout=timeout)

    def close(self):
        with self.condition:
            self.stopping = True
            self.condition.notify_all()
        if self.thread:
            self.thread.join(timeout=185)
