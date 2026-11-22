#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
: "${VIDEO_RENDER_PLAYWRIGHT_MODULE:?Set VIDEO_RENDER_PLAYWRIGHT_MODULE}"
: "${VIDEO_RENDER_BROWSER:?Set VIDEO_RENDER_BROWSER}"
exec "$ROOT/.venv/bin/python" - "$ROOT" "${1:?Usage: render_recipe_sample.sh id portrait\|landscape}" "${2:?Usage: render_recipe_sample.sh id portrait\|landscape}" <<'PY'
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

root, name, orientation = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in name) or orientation not in ('portrait', 'landscape'):
    raise SystemExit('Invalid sample id or orientation')
source = root / 'scripts/direct_video/recipe_samples' / name / f'{orientation}.html'
evidence = Path.home() / '.photo-content-os/evidence/Pho_R05-shotcraft-line/work' / f'{name}-{orientation}'
lock_path = Path.home() / '.photo-content-os/evidence/R283-direct-style-library/.render.lock'
evidence.mkdir(parents=True, exist_ok=True)
lock_path.parent.mkdir(parents=True, exist_ok=True)
font = Path(os.environ.get('VIDEO_RENDER_FONT', '/System/Library/Fonts/STHeiti Medium.ttc'))
for label, path in [('source', source), ('font', font), ('Playwright', Path(os.environ['VIDEO_RENDER_PLAYWRIGHT_MODULE'])), ('browser', Path(os.environ['VIDEO_RENDER_BROWSER']))]:
    if not path.is_file():
        raise SystemExit(f'{label} missing: {path}')
for cmd in ('node', 'ffmpeg'):
    if not shutil.which(cmd):
        raise SystemExit(f'Missing tool: {cmd}')

def check_space():
    if shutil.disk_usage(evidence).free < 3 * 1024**3:
        raise RuntimeError('Less than 3 GiB free; stopped')

def run(args, log):
    with (evidence / log).open('w') as output:
        process = subprocess.Popen(args, cwd=root, stdout=output, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                check_space()
                time.sleep(1)
            if process.returncode:
                raise RuntimeError(f'{log} failed ({process.returncode})')
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

def stop(signum, _frame):
    raise SystemExit(128 + signum)
signal.signal(signal.SIGTERM, stop)
with lock_path.open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    check_space()
    inputs = evidence / 'in'
    output = evidence / 'out'
    if inputs.exists() or output.exists():
        raise SystemExit('Previous intermediate directory exists; inspect before retrying')
    inputs.mkdir()
    try:
        shutil.copyfile(source, inputs / '01.html')
        # Every sample declares its duration in seconds as a numeric const D.
        import re
        match = re.search(r'\bconst\s+D\s*=\s*(\d+(?:\.\d+)?)\s*;', source.read_text())
        if not match:
            raise RuntimeError('Missing numeric const D')
        frames = round(float(match.group(1)) * 30)
        width, height = (1080, 1920) if orientation == 'portrait' else (1920, 1080)
        manifest = {'width': width, 'height': height, 'fps': 30, 'timeout_seconds': 600, 'assets_dir': str(inputs), 'fonts': [{'path': str(font)}], 'shots': [{'id': '01', 'html': '01.html', 'frames': frames, 'start_frame': 0}], 'browser_executable': os.environ['VIDEO_RENDER_BROWSER']}
        manifest_path = evidence / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest))
        run([sys.executable, 'scripts/video_render/multi_shot.py', '--manifest', str(manifest_path), '--output', str(output)], 'render.log')
        status = json.loads((output / 'shot-status.json').read_text())
        if status['status'] != 'completed' or status['shots'][0]['progress_frames'] != frames:
            raise RuntimeError('Renderer did not complete all frames')
        if source.read_bytes() != (inputs / '01.html').read_bytes():
            raise RuntimeError('Source changed during rendering')
        frame_dir = output / '01/frames'
        ffmpeg = ['ffmpeg', '-v', 'error', '-y']
        height_out = 640 if orientation == 'portrait' else 202
        scale = f'scale=360:{height_out}'
        poster, clip = evidence / 'poster.jpg', evidence / 'clip.mp4'
        run(ffmpeg + ['-i', str(frame_dir / f'frame-{frames-1:06d}.png'), '-vf', scale, '-q:v', '3', str(poster)], 'poster.log')
        run(ffmpeg + ['-framerate', '30', '-start_number', '0', '-i', str(frame_dir / 'frame-%06d.png'), '-vf', scale, '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(clip)], 'clip.log')
        indexes = [round((frames-1)*i/5) for i in range(6)]
        command = ffmpeg.copy()
        for index in indexes:
            command += ['-i', str(frame_dir / f'frame-{index:06d}.png')]
        filters = ';'.join(f'[{i}]{scale}[s{i}]' for i in range(6)) + ';' + ''.join(f'[s{i}]' for i in range(6)) + 'hstack=6'
        run(command + ['-filter_complex', filters, str(evidence / 'sheet.png')], 'sheet.log')
        shutil.copyfile(poster, source.with_suffix('.jpg'))
        shutil.copyfile(clip, source.with_suffix('.mp4'))
        print(f'{name} {orientation}: {frames}/{frames} frames; sheet={evidence / "sheet.png"}')
    finally:
        shutil.rmtree(output, ignore_errors=True)
        shutil.rmtree(inputs, ignore_errors=True)
PY
