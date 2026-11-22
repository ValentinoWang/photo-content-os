#!/usr/bin/env python3
"""Schedule promotional shots on musical downbeats and produce one PCM mix."""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / 'scripts', ROOT / 'scripts/video_render'):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from studio.music_analysis import BeatMapUnavailable, load_beat_map
from animation_duration import declared_duration


# Leave 1 dB of headroom under full scale so later mixing never clips.
PEAK_LIMIT = 10 ** (-1 / 20)


class PlanError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def positive(value, name):
    if type(value) is not int or value <= 0:
        raise PlanError('invalid_input', f'{name} must be a positive integer')
    return value


def auto_end(downbeats, cursor, origin, fps, previous_frame, html_path, sid):
    """Fewest whole bars whose frames cover the shot's declared animation length D."""
    try:
        declared = declared_duration(Path(html_path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as exc:
        raise PlanError('animation_duration_invalid', f'{sid}: {exc}') from exc
    if declared is None:
        raise PlanError('animation_duration_missing', f'{sid}: bars "auto" needs const D in the shot HTML')
    for end in range(cursor + 1, len(downbeats)):
        frames = math.floor((downbeats[end] - origin) * fps + .5) - previous_frame
        if frames * 1000 >= declared * fps * 1000:
            return end
    raise PlanError('track_too_short', f'{sid}: not enough bars left to cover D={float(declared):.3f}s')


def create_plan(spec, media_root, out, *, beat_map=None, spec_dir=None):
    if not isinstance(spec, dict):
        raise PlanError('invalid_input', 'spec must be an object')
    track_id = spec.get('track_id')
    if not isinstance(track_id, str) or not re.fullmatch(r'[a-f0-9]{64}', track_id):
        raise PlanError('invalid_input', 'track_id must be a 64-character lowercase hex identifier')
    fps = positive(spec.get('fps'), 'fps')
    width = positive(spec.get('width'), 'width')
    height = positive(spec.get('height'), 'height')
    if width % 2 or height % 2:
        raise PlanError('invalid_input', 'width and height must be even')
    start = positive(spec.get('start_bar'), 'start_bar') - 1
    shots = spec.get('shots')
    if not isinstance(shots, list) or not shots:
        raise PlanError('invalid_input', 'shots must be a nonempty list')
    beat_map = load_beat_map(track_id, media_root=Path(media_root)) if beat_map is None else beat_map
    downbeats = beat_map['downbeats']
    if start >= len(downbeats):
        raise PlanError('track_too_short', 'starting downbeat is unavailable')
    origin = downbeats[start]
    html_root = Path(spec_dir or Path.cwd()).resolve() / spec.get('assets_dir', '.')
    cursor = start
    previous_frame = 0
    render_shots, plan_shots, ids = [], [], set()
    for shot in shots:
        if not isinstance(shot, dict):
            raise PlanError('invalid_input', 'each shot must be an object')
        sid, html = shot.get('id'), shot.get('html')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', sid) or sid in ids:
            raise PlanError('invalid_input', 'shot ids must be unique safe names')
        if not isinstance(html, str) or not html:
            raise PlanError('invalid_input', 'shot html is required')
        ids.add(sid)
        if shot.get('bars') == 'auto':
            end = auto_end(downbeats, cursor, origin, fps, previous_frame, html_root / html, sid)
        else:
            end = cursor + positive(shot.get('bars'), 'bars')
        if end >= len(downbeats) or downbeats[end] > beat_map['duration_seconds']:
            raise PlanError('track_too_short', 'ending downbeat is unavailable or beyond the track')
        boundary = math.floor((downbeats[end] - origin) * fps + .5)
        if boundary <= previous_frame:
            raise PlanError('invalid_input', 'shot must occupy at least one frame')
        render_shots.append(dict(id=sid, html=html, frames=boundary - previous_frame, start_frame=previous_frame))
        plan_shots.append(dict(id=sid, start_seconds=downbeats[cursor], end_seconds=downbeats[end], start_bar=cursor + 1, end_bar=end + 1))
        previous_frame, cursor = boundary, end
    duration = previous_frame / fps
    if origin + duration > beat_map['duration_seconds'] + 1e-9:
        raise PlanError('track_too_short', 'scheduled audio exceeds track duration')
    fade = spec.get('fade_out_seconds', 0)
    if isinstance(fade, bool) or not isinstance(fade, (int, float)) or not math.isfinite(fade) or fade < 0 or fade > duration:
        raise PlanError('invalid_input', 'fade_out_seconds must be between zero and the duration')
    sfx = spec.get('sfx', [])
    if not isinstance(sfx, list):
        raise PlanError('invalid_input', 'sfx must be a list')
    by_id = {s['id']: s for s in render_shots}
    base = Path(spec_dir or Path.cwd()).resolve()
    effects = []
    for effect in sfx:
        if not isinstance(effect, dict) or effect.get('shot') not in by_id:
            raise PlanError('invalid_input', 'sfx shot must identify a shot')
        offset, gain, file = effect.get('offset_frames'), effect.get('gain_db'), effect.get('file')
        if type(offset) is not int or isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(gain) or not isinstance(file, str) or not file:
            raise PlanError('invalid_input', 'invalid sfx offset, gain or file')
        effects.append(((base / file).resolve(), by_id[effect['shot']]['start_frame'] + offset, gain))
    folder = Path(media_root) / 'library' / 'music' / track_id
    try:
        metadata = json.loads((folder / 'track.json').read_text(encoding='utf-8'))
        audio_file = metadata['audio_file']
        if not isinstance(audio_file, str) or not audio_file:
            raise ValueError('audio_file must be a nonempty string')
        audio = (folder / audio_file).resolve()
        if not audio.is_relative_to(folder.resolve()):
            raise ValueError('audio_file escapes track directory')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PlanError('track_unreadable', str(exc)) from exc
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    wav = out / 'premix.wav'
    samples = (previous_frame * 48000 * 2 + fps) // (2 * fps)
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(origin), '-i', str(audio)]
    for file, _, _ in effects:
        command += ['-i', str(file)]
    filters = [f'[0:a]aresample=48000,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.03' + (f',afade=t=out:st={duration-fade}:d={fade}' if fade else '') + '[music]']
    labels = ['[music]']
    for i, (_, frame, gain) in enumerate(effects, 1):
        sample_offset = round(frame * 48000 / fps)
        trim = f'atrim=start_sample={-sample_offset},asetpts=PTS-STARTPTS,' if sample_offset < 0 else ''
        delay = max(0, sample_offset)
        filters.append(f'[{i}:a]aresample=48000,{trim}volume={gain}dB,adelay={delay}S:all=1[s{i}]')
        labels.append(f'[s{i}]')
    filters.append(''.join(labels) + f'amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit={PEAK_LIMIT}:level=0:latency=1,apad,atrim=end_sample={samples},asetpts=PTS-STARTPTS[out]')
    command += ['-filter_complex', ';'.join(filters), '-map', '[out]', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(wav)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise PlanError('ffmpeg_unavailable', str(exc)) from exc
    if result.returncode:
        raise PlanError('ffmpeg_failed', result.stderr[-800:])
    render = dict(width=width, height=height, fps=fps, shots=render_shots)
    if 'fonts' in spec:
        render['fonts'] = [{**font, 'path': str((base / font['path']).resolve())} for font in spec['fonts']]
    render['assets_dir'] = str((base / spec.get('assets_dir', '.')).resolve())
    composition = {**render, 'narration_wav': str(wav)}
    plan = {'track_id': track_id, 'shots': plan_shots}
    for name, value in [('render-manifest.json', render), ('compose-manifest.json', composition), ('plan.json', plan)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return render, composition, plan


def main(argv=None):
    class JsonArgumentParser(argparse.ArgumentParser):
        def error(self, message):
            raise PlanError('invalid_input', message)

    parser = JsonArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--media-root', required=True)
    parser.add_argument('--out', required=True)
    try:
        args = parser.parse_args(argv)
        path = Path(args.spec).resolve()
        spec = json.loads(path.read_text(encoding='utf-8'))
        create_plan(spec, Path(args.media_root), Path(args.out), spec_dir=path.parent)
        return 0
    except (PlanError, BeatMapUnavailable) as exc:
        print(json.dumps({'code': exc.code, 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'code': 'input_unreadable', 'message': str(exc)}, ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
