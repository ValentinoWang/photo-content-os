"""Exercise the pinned musicdl parser/writer with synthetic cached HTTP responses."""
import io
import json
import sys
from email.message import Message
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.cache import CachedHTTP
from music_library.errors import MusicError, MemberRequired
from music_library.library import MusicLibrary
from music_library.platforms import PlatformAdapter

FIXTURES = Path(__file__).parent / 'fixtures/music-library'


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError('offline tests cannot open sockets')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)


@pytest.fixture
def audio(tmp_path):
    from music_library.client_files import decode_ncm
    path, _ = decode_ncm(FIXTURES / 'synthetic.ncm', tmp_path)
    return path.read_bytes()


class Response(io.BytesIO):
    def __init__(self, body, content_type, code=200, location=None):
        super().__init__(body)
        self.code, self.headers = code, Message()
        self.headers['Content-Type'] = content_type
        self.headers['Content-Length'] = str(len(body))
        if location:
            self.headers['Location'] = location


class RecordedOpener:
    def __init__(self, audio, *, member=False, trial=False, search=None):
        self.audio, self.member, self.trial, self.search = audio, member, trial, search
        self.calls = []

    def open(self, request, timeout):
        url = request.full_url
        self.calls.append((request.get_method(), url))
        if '163cn.tv' in url:
            return Response(b'', 'text/html', 302, 'https://music.163.com/song?id=90001')
        if 'qishui.douyin.com/s/' in url:
            return Response(b'', 'text/html', 302, 'https://music.douyin.com/qishui/share/track?track_id=90001')
        if '/song?id=' in url:
            return Response(b'<html></html>', 'text/html')
        if '/api/v3/song/detail' in url:
            detail = json.loads((FIXTURES / 'netease-free-detail.json').read_text())
            detail['songs'][0]['fee'] = 1 if self.member else 0
            return Response(json.dumps(detail).encode(), 'application/json')
        if '/eapi/song/enhance/player/url/v1' in url:
            result = json.loads((FIXTURES / ('netease-member-player.json' if self.trial else 'netease-full-player.json')).read_text())
            return Response(json.dumps(result).encode(), 'application/json')
        if '/luna/search/track?' in url:
            return Response(json.dumps({'result_groups': [{'data': self.search or []}]}).encode(), 'application/json')
        if '/qishui/share/track?' in url:
            return Response((FIXTURES / 'qishui.html').read_bytes(), 'text/html')
        if 'cdn.example.test/full.mp3' in url:
            return Response(self.audio, 'audio/mpeg')
        raise AssertionError('unapproved request: ' + url)


def library(tmp_path, opener):
    http = CachedHTTP(tmp_path / 'http', opener=opener)
    return MusicLibrary(tmp_path, adapter=PlatformAdapter(tmp_path / 'unused', http=http)), http


def test_musicdl_qishui_single_page_single_audio_and_duplicate_zero_network(tmp_path, audio):
    opener = RecordedOpener(audio)
    lib, http = library(tmp_path, opener)
    status, track = lib.import_link('https://qishui.douyin.com/s/synthetic/')
    assert status == '已入库' and track['title'] == '合成汽水曲'
    assert len(opener.calls) == 3  # short-link redirect, share page, full audio; no extra HEAD/lyrics/cover.
    before = http.network_calls
    assert lib.import_link('https://qishui.douyin.com/s/synthetic/')[0] == '已在库里'
    assert lib.import_link('https://music.douyin.com/qishui/share/track?track_id=90001')[0] == '已在库里'
    assert http.network_calls == before


def test_musicdl_netease_exact_request_budget_and_cached_replay(tmp_path, audio):
    opener = RecordedOpener(audio)
    lib, http = library(tmp_path, opener)
    assert lib.import_link('https://163cn.tv/synthetic/')[0] == '已入库'
    assert len(opener.calls) == 5  # short-link, song page, details, one standard URL, one media GET.
    assert len([url for _, url in opener.calls if '/eapi/' in url]) == 1
    assert not any('lyric' in url or 'cover' in url for _, url in opener.calls)
    before = http.network_calls
    assert lib.import_link('https://music.163.com/song?id=90001')[0] == '已在库里'
    assert http.network_calls == before
    http.allow_network = False
    # Full engine replay uses the same cache even with a fresh engine/client instance.
    other = PlatformAdapter(tmp_path / 'unused', http=http)
    assert other.resolve(__import__('music_library.links', fromlist=['parse_link']).parse_link('https://music.163.com/song?id=90001'))['title'] == '合成测试曲'
    assert http.network_calls == before


@pytest.mark.parametrize('member,trial,budget', [(True, False, 1), (False, True, 2)])
def test_musicdl_member_and_trial_never_download_media(tmp_path, audio, member, trial, budget):
    opener = RecordedOpener(audio, member=member, trial=trial)
    lib, http = library(tmp_path, opener)
    with pytest.raises(MemberRequired, match='你的账号不是会员.*--search-elsewhere'):
        lib.import_link('https://music.163.com/song?id=90001')
    assert len(opener.calls) == budget
    assert lib.list_tracks() == []
    with pytest.raises(MusicError, match='本地失败缓存'):
        lib.import_link('https://music.163.com/song?id=90001')
    assert len(opener.calls) == budget


def candidate(identity='90001', title='合成测试曲', artist='合成歌手'):
    return {'entity': {'track': {'id': identity, 'name': title, 'artists': [{'name': artist}]}}}


def test_search_only_with_flag_once_and_exact_match(tmp_path, audio):
    opener = RecordedOpener(audio, member=True, search=[candidate(title='差不多的歌'), candidate()])
    lib, http = library(tmp_path, opener)
    url = 'https://music.163.com/song?id=90001'
    with pytest.raises(MemberRequired):
        lib.import_link(url)
    assert len(opener.calls) == 1
    status, track = lib.import_link(url, search_elsewhere=True)
    assert status == '已入库' and track['platform'] == 'qishui'
    assert len([url for _, url in opener.calls if '/luna/search/track?' in url]) == 1
    assert len(opener.calls) == 4  # cached member detail, one search, share page, audio.
    assert lib.import_link(url, search_elsewhere=True)[0] == '已在库里'
    assert len(opener.calls) == 4


def test_search_mismatch_stops_and_never_uses_approximation(tmp_path, audio):
    opener = RecordedOpener(audio, member=True, search=[candidate(artist='另一位歌手')])
    lib, _ = library(tmp_path, opener)
    url = 'https://music.163.com/song?id=90001'
    for _ in range(2):
        with pytest.raises(MusicError, match='没找到同一首'):
            lib.import_link(url, search_elsewhere=True)
    assert len(opener.calls) == 2  # one detail, one search; no media or repeat.
    assert lib.list_tracks() == []


def test_error_response_cached_and_offline_cache_miss_never_opens_socket(tmp_path):
    class ErrorOpener:
        calls = 0
        def open(self, *args, **kwargs):
            self.calls += 1
            return Response(b'{"error":"synthetic refusal"}', 'application/json', 403)
    opener = ErrorOpener()
    http = CachedHTTP(tmp_path, opener=opener)
    for _ in range(2):
        with pytest.raises(MusicError, match='响应已缓存'):
            http.fetch('https://cdn.example.test/refused')
    assert opener.calls == 1
    assert next(tmp_path.glob('*.body')).read_bytes() == b'{"error":"synthetic refusal"}'
    http.allow_network = False
    with pytest.raises(MusicError, match='缓存不足'):
        http.fetch('https://cdn.example.test/not-recorded')
    assert opener.calls == 1


def test_region_restriction_detected_before_player_request_or_media(tmp_path, audio):
    class RegionalOpener(RecordedOpener):
        def open(self, request, timeout):
            if '/api/v3/song/detail' in request.full_url:
                self.calls.append((request.get_method(), request.full_url))
                result = json.loads((FIXTURES / 'netease-free-detail.json').read_text())
                result['privileges'] = [{'id': 90001, 'st': -100, 'pl': 0, 'dl': 0,
                                         'freeTrialPrivilege': {'cannotListenReason': 1}}]
                return Response(json.dumps(result).encode(), 'application/json')
            return super().open(request, timeout)
    opener = RegionalOpener(audio)
    lib, _ = library(tmp_path, opener)
    with pytest.raises(MusicError, match='网络不在大陆.*大陆网络导入'):
        lib.import_link('https://music.163.com/song?id=90001')
    assert len(opener.calls) == 1
    assert lib.list_tracks() == []
    record = json.loads(next((lib.root / '.attempts').glob('*.json')).read_text())
    assert record['failure']['failure_class'] == 'region_restricted'


def test_qishui_redirect_page_reused_as_musicdl_input_without_http_aliasing(tmp_path, audio):
    class TrackingOpener(RecordedOpener):
        def open(self, request, timeout):
            if 'qishui.douyin.com/s/' in request.full_url:
                self.calls.append((request.get_method(), request.full_url))
                return Response(b'', 'text/html', 302,
                                'https://music.douyin.com/qishui/share/track?track_id=90001&auto_play_bgm=1')
            return super().open(request, timeout)
    opener = TrackingOpener(audio)
    lib, _ = library(tmp_path, opener)
    assert lib.import_link('https://qishui.douyin.com/s/synthetic/')[0] == '已入库'
    assert len(opener.calls) == 3
    assert any('auto_play_bgm=1' in url for _, url in opener.calls)
    assert not any(url.endswith('/qishui/share/track?track_id=90001') for _, url in opener.calls)
