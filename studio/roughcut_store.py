"""R226 local records: explicit read failures, cross-process CAS and atomic writes."""
from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from jsonschema import Draft202012Validator
from studio.project_store import _thread_lock

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {name: json.loads((ROOT / 'schemas' / name).read_text()) for name in
           ('roughcut-api.schema.json', 'editing-presets.schema.json')}
CATALOG = SCHEMAS['roughcut-api.schema.json']['x-error-catalog']
VALIDATORS = {}
HELD_LOCKS = threading.local()
NOTICE_GROUPS = {
    'N1': 'csrf_invalid origin_forbidden host_forbidden body_invalid revision_invalid request_invalid roughcut_command_invalid roughcut_job_action_invalid music_count_invalid playlist_invalid preset_not_found preset_invalid occurrence_not_found overrides_invalid swap_boundary_invalid transcript_selection_invalid project_not_found roughcut_job_not_found',
    'N2': 'revision_conflict roughcut_inputs_stale', 'N3': 'selection_not_confirmed',
    'N4': 'roughcut_state_unreadable roughcut_job_unreadable settings_invalid builtin_presets_invalid shots_invalid',
    'N5': 'preset_write_failed', 'N6': 'beat_analysis_unavailable beat_map_missing',
    'N7': 'song_too_short', 'N8': 'transcription_unavailable transcript_failed',
    'N9': 'transcript_unreadable transcript_invalid',
    'N10': 'editor_diagnostics_unreadable editor_readiness_invalid',
    'N11': 'draft_failed runtime_unavailable', 'N12': 'preview_failed',
    'N13': 'edl_provenance_required',
}
TITLES = dict(zip(NOTICE_GROUPS, ('这次操作没成功','这件作品刚在别处改过','精选还没确认','读不到这件作品的粗剪记录','这个预设没存上','拍子分析还不能用','这首歌比粗剪短，排不下','这几段自拍没转写成','读不到自拍的转写结果','读不到剪辑软件的状态','草稿没出成','预览没生成出来','这件作品还不能出草稿')))
CODE_NOTICE = {code: group for group, codes in NOTICE_GROUPS.items() for code in codes.split()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                     separators=(',', ':')).encode()).hexdigest()


def validate(name, value, *, presets=False, code='request_invalid'):
    file = 'editing-presets.schema.json' if presets else 'roughcut-api.schema.json'
    key = (file, name)
    if key not in VALIDATORS:
        VALIDATORS[key] = Draft202012Validator({**SCHEMAS[file], '$ref': '#/$defs/' + name})
    if not VALIDATORS[key].is_valid(value):
        raise RoughcutError(code)


class RoughcutError(ValueError):
    def __init__(self, code, details=None, *, previous=False):
        if code not in CATALOG:
            code = 'request_invalid'
        self.code = code
        spec = CATALOG[code]
        self.http_status = spec['http_status']
        allowed = SCHEMAS['roughcut-api.schema.json']['$defs']['error_details']['properties']
        details = {k: copy.deepcopy(v) for k, v in (details or {}).items() if k in allowed}
        state = spec['design_state']
        if previous and code in ('song_entry_unavailable','shot_too_short','result_unreadable','beat_map_invalid'):
            state = 'cut-rearrange-failed'
        message = TITLES.get(CODE_NOTICE.get(code), '这次操作没成功')
        if code == 'shot_too_short':
            message = f'有 {details.get("short_shot_count", 1)} 个镜头太短，按这首歌的拍子排不进去'
        elif code in ('result_unreadable','beat_map_invalid'):
            message = '读不到这首歌的拍子分析结果'
        elif code in ('unknown_track','music_track_not_found'):
            message = '音乐库里找不到这首歌了'
        elif code == 'editor_choice_unreadable':
            message = '读不到这件作品用什么出草稿'
        elif code == 'editor_not_ready':
            message = TITLES['N10']
        self.failure = dict(code=code, http_status=self.http_status, message=message,
                            retryable=spec['retryable'], fixer=spec['fixer'], design_state=state, details=details)
        if code == 'beat_failed' and details.get('upstream_failure_code') == 'audio_unreadable':
            self.failure['retryable'] = False
        if code == 'preview_failed' and details.get('dependency')=='roughcut_preview_renderer':
            self.failure.update(fixer='wait_dependency',retryable=False)
        if code == 'draft_failed' and details.get('dependency')=='roughcut_guide_exporter':
            self.failure.update(fixer='wait_dependency',retryable=False)
        super().__init__(code)

    def response(self):
        return {'ok': False, 'error': copy.deepcopy(self.failure)}


def safe_path(path, root, code, *, absent=False):
    """Check lexical parents before resolving, so a dangling link is never absence."""
    path, root = Path(path), Path(root).resolve()
    try:
        relative = path.relative_to(root)
        if '..' in relative.parts or any((root / Path(*relative.parts[:i])).is_symlink()
                                       for i in range(1, len(relative.parts) + 1)):
            raise RoughcutError(code)
        if not path.exists():
            if absent:
                return path
            raise RoughcutError(code)
        if not path.is_file() or not path.stat().st_mode & 0o444:
            raise RoughcutError(code)
        if not path.resolve().is_relative_to(root):
            raise RoughcutError(code)
        return path
    except (OSError, ValueError) as exc:
        if isinstance(exc, RoughcutError):
            raise
        raise RoughcutError(code) from exc


def atomic_json(path, value, code):
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, allow_nan=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError) as exc:
        raise RoughcutError(code) from exc
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


class JsonReader:
    """Cache by filesystem identity; share a single parsed input across six recipes."""
    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()
        self.stats = dict(reads=0, bytes=0)
        self.loads = {}

    def read(self, path, root, code, *, optional=False):
        path = safe_path(path, root, code, absent=optional)
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RoughcutError(code) from exc
        stamp = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino)
        with self.lock:
            cached = self.cache.get(path)
            if cached and cached[0] == stamp:
                return copy.deepcopy(cached[1])
            try:
                raw = path.read_bytes()
                value = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
                if value is None:
                    raise ValueError('null record')
            except (OSError, ValueError, UnicodeError) as exc:
                raise RoughcutError(code) from exc
            self.stats['reads'] += 1
            self.stats['bytes'] += len(raw)
            entry = self.loads.setdefault(path, dict(reads=0, bytes=0))
            entry['reads'] += 1
            entry['bytes'] += len(raw)
            self.cache[path] = (stamp, value)
            return copy.deepcopy(value)


class RoughcutStore:
    def __init__(self, state_dir, reader=None):
        self.root = Path(state_dir).resolve()
        self.reader = reader or JsonReader()
        self.presets_path = self.root / 'settings/editing-presets.json'
        self.validated_states = {}

    def state_path(self, piece_id):
        return self.root / 'roughcut/states' / (hashlib.sha256(piece_id.encode()).hexdigest() + '.json')

    def job_path(self, job_id):
        return self.root / 'roughcut/jobs' / (hashlib.sha256(job_id.encode()).hexdigest() + '.json')

    @staticmethod
    def validate_artifacts(artifacts, index, revision):
        if not isinstance(index,dict) or set(index)!={a['id'] for a in artifacts}:
            raise RoughcutError('roughcut_state_unreadable')
        for artifact in artifacts:
            validate('artifact',artifact,code='roughcut_state_unreadable')
            locator=index[artifact['id']];allowed=locator['allowed_root'];relative=Path(locator['relative_path'])
            derived=bool(re.fullmatch(r'(?:draft-project|ai-analysis)/roughcut/'+str(revision)+r'/[a-f0-9]{32}',allowed))
            if ((allowed not in ('ai-analysis/shots/frames','ai-analysis/roughcut') and not derived) or relative.is_absolute() or '..' in relative.parts or not relative.is_relative_to(allowed) or
                locator['content_type']!=artifact['content_type'] or artifact['revision']!=revision):
                raise RoughcutError('roughcut_state_unreadable')
            if 'stamp' in locator and (not isinstance(locator['stamp'],list) or len(locator['stamp'])!=3 or any(type(n) is not int or n<0 for n in locator['stamp'])):
                raise RoughcutError('roughcut_state_unreadable')

    @contextmanager
    def locked(self, kind, identity):
        path = self.root / 'roughcut/locks' / (hashlib.sha256((kind + ':' + identity).encode()).hexdigest() + '.lock')
        safe_path(path, self.root, 'roughcut_state_unreadable', absent=True)
        with _thread_lock(path):
            held = getattr(HELD_LOCKS, 'paths', set())
            if path in held:
                yield
                return
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'a+b') as handle:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                    HELD_LOCKS.paths = held | {path}
                    try:
                        yield
                    finally:
                        HELD_LOCKS.paths = held
                        fcntl.flock(handle, fcntl.LOCK_UN)
            except OSError as exc:
                raise RoughcutError('roughcut_state_unreadable') from exc

    def read_state(self, piece_id):
        path = self.state_path(piece_id)
        value = self.reader.read(path, self.root, 'roughcut_state_unreadable', optional=True)
        if value is None:
            return None
        stamp = self.reader.cache[path][0]
        if self.validated_states.get(path) == stamp:
            return value
        try:
            if (value['schema_version'] != 'roughcut_store_v1' or value['piece_id'] != piece_id or
                type(value['revision']) is not int or value['revision'] < 1 or
                value['status'] not in ('no_music','queued','arranging','ready','failed','stopping','stopped')):
                raise RoughcutError('roughcut_state_unreadable')
            validate('selection', value['selection'], code='roughcut_state_unreadable')
            validate('input_binding', value['input_binding'], code='roughcut_state_unreadable')
            if value['published'] is not None:
                published = value['published']
                validate('plan', published['plan'], code='roughcut_state_unreadable')
                validate('input_binding', published['binding'], code='roughcut_state_unreadable')
                if type(published['revision']) is not int or published['revision'] < 1:
                    raise RoughcutError('roughcut_state_unreadable')
                validate('preset', published['preset'], presets=True, code='roughcut_state_unreadable')
                self.validate_artifacts(published['artifacts'],published['artifact_index'],published['revision'])
                if 'playback' in published:
                    validate('playback',published['playback'],code='roughcut_state_unreadable')
                    if not isinstance(published.get('planner_inputs'),dict) or not isinstance(published.get('music_facts'),dict):
                        raise RoughcutError('roughcut_state_unreadable')
                for row in published['source_audio']:
                    validate('source_audio', row, code='roughcut_state_unreadable')
            if (not isinstance(value['analysis'], list) or not isinstance(value['preset_previews'], list) or
                (value['job_id'] is not None and not isinstance(value['job_id'], str))):
                raise RoughcutError('roughcut_state_unreadable')
            for item in value['analysis']:
                validate('analysis', item, code='roughcut_state_unreadable')
            for item in value['preset_previews']:
                validate('preset_preview', item, code='roughcut_state_unreadable')
            if value['failure'] is not None:
                validate('failure', value['failure'], code='roughcut_state_unreadable')
            if value.get('draft_failure') is not None:
                validate('failure',value['draft_failure'],code='roughcut_state_unreadable')
            if value.get('draft_published') is not None:
                draft=value['draft_published']
                validate('draft_result',draft['result'],code='roughcut_state_unreadable')
                validate('input_binding',draft['binding'],code='roughcut_state_unreadable')
                validate('editor_choice',draft['choice'],code='roughcut_state_unreadable')
                if type(draft['plan_revision']) is not int or draft['plan_revision']<1:
                    raise RoughcutError('roughcut_state_unreadable')
                self.validate_artifacts(draft['artifacts'],draft['artifact_index'],draft['plan_revision'])
                if set(draft['result']['artifact_ids'])!=set(draft['artifact_index']) or draft['guide_artifact_id'] not in draft['artifact_index'] or (draft['project_artifact_id'] is not None and draft['project_artifact_id'] not in draft['artifact_index']):
                    raise RoughcutError('roughcut_state_unreadable')
            if 'retired_artifact_ids' in value and (not isinstance(value['retired_artifact_ids'],list) or any(not isinstance(a,str) for a in value['retired_artifact_ids'])):
                raise RoughcutError('roughcut_state_unreadable')
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            if isinstance(exc, RoughcutError):
                raise
            raise RoughcutError('roughcut_state_unreadable') from exc
        self.validated_states[path] = stamp
        return value

    def write_state(self, piece_id, value):
        path = self.state_path(piece_id)
        safe_path(path, self.root, 'roughcut_state_unreadable', absent=True)
        atomic_json(path, value, 'roughcut_state_unreadable')

    def read_job(self, job_id):
        value = self.reader.read(self.job_path(job_id), self.root, 'roughcut_job_unreadable', optional=True)
        if value is None:
            raise RoughcutError('roughcut_job_not_found')
        if not isinstance(value, dict) or not isinstance(value.get('public'), dict) or value['public'].get('job_id') != job_id:
            raise RoughcutError('roughcut_job_unreadable')
        validate('job_response', value['public'], code='roughcut_job_unreadable')
        for name in ('binding', 'selection'):
            validate('input_binding' if name == 'binding' else name, value.get(name), code='roughcut_job_unreadable')
        if 'command_request' in value:
            validate('command_request', value['command_request'], code='roughcut_job_unreadable')
            validate('input_binding', value.get('accepted_binding'), code='roughcut_job_unreadable')
        if value['public']['kind']=='draft':
            validate('editor_choice',value.get('choice'),code='roughcut_job_unreadable')
            if type(value.get('plan_revision')) is not int or value['plan_revision']<1 or value['binding']['editor_choice_revision']!=value['choice']['revision'] or value['binding']['edl_digest'] is None:
                raise RoughcutError('roughcut_job_unreadable')
        if not isinstance(value.get('confirmation_digest'), str) or not isinstance(value.get('media_ids'), list) or not isinstance(value.get('shot_ids'), list):
            raise RoughcutError('roughcut_job_unreadable')
        return value

    def write_job(self, value):
        path = self.job_path(value['public']['job_id'])
        safe_path(path, self.root, 'roughcut_job_unreadable', absent=True)
        atomic_json(path, value, 'roughcut_job_unreadable')

    def mine(self):
        value = self.reader.read(self.presets_path, self.root, 'preset_store_unreadable', optional=True)
        if value is not None:
            validate('mine_store', value, presets=True, code='preset_store_unreadable')
            ids = [p['id'] for p in value['presets']]
            if len(set(ids)) != len(ids):
                raise RoughcutError('preset_store_unreadable')
        return value

    def write_mine(self, value):
        validate('mine_store', value, presets=True, code='preset_invalid')
        safe_path(self.presets_path, self.root, 'preset_store_unreadable', absent=True)
        atomic_json(self.presets_path, value, 'preset_write_failed')
