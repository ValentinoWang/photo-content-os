"""Authorized one-pass smoke. Never delete import/request attempt records."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'scripts'))
from music_library.cache import CachedHTTP, write_json
from music_library.errors import MusicError
from music_library.library import MusicLibrary
from music_library.platforms import PlatformAdapter

inputs = [
    ('qishui', '《Fever Pitch》@汽水音乐 https://qishui.douyin.com/s/iXGDYc11/'),
    ('douyin', '8.79 复制打开抖音，看看【歪头美啦的图文作品】开智的小曲。# vibe知识大赏 # ai小曲  https://v.douyin.com/iSj4d8_TFGA/ qre:/ m@Q.KW :9pm 04/26'),
    ('netease', '分享Rich Edwards/Emelie的单曲《Turn Back Time》https://163cn.tv/bi1PoHIY (@网易云音乐)'),
]
lib = MusicLibrary()
http = CachedHTTP(lib.root / '.http-cache')
lib.adapter = PlatformAdapter(lib.root / '.http-cache', http=http)
result = {'started_at': datetime.now(timezone.utc).isoformat(), 'search_elsewhere': False,
          'media_root': str(lib.root), 'results': []}
evidence = Path(__file__).resolve().parent
for platform, share in inputs:
    before, audit_before = http.network_calls, len(http.audit)
    row = {'platform': platform, 'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        status, track = lib.import_link(share)
        row.update(status=status, title=track['title'], artist=track['artist'], platform_id=track['platform_id'],
                   file_sha256=track['file_sha256'], duration_seconds=track['duration_seconds'],
                   license_status=track['license_status'])
        audio = lib.root / track['file_sha256'] / track['audio_file']
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                                'stream=codec_name,sample_rate,duration:format=duration', '-of', 'json', str(audio)],
                               capture_output=True, text=True, timeout=60, check=True)
        row['ffprobe'] = json.loads(probe.stdout)
        decode = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(audio), '-map', '0:a:0', '-f', 'null', '-'],
                                capture_output=True, timeout=300)
        row['full_audio_decode_exit_code'] = decode.returncode
        duplicate_before = http.network_calls
        duplicate_status, _ = lib.import_link(share)
        row['duplicate_status'] = duplicate_status
        row['duplicate_network_calls'] = http.network_calls - duplicate_before
        assert row['duplicate_network_calls'] == 0 and duplicate_status == '已在库里'
    except MusicError as exc:
        row.update(status='失败', reason=str(exc), error_type=type(exc).__name__)
    except Exception as exc:
        row.update(status='失败', reason='冒烟遇到未分类异常，停止该链接；未重试', error_type=type(exc).__name__)
    row['network_calls'] = http.network_calls - before
    row['request_audit'] = http.audit[audit_before:]
    result['results'].append(row)
    write_json(evidence / 'smoke-results.json', result)
    print(platform, row['status'], row.get('reason', row.get('title')), 'requests=', row['network_calls'], flush=True)
http.allow_network = False
result['ended_at'] = datetime.now(timezone.utc).isoformat()
result['total_network_calls'] = http.network_calls
result['network_disabled_for_replay'] = True
result['library_after'] = [{'title': t['title'], 'platform': t['platform'], 'file_sha256': t['file_sha256']}
                           for t in lib.list_tracks()]
write_json(evidence / 'smoke-results.json', result)
