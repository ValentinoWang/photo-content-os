"""Versioned shot revisions and image review, using the product model gateway."""
from __future__ import annotations

import copy
import json
import shutil

from direct_video.media import atomic_bytes
from direct_video.revision_library import read_json

VERSION_FIELDS = ('status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt',
                  'renderedAt', 'codeChars', 'posterRevision', 'checks', 'boxes', 'look')


def empty_look():
    return {'status': 'none', 'failureCode': None, 'findings': []}


def validate_lines(lines, boxes):
    from direct_video.generate import DirectVideoError
    if not isinstance(lines, list) or not 1 <= len(lines) <= 200:
        raise DirectVideoError('instruction_invalid')
    ids = {box['id'] for box in boxes}
    cleaned = []
    for row in lines:
        if not isinstance(row, dict) or not isinstance(row.get('text'), str) or not row['text'].strip():
            raise DirectVideoError('instruction_invalid')
        selectors = sum(key in row for key in ('action', 'issue', 'own'))
        if selectors != 1 or set(row) - {'text', 'boxId', 'action', 'issue', 'own'}:
            raise DirectVideoError('instruction_invalid')
        if 'action' in row:
            if not isinstance(row.get('boxId'), str) or row['boxId'] not in ids or row['action'] not in ('main', 'dim', 'del', 'short'):
                raise DirectVideoError('instruction_invalid')
        elif 'issue' in row:
            if row['issue'] not in ('space', 'color', 'sync') or 'boxId' in row:
                raise DirectVideoError('instruction_invalid')
        elif row['own'] is not True or 'boxId' in row:
            raise DirectVideoError('instruction_invalid')
        cleaned.append(copy.deepcopy(row))
    length = sum(len(row['text']) for row in cleaned)
    if length > 200:
        raise DirectVideoError('instruction_too_long')
    return cleaned


def validate_findings(value, boxes):
    from direct_video.generate import DirectVideoError
    rows = value.get('findings')
    if not isinstance(rows, list) or len(rows) > 5:
        raise DirectVideoError('look_failed')
    ids = {b['id'] for b in boxes}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'boxId', 'kind', 'text', 'suggest'}
                or (row['boxId'] is not None and (not isinstance(row['boxId'], str) or row['boxId'] not in ids))
                or row['suggest'] not in ('main', 'dim', 'del', 'short')
                or any(not isinstance(row[k], str) or not 0 < len(row[k].strip()) <= 300 for k in ('kind', 'text'))):
            raise DirectVideoError('look_failed')
    return rows


def validate_verify(value, count):
    from direct_video.generate import DirectVideoError
    rows = value.get('items')
    if not isinstance(rows, list) or len(rows) != count:
        raise DirectVideoError('verify_failed')
    for index, row in enumerate(rows):
        if (not isinstance(row, dict) or set(row) != {'index', 'result', 'reason'}
                or type(row['index']) is not int or row['index'] != index or row['result'] not in ('done', 'missed')
                or not isinstance(row['reason'], str) or len(row['reason']) > 300
                or (row['result'] == 'missed' and not row['reason'].strip())):
            raise DirectVideoError('verify_failed')
    return rows


class RevisionMixin:
    def upgrade_versions(self, root, job):
        """Lazily preserve a pre-R277 shot before any mutation of its files."""
        changed = False
        for shot in job['shots']:
            if 'versions' in shot:
                for version in shot['versions']:
                    if 'baseVersion' not in version:
                        version['baseVersion'] = None
                        changed = True
                continue
            changed = True
            shot.update(versions=[], currentVersion=0, boxes=[], look=empty_look(), sample=False)
            if shot['codeChars'] and (root / 'shots' / (shot['shotId'] + '.html')).is_file():
                self.snapshot_version(root, shot, None)
        return changed

    def version_dir(self, root, sid, version):
        return root / 'versions' / sid / str(version)

    def snapshot_version(self, root, shot, request, *, include_poster=True):
        from direct_video.generate import now
        version = max((v['version'] for v in shot['versions']), default=0) + 1
        destination = self.version_dir(root, shot['shotId'], version)
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / 'shots' / (shot['shotId'] + '.html'), destination / 'code.html')
        poster = root / 'posters' / (shot['shotId'] + '.jpg')
        if include_poster and poster.exists():
            shutil.copyfile(poster, destination / 'poster.jpg')
        record = {k: copy.deepcopy(shot.get(k)) for k in VERSION_FIELDS}
        record.update(version=version, baseVersion=shot['currentVersion'] or None,
                      createdAt=now(), request=copy.deepcopy(request), verify=None)
        shot['versions'].append(record)
        shot['currentVersion'] = version
        shot['_cacheVersion'] = version
        shot['sample'] = False
        self.save_version(root, shot)

    def save_version(self, root, shot):
        from direct_video.generate import dump
        if shot['currentVersion']:
            record = next(v for v in shot['versions'] if v['version'] == shot['currentVersion'])
            for key in VERSION_FIELDS:
                record[key] = copy.deepcopy(shot.get(key))
            dump(self.version_dir(root, shot['shotId'], record['version']) / 'checks.json', record['checks'])

    def idle_shot(self, project_id, job_id, sid):
        from direct_video.generate import DirectVideoError, process_alive
        job = self.read(project_id, job_id)
        shot = next((s for s in job['shots'] if s['shotId'] == sid), None)
        if shot is None:
            raise DirectVideoError('shot_not_found')
        if ((project_id, job_id) in self.active or process_alive(job.get('_workerPid'))
                or job['output']['status'] == 'composing' or shot['look']['status'] == 'running'):
            raise DirectVideoError('job_busy')
        return job, shot

    def revise(self, project_id, job_id, sid, lines, title=''):
        from direct_video.generate import DirectVideoError, now
        with self.lock:
            job, shot = self.idle_shot(project_id, job_id, sid)
            lines = validate_lines(lines, shot['boxes'])
            if job['design']['status'] != 'done':
                raise DirectVideoError('design_not_ready')
            request = {'lines': lines}
            shot['_revisionRequest'] = request
            instruction = '\n'.join(row['text'] for row in lines)
            retry_errors = copy.deepcopy(shot['checks']['errors']) if shot['status'] in {'interrupted', 'failed'} else None
            shot.update(status='writing', lastInstruction=instruction, writingStartedAt=now())
            job['status'] = 'writing'
            self.invalidate_output(self.path(project_id, job_id), job)
            self.library.record(job, shot, lines, title or project_id, now())
            self.start(project_id, job_id, self._revise, sid, instruction, retry_errors)
            return job

    def _revise(self, project_id, job_id, sid, instruction, retry_errors):
        self._rewrite(project_id, job_id, sid, instruction, retry_errors)
        self.draft_rules()

    def draft_rules(self):
        with self.lock:
            candidates = self.library.draft_candidates()
        for proposal, texts in candidates:
            text = None
            try:
                value = self.call('根据反复提交的画面修改要求，起草一条可执行的中文镜头规则。只输出 JSON {"rule":"中文条文"}。',
                                  {'category': proposal['category'], 'requests': texts})
                if isinstance(value.get('rule'), str) and 0 < len(value['rule'].strip()) <= 1000:
                    text = value['rule'].strip()
            except Exception:
                # A failed draft stays visible and never enters active rules.
                pass
            with self.lock:
                self.library.finish_draft(proposal['proposalId'], text)

    def current(self, project_id, job_id, sid, version):
        from direct_video.generate import DirectVideoError
        with self.lock:
            job, shot = self.idle_shot(project_id, job_id, sid)
            record = next((v for v in shot['versions'] if type(version) is int and v['version'] == version), None)
            if record is None:
                raise DirectVideoError('version_not_found')
            if version == shot['currentVersion']:
                return job
            source = self.version_dir(self.path(project_id, job_id), sid, version)
            if not (source / 'poster.jpg').is_file() or record['status'] != 'rendered':
                raise DirectVideoError('shots_not_ready')
            # Read everything before replacing any current artifact.
            code, poster = (source / 'code.html').read_bytes(), (source / 'poster.jpg').read_bytes()
            root = self.path(project_id, job_id)
            atomic_bytes(root / 'shots' / (sid + '.html'), code)
            atomic_bytes(root / 'posters' / (sid + '.jpg'), poster)
            for key in VERSION_FIELDS:
                shot[key] = copy.deepcopy(record[key])
            shot['currentVersion'] = version
            shot['sample'] = self.library.is_sample(job, shot)
            self.record_layout_checks(root, shot)
            job.update(status='ready' if all(s['status'] == 'rendered' for s in job['shots']) else 'failed', failureCode=None)
            self.invalidate_output(root, job)
            return job

    def record_layout_checks(self, root, shot):
        from direct_video.generate import dump
        dump(root / 'checks' / (shot['shotId'] + '.json'), shot['checks'])

    def look(self, project_id, job_id, sid):
        from direct_video.generate import DirectVideoError
        with self.lock:
            job, shot = self.idle_shot(project_id, job_id, sid)
            if shot['status'] != 'rendered':
                raise DirectVideoError('shots_not_ready')
            shot['look'] = {'status': 'running', 'failureCode': None, 'findings': []}
            self.save(self.path(project_id, job_id), job, touch_updated_at=False)
            self.start(project_id, job_id, self.review_shot, sid, False, touch_updated_at=False)
            return job

    def review_shot(self, project_id, job_id, sid, verify=False):
        from direct_video.generate import dump
        root = self.path(project_id, job_id)
        with self.lock:
            job = self.read(project_id, job_id)
            shot = next(s for s in job['shots'] if s['shotId'] == sid)
            version = shot['currentVersion']
            record = next(v for v in shot['versions'] if v['version'] == version)
            shot['look'] = {'status': 'running', 'failureCode': None, 'findings': []}
            if verify:
                record['verify'] = {'status': 'running', 'items': []}
            self.save(root, job, touch_updated_at=False)
        images = None
        try:
            images = self.media.review_frames(root, shot)
            if shot.get('_cacheVersion') != version or any(not image.is_file() for image in images):
                self.render(root, shot)
                images = self.media.review_frames(root, shot)
                shot['boxes'] = json.loads((root / 'boxes' / (sid + '.json')).read_text())
                with self.lock:
                    current = self.read(project_id, job_id)
                    target = next(s for s in current['shots'] if s['shotId'] == sid)
                    target.update(boxes=shot['boxes'], _cacheVersion=version)
                    self.save_version(root, target)
                    self.save(root, current, touch_updated_at=False)
            if len(images) != 3 or any(not image.is_file() for image in images):
                raise ValueError('review_frames_unavailable')
            context = {'design': json.loads((root / 'design.json').read_text()), 'dialogue': shot['dialogue'],
                       'boxes': shot['boxes'], 'framesAt': [.3, .6, .9]}
            findings = validate_findings(self.call(
                '看所附三张实际画面，检查主次、字量、构图、颜色、口播同步。只输出 JSON {"findings":[{"boxId":null,"kind":"主次","text":"中文一句","suggest":"main"}]}。'
                '最多五条，每条只落一个已提供的块，整镜 boxId=null。suggest 只能 main、dim、del、short。没有问题返回空数组。',
                context, image_paths=images), shot['boxes'])
            look = {'status': 'done', 'failureCode': None, 'findings': findings}
        except Exception:
            look = {'status': 'failed', 'failureCode': 'look_failed', 'findings': []}
        verification = None
        if verify:
            try:
                if images is None or len(images) != 3 or any(not image.is_file() for image in images):
                    raise ValueError('review_frames_unavailable')
                rows = validate_verify(self.call(
                    '看新画面三帧，对照每条修改要求逐条核对。只输出 JSON {"items":[{"index":0,"result":"done","reason":""}]}。'
                    'index 从零按要求顺序，不能遗漏。result 只能 done 或 missed；missed 必须一句中文原因，不可只看代码推断。',
                    {'lines': record['request']['lines'], 'boxes': shot['boxes'], 'dialogue': shot['dialogue']}, image_paths=images),
                    len(record['request']['lines']))
                verification = {'status': 'done', 'items': rows}
            except Exception:
                verification = {'status': 'failed', 'failureCode': 'verify_failed', 'items': []}
        with self.lock:
            current = self.read(project_id, job_id)
            target = next(s for s in current['shots'] if s['shotId'] == sid)
            target_record = next(v for v in target['versions'] if v['version'] == version)
            target_record['look'] = look
            if verify:
                target_record['verify'] = verification
            if target['currentVersion'] == version:
                target['look'] = look
            self.save(root, current, touch_updated_at=False)
            dump(self.version_dir(root, sid, version) / 'review.json', {'look': look, 'verify': verification})

    def set_sample(self, project_id, job_id, sid, enabled, title=''):
        from direct_video.generate import DirectVideoError, now
        with self.lock:
            job, shot = self.idle_shot(project_id, job_id, sid)
            if shot['status'] != 'rendered' or not shot['currentVersion']:
                raise DirectVideoError('shots_not_ready')
            self.library.sample(job, shot, self.path(project_id, job_id), enabled, title or project_id, now())
            shot['sample'] = enabled
            self.save(self.path(project_id, job_id), job, touch_updated_at=False)
            return job
