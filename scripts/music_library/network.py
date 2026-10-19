"""Music-only HTTP transport. Explicit proxy, no ambient proxies or fallback."""
import errno
import os
import ssl
from email.message import Message
from urllib.parse import urlsplit

from .errors import MusicError, NetworkFailure


PROXY_ENV = 'CONTENT_OS_MUSIC_PROXY'


def network_failure(exc, *, proxy_configured=False):
    chain, pending, seen = [], [exc], set()
    while pending and len(chain) < 16:
        item = pending.pop(0)
        if not isinstance(item, BaseException) or id(item) in seen:
            continue
        seen.add(id(item))
        chain.append(item)
        pending.extend([item.__cause__, item.__context__, getattr(item, 'reason', None)])
        pending.extend(arg for arg in item.args if isinstance(arg, BaseException))
    names = [type(item).__name__ for item in chain]
    if any('Proxy' in name or 'SOCKS' in name for name in names):
        category, label = 'proxy_connection', '音乐代理连接失败'
    elif any('Timeout' in name for name in names):
        category, label = 'timeout', '音乐请求超时'
    elif any(isinstance(item, ssl.SSLError) or 'SSL' in type(item).__name__ or 'TLS' in type(item).__name__ for item in chain):
        category, label = 'tls', '音乐请求 TLS 连接失败'
    elif any(isinstance(item, ConnectionResetError) or getattr(item, 'errno', None) == errno.ECONNRESET for item in chain):
        category, label = 'connection_reset', '音乐请求连接被重置'
    elif any(isinstance(item, ConnectionRefusedError) or getattr(item, 'errno', None) == errno.ECONNREFUSED for item in chain):
        category, label = 'connection_refused', '音乐请求连接被拒绝'
    elif any('gaierror' == name for name in names):
        category, label = 'dns', '音乐请求域名解析失败'
    else:
        category, label = 'unknown_network', '音乐网络请求失败，具体原因未确认'
    if proxy_configured:
        message = label + '（已配置音乐代理，未退回直连），已停止重试'
    else:
        message = label + '，已停止重复联网'
    details = {'failure_class': category, 'exception_types': names, 'proxy_configured': proxy_configured}
    error_numbers = [item.errno for item in chain if isinstance(getattr(item, 'errno', None), int)]
    if error_numbers:
        details['errno'] = error_numbers
    return NetworkFailure(message, details)


class MusicResponse:
    def __init__(self, response):
        self.response = response
        self.code = response.status_code
        self.headers = Message()
        for name, value in response.headers.items():
            if name.lower() != 'set-cookie':
                self.headers[name] = value
        # QR auth can read cookies in memory; the request cache never stores them.
        raw_headers = getattr(response.raw, 'headers', None)
        if raw_headers and hasattr(raw_headers, 'getlist'):
            for value in raw_headers.getlist('Set-Cookie'):
                self.headers['Set-Cookie'] = value
        if response.headers.get('Content-Encoding'):
            del self.headers['Content-Length']

    @property
    def bytes_received(self):
        return self.response.raw.tell()

    def read(self, size=-1):
        return self.response.raw.read(size, decode_content=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.response.close()


class MusicOpener:
    def __init__(self, *, session=None, proxy=None):
        import requests
        from requests.adapters import HTTPAdapter
        self.proxy = os.environ.get(PROXY_ENV, '').strip() if proxy is None else proxy.strip()
        if self.proxy:
            try:
                parsed = urlsplit(self.proxy)
                valid = parsed.scheme in ('http', 'https', 'socks5', 'socks5h') and parsed.hostname and parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise MusicError('音乐代理配置无效，请检查代理协议、地址和端口；未连接或退回直连')
        self.session = session if session is not None else requests.Session()
        self.session.trust_env = False
        self.session.mount('https://', HTTPAdapter(max_retries=0))
        self.session.mount('http://', HTTPAdapter(max_retries=0))

    def open(self, request, timeout):
        proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else {}
        headers = {'Accept-Encoding': 'identity', **dict(request.header_items())}
        # Match urllib and musicdl/requests form POST semantics after encoding to bytes.
        if request.data is not None and not any(key.lower() == 'content-type' for key in headers):
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            if hasattr(self.session, 'cookies'):
                self.session.cookies.clear()
            response = self.session.request(method=request.get_method(), url=request.full_url,
                                            data=request.data, headers=headers, timeout=timeout,
                                            allow_redirects=False, stream=True, proxies=proxies)
            if hasattr(self.session, 'cookies'):
                self.session.cookies.clear()
            return MusicResponse(response)
        except Exception as exc:
            raise network_failure(exc, proxy_configured=bool(self.proxy)) from exc
