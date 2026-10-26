"""R278 clip encoding and delivery using tiny synthetic frames, no HTML render."""
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from test_r276_direct_api import api
from test_r278_style_base import Model, generate, idle
from direct_video.generate import DirectVideoError, Generator
from direct_video.media import LocalMedia


def frames(root, shot, color='red'):
    target = root / 'cache' / shot['shotId'] / shot['shotId'] / 'frames'
    target.mkdir(parents=True, exist_ok=True)
    count = max(1, round((shot['measuredSeconds'] or shot['estimatedSeconds']) * 30))
    for index in range(count):
        Image.new('RGB', (36, 64), color).save(target / f'frame-{index:06d}.png')
    (target / 'boxes.json').write_text('[]')
    return count


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def test_render_outputs_poster_and_clip_same_step(tmp_path):
    shot = {'shotId': '01', 'estimatedSeconds': .2, 'measuredSeconds': None}
    (tmp_path / 'shots').mkdir()
    (tmp_path / 'shots/01.html').write_text('synthetic')
    count = frames(tmp_path, shot)
    with patch('direct_video.media.render_shots', return_value={'status': 'completed'}):
        LocalMedia().render(tmp_path, shot)
    assert (tmp_path / 'posters/01.jpg').is_file()
    clip = tmp_path / 'clips/01.mp4'
    info = probe(clip)
    assert len(info['streams']) == 1
    stream = info['streams'][0]
    assert (stream['width'], stream['height'], stream['codec_name'], stream['r_frame_rate']) == (360, 640, 'h264', '30/1')
    assert int(stream['nb_read_frames']) == count
    assert float(stream['duration']) == pytest.approx(.2)
    data = clip.read_bytes()
    assert data.index(b'moov') < data.index(b'mdat')


class FrameMedia(LocalMedia):
    def render(self, root, shot):
        code = (root / 'shots' / (shot['shotId'] + '.html')).read_text()
        frames(root, shot, 'blue' if '蓝' in code else 'red')
        with patch('direct_video.media.render_shots', return_value={'status': 'completed'}):
            return super().render(root, shot)


def test_clips_follow_rewrite_rollback_lazy_request_and_missing_frames(api):
    request, csrf, pid, app, host = api
    gen = app.direct_video.generator
    gen.model_call, gen.media = Model(), FrameMedia()
    job = generate(gen, {'script': '甲', 'style': '浅底'}, pid)
    jid = job['jobId']
    root = gen.path(pid, jid)
    path = f'/api/projects/{pid}/direct/jobs/{jid}/shots/01/clip.mp4'
    first = request(path + '?v=1')
    assert first[0] == 200
    assert first[1]['Content-Type'] == 'video/mp4'
    assert request(path, headers={'Range': 'bytes=0-3'})[0] == 206
    assert request(path, headers={'Range': 'bytes=0-3'})[2] == first[2][:4]
    gen.rewrite(pid, jid, '01', '改蓝')
    idle(gen)
    changed = request(path + '?v=2')
    assert changed[0] == 200 and changed[2] != first[2]
    gen.current(pid, jid, '01', 1)
    reverted = request(path + '?v=1')
    assert reverted[0] == 200 and reverted[2] == first[2]
    # Selected version's frames must be used; stale frames from the newer version must never leak.
    (root / 'clips/01.mp4').unlink()
    for item in (root / 'versions').rglob('clip.mp4'):
        item.unlink()
    assert request(path)[0] == 404
    # A legacy job with matching current frames can create its clip on first read.
    gen.current(pid, jid, '01', 2)
    current = gen.read(pid, jid)
    gen.render(root, current['shots'][0])
    (root / 'clips/01.mp4').unlink()
    assert request(path)[0] == 200
    (root / 'clips/01.mp4').unlink()
    shutil.rmtree(root / 'cache')
    assert request(path)[0] == 404
    assert request(path.replace('/01/', '/missing/'))[0] == 404


def test_encoding_command_has_crf_faststart_no_audio_and_frame_count(tmp_path):
    shot = {'shotId': '01', 'estimatedSeconds': .2, 'measuredSeconds': None}
    frames(tmp_path, shot)
    media = LocalMedia()
    with patch('direct_video.media.run_ffmpeg') as run:
        def encoded(args):
            Path(args[-1]).write_bytes(b'encoded')
        run.side_effect = encoded
        media.encode_clip(tmp_path, shot)
    args = run.call_args.args[0]
    for key, value in [('-crf', '28'), ('-vf', 'scale=360:640'), ('-frames:v', '6'), ('-framerate', '30'), ('-movflags', '+faststart')]:
        assert args[args.index(key) + 1] == value
    assert '-an' in args
