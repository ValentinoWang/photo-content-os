"""Finish the authorized import using the recorded Qishui page, one media GET."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from music_library.cache import CachedHTTP, read_json, write_json, request_cache_key
from music_library.network import MusicOpener
from music_library.library import MusicLibrary, now
from music_library.musicdl_engine import MusicDLEngine
from music_library.links import parse_link
from music_library.errors import MusicError

EVIDENCE = Path(__file__).resolve().parent


class ObservedMedia:
    proxy = ''
    def __init__(self, cache, url):
        self.url = url
        self.inner = MusicOpener(proxy='')
        self.ledger_path = cache.parent / '.request-grants/R210-phase2b-qishui-media.json'
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        digest = hashlib.sha256(url.encode()).hexdigest()
        if self.ledger_path.exists():
            self.ledger = read_json(self.ledger_path, '音频单次请求记录')
            assert self.ledger['url_sha256'] == digest
        else:
            self.ledger = {'url_sha256': digest, 'used': 0, 'source': 'recorded Qishui share page'}
            write_json(self.ledger_path, self.ledger)

    def check_request(self, request):
        if request.full_url != self.url or request.get_method() != 'GET' or self.ledger['used']:
            raise MusicError('音频请求超出本次导入的单次范围，未重新联网')
        if any(name.lower() in ('cookie', 'authorization') for name, _ in request.header_items()):
            raise MusicError('音频只允许匿名请求，已停止')

    def open(self, request, timeout):
        self.check_request(request)
        self.ledger['used'] = 1
        write_json(self.ledger_path, self.ledger)
        return self.inner.open(request, timeout)


def main():
    lib = MusicLibrary()
    cache = lib.root / '.http-cache'
    short = 'https://qishui.douyin.com/s/iXGDYc11/'
    url = urljoin(short, read_json(cache / (request_cache_key(short) + '.json'), '汽水分享跳转')['location'])
    record = read_json(cache / (request_cache_key(url) + '.json'), '已捕获汽水页面')
    page = (url, record['content_type'], (cache / (request_cache_key(url) + '.body')).read_bytes())
    identity = parse_link(url).platform_id
    http = CachedHTTP(cache, opener=MusicOpener(proxy=''), allow_network=False)
    engine = MusicDLEngine(http)
    engine.soda.prefetched_pages['https://music.douyin.com/qishui/share/track?track_id=' + identity] = page
    info = engine.soda._getsongmetainfo(identity)
    media_url = info['audition_url'].replace('http://', 'https://', 1)
    http.opener = ObservedMedia(cache, media_url)
    http.allow_network = True
    link = parse_link(short)
    attempt_path = lib.root / '.attempts' / (hashlib.sha256(link.key.encode()).hexdigest() + '.json')
    previous = read_json(attempt_path, '原导入记录')
    history = lib.root / '.attempt-history/R210-phase2b'
    history.mkdir(parents=True, exist_ok=True)
    if not (history / attempt_path.name).exists():
        write_json(history / attempt_path.name, previous)
    result = {'page_network_calls': 0, 'anonymous': True, 'proxy_enabled': False, 'expected_duration_seconds': info['duration']}
    try:
        metadata = engine.resolve('qishui', identity, page_response=page)
        with lib.locked(), tempfile.TemporaryDirectory(prefix='.import-', dir=lib.root) as staging:
            audio = Path(staging) / ('audio' + metadata['extension'])
            engine.download(metadata, audio)
            source = {'platform': 'qishui', 'platform_id': identity, 'kind': 'song', 'original_url': short, 'imported_at': now()}
            status, track = lib._store(audio, metadata, source, lib._tracks())
        write_json(attempt_path, {'state': 'complete', 'file_sha256': track['file_sha256'], 'completed_under': 'R210-phase2b'})
        path = lib.root / track['file_sha256'] / track['audio_file']
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                                'stream=codec_name,sample_rate,duration:format=duration', '-of', 'json', str(path)],
                               capture_output=True, text=True, check=True, timeout=60)
        decode = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-f', 'null', '-'],
                                capture_output=True, timeout=300)
        before = http.network_calls
        lib.import_link(short)
        result.update(status=status, title=track['title'], artist=track['artist'], platform_id=identity,
                      duration_seconds=track['duration_seconds'], sample_rate_hz=track['sample_rate_hz'],
                      file_sha256=track['file_sha256'], license_status=track['license_status'],
                      ffprobe=json.loads(probe.stdout), full_decode_exit=decode.returncode,
                      duplicate_network_calls=http.network_calls-before)
    except MusicError as exc:
        write_json(attempt_path, {'state': 'failed', 'reason': str(exc), 'failure': getattr(exc, 'diagnostic', None),
                                  'attempt_authorization': 'R210-phase2b', 'page_received': True})
        result.update(status='失败', reason=str(exc), failure=getattr(exc, 'diagnostic', None))
    finally:
        http.allow_network = False
        result.update(media_network_calls=http.network_calls, request_audit=http.audit, network_disabled_after_run=True)
        write_json(EVIDENCE / 'qishui-import-result.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
