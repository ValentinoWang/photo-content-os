"""Shared identity-bound handoff reader and direct-video API contract."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote

from studio.project_store import ProjectStoreError

if __package__:
    from .constants import (
        MAX_DESCRIPTOR_BYTES,
        DIRECT_HANDOFF_CONTRACT_SAFE_ID as SAFE_ID,
        RUN_RECORD_SCHEMA,
        RUN_RECORD_KEYS,
        RUN_RECORD_IDENTITY_KEYS,
        HANDOFF_REF,
    )
else:
    try:
        from studio.constants import (
            MAX_DESCRIPTOR_BYTES,
            DIRECT_HANDOFF_CONTRACT_SAFE_ID as SAFE_ID,
            RUN_RECORD_SCHEMA,
            RUN_RECORD_KEYS,
            RUN_RECORD_IDENTITY_KEYS,
            HANDOFF_REF,
        )
    except ImportError:
        from constants import (
            MAX_DESCRIPTOR_BYTES,
            DIRECT_HANDOFF_CONTRACT_SAFE_ID as SAFE_ID,
            RUN_RECORD_SCHEMA,
            RUN_RECORD_KEYS,
            RUN_RECORD_IDENTITY_KEYS,
            HANDOFF_REF,
        )


def read_json(root: Path, ref: str) -> dict:
    try:
        path = (root / ref).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size > MAX_DESCRIPTOR_BYTES:
            return {}
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


# Stage replays must agree on these; the derived plan and timestamp may differ.
_HANDOFF_PAIRS = {'jobId': 'job_id', 'publicVariantId': 'work_id', 'workRevision': 'work_revision',
                  'photoProjectId': 'project_id', 'photoProjectRevision': 'project_revision',
                  'catalogDigest': 'catalog_digest', 'confirmationRef': 'confirmation_ref'}


def selection_root(media_root=None):
    """Persistent delivery journal; every stored path is relative to the media root."""
    from runtime_paths import local_media_root
    return (Path(media_root) if media_root is not None else local_media_root()) / '.openclaw-p1a'


def run_record_path(root, job_id):
    return Path(root) / 'runs' / (hashlib.sha256(job_id.encode()).hexdigest()[:32] + '.json')


def read_run_record(root, job_id):
    """The delivered run record for one job, or None when absent or malformed."""
    if not isinstance(job_id, str) or not SAFE_ID.fullmatch(job_id):
        return None
    try:
        record = json.loads(run_record_path(root, job_id).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if (not isinstance(record, dict) or record.keys() != RUN_RECORD_KEYS or record['schema'] != RUN_RECORD_SCHEMA
            or record['job_id'] != job_id):
        return None
    return record


def binding_from_record(record, store_path, media_root):
    """Run binding derived from a delivered record; there is no hand-written binding file."""
    return {'identity': dict(record['identity']), 'handoff_digest': record['handoff_digest'],
            'creative_store': str(store_path), 'project_root': str(Path(media_root) / record['project_root_ref']),
            'steps': record['steps'], 'candidate_ref': record['candidate_ref'], 'source_refs': record['source_refs']}


def _delivered_records(root, project_id, device_id, job_id):
    runs = Path(root) / 'runs'
    try:
        names = sorted(runs.glob('*.json'))
    except OSError:
        return []
    found = []
    for path in names:
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        record = read_run_record(root, raw.get('job_id')) if isinstance(raw, dict) else None
        if (record is None or record['project_id'] != project_id or (device_id is not None and record['device_id'] != device_id)
                or (job_id is not None and record['job_id'] != job_id)):
            continue
        found.append(record)
    return sorted(found, key=lambda r: (r['delivered_at'], r['job_id']))


def read_delivered_handoff(store, project_id, *, device_id, job_id=None, root=None, media_root=None):
    """Read the package the installed Agent delivered to this project; never falls back to env or root video.json."""
    from runtime_paths import local_media_root
    from openclaw_product_contract import video_digest
    try:
        media = local_media_root(media_root)
        journal = Path(root) if root is not None else selection_root(media)
        if job_id is None:
            records = _delivered_records(journal, project_id, device_id, None)
            record = records[-1] if records else None
        else:
            record = read_run_record(journal, job_id)
        if record is None or record['project_id'] != project_id or (device_id is not None and record['device_id'] != device_id):
            return None
        project = store.get_project(project_id)
        project_root = store.local_workspace_path(project_id).resolve()
        revision = project['revision']
        if (not project_root.is_relative_to(media) or project_root != (media / record['project_root_ref']).resolve()
                or type(revision) is not int or revision != record['project_revision']):
            return None
        workspace = (media / record['workspace_ref']).resolve()
        if not workspace.is_relative_to(media):
            return None
        descriptor = read_json(workspace, 'video-inputs/' + record['job_id'] + '/video.json')
        identity = descriptor.get('identity', {})
        mx = descriptor.get('mxHandoff', {})
        mx_identity = mx.get('identity', {})
        if (descriptor.get('scope') != 'video_handoff_v1' or identity.get('jobId') != record['job_id']
                or identity.get('photoProjectId') != project_id or identity.get('photoProjectRevision') != revision
                or mx.get('handoff_digest') != record['handoff_digest']
                or video_digest({k: v for k, v in mx.items() if k != 'handoff_digest'}) != record['handoff_digest']
                or mx_identity != record['identity'] or descriptor.get('binding_id') != record['binding_id']
                or descriptor.get('binding_generation') != record['binding_generation']
                or any(identity.get(k) != mx_identity.get(v) for k, v in _HANDOFF_PAIRS.items())
                or mx_identity.get('confirmation_ref') != record['confirmation_ref']
                or mx_identity.get('catalog_digest') != record['catalog_digest']):
            return None
        return dict(project=project, root=project_root, workspace=workspace,
                    binding=binding_from_record(record, store.path, media),
                    revision=revision, descriptor=descriptor, identity=identity, run_record=record)
    except (ProjectStoreError, OSError, ValueError, TypeError, AttributeError, KeyError):
        return None


def read_handoff(store, project_id, *, delivered=None):
    """Resolve exactly the descriptor accepted by the editing handoff page.

    ``delivered={'device_id': ..., 'job_id': optional}`` reads only the package the
    installed Agent delivered to this project. Without it, the explicit legacy
    environment and workspace-root inputs remain for existing callers.
    """
    from runtime_paths import local_media_root
    if delivered is not None:
        return read_delivered_handoff(store, project_id, device_id=delivered['device_id'],
                                      job_id=delivered.get('job_id'), root=delivered.get('root'))
    try:
        project = store.get_project(project_id)
        root = store.local_workspace_path(project_id).resolve()
        if not root.is_relative_to(local_media_root()):
            return None
        binding_ref = os.environ.get('PHOTO_STUDIO_VIDEO_BINDING')
        binding = {}
        if binding_ref:
            path = Path(binding_ref).expanduser().resolve()
            binding = read_json(path.parent, path.name)
            identity = binding.get('identity', {})
            if identity.get('project_id') != project_id or Path(binding.get('project_root', '')).resolve() != root:
                return None
            canonical_path = Path(binding.get('creative_store', '')).expanduser().resolve()
            canonical = read_json(canonical_path.parent, canonical_path.name)
            active = [p for p in canonical.get('projects', []) if p.get('id') == project_id]
            if len(active) != 1 or active[0].get('revision') != identity.get('project_revision'):
                return None
            revision = active[0]['revision']
        else:
            revision = project['revision']
        workspace = Path(os.environ.get('PHOTO_STUDIO_VIDEO_WORKSPACE', str(root))).expanduser().resolve()
        if not workspace.is_relative_to(local_media_root()):
            return None
        job = binding.get('identity', {}).get('job_id')
        if job is not None and (not isinstance(job, str) or not SAFE_ID.fullmatch(job)):
            return None
        descriptor = read_json(workspace, 'video-inputs/' + job + '/video.json') if job else {}
        descriptor = descriptor or read_json(workspace, 'video.json')
        identity = descriptor.get('identity', {})
        jid = identity.get('jobId')
        if not isinstance(jid, str) or not SAFE_ID.fullmatch(jid):
            return None
        if (descriptor.get('scope') != 'video_handoff_v1' or identity.get('photoProjectId') != project_id
                or identity.get('photoProjectRevision') != revision or (job and jid != job)):
            return None
        return dict(project=project, root=root, workspace=workspace, binding=binding,
                    revision=revision, descriptor=descriptor, identity=identity)
    except (ProjectStoreError, OSError, ValueError, TypeError, AttributeError, KeyError):
        return None


def local_file(workspace, ref):
    if not isinstance(ref, str) or not ref or '\\' in ref or ':' in ref or Path(ref).is_absolute() or '..' in Path(ref).parts:
        return None
    try:
        path = (workspace / ref).resolve()
        return path if path.is_relative_to(workspace.resolve()) and path.is_file() else None
    except (OSError, ValueError):
        return None


def image_path(context, shot_id):
    if not isinstance(shot_id, str) or not SAFE_ID.fullmatch(shot_id):
        return None
    return local_file(context['workspace'], f'video-inputs/{context["identity"]["jobId"]}/shot-images/{shot_id}.jpg')


def revision_number(value):
    return value if type(value) is int and value >= 1 else None


def handoff_time(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)', value):
        return None
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return value


def handoff_identity(context):
    if context is None:
        return None
    descriptor = context['descriptor']
    return {'jobId': context['identity']['jobId'],
            'revision': revision_number(descriptor.get('storyboardRevision')),
            'title': context['project']['title'], 'handedAt': handoff_time(descriptor.get('handedAt'))}


def handoff_projection(context):
    header = handoff_identity(context)
    if header is None:
        return None
    descriptor, identity = context['descriptor'], context['identity']
    try:
        shots = []
        for row in descriptor['shots']:
            shot, visual = row['shot'], row['visual']
            sid = shot['shotId']
            if not isinstance(sid, str) or not SAFE_ID.fullmatch(sid):
                return None
            image = visual.get('image')
            if isinstance(image, dict):
                path = image_path(context, sid)
                # Hash the actual local bytes so a changed/replaced image cannot
                # keep a previously cached version URL.
                version = hashlib.sha256(path.read_bytes()).hexdigest()[:20] if path else None
                image = {key: image.get(key) for key in ('source', 'rightsStatus', 'sourceTimeSeconds')}
                image['url'] = (f'/api/projects/{quote(identity["photoProjectId"], safe="")}/direct/handoff/images/{quote(sid, safe="")}?v={version}'
                                if path else None)
            else:
                image = None
            shots.append({**{key: shot[key] for key in ('shotId', 'startSeconds', 'endSeconds')},
                          **{key: row[key] for key in ('dialogue', 'subtitle', 'camera', 'audio')},
                          'visual': visual['text'], 'image': image})
        narration = descriptor.get('narration')
        narration = {'voice': narration.get('voiceId'), 'durationSeconds': narration.get('durationSeconds')} if isinstance(narration, dict) else None
        return {**header, 'shots': shots, 'narration': narration}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def newer_handoff(job, current):
    if current is None:
        return False
    bound = job.get('handoff')
    previous_revision = revision_number(bound.get('revision')) if isinstance(bound, dict) else None
    current_revision = revision_number(current.get('revision'))
    if previous_revision is not None and current_revision is not None:
        return previous_revision < current_revision
    try:
        handed = datetime.fromisoformat(current['handedAt'].replace('Z', '+00:00'))
        created = datetime.fromisoformat(job['createdAt'].replace('Z', '+00:00'))
        return handed > created
    except (KeyError, TypeError, ValueError, AttributeError):
        return False




def routes():
    base = '/api/projects/{projectId}/direct/handoff'
    return (dict(method='GET', path=base, operation_id='getDirectHandoff', summary='Read the current local handoff'),
            dict(method='GET', path=base + '/images/{shotId}', operation_id='getDirectHandoffImage',
                 summary='Read a locally available handoff image', response_media='image/jpeg'))


def operation_contract(operation, spec):
    if spec['operation_id'] == 'createDirectJob':
        operation['requestBody']['content']['application/json']['schema']['properties']['handoff'] = HANDOFF_REF
        operation['responses']['409']['description'] += '; handoff_changed when jobId or revision no longer matches the current local package'
    elif spec['operation_id'] == 'getDirectHandoff':
        image = {'type': ['object', 'null'], 'required': ['source', 'rightsStatus', 'sourceTimeSeconds', 'url'],
                 'properties': {'source': {'type': ['string', 'null']}, 'rightsStatus': {'type': ['string', 'null']},
                                'sourceTimeSeconds': {'type': ['number', 'null']}, 'url': {'type': ['string', 'null']}}}
        shot = {'shotId': {'type': 'string'}, 'startSeconds': {'type': 'number'}, 'endSeconds': {'type': 'number'},
                **{key: {'type': 'string'} for key in ('dialogue', 'visual', 'subtitle', 'camera', 'audio')}, 'image': image}
        properties = {**HANDOFF_REF['properties'], 'title': {'type': 'string'},
                      'handedAt': {'type': ['string', 'null'], 'format': 'date-time',
                                   'description': 'Top-level handedAt, an ISO UTC timestamp; null when absent or invalid.'},
                      'shots': {'type': 'array', 'items': {'type': 'object', 'required': list(shot), 'properties': shot}},
                      'narration': {'type': ['object', 'null'], 'required': ['voice', 'durationSeconds'], 'properties': {
                          'voice': {'type': ['string', 'null']}, 'durationSeconds': {'type': ['number', 'null']}}}}
        operation['responses']['200']['content']['application/json']['schema'] = {
            'type': 'object', 'required': ['ok', 'handoff'], 'properties': {'ok': {'const': True},
                'handoff': {'type': ['object', 'null'], 'required': list(properties), 'properties': properties}}}
    elif spec['operation_id'] == 'getDirectHandoffImage':
        operation.setdefault('parameters', []).append({'name': 'v', 'in': 'query', 'schema': {'type': 'string'},
                                        'description': 'Local image content fingerprint'})
        operation['responses']['404'] = {'description': 'Current handoff image unavailable or version changed'}
