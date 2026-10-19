"""Synthetic iPhone SSR responses; redirects and signatures cannot open sockets."""
import io
import json
import sys
from pathlib import Path
from email.message import Message
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from music_library.cache import CachedHTTP
from music_library.errors import MusicError
from music_library.links import parse_link
from music_library.platforms import PlatformAdapter
FIXTURES=Path(__file__).parent/'fixtures/music-library'

@pytest.fixture(autouse=True)
def offline(monkeypatch):
    import socket
    def forbidden(*a,**k): raise AssertionError('offline test cannot open sockets')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'getaddrinfo',forbidden)

class Response(io.BytesIO):
    def __init__(self,body,code=200):
        super().__init__(body);self.code=code;self.headers=Message()
        self.headers['Content-Type']='text/html'
        self.headers['Content-Length']=str(len(body))
        if code==302:self.headers['Location']='https://www.douyin.com/note/80001'


@pytest.mark.parametrize('kind', ['note', 'video'])
def test_share_page_iphone_anonymous_extracts_exact_work_music(tmp_path,monkeypatch,kind):
    calls=[]
    class Opener:
        def open(self,request,timeout):
            calls.append(request)
            assert request.full_url==f'https://www.iesdouyin.com/share/{kind}/80001/'
            assert 'iPhone' in request.get_header('User-agent') and 'Safari' in request.get_header('User-agent')
            assert not request.has_header('Cookie')
            return Response((FIXTURES/'douyin-share-note.html').read_bytes())
    monkeypatch.setattr('music_library.douyin_api.music_detail',lambda *a,**k:pytest.fail('signature path must not run'))
    http=CachedHTTP(tmp_path,opener=Opener(),cookie_reader=lambda _:pytest.fail('must not read browser'))
    adapter=PlatformAdapter(tmp_path,http=http,browser='chrome')
    result=adapter.resolve(parse_link(f'https://www.douyin.com/{kind}/80001'))
    assert result['platform_id']=='90001' and result['title']=='合成图文原声'
    assert result['url']=='https://cdn.example.test/full.mp3' and result['expected_duration']==3
    http.allow_network=False
    assert adapter.resolve(parse_link(f'https://www.douyin.com/{kind}/80001'))==result
    assert len(calls)==1


def test_share_redirect_is_cached_but_never_followed(tmp_path):
    calls=[]
    class Opener:
        def open(self,request,timeout):
            calls.append(request.full_url)
            return Response(b'',302)
    http=CachedHTTP(tmp_path,opener=Opener())
    adapter=PlatformAdapter(tmp_path,http=http)
    for _ in range(2):
        with pytest.raises(MusicError,match='302.*未跟随'):
            adapter.resolve(parse_link('https://www.douyin.com/note/80001'))
    assert calls==['https://www.iesdouyin.com/share/note/80001/']
    assert len(list(tmp_path.glob('*.json')))==1


def test_share_parser_rejects_unreadable_wrong_work_and_ambiguous_payload(tmp_path):
    from music_library.douyin_share import parse_router_data
    for body in ['<script>window.acrawler=true</script>','<script>window._ROUTER_DATA=not_json()</script>']:
        with pytest.raises(MusicError,match='分享页.*无法读取'):
            parse_router_data(body)
    data=json.loads('{"aweme_id":"80002","music":{"id":90001,"title":"wrong"}}')
    with pytest.raises(MusicError,match='无法确认'):
        PlatformAdapter(tmp_path).douyin(parse_link('https://www.douyin.com/note/80001'),'https://www.douyin.com/note/80001',data)


def test_new_shortlink_stops_at_redirect_then_requests_iphone_ssr_once(tmp_path):
    calls=[]
    class Opener:
        def open(self,request,timeout):
            calls.append(request.full_url)
            if request.full_url=='https://v.douyin.com/synthetic/':
                response=Response(b'',302)
                response.headers.replace_header('Location','https://www.iesdouyin.com/share/note/80001/')
                return response
            assert request.full_url=='https://www.iesdouyin.com/share/note/80001/'
            assert 'iPhone' in request.get_header('User-agent')
            return Response((FIXTURES/'douyin-share-note.html').read_bytes())
    adapter=PlatformAdapter(tmp_path,http=CachedHTTP(tmp_path,opener=Opener()))
    assert adapter.resolve(parse_link('https://v.douyin.com/synthetic/'))['platform_id']=='90001'
    assert len(calls)==2


def test_router_page_config_without_music_never_becomes_success(tmp_path):
    class Opener:
        def open(self,*a,**k):
            return Response(b'<script>window._ROUTER_DATA={"loaderData":{"note_(id)/page":{"itemId":"80001","renderInSSR":1}},"errors":null};</script>')
    adapter=PlatformAdapter(tmp_path,http=CachedHTTP(tmp_path,opener=Opener()))
    with pytest.raises(MusicError,match='无法确认.*作品.*原声'):
        adapter.resolve(parse_link('https://www.douyin.com/note/80001'))
