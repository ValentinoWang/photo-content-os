from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
WAN_PROVIDER = ROOT / "integrations/dreamverse/wanxiang-provider"


def bridge_module():
    spec = spec_from_file_location("dreamverse_bridge", ROOT / "scripts/aigc/dreamverse_bridge.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_single(bridge, tmp_path, **options):
    manifest = tmp_path / "shots.json"
    manifest.write_text(
        json.dumps(
            {
                "shots": [
                    {
                        "shot_id": "track",
                        "prompt": "清晨空跑道慢推，画面里没有人",
                        "seconds": 5,
                        "aspect_ratio": "9:16",
                        **options,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return bridge.read_shots(manifest)


class BridgeStub:
    url = "http://127.0.0.1:49183"

    def __init__(self):
        self.events = []
        self.tasks = {}

    def json(self, route, body=None):
        self.events.append((route, body))
        if route == "/api/dv/projects":
            return [] if body is None else {"id": "project-1"}
        if route == "/api/dv/operation/check":
            return {"problems": []}
        if route == "/api/dv/wanxiang/submit":
            assert body["key"] not in self.tasks
            self.tasks[body["key"]] = body
            return {"task_id": f"task-{len(self.tasks)}", "status": "submitted"}
        if route == "/api/dv/wanxiang/status":
            assert body["key"] in self.tasks
            return {"task_id": body["task_id"], "status": "SUCCEEDED", "billed_video_seconds": 5}
        if route == "/api/dv/history":
            return {"entries": []}
        if route == "/api/dv/operation":
            key = body["params"]["extra"]["bridge_confirmation"]
            assert key in self.tasks
            return {"id": f"render-{len(self.tasks)}", "status": "done", "outputs": ["video", "still"]}
        raise AssertionError(route)

    def download(self, asset_id, path):
        path.write_text(asset_id, encoding="utf-8")


def test_wanxiang_defaults_overrides_and_reconfirmation(tmp_path):
    bridge = bridge_module()
    service = BridgeStub()
    runner = bridge.Bridge(service, tmp_path, 1, 0.01)

    default_shots = read_single(bridge, tmp_path)
    default_spec = default_shots["track"]
    assert default_spec["prompt_extend"] is True
    for keyword in ("品牌标识", "logo", "商标", "水印", "文字"):
        assert keyword in default_spec["negative_prompt"]

    runner.run(default_shots, ["track"])
    first_row = dict(runner.ledger["shots"]["track"])
    first_submit = next(body for route, body in service.events if route == "/api/dv/wanxiang/submit")
    first_op = next(body for route, body in service.events if route == "/api/dv/operation")
    assert first_submit["prompt_extend"] is True
    assert first_submit["negative_prompt"] == bridge.DEFAULT_WAN_NEGATIVE_PROMPT
    assert first_op["params"]["extra"]["prompt_extend"] is True
    assert first_op["params"]["extra"]["negative_prompt"] == bridge.DEFAULT_WAN_NEGATIVE_PROMPT
    assert first_row["prompt_extend"] is True
    assert first_row["negative_prompt"] == bridge.DEFAULT_WAN_NEGATIVE_PROMPT

    # Changing prompt_extend to false must require fresh confirmation and a new provider key.
    no_extend = read_single(bridge, tmp_path, prompt_extend=False)
    service.events.clear()
    with pytest.raises(bridge.BridgeError, match="confirm"):
        runner.run(no_extend, [])
    assert not service.events

    runner.run(no_extend, ["track"])
    second_row = dict(runner.ledger["shots"]["track"])
    second_submit = next(body for route, body in service.events if route == "/api/dv/wanxiang/submit")
    assert second_row["confirmation_key"] != first_row["confirmation_key"]
    assert second_submit["key"] != first_submit["key"]
    assert second_submit["prompt_extend"] is False
    assert second_submit["negative_prompt"] == bridge.DEFAULT_WAN_NEGATIVE_PROMPT
    assert second_row["prompt_extend"] is False

    # Overriding negative_prompt (including empty string) must also require reconfirmation.
    cleared = read_single(bridge, tmp_path, prompt_extend=False, negative_prompt="")
    service.events.clear()
    with pytest.raises(bridge.BridgeError, match="confirm"):
        runner.run(cleared, [])
    runner.run(cleared, ["track"])
    third_row = dict(runner.ledger["shots"]["track"])
    third_submit = next(body for route, body in service.events if route == "/api/dv/wanxiang/submit")
    assert third_row["confirmation_key"] != second_row["confirmation_key"]
    assert third_submit["key"] != second_submit["key"]
    assert third_submit["negative_prompt"] == ""
    assert third_row["negative_prompt"] == ""


def test_wanxiang_and_seedance_control_validation(tmp_path):
    bridge = bridge_module()

    # Exact 500-character boundary is accepted; 501 characters is rejected.
    at_limit = read_single(bridge, tmp_path, negative_prompt="字" * 500)
    assert len(at_limit["track"]["negative_prompt"]) == 500
    with pytest.raises(bridge.BridgeError, match="negative_prompt"):
        read_single(bridge, tmp_path, negative_prompt="字" * 501)

    for bad_extend in (1, 0, "false", None):
        with pytest.raises(bridge.BridgeError, match="prompt_extend"):
            read_single(bridge, tmp_path, prompt_extend=bad_extend)

    for bad_negative in (123, None, ["logo"]):
        with pytest.raises(bridge.BridgeError, match="negative_prompt"):
            read_single(bridge, tmp_path, negative_prompt=bad_negative)

    # Seedance does not support prompt_extend or negative_prompt in the official Ark API.
    with pytest.raises(bridge.BridgeError, match="seedance"):
        read_single(bridge, tmp_path, provider="seedance", prompt_extend=False)
    with pytest.raises(bridge.BridgeError, match="seedance"):
        read_single(bridge, tmp_path, provider="seedance", negative_prompt="logo")


def test_wanxiang_provider_local_http_controls_and_hash_parity(tmp_path):
    bridge = bridge_module()
    node = shutil.which("node") or str(ROOT / ".tools/node/bin/node")
    package = tmp_path / "packages/dv/fastvideo/package.json"
    package.parent.mkdir(parents=True)
    package.write_text("{}", encoding="utf-8")
    mock = package.parent / "node_modules/@deepseek-ai/schemastery"
    mock.mkdir(parents=True)
    (mock / "index.js").write_text(
        "const schema = new Proxy(() => schema, {get: () => schema}); module.exports = schema;",
        encoding="utf-8",
    )

    cases = [
        ("default_controls", {}),
        ("no_extend", {"prompt_extend": False}),
        ("custom_negative", {"prompt_extend": False, "negative_prompt": "人物、品牌标识、水印"}),
        ("clear_negative", {"negative_prompt": ""}),
    ]
    expected = {}
    for name, overrides in cases:
        spec = read_single(bridge, tmp_path, **overrides)["track"]
        legacy_hash = bridge.specification_hash(spec, legacy=True)
        expected[name] = {
            "spec": spec,
            "legacy_hash": legacy_hash,
            "provider_key": bridge.digest(["project-1", name, legacy_hash]),
        }

    script = tmp_path / "test_wanxiang.mjs"
    script.write_text(
        r"""
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';

const plugin = await import(process.argv[2]);
const stateDir = process.argv[3];
const expected = JSON.parse(await readFile(process.argv[4], 'utf8'));
process.env.DV_WAN_API_KEY = 'fake-wan-credential';

const routes = new Map();
let registeredEntry = null;
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
  dvModels: {
    register(entry) {
      registeredEntry = entry;
      return () => {};
    },
  },
  effect(register) { register(); },
};

const calls = [];
const server = createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const body = chunks.length ? JSON.parse(Buffer.concat(chunks)) : null;
  calls.push({ method: request.method, url: request.url, body });
  if (request.method === 'POST' && request.url === '/api/v1/services/aigc/video-generation/video-synthesis') {
    response.end(JSON.stringify({ output: { task_id: 'wan-task-' + calls.length } }));
    return;
  }
  response.writeHead(404).end();
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));

try {
  plugin.apply(ctx, { baseUrl: 'http://127.0.0.1:' + server.address().port, stateDir });
  assert.ok(registeredEntry, 'Wanxiang model entry was not registered');

  const schema = await registeredEntry.schema();
  assert.equal(schema.extra.prompt_extend.type, 'boolean');
  assert.equal(schema.extra.negative_prompt.type, 'string');

  async function submit(shotId, spec, key) {
    const handler = routes.get('/api/dv/wanxiang/submit');
    const response = await handler(new Request('http://localhost/', {
      method: 'POST',
      body: JSON.stringify({ project: 'project-1', shot_id: shotId, key, ...spec }),
    }));
    return [response.status, await response.json()];
  }

  for (const [name, item] of Object.entries(expected)) {
    const [status, payload] = await submit(name, item.spec, item.provider_key);
    assert.equal(status, 200, name + ': ' + JSON.stringify(payload));
    assert.equal(payload.status, 'submitted', name);
    const receipt = JSON.parse(await readFile(stateDir + '/' + item.provider_key + '.json', 'utf8'));
    assert.equal(receipt.spec_hash, item.legacy_hash, name + ' spec_hash mismatch');

    const validationErrors = await registeredEntry.validateGenerationRequest({
      prompt: item.spec.prompt,
      references: [],
      firstFrame: null,
      lastFrame: null,
      durationSec: item.spec.seconds,
      aspectRatio: item.spec.aspect_ratio,
      resolution: item.spec.resolution,
      seed: Number.parseInt(item.provider_key.slice(0, 7), 16),
      extra: {
        bridge_confirmation: item.provider_key,
        prompt_extend: item.spec.prompt_extend,
        negative_prompt: item.spec.negative_prompt,
      },
    });
    assert.deepEqual(validationErrors, [], name + ' validation failed');
  }

  // Verify exact DashScope payloads for each case.
  assert.equal(calls.length, 4);

  // 1. default_controls: prompt_extend=true, shot_type='single', default negative_prompt
  assert.equal(calls[0].body.parameters.prompt_extend, true);
  assert.equal(calls[0].body.parameters.shot_type, 'single');
  assert.equal(calls[0].body.input.negative_prompt, '品牌标识、logo、商标、水印、文字');

  // 2. no_extend: prompt_extend=false, shot_type omitted, default negative_prompt kept
  assert.equal(calls[1].body.parameters.prompt_extend, false);
  assert.equal('shot_type' in calls[1].body.parameters, false);
  assert.equal(calls[1].body.input.negative_prompt, '品牌标识、logo、商标、水印、文字');

  // 3. custom_negative: custom negative_prompt forwarded in input.negative_prompt
  assert.equal(calls[2].body.parameters.prompt_extend, false);
  assert.equal(calls[2].body.input.negative_prompt, '人物、品牌标识、水印');

  // 4. clear_negative: empty string omits input.negative_prompt
  assert.equal(calls[3].body.parameters.prompt_extend, true);
  assert.equal('negative_prompt' in calls[3].body.input, false);

  // Invalid types / oversized negative_prompt must be rejected with HTTP 400 and make zero upstream calls.
  const base = expected.default_controls;
  const [badTypeStatus] = await submit('bad_bool', { ...base.spec, prompt_extend: 'false' }, base.provider_key);
  assert.equal(badTypeStatus, 400);
  const [badLenStatus] = await submit('bad_len', { ...base.spec, negative_prompt: '字'.repeat(501) }, base.provider_key);
  assert.equal(badLenStatus, 400);
  assert.equal(calls.length, 4);

  // Unknown extra key rejected in validateGenerationRequest.
  const extraErrors = await registeredEntry.validateGenerationRequest({
    prompt: base.spec.prompt,
    references: [],
    firstFrame: null,
    lastFrame: null,
    durationSec: base.spec.seconds,
    aspectRatio: base.spec.aspect_ratio,
    resolution: base.spec.resolution,
    seed: Number.parseInt(base.provider_key.slice(0, 7), 16),
    extra: { bridge_confirmation: base.provider_key, unknown_param: 1 },
  });
  assert.ok(extraErrors.length > 0);
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
""",
        encoding="utf-8",
    )

    expected_path = tmp_path / "expected.json"
    expected_path.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [node, str(script), (WAN_PROVIDER / "index.ts").as_uri(), str(tmp_path / "receipts"), str(expected_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
