from contextlib import contextmanager
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .cache import CachedHTTP, read_json, request_cache_key
from .errors import MusicError, NetworkFailure
from .links import parse_link


def objects(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)


def media_extension(url):
    extension = Path(urlsplit(url).path).suffix.lower()
    return extension if extension in ('.mp3', '.mp4', '.m4a', '.flac', '.wav', '.ogg', '.aac') else '.m4a'


class PlatformAdapter:
    def __init__(self, cache_root, *, http=None, browser=None, profile='Default'):
        self.cache_root = cache_root
        self.injected_http = http is not None
        self.engine = None
        self.browser = browser
        self.profile = profile
        from .network import MusicOpener
        self.http = http or CachedHTTP(cache_root, cookie_reader=self.cookies, opener=MusicOpener(proxy=''))

    @contextmanager
    def import_context(self, platform):
        from .egress import read_target, cache_partition, SSHTunnel, TunnelOpener
        if self.injected_http or platform == 'douyin':
            yield
            return
        target = read_target()
        previous, previous_engine = self.http, self.engine
        opener = None
        try:
            if target:
                opener = TunnelOpener(SSHTunnel(target))
                self.http = CachedHTTP(self.cache_root / cache_partition(target), opener=opener)
            else:
                self.http = CachedHTTP(self.cache_root)
            self.engine = None
            yield
        finally:
            if opener:
                opener.close()
            self.http, self.engine = previous, previous_engine

    def cookies(self, url):
        if self.browser:
            from .browser_cookies import build_cookie_header
            return build_cookie_header(url, self.browser, self.profile)
        return ''

    def musicdl(self):
        if self.engine is None:
            from .musicdl_engine import MusicDLEngine
            self.engine = MusicDLEngine(self.http)
        return self.engine

    def cached_identity(self, link):
        url = link.url
        for _ in range(6):
            parsed = parse_link(url)
            if parsed.platform_id:
                return parsed
            record = self.cache_root / (request_cache_key(url) + '.json')
            if not record.exists():
                return link
            value = read_json(record, '短链跳转缓存')
            if value.get('state') != 'complete' or value.get('status') not in (301, 302, 303, 307, 308):
                return link
            url = urljoin(url, value['location'])
        raise MusicError('短链缓存跳转过多；未联网')

    def douyin_short_identity(self, link):
        try:
            final_url, _, _ = self.http.fetch(link.url, cookies=False, follow_redirects=False)
        except NetworkFailure as exc:
            if exc.diagnostic.get('failure_class') != 'redirect_not_followed':
                raise
            record = read_json(self.http.root / (request_cache_key(link.url) + '.json'), '抖音短链跳转缓存')
            final_url = urljoin(link.url, record['location'])
        target = parse_link(final_url)
        if target.platform != 'douyin' or not target.platform_id:
            raise MusicError('短链没有返回可确认的抖音作品编号；未继续跳转')
        return target

    def resolve(self, link):
        link = self.cached_identity(link)
        if link.platform == 'douyin':
            if not link.platform_id:
                link = self.douyin_short_identity(link)
            if not link.platform_id:
                raise MusicError('无法确认抖音作品编号，已停止')
            if link.kind in ('note', 'video'):
                from .douyin_share import work_detail
                data = work_detail(self.http, link.platform_id, link.kind)
            else:
                from .douyin_api import music_detail
                data = music_detail(self.http, link.platform_id)
            return self.douyin(link, link.url, data)
        page_response = None
        if link.platform_id:
            identity = link.platform_id
        else:
            page_response = self.http.fetch(link.url)
            final_url = page_response[0]
            final = parse_link(final_url)
            if final.platform != link.platform or not final.platform_id:
                raise MusicError('分享短链没有指向可确认的单首歌曲')
            identity = final.platform_id
        return self.musicdl().resolve(link.platform, identity, page_response=page_response if link.platform == 'qishui' else None)

    def search_exact(self, title, artist, *, existing_ids=()):
        return self.musicdl().search_exact(title, artist, existing_ids=existing_ids)

    def douyin(self, link, final_url, data):
        final = parse_link(final_url)
        target = link if link.platform_id else final
        if target.kind in ('video', 'note'):
            videos = [obj for obj in objects(data) if str(obj.get('aweme_id')) == target.platform_id and isinstance(obj.get('music'), dict)]
            if len(videos) != 1:
                raise MusicError('无法确认这条抖音作品使用的原声，未下载')
            music = videos[0]['music']
        else:
            candidates = [obj for obj in objects(data) if str(obj.get('id') or obj.get('mid')) == target.platform_id
                          and isinstance(obj.get('play_url'), dict) and obj.get('title')]
            if len(candidates) != 1:
                raise MusicError('抖音音乐页没有可确认的原声信息；可能需要浏览器验证，未重试')
            music = candidates[0]
        urls = (music.get('play_url') or {}).get('url_list') or []
        if not urls or not (music.get('id') or music.get('mid')) or not music.get('title'):
            raise MusicError('这条抖音原声暂时不可下载')
        url = urls[0]
        return {'platform_id': str(music.get('id') or music['mid']), 'title': music['title'],
                'artist': music.get('author') or '未知歌手', 'album': None, 'url': url,
                'extension': media_extension(url),
                'expected_duration': self.douyin_duration(music)}

    @staticmethod
    def douyin_duration(music):
        duration = music.get('duration')
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise MusicError('抖音未返回可核验的原声时长；未下载')
        return duration

    def download(self, metadata, target):
        if '_musicdl_song' in metadata:
            return self.musicdl().download(metadata, target)
        url, content_type, body = self.http.fetch(metadata['url'].replace('http://', 'https://', 1))
        if '.m3u8' in urlsplit(url).path or 'mpegurl' in content_type or body.startswith(b'#EXTM3U'):
            self.download_hls(url, body, target)
            return
        target.write_bytes(body)

    def download_hls(self, url, body, target):
        for _ in range(3):
            lines = body.decode('utf-8').splitlines()
            if any(line.startswith('#EXT-X-STREAM-INF') for line in lines):
                index = next(i for i, line in enumerate(lines) if line.startswith('#EXT-X-STREAM-INF'))
                url, _, body = self.http.fetch(urljoin(url, lines[index + 1]))
                continue
            if '#EXT-X-ENDLIST' not in lines or any(line.startswith(('#EXT-X-KEY', '#EXT-X-BYTERANGE', '#EXT-X-MAP')) for line in lines):
                raise MusicError('暂不支持直播、加密或分段范围音频，未入库')
            segments = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            if not segments:
                raise MusicError('音频分段列表为空，未入库')
            joined = target.with_suffix('.segments')
            try:
                with joined.open('wb') as handle:
                    for segment in segments:
                        _, _, chunk = self.http.fetch(urljoin(url, segment))
                        handle.write(chunk)
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(joined), '-map', '0:a:0',
                                '-c:a', 'copy', '-f', 'mp4', str(target)], capture_output=True, check=True, timeout=300)
                return
            except (OSError, subprocess.SubprocessError) as exc:
                raise MusicError('分段音频无法合并，未入库') from exc
            finally:
                joined.unlink(missing_ok=True)
        raise MusicError('分段音频列表嵌套过多，未入库')
