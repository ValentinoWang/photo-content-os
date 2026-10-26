"""R278 backend contracts with isolated state and deterministic model responses."""
import copy
import json
import threading
import time
from pathlib import Path

import pytest

from test_r276_direct_api import api
from test_r276_direct_video import FakeMedia, html
from direct_video.generate import DirectVideoError, Generator, parse_shots, validate_design
from studio.direct_video import projection

SHOT = {'shotId': '01', 'dialogue': '第一句话。', 'visual': '一条线逐步长出',
        'subtitle': '先看这里', 'camera': '固定近景', 'audio': 'PRIVATE_AUDIO_ONLY'}


def design(rows):
    return {'palette': dict(background='#ffffff', primary='#113344', accent='#ee6611', neutral='#777777'),
            'typeScale': [132, 72, 44], 'motionRules': '每句只动一个东西，动完就停',
            'motionSummary': '每句只动一个东西', 'banned': ['霓虹', '渐变', '毛玻璃'],
            'bannedShort': ['霓虹', '渐变'],
            'perShot': [{'shotId': r['shotId'], 'mainAction': r.get('visual') or '画线', 'takeaway': '看清关系'} for r in rows]}


class Model:
    def __init__(self):
        self.calls = []
        self.bad_design = 0
        self.bad_code = 0
        self.gate = None

    def __call__(self, **kwargs):
        user = json.loads(kwargs['user_prompt'])
        self.calls.append(copy.deepcopy(kwargs))
        if self.gate:
            self.gate.wait(8)
        if 'shots' in user:
            value = design(user['shots'])
            if self.bad_design:
                self.bad_design -= 1
                value.pop('motionSummary')
        else:
            value = {'code': html(user['D'], user.get('instruction') or '样张')}
            if self.bad_code:
                self.bad_code -= 1
                value['code'] = 'invalid'
        return json.dumps(value, ensure_ascii=False)

    def contexts(self):
        return [json.loads(c['user_prompt']) for c in self.calls]


def idle(gen):
    deadline = time.monotonic() + 10
    while gen.active and time.monotonic() < deadline:
        time.sleep(.01)
    assert not gen.active


@pytest.fixture
def gen(tmp_path):
    return Generator(tmp_path, model_call=Model(), media=FakeMedia(), workers=1)


def generate(gen, body=None, pid='project1'):
    job = gen.create(pid, body or {'storyboard': {'shots': [SHOT]}, 'style': '浅底深青'}, background=False)
    gen.generate(pid, job['jobId'])
    return gen.read(pid, job['jobId'])


def draft(gen, shot=None):
    row = gen.create_draft('project1', {'text': '浅底深青', 'shot': shot or SHOT})
    idle(gen)
    result = gen.read_draft('project1', row['jobId'])
    assert result['status'] == 'ready'
    return result


def test_four_columns_storage_projection_and_all_writing_prompts(gen):
    job = generate(gen)
    for key in ('visual', 'subtitle', 'camera', 'audio'):
        assert job['shots'][0][key] == SHOT[key]
        assert projection(job)['shots'][0][key] == SHOT[key]
    gen.revise('project1', job['jobId'], '01', [{'text': '线条更粗', 'own': True}])
    idle(gen)
    assert len(gen.model_call.calls) == 3
    for call in gen.model_call.calls:
        text = call['user_prompt'] + call['system_prompt']
        assert 'PRIVATE_AUDIO_ONLY' not in text
        for key in ('visual', 'subtitle', 'camera'):
            assert SHOT[key] in text
    write = gen.model_call.calls[1]['system_prompt']
    assert all(label in write for label in ('编导写的画面', '画面上要出现的字', '景别 · 运镜', '颜色、字号以全片设计为准'))
    assert 'mainAction' in gen.model_call.calls[0]['system_prompt']


@pytest.mark.parametrize('key', ['visual', 'subtitle', 'camera', 'audio'])
@pytest.mark.parametrize('value', ['', ' \n\t ', ' 字 '])
def test_optional_columns_trim_and_null(key, value):
    result = parse_shots({'storyboard': {'shots': [{**SHOT, key: value}]}})[0]
    assert result[key] == (value.strip() or None)


@pytest.mark.parametrize('key', ['visual', 'subtitle', 'camera', 'audio'])
@pytest.mark.parametrize('value', [12, None, [], '字' * 2001])
def test_invalid_columns_rejected(key, value):
    with pytest.raises(DirectVideoError, match='script_invalid'):
        parse_shots({'storyboard': {'shots': [{**SHOT, key: value}]}})


def test_script_compatibility_and_old_projection(gen):
    job = generate(gen, {'script': '旧调用。', 'style': '浅底'})
    for key in ('visual', 'subtitle', 'camera', 'audio'):
        assert job['shots'][0][key] is None
        del job['shots'][0][key]
    for key in ('motionSummary', 'bannedShort', 'source'):
        job['design'].pop(key, None)
    result = projection(job)
    assert result['design']['motionSummary'] is None and result['design']['bannedShort'] is None
    assert result['design']['source'] is None
    assert result['shots'][0]['visual'] is None


@pytest.mark.parametrize('field,value', [('motionSummary', None), ('bannedShort', None),
    ('motionSummary', '字' * 31), ('motionSummary', '移动20px'), ('motionSummary', '放大50%'),
    ('motionSummary', '移到(10,20)'), ('bannedShort', []), ('bannedShort', ['字'] * 9),
    ('bannedShort', ['字' * 13]), ('motionSummary', ''), ('bannedShort', [1])])
def test_short_design_validation(field, value):
    data = design([SHOT])
    if value is None:
        data.pop(field)
    else:
        data[field] = value
    with pytest.raises(DirectVideoError, match='design_invalid'):
        validate_design(data, [SHOT])


@pytest.mark.parametrize('bad,success', [(1, True), (2, False)])
def test_design_retry_once(gen, bad, success):
    gen.model_call.bad_design = bad
    row = gen.create('project1', {'script': '一句话。', 'style': '浅底'})
    idle(gen)
    job = gen.read('project1', row['jobId'])
    assert (job['status'] == 'ready') is success
    assert sum('shots' in c for c in gen.model_call.contexts()) == 2
    if not success:
        assert job['failureCode'] == 'design_invalid' and job['design']['status'] == 'failed'


@pytest.mark.parametrize('instruction', ['', '主色更深'])
def test_inherit_or_adjust_design(gen, instruction):
    base = generate(gen)
    before = len(gen.model_call.calls)
    job = generate(gen, {'script': '另一段话。', 'style': instruction,
                        'styleBase': {'kind': 'job', 'projectId': 'project1', 'jobId': base['jobId']}})
    calls = gen.model_call.contexts()[before:]
    assert sum('shots' in c for c in calls) == bool(instruction)
    assert job['design']['source']['kind'] == ('adjusted' if instruction else 'inherited')
    if instruction:
        assert calls[0]['baseDesign']['palette'] == base['design']['palette']
        assert calls[0]['style'] == instruction
    else:
        assert {k: v for k, v in job['design'].items() if k != 'source'} == {k: v for k, v in base['design'].items() if k != 'source'}


def test_legacy_design_inherits_short_fields_unchanged(gen):
    base = generate(gen)
    root = gen.path('project1', base['jobId'])
    for key in ('motionSummary', 'bannedShort'):
        base['design'].pop(key)
    gen.save(root, base)
    content = json.loads((root / 'design.json').read_text())
    for key in ('motionSummary', 'bannedShort'):
        content.pop(key)
    (root / 'design.json').write_text(json.dumps(content))
    job = generate(gen, {'script': '话。', 'styleBase': {'kind': 'job', 'projectId': 'project1', 'jobId': base['jobId']}})
    assert projection(job)['design']['motionSummary'] is None
    assert projection(job)['design']['bannedShort'] is None


@pytest.mark.parametrize('key', [None, 'dialogue', 'visual', 'subtitle', 'camera'])
def test_draft_reuse_exact_bytes_and_changed_columns_rewrite(gen, key):
    source = draft(gen)
    row = {**SHOT}
    if key:
        row[key] += '变化'
    before = len(gen.model_call.calls)
    job = generate(gen, {'storyboard': {'shots': [row]}, 'styleBase': {
        'kind': 'draft', 'projectId': 'project1', 'draftId': source['jobId']}})
    assert job['design']['source']['kind'] == 'drafted'
    assert job['design']['palette'] == source['design']['palette']
    assert sum('shots' in c for c in gen.model_call.contexts()[before:]) == 0
    assert bool(job['shots'][0].get('fromDraft')) is (key is None)
    if key is None:
        assert len(gen.model_call.calls) == before
        for folder, ext in [('shots', 'html'), ('posters', 'jpg')]:
            assert (gen.path('project1', job['jobId']) / folder / ('01.' + ext)).read_bytes() == (gen.path('project1', source['jobId']) / folder / ('01.' + ext)).read_bytes()


def test_draft_busy_restart_failure_retry_and_code_retry(gen, tmp_path):
    gate = threading.Event()
    gen.model_call.gate = gate
    row = gen.create_draft('project1', {'text': '浅底', 'shot': SHOT})
    try:
        with pytest.raises(DirectVideoError, match='draft_busy'):
            gen.revise_draft('project1', row['jobId'], '再深一点')
    finally:
        gate.set()
    idle(gen)
    gen.model_call.gate = None
    gen.model_call.bad_code = 1
    gen.revise_draft('project1', row['jobId'], '主色再深一点')
    idle(gen)
    final = gen.read_draft('project1', row['jobId'])
    assert final['status'] == 'ready' and final['revisions'][-1]['instruction'] == '主色再深一点'
    assert final['shots'][0]['attempts'] == 3
    assert Generator(tmp_path, model_call=Model(), media=FakeMedia()).read_draft('project1', row['jobId'])['status'] == 'ready'
    final['status'] = 'writing'
    final['_workerPid'] = 2147483647
    gen.save(gen.path('project1', row['jobId']), final)
    restarted = Generator(tmp_path, model_call=Model(), media=FakeMedia())
    assert restarted.read_draft('project1', row['jobId'])['status'] == 'failed'
    restarted.revise_draft('project1', row['jobId'], '重试')
    idle(restarted)
    assert restarted.read_draft('project1', row['jobId'])['status'] == 'ready'


def test_style_http_draft_lifecycle_security_errors_and_contract(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    gen.model_call = Model()
    base = f'/api/projects/{pid}/direct/style-drafts'
    body = {'text': '浅底深青', 'shot': SHOT}
    assert request(base, 'POST', body)[0] == 403
    assert request(base, 'POST', body, {**csrf, 'Origin': 'https://evil.example'})[0] == 403
    status, _, result = request(base, 'POST', body, csrf)
    assert status == 202
    did = result['draft']['draftId']
    idle(gen)
    path = base + '/' + did
    payload = request(path)[2]['draft']
    assert payload['status'] == 'ready' and payload['shot'] == SHOT
    assert request(path + '/poster.jpg?v=1')[0] == 200
    for instruction in ['', '字' * 1001, 1]:
        assert request(path + '/revise', 'POST', {'instruction': instruction}, csrf)[0] == 400
    assert request(path + '/revise', 'POST', {'instruction': '深一点'})[0] == 403
    assert request(path + '/revise', 'POST', {'instruction': '深一点'}, csrf)[0] == 202
    idle(gen)
    jobs = f'/api/projects/{pid}/direct/jobs'
    assert request(jobs, 'POST', {'script': '话'}, csrf)[2]['error']['code'] == 'style_required'
    for kind, ident in [('job', 'jobId'), ('draft', 'draftId')]:
        res = request(jobs, 'POST', {'script': '话', 'styleBase': {'kind': kind, 'projectId': pid, ident: 'missing'}}, csrf)
        assert res[0] == 404 and res[2]['error']['code'] == 'style_base_not_found'
    current = gen.read_draft(pid, did)
    current['status'] = 'failed'
    gen.save(gen.path(pid, did), current)
    assert request(jobs, 'POST', {'script': '话', 'styleBase': {'kind': 'draft', 'projectId': pid, 'draftId': did}}, csrf)[0] == 409
    for key in ('visual', 'subtitle', 'camera', 'audio'):
        res = request(jobs, 'POST', {'style': '浅底', 'storyboard': {'shots': [{**SHOT, key: '字' * 2001}]}}, csrf)
        assert res[0] == 400 and res[2]['error']['code'] == 'script_invalid'
    from studio.api_contract import build_openapi, route_inventory
    import jsonschema
    spec = build_openapi()
    jsonschema.validate(payload, spec['components']['schemas']['DirectStyleDraft'])
    assert any(r['path'] == '/api/direct/styles' for r in route_inventory())
    assert json.loads((Path(__file__).resolve().parents[1] / 'schemas/studio-openapi.json').read_text()) == spec
    assert str(app.store.state_dir) not in json.dumps(payload)


def test_styles_cross_project_sort_dedup_and_smallest_poster(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    gen.model_call = Model()
    other = request('/api/projects', 'POST', {'title': '另一作品'}, csrf)[2]['project']['id']
    first = generate(gen, pid=pid)
    second = generate(gen, {'script': '第二次。', 'style': '深青'}, pid=other)
    root = gen.path(other, second['jobId'])
    (root / 'posters/01.jpg').rename(root / 'posters/02.jpg')
    (root / 'versions/01/1/poster.jpg').unlink()
    second['shots'].append({**copy.deepcopy(second['shots'][0]), 'shotId': '02', 'currentVersion': 0})
    gen.save(root, second)
    result = request('/api/direct/styles')
    assert result[0] == 200
    rows = result[2]['styles']
    assert len(rows) == 1 and rows[0]['projectId'] == other and rows[0]['title'] == '另一作品'
    assert '/shots/02/poster.jpg' in rows[0]['posterUrl']
    assert request(rows[0]['posterUrl'])[0] == 200
    first['design']['palette']['accent'] = '#00ff00'
    gen.save(gen.path(pid, first['jobId']), first)
    rows = request('/api/direct/styles')[2]['styles']
    assert [r['projectId'] for r in rows] == [other, pid]
    assert rows[0]['design']['motionSummary'] and rows[0]['design']['bannedShort']


def test_draft_dialogue_only_and_audio_change_still_reuses(gen):
    source = draft(gen, {'shotId': '01', 'dialogue': '旧格式样张。'})
    job = generate(gen, {'storyboard': {'shots': [{'shotId': '01', 'dialogue': '旧格式样张。', 'audio': '换音乐'}]},
                        'styleBase': {'kind': 'draft', 'projectId': 'project1', 'draftId': source['jobId']}})
    assert job['shots'][0]['fromDraft'] is True
    assert job['shots'][0]['audio'] == '换音乐'
    assert '换音乐' not in json.dumps(gen.model_call.calls, ensure_ascii=False)


@pytest.mark.parametrize('instruction', [' ', '字' * 4001, None])
def test_style_input_failures(gen, instruction):
    with pytest.raises(DirectVideoError, match='style_required' if instruction == ' ' else 'style_invalid'):
        gen.create('project1', {'script': '话', 'style': instruction}, background=False)


def test_legacy_styles_nulls_and_no_poster(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    gen.model_call = Model()
    job = generate(gen, pid=pid)
    for key in ('motionSummary', 'bannedShort'):
        job['design'].pop(key)
    gen.save(gen.path(pid, job['jobId']), job)
    root = gen.path(pid, job['jobId'])
    for path in root.rglob('*.jpg'):
        path.unlink()
    row = request('/api/direct/styles')[2]['styles'][0]
    assert row['design']['motionSummary'] is None and row['design']['bannedShort'] is None
    assert row['posterUrl'] is None


def test_busy_draft_http_and_style_base_not_ready(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    model = Model()
    gate = threading.Event()
    model.gate = gate
    gen.model_call = model
    base = f'/api/projects/{pid}/direct/style-drafts'
    result = request(base, 'POST', {'text': '浅底', 'shot': SHOT}, csrf)
    assert result[0] == 202
    did = result[2]['draft']['draftId']
    try:
        assert request(base + '/' + did + '/revise', 'POST', {'instruction': '加深'}, csrf)[2]['error']['code'] == 'draft_busy'
        status, _, result = request(f'/api/projects/{pid}/direct/jobs', 'POST', {
            'script': '话', 'styleBase': {'kind': 'draft', 'projectId': pid, 'draftId': did}}, csrf)
        assert status == 409 and result['error']['code'] == 'draft_not_ready'
    finally:
        gate.set()
        idle(gen)


def test_inherited_source_uses_current_project_title_for_legacy_job(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    gen.model_call = Model()
    source = generate(gen, pid=pid)
    source.pop('_projectTitle', None)
    gen.save(gen.path(pid, source['jobId']), source)
    status, _, result = request(f'/api/projects/{pid}/direct/jobs', 'POST', {'script': '新版本。',
        'styleBase': {'kind': 'job', 'projectId': pid, 'jobId': source['jobId']}}, csrf)
    assert status == 201
    assert result['job']['design']['source']['title'] == '合成测试'
    idle(gen)
