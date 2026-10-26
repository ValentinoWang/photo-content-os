"""Studio adapter for persisted local direct-video jobs; no provider processes."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re

from direct_video.generate import DirectVideoError, Generator
from studio.project_store import ProjectStoreError

JOB_FIELDS = ('jobId', 'projectId', 'model', 'status', 'createdAt', 'updatedAt', 'failureCode',
              'design', 'shots', 'narration', 'output')
SHOT_FIELDS = ('shotId', 'dialogue', 'mainAction', 'estimatedSeconds', 'measuredSeconds', 'timingSource',
               'status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt', 'renderedAt',
               'codeChars', 'posterRevision', 'checks', 'visual', 'subtitle', 'camera', 'audio', 'fromDraft', 'currentVersion', 'versions', 'boxes', 'look', 'sample')
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
    result['shots'] = [{k: copy.deepcopy(shot.get(k, False if k == 'fromDraft' else None) if k in ('writingStartedAt', 'visual', 'subtitle', 'camera', 'audio', 'fromDraft') else shot[k]) for k in SHOT_FIELDS} for shot in job['shots']]
    result['design'] = {k: result['design'].get(k) for k in ('status', 'palette', 'typeScale', 'motionRules', 'banned', 'motionSummary', 'bannedShort', 'source')}
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
        title = self.store.get_project(project_id)['title']
        body = {**body, '_projectTitle': title, '_styleBaseTitle': None}
        source = body.get('styleBase')
        if isinstance(source, dict) and isinstance(source.get('projectId'), str):
            try:
                body['_styleBaseTitle'] = self.store.get_project(source['projectId'])['title']
            except ProjectStoreError as exc:
                raise DirectVideoError('style_base_not_found') from exc
        job = self.generator.create(project_id, body)
        return projection(job)

    def draft(self, project_id, draft_id=None, body=None, *, revise=False):
        title = self.store.get_project(project_id)['title']
        if draft_id is None:
            job = self.generator.create_draft(project_id, {**body, '_projectTitle': title})
        elif revise:
            job = self.generator.revise_draft(project_id, draft_id, body.get('instruction'))
        else:
            job = self.generator.read_draft(project_id, draft_id)
        public = projection(job)
        shot = public['shots'][0]
        return {'draftId': job['jobId'], 'status': 'writing' if job['status'] == 'rendering' else job['status'],
                'text': redact(job['text']), 'dialogue': shot['dialogue'],
                'shot': {key: shot[key] for key in ('shotId', 'dialogue', 'visual', 'subtitle', 'camera', 'audio')},
                'design': public['design'], 'sample': {key: shot[key] for key in ('posterRevision', 'codeChars', 'checks')},
                'failureCode': job['failureCode'], 'startedAt': job['startedAt'], 'revisions': redact(job['revisions'])}

    def styles(self):
        from direct_video.styles import DESIGN_FIELDS, StyleLibrary
        projects = {row['id']: row['title'] for row in self.store.list_projects()}
        rows = []
        with self.generator.lock:
            for path in self.generator.root.glob('*/*/job.json'):
                job = json.loads(path.read_text())
                if job['projectId'] in projects and job['design']['status'] == 'done':
                    rows.append(job)
            rows.sort(key=lambda row: (row['createdAt'], row['jobId']), reverse=True)
            result, seen = [], set()
            for job in rows:
                design = {key: copy.deepcopy(job['design'].get(key)) for key in DESIGN_FIELDS}
                identity = json.dumps(design, sort_keys=True, ensure_ascii=False)
                if identity in seen:
                    continue
                seen.add(identity)
                pid, jid = job['projectId'], job['jobId']
                poster = None
                for shot in sorted(job['shots'], key=lambda s: (0, int(s['shotId'])) if s['shotId'].isdigit() else (1, s['shotId'])):
                    sid = shot['shotId']
                    root = self.generator.path(pid, jid)
                    path = (self.generator.version_dir(root, sid, shot['currentVersion']) / 'poster.jpg'
                            if shot.get('currentVersion') else root / 'posters' / (sid + '.jpg'))
                    if path.is_file():
                        poster = f'/api/projects/{pid}/direct/jobs/{jid}/shots/{sid}/poster.jpg?v={shot["posterRevision"]}'
                        break
                result.append({'projectId': pid, 'jobId': jid, 'title': redact(projects[pid]), 'createdAt': job['createdAt'],
                               'design': redact(design), 'posterUrl': poster})
        library = []
        for row in StyleLibrary().entries():
            base = '/api/direct/styles/library/' + row['id']
            library.append({'id': row['id'], 'name': redact(row['name']),
                            'design': redact({k: row['design'][k] for k in DESIGN_FIELDS}),
                            'posterUrl': base + '/poster.jpg', 'clipUrl': base + '/clip.mp4'})
        return {'styles': result, 'library': library}

    def style_library_artifact(self, ident, kind):
        from direct_video.styles import StyleLibrary
        row = StyleLibrary().get(ident)
        return row['poster' if kind == 'poster.jpg' else 'clip']

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
        if kind == 'clip.mp4':
            return self.generator.clip(project_id, job_id, sid)
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
