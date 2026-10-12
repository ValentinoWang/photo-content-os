"""Local, confirmed shot inputs and bounded JPEG derivatives."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

from openclaw_product_contract import ProductContractError
from video_render.multi_shot import load_manifest, render_shots, sha256, write_json


def code_bytes(value: dict) -> bytes:
    if not isinstance(value, dict) or set(value) != {'language', 'code', 'contentDigest'} or value['language'] != 'html':
        raise ProductContractError('photo_render_code_rejected')
    code = value['code']
    if not isinstance(code, str) or not 0 < len(code) <= 100000:
        raise ProductContractError('photo_render_code_rejected')
    data = code.encode('utf-8')
    if value['contentDigest'] != 'sha256:' + hashlib.sha256(data).hexdigest():
        raise ProductContractError('photo_render_code_digest_rejected')
    return data


def inspect_jpeg(path: Path) -> dict:
    from video_candidate import ffmpeg
    try:
        if not 0 < path.stat().st_size <= 200000 or not path.read_bytes().startswith(b'\xff\xd8\xff'):
            raise ProductContractError('video_jpeg_rejected')
        probe = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(path)],
                               capture_output=True, text=True, check=True, timeout=15)
        streams = json.loads(probe.stdout)['streams']
        if len(streams) != 1 or streams[0]['codec_name'] != 'mjpeg' or int(streams[0].get('nb_read_frames', 0)) != 1:
            raise ProductContractError('video_jpeg_rejected')
        width, height = streams[0]['width'], streams[0]['height']
        if not 0 < min(width, height) <= 360:
            raise ProductContractError('video_jpeg_rejected')
        ffmpeg(['-i', str(path), '-f', 'null', '-'])
        return {'width': width, 'height': height, 'shortEdge': min(width, height)}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise ProductContractError('video_jpeg_rejected') from exc


def jpeg_frame(source: Path, output: Path) -> dict:
    from video_candidate import ffmpeg
    from edit_backends.kdenlive_render import probe_media
    output.parent.mkdir(parents=True, exist_ok=True)
    video = next(s for s in probe_media(source)['streams'] if s.get('codec_type') == 'video')
    factor = min(1, 360 / min(video['width'], video['height']))
    width, height = max(1, int(video['width'] * factor)), max(1, int(video['height'] * factor))
    for quality in (2, 5, 10, 20, 31):
        ffmpeg(['-i', str(source), '-map', '0:v:0', '-frames:v', '1', '-vf', f'scale={width}:{height}',
                '-c:v', 'mjpeg', '-threads', '1', '-q:v', str(quality), '-map_metadata', '-1', str(output)])
        if output.stat().st_size <= 200000:
            return inspect_jpeg(output)
    output.unlink(missing_ok=True)
    raise ProductContractError('video_jpeg_rejected')


def confirmed_manifest(manifest_path: Path, descriptor: dict, workspace: Path, output: Path, *, teaching=False, narration_path: Path | None = None, previous_manifest: Path | None = None) -> Path:
    """Keep unchanged asset paths stable so their verified caches remain reusable."""
    manifest = load_manifest(manifest_path)
    previous = json.loads(previous_manifest.read_text()) if previous_manifest is not None else {}
    prior_shots = {s['id']: s for s in previous.get('shots', [])}
    if not teaching and narration_path is not None:
        manifest['narration_wav'] = str(narration_path)
        for shot in manifest['shots']:
            shot.pop('narration_wav', None)
    rows = {row['shot']['shotId']: row for row in descriptor['shots']}
    animations = {a['shotId']: a for a in descriptor['animations']}
    if not {s['id'] for s in manifest['shots']} <= rows.keys():
        raise ProductContractError('photo_shot_identity_rejected')
    if not teaching and {s['id'] for s in manifest['shots']} != rows.keys():
        raise ProductContractError('photo_shot_identity_rejected')
    images = {}
    for item in descriptor.get('shotImageInputs', []):
        sid = item['shotId']
        if sid not in rows or sid in images:
            raise ProductContractError('photo_image_identity_rejected')
        # Agent writes this one controlled location after authenticated download.
        path = workspace / 'video-inputs' / descriptor['identity']['jobId'] / 'shot-images' / (sid + '.jpg')
        if not path.resolve().is_relative_to(workspace.resolve()):
            raise ProductContractError('photo_image_identity_rejected')
        meta = item['artifact']
        if meta['mimeType'] != 'image/jpeg' or path.stat().st_size != meta['sizeBytes'] or meta['sha256'] != 'sha256:' + sha256(path):
            raise ProductContractError('photo_image_digest_rejected')
        inspect_jpeg(path)
        images[sid] = path
    cursor = 0
    for shot in manifest['shots']:
        sid = shot['id']; row = rows[sid]
        template_duration = shot['frames'] / manifest['fps']
        if teaching:
            if sid not in animations:
                raise ProductContractError('photo_animation_projection_missing')
            duration = animations[sid]['durationSeconds']
        else:
            duration = row['shot']['endSeconds'] - row['shot']['startSeconds']
            if abs(row['shot']['startSeconds'] - cursor / manifest['fps']) > 1 / manifest['fps']:
                raise ProductContractError('photo_shot_timing_rejected')
        if not math.isfinite(duration) or duration <= 0:
            raise ProductContractError('photo_shot_timing_rejected')
        shot['frames'] = max(1, round(duration * manifest['fps']))
        shot['start_frame'] = cursor; cursor += shot['frames']
        if not teaching and sid in animations:
            animation_frames = round(animations[sid]['durationSeconds'] * manifest['fps'])
            if not 1 <= animation_frames <= shot['frames']:
                raise ProductContractError('photo_animation_timing_rejected')
            shot['animation_frames'] = animation_frames
        if row.get('renderCode') or sid in images:
            data = code_bytes(row['renderCode']) if row.get('renderCode') else Path(shot['html']).read_bytes()
            identity = hashlib.sha256(data + (images[sid].read_bytes() if sid in images else b'')).hexdigest()
            directory = Path(manifest['assets_dir']) / '.photo-confirmed' / identity
            if not directory.resolve().is_relative_to(Path(manifest['assets_dir']).resolve()):
                raise ProductContractError('photo_binding_rejected')
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / 'shot.html'
            if path.is_symlink():
                raise ProductContractError('photo_binding_rejected')
            if path.exists() and path.read_bytes() != data:
                raise ProductContractError('photo_render_code_digest_rejected')
            if not path.exists():
                path.write_bytes(data)
            if sid in images:
                target = directory / 'shot-image.jpg'
                if target.is_symlink() or (target.exists() and sha256(target) != sha256(images[sid])):
                    raise ProductContractError('photo_image_digest_rejected')
                if not target.exists():
                    shutil.copyfile(images[sid], target)
            shot['html'] = str(path)
            shot['render_assets_dir'] = str(directory)
            if row.get('renderCode'):
                shot['css_frame_clock'] = True
        digest = 'sha256:' + sha256(Path(shot['html']))
        prior = prior_shots.get(sid, {})
        if prior.get('source_code_digest') == digest:
            source_duration = prior['code_duration_seconds']
        elif row.get('renderCode'):
            source_duration = animations[sid]['durationSeconds'] if sid in animations else duration
        else:
            source_duration = template_duration
        if isinstance(source_duration, bool) or not isinstance(source_duration, (int, float)) or not math.isfinite(source_duration) or source_duration <= 0:
            raise ProductContractError('photo_animation_clock_rejected')
        target_duration = shot.get('animation_frames', shot['frames']) / manifest['fps']
        shot.update(source_code_digest=digest, code_duration_seconds=source_duration, frame_clock_scale=source_duration / target_duration)
    write_json(output, manifest)
    return output


def clone_render_cache(source: Path, destination: Path) -> None:
    """Reuse frame bytes without copying a large sequence or mutating old receipts."""
    if (source / '.export.lock').exists() or (source / 'render/.render.lock').exists():
        raise ProductContractError('photo_previous_run_busy')
    def copy_file(src, dst):
        path = Path(src)
        if path.suffix in {'.png', '.mp4', '.mov'}:
            os.link(src, dst)
        else:
            shutil.copyfile(src, dst)
        return dst
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / 'render', destination / 'render', copy_function=copy_file)
    if (source / 'segments').is_dir():
        shutil.copytree(source / 'segments', destination / 'segments', copy_function=copy_file)
    for clip in source.glob('*.mp4'):
        if clip.stem != 'candidate':
            copy_file(clip, destination / clip.name)
            if clip.with_suffix(clip.suffix + '.json').is_file():
                shutil.copyfile(clip.with_suffix(clip.suffix + '.json'), destination / (clip.name + '.json'))
    for clip in source.glob('*.mov'):
        copy_file(clip, destination / clip.name)
        if clip.with_suffix(clip.suffix + '.json').is_file():
            shutil.copyfile(clip.with_suffix(clip.suffix + '.json'), destination / (clip.name + '.json'))
    shutil.copyfile(source / '.video-render-owner.json', destination / '.video-render-owner.json')
    status = destination / 'render/shot-status.json'
    state = json.loads(status.read_text())
    for shot in state.get('shots', []):
        shot['frames_dir'] = str(destination / 'render' / shot['id'] / 'frames')
    write_json(status, state)


def teaching_overlays(native: dict, descriptor: dict, source: Path) -> list[dict]:
    from edit_backends.kdenlive_render import probe_media
    video = next(s for s in probe_media(source)['streams'] if s.get('codec_type') == 'video')
    width, height = video['width'], video['height']
    clips = {c['id']: c for c in native['clips']}
    overlays = []
    for animation in descriptor['animations']:
        clip = clips.get(animation['shotId'])
        if clip is None or clip['status'] != 'completed' or animation.get('timeBasis') == 'edited':
            raise ProductContractError('photo_animation_projection_missing')
        layout = animation['selectedLayout']
        if layout == 'full_screen':
            x, y, w, h = 0, 0, width, height
        elif layout == 'split_screen':
            x, y, w, h = width // 2, 0, width - width // 2, height
        elif layout == 'pip_right':
            w, h = max(1, width // 3), max(1, height // 3)
            x, y = width - w, height - h
        else:
            raise ProductContractError('photo_animation_layout_rejected')
        start = animation['suggestedStartSeconds']
        overlays.append({'path': clip['file'], 'animation_id': animation['animationId'],
                         'start': start, 'end': start + animation['durationSeconds'],
                         'geometry': {'x': x, 'y': y, 'width': w, 'height': h}})
    return overlays


def create_shot_image(*, task: dict, source: Path | None, manifest_path: Path | None, output: Path) -> dict:
    from video_candidate import ffmpeg
    from edit_backends.kdenlive_render import probe_media
    output.mkdir(parents=True, exist_ok=True)
    image = output / 'image.jpg'
    receipt = output / 'image-receipt.json'
    action = task.get('action')
    if action == 'source_frame':
        value = task.get('sourceTimeSeconds')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or source is None:
            raise ProductContractError('photo_source_frame_rejected')
        info = probe_media(source)
        video = next((s for s in info['streams'] if s.get('codec_type') == 'video'), None)
        if video is None or value >= float(video.get('duration') or info['format']['duration']):
            raise ProductContractError('photo_source_frame_rejected')
        temporary = output / 'source-frame.png'
        try:
            ffmpeg(['-i', str(source), '-ss', str(value), '-map', '0:v:0', '-frames:v', '1', str(temporary)])
            measured = jpeg_frame(temporary, image)
        finally:
            temporary.unlink(missing_ok=True)
        fact = {'action': action, 'requestedSourceTimeSeconds': value, 'sourceSha256': sha256(source)}
    elif action == 'code_render' and manifest_path is not None:
        manifest = load_manifest(manifest_path)
        target = next((copy.deepcopy(s) for s in manifest['shots'] if s['id'] == task['shotId']), None)
        if target is None:
            raise ProductContractError('photo_image_identity_rejected')
        target.update(frames=1, start_frame=0)
        manifest['shots'] = [target]
        state = render_shots(manifest, output / 'render')
        if state['status'] != 'completed':
            raise ProductContractError('photo_image_render_failed')
        measured = jpeg_frame(Path(state['shots'][0]['frames_dir']) / 'frame-000000.png', image)
        fact = {'action': action, 'renderedFrame': 0, 'htmlSha256': sha256(Path(target['html']))}
    else:
        # retry_image is normalized by Media to the original confirmed task.
        raise ProductContractError('photo_image_action_rejected')
    write_json(receipt, {**fact, **measured, 'shotId': task['shotId'], 'sha256': sha256(image)})
    return {'image_path': str(image), 'shotId': task['shotId']}
