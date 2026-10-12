"""Measure native Photo output and produce the bounded MC candidate view."""
from __future__ import annotations

import array
import copy
from datetime import datetime, timezone
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

from edit_backends.kdenlive_render import probe_media, review_module
from media_common import file_sha256
from openclaw_product_contract import ProductContractError, video_digest


def ffmpeg(args, *, cwd=None):
    return subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-v', 'error', '-xerror', '-y', *args],
                          cwd=cwd, capture_output=True, timeout=1800, check=True)


def waveform_peaks(source: Path, *, count: int = 400) -> list[float]:
    if type(count) is not int or not 1 <= count <= 400:
        raise ProductContractError('video_waveform_rejected')
    info = probe_media(source)
    audio = next((s for s in info['streams'] if s.get('codec_type') == 'audio'), None)
    if audio is None:
        raise ProductContractError('video_waveform_audio_missing')
    duration = float(audio.get('duration') or info['format']['duration'])
    samples_per_bin = max(1, math.ceil(duration * 8000 / count))
    peaks = [0.0] * count
    seen = 0
    # Stream bounded PCM chunks; never hold an original audio file in memory.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source),
                                    '-map', '0:a:0', '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                                   stdout=subprocess.PIPE, stderr=errors)
        try:
            while chunk := process.stdout.read(8192):
                values = array.array('h', chunk)
                import sys
                if sys.byteorder != 'little':
                    values.byteswap()
                for value in values:
                    index = min(count - 1, seen // samples_per_bin)
                    peaks[index] = max(peaks[index], abs(value) / 32768)
                    seen += 1
            if process.wait(timeout=30) or not seen:
                raise ProductContractError('video_waveform_decode_failed')
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
    return peaks[:min(count, math.ceil(seen / samples_per_bin))]


def burn_subtitles(video: Path, subtitles: Path, output: Path) -> float:
    cues = review_module().read_srt_cues(subtitles)
    stream = next(s for s in probe_media(video)['streams'] if s.get('codec_type') == 'video')
    width, height = stream['width'], stream['height']
    def stamp(value):
        cs = round(value * 100)
        sec, cs = divmod(cs, 100); minute, sec = divmod(sec, 60); hour, minute = divmod(minute, 60)
        return f'{hour}:{minute:02}:{sec:02}.{cs:02}'
    def text(value):
        return value.replace('\\', '\\u005c').replace('{', '\\{').replace('}', '\\}').replace('\n', '\\N')
    with tempfile.TemporaryDirectory(prefix='pf-subtitles-') as directory:
        root = Path(directory)
        lines = ['[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {width}', f'PlayResY: {height}',
                 '[V4+ Styles]', 'Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV',
                 f'Style: Default,PingFang SC,{max(12, height // 25)},&H00FFFFFF,&H00000000,1,1,0,2,10,10,0',
                 '[Events]', 'Format: Layer, Start, End, Style, Text']
        for start, end, value in cues:
            override = f'{{\\an5\\pos({width/2},{height*.9})\\clip(0,{round(height*.8)},{width},{height})}}'
            lines.append(f'Dialogue: 0,{stamp(start)},{stamp(end)},Default,{override}{text(value)}')
        (root / 'captions.ass').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        ffmpeg(['-i', str(video), '-vf', 'ass=filename=captions.ass', '-map', '0:v:0', '-map', '0:a:0',
                '-c:v', 'libx264', '-threads', '1', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy',
                '-map_metadata', '-1', '-movflags', '+faststart', str(output)], cwd=root)
    return .8


def preview_video(video: Path, output: Path) -> dict:
    info = probe_media(video)
    v = next(s for s in info['streams'] if s.get('codec_type') == 'video')
    duration = float(v.get('duration') or info['format']['duration'])
    factor = min(1, 480 / min(v['width'], v['height']), 854 / max(v['width'], v['height']))
    width, height = max(2, int(v['width'] * factor) // 2 * 2), max(2, int(v['height'] * factor) // 2 * 2)
    budget = int(20_000_000 * 8 * .94 / duration) - 128000
    if budget < 32000:
        raise ProductContractError('video_preview_budget_exceeded')
    ffmpeg(['-i', str(video), '-vf', f'scale={width}:{height}', '-map', '0:v:0', '-map', '0:a:0',
            '-c:v', 'libx264', '-threads', '1', '-b:v', str(min(1_000_000, budget)), '-maxrate', str(min(1_000_000, budget)),
            '-bufsize', str(min(2_000_000, budget * 2)), '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
            '-map_metadata', '-1', '-movflags', '+faststart', str(output)])
    if not 0 < output.stat().st_size <= 20_000_000:
        output.unlink()
        raise ProductContractError('video_preview_size_rejected')
    actual = probe_media(output)
    videos = [s for s in actual['streams'] if s.get('codec_type') == 'video']
    audios = [s for s in actual['streams'] if s.get('codec_type') == 'audio']
    if len(videos) != 1 or len(audios) != 1 or videos[0]['codec_name'] != 'h264' or audios[0]['codec_name'] != 'aac':
        raise ProductContractError('video_preview_container_rejected')
    ffmpeg(['-i', str(output), '-f', 'null', '-'])
    return {'artifact': {'artifactId': 'art_' + file_sha256(output)[:32], 'sha256': 'sha256:' + file_sha256(output),
                         'mimeType': 'video/mp4', 'sizeBytes': output.stat().st_size,
                         'downloadPath': '/openclaw/media/api/jobs/local/video-artifacts/art_' + file_sha256(output)[:32]},
            'width': width, 'height': height, 'shortEdge': min(width, height), 'longEdge': max(width, height)}


def cut_projection(plan: dict, source_duration: float) -> list[dict]:
    cuts, cursor = [], 0.0
    # The execution map uses the editor's frame grid. Resampling a source at
    # another rate can leave half a frame of header duration; that is no edit.
    planned_end = round(source_duration * plan['fps']) / plan['fps'] if plan.get('time_map') else source_duration
    for item in plan.get('time_map', []):
        if item['source_start'] > cursor:
            cuts.append({'kind': 'silence', 'startSeconds': cursor, 'endSeconds': item['source_start']})
        cursor = item['source_end']
    if plan.get('time_map') and cursor < planned_end - 1e-6:
        cuts.append({'kind': 'silence', 'startSeconds': cursor, 'endSeconds': planned_end})
    # Kind comes from executed, frame-aligned cut facts; never infer it from a gap.
    if cuts:
        executed = plan.get('executed_cuts')
        if not isinstance(executed, list) or len(executed) != len(cuts):
            raise ProductContractError('photo_cut_projection_missing')
        for cut, fact in zip(cuts, executed):
            if abs(cut['startSeconds'] - fact['startSeconds']) > 1e-6 or abs(cut['endSeconds'] - fact['endSeconds']) > 1e-6:
                raise ProductContractError('photo_cut_projection_missing')
            cut['kind'] = fact['kind']
            cut['endSeconds'] = min(cut['endSeconds'], source_duration)
    return cuts


def failed_shot_progress(native: dict, descriptor: dict, fps: float) -> dict:
    """Bound real failed-render counters without exposing native diagnostics."""
    known = {row['shot']['shotId'] for row in descriptor['shots']}
    selected = {descriptor['retryShotId']} if descriptor.get('retryShotId') else set(descriptor.get('renderShotIds', known))
    progress = []
    for shot in native.get('shots', []):
        if shot.get('id') not in known or shot['id'] not in selected or shot.get('status') not in {'failed', 'completed'}:
            continue
        code = shot.get('code') if shot['status'] == 'failed' else None
        if code is not None and (not isinstance(code, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,127}', code)):
            code = 'photo_execution_failed'
        progress.append({'shotId': shot['id'], 'status': shot['status'], 'renderedFrames': shot.get('progress_frames', 0),
                         'totalFrames': shot['total_frames'], 'durationSeconds': shot['total_frames'] / fps,
                         'failureCode': code, 'lineNumber': None, 'assetName': None, 'timeoutSeconds': None, 'codeExcerpt': None})
    failed = [shot['shotId'] for shot in progress if shot['status'] == 'failed']
    return {'shotProgress': progress, 'failedShotId': failed[0] if len(failed) == 1 else None}


def project_candidate(*, native: dict, descriptor: dict, source: Path, original_hashes: dict[Path, str],
                      output_dir: Path, workspace: Path) -> dict:
    if native.get('status') not in {'candidate', 'completed'}:
        raise ProductContractError('photo_native_candidate_missing')
    video = Path(native.get('output') or native.get('candidate') or '')
    if not video.is_file() or video in original_hashes:
        raise ProductContractError('photo_native_candidate_missing')
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(native['manifest']).read_text()) if native.get('manifest') else {}
    if plan and (plan['output']['sha256'] != file_sha256(video) or plan['output']['path'] != str(video)):
        raise ProductContractError('photo_native_candidate_changed')
    if plan:
        for item in plan['inputs']:
            path = Path(item['path'])
            if file_sha256(path) != item['sha256']:
                raise ProductContractError('photo_native_candidate_changed')
    metadata = probe_media(video)
    v = next(s for s in metadata['streams'] if s.get('codec_type') == 'video')
    duration = float(v['duration']); fps = float(Fraction(v['avg_frame_rate']))
    expected = native.get('frames') if plan else native['checks']['frames']
    source_info = probe_media(source)
    source_stream = next((s for s in source_info['streams'] if s.get('codec_type') == 'video'), None)
    source_duration = float((source_stream or {}).get('duration') or source_info['format']['duration'])
    cuts = cut_projection(plan, source_duration)
    subtitle_path = Path(plan['subtitles']) if plan.get('subtitles') else output_dir / 'subtitles.srt'
    if not plan.get('subtitles'):
        rows = []
        for row in descriptor['shots']:
            text = row['subtitle']
            if text:
                from edit_backends.kdenlive_render import srt_timestamp
                shot = row['shot']
                rows.append(f"{len(rows)+1}\n{srt_timestamp(shot['startSeconds'])} --> {srt_timestamp(shot['endSeconds'])}\n{text}")
        if not rows:
            raise ProductContractError('photo_subtitle_projection_missing')
        subtitle_path.write_text('\n\n'.join(rows) + '\n', encoding='utf-8')
    subtitle_text = subtitle_path.read_text(encoding='utf-8')
    if re.search(r"(?:^|[\s\"'=(:：])(?:/(?:[\w.-]+/)+[^\s\"']*|[A-Za-z]:[\\/][^\s\"']*)", subtitle_text):
        raise ProductContractError('photo_subtitle_projection_rejected')
    if len(subtitle_text.encode()) > 200000 or '\x00' in subtitle_text:
        raise ProductContractError('photo_subtitle_projection_rejected')
    # Validate timeline before burning; malformed/out-of-bounds cues never render.
    review = review_module().check_output_video(video, original_hashes=original_hashes, subtitles=subtitle_path,
                                               expected_duration=expected / fps, expected_frames=expected, expected_fps=fps)
    subtitle_check = next(c for c in review['checks'] if c['check'] == 'subtitles')
    if subtitle_check['status'] != 'passed':
        raise ProductContractError('photo_subtitle_projection_rejected')
    if plan.get('subtitle_burned_in'):
        captioned = video
        bottom = plan['subtitle_bottom_ratio']
    else:
        captioned = output_dir / 'captioned.mp4'
        bottom = burn_subtitles(video, subtitle_path, captioned)
    preview_path = output_dir / 'preview.mp4'
    preview = preview_video(captioned, preview_path)
    measured = review_module().check_output_video(captioned, original_hashes=original_hashes, subtitles=subtitle_path,
                                                 expected_duration=expected/fps, expected_frames=expected, expected_fps=fps)
    groups = {}
    for c in measured['checks']:
        groups.setdefault(c['check'], []).append(c)
    def status(names):
        values = [c['status'] for name in names for c in groups.get(name, [])]
        return 'fail' if 'failed' in values else ('pass' if values and len(values) >= len(names) and all(s == 'passed' for s in values) else 'unknown')
    frames = next(c for c in groups['frames'] if 'frames' in c['details'])['details']['frames']
    av = groups['av_duration'][0]['details'].get('stream_seconds')
    if av is None or len(av) != 2:
        raise ProductContractError('photo_av_projection_missing')
    black = subprocess.run(['ffmpeg', '-nostdin', '-v', 'info', '-i', str(video), '-vf', 'blackframe=amount=98:threshold=32',
                            '-an', '-f', 'null', '-'], capture_output=True, text=True, check=True, timeout=1800)
    checks = {'playable': status(['decode', 'tracks']), 'avSync': status(['av_duration']),
              'frameCount': status(['frames']), 'sourceUnchanged': status(['original_integrity']),
              'subtitles': status(['subtitles']), 'blackFrames': 'fail' if re.search(r'\bpblack:', black.stderr) else 'pass',
              'avOffsetSeconds': abs(av[0] - av[1]), 'avOffsetLimitSeconds': .1, 'expectedFrames': expected, 'actualFrames': frames}
    successful = all(checks[k] == 'pass' for k in ('playable', 'avSync', 'frameCount', 'sourceUnchanged', 'subtitles', 'blackFrames'))
    # Direct composition's source is the original narration, with no edit cuts.
    removed = sum(c['endSeconds'] - c['startSeconds'] for c in cuts)
    if abs(source_duration - removed - duration) > .1:
        raise ProductContractError('photo_source_timing_rejected')
    placements = {}
    executed_placements = plan.get('animation_placements', [])
    if not plan and descriptor['animations']:
        rendered = {s['id']: s for s in native.get('shots', []) if s['status'] == 'completed'}
        if len({a['shotId'] for a in descriptor['animations']}) != len(descriptor['animations']):
            raise ProductContractError('photo_animation_projection_missing')
        executed_placements = []
        for animation in descriptor['animations']:
            shot = rendered.get(animation['shotId'])
            if shot is None:
                raise ProductContractError('photo_animation_projection_missing')
            start = shot['start_frame'] / fps
            executed_placements.append({'animation_id': animation['animationId'], 'start': start,
                                        'end': start + shot.get('animation_frames', shot['total_frames']) / fps})
    for placement in executed_placements:
        aid = placement['animation_id']
        if aid in placements:
            if abs(placements[aid]['end'] - placement['start']) > 1e-6:
                raise ProductContractError('photo_animation_projection_missing')
            placements[aid]['end'] = placement['end']
        else:
            placements[aid] = copy.deepcopy(placement)
    if set(placements) != {a['animationId'] for a in descriptor['animations']}:
        raise ProductContractError('photo_animation_projection_missing')
    animations = []
    for original in descriptor['animations']:
        placement = placements[original['animationId']]
        animation = copy.deepcopy(original)
        animation.update(suggestedStartSeconds=placement['start'], durationSeconds=placement['end'] - placement['start'], timeBasis='edited')
        animations.append(animation)
    candidate = {'publicCandidateId': 'candidate_' + file_sha256(captioned)[:32], 'identity': copy.deepcopy(descriptor['identity']),
                 'status': 'candidate' if successful else 'check_failed', 'description': '', 'provenance': 'native_readback',
                 'durationSeconds': duration, 'sourceDurationSeconds': source_duration, 'frameCount': frames, 'fps': fps,
                 'removedSeconds': removed, 'cutCount': len(cuts), 'cuts': cuts, 'animations': animations, 'checks': checks,
                 'subtitles': subtitle_text, 'subtitleBurnedIn': True, 'subtitleBottomRatio': bottom, 'preview': preview,
                 'returnedAt': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), 'waveformPeaks': waveform_peaks(source)}
    candidate['candidateDigest'] = video_digest(candidate)
    progress = {'shotProgress': [], 'waveformPeaks': candidate['waveformPeaks'], 'waveformSource': 'source' if plan else 'narration'}
    if plan:
        progress.update(precutCount=len(cuts), exported=True)
    for shot in native.get('shots', []):
        if shot['id'] not in {r['shot']['shotId'] for r in descriptor['shots']}:
            raise ProductContractError('photo_shot_identity_rejected')
        selected = [descriptor['retryShotId']] if descriptor.get('retryShotId') else descriptor.get('renderShotIds')
        if selected is not None and shot['id'] not in selected:
            continue
        shot_fps = native.get('shot_fps', fps)
        progress['shotProgress'].append({'shotId': shot['id'], 'status': 'completed' if shot['status'] == 'completed' else 'failed',
                                        'renderedFrames': shot.get('progress_frames', 0), 'totalFrames': shot['total_frames'],
                                        'durationSeconds': shot['total_frames'] / shot_fps, 'failureCode': None,
                                        'lineNumber': None, 'assetName': None, 'timeoutSeconds': None, 'codeExcerpt': None})
        if not plan and shot['status'] == 'completed':
            from video_derivatives import jpeg_frame
            poster = output_dir / ('poster-' + shot['id'] + '.jpg')
            measured = jpeg_frame(Path(shot['frames_dir']) / 'frame-000000.png', poster)
            progress['shotProgress'][-1].update(poster_ref=str(poster.resolve().relative_to(workspace.resolve())),
                poster_width=measured['width'], poster_height=measured['height'], poster_short_edge=measured['shortEdge'])
    payload = {'candidate': candidate, 'preview_ref': str(preview_path.resolve().relative_to(workspace.resolve())), 'progress': progress}
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False)
    if len(encoded.encode()) > 1_000_000:
        raise ProductContractError('video_candidate_size_rejected')
    (output_dir / 'candidate.json').write_text(encoded + '\n')
    return payload
