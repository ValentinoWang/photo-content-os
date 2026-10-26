"""R283 library contracts; all generation uses deterministic doubles."""
import copy
import json
from pathlib import Path

import jsonschema
import pytest

from test_r276_direct_api import api
from test_r276_direct_video import FakeMedia, html
from test_r278_style_base import Model, SHOT, design, generate, idle
from direct_video import styles
from direct_video.generate import DirectVideoError, Generator
from direct_video.lint import declared_seconds, lint
from studio.api_contract import build_openapi
from studio.direct_video import projection

IDS = ['flat', 'math', 'launch', 'whiteboard', 'cyber', 'ink', 'dataviz', 'pixel', 'code']


def sample(root, ident='flat'):
    root.mkdir(parents=True, exist_ok=True)
    value = {k: v for k, v in design([SHOT]).items() if k != 'perShot'}
    value.update(id=ident, name='测试画法', visualGrammar='米白纸底，逐笔画出，不用默认霓虹。')
    # Library recipes may have more bans than a newly generated design.
    value['banned'] = ['不用套路' + str(i) for i in range(8)]
    (root / (ident + '.json')).write_text(json.dumps(value, ensure_ascii=False))
    (root / (ident + '.html')).write_text(html(12, '不同内容的风格样张'))
    (root / (ident + '.jpg')).write_bytes(b'synthetic-poster')
    (root / (ident + '.mp4')).write_bytes(b'synthetic-clip')
    return value


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    root = tmp_path / 'catalog'
    value = sample(root)
    (root / 'index.json').write_text(json.dumps(['flat']))
    monkeypatch.setattr(styles, 'STYLE_LIBRARY_ROOT', root, raising=False)
    return root, value


@pytest.fixture
def gen(tmp_path, catalog):
    return Generator(tmp_path / 'state', model_call=Model(), media=FakeMedia(), workers=1)


def test_index_order_is_authoritative_and_unrelated_files_are_not_read(catalog, monkeypatch):
    root, _ = catalog
    sample(root, 'math')
    (root / 'index.json').write_text(json.dumps(['math', 'flat']))
    reads = []
    original = Path.read_text

    def read(path, *args, **kwargs):
        reads.append(path.name)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    for count in [1, 10]:
        for i in range(count):
            (root / f'unlisted-{i}.json').write_text('invalid')
        reads.clear()
        assert [row['id'] for row in styles.StyleLibrary().entries()] == ['math', 'flat']
        assert sorted(reads) == ['flat.html', 'flat.json', 'index.json', 'math.html', 'math.json']


@pytest.mark.parametrize('field,value', [
    ('palette', {'background': '#ffffff'}), ('palette', dict.fromkeys(['background', 'primary', 'accent', 'neutral'], 'red')),
    ('typeScale', [100, 50]), ('typeScale', [True, 50, 40]), ('typeScale', [100, 50, 40.5]),
    ('motionSummary', '字' * 31), ('motionSummary', '字' + ' ' * 30), ('motionSummary', ''), ('bannedShort', []),
    ('bannedShort', ['字'] * 9), ('bannedShort', ['字' * 13]), ('bannedShort', ['字' + ' ' * 12]), ('bannedShort', [1]),
    ('motionRules', None), ('banned', None), ('visualGrammar', None),
])
def test_invalid_entry_is_logged_and_does_not_hide_valid_entries(catalog, field, value, caplog):
    root, _ = catalog
    bad = sample(root, 'math')
    bad[field] = value
    (root / 'math.json').write_text(json.dumps(bad))
    (root / 'index.json').write_text(json.dumps(['math', 'flat']))
    assert [row['id'] for row in styles.StyleLibrary().entries()] == ['flat']
    assert 'math' in caplog.text
    with pytest.raises(DirectVideoError, match='style_base_not_found'):
        styles.StyleLibrary().get('math')


@pytest.mark.parametrize('suffix', ['html', 'json', 'jpg', 'mp4'])
def test_missing_artifact_hides_entry(catalog, suffix, caplog):
    root, _ = catalog
    (root / ('flat.' + suffix)).unlink()
    assert styles.StyleLibrary().entries() == []
    assert 'flat' in caplog.text


def test_bad_json_and_outside_symlink_are_rejected(catalog, tmp_path, caplog):
    root, _ = catalog
    (root / 'flat.json').write_text('{')
    assert styles.StyleLibrary().entries() == []
    sample(root)
    outside = tmp_path / 'outside.html'
    outside.write_text('private')
    (root / 'flat.html').unlink()
    (root / 'flat.html').symlink_to(outside)
    assert styles.StyleLibrary().entries() == []
    assert 'flat' in caplog.text


def test_catalog_refreshes_after_edit(catalog):
    root, value = catalog
    library = styles.StyleLibrary()
    assert library.get('flat')['name'] == value['name']
    value['name'] = '新名字'
    (root / 'flat.json').write_text(json.dumps(value))
    assert library.get('flat')['name'] == '新名字'


@pytest.mark.parametrize('instruction', ['', '  ', '底色换成深色，其余不动'])
def test_library_design_and_prompts_survive_restart_and_single_shot_revision(gen, catalog, instruction):
    root, value = catalog
    class RecipeModel(Model):
        def __call__(self, **kwargs):
            result = super().__call__(**kwargs)
            context = json.loads(kwargs['user_prompt'])
            if 'shots' in context:
                changed = copy.deepcopy(context['baseDesign'])
                changed['palette']['background'] = '#000000'
                changed['perShot'] = design(context['shots'])['perShot']
                return json.dumps(changed)
            return result
    gen.model_call = RecipeModel()
    job = generate(gen, {'storyboard': {'shots': [SHOT, {**SHOT, 'shotId': '02'}]},
                         'styleBase': {'kind': 'library', 'id': 'flat'}, 'style': instruction})
    assert job['status'] == 'ready'
    contexts = gen.model_call.contexts()
    designs = [c for c in contexts if 'shots' in c]
    assert len(designs) == bool(instruction.strip())
    if instruction.strip():
        assert designs[0]['style'] == instruction.strip()
        assert designs[0]['baseDesign'] == {k: value[k] for k in (*styles.DESIGN_FIELDS, 'visualGrammar')}
        for key in styles.DESIGN_FIELDS:
            expected = {**value[key], 'background': '#000000'} if key == 'palette' else value[key]
            assert job['design'][key] == expected
    else:
        assert {k: job['design'][k] for k in styles.DESIGN_FIELDS} == {k: value[k] for k in styles.DESIGN_FIELDS}
    assert projection(job)['design']['source'] == {
        'kind': 'library', 'id': 'flat', 'name': value['name'], 'instruction': instruction.strip()}
    # Rewriting uses the frozen sample even if the library later changes.
    sample_code = (root / 'flat.html').read_text()
    (root / 'flat.html').write_text('changed after job creation')
    restarted = Generator(gen.root.parent, model_call=Model(), media=FakeMedia(), workers=1)
    restarted.revise('project1', job['jobId'], '01', [{'text': '线条更粗', 'own': True}])
    idle(restarted)
    assert restarted.read('project1', job['jobId'])['status'] == 'ready'
    writing = [c for c in contexts + restarted.model_call.contexts() if 'D' in c]
    assert len(writing) == 3
    for context in writing:
        assert context['form_profile']['visual_grammar'] == value['visualGrammar']
        assert context['styleSampleCode'] == sample_code
    for call in [c for c in gen.model_call.calls + restarted.model_call.calls if '"D"' in c['user_prompt']]:
        assert '同一风格的一镜样例，内容不同，只照画法' in call['system_prompt']
    assert str(gen.root.parent) not in json.dumps(projection(job))


@pytest.mark.parametrize('ident', ['missing', '../flat', '/flat', '', None, 1])
def test_unknown_id_never_calls_model(gen, ident):
    with pytest.raises(DirectVideoError, match='style_base_not_found'):
        gen.create('project1', {'script': '话。', 'styleBase': {'kind': 'library', 'id': ident}}, background=False)
    assert gen.model_call.calls == []
    assert not list(gen.root.glob('*/*/job.json'))


def test_library_http_media_range_creation_and_openapi(api, catalog):
    request, csrf, pid, app, _ = api
    root, value = catalog
    app.direct_video.generator.model_call = Model()
    status, _, result = request('/api/direct/styles')
    assert status == 200 and result['styles'] == []
    entry = result['library'][0]
    assert entry['id'] == 'flat' and entry['name'] == value['name']
    assert entry['design'] == {k: value[k] for k in styles.DESIGN_FIELDS}
    spec = build_openapi()
    jsonschema.validate(result, spec['paths']['/api/direct/styles']['get']['responses']['200']['content']['application/json']['schema'])
    for field, suffix, mime in [('posterUrl', 'jpg', 'image/jpeg'), ('clipUrl', 'mp4', 'video/mp4')]:
        path = entry[field]
        content = (root / ('flat.' + suffix)).read_bytes()
        response = request(path)
        assert response[0] == 200 and response[2] == content and response[1]['Content-Type'] == mime
        for header, expected in [('bytes=0-3', content[:4]), ('bytes=4-', content[4:]), ('bytes=-3', content[-3:])]:
            ranged = request(path, headers={'Range': header})
            assert ranged[0] == 206 and ranged[2] == expected
            assert ranged[1]['Accept-Ranges'] == 'bytes'
        for header in ['bytes=9999-', 'bytes=2-1', 'bytes=0-1,3-4']:
            assert request(path, headers={'Range': header})[0] == 416
        assert request(path.replace('/flat/', '/missing/'))[0] == 404
    jobs = f'/api/projects/{pid}/direct/jobs'
    body = {'script': '新的话。', 'styleBase': {'kind': 'library', 'id': 'flat'}}
    assert request(jobs, 'POST', body)[0] == 403
    status, _, payload = request(jobs, 'POST', body, csrf)
    assert status == 201 and payload['job']['design']['source']['kind'] == 'library'
    idle(app.direct_video.generator)
    public = request(jobs + '/' + payload['job']['jobId'])[2]['job']
    jsonschema.validate(public, spec['components']['schemas']['DirectJob'])
    jsonschema.validate(body, spec['paths']['/api/projects/{projectId}/direct/jobs']['post']['requestBody']['content']['application/json']['schema'])
    assert str(root) not in json.dumps(result) + json.dumps(public)
    assert request(jobs, 'POST', {**body, 'styleBase': {'kind': 'library', 'id': 'missing'}}, csrf)[2]['error']['code'] == 'style_base_not_found'
    assert request(jobs, 'POST', {**body, 'styleBase': {'kind': 'library', 'id': 'missing'}}, csrf)[0] == 404
    assert json.loads((Path(__file__).resolve().parents[1] / 'schemas/studio-openapi.json').read_text()) == spec


def test_real_library_nine_complete_valid_samples():
    root = Path(styles.__file__).with_name('style_library')
    assert json.loads((root / 'index.json').read_text()) == IDS
    library = styles.StyleLibrary(root)
    assert [row['id'] for row in library.entries()] == IDS
    for ident in IDS:
        for suffix in ['json', 'html', 'jpg', 'mp4']:
            assert (root / (ident + '.' + suffix)).is_file()
        code = (root / (ident + '.html')).read_text()
        checks = lint(code, '有个经典实验：让学生穿件尴尬的衣服走进教室。穿的人估计，约 50% 的人会注意到；实际只有约 25%。别人的注意，远比我们以为的少。', declared_seconds(code) or 0)
        assert not checks['errors'], (ident, checks['errors'])
