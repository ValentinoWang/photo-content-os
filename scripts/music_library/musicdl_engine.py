"""Bounded musicdl 2.14.2 integration for the course's local music library.

Netease parser adapted from CharlesPikachu/musicdl's official API parser,
Copyright (c) 2018–2026 CharlesPikachu, PolyForm Noncommercial 1.0.0.
Full license: musicdl.LICENSE. Changes: one standard quality, no lyrics/covers,
no third-party parsers, no retries, persistent cached transport.
"""
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from urllib.parse import urlencode, urlsplit
import unicodedata
import re

from .errors import MusicError, MemberRequired, RegionRestricted


def check_region(detail, payload):
    privileges = payload.get('privileges', [])
    if not isinstance(privileges, list):
        raise MusicError('网易云播放权限响应无法读取，未判定为会员或版权问题')
    candidates = [detail.get('privilege') or {}, detail]
    candidates.extend(p for p in privileges if isinstance(p, dict) and str(p.get('id')) == str(detail.get('id')))
    for privilege in candidates:
        if not isinstance(privilege, dict):
            raise MusicError('网易云播放权限格式无效，未入库')
        trial = privilege.get('freeTrialPrivilege') or {}
        if not isinstance(trial, dict):
            raise MusicError('网易云地区权限格式无效，未入库')
        if privilege.get('st') == -100 or trial.get('cannotListenReason') == 1:
            raise RegionRestricted()


def exact_text(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value)).casefold().split())


def exact_artists(value):
    return {exact_text(part) for part in re.split(r'\s*[/,、，&]\s*', str(value)) if part.strip()}


class QuietLogger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class CachedClient:
    """Replace musicdl's retrying sessions with the project-owned cache."""
    def __init__(self, http):
        self.http = http
        self.failure = None
        self.last_response = None
        self.prefetched_pages = {}
        self.default_headers = self.default_search_headers = self.default_download_headers = self.default_parse_headers = {}
        self.default_cookies = self.default_search_cookies = self.default_download_cookies = self.default_parse_cookies = {}
        self.enable_download_curl_cffi = False
        self.logger_handle = QuietLogger()
        self.disable_print = True
        self.max_retries = 1
        self.soda_auth_info = {}
        self.search_size_per_source = self.search_size_per_page = 20
        self.strict_limit_search_size_per_page = True
        self.audio_link_tester = CachedProbe(http)

    def _initsession(self):
        # Decorators may reset sessions; no direct requests session is ever created.
        pass

    def _request(self, url, data=None, **kwargs):
        import requests
        if kwargs.get('params'):
            url += ('&' if '?' in url else '?') + urlencode(kwargs['params'])
        if isinstance(data, dict):
            data = urlencode(data).encode()
        elif isinstance(data, str):
            data = data.encode()
        try:
            if data is None and url in self.prefetched_pages:
                final, content_type, body = self.prefetched_pages[url]
            else:
                final, content_type, body = self.http.fetch(url.replace('http://', 'https://', 1), data,
                                                           headers=kwargs.get('headers'), cookies=False)
        except MusicError as exc:
            self.failure = exc
            raise
        response = requests.Response()
        response.status_code, response.url = 200, final
        response._content, response._content_consumed = body, True
        response.encoding = 'utf-8'
        response.headers.update({'Content-Type': content_type, 'Content-Length': str(len(body))})
        response.raw = io.BytesIO(body)
        self.last_response = response
        return response

    def get(self, url, **kwargs):
        return self._request(url, **kwargs)

    def post(self, url, data=None, **kwargs):
        return self._request(url, data, **kwargs)


class CachedProbe:
    def __init__(self, http):
        self.http = http

    def test(self, url, **kwargs):
        from musicdl.modules.utils import AudioLinkTester
        if not isinstance(url, str) or not url:
            raise MusicError('平台没有提供可用音频，未入库')
        final, content_type, body = self.http.fetch(url.replace('http://', 'https://', 1))
        # Reuse musicdl's content/extension inference without HEAD or range probes.
        tester = AudioLinkTester.__new__(AudioLinkTester)
        ext, _ = tester.inferext(url, final, content_type, None, body[:8192], [])
        if ext not in {'mp3', 'm4a', 'mp4', 'flac', 'wav', 'ogg', 'aac'}:
            raise MusicError('音频格式无法确认，未入库')
        return {'ok': True, 'ext': ext, 'download_url': final, 'file_size_bytes': len(body),
                'file_size': AudioLinkTester.byte2mb(len(body))}


def clients(http):
    from musicdl.modules.sources.soda import SodaMusicClient
    from musicdl.modules.sources.netease import NeteaseMusicClient

    class Soda(CachedClient, SodaMusicClient):
        pass

    class Netease(CachedClient, NeteaseMusicClient):
        def _parsewithofficialapiv1(self, search_result, **kwargs):
            # Adapted from musicdl 2.14.2: a single official standard-quality request.
            from musicdl.modules.utils import SongInfo
            from musicdl.modules.utils.neteaseutils import EapiCryptoUtils
            identity = search_result['id']
            if search_result.get('fee') in (1, 4):
                raise MemberRequired(search_result['name'], ' / '.join(a['name'] for a in search_result['ar']))
            params = {'ids': [identity], 'level': 'standard', 'encodeType': 'mp3',
                      'header': json.dumps({'os': 'pc', 'appver': '', 'osver': '', 'deviceId': 'pyncm!', 'requestId': '20000000'})}
            url = 'https://interface3.music.163.com/eapi/song/enhance/player/url/v1'
            encrypted = EapiCryptoUtils.encryptparams(url=url, payload=params)
            response = self.post(url, data={'params': encrypted}).json()
            items = response.get('data') or []
            item = next((entry for entry in items if str(entry.get('id')) == str(identity)), None)
            if not item or response.get('code') != 200:
                raise MusicError('网易云没有返回可确认的单曲音源，未入库')
            if item.get('freeTrialInfo') is not None or item.get('code') == -105:
                raise MemberRequired(search_result['name'], ' / '.join(a['name'] for a in search_result['ar']))
            if item.get('code') != 200 or not item.get('url'):
                raise MusicError('网易云未提供可用音源，具体原因尚未明确，未入库')
            if 'freeTrialInfo' not in item:
                raise MusicError('网易云没有明确说明是否为试听，未下载')
            status = self.audio_link_tester.test(item['url'])
            return SongInfo(source=self.source, raw_data={'search': search_result, 'download': response},
                            song_name=search_result['name'], singers=' / '.join(a['name'] for a in search_result['ar']),
                            album=(search_result.get('al') or {}).get('name'), identifier=str(identity),
                            duration_s=search_result['dt'] / 1000, ext=status['ext'], download_url=status['download_url'],
                            download_url_status=status, file_size_bytes=status['file_size_bytes'])

    return Soda(http), Netease(http)


class MusicDLEngine:
    def __init__(self, http):
        self.http = http
        self.soda, self.netease = clients(http)

    def resolve(self, platform, identity, *, page_response=None):
        try:
            if platform == 'qishui':
                client = self.soda
                if page_response is not None:
                    from .links import parse_link
                    source = parse_link(page_response[0])
                    if source.platform != 'qishui' or source.platform_id != str(identity):
                        raise MusicError('已有分享页与曲目编号不一致，已停止解析')
                    canonical = 'https://music.douyin.com/qishui/share/track?track_id=' + str(identity)
                    client.prefetched_pages[canonical] = page_response
                song = client._parsewithofficialnonvipapiv1({'entity': {'track': {'id': identity}}})
            else:
                client = self.netease
                detail = client._getsongmetainfo(int(identity))
                if client.failure:
                    raise client.failure
                if str(detail.get('id')) != str(identity) or not detail.get('name') or not detail.get('ar') or not detail.get('dt'):
                    raise MusicError('网易云单曲详情无法确认，未入库')
                check_region(detail, client.last_response.json())
                song = client._parsewithofficialapiv1(detail)
            if client.failure:
                raise client.failure
            if not song.with_valid_download_url or not song.duration_s or not song.song_name or not song.singers:
                raise MusicError('musicdl 未返回完整曲目信息，未入库')
            return {'platform_id': str(song.identifier), 'title': song.song_name, 'artist': song.singers,
                    'album': song.album, 'extension': '.' + song.ext.lstrip('.'), 'url': song.download_url,
                    'expected_duration': float(song.duration_s), 'license_status': 'platform_copyrighted',
                    '_musicdl_song': song, '_musicdl_client': client}
        except MusicError:
            raise
        except Exception as exc:
            raise MusicError('musicdl 无法解析这首歌；已停止，不会自动重抓') from exc

    def search_exact(self, title, artist, *, existing_ids=()):
        query = title + ' ' + artist
        # Only construct one search page; do not call the upstream batch search/parser chain.
        url = self.soda._constructsearchurls(query, rule={'_rticket': '0'})[0]
        result = self.soda.get(url).json()
        groups = result.get('result_groups') or []
        if not groups or not isinstance(groups[0].get('data'), list):
            raise MusicError('汽水搜索响应无法读取，不能判定为没有匹配歌曲')
        for item in groups[0]['data']:
            track = (item.get('entity') or {}).get('track') or {}
            singers = ' / '.join(a['name'] for a in track.get('artists', []))
            if exact_text(track.get('name')) == exact_text(title) and exact_artists(singers) == exact_artists(artist):
                resolved = ({'platform_id': str(track['id'])} if str(track['id']) in existing_ids
                            else self.resolve('qishui', str(track['id'])))
                resolved['source_platform'] = 'qishui'
                resolved['source_url'] = 'https://music.douyin.com/qishui/share/track?track_id=' + str(track['id'])
                return resolved
        raise MusicError('没找到同一首')

    def download(self, metadata, target):
        from rich.progress import Progress
        song, client = metadata['_musicdl_song'], metadata['_musicdl_client']
        song._save_path = str(target)
        song.work_dir = str(target.parent)
        song.lyric, song.cover_url = None, None
        # Only call the single-file musicdl writer: no metadata/cover/tag network activity.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), Progress(disable=True) as progress:
            task = progress.add_task('下载音频', total=None)
            results = client._download(song, downloaded_song_infos=[], progress=progress, song_progress_id=task,
                                       auto_supplement_song=False)
        if not results or not target.is_file() or not target.stat().st_size:
            target.unlink(missing_ok=True)
            if client.failure:
                raise client.failure
            raise MusicError('musicdl 未完成音频写入，未入库')
