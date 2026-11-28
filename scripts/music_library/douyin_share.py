"""Read anonymous work SSR once; never execute page JavaScript or follow redirects."""
import html
import json
import re

from .errors import MusicError

if __package__:
    from .constants import (
        IPHONE_SAFARI,
    )
else:
    try:
        from scripts.music_library.constants import (
            IPHONE_SAFARI,
        )
    except ImportError:
        from constants import (
            IPHONE_SAFARI,
        )


def parse_router_data(text):
    values = []
    for match in re.finditer(r'(?:window\.)?_ROUTER_DATA\s*=\s*', text):
        tail = text[match.end():]
        for candidate in (tail, html.unescape(tail)):
            try:
                value, _ = json.JSONDecoder().raw_decode(candidate)
            except ValueError:
                continue
            if isinstance(value, dict):
                values.append(value)
                break
    if not values:
        raise MusicError('抖音分享页作品数据无法读取，可能遇到访问验证；未重试')
    return values


def work_detail(http, identity, kind):
    url = f'https://www.iesdouyin.com/share/{kind}/{identity}/'
    _, _, body = http.fetch(url, cookies=False, headers={'User-Agent': IPHONE_SAFARI}, follow_redirects=False)
    try:
        return parse_router_data(body.decode('utf-8'))
    except UnicodeError as exc:
        raise MusicError('抖音分享页编码无法读取；未重试') from exc
