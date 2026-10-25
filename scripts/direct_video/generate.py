"""Persisted direct-video generation; all model traffic uses llm_common.

Shot instructions originate in the user's direct-video-shots skill; motion rules
partly derive from HeyGen HyperFrames (Apache-2.0).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time
import uuid
import wave

import llm_common
from direct_video.lint import declared_seconds, lint
from direct_video.media import FPS, LocalMedia, OutputCheckError, atomic_bytes, wav_seconds
from direct_video.revisions import RevisionMixin, empty_look
from direct_video.revision_library import RevisionLibrary, read_json

MODEL = 'claude-opus-5-5'
RULES = Path(__file__).with_name('rules') / 'shots.md'
SAFE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')


class DirectVideoError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def process_alive(pid) -> bool:
    if type(pid) is not int or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def dump(path: Path, value) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode())


def validate_design(value: dict, shots: list[dict]) -> dict:
    if not isinstance(value, dict):
        raise DirectVideoError('design_invalid')
    palette = value.get('palette')
    scale, banned, rows = value.get('typeScale'), value.get('banned'), value.get('perShot')
    valid = (isinstance(palette, dict) and set(palette) == {'background', 'primary', 'accent', 'neutral'}
             and all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in palette.values())
             and isinstance(scale, list) and len(scale) == 3 and all(type(n) is int and 34 <= n <= 500 for n in scale)
             and scale[0] > scale[1] > scale[2]
             and isinstance(banned, list) and 3 <= len(banned) <= 6
             and all(isinstance(b, str) and 0 < len(b.strip()) <= 500 for b in banned)
             and isinstance(value.get('motionRules'), str) and 0 < len(value['motionRules'].strip()) <= 1000
             and isinstance(rows, list) and len(rows) == len(shots))
    if not valid:
        raise DirectVideoError('design_invalid')
    for row, shot in zip(rows, shots):
        if not isinstance(row, dict) or row.get('shotId') != shot['shotId'] or any(
            not isinstance(row.get(k), str) or not 0 < len(row[k].strip()) <= 1000 for k in ('mainAction', 'takeaway')
        ):
            raise DirectVideoError('design_invalid')
    return {k: value[k] for k in ('palette', 'typeScale', 'motionRules', 'banned', 'perShot')}


def validate_code(value) -> str:
    code = value.get('code') if isinstance(value, dict) else None
    if not isinstance(code, str) or len(code) >= 100000 or not code.lower().startswith('<!doctype html>') or 'window.seekFrame' not in code or not re.search(r'data-role\s*=\s*[\'"]header[\'"]', code):
        raise DirectVideoError('code_invalid')
    return code


def parse_shots(body: dict) -> list[dict]:
    if body.get('model', MODEL) != MODEL:
        raise DirectVideoError('model_invalid')
    if not isinstance(body.get('style', ''), str) or len(body.get('style', '')) > 4000:
        raise DirectVideoError('style_invalid')
    if ('script' in body) == ('storyboard' in body):
        raise DirectVideoError('script_invalid')
    if 'script' in body:
        if not isinstance(body['script'], str) or len(body['script']) > 20000:
            raise DirectVideoError('script_invalid')
        rows = [{'shotId': f'{i:02d}', 'dialogue': line.strip()}
                for i, line in enumerate((s for s in body['script'].splitlines() if s.strip()), 1)]
    else:
        storyboard = body['storyboard']
        rows = storyboard.get('shots') if isinstance(storyboard, dict) else None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 99:
        raise DirectVideoError('script_invalid')
    result, ids = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise DirectVideoError('script_invalid')
        sid, dialogue = row.get('shotId'), row.get('dialogue')
        if not isinstance(sid, str) or not SAFE_ID.fullmatch(sid) or sid in ids or not isinstance(dialogue, str) or not 0 < len(dialogue.strip()) <= 2000:
            raise DirectVideoError('script_invalid')
        ids.add(sid)
        result.append({'shotId': sid, 'dialogue': dialogue})
    if sum(len(s['dialogue']) for s in result) > 20000:
        raise DirectVideoError('script_invalid')
    return result


def allocate_timing(shots: list[dict], duration: float, transcript: dict | None) -> tuple[list[float], str]:
    """Use only exact acoustic-token boundaries; otherwise label proportional time."""
    def key(text):
        return ''.join(c.casefold() for c in text if c.isalnum())
    if not math.isfinite(duration):
        raise DirectVideoError('narration_invalid')
    total_frames = round(duration * FPS)
    if total_frames < len(shots):
        raise DirectVideoError('narration_invalid')
    boundaries = None
    if isinstance(transcript, dict):
        words = [w for s in transcript.get('segments', []) for w in s.get('words', [])]
        words = transcript.get('words') or words
        try:
            tokens = [key(w['text']) for w in words]
            expected = ''.join(key(s['dialogue']) for s in shots)
            if words and expected and ''.join(tokens) == expected:
                starts, previous_end = {}, 0.0
                offset = 0
                for word, token in zip(words, tokens):
                    start, end = float(word['start']), float(word['end'])
                    if not all(math.isfinite(t) for t in (start, end)) or start < previous_end or not start < end <= duration:
                        raise ValueError('invalid acoustic time')
                    if token:
                        starts[offset] = start
                    offset += len(token)
                    previous_end = end
                cursor = 0
                boundaries = [0]
                for shot in shots[:-1]:
                    cursor += len(key(shot['dialogue']))
                    boundaries.append(round(starts[cursor] * FPS))
                boundaries.append(total_frames)
                if any(b <= a for a, b in zip(boundaries, boundaries[1:])):
                    boundaries = None
        except (KeyError, TypeError, ValueError):
            boundaries = None
    source = 'narration' if boundaries is not None else 'proportional'
    if boundaries is None:
        weights = [len(s['dialogue']) for s in shots]
        cursor = 0
        boundaries = [0]
        for index, weight in enumerate(weights[:-1], 1):
            cursor += weight
            boundary = round(total_frames * cursor / sum(weights))
            boundaries.append(max(boundaries[-1] + 1, min(total_frames - (len(shots) - index), boundary)))
        boundaries.append(total_frames)
    return [(b - a) / FPS for a, b in zip(boundaries, boundaries[1:])], source


def failure_code(exc: Exception, default='generation_failed') -> str:
    if isinstance(exc, OutputCheckError):
        return 'output_check_failed'
    if isinstance(exc, DirectVideoError):
        return exc.code
    if isinstance(exc, llm_common.LLMError):
        text = str(exc).lower()
        return 'model_timeout' if 'timed out' in text else 'claude_cli_unavailable' if 'required' in text or 'could not start' in text else 'model_failed'
    return default


class Generator(RevisionMixin):
    def __init__(self, state_dir: Path, *, workers: int | None = None, model_call=None, media=None):
        self.root = state_dir / 'direct-jobs'
        self.root.mkdir(parents=True, exist_ok=True)
        workers = workers if workers is not None else int(os.environ.get('DIRECT_VIDEO_WORKERS', '3'))
        if type(workers) is not int or not 1 <= workers <= 3:
            raise ValueError('DIRECT_VIDEO_WORKERS must be between 1 and 3')
        self.workers = workers
        self.slots = threading.BoundedSemaphore(workers)
        self.lock = threading.RLock()
        self.active = set()
        self.model_call = model_call or llm_common.generate_text
        self.media = media or LocalMedia()
        self.library = RevisionLibrary(state_dir)
        self.recover()

    def path(self, project_id: str, job_id: str) -> Path:
        if not SAFE_ID.fullmatch(project_id) or not re.fullmatch(r'dv_[a-f0-9]{24}', job_id):
            raise DirectVideoError('job_not_found')
        path = self.root / project_id / job_id
        if not path.resolve().is_relative_to(self.root.resolve()):
            raise DirectVideoError('job_not_found')
        return path

    def read(self, project_id: str, job_id: str) -> dict:
        with self.lock:
            try:
                root = self.path(project_id, job_id)
                job = json.loads((root / 'job.json').read_text())
            except FileNotFoundError as exc:
                raise DirectVideoError('job_not_found') from exc
            if self.upgrade_versions(root, job):
                self.save(root, job, touch_updated_at=False)
            return job

    def save(self, root: Path, job: dict, *, touch_updated_at=True) -> None:
        if touch_updated_at:
            job['updatedAt'] = now()
        dump(root / 'job.json', job)

    def recover(self) -> None:
        for path in self.root.glob('*/*/job.json'):
            job = json.loads(path.read_text())
            owner = job.get('_workerPid')
            if process_alive(owner):
                continue
            interrupted_work = job['status'] in {'designing', 'writing', 'rendering', 'composing'} or job['narration']['status'] == 'aligning'
            if (interrupted_work
                    or any(s.get('look', {}).get('status') == 'running' for s in job['shots'])):
                if owner is not None:
                    # Only reclaim renderer locks belonging to this job after
                    # its recorded worker process is proven to have exited.
                    locks = list(path.parent.glob('cache/*/.render.lock'))
                    locks += [path.parent / 'composition/.export.lock', path.parent / 'composition/render/.render.lock']
                    for lock in locks:
                        lock.unlink(missing_ok=True)
                for shot in job['shots']:
                    if shot['status'] in {'queued', 'writing', 'written', 'rendering'}:
                        shot.update(status='interrupted', failureCode='process_interrupted')
                    if shot.get('look', {}).get('status') == 'running':
                        shot['look'].update(status='failed', failureCode='look_failed')
                    for version in shot.get('versions', []):
                        if (version.get('look') or {}).get('status') == 'running':
                            version['look'].update(status='failed', failureCode='look_failed')
                        if (version.get('verify') or {}).get('status') == 'running':
                            version['verify'].update(status='failed', failureCode='verify_failed')
                if job['design']['status'] == 'writing':
                    job['design']['status'] = 'failed'
                if job['narration']['status'] == 'aligning':
                    job['narration']['status'] = 'invalid'
                if job['output']['status'] == 'composing':
                    job['output'].update(status='failed', composedAt=None)
                if interrupted_work:
                    job.update(status='failed', failureCode='process_interrupted')
                job.pop('_workerPid', None)
                self.save(path.parent, job, touch_updated_at=interrupted_work)

    def latest(self, project_id: str) -> dict | None:
        if not SAFE_ID.fullmatch(project_id):
            raise DirectVideoError('job_not_found')
        with self.lock:
            paths = list((self.root / project_id).glob('dv_*/job.json'))
            jobs = [json.loads(p.read_text()) for p in paths]
            latest = max(jobs, key=lambda j: j['createdAt']) if jobs else None
            return self.read(project_id, latest['jobId']) if latest else None

    def start(self, project_id: str, job_id: str, action, *args, touch_updated_at=True) -> None:
        key = (project_id, job_id)
        with self.lock:
            job = self.read(project_id, job_id)
            if key in self.active or process_alive(job.get('_workerPid')):
                raise DirectVideoError('job_busy')
            job['_workerPid'] = os.getpid()
            self.save(self.path(project_id, job_id), job, touch_updated_at=touch_updated_at)
            self.active.add(key)
        def run():
            root = self.path(project_id, job_id)
            try:
                action(project_id, job_id, *args)
            except Exception as exc:
                with self.lock:
                    job = self.read(project_id, job_id)
                    job.update(status='failed', failureCode=failure_code(exc))
                    if job['design']['status'] == 'writing':
                        job['design']['status'] = 'failed'
                    if job['narration']['status'] == 'aligning':
                        job['narration']['status'] = 'invalid'
                    if job['output']['status'] == 'composing':
                        job['output'].update(status='failed', composedAt=None)
                    self.save(root, job, touch_updated_at=touch_updated_at)
            finally:
                with self.lock:
                    job = self.read(project_id, job_id)
                    job.pop('_workerPid', None)
                    self.save(root, job, touch_updated_at=touch_updated_at)
                    self.active.discard(key)
        threading.Thread(target=run, daemon=True, name='direct-video-job').start()

    def create(self, project_id: str, body: dict, *, background=True) -> dict:
        rows = parse_shots(body)
        job_id = 'dv_' + uuid.uuid4().hex[:24]
        root = self.path(project_id, job_id)
        timestamp = now()
        job = {'jobId': job_id, 'projectId': project_id, 'model': MODEL, 'style': body.get('style', ''),
               'status': 'designing', 'createdAt': timestamp, 'updatedAt': timestamp, 'failureCode': None,
               'design': {'status': 'pending', 'palette': None, 'typeScale': None, 'motionRules': None, 'banned': []},
               'shots': [{**row, 'mainAction': None, 'estimatedSeconds': round(len(row['dialogue']) / 5.1, 1),
                          'measuredSeconds': None, 'timingSource': 'estimate', 'status': 'queued', 'failureCode': None,
                          'attempts': 0, 'lastInstruction': None, 'writingStartedAt': None, 'writtenAt': None, 'renderedAt': None,
                          'codeChars': 0, 'posterRevision': 0, 'checks': {'errors': [], 'warnings': []},
                          'currentVersion': 0, 'versions': [], 'boxes': [], 'look': empty_look(), 'sample': False} for row in rows],
               'narration': {'status': 'none', 'durationSeconds': None},
               'output': {'status': 'none', 'composedAt': None, 'kind': 'silent', 'durationSeconds': None, 'frames': None, 'revision': 0,
                          'checks': {'playable': 'unknown', 'avOffsetSeconds': None, 'blackFrames': None}}}
        with self.lock:
            self.save(root, job)
        if background:
            self.start(project_id, job_id, self.generate)
        return copy.deepcopy(job)

    def call(self, system: str, user: dict, *, image_paths=None):
        options = {'image_paths': image_paths} if image_paths else {}
        text = self.model_call(provider='claude_cli', model=MODEL, system_prompt=system,
                               user_prompt=json.dumps(user, ensure_ascii=False), **options)
        try:
            return llm_common.parse_json_response(text, require=dict)
        except ValueError as exc:
            raise DirectVideoError('model_json_invalid') from exc

    def record(self, root: Path, phase: str, **details) -> None:
        """Keep measured private evidence separate from the public job contract."""
        with self.lock:
            path = root / 'metrics.json'
            events = json.loads(path.read_text()) if path.exists() else []
            events.append({'phase': phase, 'recordedAt': now(), **details})
            dump(path, events)

    def timed_call(self, root: Path, phase: str, system: str, user: dict, *, image_paths=None, **details):
        started = time.perf_counter()
        status, code = 'passed', None
        try:
            return self.call(system, user, image_paths=image_paths)
        except Exception as exc:
            status, code = 'failed', failure_code(exc)
            raise
        finally:
            self.record(root, phase, elapsedSeconds=round(time.perf_counter() - started, 3),
                        status=status, failureCode=code, **details)

    def render(self, root: Path, shot: dict) -> dict | None:
        started = time.perf_counter()
        status = 'passed'
        try:
            return self.media.render(root, shot)
        except Exception:
            status = 'failed'
            raise
        finally:
            self.record(root, 'render', shotId=shot['shotId'], status=status,
                        elapsedSeconds=round(time.perf_counter() - started, 3))

    def record_layout(self, root: Path, shot: dict, result: dict | None) -> None:
        if result is None:
            return
        dump(root / 'checks' / 'layout' / (shot['shotId'] + '.json'), result)
        if result['status'] != 'measured':
            return
        checks = shot['checks']
        checks['warnings'] = [warning for warning in checks['warnings'] if warning['code'] != 'layout_bottom_gap'] + result['warnings']
        dump(root / 'checks' / (shot['shotId'] + '.json'), checks)

    def generate(self, project_id: str, job_id: str) -> None:
        root = self.path(project_id, job_id)
        with self.lock:
            job = self.read(project_id, job_id)
            job['design']['status'] = 'writing'
            self.save(root, job)
        design = validate_design(self.timed_call(root, 'design',
            '为竖屏口播设计全片视觉系统。只输出 JSON，包含 palette（background、primary、accent、neutral 的六位十六进制颜色），'
            'typeScale（三档从大到小整数），motionRules（一句话），banned（3–6 条），perShot（shotId、唯一主动作 mainAction、观众读到的 takeaway）。\n' + self.library.rules(RULES),
            {'shots': [{'shotId': s['shotId'], 'dialogue': s['dialogue']} for s in job['shots']], 'style': job['style']}), job['shots'])
        dump(root / 'design.json', design)
        with self.lock:
            job['design'] = {'status': 'done', **{k: v for k, v in design.items() if k != 'perShot'}}
            for shot, row in zip(job['shots'], design['perShot']):
                shot['mainAction'] = row['mainAction']
            job['status'] = 'writing'
            self.save(root, job)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            list(pool.map(lambda sid: self.write_shot(project_id, job_id, sid), [s['shotId'] for s in job['shots']]))
        self.finish_shots(project_id, job_id)

    def finish_shots(self, project_id, job_id):
        with self.lock:
            job = self.read(project_id, job_id)
            failed = next((s for s in job['shots'] if s['status'] != 'rendered'), None)
            job.update(status='failed' if failed else 'ready', failureCode=failed['failureCode'] if failed else None)
            self.save(self.path(project_id, job_id), job)

    def write_shot(self, project_id: str, job_id: str, sid: str, instruction: str | None = None, *, retry_errors: list | None = None) -> None:
        root = self.path(project_id, job_id)
        with self.slots:
            with self.lock:
                job = self.read(project_id, job_id)
                index = next(i for i, s in enumerate(job['shots']) if s['shotId'] == sid)
                shot = job['shots'][index]
                shot.update(status='writing', failureCode=None, lastInstruction=instruction, writingStartedAt=now())
                job['status'] = 'writing'
                self.save(root, job)
            checks, phase = {'errors': [], 'warnings': []}, 'writing'
            try:
                design = json.loads((root / 'design.json').read_text())
                duration = shot['measuredSeconds'] or shot['estimatedSeconds']
                context = {'design': design, 'dialogue': shot['dialogue'], 'D': duration, 'timingSource': shot['timingSource'],
                           'shotId': sid, 'shotNumber': index + 1, 'totalShots': len(job['shots']),
                           'previousDialogue': job['shots'][index - 1]['dialogue'] if index else None,
                           'nextDialogue': job['shots'][index + 1]['dialogue'] if index + 1 < len(job['shots']) else None,
                           'instruction': instruction}
                with self.lock:
                    samples = self.library.closest(shot)
                    sample_images = []
                    for row in samples:
                        image = root / 'sample-context' / sid / (uuid.uuid4().hex + '.jpg')
                        atomic_bytes(image, self.library.poster(row['sampleId']).read_bytes())
                        sample_images.append(image)
                    if samples:
                        context['samples'] = samples
                if shot.get('_revisionRequest'):
                    context['request'] = shot['_revisionRequest']
                    context['boxes'] = shot['boxes']
                if retry_errors is not None:
                    context['errors'] = retry_errors
                if (instruction or retry_errors is not None) and (root / 'shots' / (sid + '.html')).exists():
                    context['previousCode'] = (root / 'shots' / (sid + '.html')).read_text()
                for attempt in range(2):
                    with self.lock:
                        current = self.read(project_id, job_id)
                        current['shots'][index]['attempts'] += 1
                        current['shots'][index]['writingStartedAt'] = now()
                        self.save(root, current)
                    value = {}
                    try:
                        value = self.timed_call(root, 'write', '只输出 JSON {"code": "完整 HTML"}。严格遵守以下镜头规则，不改口播。\n' + self.library.rules(RULES), context,
                                                image_paths=sample_images,
                                                shotId=sid, attempt=attempt + 1, instructionKind='retry' if retry_errors is not None else 'requested' if instruction else 'initial')
                        if isinstance(value.get('code'), str):
                            atomic_bytes(root / 'checks' / 'code-attempts' / f'{sid}-{uuid.uuid4().hex}.html', value['code'].encode())
                        code = validate_code(value)
                        checks = lint(code, shot['dialogue'], duration)
                    except DirectVideoError:
                        checks = {'errors': [{'code': 'code_invalid', 'message': '请输出完整 HTML、逐帧入口和页眉标记，且少于十万字。'}], 'warnings': []}
                    dump(root / 'checks' / (sid + '.json'), checks)
                    self.record(root, 'lint', shotId=sid, attempt=attempt + 1, checks=checks)
                    if not checks['errors']:
                        break
                    if attempt:
                        raise DirectVideoError('lint_failed_after_retry')
                    context['errors'] = checks['errors']
                    context['previousCode'] = value.get('code')
                atomic_bytes(root / 'shots' / (sid + '.html'), code.encode())
                with self.lock:
                    current = self.read(project_id, job_id)
                    current['shots'][index].update(status='written', writtenAt=now(), codeChars=len(code), checks=checks)
                    target = current['shots'][index]
                    target.update(boxes=[], look=empty_look())
                    request = target.pop('_revisionRequest', None)
                    self.snapshot_version(root, target, request, include_poster=False)
                    self.save(root, current)
                    current['shots'][index]['status'] = 'rendering'
                    current['status'] = 'rendering'
                    self.save(root, current)
                phase = 'rendering'
                layout = self.render(root, current['shots'][index])
                with self.lock:
                    current = self.read(project_id, job_id)
                    target = current['shots'][index]
                    self.record_layout(root, target, layout)
                    revision = max([target['posterRevision'], *[v['posterRevision'] for v in target['versions']]]) + 1
                    target.update(status='rendered', renderedAt=now(), posterRevision=revision)
                    target['boxes'] = read_json(root / 'boxes' / (sid + '.json'), [])
                    target['look'] = empty_look()
                    shutil.copyfile(root / 'posters' / (sid + '.jpg'),
                                    self.version_dir(root, sid, target['currentVersion']) / 'poster.jpg')
                    self.save_version(root, target)
                    self.save(root, current)
                self.review_shot(project_id, job_id, sid, bool(request))
            except Exception as exc:
                with self.lock:
                    current = self.read(project_id, job_id)
                    current['shots'][index].update(status='failed', failureCode=failure_code(exc, 'render_failed' if phase == 'rendering' else 'generation_failed'), checks=checks)
                    if phase == 'rendering':
                        self.save_version(root, current['shots'][index])
                    self.save(root, current)

    def rewrite(self, project_id: str, job_id: str, sid: str, instruction: str | None = None) -> dict:
        if isinstance(instruction, str) and instruction.strip() and len(instruction) <= 200:
            return self.revise(project_id, job_id, sid, [{'text': instruction, 'own': True}])
        with self.lock:
            job = self.read(project_id, job_id)
            target = next((s for s in job['shots'] if s['shotId'] == sid), None)
            if target is None:
                raise DirectVideoError('shot_not_found')
            if instruction is not None and (not isinstance(instruction, str) or len(instruction) > 200):
                raise DirectVideoError('instruction_invalid')
            opinion = instruction.strip() if instruction is not None else ''
            retrying = target['status'] in {'interrupted', 'failed'}
            if not opinion and not retrying:
                raise DirectVideoError('instruction_invalid')
            retry_errors = copy.deepcopy(target['checks']['errors']) if retrying else None
            effective = opinion or target.get('lastInstruction')
            if effective:
                target['_revisionRequest'] = {'lines': [{'text': effective, 'own': True}]}
            if job['design']['status'] != 'done':
                raise DirectVideoError('design_not_ready')
            if (project_id, job_id) in self.active or process_alive(job.get('_workerPid')) or job['output']['status'] == 'composing':
                raise DirectVideoError('job_busy')
            job['status'] = 'writing'
            target.update(status='writing', lastInstruction=effective, writingStartedAt=now())
            self.invalidate_output(self.path(project_id, job_id), job)
            self.start(project_id, job_id, self._rewrite, sid, effective, retry_errors)
            return job

    def invalidate_output(self, root, job, *, preserve_composed_at=False):
        if not preserve_composed_at:
            job['output']['composedAt'] = None
        job['output'].update(status='none', durationSeconds=None, frames=None,
                             checks={'playable': 'unknown', 'avOffsetSeconds': None, 'blackFrames': None})
        self.save(root, job)

    def _rewrite(self, project_id, job_id, sid, instruction, retry_errors=None):
        self.write_shot(project_id, job_id, sid, instruction, retry_errors=retry_errors)
        self.finish_shots(project_id, job_id)

    def narration(self, project_id, job_id, stream, length: int) -> dict:
        if type(length) is not int or not 0 < length <= 100 * 1024 * 1024:
            raise DirectVideoError('narration_invalid')
        with self.lock:
            job = self.read(project_id, job_id)
            if (project_id, job_id) in self.active or process_alive(job.get('_workerPid')):
                raise DirectVideoError('job_busy')
            if job['design']['status'] != 'done' or not all(s['status'] == 'rendered' for s in job['shots']):
                raise DirectVideoError('shots_not_ready')
            root = self.path(project_id, job_id)
            pending = root / 'narration.pending.wav'
            try:
                with pending.open('wb') as handle:
                    remaining = length
                    while remaining:
                        block = stream.read(min(remaining, 256 * 1024))
                        if not block:
                            raise DirectVideoError('narration_invalid')
                        handle.write(block)
                        remaining -= len(block)
                duration = wav_seconds(pending)
                if round(duration * FPS) < len(job['shots']):
                    raise DirectVideoError('narration_invalid')
                pending.replace(root / 'narration.wav')
            except (OSError, ValueError, wave.Error, EOFError) as exc:
                job['narration']['status'] = 'invalid'
                self.save(root, job)
                raise DirectVideoError('narration_invalid') from exc
            finally:
                pending.unlink(missing_ok=True)
            job['narration'] = {'status': 'aligning', 'durationSeconds': duration}
            self.invalidate_output(root, job, preserve_composed_at=True)
            self.start(project_id, job_id, self._align)
            return job

    def _align(self, project_id, job_id):
        root = self.path(project_id, job_id)
        job = self.read(project_id, job_id)
        started = time.perf_counter()
        try:
            transcript = self.media.transcribe(root / 'narration.wav')
        except Exception:
            # Local ASR unavailability and nonmatching words both use the
            # explicitly labelled proportional schedule, never another service.
            transcript = None
        durations, source = allocate_timing(job['shots'], job['narration']['durationSeconds'], transcript)
        self.record(root, 'alignment', timingSource=source, elapsedSeconds=round(time.perf_counter() - started, 3))
        dump(root / 'checks' / 'timing.json', {'timingSource': source, 'seconds': durations})
        rewrite = []
        with self.lock:
            for shot, duration in zip(job['shots'], durations):
                code = (root / 'shots' / (shot['shotId'] + '.html')).read_text()
                if duration + 1e-6 < (declared_seconds(code) or shot['estimatedSeconds']):
                    rewrite.append(shot['shotId'])
                shot.update(measuredSeconds=duration, timingSource=source)
            job['status'] = 'rendering'
            self.save(root, job)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            list(pool.map(lambda sid: self.write_shot(project_id, job_id, sid, '配音短于原动画，请按新的实测 D 重排，保持结尾完整。'), rewrite))
        for shot in job['shots']:
            if shot['shotId'] not in rewrite:
                try:
                    layout = self.render(root, shot)
                    with self.lock:
                        current = self.read(project_id, job_id)
                        target = next(s for s in current['shots'] if s['shotId'] == shot['shotId'])
                        self.record_layout(root, target, layout)
                        target.update(status='rendered', renderedAt=now(), posterRevision=target['posterRevision'] + 1)
                        target['boxes'] = read_json(root / 'boxes' / (shot['shotId'] + '.json'), [])
                        target['look'] = empty_look()
                        self.snapshot_version(root, target, None)
                        self.save(root, current)
                    self.review_shot(project_id, job_id, shot['shotId'])
                except Exception:
                    with self.lock:
                        current = self.read(project_id, job_id)
                        target = next(s for s in current['shots'] if s['shotId'] == shot['shotId'])
                        target.update(status='failed', failureCode='render_failed')
                        self.save(root, current)
        with self.lock:
            current = self.read(project_id, job_id)
            current['narration']['status'] = 'ready'
            self.save(root, current)
        self.finish_shots(project_id, job_id)

    def request_compose(self, project_id, job_id):
        with self.lock:
            job = self.read(project_id, job_id)
            if not all(s['status'] == 'rendered' for s in job['shots']) or job['narration']['status'] in {'aligning', 'invalid'}:
                raise DirectVideoError('shots_not_ready')
            if (project_id, job_id) in self.active or process_alive(job.get('_workerPid')):
                raise DirectVideoError('job_busy')
            job['status'] = 'composing'
            job['output'].update(status='composing', composedAt=None, kind='narrated' if job['narration']['status'] == 'ready' else 'silent')
            self.save(self.path(project_id, job_id), job)
            self.start(project_id, job_id, self._compose)
            return job

    def _compose(self, project_id, job_id):
        root = self.path(project_id, job_id)
        with self.lock:
            job = self.read(project_id, job_id)
            job['status'] = 'composing'
            job['output'].update(status='composing', composedAt=None, kind='narrated' if job['narration']['status'] == 'ready' else 'silent')
            self.save(root, job)
        started = time.perf_counter()
        try:
            for shot in job['shots']:
                if shot.get('_cacheVersion') != shot.get('currentVersion'):
                    self.render(root, shot)
                    shot['_cacheVersion'] = shot['currentVersion']
            result = self.media.compose(root, job)
            self.record(root, 'compose', status='passed', elapsedSeconds=round(time.perf_counter() - started, 3))
            with self.lock:
                job['output'].update(result, status='ready', composedAt=now(), kind='narrated' if job['narration']['status'] == 'ready' else 'silent', revision=job['output']['revision'] + 1)
                job.update(status='done', failureCode=None)
                self.save(root, job)
        except Exception as exc:
            self.record(root, 'compose', status='failed', elapsedSeconds=round(time.perf_counter() - started, 3), failureCode=failure_code(exc, 'compose_failed'))
            with self.lock:
                job['output'].update(status='failed', composedAt=None)
                if isinstance(exc, OutputCheckError):
                    job['output']['checks'] = exc.checks
                job.update(status='failed', failureCode=failure_code(exc, 'compose_failed'))
                self.save(root, job)
