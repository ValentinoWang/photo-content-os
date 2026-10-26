"""R276 C backend contract changes; models and media are isolated test doubles."""
from __future__ import annotations

import copy
from datetime import datetime
import io
import json
from pathlib import Path
import time

import pytest

from test_r276_direct_video import FakeMedia, FakeModel, ready, wait, wav
from test_r276_direct_api import api, create
from direct_video.generate import DirectVideoError, Generator
from studio.direct_video import projection


@pytest.mark.parametrize('bad,expected_status', [(1, 'rendered'), (2, 'failed')])
def test_writing_clock_updates_on_each_model_attempt_and_survives_restart(tmp_path, bad, expected_status):
    observed = []
    class ObservingModel(FakeModel):
        def __call__(self, **kwargs):
            user = json.loads(kwargs['user_prompt'])
            if 'D' in user:
                shot = gen.read('project1', job['jobId'])['shots'][0]
                observed.append(shot['writingStartedAt'])
                datetime.fromisoformat(observed[-1].replace('Z', '+00:00'))
                time.sleep(.002)
            return super().__call__(**kwargs)
    gen = Generator(tmp_path, model_call=ObservingModel(bad=bad), media=FakeMedia())
    job = gen.create('project1', {'script': '一句话。', 'style': '浅底图解'}, background=False)
    assert job['shots'][0]['writingStartedAt'] is None
    gen.generate('project1', job['jobId'])
    current = gen.read('project1', job['jobId'])
    assert len(observed) == 2 and observed[1] > observed[0]
    assert current['shots'][0]['status'] == expected_status
    assert current['shots'][0]['writingStartedAt'] == observed[-1]
    assert Generator(tmp_path, model_call=FakeModel(), media=FakeMedia()).read('project1', job['jobId'])['shots'][0]['writingStartedAt'] == observed[-1]


def test_requested_and_narration_rewrites_refresh_writing_clock(tmp_path):
    gen, job, _, _ = ready(tmp_path, script='这是一句稍长的口播。')
    first = job['shots'][0]['writingStartedAt']
    gen.rewrite('project1', job['jobId'], '01', '放大数字')
    requested = wait(gen, job)
    second = requested['shots'][0]['writingStartedAt']
    assert second > first
    audio = wav(.3)
    gen.narration('project1', job['jobId'], io.BytesIO(audio), len(audio))
    narrated = wait(gen, job)
    assert narrated['shots'][0]['writingStartedAt'] > second
    assert narrated['shots'][0]['status'] == 'rendered'


def test_legacy_projection_has_unknown_clock_without_inventing_history(tmp_path):
    _, job, _, _ = ready(tmp_path)
    del job['shots'][0]['writingStartedAt']
    assert projection(job)['shots'][0]['writingStartedAt'] is None


@pytest.mark.parametrize('status', ['failed', 'interrupted'])
@pytest.mark.parametrize('opinion', [None, '', ' \t '])
def test_retry_without_opinion_preserves_intent_errors_and_other_shot(tmp_path, status, opinion):
    gen, job, model, media = ready(tmp_path)
    root = gen.path('project1', job['jobId'])
    untouched = copy.deepcopy(job['shots'][1])
    code = (root / 'shots/02.html').read_bytes()
    poster = (root / 'posters/02.jpg').read_bytes()
    target = job['shots'][0]
    old_clock = target['writingStartedAt']
    target.update(status=status, failureCode='lint_failed_after_retry', lastInstruction='放大数字')
    target['checks']['errors'] = [{'code': 'header_missing', 'message': '页眉缺少标记。'}]
    gen.save(root, job)
    calls_before = len(model.calls)
    gen.rewrite('project1', job['jobId'], '01', opinion)
    after = wait(gen, job)
    assert after['status'] == 'ready'
    assert len(model.calls) == calls_before + 1
    assert model.calls[-1]['errors'] == [{'code': 'header_missing', 'message': '页眉缺少标记。'}]
    assert model.calls[-1]['instruction'] == '放大数字'
    assert model.calls[-1]['previousCode'].startswith('<!doctype html>')
    assert after['shots'][0]['lastInstruction'] == '放大数字'
    assert after['shots'][0]['writingStartedAt'] > old_clock
    assert after['shots'][1] == untouched
    assert (root / 'shots/02.html').read_bytes() == code
    assert (root / 'posters/02.jpg').read_bytes() == poster


@pytest.mark.parametrize('status', ['queued', 'writing', 'written', 'rendering', 'rendered'])
@pytest.mark.parametrize('opinion', [None, '', ' \n '])
def test_empty_opinion_rejected_in_other_states(tmp_path, status, opinion):
    gen, job, model, _ = ready(tmp_path)
    job['shots'][0]['status'] = status
    gen.save(gen.path('project1', job['jobId']), job)
    call_count = len(model.calls)
    with pytest.raises(DirectVideoError, match='instruction_invalid'):
        gen.rewrite('project1', job['jobId'], '01', opinion)
    assert len(model.calls) == call_count
    assert gen.read('project1', job['jobId']) == job


@pytest.mark.parametrize('opinion', [123, True, [], {}, '字'*201, ' '*201])
def test_retry_still_rejects_invalid_type_or_over_limit(tmp_path, opinion):
    gen, job, _, _ = ready(tmp_path)
    job['shots'][0]['status'] = 'failed'
    gen.save(gen.path('project1', job['jobId']), job)
    with pytest.raises(DirectVideoError, match='instruction_invalid'):
        gen.rewrite('project1', job['jobId'], '01', opinion)


@pytest.mark.parametrize('status', ['failed', 'interrupted'])
@pytest.mark.parametrize('body', [{}, {'instruction': ''}, {'instruction': None}, None])
def test_http_retry_without_instruction(api, status, body):
    request, csrf, pid, app, _ = api
    path, job = create(api)
    gen = app.direct_video.generator
    # Wait for owner cleanup before changing the synthetic failed/interrupted state.
    deadline = time.monotonic() + 5
    while gen.active and time.monotonic() < deadline:
        time.sleep(.01)
    current = gen.read(pid, job['jobId'])
    current['shots'][0].update(status=status, failureCode='process_interrupted')
    current['shots'][0]['checks']['errors'] = [{'code': 'code_invalid', 'message': '请补齐镜头代码。'}]
    gen.save(gen.path(pid, job['jobId']), current)
    response, _, accepted = request(path+'/shots/01/rewrite', 'POST', body, csrf)
    assert response == 200
    assert accepted['job']['shots'][0]['writingStartedAt']
    deadline = time.monotonic() + 5
    while gen.active and time.monotonic() < deadline:
        time.sleep(.01)
    done = request(path)[2]['job']
    assert done['status'] == 'ready'
    assert done['shots'][0]['writingStartedAt']
    assert app.direct_video.generator.model_call.calls[-1]['errors'][0]['code'] == 'code_invalid'


def test_openapi_declares_clock_and_state_dependent_optional_instruction():
    from studio.api_contract import build_openapi
    schema = build_openapi()
    shot = schema['components']['schemas']['DirectJob']['properties']['shots']['items']
    assert 'writingStartedAt' in shot['required']
    assert shot['properties']['writingStartedAt']['format'] == 'date-time'
    operation = schema['paths']['/api/projects/{projectId}/direct/jobs/{jobId}/shots/{shotId}/rewrite']['post']
    assert operation['requestBody']['required'] is False
    body = operation['requestBody']['content']['application/json']['schema']
    assert 'instruction' not in body.get('required', [])
    assert body['properties']['instruction']['maxLength'] == 200
    assert 'failed' in operation['description'] and 'interrupted' in operation['description']


def poster_fixture(path, *, bottom=900, background=(20, 24, 27), width=360, height=640):
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 15, width-24, 45), fill='#eeeeee')  # header, outside content bounds
    draw.rectangle((45, 100, width-45, round(bottom * height / 1920)-1), fill='#46b6aa')
    image.save(path)
    return image


@pytest.mark.parametrize('background', [(20, 24, 27), (244, 240, 232), (40, 76, 104)])
@pytest.mark.parametrize('bottom,warning', [(900, True), (1107, True), (1110, False), (1350, False), (1650, False)])
def test_layout_samples_background_and_obeys_strict_thirty_percent(tmp_path, background, bottom, warning):
    from direct_video.layout import inspect_layout
    path = tmp_path/'poster.png'
    poster_fixture(path, bottom=bottom, background=background)
    result = inspect_layout(path)
    assert result['status'] == 'measured'
    assert result['backgroundRgb'] == list(background)
    assert bool(result['warnings']) is warning
    if warning:
        assert result['warnings'][0]['code'] == 'layout_bottom_gap'
        assert result['warnings'][0]['message'].startswith('画面下半截空着：主画面只占到 y=')
    else:
        assert result['warnings'] == []


def test_layout_ignores_isolated_noise_and_header(tmp_path):
    from direct_video.layout import inspect_layout
    from PIL import ImageDraw
    path = tmp_path/'poster.jpg'
    image = poster_fixture(tmp_path/'source.png', bottom=900)
    ImageDraw.Draw(image).point((180, 490), fill='white')
    image.save(path, quality=90)
    result = inspect_layout(path)
    assert result['status'] == 'measured'
    assert abs(result['contentBottom'] - 900) <= 3
    assert result['warnings'][0]['code'] == 'layout_bottom_gap'


def test_layout_unreadable_or_unstable_background_is_unknown_not_pass(tmp_path):
    from direct_video.layout import inspect_layout
    from PIL import Image
    missing = inspect_layout(tmp_path/'missing.jpg')
    assert missing['status'] == 'unmeasurable' and missing['reason'] == 'image_unreadable'
    image = Image.new('RGB', (360, 640))
    image.putdata([((255, 255, 255) if (x//10+y//10)%2 else (0, 0, 0)) for y in range(640) for x in range(360)])
    path = tmp_path/'variable.png'
    image.save(path)
    assert inspect_layout(path)['status'] == 'unmeasurable'


def test_layout_warning_never_rewrites_and_refreshes_after_rerender(tmp_path):
    class LayoutMedia(FakeMedia):
        layout = {'status': 'measured', 'contentBottom': 900, 'warnings': [
            {'code': 'layout_bottom_gap', 'message': '画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%'}]}
        def render(self, root, shot):
            super().render(root, shot)
            return copy.deepcopy(self.layout)
    media = LayoutMedia()
    gen, job, model, _ = ready(tmp_path, media=media, script='一句话。')
    assert job['status'] == 'ready' and job['shots'][0]['attempts'] == 1
    assert len(model.calls) == 2  # design + the one initial model write
    assert job['shots'][0]['checks']['errors'] == []
    assert job['shots'][0]['checks']['warnings'][0]['code'] == 'layout_bottom_gap'
    root = gen.path('project1', job['jobId'])
    assert json.loads((root/'checks/01.json').read_text())['warnings'][0]['code'] == 'layout_bottom_gap'
    assert json.loads((root/'checks/layout/01.json').read_text())['contentBottom'] == 900
    original_clock = job['shots'][0]['writingStartedAt']
    media.layout = {'status': 'measured', 'contentBottom': 1450, 'warnings': []}
    audio = wav(2)
    gen.narration('project1', job['jobId'], io.BytesIO(audio), len(audio))
    final = wait(gen, job)
    assert final['status'] == 'ready'
    assert final['shots'][0]['checks']['warnings'] == []
    assert final['shots'][0]['writingStartedAt'] == original_clock
    assert len(model.calls) == 2


def test_restart_preserves_last_start_then_empty_retry_refreshes_it(tmp_path):
    gen, job, _, _ = ready(tmp_path, script='一句话。')
    clock = job['shots'][0]['writingStartedAt']
    job['status'] = 'writing'
    job['shots'][0]['status'] = 'writing'
    gen.save(gen.path('project1', job['jobId']), job)
    restarted = Generator(tmp_path, model_call=FakeModel(), media=FakeMedia())
    restored = restarted.read('project1', job['jobId'])
    assert restored['shots'][0]['status'] == 'interrupted'
    assert restored['shots'][0]['writingStartedAt'] == clock
    restarted.rewrite('project1', job['jobId'], '01')
    retried = wait(restarted, job)
    assert retried['shots'][0]['writingStartedAt'] > clock


def test_failed_first_draft_can_retry_without_an_existing_code_file(tmp_path):
    model = FakeModel(bad=2)
    gen, job, _, _ = ready(tmp_path, model=model, script='一句话。')
    assert job['shots'][0]['status'] == 'failed'
    original_errors = copy.deepcopy(job['shots'][0]['checks']['errors'])
    assert not (gen.path('project1', job['jobId'])/'shots/01.html').exists()
    gen.rewrite('project1', job['jobId'], '01')
    result = wait(gen, job)
    assert result['status'] == 'ready'
    assert model.calls[-1]['instruction'] is None
    assert model.calls[-1]['errors'] == original_errors
    assert result['shots'][0]['attempts'] == 3


@pytest.mark.parametrize('opinion', ['字', '字'*200])
def test_normal_rewrite_still_accepts_boundary_lengths(tmp_path, opinion):
    gen, job, _, _ = ready(tmp_path, script='一句话。')
    gen.rewrite('project1', job['jobId'], '01', opinion)
    assert wait(gen, job)['status'] == 'ready'


def test_unknown_layout_does_not_erase_last_measured_warning(tmp_path):
    gen, job, model, _ = ready(tmp_path, script='一句话。')
    root = gen.path('project1', job['jobId'])
    shot = job['shots'][0]
    warning = {'code': 'layout_bottom_gap', 'message': '画面下半截空着：主画面只占到 y=900，离字幕带还空 46.2%'}
    gen.record_layout(root, shot, {'status': 'measured', 'warnings': [warning]})
    gen.record_layout(root, shot, {'status': 'unmeasurable', 'reason': 'edge_background_not_uniform', 'warnings': []})
    assert shot['checks']['warnings'] == [warning]
    assert json.loads((root/'checks/01.json').read_text())['warnings'] == [warning]
    assert json.loads((root/'checks/layout/01.json').read_text())['status'] == 'unmeasurable'
    assert len(model.calls) == 2 and shot['attempts'] == 1
