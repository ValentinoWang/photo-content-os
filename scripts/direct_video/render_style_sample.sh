#!/usr/bin/env bash
# Render one library sample with the project renderer and pinned runtime.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
: "${VIDEO_RENDER_PLAYWRIGHT_MODULE:?Set VIDEO_RENDER_PLAYWRIGHT_MODULE to the pinned Playwright module}"
: "${VIDEO_RENDER_BROWSER:?Set VIDEO_RENDER_BROWSER to the pinned headless browser}"
exec "$ROOT/.venv/bin/python" - "$ROOT" "${1:?Usage: render_style_sample.sh <style-id>}" <<'PY'
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

def stop(signum, frame):
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, stop)
root, style_id = Path(sys.argv[1]), sys.argv[2]
ids = ('flat', 'math', 'launch', 'whiteboard', 'cyber', 'ink', 'dataviz', 'pixel', 'code')
if style_id not in ids:
    raise SystemExit('Unknown style id')
library = root / 'scripts/direct_video/style_library'
source = library / f'{style_id}.html'
evidence = Path.home() / '.photo-content-os/evidence/R283-direct-style-library'
work = evidence / 'work' / style_id
work.mkdir(parents=True, exist_ok=True)
font = Path(os.environ.get('VIDEO_RENDER_FONT', str(Path(os.sep) / 'System/Library/Fonts/STHeiti Medium.ttc')))
for name, path in [('source', source), ('design', library / f'{style_id}.json'), ('font', font), ('Playwright', Path(os.environ['VIDEO_RENDER_PLAYWRIGHT_MODULE'])), ('browser', Path(os.environ['VIDEO_RENDER_BROWSER']))]:
    if not path.is_file():
        raise SystemExit(f'{name} file missing: {path}')
for command in ('node', 'ffmpeg', 'ffprobe'):
    if not shutil.which(command):
        raise SystemExit(f'Missing tool: {command}')

def space_check():
    if shutil.disk_usage(evidence).free < 3 * 1024**3:
        raise RuntimeError('Disk has less than 3 GiB available; rendering stopped')

def run(command, log):
    with log.open('w') as stream:
        process = subprocess.Popen(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                space_check()
                time.sleep(1)
            if process.returncode:
                raise RuntimeError(f'{log.name} failed ({process.returncode}): {log.read_text()[-800:]}')
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

# A kernel lock releases on failure or interruption; all styles share it.
with (evidence / '.render.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    space_check()
    for directory in ('in', 'out'):
        shutil.rmtree(work / directory, ignore_errors=True)
    inputs = work / 'in'
    inputs.mkdir()
    shutil.copyfile(source, inputs / '01.html')
    dialogue = '有个经典实验：让学生穿件尴尬的衣服走进教室。穿的人估计，约 50% 的人会注意到；实际只有约 25%。别人的注意，远比我们以为的少。'
    storyboard = work / 'storyboard.json'
    storyboard.write_text(json.dumps({'shots': [{'shotId': '01', 'dialogue': dialogue}]}, ensure_ascii=False))
    run([sys.executable, 'scripts/direct_video/lint.py', str(inputs), '--storyboard', str(storyboard)], work / 'lint.json')
    manifest = {'width': 1080, 'height': 1920, 'fps': 30, 'timeout_seconds': 600, 'assets_dir': str(inputs), 'fonts': [{'path': str(font)}], 'shots': [{'id': '01', 'html': '01.html', 'frames': 360, 'start_frame': 0}], 'browser_executable': os.environ['VIDEO_RENDER_BROWSER']}
    manifest_path = work / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    run([sys.executable, 'scripts/video_render/multi_shot.py', '--manifest', str(manifest_path), '--output', str(work / 'out')], work / 'render.log')
    status = json.loads((work / 'out/shot-status.json').read_text())
    if status['status'] != 'completed' or status['shots'][0]['progress_frames'] != 360:
        raise RuntimeError('Renderer did not complete all 360 frames')
    if source.read_bytes() != (inputs / '01.html').read_bytes():
        raise RuntimeError('Source changed during rendering; rerender before publishing')
    frames = work / 'out/01/frames'
    ffmpeg = ['ffmpeg', '-v', 'error', '-y']
    run(ffmpeg + ['-i', str(frames / 'frame-000359.png'), '-vf', 'scale=360:640', '-q:v', '3', str(work / 'poster.jpg')], work / 'poster.log')
    run(ffmpeg + ['-framerate', '30', '-start_number', '0', '-i', str(frames / 'frame-%06d.png'), '-vf', 'scale=360:640', '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(work / 'clip.mp4')], work / 'clip.log')
    command = ffmpeg.copy()
    for frame in (0, 60, 120, 180, 250, 359):
        command += ['-i', str(frames / f'frame-{frame:06d}.png')]
    filters = ';'.join(f'[{i}]scale=270:480[s{i}]' for i in range(6)) + ';' + ''.join(f'[s{i}]' for i in range(6)) + 'hstack=6'
    run(command + ['-filter_complex', filters, str(work / 'sheet.png')], work / 'sheet.log')
    shutil.copyfile(frames / 'frame-000359.png', work / 'last.png')
    for filename in ('boxes.json', 'render-manifest.json'):
        shutil.copyfile(frames / filename, work / filename)
    for suffix, filename in [('jpg', 'poster.jpg'), ('mp4', 'clip.mp4')]:
        shutil.copyfile(work / filename, library / f'{style_id}.{suffix}')
    shutil.copyfile(work / 'out/shot-status.json', work / 'shot-status.json')
    record = {'id': style_id, 'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'canvas': [1080, 1920], 'output': [360, 640], 'fps': 30, 'frames': 360, 'sample_frames': [0, 60, 120, 180, 250, 359], 'sha256': {f'{style_id}.{ext}': hashlib.sha256((library / f'{style_id}.{ext}').read_bytes()).hexdigest() for ext in ('html', 'json', 'jpg', 'mp4')}}
    (work / 'capture.json').write_text(json.dumps(record, indent=2))
    shutil.rmtree(work / 'out')
    print(f'{style_id}: completed 360/360; sheet={work / "sheet.png"}; last={work / "last.png"}; raw frames removed')
PY
