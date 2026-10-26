"""R277 state, transport and API behavior; models are fake executables."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import shutil
import sys
import threading
import time

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import llm_common
from direct_video.generate import DirectVideoError, Generator, RULES
from direct_video.revisions import validate_findings, validate_lines, validate_verify
from studio.direct_video import projection
from test_r276_direct_video import FakeMedia, html, design, wait, wav


@pytest.fixture
def image_claude(tmp_path, monkeypatch):
    executable = tmp_path / 'fake-claude'
    executable.write_text('''#!/usr/bin/env python3
import json,os,sys,time
from pathlib import Path
sys.path[:0] = ROOT_PATHS
from test_r276_direct_video import html,design
raw=sys.stdin.read()
args=sys.argv[1:]
stream='--input-format' in args
message=json.loads(raw) if stream else None
prompt=message['message']['content'][-1]['text'] if stream else raw
context=json.loads(prompt.split('<user_context>\\n',1)[1].rsplit('\\n</user_context>',1)[0])
record={'args':args,'context':context,'content':message['message']['content'] if stream else None,'cwdFiles':list(Path.cwd().iterdir()),'nested':os.getenv('CLAUDECODE')}
record['cwdFiles']=[str(p) for p in record['cwdFiles']]
with open(os.environ['R277_CALLS'],'a') as out:out.write(json.dumps(record)+'\\n')
if os.getenv('R277_DELAY'): time.sleep(float(os.environ['R277_DELAY']))
if 'shots' in context: result=design(context['shots'])
elif 'requests' in context: result={'rule':'让主要图形和次要信息有明确的大小区别。'}
elif 'framesAt' in context:
 if os.getenv('R277_FAIL_LOOK'): print('invalid');sys.exit(0)
 result={'findings':[{'boxId':'b3','kind':'主次','text':'次要柱子抢眼','suggest':'dim'}]}
elif 'lines' in context:
 result={'items':[{'index':i,'result':'done' if i%2==0 else 'missed','reason':'' if i%2==0 else '柱子仍然太大'} for i,_ in enumerate(context['lines'])]}
 if os.getenv('R277_BAD_VERIFY'):result={'items':[]}
else:result={'code':html(context['D'],context.get('instruction') or '示意图')}
if stream:print(json.dumps({'type':'system','subtype':'init'}))
print(json.dumps({'type':'result','result':json.dumps(result),'is_error':False,'permission_denials':[]}))
'''.replace('#!/usr/bin/env python3', '#!' + sys.executable).replace('ROOT_PATHS', repr([str(ROOT), str(ROOT / 'scripts'), str(ROOT / 'tests')])))
    executable.chmod(0o755)
    calls = tmp_path / 'calls.jsonl'
    monkeypatch.setenv('OPENCLAW_CLAUDE_BIN', str(executable))
    monkeypatch.setenv('R277_CALLS', str(calls))
    return calls


class ImageMedia(FakeMedia):
    def render(self, root, shot):
        self.rendered.append(shot['shotId'])
        path = root / 'posters' / (shot['shotId'] + '.jpg')
        path.parent.mkdir(exist_ok=True)
        code = (root / 'shots' / (shot['shotId'] + '.html')).read_text()
        Image.new('RGB', (108, 192), 'blue' if '变灰' in code else 'red').save(path)
        boxes = root / 'boxes' / (shot['shotId'] + '.json')
        boxes.parent.mkdir(exist_ok=True)
        boxes.write_text(json.dumps([{'id': 'b3', 'name': '「约 25%」柱子', 'x': 580, 'y': 886, 'w': 300, 'h': 316}]))
        frames = root / 'review-frames' / shot['shotId']
        frames.mkdir(parents=True, exist_ok=True)
        for n in (3, 6, 9):
            shutil.copyfile(path, frames / f'{n}.jpg')
        return {'status': 'measured', 'warnings': []}

    def review_frames(self, root, shot):
        return [root / 'review-frames' / shot['shotId'] / f'{n}.jpg' for n in (3, 6, 9)]

    def compose(self, root, job):
        self.last_codes = {s['shotId']: (root / 'shots' / (s['shotId'] + '.html')).read_bytes() for s in job['shots']}
        return super().compose(root, job)


@pytest.fixture
def ready_image(tmp_path, image_claude):
    media = ImageMedia()
    gen = Generator(tmp_path / 'state', media=media)
    job = gen.create('project1', {'script': '第一句。\n第二句。', 'style': '浅底图解'}, background=False)
    gen.generate('project1', job['jobId'])
    return gen, gen.read('project1', job['jobId']), media, image_claude


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_image_stream_keeps_isolation_and_validated_bytes(ready_image, monkeypatch):
    gen, job, _, path = ready_image
    calls = records(path)
    images = [c for c in calls if c['content']]
    assert len(images) == 2
    for call in calls:
        args = call['args']
        assert call['cwdFiles'] == [] and call['nested'] is None
        for flag in ('--safe-mode', '--strict-mcp-config', '--no-session-persistence'):
            assert flag in args
        assert args[args.index('--tools') + 1] == ''
        assert args[args.index('--setting-sources') + 1] == ''
        assert json.loads(args[args.index('--mcp-config') + 1]) == {'mcpServers': {}}
        assert args[args.index('--output-format') + 1] == ('stream-json' if call['content'] else 'json')
    content = images[0]['content']
    assert len(content) == 4
    assert content[0]['source']['media_type'] == 'image/jpeg'
    assert base64.b64decode(content[0]['source']['data']).startswith(b'\xff\xd8')
    assert job['shots'][0]['look']['status'] == 'done'
    assert job['shots'][0]['checks']['errors'] == []
    with pytest.raises(llm_common.LLMError):
        llm_common.generate_text(provider='claude', system_prompt='', user_prompt='{}', image_paths=[Path('missing.jpg')])


@pytest.mark.parametrize('action', ['revise', 'rewrite'])
def test_versions_rollback_current_fields_and_compose(ready_image, action):
    gen, job, media, calls = ready_image
    root, jid = gen.path('project1', job['jobId']), job['jobId']
    first, untouched = copy.deepcopy(job['shots'])
    old_code = (root / 'shots/01.html').read_bytes()
    old_poster = (root / 'posters/01.jpg').read_bytes()
    gen.request_compose('project1', jid)
    assert wait(gen, job)['output']['status'] == 'ready'
    lines = [{'text': '柱子变灰', 'boxId': 'b3', 'action': 'dim'}, {'text': '底色不动', 'own': True}]
    gen.revise('project1', jid, '01', lines, '作品甲')
    changed = wait(gen, job)
    shot = changed['shots'][0]
    assert len(shot['versions']) == 2 and shot['currentVersion'] == 2
    assert [v['baseVersion'] for v in shot['versions']] == [None, 1]
    assert shot['versions'][1]['request'] == {'lines': lines}
    assert shot['versions'][1]['verify']['items'] == [
        {'index': 0, 'result': 'done', 'reason': ''}, {'index': 1, 'result': 'missed', 'reason': '柱子仍然太大'}]
    assert changed['shots'][1] == untouched and changed['output']['status'] == 'none'
    assert (root / 'versions/01/1/code.html').read_bytes() == old_code
    assert (root / 'versions/01/1/poster.jpg').read_bytes() == old_poster
    gen.request_compose('project1', jid)
    wait(gen, job)
    before_revert_calls = len(records(calls))
    reverted = gen.current('project1', jid, '01', 1)
    assert len(records(calls)) == before_revert_calls
    assert reverted['output']['status'] == 'none' and len(reverted['shots'][0]['versions']) == 2
    for key in ('posterRevision', 'codeChars', 'checks', 'writtenAt', 'attempts', 'boxes'):
        assert reverted['shots'][0][key] == first[key]
    assert (root / 'shots/01.html').read_bytes() == old_code
    assert (root / 'posters/01.jpg').read_bytes() == old_poster
    gen.request_compose('project1', jid)
    composed = wait(gen, job)
    assert media.last_codes['01'] == old_code and composed['output']['status'] == 'ready'
    assert composed['shots'][1] == untouched
    if action == 'revise':
        gen.revise('project1', jid, '01', [{'text': '第三版', 'own': True}])
    else:
        gen.rewrite('project1', jid, '01', '第三版')
    new = wait(gen, job)['shots'][0]
    assert new['currentVersion'] == 3 and len(new['versions']) == 3
    assert [v['baseVersion'] for v in new['versions']] == [None, 1, 1]
    persisted = json.loads((root / 'job.json').read_text())['shots'][0]
    assert [v['baseVersion'] for v in persisted['versions']] == [None, 1, 1]
    assert gen.current('project1', jid, '01', 2)['shots'][0]['versions'] == new['versions']
    assert new['versions'][2]['request'] == {'lines': [{'text': '第三版', 'own': True}]}


@pytest.mark.parametrize('lines,code', [([], 'instruction_invalid'), ([{'text': '' , 'own': True}], 'instruction_invalid'),
    ([{'text': ' ', 'own': True}], 'instruction_invalid'), ([{'text': '字'*201, 'own': True}], 'instruction_too_long'),
    ([{'text': '字'*100, 'own': True}, {'text': '字'*101, 'own': True}], 'instruction_too_long'),
    ([{'text': '删', 'boxId': 'missing', 'action': 'del'}], 'instruction_invalid'),
    ([{'text': '删', 'action': 'del'}], 'instruction_invalid'), ([{'text': '改', 'own': False}], 'instruction_invalid'),
    ([{'text': '改', 'own': True, 'issue': 'color'}], 'instruction_invalid'),
    ([{'text': '改', 'issue': 'bad'}], 'instruction_invalid'), ([{'text': '改', 'own': True, 'extra': 1}], 'instruction_invalid')])
def test_lines_validation_and_no_count_on_rejection(ready_image, lines, code):
    gen, job, _, _ = ready_image
    with pytest.raises(DirectVideoError, match=code):
        gen.revise('project1', job['jobId'], '01', lines)
    assert all(c['count'] == 0 for c in gen.library.log()['categories'])


def test_length_boundaries():
    assert validate_lines([{'text': '字', 'own': True}], [])
    assert validate_lines([{'text': '字'*200, 'own': True}], [])


@pytest.mark.parametrize('busy', ['active', 'compose'])
@pytest.mark.parametrize('action', ['revise', 'rewrite', 'current', 'look'])
def test_mutual_exclusion(ready_image, busy, action):
    gen, job, _, path = ready_image
    if busy == 'active':
        gen.active.add(('project1', job['jobId']))
    else:
        job['output']['status'] = 'composing'
        gen.save(gen.path('project1', job['jobId']), job)
    before = path.read_bytes()
    args = {'revise': ([{'text': '改', 'own': True}],), 'rewrite': ('改',), 'current': (1,), 'look': ()}[action]
    with pytest.raises(DirectVideoError, match='job_busy'):
        getattr(gen, action)('project1', job['jobId'], '01', *args)
    assert path.read_bytes() == before
    gen.active.clear()


def test_busy_while_real_background_look(ready_image, monkeypatch):
    gen, job, _, _ = ready_image
    monkeypatch.setenv('R277_DELAY', '.15')
    gen.look('project1', job['jobId'], '01')
    with pytest.raises(DirectVideoError, match='job_busy'):
        gen.current('project1', job['jobId'], '01', 1)
    assert wait(gen, job)['shots'][0]['look']['status'] == 'done'


def test_failed_image_and_verify_do_not_fail_render(ready_image, monkeypatch):
    gen, job, _, _ = ready_image
    monkeypatch.setenv('R277_FAIL_LOOK', '1')
    monkeypatch.setenv('R277_BAD_VERIFY', '1')
    gen.revise('project1', job['jobId'], '01', [{'text': '变灰', 'own': True}])
    result = wait(gen, job)
    shot = result['shots'][0]
    assert result['status'] == 'ready' and shot['status'] == 'rendered'
    assert shot['checks']['errors'] == [] and shot['failureCode'] is None
    assert shot['look']['failureCode'] == 'look_failed'
    assert shot['versions'][1]['verify'] == {'status': 'failed', 'failureCode': 'verify_failed', 'items': []}
    assert shot['versions'][0]['verify'] is None


def test_samples_copy_survives_job_deletion_and_two_prompt_examples(ready_image):
    gen, job, media, calls = ready_image
    for sid in ('01', '02'):
        assert gen.set_sample('project1', job['jobId'], sid, True, '作品甲')['shots'][int(sid)-1]['sample']
    gen.set_sample('project1', job['jobId'], '01', True)
    assert len(gen.library.samples()) == 2
    sample = gen.library.samples()[0]
    poster = gen.library.poster(sample['sampleId']).read_bytes()
    shutil.rmtree(gen.path('project1', job['jobId']))
    assert gen.library.poster(sample['sampleId']).read_bytes() == poster
    other = gen.create('project2', {'script': '第一句。', 'style': '浅底图解'}, background=False)
    gen.generate('project2', other['jobId'])
    gen.set_sample('project2', other['jobId'], '01', True, '作品乙')
    third = gen.create('project3', {'script': '第一句。', 'style': '浅底图解'}, background=False)
    gen.generate('project3', third['jobId'])
    writing = [c['context'] for c in records(calls) if 'D' in c['context']]
    assert len(writing[-1]['samples']) == 2 and 'code' in writing[-1]['samples'][0]
    assert any(s['sampleId'] == sample['sampleId'] for s in writing[-1]['samples'])
    gen.set_sample('project2', other['jobId'], '01', False)
    assert len(gen.library.samples()) == 2


def test_issue_counts_proposal_adopt_and_two_rule_layers(ready_image):
    gen, job, _, calls = ready_image
    before = RULES.read_bytes()
    base_rules = gen.library.rules(RULES)
    assert all(row['count'] == 0 for row in gen.library.log()['categories'])
    lines = [{'text': '柱子做主角', 'boxId': 'b3', 'action': 'main'},
             {'text': '柱子变灰', 'boxId': 'b3', 'action': 'dim'}, {'text': '字改短', 'boxId': 'b3', 'action': 'short'},
             {'text': '删掉多字', 'boxId': 'b3', 'action': 'del'}, {'text': '布局重排', 'issue': 'space'},
             {'text': '简化颜色', 'issue': 'color'}, {'text': '和口播同步', 'issue': 'sync'}, {'text': '底色不动', 'own': True}]
    gen.revise('project1', job['jobId'], '01', lines, '作品甲')
    wait(gen, job)
    assert [c['count'] for c in gen.library.log()['categories']] == [2, 2, 1, 1, 1]
    assert gen.library.rules(RULES) == base_rules
    gen.revise('project1', job['jobId'], '01', [lines[0]], '作品甲')
    wait(gen, job)
    log = gen.library.log()
    proposal = log['categories'][0]['proposals'][0]
    assert proposal['status'] == 'pending' and log['categories'][0]['count'] == 3
    assert log['categories'][0]['sources'][0]['projectTitle'] == '作品甲'
    assert gen.library.rules(RULES) == base_rules and RULES.read_bytes() == before
    with gen.lock:
        gen.library.decide(proposal['proposalId'], True)
        gen.library.decide(proposal['proposalId'], True)
    assert gen.library.log()['rulesRevision'] == 1
    assert proposal['text'] in gen.library.rules(RULES) and RULES.read_bytes() == before
    gen.rewrite('project1', job['jobId'], '01', '底色不动')
    wait(gen, job)
    assert gen.library.log()['categories'][0]['count'] == 3
    gen.revise('project1', job['jobId'], '01', [lines[0]]*3)
    wait(gen, job)
    next_proposal = gen.library.log()['categories'][0]['proposals'][1]
    gen.library.decide(next_proposal['proposalId'], False)
    assert gen.library.log()['categories'][0]['count'] == 6 and gen.library.log()['rulesRevision'] == 1


def test_unreadable_library_is_not_empty(ready_image):
    gen, job, _, _ = ready_image
    path = gen.library.root / 'direct-samples/index.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text('invalid-json')
    with pytest.raises(json.JSONDecodeError):
        gen.library.samples()
    path = gen.library.root / 'direct-rules/state.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text('invalid-json')
    with pytest.raises(json.JSONDecodeError):
        gen.library.log()


def test_legacy_projection_fields_and_privacy(ready_image):
    gen, job, _, _ = ready_image
    result = projection(job)
    new = {'currentVersion', 'versions', 'boxes', 'look', 'sample', 'visual', 'subtitle', 'camera', 'audio', 'fromDraft'}
    old = {'shotId', 'dialogue', 'mainAction', 'estimatedSeconds', 'measuredSeconds', 'timingSource', 'status',
           'failureCode', 'attempts', 'lastInstruction', 'writingStartedAt', 'writtenAt', 'renderedAt', 'codeChars', 'posterRevision', 'checks'}
    for original, projected in zip(job['shots'], result['shots']):
        assert set(projected) - new == old
        assert {k: projected[k] for k in old} == {k: original[k] for k in old}
    job['shots'][0]['versions'][0]['secretPath'] = str(gen.root)
    job['shots'][0]['look']['findings'][0]['text'] = str(gen.root / 'secret/data')
    assert str(gen.root) not in json.dumps(projection(job))
    from studio.api_contract import build_openapi
    import jsonschema
    jsonschema.validate(projection(job), build_openapi()['components']['schemas']['DirectJob'])


@pytest.mark.parametrize('value', [ {'findings': [{'boxId': 'wrong', 'kind': '主次', 'text': '错', 'suggest': 'dim'}]},
                                   {'findings': [None]}, {'findings': [{'boxId': None, 'kind': '主次', 'text': '错', 'suggest': 'other'}]},
                                   {'findings': [{}]*6}])
def test_invalid_findings_not_done(value):
    with pytest.raises(DirectVideoError, match='look_failed'):
        validate_findings(value, [])


@pytest.mark.parametrize('items', [[], [{'index': True, 'result': 'done', 'reason': ''}],
    [{'index': 0, 'result': 'missed', 'reason': ''}], [{'index': 0, 'result': 'unknown', 'reason': ''}]])
def test_invalid_verification_not_done(items):
    with pytest.raises(DirectVideoError, match='verify_failed'):
        validate_verify({'items': items}, 1)


def test_legacy_job_upgrade_retains_original_files(ready_image):
    gen, job, media, calls = ready_image
    root = gen.path('project1', job['jobId'])
    original_code = (root / 'shots/01.html').read_bytes()
    original_poster = (root / 'posters/01.jpg').read_bytes()
    for shot in job['shots']:
        for key in ('versions', 'currentVersion', 'boxes', 'look', 'sample', '_cacheVersion'):
            shot.pop(key, None)
    shutil.rmtree(root / 'versions')
    gen.save(root, job)
    updated_at = job['updatedAt']
    restored = gen.read('project1', job['jobId'])
    assert restored['updatedAt'] == updated_at
    assert json.loads((root / 'job.json').read_text())['updatedAt'] == updated_at
    assert restored['shots'][0]['currentVersion'] == 1
    assert restored['shots'][0]['versions'][0]['baseVersion'] is None
    assert (root / 'versions/01/1/code.html').read_bytes() == original_code
    assert (root / 'versions/01/1/poster.jpg').read_bytes() == original_poster
    # Rebuild review evidence when an older job has no extracted review frames.
    shutil.rmtree(root / 'review-frames')
    gen.look('project1', job['jobId'], '01')
    reviewed = wait(gen, job)
    assert reviewed['shots'][0]['look']['status'] == 'done'
    assert reviewed['updatedAt'] == updated_at


def test_restart_during_look_preserves_render_success(ready_image):
    gen, job, media, _ = ready_image
    root = gen.path('project1', job['jobId'])
    job['shots'][0]['look']['status'] = 'running'
    job['shots'][0]['versions'][0]['look']['status'] = 'running'
    job['shots'][0]['versions'][0]['verify'] = {'status': 'running', 'items': []}
    gen.save(root, job)
    updated_at = job['updatedAt']
    restored = Generator(root.parents[2], media=media).read('project1', job['jobId'])
    assert restored['updatedAt'] == updated_at
    assert restored['status'] == 'ready'
    assert restored['shots'][0]['status'] == 'rendered'
    assert restored['shots'][0]['look']['failureCode'] == 'look_failed'
    assert restored['shots'][0]['versions'][0]['look']['failureCode'] == 'look_failed'
    assert restored['shots'][0]['versions'][0]['verify']['failureCode'] == 'verify_failed'


def test_render_failure_keeps_new_code_and_previous_version(ready_image, monkeypatch):
    gen, job, media, _ = ready_image
    root = gen.path('project1', job['jobId'])
    old = (root / 'versions/01/1/code.html').read_bytes()
    def fail(*args):
        raise RuntimeError('render did not complete')
    monkeypatch.setattr(media, 'render', fail)
    gen.rewrite('project1', job['jobId'], '01', '变灰')
    current = wait(gen, job)
    assert current['shots'][0]['status'] == 'failed'
    assert current['shots'][0]['currentVersion'] == 2
    assert len(current['shots'][0]['versions']) == 2
    assert (root / 'versions/01/1/code.html').read_bytes() == old
    assert b'\xe5\x8f\x98\xe7\x81\xb0' in (root / 'versions/01/2/code.html').read_bytes()
    assert not (root / 'versions/01/2/poster.jpg').exists()
    assert gen.current('project1', job['jobId'], '01', 1)['shots'][0]['status'] == 'rendered'


def test_narration_recalculation_reads_selected_code(ready_image):
    import io
    gen, job, media, _ = ready_image
    jid = job['jobId']
    root = gen.path('project1', jid)
    code = (root / 'shots/01.html').read_bytes()
    gen.rewrite('project1', jid, '01', '变灰')
    wait(gen, job)
    gen.current('project1', jid, '01', 1)
    data = wav(4)
    gen.narration('project1', jid, io.BytesIO(data), len(data))
    aligned = wait(gen, job)
    assert (root / 'shots/01.html').read_bytes() == code
    assert aligned['narration']['status'] == 'ready'
    assert (root / 'versions/01/2/code.html').read_bytes() != code
    assert aligned['shots'][0]['currentVersion'] == 3
    assert [v['baseVersion'] for v in aligned['shots'][0]['versions']] == [None, 1, 1]


@pytest.mark.parametrize('mode', ['invalid', 'no-result', 'error', 'empty', 'exit', 'timeout'])
def test_image_transport_failures_are_private(tmp_path, monkeypatch, mode):
    path = tmp_path / 'fake-image-cli'
    path.write_text(('#!' + sys.executable + '\n') + '''import json,sys,time
raw=sys.stdin.read()
mode=MODE
if mode=='timeout':time.sleep(3)
if mode=='exit':print(raw,file=sys.stderr);sys.exit(7)
if mode=='invalid':print('invalid');sys.exit(0)
if mode=='no-result':print(json.dumps({'type':'assistant','text':'not a result'}));sys.exit(0)
print(json.dumps({'type':'result','result':' ' if mode=='empty' else raw,'is_error':mode=='error'}))
'''.replace('MODE', repr(mode)))
    path.chmod(0o755)
    image = tmp_path / 'frame.jpg'
    Image.new('RGB', (8, 8), 'red').save(image)
    monkeypatch.setenv('OPENCLAW_CLAUDE_BIN', str(path))
    monkeypatch.setenv('OPENCLAW_CLAUDE_TIMEOUT_SEC', '1')
    with pytest.raises(llm_common.LLMError) as error:
        llm_common.generate_text(provider='claude', system_prompt='private-system', user_prompt='private-user', image_paths=[image])
    assert 'private-system' not in str(error.value) and 'private-user' not in str(error.value)


def test_pre_field_version_metadata_keeps_unknown_base_null(ready_image):
    gen, job, _, _ = ready_image
    gen.rewrite('project1', job['jobId'], '01', '第二版')
    rewritten = wait(gen, job)
    root = gen.path('project1', job['jobId'])
    for version in rewritten['shots'][0]['versions']:
        version.pop('baseVersion')
    gen.save(root, rewritten)
    upgraded = gen.read('project1', job['jobId'])
    assert upgraded['updatedAt'] == rewritten['updatedAt']
    assert [v['baseVersion'] for v in upgraded['shots'][0]['versions']] == [None, None]
    assert json.loads((root / 'job.json').read_text())['shots'][0]['versions'] == upgraded['shots'][0]['versions']


@pytest.mark.parametrize('review_mode', ['success', 'failed', 'rebuild-frames'])
def test_metadata_actions_preserve_output_timestamp(ready_image, monkeypatch, review_mode):
    gen, job, _, _ = ready_image
    jid = job['jobId']
    gen.request_compose('project1', jid)
    composed = wait(gen, job)
    updated_at = composed['updatedAt']
    output = copy.deepcopy(composed['output'])
    if review_mode == 'failed':
        monkeypatch.setenv('R277_FAIL_LOOK', '1')
    elif review_mode == 'rebuild-frames':
        shutil.rmtree(gen.path('project1', jid) / 'review-frames')
    accepted = gen.look('project1', jid, '01')
    assert accepted['updatedAt'] == updated_at
    assert gen.read('project1', jid)['updatedAt'] == updated_at
    reviewed = wait(gen, job)
    assert reviewed['shots'][0]['look']['status'] == ('failed' if review_mode == 'failed' else 'done')
    assert reviewed['updatedAt'] == updated_at and reviewed['output'] == output
    for enabled in (True, False):
        sampled = gen.set_sample('project1', jid, '01', enabled, '作品甲')
        assert sampled['shots'][0]['sample'] is enabled
        assert sampled['updatedAt'] == updated_at and sampled['output'] == output
        assert gen.read('project1', jid)['updatedAt'] == updated_at


@pytest.mark.parametrize('action', ['revise', 'rewrite', 'current'])
def test_content_actions_still_update_timestamp(ready_image, action):
    from direct_video.generate import dump
    gen, job, _, _ = ready_image
    jid = job['jobId']
    if action == 'current':
        gen.rewrite('project1', jid, '01', '第二版')
        job = wait(gen, job)
    previous = '2000-01-01T00:00:00Z'
    job['updatedAt'] = previous
    dump(gen.path('project1', jid) / 'job.json', job)
    if action == 'current':
        changed = gen.current('project1', jid, '01', 1)
    elif action == 'revise':
        changed = gen.revise('project1', jid, '01', [{'text': '变灰', 'own': True}])
    else:
        changed = gen.rewrite('project1', jid, '01', '变灰')
    assert changed['updatedAt'] != previous
    assert wait(gen, job)['updatedAt'] != previous
