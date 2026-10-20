"""Measure and replay duplicates only from the phase-B copy, with network denied."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import runpy
import socket
import subprocess
import sys

root = Path.cwd()
sys.path[:0] = [str(root), str(root / 'scripts')]
from runtime_paths import local_media_root
from music_library.library import MusicLibrary

media = local_media_root()
assert '.photo-content-os/evidence/R223-music-beat-map/phase-c/' in str(media)
library = MusicLibrary(media)
tracks = library.list_tracks()
proof = []
for track in tracks:
    audio = library.root / track['file_sha256'] / track['audio_file']
    assert hashlib.sha256(audio.read_bytes()).hexdigest() == track['file_sha256']
    measured = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'json', str(audio)]))
    assert abs(float(measured['format']['duration']) - track['duration_seconds']) < .1
    proof.append({'title': track['title'], 'hash_matches': True, 'duration_matches': True})

def deny_network(*args, **kwargs):
    raise AssertionError('Duplicate replay must not connect to a platform')

socket.create_connection = deny_network
for track in tracks:
    if track['platform'] not in ('qishui', 'netease'):
        continue
    url = track['original_url']
    output = io.StringIO()
    sys.argv = ['import_music.py', url]
    with contextlib.redirect_stdout(output):
        try:
            runpy.run_path(str(root / 'scripts/import_music.py'), run_name='__main__')
        except SystemExit as exc:
            assert exc.code in (None, 0)
    assert '已在库里' in output.getvalue()
    proof.append({'title': track['title'], 'cli_duplicate': '已在库里', 'network': 'denied'})
print(json.dumps({'result': 'PASS', 'checks': proof}, ensure_ascii=False, indent=2))
