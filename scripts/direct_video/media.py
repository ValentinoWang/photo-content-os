"""Reuse Photo frame rendering, composition and candidate checks for direct jobs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import wave

from video_render.compose import compose, concat_schedule, run_ffmpeg
from video_render.multi_shot import RenderError, load_manifest, owned_workspace, render_shots, write_json
from direct_video.layout import inspect_layout

FPS = 30


class OutputCheckError(RenderError):
    def __init__(self, checks: dict):
        super().__init__('output_check_failed', 'Output checks failed')
        self.checks = checks


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def manifest(root: Path, shots: list[dict]) -> dict:
    font = os.environ.get('DIRECT_VIDEO_FONT') or str(Path('/System/Library/Fonts/STHeiti Medium.ttc'))
    value = {'width': 1080, 'height': 1920, 'fps': FPS, 'assets_dir': str(root / 'shots'),
             'fonts': [{'path': font}], 'shots': []}
    browser = os.environ.get('VIDEO_RENDER_BROWSER') or os.environ.get('VIDEO_RENDER_TEST_BROWSER')
    if browser:
        value['browser_executable'] = browser
    cursor = 0
    for shot in shots:
        frames = max(1, round((shot['measuredSeconds'] or shot['estimatedSeconds']) * FPS))
        value['shots'].append({'id': shot['shotId'], 'html': shot['shotId'] + '.html',
                               'frames': frames, 'start_frame': cursor})
        cursor += frames
    return value


class LocalMedia:
    def render(self, root: Path, shot: dict) -> dict:
        sid = shot['shotId']
        path = root / 'manifests' / (sid + '.json')
        write_json(path, manifest(root, [shot]))
        loaded = load_manifest(path)
        state = render_shots(loaded, root / 'cache' / sid)
        if state['status'] != 'completed':
            raise RenderError('render_failed', 'Shot render failed')
        frames = loaded['shots'][0]['frames']
        source = root / 'cache' / sid / sid / 'frames' / f'frame-{min(frames - 1, int(.8 * frames)):06d}.png'
        from video_derivatives import jpeg_frame
        poster = root / 'posters' / (sid + '.jpg')
        poster.parent.mkdir(parents=True, exist_ok=True)
        pending = poster.with_name(sid + '.pending.jpg')
        try:
            jpeg_frame(source, pending)
            pending.replace(poster)
        finally:
            pending.unlink(missing_ok=True)
        frame_root = source.parent
        boxes = json.loads((frame_root / 'boxes.json').read_text())
        atomic_bytes(root / 'boxes' / (sid + '.json'), json.dumps(boxes, ensure_ascii=False).encode())
        for fraction in (.3, .6, .9):
            frame = frame_root / f'frame-{min(frames - 1, int(fraction * frames)):06d}.png'
            destination = root / 'review-frames' / sid / f'{int(fraction * 10)}.jpg'
            destination.parent.mkdir(parents=True, exist_ok=True)
            jpeg_frame(frame, destination)
        self.encode_clip(root, shot)
        return inspect_layout(poster)

    def encode_clip(self, root: Path, shot: dict) -> Path:
        sid = shot['shotId']
        count = max(1, round((shot['measuredSeconds'] or shot['estimatedSeconds']) * FPS))
        frames = root / 'cache' / sid / sid / 'frames'
        if any(not (frames / f'frame-{index:06d}.png').is_file() for index in range(count)):
            raise FileNotFoundError('clip_frames_unavailable')
        target = root / 'clips' / (sid + '.mp4')
        target.parent.mkdir(parents=True, exist_ok=True)
        pending = target.with_suffix('.pending.mp4')
        try:
            run_ffmpeg(['-framerate', str(FPS), '-start_number', '0', '-i', str(frames / 'frame-%06d.png'),
                        '-frames:v', str(count), '-vf', 'scale=360:640', '-an', '-c:v', 'libx264',
                        '-threads', '1', '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(pending)])
            pending.replace(target)
        finally:
            pending.unlink(missing_ok=True)
        return target

    def review_frames(self, root: Path, shot: dict) -> list[Path]:
        return [root / 'review-frames' / shot['shotId'] / f'{n}.jpg' for n in (3, 6, 9)]

    def transcribe(self, path: Path) -> dict:
        from transcribe_audio import DEFAULT_FUNASR_MODEL, FunASRProvider
        return FunASRProvider(DEFAULT_FUNASR_MODEL).transcribe(path, language='zh')

    def compose(self, root: Path, job: dict) -> dict:
        value = manifest(root, job['shots'])
        frames = sum(s['frames'] for s in value['shots'])
        narrated = job['narration']['status'] == 'ready'
        pending = root / 'output.pending.mp4'
        if narrated:
            # Seed the composer's existing content-addressed cache from shots
            # rendered immediately after writing. Composition never needs to
            # regenerate an unaffected shot.
            with owned_workspace(root / 'composition', root / 'shots', 'compose') as workspace:
                destination = workspace / 'render'
                destination.mkdir(parents=True, exist_ok=True)
                entries = []
                for shot in value['shots']:
                    sid = shot['id']
                    cache = root / 'cache' / sid
                    entry = json.loads((cache / 'shot-status.json').read_text())['shots'][0]
                    target = destination / sid
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(cache / sid, target, copy_function=os.link)
                    entry['frames_dir'] = str(target / 'frames')
                    entries.append(entry)
                write_json(destination / 'shot-status.json', {'shots': entries})
            value['narration_wav'] = str(root / 'narration.wav')
            path = root / 'manifests' / 'compose.json'
            write_json(path, value)
            state = compose(path, root / 'composition')
            if state['status'] != 'completed':
                raise RenderError('compose_failed', 'Composition failed')
            shutil.copyfile(state['candidate'], pending)
        else:
            segments = root / 'silent'
            segments.mkdir(exist_ok=True)
            for shot in value['shots']:
                sid = shot['id']
                run_ffmpeg(['-framerate', str(FPS), '-start_number', '0', '-i',
                            str(root / 'cache' / sid / sid / 'frames' / 'frame-%06d.png'),
                            '-frames:v', str(shot['frames']), '-an', '-c:v', 'libx264', '-threads', '1',
                            '-crf', '18', '-pix_fmt', 'yuv420p', str(segments / (sid + '.pending.mp4'))])
                (segments / (sid + '.pending.mp4')).replace(segments / (sid + '.mp4'))
            atomic_bytes(segments / 'concat.txt', concat_schedule(value['shots'], FPS).encode())
            run_ffmpeg(['-f', 'concat', '-safe', '1', '-i', str(segments / 'concat.txt'),
                        '-map', '0:v:0', '-an', '-c:v', 'copy', '-movflags', '+faststart', str(pending)])
        from video_candidate import check_direct_output
        checks = check_direct_output(pending, frames=frames, fps=FPS, narrated=narrated,
                                     diagnostic=root / 'checks' / 'output.json')
        if checks['playable'] != 'pass' or checks['frameCount'] != 'pass' or checks['blackFrames'] != 'pass' or (narrated and checks['avOffsetSeconds'] > .1):
            raise OutputCheckError(checks)
        pending.replace(root / 'output.mp4')
        return {'durationSeconds': frames / FPS, 'frames': frames, 'checks': checks}


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), 'rb') as audio:
        if audio.getcomptype() != 'NONE' or audio.getnframes() <= 0 or audio.getframerate() <= 0:
            raise ValueError('invalid WAV')
        expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
        actual = 0
        while block := audio.readframes(65536):
            actual += len(block)
        if actual != expected:
            raise ValueError('truncated WAV')
        return audio.getnframes() / audio.getframerate()
