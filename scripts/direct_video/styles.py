"""Persisted style sources and single-shot drafts on the direct generation pipeline."""
from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
import re

from direct_video.media import atomic_bytes
from direct_video.revision_library import read_json

DESIGN_FIELDS = ('palette', 'typeScale', 'motionRules', 'banned', 'motionSummary', 'bannedShort')
SCRIPT_FIELDS = ('dialogue', 'visual', 'subtitle', 'camera')
STYLE_LIBRARY_ROOT = Path(__file__).with_name('style_library')
LOGGER = logging.getLogger(__name__)
LIBRARY_ID = re.compile(r'[a-z][a-z0-9_-]{0,79}')


class StyleLibrary:
    """Read only indexed recipes; reject a broken recipe independently."""
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else STYLE_LIBRARY_ROOT

    def index(self):
        try:
            value = json.loads((self.root / 'index.json').read_text(encoding='utf-8'))
            if not isinstance(value, list) or any(not isinstance(i, str) or not LIBRARY_ID.fullmatch(i) for i in value) or len(set(value)) != len(value):
                raise ValueError('index must contain distinct style ids')
            return value
        except (OSError, ValueError) as exc:
            LOGGER.warning('Style library index unavailable: %s', exc)
            return []

    def load(self, ident):
        try:
            paths = {suffix: self.root / (ident + '.' + suffix) for suffix in ('json', 'html', 'jpg', 'mp4')}
            if any(not p.resolve().is_relative_to(self.root.resolve()) or not p.is_file() or p.stat().st_size == 0 for p in paths.values()):
                raise ValueError('missing or unsafe style artifact')
            data = json.loads(paths['json'].read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('recipe must be an object')
            palette, scale = data.get('palette'), data.get('typeScale')
            summary, short = data.get('motionSummary'), data.get('bannedShort')
            valid = (data.get('id') == ident and isinstance(data.get('name'), str) and bool(data['name'].strip())
                     and isinstance(palette, dict) and set(palette) == {'background', 'primary', 'accent', 'neutral'}
                     and all(isinstance(c, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', c) for c in palette.values())
                     and isinstance(scale, list) and len(scale) == 3 and all(type(n) is int for n in scale)
                     and isinstance(summary, str) and bool(summary.strip()) and len(summary) <= 30
                     and isinstance(short, list) and 1 <= len(short) <= 8
                     and all(isinstance(b, str) and bool(b.strip()) and len(b) <= 12 for b in short)
                     and all(isinstance(data.get(k), str) and bool(data[k].strip()) for k in ('motionRules', 'visualGrammar'))
                     and isinstance(data.get('banned'), list) and bool(data['banned'])
                     and all(isinstance(b, str) and bool(b.strip()) for b in data['banned']))
            if not valid:
                raise ValueError('invalid style fields')
            return {'id': ident, 'name': data['name'],
                    'design': {key: data[key] for key in (*DESIGN_FIELDS, 'visualGrammar')},
                    'code': paths['html'].read_text(encoding='utf-8'), 'poster': paths['jpg'], 'clip': paths['mp4']}
        except (OSError, ValueError) as exc:
            LOGGER.warning('Style library entry %s excluded: %s', ident, exc)
            return None

    def entries(self):
        return [row for ident in self.index() if (row := self.load(ident)) is not None]

    def get(self, ident):
        from direct_video.generate import DirectVideoError
        if isinstance(ident, str) and LIBRARY_ID.fullmatch(ident) and ident in self.index():
            row = self.load(ident)
            if row is not None:
                return row
        raise DirectVideoError('style_base_not_found')


def shot_context(shot):
    return {key: shot.get(key) for key in ('visual', 'subtitle', 'camera')}


class StyleMixin:
    def style_shot_context(self, job, shot):
        context = shot_context(shot)
        if job.get('_styleSample'):
            context['form_profile'] = {'visual_grammar': job['_styleSample']['visualGrammar']}
            context['styleSampleCode'] = job['_styleSample']['code']
        return context

    def make_design(self, root, job):
        from direct_video.generate import DirectVideoError, RULES, validate_design
        context = {'shots': [{'shotId': s['shotId'], 'dialogue': s['dialogue'], **shot_context(s)} for s in job['shots']],
                   'style': job['style']}
        if job.get('_baseDesign') is not None:
            context['baseDesign'] = job['_baseDesign']
        banned_rule = '保留原设计的完整禁用列表，仅按 style 修改' if job.get('_styleSample') else '3–6 条'
        system = ('为竖屏口播设计全片视觉系统。只输出 JSON，包含 palette（background、primary、accent、neutral 的六位十六进制颜色），'
                  f'typeScale（三档从大到小整数），motionRules（一句话），banned（{banned_rule}），'
                  'motionSummary（一句给人看的动作规矩，最多30字，不含数字加单位、坐标、百分比），'
                  'bannedShort（给人看的不用套路，1–8条，每条最多12字），'
                  'perShot（shotId、唯一主动作 mainAction、观众读到的 takeaway）。'
                  'visual 是编导写的画面，subtitle 是字幕 / 花字，camera 是景别 · 运镜；有画面时 mainAction 照画面定。'
                  '提供 baseDesign 时只按 style 这句话修改原设计，其他视觉规则保留。\n' + self.library.rules(RULES))
        for attempt in range(2):
            try:
                design = validate_design(self.timed_call(root, 'design', system, context), job['shots'],
                                         library_recipe=bool(job.get('_styleSample')))
                if job.get('_styleSample'):
                    design['visualGrammar'] = job['_styleSample']['visualGrammar']
                return design
            except DirectVideoError as exc:
                if exc.code not in {'design_invalid', 'model_json_invalid'} or attempt:
                    raise
                context['errors'] = [{'code': exc.code, 'message': '设计字段不合格，请按上述全部字段和长度重新输出。'}]

    def resolve_style_base(self, body):
        from direct_video.generate import DirectVideoError
        if 'styleBase' not in body:
            return None
        value = body['styleBase']
        if not isinstance(value, dict) or value.get('kind') not in ('job', 'draft', 'library'):
            raise DirectVideoError('style_base_not_found')
        if value['kind'] == 'library':
            row = StyleLibrary().get(value.get('id'))
            return {'reference': {'kind': 'library', 'id': row['id']}, 'name': row['name'],
                    'design': row['design'], 'sample': {'code': row['code'], 'visualGrammar': row['design']['visualGrammar']}}
        pid = value.get('projectId')
        key = 'jobId' if value['kind'] == 'job' else 'draftId'
        jid = value.get(key)
        if not isinstance(jid, str) or not jid.startswith('dv_' if key == 'jobId' else 'ds_'):
            raise DirectVideoError('style_base_not_found')
        try:
            with self.lock:
                job = self.read(pid, jid)
                if value['kind'] == 'draft' and job['status'] != 'ready':
                    raise DirectVideoError('draft_not_ready')
                if job['design']['status'] != 'done':
                    raise DirectVideoError('style_base_not_found')
                root = self.path(pid, jid)
                design = json.loads((root / 'design.json').read_text())
                # The accepted job projection is the source of the shared visual fields.
                for field in DESIGN_FIELDS:
                    if field in job['design']:
                        design[field] = copy.deepcopy(job['design'][field])
                    else:
                        design.pop(field, None)
                result = {'reference': copy.deepcopy(value), 'job': job, 'design': design}
                if value['kind'] == 'draft':
                    result['code'] = (root / 'shots/01.html').read_bytes()
                    result['poster'] = (root / 'posters/01.jpg').read_bytes()
                    result['clip'] = (root / 'clips/01.mp4').read_bytes() if (root / 'clips/01.mp4').is_file() else None
                return result
        except FileNotFoundError as exc:
            raise DirectVideoError('style_base_not_found') from exc
        except DirectVideoError as exc:
            if exc.code == 'job_not_found':
                raise DirectVideoError('style_base_not_found') from exc
            raise

    def bind_style_base(self, root, job, base, body):
        if base['reference']['kind'] == 'library':
            instruction = body.get('style', '').strip()
            job['style'] = instruction
            job['_baseDesign'] = copy.deepcopy(base['design'])
            job['_styleSample'] = copy.deepcopy(base['sample'])
            job['design']['source'] = {**base['reference'], 'name': base['name'], 'instruction': instruction}
            return
        source_job, reference = base['job'], base['reference']
        drafted = reference['kind'] == 'draft'
        instruction = '' if drafted else body.get('style', '').strip()
        job['style'] = instruction
        job['_baseDesign'] = base['design']
        if source_job.get('_styleSample'):
            job['_styleSample'] = copy.deepcopy(source_job['_styleSample'])
        job['design']['source'] = {**reference, 'kind': 'drafted' if drafted else 'adjusted' if instruction else 'inherited',
                                   'title': body.get('_styleBaseTitle', source_job.get('_projectTitle', reference['projectId'])), 'instruction': instruction}
        if not drafted or job['shots'][0]['shotId'] != '01':
            return
        target, sample = job['shots'][0], source_job['shots'][0]
        if any(target.get(k) != sample.get(k) for k in SCRIPT_FIELDS):
            return
        for key in ('status', 'codeChars', 'checks', 'writtenAt', 'renderedAt', 'posterRevision', 'boxes', 'look'):
            target[key] = copy.deepcopy(sample[key])
        target['fromDraft'] = True
        target['mainAction'] = sample['mainAction']
        for path, content in [('shots/01.html', base['code']), ('posters/01.jpg', base['poster']), ('clips/01.mp4', base['clip'])]:
            if content is not None:
                atomic_bytes(root / path, content)
        self.snapshot_version(root, target, None)
        # A reused draft has no local frame cache; compose/review may rebuild it later.
        target.pop('_cacheVersion', None)
        self.retain_clip(root, target)

    def create_draft(self, project_id, body):
        from direct_video.generate import DirectVideoError, parse_shots
        text = body.get('text')
        if not isinstance(text, str) or not 0 < len(text.strip()) <= 4000:
            raise DirectVideoError('style_invalid')
        rows = parse_shots({'storyboard': {'shots': [body.get('shot')]}})
        if rows[0]['shotId'] != '01':
            raise DirectVideoError('script_invalid')
        job = self.create(project_id, {'style': text.strip(), 'storyboard': {'shots': [body['shot']]},
                                       '_projectTitle': body.get('_projectTitle', project_id)}, background=False, draft=True)
        self.start(project_id, job['jobId'], self.generate)
        return job

    def read_draft(self, project_id, draft_id):
        from direct_video.generate import DirectVideoError
        if not isinstance(draft_id, str) or not draft_id.startswith('ds_'):
            raise DirectVideoError('draft_not_found')
        try:
            return self.read(project_id, draft_id)
        except DirectVideoError as exc:
            if exc.code == 'job_not_found':
                raise DirectVideoError('draft_not_found') from exc
            raise

    def revise_draft(self, project_id, draft_id, instruction):
        from direct_video.generate import DirectVideoError, now, process_alive
        if not isinstance(instruction, str) or not 0 < len(instruction.strip()) <= 1000:
            raise DirectVideoError('instruction_invalid')
        with self.lock:
            job = self.read_draft(project_id, draft_id)
            if ((project_id, draft_id) in self.active or process_alive(job.get('_workerPid'))
                    or job['status'] in ('designing', 'writing', 'rendering')):
                raise DirectVideoError('draft_busy')
            root = self.path(project_id, draft_id)
            job['_baseDesign'] = read_json(root / 'design.json', None)
            job.update(status='designing', failureCode=None, style=instruction.strip(), startedAt=now())
            job['design']['status'] = 'pending'
            job['revisions'].append({'instruction': instruction.strip(), 'at': job['startedAt']})
            job['shots'][0].update(status='queued', failureCode=None)
            self.save(root, job)
            self.start(project_id, draft_id, self.generate)
            return job

    def retain_clip(self, root, shot):
        source = root / 'clips' / (shot['shotId'] + '.mp4')
        if source.is_file() and shot['currentVersion']:
            atomic_bytes(self.version_dir(root, shot['shotId'], shot['currentVersion']) / 'clip.mp4', source.read_bytes())

    def clip(self, project_id, job_id, sid):
        from direct_video.generate import DirectVideoError
        with self.lock:
            job = self.read(project_id, job_id)
            shot = next((s for s in job['shots'] if s['shotId'] == sid), None)
            if shot is None:
                raise DirectVideoError('shot_not_found')
            root = self.path(project_id, job_id)
            target = root / 'clips' / (sid + '.mp4')
            if shot['status'] != 'rendered':
                raise DirectVideoError('artifact_not_found')
            if target.is_file():
                return target
            if shot.get('_cacheVersion') != shot['currentVersion']:
                raise DirectVideoError('artifact_not_found')
            try:
                self.media.encode_clip(root, shot)
            except FileNotFoundError as exc:
                raise DirectVideoError('artifact_not_found') from exc
            self.retain_clip(root, shot)
            return target
