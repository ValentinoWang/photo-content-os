"""Anonymous signed detail path, with no browser state or platform sockets."""
import io
import json
import sys
from pathlib import Path
from email.message import Message
from urllib.parse import urlsplit, parse_qs
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.cache import CachedHTTP
from music_library.errors import MusicError
from music_library.douyin_api import music_detail as detail, REGISTER


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket
    def forbidden(*a, **k): raise AssertionError('offline tests cannot open sockets')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


class Response(io.BytesIO):
    def __init__(self, payload, register=False):
        super().__init__(json.dumps(payload).encode())
        self.code, self.headers = 200, Message()
        self.headers['Content-Type'] = 'application/json'
        if register: self.headers['Set-Cookie'] = 'ttwid=synthetic-anonymous; Path=/; Secure'


@pytest.mark.parametrize('kind', ['music'])
def test_signature_registration_detail_once_and_cached_replay(tmp_path, kind):
    from music_library.platforms import PlatformAdapter
    from music_library.links import parse_link
    calls = []
    music = {'id': 90001, 'title': 'synthetic', 'author': 'synth', 'duration': 180,
             'play_url': {'url_list': ['https://cdn.example.test/full.mp3']}}
    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            if request.full_url == REGISTER:
                assert not request.has_header('Cookie')
                return Response({'status_code': 0}, True)
            from http.cookies import SimpleCookie
            jar = SimpleCookie(); jar.load(request.get_header('Cookie'))
            assert jar['ttwid'].value == 'synthetic-anonymous'
            query = parse_qs(urlsplit(request.full_url).query, keep_blank_values=True)
            assert len(query['msToken'][0]) == 184
            assert jar['msToken'].value == query['msToken'][0]
            assert set(jar) == {'ttwid', 'msToken'}
            assert 'a_bogus' in parse_qs(urlsplit(request.full_url).query)
            return Response({'music_info': music} if kind == 'music' else
                            {'aweme_detail': {'aweme_id': '80001', 'music': music}})
    http = CachedHTTP(tmp_path, opener=Opener(), cookie_reader=lambda _: pytest.fail('must not read browser'))
    adapter = PlatformAdapter(tmp_path, http=http, browser='chrome')
    url = f'https://www.douyin.com/{kind}/' + ('90001' if kind == 'music' else '80001')
    first = adapter.resolve(parse_link(url))
    http.allow_network = False
    assert adapter.resolve(parse_link(url)) == first
    assert first['expected_duration'] == 180 and first['platform_id'] == '90001'
    assert len(calls) == 2
    assert (tmp_path / '.douyin-anonymous/anonymous.json').stat().st_mode & 0o777 == 0o600


def test_login_required_is_explicit_and_not_retried(tmp_path):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            return Response({'ok': True}, True) if request.full_url == REGISTER else Response({'status_code': 2483})
    http = CachedHTTP(tmp_path, opener=Opener())
    for _ in range(2):
        with pytest.raises(MusicError, match='要求登录态.*未读取'):
            detail(http, '80001')
    assert len(calls) == 2


def test_unknown_empty_payload_never_claims_login_required(tmp_path):
    class Opener:
        def open(self, request, timeout):
            return Response({}, request.full_url == REGISTER)
    with pytest.raises(MusicError, match='原因未确认'):
        detail(CachedHTTP(tmp_path, opener=Opener()), '80001')


def test_registration_cache_reused_after_anonymous_plan_upgrade(tmp_path):
    from music_library.douyin_api import AnonymousOpener, REGISTER_DATA
    private = tmp_path / '.douyin-anonymous'
    private.mkdir()
    token_path = private / 'anonymous.json'
    old_plan = private / 'work-80001.json'
    old_plan.write_text('{"url":"https://www.douyin.com/old?msToken="}')
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            return Response({'ok': True}, True) if request.full_url == REGISTER else Response({'music_info': {'id': '80001'}})
    opener = Opener()
    http = CachedHTTP(tmp_path, opener=AnonymousOpener(opener, token_path))
    http.fetch(REGISTER, REGISTER_DATA)
    http.opener = opener
    assert detail(http, '80001')['id'] == '80001'
    assert calls.count(REGISTER) == 1 and len(calls) == 2
    assert old_plan.read_text() == '{"url":"https://www.douyin.com/old?msToken="}'
