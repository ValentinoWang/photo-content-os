"""Offline contract tests. All identifiers and response bodies are synthetic."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.links import parse_link
from music_library.library import MusicLibrary, MusicError


@pytest.mark.parametrize('value', [
    'https://example.org/song/1', 'https://douyin.com.evil.test/music/1',
    'https://music.163.com/playlist?id=12', 'https://www.douyin.com/user/12',
    'https://music.163.com/song?id=12 https://music.163.com/song?id=13',
])
def test_unsupported(value):
    with pytest.raises(MusicError, match='不支持的链接'):
        parse_link(value)


def test_corrupt_index_is_not_empty(tmp_path):
    root = tmp_path / 'library/music'
    root.mkdir(parents=True)
    (root / 'index.json').write_text('{broken')
    with pytest.raises(MusicError, match='索引.*损坏'):
        MusicLibrary(tmp_path).list_tracks()


def test_no_retry_after_partial_failure(tmp_path):
    class Broken:
        calls = 0
        def resolve(self, link):
            self.calls += 1
            raise MusicError('下载中断')
    adapter = Broken()
    library = MusicLibrary(tmp_path, adapter=adapter)
    for _ in range(2):
        with pytest.raises(MusicError):
            library.import_link('https://music.163.com/song?id=90001')
    assert adapter.calls == 1
    assert library.list_tracks() == []
    assert not list((tmp_path / 'library/music').glob('*/track.json'))


def test_missing_license_cannot_validate(tmp_path):
    from music_library.library import validate_track
    with pytest.raises(MusicError):
        validate_track({'title': 'synthetic'})

FIXTURES = Path(__file__).parent / 'fixtures/music-library'


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('Music tests must never access the network')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.mark.parametrize('text,platform,kind,identity', [
    ('分享 https://music.163.com/#/song?id=90001&userid=123 。', 'netease', 'song', '90001'),
    ('https://music.163.com/song?id=90001', 'netease', 'song', '90001'),
    ('https://y.music.163.com/m/song?id=90001', 'netease', 'song', '90001'),
    ('分享 https://163cn.tv/abcXYZ/。', 'netease', 'share', None),
    ('https://www.douyin.com/music/90001', 'douyin', 'music', '90001'),
    ('视频分享 https://v.douyin.com/abcXYZ/，', 'douyin', 'share', None),
    ('https://www.iesdouyin.com/share/video/80001/', 'douyin', 'video', '80001'),
    ('https://qishui.douyin.com/s/abcXYZ/', 'qishui', 'share', None),
    ('https://music.douyin.com/qishui/share/track?track_id=90001', 'qishui', 'song', '90001'),
    ('https://music.douyin.com/c/abcXYZ/', 'qishui', 'share', None),
    ('https://qishui.com/song/90001', 'qishui', 'song', '90001'),
])
def test_link_forms(text, platform, kind, identity):
    link = parse_link(text)
    assert (link.platform, link.kind, link.platform_id) == (platform, kind, identity)
    assert 'userid' not in link.url


@pytest.fixture
def synthetic_audio(tmp_path):
    from music_library.client_files import decode_ncm
    audio, metadata = decode_ncm(FIXTURES / 'synthetic.ncm', tmp_path)
    from music_library.library import file_hash
    assert file_hash(audio) == (FIXTURES / 'synthetic-audio.sha256').read_text().strip()
    assert metadata['platform_id'] == '90001'
    return audio


class Adapter:
    def __init__(self, audio, fail=False):
        self.audio = audio
        self.calls = []
        self.fail = fail
    def resolve(self, link):
        self.calls.append('resolve')
        return {'platform_id': link.platform_id, 'title': '合成测试曲', 'artist': '合成歌手',
                'extension': '.mp3', 'license_status': 'platform_copyrighted'}
    def download(self, metadata, target):
        self.calls.append('download')
        target.write_bytes(self.audio.read_bytes())
        if self.fail:
            raise MusicError('下载到一半中断')


def test_duplicate_id_has_zero_network_calls_after_restart(tmp_path, synthetic_audio):
    adapter = Adapter(synthetic_audio)
    first = MusicLibrary(tmp_path, adapter=adapter)
    assert first.import_link('https://music.163.com/song?id=90001')[0] == '已入库'
    adapter.calls.clear()
    second = MusicLibrary(tmp_path, adapter=adapter)
    assert second.import_link('分享 https://music.163.com/#/song?id=90001&userid=1')[0] == '已在库里'
    assert adapter.calls == []


def test_same_hash_keeps_one_track_with_all_sources(tmp_path, synthetic_audio):
    library = MusicLibrary(tmp_path, adapter=Adapter(synthetic_audio))
    library.import_link('https://music.163.com/song?id=90001')
    assert library.import_link('https://douyin.com/music/90002')[0] == '已在库里'
    tracks = library.list_tracks()
    assert len(tracks) == len(list(library.root.glob('*/track.json'))) == 1
    assert {s['platform'] for s in tracks[0]['sources']} == {'netease', 'douyin'}
    from music_library.library import validate_track
    validate_track(tracks[0])


def test_partial_download_never_commits_or_leaves_partial(tmp_path, synthetic_audio):
    adapter = Adapter(synthetic_audio, fail=True)
    library = MusicLibrary(tmp_path, adapter=adapter)
    for _ in range(2):
        with pytest.raises(MusicError, match='下载到一半中断'):
            library.import_link('https://music.163.com/song?id=90001')
    assert adapter.calls == ['resolve', 'download']
    assert library.list_tracks() == []
    assert not (library.root / 'index.json').exists()
    assert not list(library.root.glob('.import-*'))
    assert not list(library.root.glob('**/*.part'))


def test_failed_index_commit_rolls_back_files(tmp_path, synthetic_audio, monkeypatch):
    library = MusicLibrary(tmp_path, adapter=Adapter(synthetic_audio))
    def fail(*args):
        raise OSError('synthetic disk full')
    monkeypatch.setattr(library, '_write_index', fail)
    with pytest.raises(MusicError):
        library.import_link('https://music.163.com/song?id=90001')
    assert library.list_tracks() == []
    assert not list(library.root.glob('*/track.json'))


def test_license_and_measurements(tmp_path, synthetic_audio):
    from music_library.library import validate_track, LICENSE_LABELS
    library = MusicLibrary(tmp_path)
    original = synthetic_audio.read_bytes()
    status, track = library.import_local(synthetic_audio)
    assert status == '已入库' and synthetic_audio.read_bytes() == original
    assert track['license_status'] == 'unknown'
    assert '发布前要确认' in LICENSE_LABELS['unknown']
    assert 2.9 < track['duration_seconds'] < 3.2
    assert track['sample_rate_hz'] == 44100
    assert track['loudness_lufs'] < 0
    assert track['bpm'] is track['beats'] is track['sections'] is None
    for field in ('license_status', 'duration_seconds', 'file_sha256'):
        bad = dict(track)
        del bad[field]
        with pytest.raises(MusicError):
            validate_track(bad)
    with pytest.raises(MusicError):
        validate_track({**track, 'license_status': 'cc_by', 'attribution': None})


def test_client_ncm_offline_then_direct_link_dedup(tmp_path):
    library = MusicLibrary(tmp_path, adapter=Adapter(None))
    before = (FIXTURES / 'synthetic.ncm').read_bytes()
    status, track = library.import_client_file(FIXTURES / 'synthetic.ncm')
    assert status == '已入库'
    assert track['platform'] == 'netease_client'
    assert track['platform_id'] == '90001' and track['title'] == '合成测试曲'
    assert library.import_client_file(FIXTURES / 'synthetic.ncm')[0] == '已在库里'
    assert library.import_link('https://music.163.com/song?id=90001')[0] == '已在库里'
    assert library.adapter.calls == []
    assert (FIXTURES / 'synthetic.ncm').read_bytes() == before


def test_client_no_id_hash_dedup(tmp_path, synthetic_audio):
    library = MusicLibrary(tmp_path)
    status, track = library.import_client_file(synthetic_audio)
    assert status == '已入库' and track['platform'] == 'netease_client'
    assert track['sources'][0]['kind'] == 'file'
    assert library.import_client_file(synthetic_audio)[0] == '已在库里'
    assert len(library.list_tracks()) == 1


def test_corrupt_ncm_keeps_original_and_no_library_entry(tmp_path):
    broken = tmp_path / 'broken.ncm'
    broken.write_bytes(b'CTENFDAM\0\0' + b'\xff' * 4)
    library = MusicLibrary(tmp_path)
    with pytest.raises(MusicError, match='损坏'):
        library.import_client_file(broken)
    assert broken.read_bytes() == b'CTENFDAM\0\0' + b'\xff' * 4
    assert library.list_tracks() == []
    assert not list(library.root.glob('.decode-*'))


def test_qr_only_auth_private_store(tmp_path, capsys):
    from music_library.netease import login_qr, read_session
    calls = []
    def request(path, params):
        calls.append(path)
        if len(calls) == 1:
            return {'code': 200, 'unikey': 'synthetic-qr'}, ''
        if len(calls) == 2:
            return {'code': 801}, ''
        return {'code': 803}, 'MUSIC_U=synthetic-login-value'
    display = []
    login_qr(request=request, display=display.append, sleep=lambda _: None, directory=tmp_path)
    assert display == ['https://music.163.com/login?codekey=synthetic-qr']
    assert read_session(tmp_path) == 'MUSIC_U=synthetic-login-value'
    assert (tmp_path / 'netease-session.json').stat().st_mode & 0o777 == 0o600
    assert capsys.readouterr().out == ''
    assert all('qrcode' in path for path in calls)


def test_auth_unreadable_not_absent(tmp_path):
    from music_library.netease import read_session
    assert read_session(tmp_path) == ''
    path = tmp_path / 'netease-session.json'
    path.write_text('{broken')
    path.chmod(0o600)
    with pytest.raises(MusicError, match='损坏.*不代表未登录'):
        read_session(tmp_path)
    path.write_text('{"cookie":"MUSIC_U=synthetic"}')
    path.chmod(0o644)
    with pytest.raises(MusicError, match='600'):
        read_session(tmp_path)


def test_qr_unknown_status_saves_nothing(tmp_path):
    from music_library.netease import login_qr
    def request(path, params):
        return ({'code': 200, 'unikey': 'synthetic'} if 'unikey' in path else {'code': 999}), ''
    with pytest.raises(MusicError, match='未知状态'):
        login_qr(request=request, display=lambda _: None, sleep=lambda _: None, directory=tmp_path)
    assert not (tmp_path / 'netease-session.json').exists()


def test_http_single_attempt_persistent_cache_and_corruption(tmp_path):
    import io
    from email.message import Message
    from music_library.cache import CachedHTTP
    class Response(io.BytesIO):
        code = 200
        headers = Message()
    Response.headers['Content-Type'] = 'audio/mpeg'
    class Opener:
        calls = 0
        def open(self, request, timeout):
            self.calls += 1
            assert 'Cookie' not in request.headers
            return Response(b'synthetic-body')
    opener = Opener()
    cache = CachedHTTP(tmp_path, opener=opener)
    assert cache.fetch('https://cdn.example.test/a')[2] == b'synthetic-body'
    assert CachedHTTP(tmp_path, opener=opener).fetch('https://cdn.example.test/a')[2] == b'synthetic-body'
    assert opener.calls == 1
    next(tmp_path.glob('*.body')).write_bytes(b'corrupted')
    with pytest.raises(MusicError, match='缓存.*损坏'):
        cache.fetch('https://cdn.example.test/a')
    assert opener.calls == 1


def test_http_midstream_failure_no_part_and_no_retry(tmp_path):
    from email.message import Message
    from music_library.cache import CachedHTTP
    class Response:
        code = 200
        headers = Message()
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            self.read = lambda _: (_ for _ in ()).throw(OSError('synthetic disconnect'))
            return b'partial'
    class Opener:
        calls = 0
        def open(self, *args, **kwargs):
            self.calls += 1
            return Response()
    opener = Opener()
    cache = CachedHTTP(tmp_path, opener=opener)
    for _ in range(2):
        with pytest.raises(MusicError):
            cache.fetch('https://cdn.example.test/a')
    assert opener.calls == 1
    assert not list(tmp_path.glob('*.part'))
    assert not list(tmp_path.glob('*.body'))


def test_http_redirect_never_forwards_cookie(tmp_path):
    import io
    from email.message import Message
    from music_library.cache import CachedHTTP
    class Response(io.BytesIO):
        def __init__(self, code, location=None):
            super().__init__(b'ok')
            self.code, self.headers = code, Message()
            if location: self.headers['Location'] = location
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            return Response(302, 'https://cdn.example.test/audio') if len(calls) == 1 else Response(200)
    cache = CachedHTTP(tmp_path, opener=Opener(), cookie_reader=lambda _: 'synthetic=value')
    cache.fetch('https://music.163.com/song?id=90001', cookies=True)
    assert calls[0].headers['Cookie'] == 'synthetic=value'
    assert 'Cookie' not in calls[1].headers
    cache.fetch('https://music.163.com/song?id=90001', cookies=True)
    assert len(calls) == 2
    assert all('synthetic=value' not in p.read_text() for p in tmp_path.glob('*.json'))


def test_duration_mismatch_cannot_import_preview(tmp_path, synthetic_audio):
    adapter = Adapter(synthetic_audio)
    original = adapter.resolve
    adapter.resolve = lambda link: {**original(link), 'expected_duration': 180}
    library = MusicLibrary(tmp_path, adapter=adapter)
    with pytest.raises(MusicError, match='试听片段'):
        library.import_link('https://music.163.com/song?id=90001')
    assert library.list_tracks() == []


def test_cli_batch_failures_do_not_stop_next_item(tmp_path, monkeypatch, capsys):
    from import_music import main
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path))
    result = main(['https://unknown.example.test/song/1', 'https://unknown.example.test/song/2', '--list'])
    output = capsys.readouterr().out
    assert result == 1 and output.count('失败：不支持的链接') == 2
    assert '暂无曲目' in output


def test_cli_folder_defaults_and_existing_ncm(tmp_path, monkeypatch, capsys):
    from import_music import main, parser
    monkeypatch.setenv('LOCAL_MEDIA_ROOT', str(tmp_path))
    assert parser().parse_args(['--from-folder']).from_folder == '~/Music/网易云音乐'
    assert main(['--from-folder', str(FIXTURES), '--list']) == 0
    assert '网易云客户端下载' in capsys.readouterr().out
    assert main(['--from-folder', str(FIXTURES)]) == 0
    assert '已在库里' in capsys.readouterr().out


def test_browser_cookie_decrypt_cbc_and_host_binding():
    from music_library.browser_cookies import decrypt_cookie
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from music_library.netease import aes_encrypt
    import hashlib
    host = '.example.test'
    key = PBKDF2HMAC(algorithm=hashes.SHA1(), length=16, salt=b'saltysalt', iterations=1003).derive(b'synthetic')
    encrypted = b'v10' + aes_encrypt(hashlib.sha256(host.encode()).digest() + b'test-value', key, b' ' * 16)
    assert decrypt_cookie(encrypted, b'synthetic', host, 24) == 'test-value'
    with pytest.raises(MusicError, match='无法解密'):
        decrypt_cookie(encrypted, b'synthetic', '.other.test', 24)
    with pytest.raises(MusicError, match='暂不支持'):
        decrypt_cookie(b'v99garbage', b'synthetic', host, 24)


def test_missing_platform_license_never_defaults_to_publishable(tmp_path, synthetic_audio):
    adapter = Adapter(synthetic_audio)
    resolve = adapter.resolve
    def missing_license(link):
        metadata = resolve(link)
        del metadata['license_status']
        return metadata
    adapter.resolve = missing_license
    library = MusicLibrary(tmp_path, adapter=adapter)
    with pytest.raises(MusicError):
        library.import_link('https://music.163.com/song?id=90001')
    assert library.list_tracks() == []


def test_shortlinks_use_cached_redirect_identity_without_refetch(tmp_path, monkeypatch):
    from music_library.platforms import PlatformAdapter
    from music_library.cache import request_cache_key, write_json
    class Pages:
        def fetch(self, *a, **k): pytest.fail('cached identity must avoid page requests')
    short = 'https://v.douyin.com/synthetic/'
    write_json(tmp_path / (request_cache_key(short) + '.json'),
               {'state': 'complete', 'status': 302, 'location': 'https://www.iesdouyin.com/share/note/80001/'})
    music = {'aweme_id': '80001', 'music': {'id': 90001, 'title': 'synthetic', 'duration': 180,
             'play_url': {'url_list': ['https://cdn.example.test/full.mp3']}}}
    monkeypatch.setattr('music_library.douyin_share.work_detail', lambda *a, **k: music)
    adapter = PlatformAdapter(tmp_path, http=Pages())
    assert adapter.resolve(parse_link(short))['platform_id'] == '90001'
    assert parse_link('https://www.iesdouyin.com/share/note/80001').kind == 'note'


def test_hls_local_remux_uses_cached_segment_once(tmp_path, synthetic_audio):
    import subprocess
    from music_library.platforms import PlatformAdapter
    from music_library.audio import measure_audio
    segment = tmp_path / 'segment.ts'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(synthetic_audio), '-c:a', 'aac', '-f', 'mpegts', str(segment)], check=True)
    class HTTP:
        calls = []
        def fetch(self, url):
            self.calls.append(url)
            return url, 'video/mp2t', segment.read_bytes()
    http = HTTP()
    target = tmp_path / 'output.m4a'
    PlatformAdapter(tmp_path, http=http).download_hls('https://cdn.example.test/list.m3u8',
        b'#EXTM3U\n#EXTINF:3\na.ts\n#EXT-X-ENDLIST\n', target)
    assert http.calls == ['https://cdn.example.test/a.ts']
    assert 2.9 < measure_audio(target)['duration_seconds'] < 3.2
    assert not target.with_suffix('.segments').exists()


@pytest.mark.parametrize('body', [b'#EXTM3U\n#EXTINF:3\na.ts\n',
                                 b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128\na.ts\n#EXT-X-ENDLIST'])
def test_live_or_encrypted_hls_never_fetches_segments(tmp_path, body):
    from music_library.platforms import PlatformAdapter
    class HTTP:
        def fetch(self, *args):
            raise AssertionError('must not fetch protected or live segments')
    with pytest.raises(MusicError, match='暂不支持'):
        PlatformAdapter(tmp_path, http=HTTP()).download_hls('https://cdn.example.test/a.m3u8', body, tmp_path/'out.m4a')


def test_locked_empty_config_redirect_does_not_store_auth_in_repo(tmp_path, monkeypatch):
    from music_library.netease import config_dir
    (tmp_path / '.git').mkdir()
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    with pytest.raises(MusicError, match='仓库外'):
        config_dir()


def test_duration_difference_above_two_seconds_rejected_even_for_long_song(tmp_path, synthetic_audio):
    adapter = Adapter(synthetic_audio)
    original = adapter.resolve
    adapter.resolve = lambda link: {**original(link), 'expected_duration': 300}
    library = MusicLibrary(tmp_path, adapter=adapter, measure=lambda p: {'duration_seconds': 302.1, 'sample_rate_hz': 44100,
                                                                     'loudness_lufs': -14, 'loudness_status': 'measured'})
    with pytest.raises(MusicError, match='时长.*不符'):
        library.import_link('https://music.163.com/song?id=90001')
    assert library.list_tracks() == []
