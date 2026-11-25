"""Offline contract & ffmpeg post-processing tests for AI music generation."""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import generate_music as generate_cli
import import_music
from music_library.ai_generate import (
    HTTPResponse,
    estimate_cost,
    generate_music,
    postprocess_audio,
    read_api_key,
    request_digest,
)
from music_library.audio import measure_audio
from music_library.errors import MusicError
from music_library.library import MusicLibrary, validate_track


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('AI music tests must never access the network')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


def _synth_wav(path: Path, *, lead_silence: float = 0.0, tone_seconds: float = 6.0, trail_silence: float = 0.0, rate: int = 44100) -> Path:
    inputs = []
    filters = []
    idx = 0
    if lead_silence > 0:
        inputs += ['-f', 'lavfi', '-i', f'anullsrc=r={rate}:cl=stereo:d={lead_silence}']
        filters.append(f'[{idx}:a]')
        idx += 1
    inputs += ['-f', 'lavfi', '-i', f'sine=frequency=440:sample_rate={rate}:duration={tone_seconds}']
    filters.append(f'[{idx}:a]')
    idx += 1
    if trail_silence > 0:
        inputs += ['-f', 'lavfi', '-i', f'anullsrc=r={rate}:cl=stereo:d={trail_silence}']
        filters.append(f'[{idx}:a]')
        idx += 1
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', *inputs]
    if idx > 1:
        cmd += ['-filter_complex', f"{''.join(filters)}concat=n={idx}:v=0:a=1[a]", '-map', '[a]']
    cmd += ['-c:a', 'pcm_s16le', str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


@pytest.fixture(scope='module')
def short_wav_bytes(tmp_path_factory) -> bytes:
    tmp = tmp_path_factory.mktemp('ai-music-short')
    wav = _synth_wav(tmp / 'short.wav', lead_silence=0.3, tone_seconds=6.5, trail_silence=0.3)
    return wav.read_bytes()


def _json_response(status: int, payload: dict) -> HTTPResponse:
    return HTTPResponse(
        status=status,
        headers={'content-type': 'application/json'},
        body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    )


def _audio_response(audio_bytes: bytes, content_type: str = 'audio/wav') -> HTTPResponse:
    return HTTPResponse(status=200, headers={'content-type': content_type}, body=audio_bytes)


def _fake_keychain(secrets: dict[str, str], *, error_code: int | None = None):
    def runner(cmd, **_kwargs):
        service = cmd[cmd.index('-s') + 1]
        if error_code is not None:
            return SimpleNamespace(returncode=error_code, stdout='', stderr='keychain locked')
        if service in secrets:
            return SimpleNamespace(returncode=0, stdout=secrets[service] + '\n', stderr='')
        return SimpleNamespace(returncode=44, stdout='', stderr='The specified item could not be found in the keychain.')

    return runner


# ---------------------------------------------------------------------------
# 1. Key resolution (missing vs unreadable)
# ---------------------------------------------------------------------------

def test_missing_keys_report_clear_chinese_guidance(tmp_path):
    empty_keychain = _fake_keychain({})
    missing_env = tmp_path / 'speech-to-text.env'

    with pytest.raises(MusicError, match='还没有 WaveSpeed 密钥：注册后放进钥匙串 wavespeed-api-key'):
        read_api_key('wavespeed', keychain_runner=empty_keychain, platform='darwin')

    with pytest.raises(MusicError, match='还没有百炼密钥'):
        read_api_key('bailian', keychain_runner=empty_keychain, stt_env_path=missing_env, platform='darwin')


def test_bailian_falls_back_to_stt_env_and_keychain_wins(tmp_path):
    env_file = tmp_path / 'speech-to-text.env'
    env_file.write_text('# comment\nSPEECH_TO_TEXT_API_KEY="sk-fallback-123"\n', encoding='utf-8')

    assert read_api_key(
        'bailian',
        keychain_runner=_fake_keychain({}),
        stt_env_path=env_file,
        platform='darwin',
    ) == 'sk-fallback-123'

    assert read_api_key(
        'bailian',
        keychain_runner=_fake_keychain({'bailian-api-key': 'sk-keychain-999'}),
        stt_env_path=env_file,
        platform='darwin',
    ) == 'sk-keychain-999'


def test_unreadable_keychain_or_env_is_never_treated_as_absent(tmp_path):
    locked_keychain = _fake_keychain({}, error_code=36)
    with pytest.raises(MusicError, match='无法读取 macOS 钥匙串.*36'):
        read_api_key('wavespeed', keychain_runner=locked_keychain, platform='darwin')

    dir_as_env = tmp_path / 'speech-to-text.env'
    dir_as_env.mkdir()
    with pytest.raises(MusicError, match='不是普通文件'):
        read_api_key('bailian', keychain_runner=_fake_keychain({}), stt_env_path=dir_as_env, platform='darwin')

    bad_utf8 = tmp_path / 'bad.env'
    bad_utf8.write_bytes(b'\xff\xfe\x80')
    with pytest.raises(MusicError, match='无法读取备用密钥文件'):
        read_api_key('bailian', keychain_runner=_fake_keychain({}), stt_env_path=bad_utf8, platform='darwin')


# ---------------------------------------------------------------------------
# 2. WaveSpeed fake HTTP: direct success, async queued -> success, AccessDenied, missing key
# ---------------------------------------------------------------------------

def test_wavespeed_direct_success_and_library_import(tmp_path, short_wav_bytes):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url, headers, body))
        if method == 'POST':
            payload = json.loads(body.decode('utf-8'))
            assert payload['tags'] == 'warm acoustic guitar, 100 bpm'
            assert payload['lyrics'] == '[inst]'
            assert payload['duration'] == 5.0
            assert headers['Authorization'] == 'Bearer ws-test-key'
            return _json_response(200, {
                'code': 200,
                'data': {
                    'id': 'pred_ws_sync_1',
                    'status': 'completed',
                    'outputs': ['https://cdn.wavespeed.test/audio/sync.wav'],
                },
            })
        assert method == 'GET' and url == 'https://cdn.wavespeed.test/audio/sync.wav'
        return _audio_response(short_wav_bytes)

    library = MusicLibrary(tmp_path)
    status, track = library.import_generated(
        'wavespeed',
        'warm acoustic guitar',
        5,
        bpm=100,
        instrumental=True,
        http_call=fake_http,
        keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-test-key'}),
        platform='darwin',
    )

    assert status == '已入库'
    assert len(calls) == 2
    assert track['platform'] == 'ai_generated'
    assert track['platform_id'] == request_digest('wavespeed', 'warm acoustic guitar', 5, bpm=100, instrumental=True)
    assert track['ai_generated'] is True
    assert track['generation']['provider'] == 'wavespeed'
    assert track['generation']['model'] == 'wavespeed-ai/ace-step-1.5'
    assert track['generation']['prompt'] == 'warm acoustic guitar'
    assert track['generation']['params'] == {'seconds': 5.0, 'bpm': 100, 'instrumental': True}
    assert track['generation']['request_id'] == 'pred_ws_sync_1'
    assert track['generation']['generated_at']
    validate_track(track)

    # Raw provider file must be kept in private cache directory.
    raw_cached = library.root / '.ai-generate' / track['platform_id'] / 'raw.wav'
    assert raw_cached.is_file() and raw_cached.read_bytes() == short_wav_bytes

    # list_tracks sees it and duplicate import returns 已在库里 with 0 new HTTP calls.
    tracks = library.list_tracks()
    assert len(tracks) == 1 and tracks[0]['file_sha256'] == track['file_sha256']

    status2, track2 = library.import_generated(
        'wavespeed',
        'warm acoustic guitar',
        5,
        bpm=100,
        instrumental=True,
        http_call=fake_http,
        keychain_runner=_fake_keychain({}),  # even without key, already in library!
        platform='darwin',
    )
    assert status2 == '已在库里'
    assert track2['file_sha256'] == track['file_sha256']
    assert len(calls) == 2


def test_wavespeed_async_polling_then_success(tmp_path, short_wav_bytes):
    calls = []
    sleeps = []
    poll_states = ['processing', 'completed']

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        if method == 'POST':
            payload = json.loads(body.decode('utf-8'))
            assert payload['lyrics'] == ''  # instrumental=False
            return _json_response(200, {
                'code': 200,
                'data': {
                    'id': 'pred_ws_async_2',
                    'status': 'created',
                    'outputs': [],
                    'urls': {'get': 'https://api.wavespeed.ai/api/v3/predictions/pred_ws_async_2/result'},
                },
            })
        if url.endswith('/result'):
            state = poll_states.pop(0)
            outputs = ['https://cdn.wavespeed.test/audio/async.wav'] if state == 'completed' else []
            return _json_response(200, {'code': 200, 'data': {'id': 'pred_ws_async_2', 'status': state, 'outputs': outputs}})
        assert url == 'https://cdn.wavespeed.test/audio/async.wav'
        return _audio_response(short_wav_bytes)

    result = generate_music(
        'wavespeed',
        'upbeat synth pop',
        5,
        cache_root=tmp_path / '.ai-generate',
        instrumental=False,
        http_call=fake_http,
        sleep=sleeps.append,
        poll_interval=0.5,
        keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-test-key'}),
        platform='darwin',
    )

    assert result.request_id == 'pred_ws_async_2'
    assert result.from_cache is False
    assert sleeps == [0.5, 0.5]
    assert len(calls) == 4  # POST + 2 poll GETs + 1 audio GET
    assert result.raw_path.is_file() and result.processed_path.is_file()


def test_wavespeed_access_denied_records_failure_and_does_not_retry(tmp_path):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        return _json_response(403, {'code': 'AccessDenied', 'message': 'invalid api key'})

    cache_root = tmp_path / '.ai-generate'
    with pytest.raises(MusicError, match='WaveSpeed 拒绝访问'):
        generate_music(
            'wavespeed',
            'piano ambient',
            10,
            cache_root=cache_root,
            http_call=fake_http,
            keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-bad-key'}),
            platform='darwin',
        )
    assert len(calls) == 1

    # Second call with same parameters hits failure cache and makes 0 HTTP calls.
    with pytest.raises(MusicError, match='本地失败缓存，未再次请求'):
        generate_music(
            'wavespeed',
            'piano ambient',
            10,
            cache_root=cache_root,
            http_call=fake_http,
            keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-bad-key'}),
            platform='darwin',
        )
    assert len(calls) == 1


def test_wavespeed_missing_key_makes_zero_requests_and_does_not_lock_cache(tmp_path, short_wav_bytes):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        if method == 'POST':
            return _json_response(200, {'code': 200, 'data': {'id': 'pred_ok', 'status': 'completed', 'outputs': ['https://cdn.wavespeed.test/ok.wav']}})
        return _audio_response(short_wav_bytes)

    cache_root = tmp_path / '.ai-generate'
    with pytest.raises(MusicError, match='还没有 WaveSpeed 密钥：注册后放进钥匙串 wavespeed-api-key'):
        generate_music(
            'wavespeed',
            'lo-fi chill',
            5,
            cache_root=cache_root,
            http_call=fake_http,
            keychain_runner=_fake_keychain({}),
            platform='darwin',
        )
    assert calls == []

    # After key is configured, the same request can proceed normally.
    result = generate_music(
        'wavespeed',
        'lo-fi chill',
        5,
        cache_root=cache_root,
        http_call=fake_http,
        keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-now-valid'}),
        platform='darwin',
    )
    assert result.request_id == 'pred_ok' and len(calls) == 2


# ---------------------------------------------------------------------------
# 3. Bailian fake HTTP: direct success, async queued -> success, AccessDenied, missing key
# ---------------------------------------------------------------------------

def test_bailian_direct_success_and_workspace_endpoint(tmp_path, short_wav_bytes):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url, headers, body))
        if method == 'POST':
            assert url == 'https://llm-demo123.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/music/generation'
            payload = json.loads(body.decode('utf-8'))
            assert payload['model'] == 'fun-music-v1'
            assert payload['input']['is_instrumental'] is True
            assert '108 BPM' in payload['input']['prompt']
            assert headers['Authorization'] == 'Bearer sk-bailian-test'
            return _json_response(200, {
                'request_id': 'req-bailian-sync-1',
                'output': {
                    'audio': {
                        'url': 'http://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/pre/fun-music/sample.wav',
                        'id': 'audio_1',
                        'data': '',
                    },
                    'finish_reason': 'stop',
                },
                'usage': {'duration': 95},
            })
        assert method == 'GET' and 'sample.wav' in url
        return _audio_response(short_wav_bytes)

    library = MusicLibrary(tmp_path)
    status, track = library.import_generated(
        'bailian',
        '温暖民谣木吉他',
        5,
        bpm=108,
        instrumental=True,
        workspace_id='llm-demo123',
        http_call=fake_http,
        keychain_runner=_fake_keychain({'bailian-api-key': 'sk-bailian-test'}),
        platform='darwin',
    )

    assert status == '已入库'
    assert track['platform'] == 'ai_generated'
    assert track['ai_generated'] is True
    assert track['generation']['provider'] == 'bailian'
    assert track['generation']['model'] == 'fun-music-v1'
    assert track['generation']['request_id'] == 'req-bailian-sync-1'
    assert track['generation']['billed_seconds'] == 95.0
    validate_track(track)
    assert len(calls) == 2


def test_bailian_async_polling_then_success(tmp_path, short_wav_bytes):
    calls = []
    sleeps = []
    poll_responses = [
        _json_response(200, {'request_id': 'req-poll-1', 'output': {'task_id': 'task-b-1', 'task_status': 'RUNNING'}}),
        _json_response(200, {
            'request_id': 'req-poll-2',
            'output': {
                'task_id': 'task-b-1',
                'task_status': 'SUCCEEDED',
                'audio': {'url': 'https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/out.wav'},
            },
            'usage': {'duration': 120},
        }),
    ]

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        if method == 'POST':
            return _json_response(200, {
                'request_id': 'req-submit-1',
                'output': {'task_id': 'task-b-1', 'task_status': 'PENDING'},
            })
        if '/api/v1/tasks/task-b-1' in url:
            return poll_responses.pop(0)
        assert url.endswith('/out.wav')
        return _audio_response(short_wav_bytes)

    result = generate_music(
        'bailian',
        '轻快电子节奏',
        5,
        cache_root=tmp_path / '.ai-generate',
        http_call=fake_http,
        sleep=sleeps.append,
        poll_interval=0.25,
        keychain_runner=_fake_keychain({'bailian-api-key': 'sk-bailian-test'}),
        platform='darwin',
    )
    assert result.request_id == 'req-poll-2'
    assert result.billed_seconds == 120.0
    assert sleeps == [0.25, 0.25]
    assert len(calls) == 4


def test_bailian_access_denied_explains_invite_preview_and_caches_failure(tmp_path):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        return _json_response(403, {
            'code': 'AccessDenied',
            'message': 'Access to model fun-music-v1 is denied.',
            'request_id': 'req-denied-1',
        })

    cache_root = tmp_path / '.ai-generate'
    with pytest.raises(MusicError, match='百炼账号还没开通 Fun-Music 邀测'):
        generate_music(
            'bailian',
            '古风笛子纯音乐',
            15,
            cache_root=cache_root,
            http_call=fake_http,
            keychain_runner=_fake_keychain({'bailian-api-key': 'sk-bailian-test'}),
            platform='darwin',
        )
    assert len(calls) == 1

    with pytest.raises(MusicError, match='百炼账号还没开通 Fun-Music 邀测.*本地失败缓存'):
        generate_music(
            'bailian',
            '古风笛子纯音乐',
            15,
            cache_root=cache_root,
            http_call=fake_http,
            keychain_runner=_fake_keychain({'bailian-api-key': 'sk-bailian-test'}),
            platform='darwin',
        )
    assert len(calls) == 1


def test_bailian_missing_key_makes_zero_requests(tmp_path):
    calls = []

    def fake_http(*args, **kwargs):
        calls.append(args)
        raise AssertionError('should not call http')

    with pytest.raises(MusicError, match='还没有百炼密钥'):
        generate_music(
            'bailian',
            '舒缓钢琴',
            10,
            cache_root=tmp_path / '.ai-generate',
            http_call=fake_http,
            keychain_runner=_fake_keychain({}),
            stt_env_path=tmp_path / 'nonexistent.env',
            platform='darwin',
        )
    assert calls == []


# ---------------------------------------------------------------------------
# 4. Cache hit makes zero HTTP calls
# ---------------------------------------------------------------------------

def test_cache_hit_reuses_processed_and_raw_without_http(tmp_path, short_wav_bytes):
    calls = []

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        calls.append((method, url))
        if method == 'POST':
            return _json_response(200, {'code': 200, 'data': {'id': 'pred_cache_1', 'status': 'completed', 'outputs': ['https://cdn.wavespeed.test/c.wav']}})
        return _audio_response(short_wav_bytes)

    cache_root = tmp_path / '.ai-generate'
    first = generate_music(
        'wavespeed',
        'cafe jazz piano',
        5,
        bpm=92,
        cache_root=cache_root,
        http_call=fake_http,
        keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-test-key'}),
        platform='darwin',
    )
    assert first.from_cache is False and len(calls) == 2

    def forbidden_http(*args, **kwargs):
        raise AssertionError('Cache hit must not send HTTP requests')

    second = generate_music(
        'wavespeed',
        'cafe jazz piano',
        5,
        bpm=92,
        cache_root=cache_root,
        http_call=forbidden_http,
        keychain_runner=_fake_keychain({}),
        platform='darwin',
    )
    assert second.from_cache is True
    assert second.request_digest == first.request_digest
    assert second.request_id == 'pred_cache_1'
    assert second.raw_path == first.raw_path and second.raw_path.is_file()
    assert second.processed_path == first.processed_path and second.processed_path.is_file()


# ---------------------------------------------------------------------------
# 5. Real ffmpeg post-processing: 2s silence + 35s sine + 3s silence -> 30s
# ---------------------------------------------------------------------------

def test_ffmpeg_postprocess_trims_silence_cuts_to_30s_fades_and_normalizes_to_minus16_lufs(tmp_path):
    raw = _synth_wav(tmp_path / 'raw_40s.wav', lead_silence=2.0, tone_seconds=35.0, trail_silence=3.0)
    processed = tmp_path / 'processed_30s.wav'

    postprocess_audio(raw, processed, 30.0)
    assert processed.is_file()

    # 1. Duration must be 30.0 ± 0.05 s, loudness must be -16 ± 1 LUFS.
    measurements = measure_audio(processed)
    assert abs(measurements['duration_seconds'] - 30.0) <= 0.05, measurements
    assert measurements['loudness_status'] == 'measured'
    assert abs(measurements['loudness_lufs'] - (-16.0)) <= 1.0, measurements

    # 2. Neither beginning nor end has >= 0.1 s silence at -45 dB.
    detect = subprocess.run(
        [
            'ffmpeg', '-nostdin', '-v', 'info', '-i', str(processed),
            '-af', 'silencedetect=noise=-45dB:d=0.1', '-f', 'null', '-',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    silence_lines = [line for line in detect.stderr.splitlines() if 'silence_start' in line or 'silence_end' in line]
    assert silence_lines == [], f'Unexpected >=0.1s silence detected: {silence_lines}'


# ---------------------------------------------------------------------------
# 6. Schema rules, family(), PLATFORMS, and CLI
# ---------------------------------------------------------------------------

def test_schema_rejects_ai_generated_without_generation_metadata(tmp_path, short_wav_bytes):
    library = MusicLibrary(tmp_path)

    def fake_http(method, url, *, headers=None, body=None, timeout=120):
        if method == 'POST':
            return _json_response(200, {'code': 200, 'data': {'id': 'pred_schema_1', 'status': 'completed', 'outputs': ['https://cdn.wavespeed.test/s.wav']}})
        return _audio_response(short_wav_bytes)

    _, track = library.import_generated(
        'wavespeed',
        'minimalist strings',
        5,
        http_call=fake_http,
        keychain_runner=_fake_keychain({'wavespeed-api-key': 'ws-key'}),
        platform='darwin',
    )
    validate_track(track)

    missing_gen = dict(track)
    del missing_gen['generation']
    with pytest.raises(MusicError):
        validate_track(missing_gen)

    false_flag = {**track, 'ai_generated': False}
    with pytest.raises(MusicError):
        validate_track(false_flag)


def test_family_platforms_and_cli_output(tmp_path, short_wav_bytes, monkeypatch, capsys):
    assert MusicLibrary.family('ai_generated') == 'ai_generated'
    assert MusicLibrary.family('netease_client') == 'netease'
    assert import_music.PLATFORMS['ai_generated'] == 'AI 生成'

    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path))

    def fake_ws(method, url, *, headers=None, body=None, timeout=120):
        if method == 'POST':
            return _json_response(200, {'code': 200, 'data': {'id': 'pred_cli_1', 'status': 'completed', 'outputs': ['https://cdn.wavespeed.test/cli.wav']}})
        return _audio_response(short_wav_bytes)

    rc = generate_cli.main(
        ['--provider', 'wavespeed', '--prompt', 'sunny vlog guitar', '--seconds', '30', '--bpm', '100'],
        gen_kwargs={'http_call': fake_ws, 'keychain_runner': _fake_keychain({'wavespeed-api-key': 'ws-key'}), 'platform': 'darwin'},
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert '已入库' in out
    assert '$0.0090' in out
    assert 'AI 生成' in out

    # Repeat CLI call hits existing library track -> 已在库里.
    rc2 = generate_cli.main(
        ['--provider', 'wavespeed', '--prompt', 'sunny vlog guitar', '--seconds', '30', '--bpm', '100'],
        gen_kwargs={'http_call': lambda *a, **kw: (_ for _ in ()).throw(AssertionError('no http')), 'keychain_runner': _fake_keychain({}), 'platform': 'darwin'},
    )
    out2 = capsys.readouterr().out
    assert rc2 == 0
    assert '已在库里' in out2

    # import_music --list works with AI-generated tracks too.
    assert import_music.main(['--list']) == 0
    list_out = capsys.readouterr().out
    assert 'AI 生成' in list_out
    assert 'sunny vlog guitar' in list_out

    # Bailian cost estimate string check.
    assert '¥0.060' in estimate_cost('bailian', 30)['text']
    assert '¥0.200' in estimate_cost('bailian', 30, billed_seconds=100)['text']
