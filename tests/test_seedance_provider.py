import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / 'integrations/dreamverse/seedance-provider'


def test_seedance_facts_and_manifest():
    facts = json.loads((PROVIDER / 'model-facts.json').read_text())
    package = json.loads((PROVIDER / 'package.json').read_text())
    assert facts['modelId'] == 'doubao-seedance-2-0-260128'
    assert facts['durationsSec'] == list(range(4, 16))
    assert '9:16' in facts['aspectRatios']
    assert '720p' in facts['resolutions']
    assert facts['source'].startswith('https://')
    assert (PROVIDER / package['exports']).is_file()


def test_install_registers_both_and_is_idempotent(tmp_path):
    launch = tmp_path / 'app/scripts/video-harness/launch.sh'
    launch.parent.mkdir(parents=True)
    launch.touch()
    profile = tmp_path / 'state/profiles/video-harness'
    profile.mkdir(parents=True)
    (profile / 'cordis.yml').write_text('[]\n')
    cmd = ['bash', str(PROVIDER.parent / 'install.sh'), str(tmp_path)]
    patch = profile / 'cordis.patch.yml'
    patch.write_bytes(b'- id: existing-plugin\n  disabled: true\n')
    subprocess.run([*cmd, '--provider', 'wanxiang'], check=True, capture_output=True)
    wan_only = patch.read_bytes()
    assert b'id: dv-seedance-provider' not in wan_only
    subprocess.run(cmd, check=True, capture_output=True)
    before = patch.read_bytes()
    assert before.startswith(wan_only)
    subprocess.run(cmd, check=True, capture_output=True)
    assert patch.read_bytes() == before
    assert before.count(b'id: dv-wanxiang-provider') == 1
    assert before.count(b'id: dv-seedance-provider') == 1
    subprocess.run([*cmd, '--provider', 'seedance'], check=True, capture_output=True)
    assert patch.read_bytes() == before
    assert (profile / 'node_modules/@dv/seedance-provider').resolve() == PROVIDER


def test_provider_against_local_ark_http(tmp_path):
    node = shutil.which('node') or str(ROOT / '.tools/node/bin/node')
    package = tmp_path / 'packages/dv/fastvideo/package.json'
    package.parent.mkdir(parents=True)
    package.write_text('{}')
    mock = package.parent / 'node_modules/@deepseek-ai/schemastery'
    mock.mkdir(parents=True)
    (mock / 'index.js').write_text(
        'const schema = new Proxy(() => schema, {get: () => schema}); module.exports = schema;'
    )
    script = tmp_path / 'test.mjs'
    script.write_text(r"""
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';

const plugin = await import(process.argv[2]);
const stateDir = process.argv[3];
const credential = 'fake-ark-credential';
process.env.DV_ARK_API_KEY = credential;
const routes = new Map();
const ctx = {
  inject(_names, configure) {
    configure({
      connection: { fetch: { register(route) {
        routes.set(route.path, route.fetch);
        return () => {};
      }}},
      effect(register) { register(); },
    });
  },
  effect() {},
};
const events = [];
const createPath = '/api/v3/contents/generations/tasks';
const server = createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const body = chunks.length ? JSON.parse(Buffer.concat(chunks)) : null;
  events.push({method: request.method, url: request.url, auth: request.headers.authorization, body});
  if (request.method === 'POST' && request.url === createPath) {
    const prompt = body.content[0].text;
    if (prompt === 'timeout') return;
    if (prompt === 'failure') {
      response.writeHead(400, {'Content-Type': 'application/json'});
      response.end(JSON.stringify({error: {code: 'InvalidParameter', message: credential}}));
      return;
    }
    response.end(JSON.stringify({id: 'task-ok'}));
    return;
  }
  if (request.method === 'GET' && request.url === createPath + '/task-ok') {
    response.end(JSON.stringify({id: 'task-ok', status: 'succeeded', usage: {completion_tokens: 500}}));
    return;
  }
  response.writeHead(404).end();
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  plugin.apply(ctx, {baseUrl: 'http://127.0.0.1:' + server.address().port, stateDir});
  const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
  function shot(prompt, seconds = 5) {
    const spec = {
      project: 'project', shot_id: prompt, model: 'doubao-seedance-2-0-260128',
      seconds, aspect_ratio: '9:16', resolution: '720p', prompt,
    };
    const hash = digest(['seedance', spec.model, seconds, spec.aspect_ratio, spec.resolution, prompt]);
    return {...spec, key: digest([spec.project, spec.shot_id, hash])};
  }
  async function call(action, data) {
    const handler = routes.get('/api/dv/seedance/' + action);
    const response = await handler(new Request('http://localhost/', {
      method: 'POST', body: JSON.stringify(data),
    }));
    return [response.status, await response.json()];
  }

  const valid = shot('ok');
  assert.deepEqual(await call('submit', valid), [200, {
    status: 'submitted', task_id: 'task-ok', submit_http_status: 200,
  }]);
  const receipt = JSON.parse(await readFile(stateDir + '/' + valid.key + '.json', 'utf8'));
  assert.equal(receipt.task_id, 'task-ok');
  assert.equal(events.length, 1);
  assert.deepEqual(await call('status', {key: valid.key, task_id: 'task-ok'}), [200, {
    status: 'SUCCEEDED', task_id: 'task-ok', billed_video_seconds: null,
  }]);
  assert.equal((await call('submit', valid))[1].task_id, 'task-ok');
  assert.equal((await call('submit', shot('outside', 16)))[0], 400);

  const rejected = shot('failure');
  assert.deepEqual((await call('submit', rejected))[1], {
    status: 'unknown', submit_http_status: 400, submit_error_code: 'InvalidParameter',
  });
  assert.equal((await call('receipt', {key: rejected.key}))[1].status, 'unknown');

  const timeout = AbortSignal.timeout;
  AbortSignal.timeout = ms => timeout.call(AbortSignal, Math.min(ms, 1000));
  const unknown = shot('timeout');
  assert.deepEqual(await call('submit', unknown), [200, {status: 'unknown'}]);
  assert.deepEqual(await call('submit', unknown), [200, {status: 'unknown'}]);
  assert.deepEqual(await call('receipt', {key: unknown.key}), [200, {status: 'unknown'}]);

  assert.deepEqual(events.map(event => [event.method, event.url]), [
    ['POST', createPath], ['GET', createPath + '/task-ok'], ['POST', createPath], ['POST', createPath],
  ]);
  assert.ok(events.every(event => event.auth === 'Bearer ' + credential));
  assert.deepEqual(events[0].body, {
    model: valid.model, content: [{type: 'text', text: 'ok'}], ratio: '9:16',
    resolution: '720p', duration: 5, seed: parseInt(valid.key.slice(0, 7), 16), watermark: false,
  });
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
""")
    result = subprocess.run(
        [node, str(script), (PROVIDER / 'index.ts').as_uri(), str(tmp_path / 'receipts')],
        cwd=tmp_path, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def bridge_module():
    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location('dreamverse_bridge', ROOT / 'scripts/aigc/dreamverse_bridge.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_bridge_shot(bridge, tmp_path, **options):
    manifest = tmp_path / 'shots.json'
    manifest.write_text(json.dumps({
        'shots': [{'shot_id': 'shot', 'prompt': '起跑', 'seconds': 5, 'aspect_ratio': '9:16', **options}],
    }))
    return bridge.read_shots(manifest)


class DreamVerseStub:
    url = 'http://127.0.0.1:49183'

    def __init__(self, transport_error):
        self.transport_error = transport_error
        self.events = []
        self.tasks = {}

    def json(self, route, body=None):
        self.events.append((route, body))
        if route == '/api/dv/projects':
            return [] if body is None else {'id': 'project-1'}
        if route == '/api/dv/operation/check':
            return {'problems': []}
        if route.endswith('/submit'):
            provider = route.split('/')[-2]
            assert body['key'] not in self.tasks
            self.tasks[body['key']] = provider
            if provider == 'seedance':
                raise self.transport_error('lost submit response')
            return {'task_id': 'task-wanxiang'}
        if route.endswith(('/receipt', '/status')):
            provider = route.split('/')[-2]
            assert self.tasks[body['key']] == provider
            return {'task_id': 'task-' + provider, 'status': 'SUCCEEDED'}
        if route == '/api/dv/history':
            return {'entries': []}
        if route == '/api/dv/operation':
            assert self.tasks[body['params']['extra']['bridge_confirmation']] == body['params']['provider']
            return {'id': 'render-1', 'status': 'done', 'outputs': ['video', 'still']}
        raise AssertionError(route)

    def download(self, asset_id, path):
        path.write_text(asset_id)


def test_bridge_provider_switch_requires_confirmation_and_uses_selected_routes(tmp_path):
    import pytest

    bridge = bridge_module()
    service = DreamVerseStub(bridge.TransportError)
    runner = bridge.Bridge(service, tmp_path, 1, 0.01)
    wan = read_bridge_shot(bridge, tmp_path)
    runner.run(wan, ['shot'])
    previous = runner.ledger['shots']['shot']
    assert previous['provider'] == 'wanxiang'
    wan_request = next(body for route, body in service.events if route == '/api/dv/wanxiang/submit')
    wan_hash = bridge.digest([wan_request[field] for field in ('model', 'seconds', 'aspect_ratio', 'resolution', 'prompt')])
    assert wan_request['key'] == bridge.digest(['project-1', 'shot', wan_hash])
    assert previous['confirmation_key'] != wan_request['key']

    seedance = read_bridge_shot(bridge, tmp_path, provider='seedance', seconds=14, aspect_ratio='21:9')
    service.events.clear()
    with pytest.raises(bridge.BridgeError, match='confirm'):
        runner.run(seedance, [])
    assert not service.events
    runner.run(seedance, ['shot'])
    current = runner.ledger['shots']['shot']
    assert current['provider'] == 'seedance'
    assert current['confirmation_key'] != previous['confirmation_key']
    assert current['task_id'] == 'task-seedance'
    calls = [(route, body) for route, body in service.events if route.startswith('/api/dv/seedance/')]
    assert [route for route, _ in calls] == [
        '/api/dv/seedance/submit', '/api/dv/seedance/receipt', '/api/dv/seedance/status',
    ]
    assert all(body['key'] == current['confirmation_key'] for _, body in calls)
    assert service.events[-1][1]['params']['provider'] == 'seedance'


def test_bridge_resumes_legacy_wanxiang_row_without_reconfirming(tmp_path):
    bridge = bridge_module()
    service = DreamVerseStub(bridge.TransportError)
    shots = read_bridge_shot(bridge, tmp_path)
    old_hash = bridge.digest(['wan2.6-t2v', 5, '9:16', '720p', '起跑'])
    old_key = bridge.digest(['project-1', 'shot', old_hash])
    service.tasks[old_key] = 'wanxiang'
    (tmp_path / 'ledger.json').write_text(json.dumps({
        'version': 1, 'dreamverse_url': service.url, 'dreamverse_project_id': 'project-1',
        'shots': {'shot': {
            'status': 'running', 'spec_hash': old_hash, 'confirmation_key': old_key,
            'cloud_status': 'RUNNING', 'task_id': 'task-wanxiang', 'billed_video_seconds': None,
            'dreamverse_record_id': None,
        }},
    }))

    runner = bridge.Bridge(service, tmp_path, 1, 0.01)
    runner.run(shots, [])
    assert service.events[0] == ('/api/dv/wanxiang/status', {'key': old_key, 'task_id': 'task-wanxiang'})
    assert all(not route.endswith('/submit') for route, _ in service.events)
    assert runner.ledger['shots']['shot']['status'] == 'completed'


def test_bridge_checks_only_populated_seedance_facts(tmp_path, monkeypatch):
    import pytest

    bridge = bridge_module()
    facts = tmp_path / 'seedance-provider/model-facts.json'
    facts.parent.mkdir()
    facts.write_text(json.dumps({'modelId': 'seedance-fixture', 'durationsSec': [5], 'frameSizes': {}, 'resolutions': []}))
    monkeypatch.setattr(bridge, 'PROVIDERS_ROOT', tmp_path)

    shot = read_bridge_shot(bridge, tmp_path, provider='seedance', resolution='fixture')['shot']
    assert shot['model'] == 'seedance-fixture'
    assert shot['resolution'] == 'fixture'
    with pytest.raises(bridge.BridgeError, match='seedance'):
        read_bridge_shot(bridge, tmp_path, provider='seedance', seconds=6)
