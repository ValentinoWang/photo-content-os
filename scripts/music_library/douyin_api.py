"""Signed anonymous detail request; one registration and one detail, no retries.

Signature/query: jiji262/douyin-downloader, ed863617aa52353821aca8fdebcfad4e916ebff5.
Anonymous registration adapted from Johnserf-Seed/f2 TokenManager.gen_ttwid
and f2/conf/conf.yaml (Apache-2.0); see THIRD_PARTY_NOTICES.md.
"""
import json
import os
from http.cookies import SimpleCookie
from urllib.parse import urlencode, urlsplit, parse_qs

from .cache import read_json, write_json
from .errors import MusicError, NetworkFailure
from .vendor.douyin_abogus import ABogus, BrowserFingerprintGenerator
from .vendor.douyin_query import default_query

REGISTER = 'https://ttwid.bytedance.com/ttwid/union/register/'
REGISTER_DATA = b'{"region":"cn","aid":1768,"needFid":false,"service":"www.ixigua.com","migrate_info":{"ticket":"","source":"node"},"cbUrlProtocol":"https","union":true}'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'


class AnonymousOpener:
    """Capture only the newly registered anonymous ID, never browser credentials."""
    proxy = ''

    def __init__(self, transport, token_path):
        self.transport, self.token_path = transport, token_path

    def check_request(self, request):
        if hasattr(self.transport, 'check_request'):
            self.transport.check_request(request)

    def open(self, request, timeout):
        response = self.transport.open(request, timeout)
        if request.full_url == REGISTER and response.code == 200:
            jar = SimpleCookie()
            for header in response.headers.get_all('Set-Cookie', []):
                jar.load(header)
            if 'ttwid' in jar:
                write_json(self.token_path, {'ttwid': jar['ttwid'].value})
                os.chmod(self.token_path, 0o600)
        return response


def music_detail(http, identity):
    private = http.root / '.douyin-anonymous'
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_path = private / 'anonymous.json'
    # Both the signed URL and opaque anonymous ID stay in the private media cache.
    plan = private / ('music-' + identity + '-anonymous-v2.json')
    if not plan.exists():
        previous_opener = http.opener
        http.opener = AnonymousOpener(previous_opener, token_path)
        try:
            http.fetch(REGISTER, REGISTER_DATA, headers={'User-Agent': UA, 'Content-Type': 'application/json; charset=utf-8'})
        finally:
            http.opener = previous_opener
        if not token_path.is_file():
            raise MusicError('抖音匿名注册未返回 ttwid，已停止；未读取浏览器登录态')
        params = default_query()
        params['music_id'] = identity
        query = urlencode(params)
        signer = ABogus(fp=BrowserFingerprintGenerator.generate_fingerprint('Chrome'), user_agent=UA)
        signed, _, user_agent, _ = signer.generate_abogus(query, '')
        path = '/aweme/v1/web/music/detail/'
        write_json(plan, {'url': 'https://www.douyin.com' + path + '?' + signed, 'user_agent': user_agent})
        os.chmod(plan, 0o600)
    request = read_json(plan, '抖音匿名请求缓存')
    token = read_json(token_path, '抖音匿名注册缓存')['ttwid']
    previous_reader = http.cookie_reader
    ms_token = parse_qs(urlsplit(request['url']).query)['msToken'][0]
    http.cookie_reader = lambda url: ('ttwid=' + token + '; msToken=' + ms_token) if urlsplit(url).hostname == 'www.douyin.com' else ''
    try:
        _, _, body = http.fetch(request['url'], cookies=True, headers={'User-Agent': request['user_agent'],
                                'Referer': 'https://www.douyin.com/?recommend=1', 'Accept': '*/*'})
    finally:
        http.cookie_reader = previous_reader
    try:
        result = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise MusicError('抖音匿名详情返回空内容或访问验证，原因未确认；未读取登录态、未重试') from exc
    if not isinstance(result, dict):
        raise MusicError('抖音匿名详情格式无法读取；未重试')
    if result.get('status_code') == 2483 or '登录' in str(result.get('status_msg', '')):
        raise NetworkFailure('抖音要求登录态，已停止；未读取用户浏览器 Cookie', {'failure_class': 'douyin_login_required'})
    value = result.get('music_info') or result.get('music_detail')
    if not isinstance(value, dict):
        raise NetworkFailure('抖音匿名接口未返回作品详情，原因未确认；已停止重试',
                             {'failure_class': 'douyin_detail_unavailable', 'status_code': result.get('status_code')})
    return value
