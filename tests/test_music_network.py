"""Offline regressions for URL caching, region messages and explicit proxies."""
import io
import json
import ssl
import sys
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.cache import CachedHTTP
from music_library.errors import MusicError


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('offline tests cannot open sockets')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


class Response(io.BytesIO):
    def __init__(self, body=b'', code=200, location=None):
        super().__init__(body)
        self.code, self.headers = code, Message()
        self.headers['Content-Type'] = 'text/html'
        self.headers['Content-Length'] = str(len(body))
        if location:
            self.headers['Location'] = location


def test_douyin_share_note_redirect_has_distinct_http_nodes(tmp_path):
    urls = ['https://v.douyin.com/synthetic/',
            'https://www.iesdouyin.com/share/note/80001/?from_ssr=1',
            'https://www.douyin.com/note/80001?previous_page=web_code_link']
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            index = urls.index(request.full_url)
            return Response(b'final SSR') if index == 2 else Response(code=302, location=urls[index + 1])
    cache = CachedHTTP(tmp_path, opener=Opener())
    assert cache.fetch(urls[0])[2] == b'final SSR'
    assert calls == urls
    assert len(list(tmp_path.glob('*.json'))) == 3
    cache.allow_network = False
    assert cache.fetch(urls[0])[2] == b'final SSR'
    assert calls == urls


def test_region_message_precedes_member_message():
    from music_library.musicdl_engine import check_region
    from music_library.errors import REGION_MESSAGE
    detail = {'id': 90001, 'fee': 1}
    payload = {'privileges': [{'id': 90001, 'st': -100, 'pl': 0, 'dl': 0}]}
    with pytest.raises(MusicError) as error:
        check_region(detail, payload)
    assert str(error.value) == REGION_MESSAGE
    assert '会员' not in str(error.value) and '版权' not in str(error.value)


def test_proxy_failure_never_falls_back_to_direct(tmp_path, monkeypatch):
    import requests
    from music_library.network import MusicOpener
    calls = []
    class Session:
        def __init__(self): self.trust_env = True
        def mount(self, *args): pass
        def request(self, **kwargs):
            calls.append(kwargs)
            raise requests.exceptions.ProxyError('synthetic proxy failure')
    monkeypatch.setenv('CONTENT_OS_MUSIC_PROXY', 'socks5h://127.0.0.1:19999')
    session = Session()
    opener = MusicOpener(session=session)
    cache = CachedHTTP(tmp_path, opener=opener)
    for _ in range(2):
        with pytest.raises(MusicError, match='代理.*未.*直连'):
            cache.fetch('https://cdn.example.test/audio')
    assert len(calls) == 1
    assert calls[0]['proxies'] == {'http': 'socks5h://127.0.0.1:19999', 'https': 'socks5h://127.0.0.1:19999'}
    assert session.trust_env is False


@pytest.mark.parametrize('privilege', [
    {'st': -100}, {'freeTrialPrivilege': {'cannotListenReason': 1}},
])
def test_region_fields_independently_trigger_precise_message(privilege):
    from music_library.musicdl_engine import check_region
    with pytest.raises(MusicError, match='当前所在地区.*网络不在大陆.*大陆网络导入'):
        check_region({'id': 90001}, {'privileges': [{'id': 90001, **privilege}]})


def test_other_song_region_and_malformed_permissions_do_not_masquerade_as_absence():
    from music_library.musicdl_engine import check_region
    check_region({'id': 90001}, {'privileges': [{'id': 90002, 'st': -100}]})
    with pytest.raises(MusicError, match='权限响应无法读取'):
        check_region({'id': 90001}, {'privileges': {}})


@pytest.mark.parametrize('exception,category', [
    (TimeoutError('synthetic timeout'), 'timeout'),
    (ConnectionResetError(54, 'synthetic reset'), 'connection_reset'),
    (urllib.error.URLError(ssl.SSLError('sensitive=must-not-be-saved')), 'tls'),
])
def test_network_exception_type_persisted_in_http_and_import_attempt(tmp_path, exception, category):
    from music_library.library import MusicLibrary
    from music_library.platforms import PlatformAdapter
    class Opener:
        calls = 0
        def open(self, *args, **kwargs):
            self.calls += 1
            raise exception
    opener = Opener()
    http = CachedHTTP(tmp_path / 'http', opener=opener)
    lib = MusicLibrary(tmp_path, adapter=PlatformAdapter(tmp_path / 'unused', http=http))
    for _ in range(2):
        with pytest.raises(MusicError):
            lib.import_link('https://www.douyin.com/note/80001')
    assert opener.calls == 1
    request_record = json.loads(next((tmp_path / 'http').glob('*.json')).read_text())
    attempt_record = json.loads(next((lib.root / '.attempts').glob('*.json')).read_text())
    assert request_record['failure']['failure_class'] == category
    assert attempt_record['failure']['failure_class'] == category
    assert request_record['failure']['exception_types']
    assert 'sensitive=' not in json.dumps(request_record)
    assert not list((tmp_path / 'http').glob('*.part'))


def test_proxy_default_off_ignores_ambient_environment(monkeypatch):
    from music_library.network import MusicOpener
    monkeypatch.delenv('CONTENT_OS_MUSIC_PROXY', raising=False)
    monkeypatch.setenv('HTTPS_PROXY', 'http://unrelated.invalid:1234')
    class CookieJar:
        clears = 0
        def clear(self): self.clears += 1
    class Session:
        def __init__(self): self.calls, self.cookies = [], CookieJar()
        def mount(self, *args): pass
        def request(self, **kwargs):
            self.calls.append(kwargs)
            class Result:
                status_code = 200
                headers = {}
                raw = None
            return Result()
    session = Session()
    opener = MusicOpener(session=session)
    import urllib.request
    opener.open(urllib.request.Request('https://cdn.example.test/audio'), timeout=1)
    assert opener.proxy == '' and session.trust_env is False
    assert session.calls[0]['proxies'] == {}
    assert session.calls[0]['allow_redirects'] is False
    assert session.cookies.clears == 2


def test_invalid_proxy_never_creates_a_direct_fallback(monkeypatch):
    from music_library.network import MusicOpener
    monkeypatch.setenv('CONTENT_OS_MUSIC_PROXY', 'invalid-protocol://127.0.0.1:9000')
    with pytest.raises(MusicError, match='代理配置无效.*未.*直连'):
        MusicOpener()


def test_request_scope_refusal_happens_before_attempt_or_socket(tmp_path):
    class ScopedOpener:
        def check_request(self, request):
            raise MusicError('超出本轮请求范围')
        def open(self, *args, **kwargs):
            raise AssertionError('must not open a refused request')
    cache = CachedHTTP(tmp_path, opener=ScopedOpener())
    with pytest.raises(MusicError, match='超出本轮请求范围'):
        cache.fetch('https://cdn.example.test/not-authorized')
    assert cache.network_calls == 0
    assert not list(tmp_path.glob('*.json'))


def test_incomplete_response_records_lengths_and_keeps_no_partial_file(tmp_path):
    class Opener:
        calls = 0
        def open(self, request, timeout):
            self.calls += 1
            response = Response(b'123')
            response.headers.replace_header('Content-Length', '10')
            return response
    opener = Opener()
    http = CachedHTTP(tmp_path, opener=opener)
    for _ in range(2):
        with pytest.raises(MusicError, match='没有下载完整'):
            http.fetch('https://cdn.example.test/truncated')
    assert opener.calls == 1
    record = json.loads(next(tmp_path.glob('*.json')).read_text())
    assert record['status'] == 200
    assert record['failure'] == {'failure_class': 'incomplete_response', 'expected_bytes': 10,
                                 'received_bytes': 3, 'exception_types': ['ContentLengthMismatch']}
    assert not list(tmp_path.glob('*.part')) and not list(tmp_path.glob('*.body'))


def test_egress_netease_matches_musicdl_native_form_request(tmp_path, monkeypatch):
    import requests
    from musicdl.modules.sources.netease import NeteaseMusicClient
    from music_library.musicdl_engine import clients
    from music_library.egress import TunnelOpener
    from music_library.network import MusicOpener
    payload = {'code': 200, 'songs': [{'id': 90001, 'name': 'synthetic'}]}
    def response():
        result = requests.Response()
        result.status_code = 200
        result._content = json.dumps(payload).encode()
        return result
    native_requests, egress_requests = [], []
    native = NeteaseMusicClient.__new__(NeteaseMusicClient)
    def native_post(url, data=None, **kwargs):
        native_requests.append(requests.Request('POST', url, data=data, **kwargs).prepare())
        return response()
    native.post = native_post
    assert native._getsongmetainfo(90001)['id'] == 90001
    class Raw(io.BytesIO):
        headers = {}
        def read(self, size=-1, decode_content=False): return super().read(size)
    class Session(requests.Session):
        def send(self, request, **kwargs):
            egress_requests.append(request)
            assert kwargs['proxies'] == {'https': 'socks5h://127.0.0.1:19000', 'http': 'socks5h://127.0.0.1:19000'}
            result = response()
            result.raw = Raw(result.content)
            result.headers = {'Content-Type': 'application/json'}
            return result
    class Tunnel:
        proxy = 'socks5h://127.0.0.1:19000'
        def start(self): pass
        def ensure_alive(self): pass
    monkeypatch.setattr('music_library.egress.MusicOpener', lambda proxy: MusicOpener(session=Session(), proxy=proxy))
    http = CachedHTTP(tmp_path, opener=TunnelOpener(Tunnel()))
    _, client = clients(http)
    assert client._getsongmetainfo(90001)['id'] == 90001
    expected, actual = native_requests[0], egress_requests[0]
    assert actual.method == expected.method == 'POST'
    assert actual.url == expected.url
    assert actual.body == expected.body.encode()
    assert actual.headers.get('Content-Type') == expected.headers['Content-Type'] == 'application/x-www-form-urlencoded'
    assert actual.headers['Content-Length'] == expected.headers['Content-Length']
    assert 'Cookie' not in actual.headers and 'Cookie' not in expected.headers


def test_transport_preserves_explicit_json_content_type():
    from music_library.network import MusicOpener
    import urllib.request
    captured = []
    class Session:
        def mount(self, *a): pass
        def request(self, **kwargs):
            captured.append(kwargs)
            class Result:
                status_code, headers, raw = 200, {}, None
            return Result()
    MusicOpener(session=Session(), proxy='').open(urllib.request.Request('https://example.test/api', data=b'{}',
        headers={'Content-Type': 'application/json; charset=utf-8'}), timeout=1)
    headers = {k.lower(): v for k, v in captured[0]['headers'].items()}
    assert headers['content-type'] == 'application/json; charset=utf-8'


def test_gateway_timeout_is_server_failure_not_invalid_link(tmp_path):
    class Opener:
        def open(self, *a, **k): return Response(b'<title>504 Gateway Time-out</title>', code=504)
    from music_library.errors import NetworkFailure
    http = CachedHTTP(tmp_path, opener=Opener())
    for _ in range(2):
        with pytest.raises(NetworkFailure, match='504.*服务端.*未重试') as error:
            http.fetch('https://www.douyin.com/aweme/v1/web/aweme/detail/?synthetic=1')
        assert error.value.diagnostic == {'failure_class': 'http_server_error', 'http_status': 504}
    assert http.network_calls == 1
