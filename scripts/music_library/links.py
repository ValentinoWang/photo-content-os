import html
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlsplit

from .errors import MusicError


@dataclass(frozen=True)
class Link:
    platform: str
    kind: str
    platform_id: str | None
    url: str

    @property
    def key(self):
        return f'{self.platform}:{self.kind}:{self.platform_id or self.url}'


def parse_link(text: str) -> Link:
    urls = re.findall(r'https?://[^\s<>"\u300a\u300b]+', html.unescape(text))
    if len(urls) != 1:
        raise MusicError('不支持的链接：每条输入请只放一首歌或一个视频的分享链接')
    url = urls[0].rstrip("。，、；！？.,;!?)）]}'\"")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise MusicError('不支持的链接') from exc
    if parsed.username or parsed.password or port not in (None, 443, 80):
        raise MusicError('不支持的链接')
    host = (parsed.hostname or '').lower()
    path = parsed.path.rstrip('/')
    query = parse_qs(parsed.query)
    if host in ('music.163.com', 'www.music.163.com', 'y.music.163.com'):
        if parsed.fragment:
            fragment = urlsplit('/' + parsed.fragment.lstrip('/'))
            path, query = fragment.path.rstrip('/'), parse_qs(fragment.query)
        if path in ('/song', '/m/song') and re.fullmatch(r'\d+', query.get('id', [''])[0]):
            identity = query['id'][0]
            return Link('netease', 'song', identity, f'https://music.163.com/song?id={identity}')
    if host == '163cn.tv' and re.fullmatch(r'/[\w-]+', path):
        return Link('netease', 'share', None, f'https://163cn.tv{path}')
    if host in ('douyin.com', 'www.douyin.com', 'iesdouyin.com', 'www.iesdouyin.com'):
        match = re.fullmatch(r'/(?:share/)?(music|video|note)/(\d+)', path)
        if match:
            kind, identity = match.groups()
            return Link('douyin', kind, identity, f'https://www.douyin.com/{kind}/{identity}')
    if host == 'v.douyin.com' and re.fullmatch(r'/[\w-]+', path):
        return Link('douyin', 'share', None, f'https://v.douyin.com{path}/')
    if host in ('qishui.douyin.com', 'music.douyin.com', 'qishui.com', 'www.qishui.com'):
        match = re.search(r'/(?:track|song)/([\w-]+)$', path)
        identity = match.group(1) if match else (query.get('track_id') or query.get('song_id') or [None])[0]
        if identity and re.fullmatch(r'[\w-]+', identity):
            return Link('qishui', 'song', identity, f'https://{host}{path}?' + urlencode({'track_id': identity}))
        if re.fullmatch(r'/(?:s|c)/[\w-]+', path):
            return Link('qishui', 'share', None, f'https://{host}{path}/')
    raise MusicError('不支持的链接')
