#!/usr/bin/env python3
"""Render independent shots and verify content-addressed frame caches."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable

RENDERER = Path(__file__).with_name('render_frames.mjs')


class RenderError(RuntimeError):
    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


@contextmanager
def owned_workspace(output: Path, assets_dir: Path, purpose: str):
    """Serialize a complete render/export without overwriting somebody's media."""
    output = output.resolve()
    assets_dir = assets_dir.resolve()
    if output.is_relative_to(assets_dir) or assets_dir.is_relative_to(output):
        raise RenderError('invalid_output', 'Output and source directories must not overlap')
    owner = output / '.video-render-owner.json'
    if output.exists() and any(output.iterdir()):
        if not owner.is_file() or json.loads(owner.read_text()).get('purpose') != purpose:
            raise RenderError('invalid_output', 'Refusing to overwrite an unowned output directory')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / '.export.lock'
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RenderError('render_busy', 'This output already has an active export; inspect .export.lock before retrying') from error
    with os.fdopen(descriptor, 'w') as lock_file:
        lock_file.write(str(os.getpid()))
    try:
        write_json(owner, {'purpose': purpose})
        yield output
    finally:
        lock.unlink()


def positive_integer(value: Any, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise RenderError('invalid_input', f'{name} must be a positive integer')
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    path = path.resolve()
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise RenderError('invalid_input', 'Manifest must be an object')
    for key in ('width', 'height', 'fps'):
        positive_integer(value.get(key), key)
    if value['width'] % 2 or value['height'] % 2:
        raise RenderError('invalid_input', 'H.264 output dimensions must be even')
    root = (path.parent / value.get('assets_dir', '.')).resolve()
    if not root.is_dir():
        raise RenderError('missing_asset', f'assets_dir does not exist: {root}')
    value['assets_dir'] = str(root)
    fonts = value.get('fonts')
    if not isinstance(fonts, list) or not fonts or not all(isinstance(font, dict) and isinstance(font.get('path'), str) for font in fonts):
        raise RenderError('font_missing', 'fonts must contain pinned local font paths')
    value['fonts'] = [{'path': str((path.parent / font['path']).resolve())} for font in fonts]
    for font in value['fonts']:
        if not Path(font['path']).is_file():
            raise RenderError('font_missing', f"Pinned font missing: {font['path']}")
    if not isinstance(value.get('shots'), list) or not value['shots']:
        raise RenderError('invalid_input', 'shots must be non-empty')
    ids = set()
    cursor = 0
    for shot in value['shots']:
        if not isinstance(shot, dict):
            raise RenderError('invalid_input', 'Each shot must be an object')
        shot_id = shot.get('id', '')
        if not isinstance(shot_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', shot_id) or shot_id in ids:
            raise RenderError('invalid_input', 'Shot IDs must be unique safe directory names')
        ids.add(shot_id)
        positive_integer(shot.get('frames'), f'{shot_id}.frames')
        if type(shot.get('start_frame', cursor)) is not int or shot.get('start_frame', cursor) != cursor:
            raise RenderError('invalid_input', f'{shot_id}: start_frame must be {cursor}; gaps/overlaps are forbidden')
        shot['start_frame'] = cursor
        cursor += shot['frames']
        if not isinstance(shot.get('html'), str) or not shot['html']:
            raise RenderError('invalid_input', f'{shot_id}: html is required')
        html = (root / shot['html']).resolve()
        if not html.is_relative_to(root):
            raise RenderError('asset_outside_root', f'{shot_id}: HTML escapes assets_dir')
        shot['html'] = str(html)
        timeout = shot.get('timeout_seconds', value.get('timeout_seconds', 120))
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise RenderError('invalid_input', f'{shot_id}: timeout_seconds must be positive and finite')
        shot['timeout_seconds'] = timeout
        if type(shot.get('seed', 1)) is not int or not 0 <= shot.get('seed', 1) <= 4294967295:
            raise RenderError('invalid_input', f'{shot_id}: seed must be an unsigned 32-bit integer')
        if 'narration_wav' in shot:
            shot['narration_wav'] = str((path.parent / shot['narration_wav']).resolve())
    if 'narration_wav' in value:
        if any('narration_wav' in shot for shot in value['shots']):
            raise RenderError('invalid_input', 'Use either global narration_wav or one narration_wav per shot')
        value['narration_wav'] = str((path.parent / value['narration_wav']).resolve())
    return value


def request_for(manifest: dict[str, Any], shot: dict[str, Any], *, transparent: bool) -> dict[str, Any]:
    return {**{key: manifest[key] for key in ('width', 'height', 'fps', 'assets_dir', 'fonts')},
            **{key: shot[key] for key in ('html', 'frames', 'timeout_seconds')},
            'seed': shot.get('seed', 1), 'transparent': transparent,
            'browser_executable': manifest.get('browser_executable')}


def runtime_identity(manifest: dict[str, Any]) -> dict[str, str]:
    module = os.environ.get('VIDEO_RENDER_PLAYWRIGHT_MODULE', 'playwright')
    script = "const {createRequire}=require('node:module');const r=createRequire(process.argv[1]);const p=r(process.argv[2]);console.log(JSON.stringify({module:r.resolve(process.argv[2]),browser:p.chromium.executablePath()}));"
    try:
        probe = subprocess.run(['node', '-e', script, str(RENDERER), module], capture_output=True, text=True, timeout=15, check=True)
        identity = json.loads(probe.stdout)
        binary = Path(manifest.get('browser_executable') or identity['browser'])
        module_path = Path(identity['module'])
        package_path = module_path.parent / 'package.json'
        info_plist = binary.parent.parent / 'Info.plist'
        return {'node': subprocess.check_output(['node', '--version'], text=True, timeout=5).strip(),
                'playwright_entry': str(module_path), 'playwright_package_sha256': sha256(package_path),
                'browser': str(binary), 'browser_sha256': sha256(binary),
                'browser_bundle_sha256': sha256(info_plist) if info_plist.is_file() else '',
                'renderer_sha256': sha256(RENDERER)}
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        raise RenderError('runtime_unavailable', f'Node / Playwright / browser unavailable: {error}') from error


def fingerprint(request: dict[str, Any], runtime: dict[str, str]) -> str:
    value = {**request, 'runtime': runtime, 'html_sha256': sha256(Path(request['html'])),
             'font_sha256': [sha256(Path(font['path'])) for font in request['fonts']]}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def cache_valid(entry: dict[str, Any], expected: str, frames_dir: Path, frames: int) -> bool:
    if entry.get('status') != 'completed' or entry.get('fingerprint') != expected:
        return False
    files = entry.get('frame_hashes', [])
    dependencies = entry.get('dependencies', [])
    if len(files) != frames or not dependencies:
        return False
    if len(list(frames_dir.glob('frame-*.png'))) != frames:
        return False
    try:
        return all(sha256(frames_dir / f'frame-{index:06d}.png') == digest for index, digest in enumerate(files)) and all(sha256(Path(item['path'])) == item['sha256'] for item in dependencies)
    except (OSError, KeyError):
        return False


def run_renderer(request_file: Path, frames_dir: Path, timeout: float, on_event: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    events: queue.Queue = queue.Queue()
    with tempfile.TemporaryFile(mode='w+t') as errors:
        process = subprocess.Popen(['node', str(RENDERER), str(request_file), str(frames_dir)], stdout=subprocess.PIPE,
                                   stderr=errors, text=True, start_new_session=os.name != 'nt')
        def read_events() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                events.put(line)
            events.put(None)
        reader = threading.Thread(target=read_events, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout
        final: dict[str, Any] | None = None
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RenderError('shot_timeout', 'Shot exceeded timeout')
                try:
                    line = events.get(timeout=min(remaining, 0.2))
                except queue.Empty:
                    continue
                if line is None:
                    break
                event = json.loads(line)
                on_event(event)
                if event.get('status') in ('completed', 'failed'):
                    final = event
                    break
            if not final:
                process.wait(timeout=max(0.01, deadline - time.monotonic()))
                errors.seek(0)
                raise RenderError('render_failed', errors.read()[-4000:] or 'Renderer exited without a completion receipt')
            return final
        except subprocess.TimeoutExpired as error:
            raise RenderError('shot_timeout', 'Shot exceeded timeout') from error
        finally:
            # Only the process group created for this shot is terminated.
            if os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait()
            reader.join(timeout=1)
            assert process.stdout is not None
            process.stdout.close()


def render_shots(manifest: dict[str, Any], output: Path, *, transparent: bool = False,
                 on_event: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    output = output.resolve()
    source_root = Path(manifest['assets_dir'])
    if output.is_relative_to(source_root) or source_root.is_relative_to(output):
        raise RenderError('invalid_output', 'Output and source directories must not overlap')
    state_path = output / 'shot-status.json'
    if output.exists() and any(output.iterdir()) and not state_path.is_file():
        raise RenderError('invalid_output', 'Refusing to overwrite an unowned output directory')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / '.render.lock'
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RenderError('render_busy', 'This output already has an active render; inspect .render.lock before retrying') from error
    os.close(lock_fd)
    try:
        previous = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
        try:
            runtime = runtime_identity(manifest)
        except RenderError as error:
            write_json(state_path, {**previous, 'status': 'failed', 'code': error.code, 'reason': str(error)})
            raise
        state = {'status': 'running', 'runtime': runtime, 'shots': []}
        old = {shot['id']: shot for shot in previous.get('shots', [])}
        state['shots'] = [{'id': shot['id'], 'status': 'pending', 'progress_frames': 0, 'total_frames': shot['frames'], 'start_frame': shot['start_frame']} for shot in manifest['shots']]
        write_json(state_path, state)
        for shot, entry in zip(manifest['shots'], state['shots']):
            frames_dir = output / shot['id'] / 'frames'
            entry['frames_dir'] = str(frames_dir)
            request = request_for(manifest, shot, transparent=transparent)
            entry['attempts'] = old.get(shot['id'], {}).get('attempts', 0)
            try:
                expected = fingerprint(request, runtime)
                if cache_valid(old.get(shot['id'], {}), expected, frames_dir, shot['frames']):
                    entry.update(old[shot['id']], cached=True, start_frame=shot['start_frame'])
                    if on_event:
                        on_event(dict(entry))
                    write_json(state_path, state)
                    continue
                entry.update(status='running', cached=False, fingerprint=expected, attempts=entry['attempts'] + 1)
                if frames_dir.exists():
                    shutil.rmtree(frames_dir)
                frames_dir.mkdir(parents=True)
                request_file = frames_dir.parent / 'request.json'
                write_json(request_file, request)
                def update(event: dict[str, Any]) -> None:
                    entry.update(event)
                    write_json(state_path, state)
                    if on_event:
                        on_event({'id': shot['id'], **event})
                result = run_renderer(request_file, frames_dir, shot['timeout_seconds'] + 5, update)
                entry.update(result)
                if result['status'] == 'completed':
                    entry['frame_hashes'] = [sha256(frames_dir / f'frame-{index:06d}.png') for index in range(shot['frames'])]
                    if not cache_valid(entry, expected, frames_dir, shot['frames']):
                        raise RenderError('input_changed', 'A shot resource changed during rendering')
                else:
                    entry['reason'] = result['reason']
            except (RenderError, OSError, ValueError, subprocess.SubprocessError) as error:
                entry.update(status='failed', code=getattr(error, 'code', 'render_failed'), reason=str(error), cached=False)
                if on_event:
                    on_event(dict(entry))
            write_json(state_path, state)
        state['status'] = 'completed' if all(shot['status'] == 'completed' for shot in state['shots']) else 'failed'
        write_json(state_path, state)
        return state
    finally:
        lock.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = render_shots(load_manifest(args.manifest), args.output, on_event=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True))
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'completed' else 1
    except (RenderError, OSError, ValueError) as error:
        print(json.dumps({'status': 'failed', 'code': getattr(error, 'code', 'invalid_input'), 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
