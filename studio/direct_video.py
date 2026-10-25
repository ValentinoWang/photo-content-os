"""Studio adapter for persisted local direct-video jobs; no provider processes."""
from __future__ import annotations

import copy
from pathlib import Path
import re

from direct_video.generate import DirectVideoError, Generator

JOB_FIELDS = ('jobId', 'projectId', 'model', 'status', 'createdAt', 'updatedAt', 'failureCode',
              'design', 'shots', 'narration', 'output')
SHOT_FIELDS = ('shotId', 'dialogue', 'mainAction', 'estimatedSeconds', 'measuredSeconds', 'timingSource',
               'status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt', 'renderedAt',
               'codeChars', 'posterRevision', 'checks', 'currentVersion', 'versions', 'boxes', 'look', 'sample')
PATH_TEXT = re.compile(r'(?:[A-Za-z]:[\\/][^\s"<>]+|/(?:[^\s/"<>]+/)+[^\s"<>]*)')


def redact(value):
    if isinstance(value, str):
        return PATH_TEXT.sub('［本机路径］', value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def projection(job: dict | None) -> dict | None:
    if job is None:
        return None
    result = {k: copy.deepcopy(job[k]) for k in JOB_FIELDS}
    result['shots'] = [{k: copy.deepcopy(shot.get(k) if k == 'writingStartedAt' else shot[k]) for k in SHOT_FIELDS} for shot in job['shots']]
    result['design'] = {k: result['design'].get(k) for k in ('status', 'palette', 'typeScale', 'motionRules', 'banned')}
    # Persisted private diagnostics must not become fields through a future
    # renderer change. Projection recursively strips unknown nested fields.
    for shot in result['shots']:
        shot['checks'] = {level: [{k: item[k] for k in ('code', 'message', 'atSeconds') if k in item}
                                 for item in shot['checks'].get(level, [])] for level in ('errors', 'warnings')}
        shot['boxes'] = [{k: box[k] for k in ('id', 'name', 'x', 'y', 'w', 'h')} for box in shot['boxes']]
        shot['look'] = {k: shot['look'][k] for k in ('status', 'failureCode', 'findings')}
        shot['look']['findings'] = [{k: row[k] for k in ('boxId', 'kind', 'text', 'suggest')} for row in shot['look']['findings']]
        shot['versions'] = [{k: v[k] for k in ('version', 'baseVersion', 'createdAt', 'posterRevision', 'codeChars', 'request', 'verify')}
                            for v in shot['versions']]
        for version in shot['versions']:
            if version['request'] is not None:
                version['request'] = {'lines': [{k: row[k] for k in ('text', 'boxId', 'action', 'issue', 'own') if k in row}
                                                for row in version['request']['lines']]}
            if version['verify'] is not None:
                value = version['verify']
                version['verify'] = {k: value[k] for k in ('status', 'failureCode') if k in value}
                version['verify']['items'] = [{k: row[k] for k in ('index', 'result', 'reason')} for row in value['items']]
    result['narration'] = {k: result['narration'].get(k) for k in ('status', 'durationSeconds')}
    result['output'] = {k: result['output'].get(k) for k in ('status', 'kind', 'composedAt', 'durationSeconds', 'frames', 'revision', 'checks')}
    result['output']['checks'] = {k: result['output']['checks'].get(k) for k in ('playable', 'avOffsetSeconds', 'blackFrames')}
    return redact(result)


class DirectVideo:
    def __init__(self, store, *, generator=None):
        self.store = store
        self.generator = generator or Generator(store.state_dir)

    def get(self, project_id, job_id):
        self.store.get_project(project_id)
        job = self.generator.latest(project_id) if job_id == 'latest' else self.generator.read(project_id, job_id)
        return projection(job)

    def create(self, project_id, body):
        self.store.get_project(project_id)
        return projection(self.generator.create(project_id, body))

    def command(self, project_id, job_id, action, body, *, sid=None):
        self.store.get_project(project_id)
        if action == 'rewrite':
            job = self.generator.rewrite(project_id, job_id, sid, body.get('instruction'))
        elif action == 'revise':
            title = self.store.get_project(project_id)['title']
            job = self.generator.revise(project_id, job_id, sid, body.get('lines'), title)
        elif action == 'current':
            job = self.generator.current(project_id, job_id, sid, body.get('version'))
        elif action == 'look':
            job = self.generator.look(project_id, job_id, sid)
        elif action in {'sample', 'unsample'}:
            title = self.store.get_project(project_id)['title']
            job = self.generator.set_sample(project_id, job_id, sid, action == 'sample', title)
        elif action == 'compose':
            job = self.generator.request_compose(project_id, job_id)
        else:
            raise DirectVideoError('route_not_found')
        return projection(job)

    def narration(self, project_id, job_id, stream, length, content_type):
        self.store.get_project(project_id)
        if content_type.split(';', 1)[0].strip().lower() != 'audio/wav':
            raise DirectVideoError('narration_invalid')
        return projection(self.generator.narration(project_id, job_id, stream, length))

    def library(self, kind, proposal_id=None, adopt=None):
        with self.generator.lock:
            library = self.generator.library
            if kind == 'revision-log':
                value = library.log()
            elif kind == 'samples':
                rows = redact(library.samples())
                return {'samples': [{**row, 'posterUrl': '/api/direct/samples?poster=' + row['sampleId']} for row in rows]}
            else:
                value = {'proposal': library.decide(proposal_id, adopt)}
            # Use the same recursive privacy treatment as the job projection.
            return redact(value)

    def artifact(self, project_id: str, job_id: str, kind: str, sid: str | None = None, version=None) -> Path:
        self.store.get_project(project_id)
        job = self.generator.read(project_id, job_id)
        root = self.generator.path(project_id, job_id)
        if kind == 'output.mp4':
            if job['output']['status'] != 'ready':
                raise DirectVideoError('output_not_ready')
            path = root / kind
        else:
            if not any(s['shotId'] == sid for s in job['shots']):
                raise DirectVideoError('shot_not_found')
            path = root / ('posters' if kind == 'poster.jpg' else 'shots') / (sid + ('.jpg' if kind == 'poster.jpg' else '.html'))
            if version is None and kind == 'poster.jpg':
                shot = next(s for s in job['shots'] if s['shotId'] == sid)
                if shot['currentVersion']:
                    path = self.generator.version_dir(root, sid, shot['currentVersion']) / 'poster.jpg'
            if version is not None:
                shot = next(s for s in job['shots'] if s['shotId'] == sid)
                if not any(str(v['version']) == version for v in shot['versions']):
                    raise DirectVideoError('version_not_found')
                path = self.generator.version_dir(root, sid, int(version)) / ('poster.jpg' if kind == 'poster.jpg' else 'code.html')
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise DirectVideoError('artifact_not_found')
        return path
