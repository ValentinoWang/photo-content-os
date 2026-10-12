"""Read the saved MLT graph, never reuse a render plan's timeline."""
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .interface import BackendError
from .kdenlive_render import probe_media, sha256_file, timeline_tractor


def properties(node):
    return {p.get('name'): p.text or '' for p in node.findall('property')}


def read_project(project_dir: Path) -> dict:
    directory = project_dir.resolve()
    project = directory / 'timeline.kdenlive'
    raw = project.read_bytes()
    if len(raw) > 10_000_000 or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise BackendError('kdenlive_project_invalid')
    try:
        root = ET.fromstring(raw)
        plan = json.loads((directory / 'render-plan.json').read_text())
        receipt = json.loads((directory / 'render-result.json').read_text())
        identity = properties(root)
        if root.tag != 'mlt' or identity.get('kdenlive:docproperties.projectid') != receipt['project_id'] or identity.get('content_os.project_revision') != str(receipt['project_revision']):
            raise BackendError('kdenlive_project_identity_mismatch')
        profile = root.find('profile')
        fps = float(Fraction(int(profile.get('frame_rate_num')), int(profile.get('frame_rate_den'))))
        if not math.isfinite(fps) or fps <= 0:
            raise BackendError('kdenlive_project_fps_invalid')
        originals = {Path(i['path']).resolve(): i for i in plan['inputs']}
        source = next(p for p, i in originals.items() if i['role'] == 'original_video')
        for path, item in originals.items():
            if item['role'] != 'source_subtitles' and sha256_file(path) != item['sha256']:
                raise BackendError('kdenlive_original_input_changed')
        source_info = probe_media(source)
        video = next(s for s in source_info['streams'] if s['codec_type'] == 'video')
        source_duration = float(video.get('duration') or source_info['format']['duration'])
        nodes = {n.get('id'): n for n in root if n.get('id')}
        sequence = timeline_tractor(root)

        def frame(value):
            if ':' in value:
                h, m, s = value.split(':')
                result = round((int(h)*3600 + int(m)*60 + float(s))*fps)
            else:
                result = int(value)
            if result < 0:
                raise BackendError('kdenlive_project_time_invalid')
            return result

        def resource(value):
            p = Path(value)
            p = (Path(root.get('root') or directory) / p).resolve() if not p.is_absolute() else p.resolve()
            if p not in originals and not p.is_relative_to(directory):
                raise BackendError('kdenlive_unapproved_project_asset')
            return p

        # Resolve only nodes reachable from the active sequence. Bin copies,
        # hidden audio tracks and unused producers are not editing evidence.
        entries, filters, visited = [], [], set()
        def walk(node, at=0, ancestors=()):
            nid = node.get('id')
            if nid in ancestors:
                raise BackendError('kdenlive_graph_cycle')
            ancestors = (*ancestors, nid)
            filters.extend(node.findall('filter'))
            if node.tag == 'tractor':
                for track in node.findall('track'):
                    if track.get('hide') in ('video', 'both'):
                        continue
                    child = nodes[track.get('producer')]
                    # A trimmed/nested sequence needs an explicit time mapping.
                    if frame(track.get('in', '0')):
                        raise BackendError('kdenlive_nested_trim_unsupported')
                    walk(child, at, ancestors)
            elif node.tag == 'playlist':
                cursor = at
                for item in node:
                    if item.tag == 'blank':
                        cursor += frame(item.get('length'))
                    elif item.tag == 'entry':
                        producer = nodes[item.get('producer')]
                        props = properties(producer)
                        if producer.tag not in ('producer', 'chain') or 'resource' not in props or props.get('mlt_service') == 'timewarp':
                            raise BackendError('kdenlive_clip_unsupported')
                        start, end = frame(item.get('in', '0')), frame(item.get('out'))+1
                        if end <= start:
                            raise BackendError('kdenlive_project_time_invalid')
                        entries.append((resource(props['resource']), start, end, cursor, producer))
                        filters.extend(producer.findall('filter'))
                        cursor += end-start
                visited.add(cursor)
        walk(sequence)
        ranges = sorted([{'source_start': a/fps, 'source_end': b/fps, 'output_start': at/fps}
                         for p, a, b, at, _ in entries if p == source], key=lambda r: r['output_start'])
        if not ranges:
            raise BackendError('kdenlive_source_trace_missing')
        cursor, output = 0., 0.
        cuts = []
        for r in [*ranges, {'source_start': round(source_duration*fps)/fps, 'source_end': round(source_duration*fps)/fps, 'output_start': output}]:
            if r['source_start'] < cursor-1e-6 or r['source_end'] > source_duration+1/fps:
                raise BackendError('kdenlive_source_reorder_unsupported')
            if r in ranges and abs(r['output_start']-output) > 1e-6:
                raise BackendError('kdenlive_source_gap_unsupported')
            if r['source_start'] > cursor+1e-6:
                # The XML establishes boundaries; the producer supplies only
                # the acoustic reason, which cannot be invented from a gap.
                facts = [c for c in plan.get('executed_cuts', []) if c['startSeconds'] <= cursor+1e-6 and c['endSeconds'] >= r['source_start']-1e-6]
                if not facts:
                    raise BackendError('kdenlive_cut_reason_unverified')
                cuts.append({'kind': facts[0]['kind'], 'startSeconds': cursor, 'endSeconds': min(r['source_start'], source_duration)})
            cursor = r['source_end']
            output += r['source_end']-r['source_start']
        animation_paths = [p for p,i in originals.items() if i['role']=='teaching_animation']
        animation_ids = list(dict.fromkeys(a['animation_id'] for a in plan.get('animation_placements', [])))
        if len(animation_paths) != len(animation_ids):
            raise BackendError('kdenlive_animation_identity_unverified')
        allowed = dict(zip(animation_paths, animation_ids))
        placements = []
        for p, a, b, at, producer in entries:
            if p == source:
                continue
            if p not in allowed:
                raise BackendError('kdenlive_unapproved_project_asset')
            transform = next((properties(f) for f in producer.findall('filter') if properties(f).get('mlt_service')=='affine'), {})
            values = transform.get('transition.rect', '').split()
            if len(values) != 5 or '=' in transform.get('transition.rect', ''):
                raise BackendError('kdenlive_animation_geometry_unverified')
            x,y,w,h,alpha = map(float, values)
            if alpha != 1 or any(v != int(v) for v in (x,y,w,h)):
                raise BackendError('kdenlive_animation_geometry_unverified')
            placements.append({'animation_id':allowed[p], 'start':at/fps, 'end':(at+b-a)/fps,
                               'geometry':dict(zip(('x','y','width','height'),map(int,(x,y,w,h))))})
        subtitles, bottom = None, None
        for filt in filters:
            props = properties(filt)
            if props.get('mlt_service') not in ('subtitle','avfilter.subtitles') or props.get('disable')=='1':
                continue
            if subtitles is not None:
                raise BackendError('kdenlive_multiple_subtitles_unsupported')
            subtitles = resource(props.get('resource') or props.get('av.filename') or props.get('filename') or '')
            match = re.fullmatch(r'[^/]+/(\d+(?:\.\d+)?)%:.*', props.get('geometry',''))
            if not match:
                raise BackendError('kdenlive_subtitle_position_unverified')
            bottom = float(match[1])/100
        if not subtitles or not subtitles.is_file():
            raise BackendError('kdenlive_subtitle_trace_missing')
        duration = max(visited)/fps
        if sequence.get('out') is not None and frame(sequence.get('out'))+1 != round(duration*fps):
            raise BackendError('kdenlive_sequence_duration_mismatch')
        if abs(duration-output) > 1/fps or any(p['end'] > duration+1/fps for p in placements):
            raise BackendError('kdenlive_project_duration_invalid')
        return {'time_map':ranges, 'fps':fps, 'duration':duration, 'frames':round(duration*fps),
                'executed_cuts':cuts, 'animation_placements':placements, 'subtitles':str(subtitles),
                'subtitle_burned_in':True, 'subtitle_bottom_ratio':bottom,
                'project_id':receipt['project_id'], 'project_revision':receipt['project_revision'],
                'engine_revision':sha256_file(project), 'render_kwargs':{'source':source, 'suggestions_path':next(p for p,i in originals.items() if i['role']=='edit_suggestions'), 'subtitles':subtitles, 'project_id':receipt['project_id'], 'project_revision':receipt['project_revision']}}
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, StopIteration) as exc:
        if isinstance(exc, BackendError):
            raise
        raise BackendError('kdenlive_saved_project_invalid') from exc


def render_saved(*, project_dir, expected_revision, output_dir, timeout_seconds):
    """Render the read-back XML itself; rebuilding suggestions would lose edits."""
    import copy
    import os
    import subprocess
    from .kdenlive_render import melt_executable, write_json, review_module
    if sha256_file(project_dir/'timeline.kdenlive') != expected_revision:
        raise BackendError('kdenlive_project_changed_during_export')
    plan=read_project(project_dir)
    output_dir=output_dir.resolve()
    if output_dir.exists():
        raise BackendError('output_directory_already_exists')
    output_dir.mkdir()
    project=project_dir/'timeline.kdenlive'
    output=output_dir/'candidate.mp4'
    try:
        with (output_dir/'melt.log').open('w') as log:
            completed=subprocess.run([melt_executable(),str(project),'-consumer',f'avformat:{output}',
                'vcodec=libx264','acodec=aac','pix_fmt=yuv420p','crf=20','ab=192k','ar=48000','real_time=-1','threads=2',f"out={plan['frames']-1}"],
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},timeout=timeout_seconds)
        if completed.returncode or sha256_file(project)!=expected_revision:
            raise BackendError('kdenlive_saved_export_failed')
        original=json.loads((project_dir/'render-plan.json').read_text())
        inputs=[{**i,'sha256':sha256_file(Path(i['path']))} for i in original['inputs']]
        inputs.extend({'path':str(p),'sha256':sha256_file(p),'role':role} for p,role in [(project,'kdenlive_project_input'),(Path(plan['subtitles']),'rendered_subtitle_sidecar')])
        manifest={k:copy.deepcopy(v) for k,v in plan.items() if k not in ('engine_revision','render_kwargs','frames','project_id','project_revision')}
        manifest.update(contract='video_pipeline_manifest.v1',output={'path':str(output),'sha256':sha256_file(output)},inputs=inputs,assets=[],audio_tracks=1,video_tracks=1,width=original['width'],height=original['height'],removed_seconds=sum(c['endSeconds']-c['startSeconds'] for c in plan['executed_cuts']),ignored_review_only=[])
        path=output_dir/'candidate.mp4.manifest.json';write_json(path,manifest)
        checks=review_module().check_pipeline_manifest(path)
        result={'status':'candidate' if checks['status']=='passed' else 'failed','editor_backend':'otio_kdenlive','project_id':plan['project_id'],'project_revision':plan['project_revision'],'output':str(output),'manifest':str(path),'frames':plan['frames'],'duration':plan['duration'],'checks':checks}
        write_json(output_dir/'render-result.json',result)
        return result
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        write_json(output_dir/'render-result.json',{'status':'failed','editor_backend':'otio_kdenlive','reason':str(exc) if isinstance(exc,BackendError) else type(exc).__name__})
        raise BackendError('kdenlive_saved_export_failed') from exc
