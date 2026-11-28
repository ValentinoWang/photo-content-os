"""Read the saved MLT graph, never reuse a render plan's timeline."""
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ..interface import BackendError
from .kdenlive_render import probe_media, sha256_file, timeline_tractor
from .otio_kdenlive import FPS, audio_level_keyframes, frames


def properties(node):
    return {p.get('name'): p.text or '' for p in node.findall('property')}


def same_frame_time(first, second, fps):
    """Compare fractional frame positions without rounding away a half-frame error."""
    delta = (Fraction(str(first)) - Fraction(str(second))) * Fraction(str(fps))
    return abs(delta) < Fraction(1, 2)


def level_frames(value):
    """Native saves may serialize animation positions as MLT clock times."""
    values = []
    for entry in value.split(';'):
        position, gain = entry.split('=')
        if ':' in position:
            h, m, s = position.split(':')
            position = frames(int(h)*3600 + int(m)*60 + float(s))
        values.append((int(position), round(float(gain), 6)))
    return values


def read_audio_graph(root, directory: Path) -> list[dict]:
    """Traverse audible graph edges, including the pure audio editing tractors."""
    nodes = {node.get("id"): node for node in root if node.get("id")}
    profile = root.find("profile")
    fps = float(Fraction(int(profile.get("frame_rate_num")), int(profile.get("frame_rate_den"))))
    def frame(value):
        if ":" in value:
            h, m, s = value.split(":")
            return round((int(h)*3600 + int(m)*60 + float(s))*fps)
        return int(value)
    sounds = []
    def walk(node, at=0, audible=True, lane=None, ancestors=()):
        identity = node.get("id")
        if identity in ancestors:
            raise BackendError("kdenlive_graph_cycle")
        ancestors = (*ancestors, identity)
        values = properties(node)
        if values.get("kdenlive:audio_track") == "1" and node.tag == "playlist":
            lane = int(values["content_os:physical_lane"]) - 1 if "content_os:physical_lane" in values else lane
        if audible and any(properties(f).get("disable") != "1" for f in node.findall("filter")):
            raise BackendError("kdenlive_audio_track_effect_unverified")
        if node.tag == "tractor":
            audio_lane = 0
            for track in node.findall("track"):
                if properties(nodes[track.get("producer")]).get("kdenlive:audio_track") == "1" and node is timeline_tractor(root):
                    lane = audio_lane
                    audio_lane += 1
                if frame(track.get("in", "0")):
                    raise BackendError("kdenlive_nested_trim_unsupported")
                walk(nodes[track.get("producer")], at, audible and track.get("hide") not in ("audio", "both"), lane, ancestors)
        elif node.tag == "playlist":
            cursor = at
            for entry in node:
                if entry.tag == "blank":
                    cursor += frame(entry.get("length"))
                elif entry.tag == "entry":
                    start, end = frame(entry.get("in", "0")), frame(entry.get("out")) + 1
                    if start < 0 or end <= start:
                        raise BackendError("kdenlive_project_time_invalid")
                    producer = nodes[entry.get("producer")]
                    info = properties(producer)
                    if audible:
                        if lane is None:
                            raise BackendError("kdenlive_video_audio_unverified")
                        if info.get("mlt_service") not in ("avformat", "avformat-novalidate") or "content_os:audio_segment_id" not in info:
                            raise BackendError("kdenlive_audio_source_unverified")
                        filters = producer.findall("filter")
                        gains = [f for f in filters if properties(f).get("mlt_service") == "volume"]
                        ramps = [f for f in filters if properties(f).get("mlt_service") == "avfilter.afade"]
                        if len(filters) != 2 or len(gains) != 1 or len(ramps) != 1 or entry.findall("filter"):
                            raise BackendError("kdenlive_audio_gain_unverified")
                        volume = gains[0]
                        ramp = ramps[0]
                        if (frame(ramp.get("in", "0")) != start or frame(ramp.get("out", "0")) != start or
                            any(properties(ramp).get(k) != v for k, v in {"internal_added": "1", "av.type": "in"}.items()) or
                            abs(float(properties(ramp).get("av.duration", "-1"))-1/fps) > 1e-9 or properties(ramp).get("disable") == "1"):
                            raise BackendError("kdenlive_audio_initial_ramp_unverified")
                        level = properties(volume)
                        if level.get("disable") == "1" or info.get("set.test_audio") == "1" or level.get('kdenlive_id') != 'volume':
                            raise BackendError("kdenlive_audio_gain_or_stream_unverified")
                        resource = Path(info["resource"]).expanduser()
                        if not resource.is_absolute():
                            resource = directory / resource
                        if "audio_index" in info:
                            first_audio = next(s["index"] for s in probe_media(resource)["streams"] if s["codec_type"] == "audio")
                            if int(info["audio_index"]) != first_audio:
                                raise BackendError("kdenlive_audio_stream_changed")
                        sounds.append({"id": info["content_os:audio_segment_id"], "source": str(resource.resolve()),
                                       "timeline_start_sec": cursor/fps, "timeline_end_sec": (cursor+end-start)/fps,
                                       "source_start_sec": start/fps, "source_end_sec": end/fps,
                                       "physical_track": lane, "level_keyframes_db": level["level"],
                                       "initial_ramp_start_sec": float(properties(ramp).get("av.start_time", "-1")),
                                       "filter_in_frame": frame(volume.get("in", "0")),
                                       "filter_out_frame": frame(volume.get("out", str(end-1)))})
                    cursor += end - start
    walk(timeline_tractor(root))
    return sounds


def audio_graph_differences(root, directory, audio_plan, audio_sources=None):
    actual = read_audio_graph(root, directory)
    profile = root.find("profile")
    fps = float(Fraction(int(profile.get("frame_rate_num")), int(profile.get("frame_rate_den"))))
    expected = {}
    for sound in audio_plan["segments"]:
        start, end = frames(sound["timeline_start_sec"]), frames(sound["timeline_end_sec"])
        source = frames(sound["source_start_sec"])
        source_path = (audio_sources or {}).get(sound['source'], sound['source'])
        expected[sound["id"]] = {"id": sound["id"], "source": str(Path(source_path).resolve()),
            "timeline_start_sec": start/FPS, "timeline_end_sec": end/FPS,
            "source_start_sec": source/FPS, "source_end_sec": (source+end-start)/FPS,
            "physical_track": sound["physical_track"], "level_keyframes_db": audio_level_keyframes(sound, end-start),
            "initial_ramp_start_sec": start/FPS,
            "filter_in_frame": source, "filter_out_frame": source+end-start-1}
    mismatches = []
    seen = set()
    for sound in actual:
        identity = sound["id"]
        if identity in seen:
            mismatches.append(f"{identity}:duplicate")
        seen.add(identity)
        if identity not in expected:
            mismatches.append(f"{identity}:unexpected")
            continue
        for key, value in expected[identity].items():
            if key == 'level_keyframes_db':
                same = level_frames(sound[key]) == level_frames(value)
            elif key.endswith('_sec'):
                same = key in sound and same_frame_time(sound[key], value, fps)
            else:
                same = sound.get(key) == value
            if not same:
                mismatches.append(f"{identity}:{key}")
    mismatches.extend(f"{identity}:missing" for identity in expected.keys() - seen)
    sequence = timeline_tractor(root)
    nodes = {node.get("id"): node for node in root if node.get("id")}
    audio_indices = [i for i, t in enumerate(sequence.findall("track")) if properties(nodes[t.get("producer")]).get("kdenlive:audio_track") == "1"]
    transitions = [t for t in sequence.findall("transition") if properties(t).get("mlt_service") == "mix"]
    mixes = [properties(t) for t in transitions]
    def frame(value):
        if ":" in value:
            h, m, s = value.split(":")
            return frames(int(h)*3600 + int(m)*60 + float(s))
        return int(value)
    trimmed = any(frame(t.get("in", "0")) != 0 or
                  (t.get('out') is not None and frame(t.get('out')) < frames(audio_plan["duration_sec"]) - 1) or
                  (t.get('out') is None and properties(t).get('internal_added') != '237') for t in transitions)
    altered_gain = any(m.get("sum") != "1" or m.get("a_track") != "0" or m.get("always_active") != "1" or
                       m.get('internal_added') != '237' or m.get('accepts_blanks') != '1' or
                       m.get("disable") == "1" or any(key in m for key in ("start", "end", "reverse", "combine")) for m in mixes)
    if sorted(int(m.get("b_track", "-1")) for m in mixes) != audio_indices or trimmed or altered_gain:
        mismatches.append("mix:physical_tracks_or_gain")
    return actual, mismatches


def read_edl_project(root, directory, plan, receipt):
    for item in plan["inputs"]:
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise BackendError("kdenlive_original_input_changed")
    for item in plan['inputs']:
        if sha256_file(Path(item['path'])) != item['sha256']:
            raise BackendError('kdenlive_original_input_changed')
    actual, mismatches = audio_graph_differences(root, directory, plan["audio_plan"], plan.get('audio_sources'))
    approved = {str(Path(item["path"]).resolve()) for item in plan["inputs"] if item["role"] in ("edl_media", "prepared_audio")}
    if any(sound["source"] not in approved for sound in actual):
        raise BackendError("kdenlive_unapproved_project_asset")
    profile = root.find("profile")
    fps = float(Fraction(int(profile.get("frame_rate_num")), int(profile.get("frame_rate_den"))))
    sequence = timeline_tractor(root)
    # Native projects add an editor-only blank tail and an inclusive wrapper
    # frame. The actual audio entries determine the audible content duration.
    duration = max((s['timeline_end_sec'] for s in actual), default=0)
    if fps != FPS or not same_frame_time(duration, plan["duration"], fps):
        mismatches.append("sequence:fps_or_duration")
    return {"project_id": receipt["project_id"], "project_revision": receipt["project_revision"],
            "mode": "edl_audio", "audio_segments": actual, "audio_matches_plan": not mismatches,
            "audio_mismatches": mismatches, "duration": duration, "fps": fps,
            "engine_revision": sha256_file(directory / "timeline.kdenlive")}


def read_project(project_dir: Path) -> dict:
    directory = project_dir.resolve()
    project = directory / 'timeline.kdenlive'
    if not project.is_file():
        raise BackendError('kdenlive_owned_project_missing')
    raw = project.read_bytes()
    if len(raw) > 10_000_000 or b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise BackendError('kdenlive_project_invalid')
    try:
        root = ET.fromstring(raw)
        plan = json.loads((directory / 'render-plan.json').read_text())
        receipt = json.loads((directory / 'render-result.json').read_text())
        identity = properties(root)
        if plan.get("doc_type") == "edl_audio_kdenlive_plan":
            identity = properties(root.find("playlist[@id='main_bin']"))
            identity["content_os.project_revision"] = identity.get("kdenlive:docproperties.content_os_revision")
        if root.tag != 'mlt' or identity.get('kdenlive:docproperties.projectid') != receipt['project_id'] or identity.get('content_os.project_revision') != str(receipt['project_revision']):
            raise BackendError('kdenlive_project_identity_mismatch')
        if plan.get("doc_type") == "edl_audio_kdenlive_plan":
            return read_edl_project(root, directory, plan, receipt)
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
            if ((r['source_start'] < cursor and not same_frame_time(r['source_start'], cursor, fps)) or
                (r['source_end'] > source_duration and not same_frame_time(r['source_end'], source_duration, fps))):
                raise BackendError('kdenlive_source_reorder_unsupported')
            if r in ranges and not same_frame_time(r['output_start'], output, fps):
                raise BackendError('kdenlive_source_gap_unsupported')
            if r['source_start'] > cursor and not same_frame_time(r['source_start'], cursor, fps):
                # The XML establishes boundaries; the producer supplies only
                # the acoustic reason, which cannot be invented from a gap.
                facts = [c for c in plan.get('executed_cuts', [])
                         if (c['startSeconds'] <= cursor or same_frame_time(c['startSeconds'], cursor, fps))
                         and (c['endSeconds'] >= r['source_start'] or same_frame_time(c['endSeconds'], r['source_start'], fps))]
                cuts.append({'kind': facts[0]['kind'] if facts else 'manual', 'startSeconds': cursor, 'endSeconds': min(r['source_start'], source_duration)})
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
        if not same_frame_time(duration, output, fps) or any(
                p['end'] > duration and not same_frame_time(p['end'], duration, fps) for p in placements):
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
