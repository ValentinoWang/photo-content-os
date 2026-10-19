import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from .errors import MusicError


def measure_audio(path: Path):
    if not shutil.which('ffprobe') or not shutil.which('ffmpeg'):
        raise MusicError('需要安装 ffmpeg 和 ffprobe 才能测量音频，尚未入库')
    try:
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_streams', '-show_format',
                                '-of', 'json', str(path)], capture_output=True, text=True, timeout=60, check=True)
        data = json.loads(probe.stdout)
        if not data['streams']:
            raise ValueError('no audio')
        stream = data['streams'][0]
        duration = float(stream.get('duration') or data['format']['duration'])
        rate = int(stream['sample_rate'])
        if not math.isfinite(duration) or duration <= 0 or rate <= 0:
            raise ValueError('invalid measurements')
        loudness = subprocess.run(['ffmpeg', '-nostdin', '-xerror', '-err_detect', 'explode', '-v', 'info', '-i', str(path), '-map', '0:a:0',
                                   '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                                  capture_output=True, text=True, timeout=300, check=True)
        blocks = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', loudness.stderr, re.S)
        value = float(json.loads(blocks[-1])['input_i'])
        if math.isnan(value) or value == math.inf:
            raise ValueError('invalid loudness')
        return {'duration_seconds': duration, 'sample_rate_hz': rate,
                'loudness_lufs': value if math.isfinite(value) else None,
                'loudness_status': 'measured' if math.isfinite(value) else 'silence'}
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        raise MusicError('音频无法完整解析或测量，尚未入库') from exc
