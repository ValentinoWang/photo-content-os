"""Execute only the two anonymous page requests authorized in TASK phase 2b.

No SSH, proxy, Cookie, automatic retry, or new redirect destination is allowed.
Previously recorded redirect responses can be replayed without a request.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from runtime_paths import local_media_root
from music_library.cache import CachedHTTP, read_json, request_cache_key, write_json
from music_library.errors import MusicError
from music_library.network import MusicOpener

MOBILE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
EVIDENCE = Path(__file__).resolve().parent


def targets(cache):
    qshort = 'https://qishui.douyin.com/s/iXGDYc11/'
    dshort = 'https://v.douyin.com/iSj4d8_TFGA/'
    q = urljoin(qshort, read_json(cache / (request_cache_key(qshort) + '.json'), '已有汽水跳转')['location'])
    ies = urljoin(dshort, read_json(cache / (request_cache_key(dshort) + '.json'), '已有抖音跳转')['location'])
    d = urljoin(ies, read_json(cache / (request_cache_key(ies) + '.json'), '已有抖音中间跳转')['location'])
    assert urlsplit(q).hostname == 'music.douyin.com' and urlsplit(q).path == '/qishui/share/track'
    assert urlsplit(d).hostname == 'www.douyin.com' and urlsplit(d).path == '/note/7694712348003151717'
    return {'douyin': d, 'qishui': q}


class AuthorizedPages:
    proxy = ''
    def __init__(self, cache, allowed):
        self.allowed = allowed
        self.inner = MusicOpener(proxy='')
        self.ledger_path = cache.parent / '.request-grants/R210-phase2b.json'
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        hashes = {name: hashlib.sha256(url.encode()).hexdigest() for name, url in allowed.items()}
        if self.ledger_path.exists():
            self.ledger = read_json(self.ledger_path, '单次请求记录')
            assert {k: v['url_sha256'] for k, v in self.ledger.items()} == hashes
        else:
            self.ledger = {name: {'url_sha256': digest, 'used': 0} for name, digest in hashes.items()}
            write_json(self.ledger_path, self.ledger)

    def check_request(self, request):
        if request.get_method() != 'GET' or any(k.lower() in ('cookie', 'authorization') for k, _ in request.header_items()):
            raise MusicError('本轮只允许不带登录态的匿名页面请求，已停止')
        name = next((name for name, url in self.allowed.items() if url == request.full_url), None)
        if name is None:
            raise MusicError('跳转目标超出本轮获准请求范围；没有发出新的请求')
        if self.ledger[name]['used']:
            raise MusicError('本轮获准请求已使用，不会再次联网')

    def open(self, request, timeout):
        self.check_request(request)
        name = next(name for name, url in self.allowed.items() if url == request.full_url)
        self.ledger[name]['used'] = 1
        self.ledger[name]['started_at'] = datetime.now(timezone.utc).isoformat()
        write_json(self.ledger_path, self.ledger)
        return self.inner.open(request, timeout)


def main():
    cache = local_media_root() / 'library/music/.http-cache'
    allowed = targets(cache)
    opener = AuthorizedPages(cache, allowed)
    http = CachedHTTP(cache, opener=opener)
    result = {'authorization': 'TASK phase 2b', 'anonymous': True, 'proxy_enabled': False,
              'ssh_executed': False, 'started_at': datetime.now(timezone.utc).isoformat(), 'results': []}
    for name, url in allowed.items():
        before = http.network_calls
        item = {'platform': name, 'host': urlsplit(url).hostname, 'path': urlsplit(url).path,
                'cache_key': request_cache_key(url)}
        try:
            final, content_type, body = http.fetch(url, headers={'User-Agent': MOBILE_UA}, cookies=False)
            item.update(status='received', final_host=urlsplit(final).hostname, final_path=urlsplit(final).path,
                        content_type=content_type, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        except MusicError as exc:
            item.update(status='failed', reason=str(exc), failure=getattr(exc, 'diagnostic', None))
        item['network_calls'] = http.network_calls - before
        record = cache / (request_cache_key(url) + '.json')
        if record.exists():
            metadata = read_json(record, '本轮请求缓存')
            item['http_status'] = metadata.get('status')
            item['cache_state'] = metadata.get('state')
        result['results'].append(item)
        write_json(EVIDENCE / 'authorized-page-results.json', result)
        print(name, item['status'], item.get('reason', item.get('bytes')), 'requests=', item['network_calls'], flush=True)
    http.allow_network = False
    result.update(total_network_calls=http.network_calls, request_audit=http.audit,
                  ended_at=datetime.now(timezone.utc).isoformat(), network_disabled_after_run=True)
    write_json(EVIDENCE / 'authorized-page-results.json', result)


if __name__ == '__main__':
    main()
