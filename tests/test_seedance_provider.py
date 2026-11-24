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
