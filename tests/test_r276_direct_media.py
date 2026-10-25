"""Synthetic FFmpeg tests; no user audio, images or paid model calls."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from direct_video.media import LocalMedia, manifest
from video_candidate import check_direct_output, ffmpeg
from video_render.multi_shot import fingerprint, load_manifest, request_for, sha256, write_json
from test_r276_direct_video import html, wav

pytestmark = pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'), reason='FFmpeg/FFprobe unavailable')


def cached_fixture(tmp_path, monkeypatch, *, narrated):
    font = tmp_path / 'font.ttf'
    font.write_bytes(b'synthetic pinned-font identity; browser is not invoked')
    monkeypatch.setenv('DIRECT_VIDEO_FONT', str(font))
    shots = [{'shotId': '01', 'estimatedSeconds': .2, 'measuredSeconds': None},
             {'shotId': '02', 'estimatedSeconds': .2, 'measuredSeconds': None}]
    (tmp_path / 'shots').mkdir()
    for shot in shots:
        sid = shot['shotId']
        (tmp_path / 'shots' / (sid + '.html')).write_text(html(.2))
        path = tmp_path / 'manifests' / (sid + '.json')
        write_json(path, manifest(tmp_path, [shot]))
        loaded = load_manifest(path)
        frames_dir = tmp_path / 'cache' / sid / sid / 'frames'
        frames_dir.mkdir(parents=True)
        for i in range(6):
            Image.new('RGB', (108, 192), 'red' if sid == '01' else 'blue').save(frames_dir / f'frame-{i:06d}.png')
        entry = {'id': sid, 'status': 'completed', 'frames_dir': str(frames_dir), 'attempts': 1,
                 'fingerprint': fingerprint(request_for(loaded, loaded['shots'][0], transparent=False), {'synthetic': 'fixture'}),
                 'frame_hashes': [sha256(frames_dir / f'frame-{i:06d}.png') for i in range(6)],
                 'dependencies': [{'path': str(tmp_path / 'shots' / (sid + '.html')), 'sha256': sha256(tmp_path / 'shots' / (sid + '.html'))}]}
        write_json(tmp_path / 'cache' / sid / 'shot-status.json', {'shots': [entry]})
    if narrated:
        (tmp_path / 'narration.wav').write_bytes(wav(.4))
    return {'shots': shots, 'narration': {'status': 'ready' if narrated else 'none'}}


@pytest.mark.parametrize('narrated', [False, True])
def test_composition_reuses_synthetic_cached_frames(tmp_path, monkeypatch, narrated):
    job = cached_fixture(tmp_path, monkeypatch, narrated=narrated)
    # Only the unavailable browser identity is supplied by the test. Cache
    # fingerprint verification, compositor, FFmpeg, decode and all output
    # checks are real. A cache miss must fail, never silently render fixtures.
    with patch('video_render.multi_shot.runtime_identity', return_value={'synthetic': 'fixture'}), patch('video_render.multi_shot.run_renderer', side_effect=AssertionError('Unexpected rerender')) as render:
        result = LocalMedia().compose(tmp_path, job)
    assert result['frames'] == 12 and result['durationSeconds'] == .4
    assert result['checks']['playable'] == result['checks']['frameCount'] == result['checks']['blackFrames'] == 'pass'
    assert (result['checks']['avOffsetSeconds'] is not None) == narrated
    assert not render.called
    assert (tmp_path / 'output.mp4').is_file()


def test_existing_candidate_checks_fail_black_and_frame_mismatch(tmp_path):
    video = tmp_path / 'black.mp4'
    ffmpeg(['-f', 'lavfi', '-i', 'color=c=black:s=108x192:r=30:d=0.2', '-an', '-c:v', 'libx264', '-threads', '1', str(video)])
    result = check_direct_output(video, frames=8, fps=30, narrated=False, diagnostic=tmp_path / 'checks.json')
    assert result['playable'] == 'pass'
    assert result['frameCount'] == result['blackFrames'] == 'fail'


@pytest.mark.skipif(not os.environ.get('VIDEO_RENDER_PLAYWRIGHT_MODULE'), reason='No pinned Playwright/browser configured; real HTML rendering deferred')
def test_real_html_render_and_poster(tmp_path):
    font = Path(os.environ.get('VIDEO_RENDER_TEST_FONT', '/System/Library/Fonts/STHeiti Medium.ttc'))
    if not font.is_file():
        pytest.skip('Pinned font unavailable')
    shots = tmp_path / 'shots'
    shots.mkdir()
    (shots / '01.html').write_text(html(.2))
    LocalMedia().render(tmp_path, {'shotId': '01', 'estimatedSeconds': .2, 'measuredSeconds': None})
    from video_derivatives import inspect_jpeg
    result = inspect_jpeg(tmp_path / 'posters/01.jpg')
    assert result['shortEdge'] <= 360


@pytest.mark.parametrize('primary,alias,expected', [('/production/browser', '/legacy/browser', '/production/browser'), ('', '/legacy/browser', '/legacy/browser'), ('', '', None)])
def test_browser_environment_precedence(tmp_path, monkeypatch, primary, alias, expected):
    monkeypatch.setenv('VIDEO_RENDER_BROWSER', primary)
    monkeypatch.setenv('VIDEO_RENDER_TEST_BROWSER', alias)
    value = manifest(tmp_path, [{'shotId': '01', 'estimatedSeconds': 1, 'measuredSeconds': None}])
    assert value.get('browser_executable') == expected


def test_concat_uses_frame_clock_instead_of_container_duration():
    from video_render.compose import concat_schedule
    counts = [219, 187, 200, 143, 194, 262, 169, 94, 112, 275]
    rows = [{'id': f'{i:02d}', 'frames': n} for i, n in enumerate(counts, 1)]
    lines = concat_schedule(rows, 30).splitlines()
    durations = [float(line.split()[1]) for line in lines if line.startswith('duration ')]
    assert len(durations) == len(rows)
    assert abs(sum(durations) - sum(counts) / 30) < .000001
    cursor = 0
    for duration, frames in zip(durations, counts):
        cursor += frames
        assert abs(sum(durations[:counts.index(frames)+1]) - cursor / 30) < .000001
