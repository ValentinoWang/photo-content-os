"""Browser-safe shot derivatives; originals stay outside the HTTP surface."""
import os
from pathlib import Path
import re
import subprocess
import tempfile


def generate_previews(project, document):
    folder = Path(project) / 'ai-analysis/shots/previews'
    folder.mkdir(parents=True, exist_ok=True)
    for row in document['shots']:
        if row['kind'] != 'video' or row.get('start_sec') is None or not row.get('duration_sec'):
            continue
        identity = row['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', identity):
            raise ValueError('invalid shot ID')
        source = (Path(project) / row['source_relative_path']).resolve()
        source.relative_to(Path(project).resolve())
        output = folder / (identity + '.mp4')
        if output.is_file() and not output.is_symlink():
            continue
        fd, staging = tempfile.mkstemp(suffix='.mp4', dir=folder)
        os.close(fd)
        try:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(row['start_sec']), '-i', str(source),
                            '-t', str(row['duration_sec']), '-vf', "scale=w='min(960,iw)':h='min(540,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
                            '-c:v', 'libx264', '-preset', 'fast', '-crf', '25', '-pix_fmt', 'yuv420p',
                            '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', staging], check=True, capture_output=True)
            os.replace(staging, output)
        finally:
            Path(staging).unlink(missing_ok=True)
