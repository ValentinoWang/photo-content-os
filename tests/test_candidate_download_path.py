"""The candidate download path follows the pinned contract's api_base."""
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import video_candidate


def _movie(path):
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x25516b:s=288x512:r=30:d=1',
                    '-f', 'lavfi', '-i', 'sine=frequency=660:duration=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-shortest', str(path)], check=True)


def test_download_path_starts_with_snapshot_api_base(tmp_path):
    source = tmp_path / 'source.mp4'
    _movie(source)
    with patch.object(video_candidate, 'load_snapshot', return_value={'api_base': '/media/api'}):
        preview = video_candidate.preview_video(source, tmp_path / 'preview.mp4')
    path = preview['artifact']['downloadPath']
    assert path.startswith('/media/api/jobs/local/video-artifacts/art_')
    assert '/openclaw/' not in path


def test_download_path_follows_a_changed_api_base(tmp_path):
    source = tmp_path / 'source.mp4'
    _movie(source)
    with patch.object(video_candidate, 'load_snapshot', return_value={'api_base': '/changed/media/api'}):
        preview = video_candidate.preview_video(source, tmp_path / 'preview.mp4')
    assert preview['artifact']['downloadPath'].startswith('/changed/media/api/jobs/local/video-artifacts/')
