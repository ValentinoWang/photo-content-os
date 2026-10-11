#!/usr/bin/env python3
"""Export storyboard animations as independent clips for the editing software."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from video_render.compose import run_ffmpeg
from video_render.multi_shot import RenderError, load_manifest, owned_workspace, render_shots, sha256, write_json


def teaching_clips(manifest_path: Path, output: Path, *, transparent: bool = False, on_event=None) -> dict:
    manifest = load_manifest(manifest_path)
    with owned_workspace(output, Path(manifest['assets_dir']), 'teaching') as workspace:
        try:
            return _teaching_clips(manifest, workspace, transparent=transparent, on_event=on_event)
        except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
            write_json(workspace / 'teaching-clips.json', {'status': 'failed', 'clips': [], 'shots': [],
                       'code': getattr(error, 'code', 'render_failed'), 'reason': str(error)})
            raise


def _teaching_clips(manifest: dict, output: Path, *, transparent: bool, on_event) -> dict:
    output = output.resolve()
    state = render_shots(manifest, output / 'render', transparent=transparent, on_event=on_event)
    result = {'status': 'running', 'clips': [], 'shots': state['shots']}
    for shot, entry in zip(manifest['shots'], state['shots']):
        clip = {'id': shot['id'], 'status': entry['status'], 'frames': shot['frames'], 'fps': manifest['fps'],
                'duration_seconds': shot['frames'] / manifest['fps'], 'transparent': transparent,
                'requirement': shot.get('animation_requirement'), 'spoken_text': shot.get('spoken_text')}
        if entry['status'] != 'completed':
            clip.update(code=entry.get('code'), reason=entry.get('reason'), file=None)
            result['clips'].append(clip)
            continue
        destination = output / f"{shot['id']}{'.mov' if transparent else '.mp4'}"
        receipt_path = destination.with_suffix(destination.suffix + '.json')
        key = hashlib.sha256(json.dumps({'frames': entry['frame_hashes'], 'fps': manifest['fps'], 'transparent': transparent, 'encoder': 'teaching-v1'}, sort_keys=True).encode()).hexdigest()
        try:
            receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            if receipt.get('key') != key or not destination.is_file() or sha256(destination) != receipt.get('sha256'):
                pending = destination.with_name(f'{shot["id"]}.pending{destination.suffix}')
                codec = ['-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le', '-alpha_bits', '16'] if transparent else ['-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p']
                try:
                    run_ffmpeg(['-framerate', str(manifest['fps']), '-start_number', '0', '-i', str(Path(entry['frames_dir']) / 'frame-%06d.png'),
                                '-frames:v', str(shot['frames']), '-an', *codec, '-threads', '1', '-map_metadata', '-1', str(pending)], shot['timeout_seconds'])
                    run_ffmpeg(['-i', str(pending), '-f', 'null', '-'], shot['timeout_seconds'])
                    pending.replace(destination)
                finally:
                    pending.unlink(missing_ok=True)
                write_json(receipt_path, {'key': key, 'sha256': sha256(destination)})
            clip.update(status='completed', file=str(destination), sha256=sha256(destination))
        except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
            clip.update(status='failed', code=getattr(error, 'code', 'encode_failed'), reason=str(error), file=None)
        result['clips'].append(clip)
        write_json(output / 'teaching-clips.json', result)
    result['status'] = 'completed' if all(clip['status'] == 'completed' for clip in result['clips']) else 'failed'
    write_json(output / 'teaching-clips.json', result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--transparent', action='store_true', help='Export ProRes 4444 MOV with alpha; otherwise H.264 MP4')
    args = parser.parse_args()
    try:
        result = teaching_clips(args.manifest, args.output, transparent=args.transparent,
                                on_event=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'completed' else 1
    except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'failed', 'code': getattr(error, 'code', 'render_failed'), 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
