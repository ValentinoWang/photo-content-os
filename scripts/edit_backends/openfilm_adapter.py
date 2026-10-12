"""Local openfilm 0.1.5 adapter; owns only its generated project and processes."""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import tempfile
import time

from .interface import BackendError, CloseResult, Description, Probe
from .kdenlive_render import (FPS, frames, plan_ranges, probe_media, remap_span,
                              review_module, seconds, sha256_file, write_json)

DEFAULT_PACKAGE = Path('/Users/vsiyo/Desktop/Opensource_Tool/openfilm-oa/runtime/node_modules/openfilm')
BRIDGE = Path(__file__).with_name('openfilm_bridge.mjs')


def _process_table():
    rows = subprocess.run(['ps', '-axo', 'pid=,ppid=,comm='], capture_output=True,
                          text=True, check=True, timeout=10).stdout.splitlines()
    return {int(pid): (int(parent), command) for row in rows
            for pid, parent, command in [row.strip().split(None, 2)]}


def _descendants(pid):
    table = _process_table()
    found = {pid} if pid in table else set()
    while True:
        more = found | {p for p, (parent, _) in table.items() if parent in found}
        if more == found:
            return found
        found = more


def _stop(proc):
    owned = _descendants(proc.pid)
    if proc.poll() is None:
        # Give Node's signal handler time to close Chromium and both HTTP servers.
        for pid in owned:
            if pid != proc.pid and Path(_process_table().get(pid, (0, ''))[1]).name == 'node':
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
    for stream in (proc.stdin, proc.stdout, proc.stderr):
        if stream:
            stream.close()
    return owned


def _queue_wait_seconds():
    value = int(os.environ.get('MEDIA_CHROMIUM_SLOT_WAIT_SECONDS', '900'))
    if value < 1:
        raise BackendError('openfilm_chromium_slot_wait_invalid')
    return value


def _deadline(when):
    left = when - time.monotonic()
    if left <= 0:
        raise BackendError('openfilm_render_timeout')
    return left


class Backend:
    def __init__(self):
        self._session = None
        self._home = None
        self._session_project = None
        self._readback = None
        self._started = set()

    def describe(self) -> Description:
        return {'id': 'openfilm', 'display_name': 'openfilm', 'license': 'MIT',
                'capabilities': {'automatic_first_cut': True, 'transparent_overlay': True,
                                 'chinese_subtitle_burn_in': True, 'web_refine': True,
                                 'undo': True, 'read_back': True, 'export_formats': ['mp4', 'srt']}}

    def _package(self):
        path = Path(os.environ.get('CONTENT_OS_OPENFILM_PACKAGE', str(DEFAULT_PACKAGE))).expanduser().resolve()
        try:
            package = json.loads((path / 'package.json').read_text())
        except (OSError, ValueError) as exc:
            raise BackendError('openfilm_runtime_unavailable') from exc
        if package.get('name') != 'openfilm' or package.get('version') != '0.1.5':
            raise BackendError('openfilm_runtime_version_unsupported')
        if not shutil.which('node') or not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            raise BackendError('openfilm_runtime_dependency_missing')
        return path

    def _start(self, *, browser=False, persistent=False, log=None):
        package = self._package()
        command = ['node', str(BRIDGE)]
        if browser:
            slot = os.environ.get('CONTENT_OS_CHROMIUM_SLOT_SCRIPT')
            if not slot or not Path(slot).is_file():
                raise BackendError('openfilm_chromium_slot_script_required')
            command = ['bash', slot, '--', *command]
        home = tempfile.TemporaryDirectory(prefix='content-os-openfilm-')
        env = {**os.environ, 'CONTENT_OS_OPENFILM_PACKAGE': str(package),
               'OPENFILM_HOME': home.name, 'OPENFILM_NO_BROWSER': '1', 'OPENFILM_NO_UPDATE_CHECK': '1',
               'OPENFILM_EXPORTS': str(Path(home.name) / 'exports')}
        try:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=log or subprocess.PIPE, text=True, env=env, start_new_session=True)
        except BaseException:
            home.cleanup()
            raise
        if persistent:
            self._session, self._home = proc, home
            self._started.add(proc.pid)
        return proc, home

    def _once(self, request, *, timeout=30, browser=False, log_path=None):
        log = log_path.open('w') if log_path else None
        proc = home = None
        try:
            proc, home = self._start(browser=browser, log=log)
            stdout, _ = proc.communicate(json.dumps(request) + '\n', timeout=timeout)
            if proc.returncode:
                raise BackendError('openfilm_bridge_failed')
            response = json.loads(stdout.strip().splitlines()[-1])
            if not response['ok']:
                raise BackendError(response['error'])
            return response['value']
        except subprocess.TimeoutExpired as exc:
            if proc:
                _stop(proc)
            raise BackendError('openfilm_render_timeout') from exc
        finally:
            if proc and proc.poll() is None:
                _stop(proc)
            if home:
                home.cleanup()
            if log:
                log.close()

    def _rpc(self, request, timeout=45):
        proc = self._session
        if proc is None or proc.poll() is not None:
            raise BackendError('openfilm_refine_session_unavailable')
        proc.stdin.write(json.dumps(request) + '\n')
        proc.stdin.flush()
        if not select.select([proc.stdout], [], [], timeout)[0]:
            self._started.update(_stop(proc))
            self._session = None
            if self._home:
                self._home.cleanup()
                self._home = None
            self._session_project = None
            raise BackendError('openfilm_render_timeout')
        line = proc.stdout.readline()
        if not line:
            self.close()
            raise BackendError('openfilm_bridge_failed')
        response = json.loads(line)
        if not response['ok']:
            raise BackendError(response['error'])
        return response['value']

    def probe(self) -> Probe:
        result = {'id': 'openfilm', 'installed': False, 'version': None,
                  'runnable': False, 'status': 'unavailable', 'reason': None}
        try:
            self._package()
            result.update(installed=True, version='0.1.5')
            with tempfile.TemporaryDirectory(prefix='openfilm-probe-') as temp:
                root = Path(temp)
                (root / 'film.html').write_text('<meta name="viewport" content="width=640,height=360"><section><img src="still.png#t=0,1"></section>')
                request = {'action': 'probe', 'project': str(root)}
                value = self._rpc(request) if self._session else self._once(request, browser=True, timeout=_queue_wait_seconds() + 30)
            if not Path(value['chromium']).is_file():
                raise BackendError('openfilm_chromium_unavailable')
            for binary in ('ffmpeg', 'ffprobe'):
                subprocess.run([binary, '-version'], capture_output=True, check=True, timeout=10)
            slot = os.environ.get('CONTENT_OS_CHROMIUM_SLOT_SCRIPT')
            if not slot or not Path(slot).is_file():
                raise BackendError('openfilm_chromium_slot_script_required')
            result.update(runnable=True, status='online')
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
            result['reason'] = str(exc) if isinstance(exc, BackendError) else f'openfilm_probe_failed:{type(exc).__name__}'
        return result

    def _compile(self, kwargs, output_dir, deadline):
        source = Path(kwargs['source']).expanduser().resolve()
        suggestions_path = Path(kwargs['suggestions_path']).expanduser().resolve()
        suggestions = json.loads(suggestions_path.read_text())
        metadata = probe_media(source)
        _deadline(deadline)
        video = next((s for s in metadata['streams'] if s['codec_type'] == 'video'), None)
        if video is None or not any(s['codec_type'] == 'audio' for s in metadata['streams']):
            raise BackendError('source_requires_video_and_audio')
        duration = float(video.get('duration') or metadata['format']['duration'])
        ranges, ignored = plan_ranges(suggestions, duration)
        if suggestions.get('source_sha256') not in (None, sha256_file(source)):
            raise BackendError('suggestions_source_hash_mismatch')
        width, height = video['width'], video['height']
        if width % 2 or height % 2:
            raise BackendError('h264_requires_even_dimensions')
        project = output_dir / 'openfilm-project'
        assets = project / 'assets'
        assets.mkdir(parents=True)
        # Explicit SDR tags keep Chromium and FFmpeg on the same color matrix.
        normalized = assets / 'source.mp4'
        command = ['ffmpeg', '-v', 'error', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0',
                   '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-c:v', 'libx264', '-crf', '12',
                   '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709',
                   '-color_trc', 'bt709', '-color_range', 'tv', '-c:a', 'aac', '-b:a', '192k', str(normalized)]
        subprocess.run(command, capture_output=True, check=True, timeout=_deadline(deadline))
        source_conversion = {'source': str(source), 'output': str(normalized), 'codec': 'h264',
                             'color_space': 'bt709', 'sha256': sha256_file(normalized), 'command': command}
        inputs = [{'path': str(source), 'sha256': sha256_file(source), 'role': 'original_video'},
                  {'path': str(suggestions_path), 'sha256': sha256_file(suggestions_path), 'role': 'edit_suggestions'}]
        talk = [f'<video id="talk{i}" src="assets/source.mp4#t={r["source_start"]},{r["source_end"]}" at="{r["output_start"]}" style="width:{width}px;height:{height}px"></video>'
                for i, r in enumerate(ranges, 1)]
        overlay, conversions, animation_assets = [], [source_conversion], []
        for index, animation in enumerate(kwargs['animations'] or []):
            original = Path(animation['path']).expanduser().resolve()
            info = probe_media(original)
            stream = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
            if stream is None:
                raise BackendError('animation_video_missing')
            native = float(stream.get('duration') or info['format']['duration'])
            if 'start' not in animation:
                matches = [s for s in suggestions['suggestions'] if s.get('type') == 'animation' and s.get('animation_id') == animation.get('animation_id')]
                if len(matches) != 1 or matches[0].get('ambiguous') is True:
                    raise BackendError('animation_position_missing_or_ambiguous')
                start, end = seconds(matches[0]['start']), min(seconds(matches[0]['end']), seconds(matches[0]['start']) + native)
            else:
                start = seconds(animation['start'])
                end = seconds(animation.get('end', start + native))
            if end <= start or end > duration + 1e-6 or end - start > native + 1 / FPS:
                raise BackendError('animation_range_invalid')
            geometry = animation.get('geometry', {'x': 0, 'y': 0, 'width': stream['width'], 'height': stream['height']})
            if not isinstance(geometry, dict) or set(geometry) != {'x', 'y', 'width', 'height'} or any(type(v) is not int for v in geometry.values()):
                raise BackendError('animation_geometry_invalid')
            x, y, w, h = (geometry[k] for k in ('x', 'y', 'width', 'height'))
            if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
                raise BackendError('animation_geometry_invalid')
            dest = assets / f'overlay-{index}.webm'
            # Chromium cannot decode ProRes alpha. VP9 alpha must bypass seekable's H.264 cache.
            decoder = ['-c:v', 'libvpx-vp9'] if stream.get('codec_name') == 'vp9' else []
            command = ['ffmpeg', '-v', 'error', *decoder, '-i', str(original), '-c:v', 'libvpx-vp9', '-lossless', '1', '-pix_fmt', 'yuva420p', '-auto-alt-ref', '0', '-an', str(dest)]
            subprocess.run(command, capture_output=True, check=True, timeout=_deadline(deadline))
            conversions.append({'source': str(original), 'output': str(dest), 'codec': 'vp9', 'pix_fmt': 'yuva420p', 'sha256': sha256_file(dest), 'command': command})
            animation_assets.append({'path': str(dest.relative_to(project)), 'animation_id': animation.get('animation_id')})
            inputs.append({'path': str(original), 'sha256': sha256_file(original), 'role': 'teaching_animation'})
            for part, (a, b, offset) in enumerate(remap_span(start, end, ranges)):
                overlay.append(f'<video id="overlay{index}-{part}" src="assets/{dest.name}#t={offset},{offset+b-a}" at="{a}" muted style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></video>')
        subtitles = kwargs['subtitles']
        if subtitles:
            subtitles = Path(subtitles).expanduser().resolve()
            cues = review_module().read_srt_cues(subtitles)
            if not cues or any(a < 0 or b <= a or b > duration + 1e-6 for a, b, _ in cues) or any(cues[i][0] < cues[i-1][1] for i in range(1, len(cues))):
                raise BackendError('subtitle_source_timeline_invalid')
            stamp = lambda v: f'{int(v)//3600:02}:{int(v)//60%60:02}:{v%60:06.3f}'
            (assets / 'source.vtt').write_text('WEBVTT\n\nNOTE Each cue is one subtitle, as cut by hand in OpenFilm Studio.\n\n' + '\n\n'.join(f'{stamp(a)} --> {stamp(b)}\n{text}' for a, b, text in cues) + '\n')
            inputs.append({'path': str(subtitles), 'sha256': sha256_file(subtitles), 'role': 'source_subtitles'})
        if subtitles:
            (project / '.film').mkdir(exist_ok=True)
            write_json(project / '.film/subtitles.json', {
                'on': True, 'look': 'bar', 'pos': {'x': 0.5, 'y': 0.94},
                'font': {'family': 'PingFang SC', 'sizePct': 5, 'weight': 500},
            })
        (project / 'film.html').write_text(f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width={width},height={height}"></head><body>\n<section id="overlay">' + '\n'.join(overlay) + '</section>\n<section id="talk">' + '\n'.join(talk) + '</section></body></html>')
        config = {'kwargs': {**kwargs, 'source': str(source), 'suggestions_path': str(suggestions_path), 'subtitles': str(subtitles) if subtitles else None},
                  'inputs': inputs, 'source_duration': duration, 'conversions': conversions,
                  'animation_assets': animation_assets, 'ignored_review_only': ignored,
                  'source_suggestions': suggestions['suggestions'],
                  'working_media': [{'path': str(p.relative_to(project)), 'sha256': sha256_file(p)}
                                    for p in assets.iterdir() if p.suffix in {'.mp4', '.webm'}]}
        write_json(project / 'adapter-project.json', config)
        return project, config

    def _state(self, project):
        request = {'action': 'snapshot', 'project': str(project)}
        return self._rpc(request) if self._session else self._once(request)

    @staticmethod
    def _time_map(state, config):
        rows = []
        allowed = {'assets/source.mp4', *(a['path'] for a in config['animation_assets'])}
        if any(c['src'] not in allowed for t in state['doc']['tracks'] for c in t['clips']):
            raise BackendError('openfilm_unapproved_project_asset')
        for track in state['doc']['tracks']:
            for clip in track['clips']:
                if clip['src'] == 'assets/source.mp4':
                    if track.get('hidden') or track.get('muted') or clip.get('speed', 1) != 1:
                        raise BackendError('openfilm_source_trace_unsupported')
                    a, b = clip['time']
                    c = clip.get('at', 0)
                    if any(not math.isfinite(v) or v < 0 for v in (a, b, c)) or b <= a or b > config['source_duration'] + 1e-6:
                        raise BackendError('openfilm_source_trace_invalid')
                    rows.append({'source_start': a, 'source_end': b, 'output_start': c})
        rows.sort(key=lambda r: r['output_start'])
        if not rows:
            raise BackendError('openfilm_all_source_removed')
        for previous, current in zip(rows, rows[1:]):
            if current['source_start'] < previous['source_end'] or current['output_start'] + 1e-6 < previous['output_start'] + previous['source_end'] - previous['source_start']:
                raise BackendError('openfilm_source_reorder_or_overlap_unsupported')
        return rows

    def _matches_readback(self, kwargs):
        return bool(self._readback and all(kwargs[k] == self._readback['kwargs'][k]
                                          for k in kwargs if k != 'timeout_seconds'))

    def render(self, *, source: Path, suggestions_path: Path, output_dir: Path,
               subtitles: Path | None = None, animations: list[dict] | None = None,
               project_id: str = 'spoken-test', project_revision: int = 1,
               timeout_seconds: float = 300) -> dict:
        output_dir = output_dir.expanduser().resolve()
        if output_dir.exists():
            raise BackendError('output_directory_already_exists')
        output_dir.mkdir(parents=True)
        result = {'status': 'failed', 'editor_backend': 'openfilm', 'project_id': project_id, 'project_revision': project_revision}
        try:
            deadline = time.monotonic() + float(timeout_seconds)
        except (TypeError, ValueError):
            deadline = time.monotonic()
        kwargs = {'source': str(Path(source).expanduser().resolve()), 'suggestions_path': str(Path(suggestions_path).expanduser().resolve()),
                  'subtitles': str(Path(subtitles).expanduser().resolve()) if subtitles else None, 'animations': animations or [],
                  'project_id': project_id, 'project_revision': project_revision, 'timeout_seconds': timeout_seconds}
        try:
            if not isinstance(project_id, str) or not project_id.strip() or type(project_revision) is not int or project_revision < 1:
                raise BackendError('render_project_identity_invalid')
            if isinstance(timeout_seconds, bool) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
                raise BackendError('render_timeout_invalid')
            _deadline(deadline)
            self._package()
            if self._matches_readback(kwargs):
                origin = self._readback['project']
                state = self._state(origin)
                if state['rev'] != self._readback['rev']:
                    raise BackendError('openfilm_read_back_stale')
                config = json.loads((origin / 'adapter-project.json').read_text())
                project = output_dir / 'openfilm-project'
                shutil.copytree(origin, project, ignore=shutil.ignore_patterns('cache', 'oa-render', '.openfilm-home', '.git'))
            else:
                project, config = self._compile(kwargs, output_dir, deadline)
                state = self._state(project)
            for asset in config['working_media']:
                if sha256_file(project / asset['path']) != asset['sha256']:
                    raise BackendError('openfilm_working_media_changed')
            time_map = self._time_map(state, config)
            for item in config['inputs']:
                if sha256_file(Path(item['path'])) != item['sha256']:
                    raise BackendError('openfilm_original_input_changed')
            # Candidate provenance remains immutable while the person edits its working project.
            export_project = output_dir / 'export-inputs'
            shutil.copytree(project, export_project, ignore=shutil.ignore_patterns('cache', 'oa-render', '.git'))
            actual_inputs = [{'path': str(p), 'sha256': sha256_file(p), 'role': 'openfilm_project_input'}
                             for p in export_project.rglob('*') if p.is_file() and 'cache' not in p.parts]
            output = output_dir / 'candidate.mp4'
            subtitle_output = output_dir / 'subtitles.srt'
            request = {'action': 'render', 'project': str(export_project), 'output': str(output),
                       'subtitles': str(subtitle_output), 'timeoutMs': max(1, int(_deadline(deadline) * 1000))}
            exported = self._rpc(request, timeout=_deadline(deadline)) if self._session else self._once(request, timeout=_deadline(deadline), browser=True, log_path=output_dir / 'openfilm.log')
            # The actual engine state, not the pre-cut plan, supplies timing and cues.
            if exported['rev'] != state['rev']:
                raise BackendError('openfilm_project_changed_during_export')
            if subtitle_output.stat().st_size:
                actual_inputs.append({'path': str(subtitle_output), 'sha256': sha256_file(subtitle_output),
                                      'role': 'rendered_subtitle_sidecar'})
            info = probe_media(output)
            stream = next(s for s in info['streams'] if s['codec_type'] == 'video')
            duration = max(clip.get('at', 0) + (clip['time'][1] - clip['time'][0]) / clip.get('speed', 1)
                           for track in state['doc']['tracks'] if not track.get('hidden') for clip in track['clips'])
            retained = sum(r['source_end'] - r['source_start'] for r in time_map)
            placements = []
            allowed = {a['path']: a for a in config['animation_assets']}
            for track in state['doc']['tracks']:
                if track.get('hidden'):
                    continue
                for clip in track['clips']:
                    if clip['src'] in allowed:
                        a, b = clip['time']
                        box = clip.get('box', {})
                        placements.append({'animation_id': allowed[clip['src']]['animation_id'], 'start': clip.get('at', 0),
                                           'end': clip.get('at', 0) + (b-a) / clip.get('speed', 1),
                                           'geometry': {'x': box.get('x', 0), 'y': box.get('y', 0), 'width': box.get('w', 160), 'height': box.get('h', 90)}})
            cuts, cursor = [], 0
            for row in [*time_map, {'source_start': config['source_duration'], 'source_end': config['source_duration']}]:
                if row['source_start'] > cursor:
                    contributors = [s for s in config['source_suggestions']
                                    if s.get('auto_cut_allowed') is True and s.get('type') in {'silence', 'repetition'}
                                    and s['start'] < row['source_start'] and s['end'] > cursor]
                    kind = 'manual' if self._matches_readback(kwargs) else ('retake' if any(s['type'] == 'repetition' for s in contributors) else 'silence')
                    cuts.append({'kind': kind, 'startSeconds': cursor, 'endSeconds': row['source_start']})
                cursor = row['source_end']
            manifest = {'contract': 'video_pipeline_manifest.v1', 'output': {'path': str(output), 'sha256': sha256_file(output)},
                        'inputs': [*config['inputs'], *actual_inputs], 'assets': [], 'time_map': time_map,
                        'duration': duration, 'fps': float(FPS), 'width': state['doc']['stage']['w'], 'height': state['doc']['stage']['h'],
                        'video_tracks': 1, 'audio_tracks': 1, 'subtitles': str(subtitle_output) if subtitle_output.stat().st_size else None,
                        'subtitle_burned_in': bool(exported['subtitles']['cues'] and exported['subtitles']['style']['on']),
                        'subtitle_bottom_ratio': 0.8, 'removed_seconds': config['source_duration'] - retained,
                        'animation_placements': placements, 'executed_cuts': cuts, 'ignored_review_only': config['ignored_review_only']}
            manifest_path = output_dir / 'candidate.mp4.manifest.json'
            write_json(manifest_path, manifest)
            checks = review_module().check_pipeline_manifest(manifest_path, expected_output=output)
            if checks['status'] != 'passed':
                result['checks'] = checks
                raise BackendError('openfilm_manifest_check_failed')
            result.update(status='candidate', output=str(output), manifest=str(manifest_path), duration=duration,
                          frames=int(stream['nb_frames']), removed_seconds=manifest['removed_seconds'], checks=checks,
                          project_dir=str(project), conversions=[{**c, 'origin_output': c['output'],
                                                                   'reused': self._matches_readback(kwargs),
                                                                   'output': str(export_project / 'assets' / Path(c['output']).name)}
                                                                 for c in config['conversions']], seekable=False,
                          render_workers=1, engine_revision=state['rev'])
        except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc:
            result['reason'] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            (output_dir / 'candidate.mp4').unlink(missing_ok=True)
            write_json(output_dir / 'render-result.json', result)
            raise BackendError(result['reason']) from exc
        write_json(output_dir / 'render-result.json', result)
        return result

    def open_for_refine(self, *, project_dir: Path) -> dict:
        root = project_dir.expanduser().resolve() / 'openfilm-project'
        if not (root / 'adapter-project.json').is_file():
            raise BackendError('openfilm_owned_project_required')
        if self._session:
            if root != self._session_project:
                raise BackendError('openfilm_refine_other_project_active')
            return self._session_descriptor
        log = (root.parent / 'openfilm-refine.log').open('w')
        try:
            self._start(browser=True, persistent=True, log=log)
            self._session_project = root
            self._session_descriptor = self._rpc({'action': 'refine', 'project': str(root)}, timeout=_queue_wait_seconds() + 45)
            self._started.update(_descendants(self._session.pid))
            return self._session_descriptor
        except BaseException:
            self.close()
            raise
        finally:
            log.close()

    def read_back(self, *, project_dir: Path) -> dict:
        root = project_dir.expanduser().resolve() / 'openfilm-project'
        config = json.loads((root / 'adapter-project.json').read_text())
        state = self._state(root)
        rows = self._time_map(state, config)
        self._readback = {'project': root, 'rev': state['rev'], 'kwargs': config['kwargs']}
        return {'time_map': rows, 'render_kwargs': copy.deepcopy(config['kwargs']), 'engine_revision': state['rev']}

    def close(self) -> CloseResult:
        if self._session:
            self._started.update(_descendants(self._session.pid))
            try:
                self._rpc({'action': 'close'}, timeout=10)
            except (OSError, ValueError):
                pass
            finally:
                proc, self._session = self._session, None
                if proc:
                    if proc.stdin:
                        proc.stdin.close()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self._started.update(_stop(proc))
                if self._home:
                    self._home.cleanup()
                    self._home = None
                self._session_project = None
                for stream in (proc.stdout, proc.stderr):
                    if stream:
                        stream.close()
        table = _process_table()
        return {'id': 'openfilm', 'started_pids': sorted(self._started),
                'remaining_pids': sorted(self._started.intersection(table))}


# EI's refine driver hooks operate the real editor; no fixture or project rewrites.
def delete_segment(backend, project_dir: Path, index: int) -> None:
    if backend._session_project != project_dir.resolve() / 'openfilm-project':
        raise BackendError('openfilm_refine_project_mismatch')
    backend._rpc({'action': 'delete', 'index': index})
    checks = review_module().check_pipeline_manifest(project_dir / 'candidate.mp4.manifest.json')
    if checks['status'] != 'passed':
        raise BackendError('openfilm_prior_candidate_provenance_changed')


def undo(backend, project_dir: Path) -> None:
    if backend._session_project != project_dir.resolve() / 'openfilm-project':
        raise BackendError('openfilm_refine_project_mismatch')
    backend._rpc({'action': 'undo'})
