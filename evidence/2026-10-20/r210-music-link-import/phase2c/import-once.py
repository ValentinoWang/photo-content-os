"""Authorized stage 2c only. Durable grants prohibit another request per node.

Do not rerun: further platform requests require a new explicit authorization.
SSH target is read solely from the external user config, never embedded here.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from contextlib import contextmanager
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from music_library.cache import read_json, write_json, request_cache_key
from music_library.egress import read_target
from music_library.errors import MusicError
from music_library.library import MusicLibrary
from music_library.links import parse_link
from music_library.platforms import PlatformAdapter
from music_library.network import MusicOpener
import music_library.egress as egress

OUT = Path(__file__).resolve().parent
library = MusicLibrary()
private = library.root / '.request-grants'
private.mkdir(parents=True, exist_ok=True, mode=0o700)
ledger_path = private / 'R210-phase2c.json'
# Exclusive one-time entry; never replace a previous run's ledger.
with os.fdopen(os.open(ledger_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
    json.dump({'phase': 'R210-phase2c', 'requests': []}, handle)
if not read_target():
    raise MusicError('本轮要求用户配置的出口；未联网')
ledger = read_json(ledger_path, '本轮请求账本')
tunnels = []
original_tunnel = egress.SSHTunnel
class AuditedTunnel(original_tunnel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tunnels.append(self)
egress.SSHTunnel = AuditedTunnel

class Adapter(PlatformAdapter):
    current_platform = None
    resolved = None
    @contextmanager
    def import_context(self, platform):
        self.current_platform = platform
        with super().import_context(platform):
            yield
    def resolve(self, link):
        result = super().resolve(link)
        self.resolved = {key: result.get(key) for key in ('platform_id', 'title', 'artist', 'expected_duration')}
        return result
adapter = Adapter(library.root / '.http-cache')
library.adapter = adapter
original_open = MusicOpener.open

def guarded_open(transport, request, timeout):
    platform = adapter.current_platform
    part = urlsplit(request.full_url)
    route = 'ssh-egress' if transport.proxy else 'direct'
    if (platform in ('netease', 'qishui')) != bool(transport.proxy):
        raise MusicError('本轮出口路由不符合授权，未发出请求')
    if platform == 'netease' and part.hostname == 'interface3.music.163.com':
        node = {'/api/v3/song/detail': 'detail', '/eapi/song/enhance/player/url/v1': 'player'}.get(part.path)
    elif platform == 'qishui' and part.hostname == 'music.douyin.com' and part.path == '/qishui/share/track':
        node = 'page'
    elif platform == 'douyin' and part.hostname == 'ttwid.bytedance.com' and part.path == '/ttwid/union/register/':
        node = 'anonymous-registration'
    elif platform == 'douyin' and part.hostname == 'www.douyin.com' and part.path == '/aweme/v1/web/aweme/detail/':
        node = 'detail'
    elif part.hostname and part.hostname.endswith(('.music.126.net', '.douyinvod.com', '.byteimg.com', '.douyinpic.com')):
        node = 'audio'
    else:
        node = None
    if not node:
        raise MusicError('本轮出现未授权的新节点，已停止且未请求')
    identity = platform + ':' + node
    if any(row['node'] == identity for row in ledger['requests']):
        raise MusicError('本轮节点已经请求过，已拒绝第二次联网')
    row = {'node': identity, 'method': request.get_method(), 'route': route, 'host': part.hostname,
           'path': part.path, 'cache_key': request_cache_key(request.full_url, request.data), 'state': 'claimed'}
    ledger['requests'].append(row)
    write_json(ledger_path, ledger)
    try:
        response = original_open(transport, request, timeout)
        row.update(state='response', status=response.code)
        return response
    except BaseException as exc:
        row.update(state='failed', exception_type=type(exc).__name__)
        raise
    finally:
        write_json(ledger_path, ledger)
MusicOpener.open = guarded_open

inputs = [
 ('netease', '分享Rich Edwards/Emelie的单曲《Turn Back Time》https://163cn.tv/bi1PoHIY (@网易云音乐)'),
 ('qishui', '《Fever Pitch》@汽水音乐 https://qishui.douyin.com/s/iXGDYc11/'),
 ('douyin', '8.79 复制打开抖音，看看【歪头美啦的图文作品】开智的小曲。# vibe知识大赏 # ai小曲 https://v.douyin.com/iSj4d8_TFGA/ qre:/ m@Q.KW :9pm 04/26'),
]
results = []
try:
    for platform, text in inputs:
        link = parse_link(text)
        attempt = library.root / '.attempts' / (hashlib.sha256(link.key.encode()).hexdigest() + '.json')
        if attempt.exists():
            previous = read_json(attempt, '历史导入记录')
            if previous.get('state') == 'complete':
                raise MusicError('歌曲此前已经成功入库；请只做缓存验证')
            archive = library.root / '.attempt-history/R210-phase2c'
            archive.mkdir(parents=True, exist_ok=True)
            destination = archive / attempt.name
            if destination.exists():
                raise MusicError('历史记录已经归档，拒绝覆盖或再次尝试')
            attempt.rename(destination)
        adapter.resolved = None
        before_requests, before_tunnels = len(ledger['requests']), sum(t.starts for t in tunnels)
        row = {'platform': platform}
        try:
            status, track = library.import_link(text)
            row.update(status=status, title=track['title'], file_sha256=track['file_sha256'],
                       duration_seconds=track['duration_seconds'], resolved=adapter.resolved,
                       sample_rate_hz=track['sample_rate_hz'])
            audio = library.root / track['file_sha256'] / track['audio_file']
            decode = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror', '-err_detect', 'explode',
                                     '-i', str(audio), '-map', '0:a:0', '-f', 'null', '-'], capture_output=True)
            row['full_decode_exit_code'] = decode.returncode
            if decode.returncode:
                raise MusicError('音频完整解码失败；需要离线排查')
            if abs(track['duration_seconds'] - adapter.resolved['expected_duration']) > 2:
                raise MusicError('时长差超过两秒')
            counts = len(ledger['requests']), sum(t.starts for t in tunnels)
            repeat_status, repeat_track = library.import_link(text)
            row['repeat'] = {'status': repeat_status, 'network_requests': len(ledger['requests'])-counts[0],
                             'tunnel_starts': sum(t.starts for t in tunnels)-counts[1]}
            assert repeat_status == '已在库里' and row['repeat']['network_requests'] == row['repeat']['tunnel_starts'] == 0
        except MusicError as exc:
            row.update(status='failed', reason=str(exc), failure=getattr(exc, 'diagnostic', None), resolved=adapter.resolved)
            results.append(row)
            break
        results.append(row)
finally:
    for tunnel in tunnels:
        tunnel.close()
    MusicOpener.open = original_open
    egress.SSHTunnel = original_tunnel
    summary = {'results': results, 'requests': ledger['requests'],
               'tunnels': [{'pid': t.process.pid if t.process else None, 'starts': t.starts,
                            'closed': t.process is None or t.process.poll() is not None} for t in tunnels],
               'stopped_on_failure': any(r['status'] == 'failed' for r in results),
               'library': [{'title': t['title'], 'platform': t['platform'], 'duration_seconds': t['duration_seconds'],
                            'file_sha256': t['file_sha256']} for t in library.list_tracks()]}
    write_json(OUT / 'real-import-results.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
