#!/usr/bin/env python3
"""Compose frame-addressed shots and local PCM narration into an MP4 candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave
from typing import Any

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from video_render.multi_shot import RenderError, load_manifest, owned_workspace, render_shots, sha256, write_json


def run_ffmpeg(arguments: list[str], timeout: float = 300) -> None:
    try:
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-y', *arguments],
                       capture_output=True, text=True, timeout=timeout, check=True)
    except subprocess.TimeoutExpired as error:
        raise RenderError('encode_timeout', 'FFmpeg exceeded timeout') from error
    except subprocess.CalledProcessError as error:
        raise RenderError('encode_failed', error.stderr[-4000:]) from error


def audio_inputs(manifest: dict[str, Any]) -> list[Path]:
    shots = manifest['shots']
    if 'narration_wav' in manifest:
        pairs = [(Path(manifest['narration_wav']), sum(shot['frames'] for shot in shots) / manifest['fps'])]
    elif all('narration_wav' in shot for shot in shots):
        pairs = [(Path(shot['narration_wav']), shot['frames'] / manifest['fps']) for shot in shots]
    else:
        raise RenderError('audio_missing', 'Provide global narration_wav or narration_wav for every shot')
    for path, expected in pairs:
        try:
            with wave.open(str(path), 'rb') as audio:
                actual = audio.getnframes() / audio.getframerate()
                if audio.getcomptype() != 'NONE' or audio.getnframes() <= 0:
                    raise RenderError('invalid_audio', f'Expected nonempty PCM WAV: {path.name}')
        except (OSError, wave.Error, EOFError) as error:
            raise RenderError('invalid_audio', f'Cannot read PCM WAV {path.name}: {error}') from error
        if abs(actual - expected) > 1 / manifest['fps'] + 1e-6:
            raise RenderError('audio_timing_mismatch', f'{path.name}: narration {actual:.6f}s does not match scheduled {expected:.6f}s (one-frame tolerance)')
    return [pair[0] for pair in pairs]


def inspect_video(path: Path, *, frames: int, fps: int, timeout: float = 300) -> dict[str, Any]:
    result = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', str(path)],
                            capture_output=True, text=True, check=True, timeout=timeout)
    metadata = json.loads(result.stdout)
    videos = [stream for stream in metadata['streams'] if stream['codec_type'] == 'video']
    audios = [stream for stream in metadata['streams'] if stream['codec_type'] == 'audio']
    if len(videos) != 1 or len(audios) != 1 or videos[0]['codec_name'] != 'h264' or audios[0]['codec_name'] != 'aac':
        raise RenderError('output_check_failed', 'Expected one H.264 track and one AAC track')
    video, audio = videos[0], audios[0]
    duration = frames / fps
    if int(video['nb_read_frames']) != frames or abs(float(video['duration']) - duration) > 1e-5:
        raise RenderError('output_check_failed', 'Decoded frame count or video duration differs from the schedule')
    if abs(float(video['duration']) - float(audio['duration'])) > 0.1:
        raise RenderError('output_check_failed', 'Audio/video duration difference exceeds 0.1 seconds')
    run_ffmpeg(['-i', str(path), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'], timeout)
    return {'frames': frames, 'fps': fps, 'duration_seconds': duration, 'audio_duration_seconds': float(audio['duration']),
            'video_codec': video['codec_name'], 'audio_codec': audio['codec_name'], 'decodable': True, 'sha256': sha256(path)}


def compose(manifest_path: Path, output: Path, *, timeout: float = 300, on_event=None, retry_shot_id: str | None = None, render_shot_ids: list[str] | None = None) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    if not math.isfinite(timeout) or timeout <= 0:
        raise RenderError('invalid_input', 'timeout must be positive and finite')
    with owned_workspace(output, Path(manifest['assets_dir']), 'compose') as workspace:
        try:
            return _compose(manifest, workspace, timeout=timeout, on_event=on_event, retry_shot_id=retry_shot_id, render_shot_ids=render_shot_ids)
        except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
            write_json(workspace / 'compose-status.json', {'status': 'failed', 'candidate': None, 'shots': [],
                       'code': getattr(error, 'code', 'compose_failed'), 'reason': str(error)})
            raise


def _compose(manifest: dict[str, Any], output: Path, *, timeout: float, on_event, retry_shot_id: str | None = None, render_shot_ids: list[str] | None = None) -> dict[str, Any]:
    narration = audio_inputs(manifest)
    audio_hashes = {str(path): sha256(path) for path in narration}
    output = output.resolve()
    state = render_shots(manifest, output / 'render', on_event=on_event, retry_shot_id=retry_shot_id, render_shot_ids=render_shot_ids)
    result_path = output / 'compose-status.json'
    result = {'status': 'running', 'shots': state['shots'], 'candidate': None}
    write_json(result_path, result)
    if state['status'] != 'completed':
        result.update(status='failed', code='shots_failed', reason='One or more shots failed; retry the same command after repair')
        write_json(result_path, result)
        return result
    segments_dir = output / 'segments'
    segments_dir.mkdir(parents=True, exist_ok=True)
    concat_file = segments_dir / 'concat.txt'
    candidate = output / 'candidate.mp4'
    pending = output / 'candidate.pending.mp4'
    try:
        for shot, entry in zip(manifest['shots'], state['shots']):
            segment = segments_dir / f"{shot['id']}.mp4"
            receipt_path = segment.with_suffix('.json')
            key = hashlib.sha256(json.dumps({'frames': entry['frame_hashes'], 'fps': manifest['fps'], 'encoder': 'libx264-threads1-crf18-yuv420p-v1'}, sort_keys=True).encode()).hexdigest()
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            if receipt.get('key') == key and segment.is_file() and sha256(segment) == receipt.get('sha256'):
                continue
            try:
                # Revision caches may hard-link immutable segments from an old
                # run. Replace a changed segment without changing that old run.
                segment.unlink(missing_ok=True)
                run_ffmpeg(['-framerate', str(manifest['fps']), '-start_number', '0', '-i', str(Path(entry['frames_dir']) / 'frame-%06d.png'),
                            '-frames:v', str(shot['frames']), '-an', '-c:v', 'libx264', '-threads', '1', '-crf', '18',
                            '-pix_fmt', 'yuv420p', '-map_metadata', '-1', str(segment)], timeout)
            except (RenderError, OSError) as error:
                entry.update(status='failed', code=getattr(error, 'code', 'encode_failed'), reason=str(error), phase='encode')
                raise
            write_json(receipt_path, {'key': key, 'sha256': sha256(segment)})
        concat_file.write_text(''.join(f"file '{shot['id']}.mp4'\n" for shot in manifest['shots']), encoding='utf-8')
        inputs = ['-f', 'concat', '-safe', '1', '-i', str(concat_file)]
        for audio in narration:
            inputs.extend(['-i', str(audio)])
        total_frames = sum(shot['frames'] for shot in manifest['shots'])
        duration = total_frames / manifest['fps']
        if len(narration) == 1:
            filters = f'[1:a]aresample=48000,apad,atrim=duration={duration:.9f},asetpts=PTS-STARTPTS[audio]'
        else:
            parts = [f"[{index + 1}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={shot['frames'] / manifest['fps']:.9f},asetpts=PTS-STARTPTS[a{index}]" for index, shot in enumerate(manifest['shots'])]
            parts.append(''.join(f'[a{index}]' for index in range(len(narration))) + f'concat=n={len(narration)}:v=0:a=1[audio]')
            filters = ';'.join(parts)
        run_ffmpeg([*inputs, '-filter_complex', filters, '-map', '0:v:0', '-map', '[audio]', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-threads', '1', '-t', f'{duration:.9f}', '-map_metadata', '-1',
                    '-movflags', '+faststart', str(pending)], timeout)
        checks = inspect_video(pending, frames=total_frames, fps=manifest['fps'], timeout=timeout)
        for entry in state['shots']:
            if any(sha256(Path(item['path'])) != item['sha256'] for item in entry['dependencies']):
                raise RenderError('input_changed', f"{entry['id']}: shot resource changed during composition")
        if any(sha256(Path(path)) != digest for path, digest in audio_hashes.items()):
            raise RenderError('input_changed', 'Narration changed during rendering')
        pending.replace(candidate)
        result.update(status='completed', candidate=str(candidate), checks=checks)
    except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
        result.update(status='failed', code=getattr(error, 'code', 'compose_failed'), reason=str(error), candidate=None)
    finally:
        pending.unlink(missing_ok=True)
    write_json(result_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout-seconds', type=float, default=300)
    args = parser.parse_args()
    try:
        if not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
            raise RenderError('invalid_input', 'timeout-seconds must be positive')
        result = compose(args.manifest, args.output, timeout=args.timeout_seconds,
                         on_event=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'completed' else 1
    except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'failed', 'code': getattr(error, 'code', 'compose_failed'), 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
