import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from scripts import generate_avatar_clip as avatar_cli
from scripts.avatar import videoretalk
from scripts.avatar.videoretalk import AvatarError, Client, generate_avatar_clip, plan_audio


@pytest.fixture
def media(tmp_path):
    video, audio = tmp_path / 'v.mp4', tmp_path / 'a.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=size=32x32:rate=10:duration=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=duration=2', str(audio)], check=True)
    return video, audio


class Response:
    ok = True
    status_code = 200
    def __init__(self, data=None, content=b''):
        self.data, self.content = data, content
    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError()
    def json(self):
        return self.data
    def iter_content(self, size):
        yield self.content


class Fake:
    def __init__(self, video):
        self.video, self.submits, self.posts, self.gets = video, 0, [], []
    def get(self, url, **kwargs):
        self.gets.append((url, kwargs))
        if '/uploads' in url:
            return Response({'data': {'upload_dir': 'tmp', 'upload_host': 'https://upload.test', 'oss_access_key_id': 'id', 'signature': 'sig', 'policy': 'policy', 'x_oss_object_acl': 'private', 'x_oss_forbid_overwrite': 'true'}})
        if '/tasks/' in url:
            return Response({'output': {'task_status': 'SUCCEEDED', 'video_url': 'https://dashscope-test.oss-cn-shanghai.aliyuncs.com/out?secret=1'}})
        return Response(content=self.video.read_bytes())
    def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        if '/video-synthesis' in url:
            self.submits += 1
            return Response({'output': {'task_id': 'task-1'}})
        return Response()


def run(media, tmp_path, fake, **kw):
    v, a = media
    return generate_avatar_clip(v, a, tmp_path / 'out', material='public-sample', owner_consent=None, api_key='SECRET', live=True, transport=fake, **kw)


def test_submit_upload_completed_and_metadata(media, tmp_path):
    f = Fake(media[0])
    run(media, tmp_path, f)
    assert f.submits == 1
    upload = next(x for x in f.posts if x[0] == 'https://upload.test')[1]
    assert set(upload['data']) == {'OSSAccessKeyId', 'Signature', 'policy', 'x-oss-object-acl', 'x-oss-forbid-overwrite', 'key', 'success_action_status'}
    assert 'file' in upload['files'] and upload['timeout'] == (10, 60)
    submit = next(x for x in f.posts if 'video-synthesis' in x[0])[1]
    assert submit['headers']['X-DashScope-Async'] == 'enable'
    assert submit['headers']['X-DashScope-OssResourceResolve'] == 'enable'
    assert submit['json']['parameters'] == {'video_extension': True}
    assert submit['json']['input']['ref_image_url'] == ''
    download = f.gets[-1][1]
    assert 'headers' not in download and download['allow_redirects'] is False
    out = tmp_path / 'out'
    info = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format_tags=comment', '-of', 'json', str(out / 'avatar.mp4')], capture_output=True, text=True, check=True)
    assert json.loads(info.stdout)['format']['tags']['comment'] == 'AI生成'
    ledger = json.loads((out / 'avatar-ledger.json').read_text())
    assert ledger['updated_at'].endswith('Z')
    assert json.loads((out / 'avatar.ai-label.json').read_text())['generated_at'].endswith('Z')
    run(media, tmp_path, f)
    assert f.submits == 1


def test_resume_and_unknown(media, tmp_path):
    f = Fake(media[0])
    run(media, tmp_path, f)
    p = tmp_path / 'out' / 'avatar-ledger.json'
    ledger = json.loads(p.read_text())
    ledger['segments'][0]['status'] = 'submitted'
    p.write_text(json.dumps(ledger))
    f.submits = 0
    run(media, tmp_path, f)
    assert f.submits == 0
    ledger = json.loads(p.read_text())
    ledger['segments'][0].update(status='submitting', task_id=None)
    p.write_text(json.dumps(ledger))
    with pytest.raises(AvatarError, match='avatar_submit_unknown'):
        run(media, tmp_path, f)
    assert f.submits == 0


def test_changed_input_resubmits(media, tmp_path):
    f = Fake(media[0])
    run(media, tmp_path, f)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=500:duration=2', str(media[1])], check=True)
    run(media, tmp_path, f)
    assert f.submits == 2


def test_silence_and_hard_cut(tmp_path):
    audio = tmp_path / 'silence.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=duration=2', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono:d=1', '-f', 'lavfi', '-i', 'sine=duration=2', '-filter_complex', '[0:a][1:a][2:a]concat=n=3:v=0:a=1', str(audio)], check=True)
    _, segments = plan_audio(audio, 3)
    assert segments[0]['cut'] == 'silence' and 2 <= segments[0]['end'] <= 3
    tone = tmp_path / 'tone.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=duration=5', str(tone)], check=True)
    assert plan_audio(tone, 3)[1][0]['cut'] == 'hard'


def test_invalid_url_and_errors(media, tmp_path, capsys):
    client = Client('SECRET', Fake(media[0]))
    for url in ['http://dashscope-a.oss-x.aliyuncs.com/a', 'https://dashscope-a.oss-x.aliyuncs.com.evil/a', 'https://evil.com/a']:
        with pytest.raises(AvatarError, match='avatar_result_url_invalid'):
            client.download(url, tmp_path / 'out')
    class Broken(Fake):
        def post(self, url, **kw):
            if 'video-synthesis' in url:
                raise requests.Timeout('SECRET signed-url')
            return super().post(url, **kw)
    with pytest.raises(AvatarError, match='avatar_submit_unknown') as e:
        run(media, tmp_path, Broken(media[0]))
    assert 'SECRET' not in str(e.value) + capsys.readouterr().out
    with pytest.raises(AvatarError, match='avatar_submit_unknown'):
        run(media, tmp_path, Fake(media[0]))


def test_dry_and_consent(media, tmp_path):
    v, a = media
    assert generate_avatar_clip(v, a, tmp_path, material='public-sample', owner_consent=None, api_key='', live=False)['estimated_yuan'] == .16
    with pytest.raises(AvatarError, match='avatar_input_invalid'):
        generate_avatar_clip(v, a, tmp_path, material='self', owner_consent=None, api_key='', live=False)
    with pytest.raises(AvatarError, match='avatar_api_key_missing'):
        generate_avatar_clip(v, a, tmp_path, material='public-sample', owner_consent=None, api_key='', live=True)


def test_hard_cut_recorded(media, tmp_path):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=duration=5', str(media[1])], check=True)
    run(media, tmp_path, Fake(media[0]), max_seconds=3)
    ledger = json.loads((tmp_path / 'out' / 'avatar-ledger.json').read_text())
    assert ledger['segments'][0]['cut'] == 'hard'
    assert len(ledger['segments']) == 2


def test_failure_codes(media, tmp_path):
    class UploadFail(Fake):
        def get(self, url, **kw):
            raise requests.Timeout('secret')
    with pytest.raises(AvatarError, match='avatar_upload_failed'):
        run(media, tmp_path / 'upload', UploadFail(media[0]))

    class SubmitFail(Fake):
        def post(self, url, **kw):
            if 'video-synthesis' in url:
                return http_error(400, 'InvalidParameter')
            return super().post(url, **kw)
    with pytest.raises(AvatarError, match='avatar_submit_failed.*provider_code=InvalidParameter'):
        run(media, tmp_path / 'submit', SubmitFail(media[0]))
    row = json.loads((tmp_path / 'submit' / 'out' / 'avatar-ledger.json').read_text())['segments'][0]
    assert row['status'] == 'rejected' and row['provider_code'] == 'InvalidParameter'

    class TaskFail(Fake):
        def get(self, url, **kw):
            if '/tasks/' in url:
                return Response({'output': {'task_status': 'FAILED'}})
            return super().get(url, **kw)
    with pytest.raises(AvatarError, match='avatar_task_failed'):
        run(media, tmp_path / 'task', TaskFail(media[0]))

    class Pending(Fake):
        def get(self, url, **kw):
            if '/tasks/' in url:
                return Response({'output': {'task_status': 'RUNNING'}})
            return super().get(url, **kw)
    with pytest.raises(AvatarError, match='avatar_timeout'):
        run(media, tmp_path / 'timeout', Pending(media[0]), wait_seconds=0.01)

    class DownloadFail(Fake):
        def get(self, url, **kw):
            if url.startswith('https://dashscope-test.'):
                raise requests.Timeout('secret')
            return super().get(url, **kw)
    with pytest.raises(AvatarError, match='avatar_download_failed'):
        run(media, tmp_path / 'download', DownloadFail(media[0]))


SIGNED_URL = 'https://dashscope-test.oss-cn-shanghai.aliyuncs.com/out?signature=private'


def http_error(status, code):
    response = Response({'code': code, 'message': f'SECRET {SIGNED_URL}'})
    response.ok = False
    response.status_code = status
    return response


class SubmitOnce(Fake):
    def __init__(self, video, first_response):
        super().__init__(video)
        self.first_response = first_response

    def post(self, url, **kwargs):
        response = super().post(url, **kwargs)
        if '/video-synthesis' in url and self.submits == 1:
            if isinstance(self.first_response, Exception):
                raise self.first_response
            return self.first_response
        return response


def cli(monkeypatch, *args):
    monkeypatch.setattr(sys, 'argv', ['generate_avatar_clip.py', *map(str, args)])
    return avatar_cli.main()


def test_arrears_rejected_then_retries(media, tmp_path, monkeypatch, capsys):
    fake = SubmitOnce(media[0], http_error(400, 'Arrearage'))
    monkeypatch.setattr(videoretalk.requests, 'Session', lambda: fake)
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'SECRET')
    out = tmp_path / 'out'
    assert cli(monkeypatch, '--video', media[0], '--audio', media[1], '--out-dir', out,
               '--material', 'public-sample', '--live') == 1
    stderr = capsys.readouterr().err
    assert 'avatar_account_arrears' in stderr
    assert '百炼账号欠费或状态异常，请到阿里云控制台处理后重试' in stderr
    assert 'provider_code=Arrearage' in stderr
    assert 'SECRET' not in stderr and SIGNED_URL not in stderr
    row = json.loads((out / 'avatar-ledger.json').read_text())['segments'][0]
    assert (row['status'], row['task_id'], row['provider_code']) == ('rejected', None, 'Arrearage')
    assert row['rejected_at'].endswith('Z')
    assert fake.submits == 1
    run(media, tmp_path, fake)
    assert fake.submits == 2
    assert sum(url == 'https://upload.test' for url, _ in fake.posts) == 4


@pytest.mark.parametrize('response', [
    http_error(503, 'ServiceUnavailable'),
    requests.Timeout(f'SECRET {SIGNED_URL}'),
    requests.ConnectionError(f'SECRET {SIGNED_URL}'),
    Response({'output': {}}),
], ids=['5xx', 'timeout', 'disconnect', 'missing-task-id'])
def test_uncertain_submission_stays_blocked(media, tmp_path, response):
    fake = SubmitOnce(media[0], response)
    with pytest.raises(AvatarError, match='avatar_submit_unknown') as error:
        run(media, tmp_path, fake)
    if getattr(response, 'status_code', None) == 503:
        assert 'provider_code=ServiceUnavailable' in str(error.value)
    assert 'SECRET' not in str(error.value) and SIGNED_URL not in str(error.value)
    row = json.loads((tmp_path / 'out' / 'avatar-ledger.json').read_text())['segments'][0]
    assert (row['status'], row['task_id']) == ('submitting', None)
    assert fake.submits == 1
    with pytest.raises(AvatarError, match='avatar_submit_unknown'):
        run(media, tmp_path, fake)
    assert fake.submits == 1


@pytest.mark.parametrize('step,fallback', [
    ('policy', 'avatar_upload_failed'),
    ('upload', 'avatar_upload_failed'),
    ('query', 'avatar_task_failed'),
])
@pytest.mark.parametrize('provider_code', ['Arrearage', 'Bad.Request-1_2', SIGNED_URL, 'A' * 65, 'SECRET'])
def test_http_response_diagnostics(media, step, fallback, provider_code):
    class Rejected(Fake):
        def get(self, url, **kwargs):
            if (step == 'policy' and '/uploads' in url) or (step == 'query' and '/tasks/' in url):
                return http_error(400, provider_code)
            return super().get(url, **kwargs)

        def post(self, url, **kwargs):
            return http_error(400, provider_code)

    client = Client('SECRET', Rejected(media[0]))
    expected = 'avatar_account_arrears' if provider_code == 'Arrearage' else fallback
    with pytest.raises(AvatarError, match=expected) as error:
        if step == 'query':
            client.poll('task-1', time.monotonic() + 10)
        else:
            client.upload(media[0])
    stderr = str(error.value)
    if provider_code in ('Arrearage', 'Bad.Request-1_2'):
        assert f'provider_code={provider_code}' in stderr
    else:
        assert 'provider_code=' not in stderr
    assert 'SECRET' not in stderr and SIGNED_URL not in stderr


def test_forget_unknown_requires_reason_then_allows_retry(media, tmp_path, monkeypatch, capsys):
    def unexpected_network():
        pytest.fail('账本解锁不应创建网络会话')

    monkeypatch.setattr(videoretalk.requests, 'Session', unexpected_network)
    fake = SubmitOnce(media[0], requests.Timeout())
    with pytest.raises(AvatarError, match='avatar_submit_unknown'):
        run(media, tmp_path, fake)
    out = tmp_path / 'out'
    ledger = out / 'avatar-ledger.json'
    before = ledger.read_bytes()
    args = ('--out-dir', out, '--forget-unknown', 0)
    with pytest.raises(SystemExit) as error:
        cli(monkeypatch, *args)
    assert error.value.code == 2
    assert '--reason' in capsys.readouterr().err
    assert ledger.read_bytes() == before

    reason = '已在百炼控制台核实，云端没有创建任务。'
    assert cli(monkeypatch, *args, '--reason', reason) == 0
    row = json.loads(ledger.read_text())['segments'][0]
    assert (row['status'], row['task_id']) == ('ready', None)
    assert fake.submits == 1
    run(media, tmp_path, fake)
    assert fake.submits == 2
    row = json.loads(ledger.read_text())['segments'][0]
    assert row['status'] == 'completed'
    assert row['forgotten_at'].endswith('Z') and row['forget_reason'] == reason
    after = ledger.read_bytes()
    assert cli(monkeypatch, *args, '--reason', reason) == 1
    assert ledger.read_bytes() == after
