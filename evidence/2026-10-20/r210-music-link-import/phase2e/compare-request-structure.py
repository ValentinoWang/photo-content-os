"""Offline reconstruction; historical caches did not store raw request headers."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlencode, parse_qs
import requests
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from music_library.cache import USER_AGENT, request_cache_key
from music_library.network import MusicOpener
from music_library.egress import read_target, cache_partition
from runtime_paths import local_media_root

url = 'https://interface3.music.163.com/api/v3/song/detail'
form = {'c': json.dumps([{'id': 1331800077, 'v': 0}])}
body = urlencode(form).encode()
headers = {'User-Agent': USER_AGENT, 'Referer': 'https://interface3.music.163.com/'}
old = urllib.request.Request(url, data=body, headers=headers)
handler = urllib.request.HTTPHandler()
handler.parent = type('Parent', (), {'addheaders': []})()
handler.do_request_(old)
broken = requests.Request('POST', url, data=body, headers={'Accept-Encoding': 'identity', **headers}).prepare()
fixed = []
class Session:
    def mount(self, *a): pass
    def request(self, **kw):
        fixed.append(requests.Request(kw['method'], kw['url'], data=kw['data'], headers=kw['headers']).prepare())
        return type('Result', (), {'status_code': 200, 'headers': {}, 'raw': None})()
MusicOpener(session=Session(), proxy='socks5h://127.0.0.1:19000').open(
    urllib.request.Request(url, data=body, headers=headers), timeout=1)
native = requests.Request('POST', url, data=form).prepare()
def shape(method, headers, data):
    h = {k.lower(): v for k, v in headers.items()}
    if isinstance(data, str): data = data.encode()
    values = parse_qs(data.decode())
    return {'method': method, 'header_names': sorted(h), 'content_type': h.get('content-type'),
            'cookie_present': 'cookie' in h, 'body_encoding': 'UTF-8 percent-encoded form',
            'body_bytes': len(data), 'body_sha256': hashlib.sha256(data).hexdigest(), 'form_keys': sorted(values),
            'c_json_shape': [sorted(item) for item in json.loads(values['c'][0])]}
root = local_media_root()/'library/music/.http-cache'
key = request_cache_key(url, body)
actual = {}
for name, folder in [('prior_taiwan', root), ('phase2c_egress', root/cache_partition(read_target()))]:
    meta = json.loads((folder/(key+'.json')).read_text())
    raw = (folder/(key+'.body')).read_bytes()
    value = json.loads(raw)
    actual[name] = {'cache_key': key, 'http_status': meta['status'], 'platform_code': value['code'],
                    'response_bytes': len(raw), 'response_sha256': hashlib.sha256(raw).hexdigest(),
                    'contains_songs': bool(value.get('songs'))}
result = {'historical_evidence_limit': 'Raw wire headers were not retained. Header comparison is an offline reconstruction from the used urllib/requests implementations; cached responses are original.',
          'urllib_prior': shape(old.get_method(), dict(old.header_items()), old.data),
          'requests_phase2c': shape(broken.method, broken.headers, broken.body),
          'requests_fixed_egress': shape(fixed[0].method, fixed[0].headers, fixed[0].body),
          'musicdl_native_form': shape(native.method, native.headers, native.body), 'cached_responses': actual}
assert result['urllib_prior']['content_type'] == result['musicdl_native_form']['content_type'] == result['requests_fixed_egress']['content_type']
assert result['requests_phase2c']['content_type'] is None
assert len({result[name]['body_sha256'] for name in ('urllib_prior','requests_phase2c','requests_fixed_egress','musicdl_native_form')}) == 1
Path(__file__).with_name('request-structure-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
