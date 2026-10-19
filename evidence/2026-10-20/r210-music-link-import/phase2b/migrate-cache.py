"""Offline, task-scoped migration of the observed canonical cache entries.

Original records stay intact. Only responses whose recorded host/path match
an observed redirect node are copied to the new exact-URL cache key.
"""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from runtime_paths import local_media_root
from music_library.cache import request_cache_key, read_json, write_json
from music_library.links import parse_link


def migrate():
    cache = local_media_root() / 'library/music/.http-cache'
    roots = ['https://qishui.douyin.com/s/iXGDYc11/', 'https://v.douyin.com/iSj4d8_TFGA/', 'https://163cn.tv/bi1PoHIY']
    report, visited = [], set()
    for initial in roots:
        url = initial
        for _ in range(6):
            if url in visited:
                break
            visited.add(url)
            exact = request_cache_key(url)
            link = parse_link(url)
            legacy = request_cache_key(link.key if link.platform_id else url)
            path = cache / (exact + '.json')
            if path.exists():
                record = read_json(path, '实际 URL 缓存')
            elif legacy != exact and (cache / (legacy + '.json')).exists():
                record = read_json(cache / (legacy + '.json'), '已有缓存')
                parsed = urlsplit(url)
                if record.get('state') != 'complete' or record.get('request_host') != parsed.hostname or record.get('request_path') != parsed.path:
                    report.append({'host': parsed.hostname, 'path': parsed.path, 'state': 'not_migrated',
                                   'legacy_key': legacy, 'exact_key': exact, 'reason': 'no completed matching HTTP response'})
                    break
                body = (cache / (legacy + '.body')).read_bytes()
                assert hashlib.sha256(body).hexdigest() == record['sha256']
                (cache / (exact + '.body')).write_bytes(body)
                write_json(path, {**record, 'migrated_from': legacy})
                report.append({'host': parsed.hostname, 'path': parsed.path, 'state': 'copied_and_hash_verified',
                               'legacy_key': legacy, 'exact_key': exact})
            else:
                break
            if record.get('status') not in (301, 302, 303, 307, 308):
                break
            url = urljoin(url, record['location'])
    write_json(Path(__file__).parent / 'cache-migration.json', {'network_calls': 0, 'records': report, 'originals_preserved': True})
    return report


if __name__ == '__main__':
    print(json.dumps(migrate(), ensure_ascii=False, indent=2))
