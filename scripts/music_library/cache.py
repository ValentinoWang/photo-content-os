"""No retries: claim each request durably before opening its socket."""
import hashlib
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

from .errors import MusicError, NetworkFailure
from .network import MusicOpener, network_failure


USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'


def read_json(path: Path, label: str):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise MusicError(f'{label}无法读取或已损坏，请检查本地文件后再继续') from exc


def write_json(path: Path, data):
    temporary = path.with_suffix('.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def request_cache_key(url, data=None):
    return hashlib.sha256(url.encode() + b'\0' + (data or b'')).hexdigest()


class CachedHTTP:
    def __init__(self, root: Path, cookie_reader=None, opener=None, *, allow_network=True):
        self.root = root
        self.allow_network = allow_network
        self.network_calls = 0
        self.audit = []
        self.cookie_reader = cookie_reader
        self.opener = opener if opener is not None else MusicOpener()

    def fetch(self, url, data=None, *, cookies=False, headers=None, follow_redirects=True):
        supplied_headers = headers or {}
        for _ in range(6):
            parsed = urlsplit(url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise MusicError('来源返回了不安全的下载地址')
            key = request_cache_key(url, data)
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            record_path, body_path = self.root / f'{key}.json', self.root / f'{key}.body'
            if record_path.exists():
                record = read_json(record_path, '网络缓存')
                if record.get('state') == 'failed':
                    message = record.get('reason', '请求失败，原因未确认') + '（本地请求失败缓存，未联网）'
                    if record.get('failure'):
                        raise NetworkFailure(message, record['failure'])
                    raise MusicError(message)
                if record.get('state') != 'complete':
                    raise MusicError('这个链接已尝试过且未完成，已停止重复联网；请保留缓存交由维护者检查')
                try:
                    body = body_path.read_bytes()
                except OSError as exc:
                    raise MusicError('网络缓存内容无法读取；已停止重复联网') from exc
                if hashlib.sha256(body).hexdigest() != record.get('sha256'):
                    raise MusicError('网络缓存内容已损坏；已停止重复联网')
            else:
                if not self.allow_network:
                    raise MusicError('本地缓存不足；已禁止重新联网，请汇报缺失请求')
                headers = {'User-Agent': USER_AGENT, 'Referer': 'https://' + parsed.hostname + '/'}
                headers.update({k: v for k, v in supplied_headers.items() if k.lower() not in ('cookie', 'authorization')})
                if cookies and self.cookie_reader:
                    cookie = self.cookie_reader(url)
                    if cookie:
                        headers['Cookie'] = cookie
                request = urllib.request.Request(url, data=data, headers=headers)
                if hasattr(self.opener, 'check_request'):
                    self.opener.check_request(request)
                write_json(record_path, {'state': 'attempted', 'request_host': parsed.hostname, 'request_path': parsed.path})
                temporary = body_path.with_suffix('.part')
                response_info = {}
                try:
                    try:
                        self.network_calls += 1
                        self.audit.append({'method': request.get_method(), 'host': parsed.hostname, 'path': parsed.path, 'cache_key': key})
                        response = self.opener.open(request, timeout=30)
                    except urllib.error.HTTPError as exc:
                        response = exc
                    except MusicError:
                        raise
                    except Exception as exc:
                        raise network_failure(exc, proxy_configured=bool(getattr(self.opener, 'proxy', None))) from exc
                    with response:
                        record = {'state': 'complete', 'status': response.code,
                                  'request_host': parsed.hostname, 'request_path': parsed.path,
                                  'content_type': response.headers.get('Content-Type', ''),
                                  'location': response.headers.get('Location', '')}
                        response_info = dict(record)
                        expected = response.headers.get('Content-Length')
                        length = 0
                        with temporary.open('wb') as handle:
                            while True:
                                try:
                                    chunk = response.read(1024 * 1024)
                                except Exception as exc:
                                    failure = network_failure(exc, proxy_configured=bool(getattr(self.opener, 'proxy', None)))
                                    failure.diagnostic.update({'expected_bytes': int(expected) if expected else None,
                                                               'received_bytes': getattr(response, 'bytes_received', length)})
                                    raise failure from exc
                                if not chunk:
                                    break
                                length += len(chunk)
                                if length > 512 * 1024 * 1024:
                                    raise MusicError('文件过大，已停止下载')
                                handle.write(chunk)
                            handle.flush()
                            os.fsync(handle.fileno())
                        if expected and length != int(expected):
                            raise NetworkFailure('音频没有下载完整，已停止入库',
                                                 {'failure_class': 'incomplete_response', 'expected_bytes': int(expected),
                                                  'received_bytes': length, 'exception_types': ['ContentLengthMismatch']})
                    temporary.replace(body_path)
                    body = body_path.read_bytes()
                    record['sha256'] = hashlib.sha256(body).hexdigest()
                    write_json(record_path, record)
                except MusicError as exc:
                    write_json(record_path, {**response_info, 'state': 'failed', 'reason': str(exc), 'failure': getattr(exc, 'diagnostic', None),
                                             'request_host': parsed.hostname, 'request_path': parsed.path})
                    raise
                except (OSError, ValueError) as exc:
                    write_json(record_path, {'state': 'failed', 'reason': '本地请求缓存写入失败或响应格式无效',
                                             'request_host': parsed.hostname, 'request_path': parsed.path})
                    raise MusicError('本地请求缓存写入失败或响应格式无效') from exc
                finally:
                    temporary.unlink(missing_ok=True)
            if record.get('status', 200) >= 500:
                raise NetworkFailure(f"平台返回 HTTP {record['status']} 服务端错误；响应已缓存、未重试",
                                     {'failure_class': 'http_server_error', 'http_status': record['status']})
            if record.get('status', 200) >= 400:
                raise MusicError('平台拒绝访问或链接已失效；响应已缓存，已停止重复联网')
            if record.get('status') in (301, 302, 303, 307, 308):
                if not follow_redirects:
                    raise NetworkFailure(f"来源返回 HTTP {record['status']} 跳转；按要求未跟随、未重试",
                                         {'failure_class': 'redirect_not_followed', 'http_status': record['status']})
                url = urljoin(url, record['location'])
                data = None
                # A redirect must never forward cookies to a CDN or another site.
                cookies = False
                continue
            return url, record['content_type'], body
        raise MusicError('链接跳转过多，已停止访问')

    def json(self, url, data=None, *, cookies=False):
        _, _, body = self.fetch(url, data, cookies=cookies)
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError) as exc:
            raise MusicError('平台响应无法解析，可能需要登录或遇到访问验证；未重试') from exc
        if not isinstance(result, dict):
            raise MusicError('平台返回了未知格式，已停止入库')
        return result
