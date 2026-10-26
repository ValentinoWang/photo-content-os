"""Deterministic R276 backend tests; paid models are never called."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import wave
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import llm_common
from direct_video.generate import DirectVideoError, Generator, allocate_timing, parse_shots, validate_code, validate_design
from direct_video.lint import lint
from direct_video.media import wav_seconds
from studio.direct_video import projection


def html(d=1, label='示意图'):
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#ffffff}}
</style></head><body><header data-role="header">标题</header><div>{label}</div>
<script>const D = {d}; window.seekFrame = (frame,fps) => {{ document.body.dataset.frame=frame; }};</script></body></html>'''


def design(rows):
    return {'palette': {'background': '#ffffff', 'primary': '#111111', 'accent': '#ef5825', 'neutral': '#777777'},
            'typeScale': [132, 72, 44], 'motionRules': '跟随口播逐步呈现', 'banned': ['霓虹', '毛玻璃', '胶囊'],
            'motionSummary': '逐步呈现，动完就停', 'bannedShort': ['霓虹', '毛玻璃', '胶囊'],
            'perShot': [{'shotId': row['shotId'], 'mainAction': '画出因果', 'takeaway': '逐步看懂'} for row in rows]}


class FakeModel:
    def __init__(self, *, bad=0, delay=0):
        self.calls = []
        self.bad = bad
        self.delay = delay
        self.running = self.maximum = 0
        self.lock = threading.Lock()

    def __call__(self, **kwargs):
        context = json.loads(kwargs['user_prompt'])
        with self.lock:
            self.calls.append(copy.deepcopy(context))
        assert kwargs['provider'] == 'claude_cli'
        assert kwargs['model'] == 'claude-opus-5-5'
        if 'shots' in context:
            return json.dumps(design(context['shots']))
        with self.lock:
            self.running += 1
            self.maximum = max(self.maximum, self.running)
        time.sleep(self.delay)
        with self.lock:
            self.running -= 1
            broken = self.bad > 0
            self.bad -= int(broken)
        code = html(context['D'], context.get('instruction') or '示意图')
        if broken:
            code = code.replace('document.body.dataset.frame=frame;', 'setTimeout(()=>{},1);')
        return json.dumps({'code': code})


class FakeMedia:
    def __init__(self):
        self.rendered = []
        self.composed = []
        self.transcript = None

    def render(self, root, shot):
        self.rendered.append(shot['shotId'])
        path = root / 'posters' / (shot['shotId'] + '.jpg')
        path.parent.mkdir(exist_ok=True)
        path.write_bytes((root / 'shots' / (shot['shotId'] + '.html')).read_bytes())

    def transcribe(self, path):
        return self.transcript

    def compose(self, root, job):
        self.composed.append(copy.deepcopy(job))
        (root / 'output.mp4').write_bytes(b'synthetic-video')
        return {'frames': 60, 'durationSeconds': 2, 'checks': {'playable': 'pass', 'frameCount': 'pass', 'blackFrames': 'pass', 'avOffsetSeconds': 0 if job['narration']['status'] == 'ready' else None}}


def ready(tmp_path, *, model=None, media=None, script='第一句。\n第二句。'):
    model, media = model or FakeModel(), media or FakeMedia()
    gen = Generator(tmp_path, model_call=model, media=media)
    job = gen.create('project1', {'script': script, 'style': '浅底图解'}, background=False)
    gen.generate('project1', job['jobId'])
    return gen, gen.read('project1', job['jobId']), model, media


def wait(gen, job):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with gen.lock:
            if ('project1', job['jobId']) not in gen.active:
                return gen.read('project1', job['jobId'])
        time.sleep(.01)
    pytest.fail('Background job did not finish')


def wav(duration=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * round(duration * 8000))
    return output.getvalue()


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    path = tmp_path / 'claude'
    path.write_text('''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
prompt=sys.stdin.read()
record={"args":sys.argv[1:],"prompt":prompt,"cwd":str(Path.cwd()),"files":list(p.name for p in Path.cwd().iterdir()),"config":os.environ.get("CLAUDE_CONFIG_DIR"),"nested":os.environ.get("CLAUDECODE")}
Path(os.environ["FAKE_RECORD"]).write_text(json.dumps(record))
mode=os.environ.get("FAKE_MODE", "ok")
if mode=="timeout":time.sleep(4)
if mode=="exit":
 print(prompt, file=sys.stderr)
 sys.exit(7)
if mode=="empty":print(json.dumps({"result":" "}));sys.exit(0)
if mode=="error":print(json.dumps({"result":prompt,"is_error":True}));sys.exit(0)
if mode=="invalid":print("not json");sys.exit(0)
if mode=="queue":
 queue=Path(os.environ["FAKE_QUEUE"])
 values=json.loads(queue.read_text())
 value=values.pop(0)
 queue.write_text(json.dumps(values))
 print(json.dumps({"result":json.dumps(value),"is_error":False}))
 sys.exit(0)
print(json.dumps({"result":"ok","is_error":False}))
''')
    path.chmod(0o755)
    record = tmp_path / 'record.json'
    monkeypatch.setenv('OPENCLAW_CLAUDE_BIN', str(path))
    monkeypatch.setenv('FAKE_RECORD', str(record))
    return path, record


@pytest.mark.parametrize('provider', ['claude_cli', 'claude', 'claude-cli'])
def test_fake_cli_isolated(provider, fake_claude, monkeypatch, tmp_path):
    _, record = fake_claude
    monkeypatch.setenv('CLAUDECODE', '1')
    monkeypatch.setenv('OPENCLAW_CLAUDE_CONFIG_DIR', str(tmp_path / 'account'))
    assert llm_common.generate_text(provider=provider, system_prompt='secret-system', user_prompt='secret-user') == 'ok'
    data = json.loads(record.read_text())
    assert 'secret-system' in data['prompt'] and 'secret-user' in data['prompt']
    assert 'secret-system' not in ' '.join(data['args'])
    assert 'secret-user' not in ' '.join(data['args'])
    assert data['files'] == []
    assert not Path(data['cwd']).exists()
    assert data['config'] == str(tmp_path / 'account') and data['nested'] is None
    args = data['args']
    for flag in ['-p', '--safe-mode', '--strict-mcp-config', '--no-session-persistence']:
        assert flag in args
    assert args[args.index('--tools') + 1] == ''
    assert args[args.index('--setting-sources') + 1] == ''
    assert args[args.index('--model') + 1] == 'claude-opus-5-5'
    assert json.loads(args[args.index('--mcp-config') + 1]) == {'mcpServers': {}}


@pytest.mark.parametrize('mode', ['timeout', 'exit', 'empty', 'error', 'invalid'])
def test_fake_cli_errors_do_not_leak(mode, fake_claude, monkeypatch):
    monkeypatch.setenv('FAKE_MODE', mode)
    monkeypatch.setenv('OPENCLAW_CLAUDE_TIMEOUT_SEC', '1')
    with pytest.raises(llm_common.LLMError) as error:
        llm_common.generate_text(provider='claude', system_prompt='never-leak', user_prompt='private-prompt')
    assert 'never-leak' not in str(error.value) and 'private-prompt' not in str(error.value)


@pytest.mark.parametrize('timeout', ['0', '-1', 'bad'])
def test_cli_invalid_timeout(fake_claude, monkeypatch, timeout):
    monkeypatch.setenv('OPENCLAW_CLAUDE_TIMEOUT_SEC', timeout)
    with pytest.raises(llm_common.LLMError):
        llm_common.generate_text(provider='claude', system_prompt='', user_prompt='')


def test_cli_missing_and_image_rejected(monkeypatch, fake_claude):
    with pytest.raises(llm_common.LLMError):
        llm_common.generate_text(provider='claude', system_prompt='', user_prompt='', image_paths=[Path('image.png')])
    monkeypatch.setenv('OPENCLAW_CLAUDE_BIN', 'r276-nonexistent-binary')
    with pytest.raises(llm_common.LLMError):
        llm_common.generate_text(provider='claude', system_prompt='', user_prompt='')


def test_lint_errors_and_warning():
    result = lint(html(10, '这是真的吗?1000'), '一句话。', 1)
    assert {'animation_cut_short', 'half_width_punctuation'} <= {e['code'] for e in result['errors']}
    assert result['warnings'][0]['code'] == 'number_unspoken'
    assert lint(html(), '示意图', 1) == {'errors': [], 'warnings': []}
    assert not lint(html().replace('示意图', '<svg xmlns="http://www.w3.org/2000/svg"></svg>'), '', 1)['errors']
    assert lint(html().replace('示意图', '问？'), '', 1)['errors']
    assert not lint(html().replace('示意图', '问<span class="fw">？</span>'), '', 1)['errors']
    assert lint(html().replace('const D = 1;', 'const D = 0;'), '', 1)['errors']


@pytest.mark.parametrize('change', [lambda d: d.update(palette={}), lambda d: d.update(typeScale=[1, 2, 3]), lambda d: d.update(banned=[]), lambda d: d['perShot'][0].update(shotId='other')])
def test_design_json_invalid(change):
    rows = [{'shotId': '01', 'dialogue': '话'}]
    value = design(rows)
    change(value)
    with pytest.raises(DirectVideoError):
        validate_design(value, rows)


@pytest.mark.parametrize('value', [{}, {'code': 'no html'}, {'code': 'x'*100000}, [], {'code': '<!doctype html>'}])
def test_code_json_invalid(value):
    with pytest.raises(DirectVideoError):
        validate_code(value)


@pytest.mark.parametrize('body', [{'script': ''}, {'script': '话', 'model': 'other'}, {'storyboard': {'shots': [{'shotId': '../x', 'dialogue': '话'}]}}, {'script': '话', 'storyboard': {}}, {'script': 10}])
def test_input_invalid(body):
    with pytest.raises(DirectVideoError):
        parse_shots(body)


def test_automatic_retry_once_and_immediate_render(tmp_path):
    gen, job, model, media = ready(tmp_path, model=FakeModel(bad=1), script='一句话。')
    assert job['status'] == 'ready'
    assert job['shots'][0]['attempts'] == 2
    assert model.calls[2]['errors'][0]['code'] == 'forbidden_runtime'
    assert media.rendered == ['01']
    gen, job, model, media = ready(tmp_path / 'failed', model=FakeModel(bad=10), script='一句话。')
    assert job['status'] == 'failed' and job['shots'][0]['attempts'] == 2
    assert job['shots'][0]['failureCode'] == 'lint_failed_after_retry'
    assert media.rendered == []


def test_parallel_limit_and_pipeline(tmp_path):
    model = FakeModel(delay=.03)
    media = FakeMedia()
    original = media.render
    def render(root, shot):
        # The renderer runs within the writing task, before every other shot
        # has necessarily been written.
        if not media.rendered:
            assert len(model.calls) < 9
        original(root, shot)
    media.render = render
    gen, job, _, _ = ready(tmp_path, model=model, media=media, script='\n'.join(['一句话。']*8))
    assert job['status'] == 'ready' and model.maximum == 3
    assert len(media.rendered) == 8
    with pytest.raises(ValueError):
        Generator(tmp_path / 'invalid', workers=4)


def test_rewrite_only_one_shot_and_invalidate_output(tmp_path):
    gen, job, model, media = ready(tmp_path)
    root = gen.path('project1', job['jobId'])
    untouched = copy.deepcopy(job['shots'][1])
    code = (root / 'shots/02.html').read_bytes()
    poster = (root / 'posters/02.jpg').read_bytes()
    mtimes = [(root / p).stat().st_mtime_ns for p in ['shots/02.html', 'posters/02.jpg']]
    gen._compose('project1', job['jobId'])
    assert gen.read('project1', job['jobId'])['status'] == 'done'
    gen.rewrite('project1', job['jobId'], '01', '放大主图')
    after = wait(gen, job)
    assert after['shots'][1] == untouched
    assert after['shots'][0]['writtenAt'] != job['shots'][0]['writtenAt']
    assert after['shots'][0]['posterRevision'] == 2
    assert after['output']['status'] == 'none'
    assert media.rendered == ['01', '02', '01'] or media.rendered == ['02', '01', '01']
    assert (root / 'shots/02.html').read_bytes() == code
    assert (root / 'posters/02.jpg').read_bytes() == poster
    assert [(root / p).stat().st_mtime_ns for p in ['shots/02.html', 'posters/02.jpg']] == mtimes


def test_timing_exact_and_proportional():
    shots = [{'dialogue': '甲。'}, {'dialogue': '乙。'}]
    transcript = {'segments': [{'words': [{'text': '甲', 'start': .1, 'end': .5}, {'text': '乙', 'start': .8, 'end': 1.5}]}]}
    values, source = allocate_timing(shots, 2, transcript)
    assert source == 'narration' and values == [.8, 1.2]
    for invalid in [None, {}, {'words': [{'text': '错', 'start': 0, 'end': 1}]}, {'words': [{'text': '甲乙', 'start': 0, 'end': 1}]}]:
        values, source = allocate_timing(shots, 2, invalid)
        assert source == 'proportional' and values == [1, 1]


def test_narration_fallback_retimes_and_rewrites_shorter(tmp_path):
    gen, job, model, media = ready(tmp_path, script='第一句话稍微长一点。\n第二句话稍微长一点。')
    payload = wav(1)
    gen.narration('project1', job['jobId'], io.BytesIO(payload), len(payload))
    after = wait(gen, job)
    assert after['status'] == 'ready' and after['narration']['status'] == 'ready'
    assert all(s['timingSource'] == 'proportional' and s['measuredSeconds'] == .5 for s in after['shots'])
    assert all(s['attempts'] == 2 for s in after['shots'])
    assert sum(s['measuredSeconds'] for s in after['shots']) == 1
    gen.request_compose('project1', job['jobId'])
    result = wait(gen, job)
    assert result['output']['kind'] == 'narrated' and result['output']['status'] == 'ready'


def test_narration_invalid_decode_and_limits(tmp_path):
    gen, job, _, _ = ready(tmp_path)
    for payload, length in [(b'bad', 3), (wav(), 104857601), (b'', 0), (wav()[:45], 45)]:
        with pytest.raises(DirectVideoError):
            gen.narration('project1', job['jobId'], io.BytesIO(payload), length)
    path = tmp_path / 'valid.wav'
    path.write_bytes(wav())
    assert wav_seconds(path) == 1


def test_recover_and_retry_interrupted(tmp_path):
    gen, job, _, media = ready(tmp_path)
    root = gen.path('project1', job['jobId'])
    job['status'] = 'writing'
    job['shots'][0]['status'] = 'writing'
    gen.save(root, job)
    recovered = Generator(tmp_path, model_call=FakeModel(), media=media)
    result = recovered.read('project1', job['jobId'])
    assert result['status'] == 'failed'
    assert result['shots'][0]['status'] == 'interrupted'
    assert result['shots'][1] == job['shots'][1]
    recovered.rewrite('project1', job['jobId'], '01', '重试这一镜')
    assert wait(recovered, job)['status'] == 'ready'


def test_busy_job_and_projection(tmp_path):
    gen, job, _, _ = ready(tmp_path)
    gen.active.add(('project1', job['jobId']))
    with pytest.raises(DirectVideoError, match='job_busy'):
        gen.rewrite('project1', job['jobId'], '01', '修改')
    job['privatePath'] = str(tmp_path)
    job['shots'][0]['checks']['warnings'].append({'code': 'note', 'message': str(tmp_path / 'secret/file'), 'privatePath': str(tmp_path)})
    result = projection(job)
    assert str(tmp_path) not in json.dumps(result)
    assert set(result['shots'][0]) == {'shotId', 'dialogue', 'mainAction', 'estimatedSeconds', 'measuredSeconds', 'timingSource', 'status', 'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt', 'renderedAt', 'codeChars', 'posterRevision', 'checks',
                                      # R277 adds per-shot versions, boxes, look and sample.
                                      'currentVersion', 'versions', 'boxes', 'look', 'sample',
                                      'visual', 'subtitle', 'camera', 'audio', 'fromDraft'}


def test_default_gateway_with_fake_executable_generates_job(tmp_path, monkeypatch, fake_claude):
    queue = tmp_path / 'responses.json'
    rows = [{'shotId': '01', 'dialogue': '一句话。'}]
    queue.write_text(json.dumps([design(rows), {'code': html(.8)}]))
    monkeypatch.setenv('FAKE_MODE', 'queue')
    monkeypatch.setenv('FAKE_QUEUE', str(queue))
    gen = Generator(tmp_path / 'state', workers=1, media=FakeMedia())
    job = gen.create('project1', {'storyboard': {'shots': rows}, 'style': '浅底图解'}, background=False)
    gen.generate('project1', job['jobId'])
    assert gen.read('project1', job['jobId'])['status'] == 'ready'
    assert json.loads(queue.read_text()) == []


def test_warning_only_is_recorded_without_retry(tmp_path):
    class WarningModel(FakeModel):
        def __call__(self, **kwargs):
            result = json.loads(super().__call__(**kwargs))
            if 'code' in result:
                result['code'] = result['code'].replace('示意图', '1000')
            return json.dumps(result)
    gen, job, model, _ = ready(tmp_path, model=WarningModel(), script='一句话。')
    assert job['status'] == 'ready'
    assert job['shots'][0]['attempts'] == 1
    assert job['shots'][0]['checks']['warnings'][0]['code'] == 'number_unspoken'


def test_recover_reclaims_only_dead_worker_locks(tmp_path):
    gen, job, _, _ = ready(tmp_path)
    root = gen.path('project1', job['jobId'])
    lock = root / 'cache/01/.render.lock'
    lock.parent.mkdir(parents=True)
    lock.write_text('')
    job.update(status='rendering', _workerPid=2147483647)
    job['shots'][0]['status'] = 'rendering'
    gen.save(root, job)
    recovered = Generator(tmp_path, model_call=FakeModel(), media=FakeMedia())
    assert not lock.exists()
    assert recovered.read('project1', job['jobId'])['shots'][0]['status'] == 'interrupted'
    job['_workerPid'] = os.getpid()
    gen.save(root, job)
    lock.write_text('')
    recovered = Generator(tmp_path, model_call=FakeModel(), media=FakeMedia())
    assert lock.exists()
    assert recovered.read('project1', job['jobId'])['shots'][0]['status'] == 'rendering'
    with pytest.raises(DirectVideoError, match='job_busy'):
        recovered.rewrite('project1', job['jobId'], '01', '重试')


def test_failed_design_and_model_timeout_are_bounded(tmp_path):
    gen = Generator(tmp_path, model_call=lambda **kwargs: '{}', media=FakeMedia())
    job = gen.create('project1', {'script': '一句话。', 'style': '浅底图解'})
    result = wait(gen, job)
    assert result['status'] == 'failed' and result['failureCode'] == 'design_invalid'
    assert result['design']['status'] == 'failed'
    def timeout(**kwargs):
        if 'shots' in json.loads(kwargs['user_prompt']):
            return json.dumps(design([{'shotId': '01'}]))
        raise llm_common.LLMError('claude CLI generation timed out after 300s')
    gen = Generator(tmp_path / 'timeout', model_call=timeout, media=FakeMedia())
    job = gen.create('project1', {'script': '一句话。', 'style': '浅底图解'})
    result = wait(gen, job)
    assert result['status'] == 'failed' and result['shots'][0]['failureCode'] == 'model_timeout'
    assert result['shots'][0]['attempts'] == 1


def test_metrics_record_calls_lint_render_and_compose_without_prompts(tmp_path):
    gen, job, _, _ = ready(tmp_path, script='一句话。')
    gen._compose('project1', job['jobId'])
    root = gen.path('project1', job['jobId'])
    events = json.loads((root / 'metrics.json').read_text())
    assert [e['phase'] for e in events] == ['design', 'write', 'lint', 'render', 'compose']
    assert all(e['elapsedSeconds'] >= 0 for e in events if 'elapsedSeconds' in e)
    assert all('prompt' not in e and 'dialogue' not in e and 'code' not in e for e in events)
    result = projection(gen.read('project1', job['jobId']))
    assert 'metrics' not in result
    assert 'subtitleBurnedIn' not in result['output']
    assert 'subtitles' not in result['output']
    assert '字幕已烧录' not in json.dumps(result, ensure_ascii=False)


@pytest.mark.parametrize('boxed', ["<span class='fw'>？</span>", '<span data-note="q" class="question fw"><b>？</b></span>'])
def test_lint_accepts_equivalent_full_width_spans(boxed):
    assert not lint(html(label=boxed), '问题？', 1)['errors']


def test_lint_svg_namespace_is_not_a_network_request():
    code = html().replace('const D = 1;', "const D = 1; const ns='http://www.w3.org/2000/svg'; document.createElementNS(ns,'circle');")
    assert not lint(code, '', 1)['errors']
    for content in ['<img src="http://www.w3.org/2000/svg">', '<a href="http://www.w3.org/2000/svg">x</a>', '<img src="https://example.test/a.jpg">', '<script>fetch("http://www.w3.org/2000/svg")</script>']:
        assert lint(html(label=content), '', 1)['errors']
    assert lint(html(label='问？'), '', 1)['errors']


@pytest.mark.parametrize('width,alignment,allowed', [('1em', 'center', True), ('.5em', 'center', False), ('1em', 'left', False)])
def test_lint_checks_equivalent_punctuation_box_geometry(width, alignment, allowed):
    code = html(label="<span class='pb'>？</span>").replace('</style>', f'.pb{{display:inline-block;width:{width};text-align:{alignment}}}</style>')
    errors = lint(code, '问题？', 1)['errors']
    assert ('punctuation_unboxed' not in {e['code'] for e in errors}) == allowed


def test_failed_composition_keeps_measured_checks_and_narrated_kind(tmp_path):
    from direct_video.media import OutputCheckError
    class FailedMedia(FakeMedia):
        def compose(self, root, job):
            raise OutputCheckError({'playable': 'pass', 'frameCount': 'pass', 'avOffsetSeconds': 0, 'blackFrames': 'fail'})
    gen, job, _, _ = ready(tmp_path, media=FailedMedia())
    job['narration']['status'] = 'ready'
    gen.save(gen.path('project1', job['jobId']), job)
    gen._compose('project1', job['jobId'])
    failed = gen.read('project1', job['jobId'])
    assert failed['failureCode'] == 'output_check_failed'
    assert failed['output']['kind'] == 'narrated'
    assert failed['output']['checks']['blackFrames'] == 'fail'
    assert failed['output']['checks']['playable'] == 'pass'
    assert projection(failed)['output']['checks']['blackFrames'] == 'fail'
