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
               'codeChars', 'posterRevision', 'checks')
PATH_TEXT = re.compile(r'(?:[A-Za-z]:[\\/][^\s"<>]+|/(?:[^\s/"<>]+/)+[^\s"<>]*)')


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
    result['narration'] = {k: result['narration'].get(k) for k in ('status', 'durationSeconds')}
    result['output'] = {k: result['output'].get(k) for k in ('status', 'kind', 'durationSeconds', 'frames', 'revision', 'checks')}
    result['output']['checks'] = {k: result['output']['checks'].get(k) for k in ('playable', 'avOffsetSeconds', 'blackFrames')}
    def redact(value):
        if isinstance(value, str):
            return PATH_TEXT.sub('［本机路径］', value)
        if isinstance(value, dict):
            return {k: redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [redact(v) for v in value]
        return value
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

    def artifact(self, project_id: str, job_id: str, kind: str, sid: str | None = None) -> Path:
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
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise DirectVideoError('artifact_not_found')
        return path
