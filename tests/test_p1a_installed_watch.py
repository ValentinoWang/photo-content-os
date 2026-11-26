"""Installed Agent ``watch`` lands every formal handoff in the project the operator confirmed.

The U13 wheel (``P1A_AGENT_WHEEL``) is installed non-editable into an isolated venv; the shared
``.venv`` is only read for third-party dependencies. Media's server, Studio's confirmation UI and
rendering are doubles. No hand-written binding, ``PHOTO_STUDIO_VIDEO_BINDING`` or root ``video.json``
takes part in the delivered path.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import openclaw_product_contract as contract
import media_project_selection as selection
import openclaw_video_execution as execution
from studio.direct_handoff_contract import read_handoff, read_run_record, run_record_path, selection_root
from studio.project_store import ProjectStore

DEVICE = 'dev_fixture'
ACCOUNT = 'account_fixture'
TENANT = '11111111-1111-4111-8111-111111111111'
JOB = 'job_p1a_fixture'


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def build_package(project_id, project_revision, *, job_id=JOB, generation=3, device_id=DEVICE, variant='variant_fixture'):
    """A server-shaped formal job, descriptor and descriptor artifact for one project version."""
    digest = contract.load_snapshot()['catalog_digest']
    document = {'publicArtifactId': 'doc_fixture', 'revision': 2, 'bodyChecksum': 'sha256:' + '1' * 64,
                'bodyAuthority': 'internal', 'remoteDocumentVersion': None}
    identity = {'jobId': job_id, 'publicTenantId': 'tenant_fixture', 'publicContentId': 'content_fixture',
                'publicVariantId': variant, 'workRevision': 1, 'photoProjectId': project_id,
                'photoProjectRevision': project_revision, 'catalogDigest': digest, 'confirmationRef': 'confirm_fixture'}
    mx = {'identity': {'job_id': job_id, 'tenant_id': TENANT, 'work_id': variant, 'work_revision': 1,
                       'project_id': project_id, 'project_revision': project_revision, 'catalog_digest': digest,
                       'confirmation_ref': 'confirm_fixture'},
          'script': '已确认旁白',
          'storyboard': [dict(shot='01', visual='动画', dialogue='旁白', subtitle='字幕', camera='全屏', audio='配音')],
          'animations': [], 'tts_ref': None}
    mx['handoff_digest'] = contract.video_digest(mx)
    identity['confirmedContentDigest'] = contract.video_digest(
        {'script': mx['script'], 'shots': [], 'animations': [], 'documentRef': document, 'narrationCacheKey': None})
    binding = {'binding_id': 'binding_fixture', 'binding_generation': generation, 'public_account_id': ACCOUNT}
    descriptor = {'scope': 'video_handoff_v1', 'identity': identity, 'script': mx['script'], 'shots': [],
                  'animations': [], 'narration': None, 'mxHandoff': mx, 'documentRef': document, **binding}
    data = canonical(descriptor)
    meta = {'artifactId': 'desc_fixture', 'sha256': 'sha256:' + hashlib.sha256(data).hexdigest(),
            'mimeType': 'application/json', 'sizeBytes': len(data),
            'downloadPath': f'/media/api/jobs/{job_id}/video-artifacts/desc_fixture'}
    job = {'job_id': job_id, 'pipeline_id': 'media.edit.handoff.v1', 'pipeline_version': '1.0.0',
           'catalog_digest': digest, 'confirmation_ref': 'confirm_fixture', 'device_id': device_id,
           'input_refs': [f'video-inputs/{job_id}/handoff.json'], 'output_selection': [], 'video_identity': identity,
           'video_handoff_artifact': meta, 'exchange_scope': 'video_handoff_v1', 'revision': 1, 'state': 'queued', **binding}
    return descriptor, data, meta, job


# ---------------------------------------------------------------- installed wheel

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_PROBE = r'''
import importlib.metadata as m, json, openclaw_media
from openclaw_media.agent import Agent
names = [r.split(";")[0].split("=")[0].strip() for r in (m.requires("openclaw-media") or [])]
print(json.dumps({"file": openclaw_media.__file__, "version": m.version("openclaw-media"),
    "studio_port": "studio_port" in Agent.__dataclass_fields__,
    "dependencies": {n: [m.version(n), str(m.distribution(n).locate_file(""))] for n in names}}))
'''


@pytest.fixture(scope='module')
def installed(tmp_path_factory):
    value = os.environ.get('P1A_AGENT_WHEEL', '')
    wheel = Path(value)
    if not wheel.is_absolute() or not wheel.is_file():
        pytest.fail('P1A_AGENT_WHEEL must be the absolute path of the wheel built from the U13 commit')
    expected = os.environ.get('P1A_AGENT_WHEEL_SHA256')
    wheel_sha = _sha(wheel)
    assert expected in (None, '', wheel_sha), 'wheel hash differs from P1A_AGENT_WHEEL_SHA256'
    venv = tmp_path_factory.mktemp('installed') / 'venv'
    subprocess.run([sys.executable, '-m', 'venv', str(venv)], check=True, capture_output=True)
    python = venv / 'bin' / 'python'
    subprocess.run([str(python), '-m', 'pip', 'install', '--quiet', '--no-deps', '--no-index', '--no-cache-dir', str(wheel)],
                   check=True, capture_output=True)
    site = Path(subprocess.check_output([str(python), '-c', 'import sysconfig;print(sysconfig.get_paths()["purelib"])'], text=True).strip())
    # Existing third-party packages come from the interpreter running pytest; the wheel itself is shadowing-first.
    shared = Path(sysconfig.get_paths()['purelib']).resolve()
    (site / 'zz_existing_dependencies.pth').write_text(str(shared) + '\n')
    probe = json.loads(subprocess.check_output([str(python), '-c', _PROBE], text=True))
    assert Path(probe['file']).resolve().is_relative_to(venv.resolve()), probe['file']
    assert probe['studio_port'] is True
    members = {}
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.startswith('openclaw_media/') and name.endswith('.py'):
                members[name] = hashlib.sha256(archive.read(name)).hexdigest()
    assert 'openclaw_media/photo_project_selection.py' in members
    assert {name: _sha(site / name) for name in members} == members, 'installed files differ from the wheel'
    for name, (version, location) in probe['dependencies'].items():
        assert Path(location).resolve() == shared, f'{name} not taken from the existing environment'
    evidence = {'wheel': str(wheel), 'wheel_sha256': wheel_sha, 'source_sha': os.environ.get('P1A_AGENT_SOURCE_SHA', 'unrecorded'),
                'import_file': probe['file'], 'version': probe['version'], 'installed_files_checked': len(members),
                'dependencies': {n: v[0] for n, v in probe['dependencies'].items()}, 'dependency_root': str(shared)}
    print('P1A installed-agent evidence ' + json.dumps(evidence, sort_keys=True))
    if os.environ.get('P1A_EVIDENCE_PATH'):
        Path(os.environ['P1A_EVIDENCE_PATH']).write_text(json.dumps(evidence, indent=2, sort_keys=True))
    return SimpleNamespace(python=python, evidence=evidence)


# ---------------------------------------------------------------- driver executed with the installed wheel

_DRIVER = r'''
import json, sys, threading, base64, hashlib
from dataclasses import asdict
from pathlib import Path
cfg = json.loads(Path(sys.argv[1]).read_text())
sys.path[:0] = [cfg['repo'], cfg['scripts'], cfg['tests']]
import openclaw_media_agent as wrapper
import openclaw_video_execution as execution
from openclaw_media import cli
from openclaw_media.agent import Agent, AgentState, AgentStateStore
from openclaw_media.device_credentials import DeviceCredentialStore
from openclaw_media.remote_client import RemoteError
from test_p1a_installed_watch import build_package, canonical, DEVICE

REMOTE = Path(cfg['remote_file'])
OUT = Path(cfg['out'])
OUT.mkdir(parents=True, exist_ok=True)


def load():
    return json.loads(REMOTE.read_text())


def save(state):
    REMOTE.write_text(json.dumps(state))


class Keyring:
    def __init__(self): self.values = {}
    def set_password(self, service, username, password): self.values[(service, username)] = password
    def get_password(self, service, username): return self.values.get((service, username))
    def delete_password(self, service, username): self.values.pop((service, username), None)


class FileRemote:
    """Media server double; its state survives process restarts in one JSON file."""
    def __init__(self, *args, **kwargs): pass
    def close(self): pass

    def heartbeat(self, **request):
        s = load(); s['device_revision'] += 1; s['heartbeats'] = s.get('heartbeats', 0) + 1
        job = s['job']
        claim = {'job_id': job['job_id'], 'state': 'queued'} if job and job['state'] == 'queued' else None
        save(s)
        return dict(state='online', revision=s['device_revision'], api_compatible=True, catalog_compatible=True,
                    device_id=DEVICE, claimable_job=claim)

    def video_project_selection_list(self, device_id):
        s = load()
        assert device_id == DEVICE
        return {'requests': [s['request']] if not s['consumed'] else []}

    def video_project_selection_confirm(self, device_id, request_id, **call):
        s = load()
        assert device_id == DEVICE and request_id == s['request']['request_id']
        s['confirmations'].append(call)
        s['consumed'] = True
        descriptor, data, meta, job = build_package(call['project_id'], call['project_revision'], generation=3)
        mutation = cfg.get('mutation')
        if mutation == 'device':
            job['device_id'] = 'dev_other'
        if mutation == 'twin':
            for owner in (descriptor['identity'], descriptor['mxHandoff']['identity'], job['video_identity']):
                owner['photoProjectId' if 'photoProjectId' in owner else 'project_id'] = cfg['twin_id']
            descriptor['mxHandoff']['handoff_digest'] = __import__('openclaw_product_contract').video_digest(
                {k: v for k, v in descriptor['mxHandoff'].items() if k != 'handoff_digest'})
            data = canonical(descriptor); meta.update(sha256='sha256:' + hashlib.sha256(data).hexdigest(), sizeBytes=len(data))
        if mutation == 'digest':
            descriptor['mxHandoff']['handoff_digest'] = 'sha256:' + '0' * 64
            data = canonical(descriptor); meta.update(sha256='sha256:' + hashlib.sha256(data).hexdigest(), sizeBytes=len(data))
        s.update(descriptor=descriptor, data=base64.b64encode(data).decode(), meta=meta, job=job)
        s['binding'] = {'bindingId': 'binding_fixture', 'bindingGeneration': 3, 'deviceId': DEVICE, 'publicAccountId': 'account_fixture',
                        'photoProjectId': call['project_id'], 'photoProjectRevision': call['project_revision']}
        save(s)
        return {'binding': s['binding'], 'selectionRevision': s['request']['revision'] + 1}

    def job_list(self, **request):
        s = load(); job = s['job']
        return {'jobs': [job] if job and job['state'] in {'queued', 'leased', 'acknowledged', 'running'} else []}

    def _advance(self, state):
        s = load(); s['job'].update(state=state, revision=s['job']['revision'] + 1); save(s)
        return {'job': dict(s['job'])}

    def job_lease(self, *a, **k): return self._advance('leased')
    def job_ack(self, *a, **k): return self._advance('acknowledged')
    def job_start(self, *a, **k): return self._advance('running')

    def video_artifact_download(self, *a):
        s = load()
        return dict(ok=True, artifact=s['meta'], contentBase64=s['data'])

    def video_progress(self, job_id, **body):
        s = load(); s['progress'].append(body['steps']); save(s)
        return {'ok': True, 'job': s['job']}

    def video_artifact_upload(self, job_id, **request):
        s = load(); s['outputs'].append(request['kind']); save(s)
        return {'artifact': dict(artifactId=request['artifactId'], sha256=request['sha256'], mimeType=request['mimeType'],
                                 sizeBytes=request['sizeBytes'], downloadPath='/media/api/jobs/' + job_id + '/video-artifacts/' + request['artifactId'])}

    def job_result(self, job_id, **request):
        s = load(); s['results'].append(request); save(s)
        return self._advance(request['result_status'])


class FastStop(threading.Event):
    def wait(self, timeout=None): return self.is_set()


def provider(request):
    """The Studio confirmation double: explicit local decisions, or still pending."""
    with (OUT / 'confirm-calls.jsonl').open('a') as log:
        log.write(json.dumps(request) + '\n')
    return cfg.get('decision')


def render_double(self, node, context):
    binding = self._binding()
    workspace = Path(context['workspace_root']).resolve()
    inputs = context['inputs']
    descriptor_path = execution.local_path(workspace, inputs.get('workspace_ref', inputs.get('run_ref')))
    handoff = execution.validate_video_handoff(json.loads(descriptor_path.read_text()), binding['identity'], expected_handoff_digest=binding['handoff_digest'])
    full = self._descriptor(workspace, str(descriptor_path.relative_to(workspace)), handoff)
    out = execution.local_path(workspace, context['run_ref']); out.mkdir(parents=True, exist_ok=True)
    (out / 'preview.mp4').write_bytes(b'bounded native preview fixture')
    candidate = dict(publicCandidateId='candidate_fixture', identity=full['identity'], status='check_failed', description='Photo receipt',
                     durationSeconds=1, sourceDurationSeconds=1, frameCount=30, fps=30, removedSeconds=0, cutCount=0, cuts=[], animations=[],
                     checks={k: 'unknown' for k in ['playable', 'avSync', 'frameCount', 'sourceUnchanged', 'subtitles', 'blackFrames']},
                     subtitles='已确认字幕', subtitleBurnedIn=False, subtitleBottomRatio=.9,
                     preview=dict(artifact=None, width=320, height=180, shortEdge=180, longEdge=320), returnedAt='2026-10-12T00:00:00Z',
                     candidateDigest='sha256:' + '0' * 64)
    candidate['checks'].update(avOffsetSeconds=0, avOffsetLimitSeconds=.1, expectedFrames=30, actualFrames=30)
    artifact = out / 'handoff_manifest.json'
    artifact.write_bytes(canonical({'candidate': candidate, 'preview_ref': str((out / 'preview.mp4').relative_to(workspace)), 'progress': {'waveformPeaks': [.1, .2]}}))
    with (OUT / 'renders.jsonl').open('a') as log:
        log.write(json.dumps({'job': full['identity']['jobId']}) + '\n')
    return {'handoff_manifest': {'local_path': str(artifact), 'artifact_ref': str(artifact.relative_to(workspace)),
                                 'mime_type': 'application/json', 'size_bytes': artifact.stat().st_size, 'cloud_bytes': 0}}


real_binding = execution.PhotoNodeRegistry._binding
def recording_binding(self):
    data = real_binding(self)
    (OUT / 'observed-binding.json').write_text(json.dumps(data))
    return data


execution.PhotoNodeRegistry._binding = recording_binding
real_factory = execution.installed_runtime_factory
def interrupting_factory(*args, **kwargs):
    create = real_factory(*args, **kwargs)
    def wrapped(workspace, catalog, *, run_binding=None):
        flag = OUT / 'crashed-once'
        if run_binding is not None and cfg.get('crash_once') and not flag.exists():
            flag.write_text('1')
            raise SystemExit('interrupted after Studio staging')
        return create(workspace, catalog, run_binding=run_binding)
    return wrapped
execution.installed_runtime_factory = interrupting_factory
execution.PhotoNodeRegistry.execute = render_double
cli.RemoteClient = FileRemote
keyring = Keyring()
def credentials():
    store = DeviceCredentialStore(backend=keyring); store.put_device(DEVICE, 'fixture-secret'); return store
cli.DeviceCredentialStore = credentials

state_path = Path(cfg['agent_dir']) / 'state.json'
if not state_path.exists():
    from openclaw_media.catalog import InstalledCatalog
    AgentStateStore(state_path).save(AgentState(remote_base_url='https://fixture.invalid', device_id=DEVICE,
        catalog_digest=InstalledCatalog().manifest['catalog_digest'], workspace=cfg['workspace']))

stop = FastStop(); counter = [0]
real_once = Agent.run_once
def counted(self):
    result = real_once(self)
    counter[0] += 1
    (OUT / 'codes.jsonl').open('a').write(json.dumps(result.last_code) + '\n')
    if counter[0] >= cfg['cycles']: stop.set()
    return result
Agent.run_once = counted
real_forever = Agent.run_forever
Agent.run_forever = lambda self, *, interval=30.0, stop_event=None: real_forever(self, interval=interval, stop_event=stop)

argv = ['watch', '--agent-dir', cfg['agent_dir'], '--workspace', cfg['workspace'], '--state-dir', cfg['state_dir'], '--interval', '1']
try:
    rc = wrapper.main(argv, confirmation_provider=provider)
except SystemExit as exc:
    print('DRIVER-EXIT ' + json.dumps(str(exc)))
    sys.exit(3)
print('DRIVER-RC ' + json.dumps(rc))
'''


class World:
    def __init__(self, root: Path):
        self.root = root
        self.media = root / 'media'
        self.workspace = self.media / 'agent-workspace'
        self.state_dir = root / 'studio-state'
        self.agent_dir = root / 'agent'
        self.out = root / 'out'
        self.remote_file = root / 'remote.json'
        self.home = root / 'home'
        for folder in (self.workspace, self.agent_dir, self.home):
            folder.mkdir(parents=True)
        self.store = ProjectStore(self.state_dir)
        self.project = self.make_project('real')
        self.twin = self.make_project('twin')
        self.request = {'request_id': 'request_fixture', 'public_variant_id': 'variant_fixture', 'public_account_id': ACCOUNT,
                        'public_session_id': 'session_fixture', 'expected_work_revision': 1,
                        'expires_at': '2099-01-01T00:00:00+00:00', 'revision': 1}
        self.remote_file.write_text(json.dumps({'device_revision': 1, 'request': self.request, 'consumed': False, 'job': None,
                                                'confirmations': [], 'results': [], 'outputs': [], 'progress': []}))

    def make_project(self, name):
        folder = self.media / 'projects' / name
        folder.mkdir(parents=True)
        (folder / 'source.mp4').write_bytes(b'synthetic source video ' + name.encode())
        # Same title on purpose: the title never identifies a project.
        return self.store.create_project(title='同名口播项目', local_workspace=str(folder))

    def decision(self, project=None):
        return {'confirmed': True, 'selection_mode': 'existing', 'project_id': (project or self.project)['id']}

    def remote(self):
        return json.loads(self.remote_file.read_text())

    def lines(self, name):
        path = self.out / name
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def watch(self, installed, *, cycles=3, decision=None, mutation=None, crash_once=False, timeout=240):
        config = {'repo': str(ROOT), 'scripts': str(ROOT / 'scripts'), 'tests': str(ROOT / 'tests'), 'media': str(self.media),
                  'agent_dir': str(self.agent_dir), 'workspace': str(self.workspace), 'state_dir': str(self.state_dir),
                  'remote_file': str(self.remote_file), 'out': str(self.out), 'cycles': cycles, 'decision': decision,
                  'mutation': mutation, 'crash_once': crash_once, 'twin_id': self.twin['id']}
        (self.root / 'driver-config.json').write_text(json.dumps(config))
        (self.root / 'driver.py').write_text(_DRIVER)
        poison = self.root / 'poison-binding.json'
        env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PHOTO_STUDIO_VIDEO_WORKSPACE'}}
        env.update(LOCAL_MEDIA_ROOT=str(self.media), HOME=str(self.home), PHOTO_STUDIO_VIDEO_BINDING=str(poison),
                   PHOTO_STUDIO_VIDEO_WORKSPACE=str(self.workspace), PYTHONDONTWRITEBYTECODE='1')
        done = subprocess.run([str(installed.python), str(self.root / 'driver.py'), str(self.root / 'driver-config.json')],
                              capture_output=True, text=True, timeout=timeout, env=env)
        return done


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path / 'media'))
    return World(tmp_path)


def assert_delivered(world, project, *, job=JOB):
    # A fresh store object: the device restarted, the project is still found by ID and version.
    store = ProjectStore(world.state_dir)
    context = read_handoff(store, project['id'], delivered={'device_id': DEVICE})
    assert context is not None
    assert context['project']['id'] == project['id'] and context['revision'] == project['revision']
    assert context['identity']['jobId'] == job and context['descriptor']['binding_generation'] == 3
    assert context['workspace'] == world.workspace.resolve() and context['root'].is_relative_to(world.media.resolve())
    assert context['binding']['source_refs'] == ['source.mp4'] and context['binding']['creative_store'] == str(store.path)
    assert context['binding']['identity']['job_id'] == job
    return context


# ---------------------------------------------------------------- the ordinary watch with the installed wheel

def test_installed_wheel_is_the_u13_build(installed):
    assert installed.evidence['installed_files_checked'] > 10
    assert len(installed.evidence['wheel_sha256']) == 64


def test_ordinary_watch_confirms_stages_and_reads_back_the_same_project(installed, world):
    done = world.watch(installed, decision=world.decision())
    assert 'DRIVER-RC 0' in done.stdout, (done.stdout[-1500:], done.stderr[-1500:])
    remote = world.remote()
    assert remote['confirmations'] == [{'expected_revision': 1, 'project_id': world.project['id'],
                                        'project_revision': world.project['revision'], 'selection_mode': 'existing'}]
    assert [(r['result_status'], r['failure_code']) for r in remote['results']] == [('succeeded', None)]
    assert remote['outputs'] == ['preview_mp4', 'subtitle_text', 'candidate_json']
    assert world.lines('renders.jsonl') == [{'job': JOB}]
    context = assert_delivered(world, world.project)
    observed = json.loads((world.out / 'observed-binding.json').read_text())
    assert observed['identity']['project_id'] == world.project['id'] and observed['identity']['job_id'] == JOB
    assert Path(observed['project_root']) == context['root'] and observed['source_refs'] == ['source.mp4']
    assert observed['steps'][0]['action'] == 'editor' and observed['steps'][0]['kwargs']['source'] == {'local_ref': 'source.mp4'}
    # Everything stored is relative to the media root.
    record = read_run_record(selection_root(world.media), JOB)
    assert record['workspace_ref'] == 'agent-workspace' and record['project_root_ref'] == 'projects/real'
    text = json.dumps(record)
    assert str(world.media) not in text and str(world.root) not in text
    assert not (world.workspace / 'video.json').exists() and not (world.media / 'projects' / 'real' / 'video.json').exists()


def test_restart_repeats_without_a_new_run_and_keeps_the_same_package(installed, world):
    first = world.watch(installed, decision=world.decision())
    assert 'DRIVER-RC 0' in first.stdout, (first.stdout[-1500:], first.stderr[-1500:])
    before = read_run_record(selection_root(world.media), JOB)
    second = world.watch(installed, cycles=2, decision=None)
    assert 'DRIVER-RC 0' in second.stdout, (second.stdout[-1500:], second.stderr[-1500:])
    assert world.lines('renders.jsonl') == [{'job': JOB}]
    assert read_run_record(selection_root(world.media), JOB) == before
    assert len(world.remote()['results']) == 1
    assert_delivered(world, world.project)


def test_restart_after_staging_resumes_the_same_job(installed, world):
    first = world.watch(installed, decision=world.decision(), crash_once=True)
    assert first.returncode == 3 and 'DRIVER-EXIT' in first.stdout, (first.stdout[-1500:], first.stderr[-1500:])
    staged = read_run_record(selection_root(world.media), JOB)
    assert staged is not None and world.remote()['results'] == []
    second = world.watch(installed, cycles=3, decision=None, crash_once=True)
    assert 'DRIVER-RC 0' in second.stdout, (second.stdout[-1500:], second.stderr[-1500:])
    assert read_run_record(selection_root(world.media), JOB) == staged
    assert [(r['result_status'], r['failure_code']) for r in world.remote()['results']] == [('succeeded', None)]
    assert world.lines('renders.jsonl') == [{'job': JOB}]
    assert_delivered(world, world.project)


def test_watch_without_a_local_confirmation_stays_pending_and_delivers_nothing(installed, world):
    done = world.watch(installed, cycles=2, decision=None)
    assert 'DRIVER-RC 0' in done.stdout, (done.stdout[-1500:], done.stderr[-1500:])
    remote = world.remote()
    assert remote['confirmations'] == [] and remote['job'] is None
    assert world.lines('codes.jsonl') == ['video_selection_pending', 'video_selection_pending']
    assert not (selection_root(world.media) / 'runs').exists()
    assert read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE}) is None


def test_creating_a_project_needs_an_explicit_title_confirmation(installed, world):
    # Studio imports the source into the new project's folder before the formal job arrives.
    folder = world.media / 'p1a-projects' / 'request_fixture'
    folder.mkdir(parents=True)
    (folder / 'source.mp4').write_bytes(b'synthetic source video created')
    done = world.watch(installed, decision={'confirmed': True, 'selection_mode': 'created', 'title': '新建口播'})
    assert 'DRIVER-RC 0' in done.stdout, (done.stdout[-1500:], done.stderr[-1500:])
    confirmation = world.remote()['confirmations'][0]
    assert confirmation['selection_mode'] == 'created'
    created = ProjectStore(world.state_dir).get_project(confirmation['project_id'])
    assert created['title'] == '新建口播' and created['id'] not in {world.project['id'], world.twin['id']}
    assert [r['result_status'] for r in world.remote()['results']] == ['succeeded']
    context = read_handoff(ProjectStore(world.state_dir), created['id'], delivered={'device_id': DEVICE})
    assert context['project']['id'] == created['id'] and context['identity']['jobId'] == JOB
    assert read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE}) is None


@pytest.mark.parametrize('mutation,code', [
    ('device', 'video_identity_stale'),
    ('digest', 'video_descriptor_digest_rejected'),
    ('twin', 'video_identity_stale'),
])
def test_wrong_device_digest_or_same_title_project_never_reach_the_project(installed, world, mutation, code):
    done = world.watch(installed, decision=world.decision(), mutation=mutation)
    assert 'DRIVER-RC' in done.stdout, (done.stdout[-1500:], done.stderr[-1500:])
    results = world.remote()['results']
    assert results and results[0]['failure_code'] == code and world.lines('renders.jsonl') == []
    assert read_run_record(selection_root(world.media), JOB) is None
    assert read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE}) is None
    assert read_handoff(world.store, world.twin['id'], delivered={'device_id': DEVICE}) is None


# ---------------------------------------------------------------- Studio port (in-process, no wheel needed)

def new_port(world, decision=None, device=DEVICE):
    return selection.StudioSelectionPort(world.store, device_id=device, workspace=world.workspace,
                                         confirm=lambda request: decision)


def confirmed(world, port=None, request=None):
    port = port or new_port(world, world.decision())
    result = port.select_project(request or world.request)
    assert result['status'] == 'confirmed'
    return port, result['local_selection']


def package(world, selected, *, project=None, **kwargs):
    project = project or world.project
    descriptor, data, meta, job = build_package(project['id'], project['revision'], **kwargs)
    folder = world.workspace / 'video-inputs' / descriptor['identity']['jobId']
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'video.json').write_bytes(data)
    (folder / 'handoff.json').write_bytes(canonical(descriptor['mxHandoff']))
    return descriptor, f"video-inputs/{descriptor['identity']['jobId']}/video.json"


def test_select_project_is_pending_until_the_operator_confirms(world):
    assert new_port(world, None).select_project(world.request) == {'status': 'pending'}
    assert new_port(world, {'status': 'pending'}).select_project(world.request) == {'status': 'pending'}
    assert not (selection_root(world.media) / 'requests').exists()


@pytest.mark.parametrize('decision', [
    {'selection_mode': 'existing', 'project_id': 'x'},
    {'confirmed': 'yes', 'selection_mode': 'existing', 'project_id': 'x'},
    {'confirmed': True, 'selection_mode': 'existing'},
    {'confirmed': True, 'selection_mode': 'created'},
    {'confirmed': True, 'selection_mode': 'other', 'project_id': 'x'},
    {'confirmed': True, 'selection_mode': 'existing', 'project_id': 'missing-project-id', 'title': 'extra'},
])
def test_select_project_rejects_anything_but_an_explicit_confirmation(world, decision):
    with pytest.raises(selection.SelectionError):
        new_port(world, decision).select_project(world.request)
    assert not (selection_root(world.media) / 'requests').exists()


def test_confirmation_replays_the_same_selection_after_restart_and_create_is_once(world):
    created = {'confirmed': True, 'selection_mode': 'created', 'title': '新建口播'}
    first = new_port(world, created).select_project(world.request)['local_selection']
    before = len(world.store.list_projects())
    assert first['selection_mode'] == 'created' and first['device_id'] == DEVICE
    replay = new_port(world, None).select_project(world.request)
    assert replay == {'status': 'confirmed', 'local_selection': first}
    # A lost journal after creating must not create a second project for the same request.
    (selection_root(world.media) / 'requests' / 'request_fixture.json').unlink()
    again = new_port(world, created).select_project(world.request)['local_selection']
    assert again['project_id'] == first['project_id'] and len(world.store.list_projects()) == before
    assert Path(world.store.local_workspace_path(first['project_id'])).resolve().is_relative_to(world.media)


def test_expired_request_cannot_be_confirmed_and_changed_request_is_stale(world):
    expired = {**world.request, 'expires_at': '2000-01-01T00:00:00+00:00'}
    with pytest.raises(selection.SelectionError) as raised:
        new_port(world, world.decision()).select_project(expired)
    assert raised.value.code == 'video_selection_expired'
    confirmed(world)
    with pytest.raises(selection.SelectionError) as stale:
        new_port(world, None).select_project({**world.request, 'revision': 2})
    assert stale.value.code == 'video_identity_stale'


def test_stage_writes_one_record_and_replays_idempotently(world):
    port, chosen = confirmed(world)
    descriptor, input_ref = package(world, chosen)
    result = port.stage_handoff(descriptor, input_ref, chosen)
    assert result == {'job_id': JOB, 'device_id': DEVICE, 'project_id': world.project['id'],
                      'project_revision': world.project['revision'], 'confirmation_ref': 'confirm_fixture',
                      'handoff_digest': descriptor['mxHandoff']['handoff_digest'], 'input_ref': input_ref, 'binding_generation': 3}
    record = read_run_record(selection_root(world.media), JOB)
    restarted = new_port(world, None)
    assert restarted.stage_handoff(descriptor, input_ref, chosen) == result
    assert read_run_record(selection_root(world.media), JOB) == record
    context = read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE})
    assert context['identity']['jobId'] == JOB and context['project']['id'] == world.project['id']


def test_stage_rejects_a_different_package_for_the_same_job(world):
    port, chosen = confirmed(world)
    descriptor, input_ref = package(world, chosen)
    port.stage_handoff(descriptor, input_ref, chosen)
    other, _ = package(world, chosen, generation=4)
    with pytest.raises(selection.SelectionError) as raised:
        port.stage_handoff(other, input_ref, chosen)
    assert raised.value.code == 'idempotency_conflict'


@pytest.mark.parametrize('mutation', ['selection', 'device', 'project', 'revision', 'digest', 'ref', 'content', 'variant', 'sources'])
def test_stage_rejects_mismatched_identity_before_writing(world, mutation):
    port, chosen = confirmed(world)
    descriptor, input_ref = package(world, chosen)
    project = world.project
    if mutation == 'selection':
        chosen = {**chosen, 'project_revision': 99}
    if mutation == 'device':
        port = new_port(world, None, device='dev_other')
    if mutation == 'project':
        descriptor, input_ref = package(world, chosen, project=world.twin)
    if mutation == 'revision':
        world.store.update_project(project['id'], {'title': '改名'}, expected_revision=project['revision'])
    if mutation == 'digest':
        descriptor['mxHandoff']['handoff_digest'] = 'sha256:' + '0' * 64
    if mutation == 'ref':
        input_ref = 'video-inputs/other/video.json'
    if mutation == 'content':
        (world.workspace / 'video-inputs' / JOB / 'video.json').write_bytes(b'{}')
    if mutation == 'variant':
        chosen = {**chosen, 'public_variant_id': 'variant_other'}
    if mutation == 'sources':
        (world.media / 'projects' / 'real' / 'second.mov').write_bytes(b'ambiguous')
    with pytest.raises(selection.SelectionError):
        port.stage_handoff(descriptor, input_ref, chosen)
    assert read_run_record(selection_root(world.media), JOB) is None


def test_stage_needs_a_confirmed_selection_for_that_request(world):
    port = new_port(world, None)
    chosen = {'request_id': 'request_fixture', 'device_id': DEVICE}
    descriptor, input_ref = package(world, chosen)
    with pytest.raises(selection.SelectionError) as raised:
        port.stage_handoff(descriptor, input_ref, chosen)
    assert raised.value.code == 'video_selection_missing'


# ---------------------------------------------------------------- Studio read_handoff and the registry

def stage(world):
    port, chosen = confirmed(world)
    descriptor, input_ref = package(world, chosen)
    return port.stage_handoff(descriptor, input_ref, chosen), descriptor


def test_read_handoff_ignores_env_binding_and_root_video_json(world, monkeypatch):
    poison = world.root / 'poison.json'
    poison.write_text('{}')
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING', str(poison))
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_WORKSPACE', str(world.workspace))
    descriptor, *_ = build_package(world.project['id'], world.project['revision'], job_id='job_root_fallback')
    for folder in (world.workspace, world.media / 'projects' / 'real'):
        (folder / 'video.json').write_bytes(canonical(descriptor))
    assert read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE}) is None
    run, _ = stage(world)
    context = read_handoff(world.store, world.project['id'], delivered={'device_id': DEVICE})
    assert context['identity']['jobId'] == run['job_id'] == JOB
    # The explicit legacy environment/root input still works for existing callers.
    monkeypatch.setenv('PHOTO_STUDIO_VIDEO_BINDING', '')
    assert read_handoff(world.store, world.project['id'])['identity']['jobId'] == 'job_root_fallback'


@pytest.mark.parametrize('change', ['device', 'project', 'revision', 'digest', 'record_digest', 'binding', 'moved_workspace'])
def test_read_handoff_rejects_project_device_version_or_digest_mismatch(world, change):
    run, descriptor = stage(world)
    device, project_id = DEVICE, world.project['id']
    record_path = run_record_path(selection_root(world.media), JOB)
    video = world.workspace / 'video-inputs' / JOB / 'video.json'
    if change == 'device':
        device = 'dev_other'
    if change == 'project':
        project_id = world.twin['id']
    if change == 'revision':
        world.store.update_project(project_id, {'title': '改名'}, expected_revision=world.project['revision'])
    if change == 'digest':
        tampered = json.loads(video.read_text())
        tampered['mxHandoff']['script'] = '被改过'
        video.write_bytes(canonical(tampered))
    if change == 'record_digest':
        record = json.loads(record_path.read_text())
        record['handoff_digest'] = 'sha256:' + '0' * 64
        record_path.write_text(json.dumps(record))
    if change == 'binding':
        tampered = json.loads(video.read_text())
        tampered['binding_generation'] = 4
        video.write_bytes(canonical(tampered))
    if change == 'moved_workspace':
        record = json.loads(record_path.read_text())
        record['workspace_ref'] = '../escape'
        record_path.write_text(json.dumps(record))
    assert read_handoff(world.store, project_id, delivered={'device_id': device}) is None


def test_registry_binding_is_derived_and_checks_the_project_version(world):
    run, _ = stage(world)
    catalog = SimpleNamespace(manifest={'catalog_digest': contract.load_snapshot()['catalog_digest']})
    source = lambda: selection.resolve_run_binding(run, store=world.store, device_id=DEVICE)
    registry = execution.PhotoNodeRegistry(catalog, None, binding_source=source)
    binding = registry._binding()
    assert binding['identity']['project_id'] == world.project['id'] and binding['creative_store'] == str(world.store.path)
    for changed in ({**run, 'project_id': world.twin['id']}, {**run, 'binding_generation': 4}, {**run, 'handoff_digest': 'sha256:' + '0' * 64},
                    {**run, 'job_id': 'job_other'}, {**run, 'extra': 1}):
        with pytest.raises(contract.ProductContractError):
            selection.resolve_run_binding(changed, store=world.store, device_id=DEVICE)
    with pytest.raises(contract.ProductContractError):
        selection.resolve_run_binding(run, store=world.store, device_id='dev_other')
    world.store.update_project(world.project['id'], {'title': '改名'}, expected_revision=world.project['revision'])
    with pytest.raises(contract.ProductContractError) as stale:
        registry._binding()
    assert stale.value.code == 'photo_binding_rejected'
    with pytest.raises(contract.ProductContractError):
        execution.PhotoNodeRegistry(catalog, None)


def test_old_explicit_binding_entry_is_gone_from_the_wrapper():
    script = ROOT / 'scripts' / 'openclaw_media_agent.py'
    removed_option = '--photo' + '-binding'
    assert removed_option not in script.read_text() and 'photo_binding' not in script.read_text()
    for command in (['once'], ['watch'], ['run', 'pipeline', '--workspace', 'w']):
        done = subprocess.run([sys.executable, str(script), *command, removed_option, 'x'], capture_output=True, text=True)
        assert done.returncode == 2 and f'unrecognized arguments: {removed_option}' in done.stderr, done.stderr
