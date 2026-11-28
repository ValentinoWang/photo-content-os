"""Compile a saved media-first arrangement and produce workspace-local draft artifacts.

The caller owns confirmation, CAS, choice/readiness and publishing the returned index.
Run generation in a job, then recheck its input binding before publishing anything.
"""
from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import uuid
import urllib.parse
import xml.etree.ElementTree as ET

from scripts.runtime_paths import local_media_root, repository_root
from scripts.roughcut_planner import plan_roughcut

# Frozen editing consumers use top-level imports and the project's fixed runtime.
if __package__:
    from .constants import (
        SCRIPTS,
        PLANNER_VERSION,
        FPS,
    )
else:
    try:
        from studio.constants import (
            SCRIPTS,
            PLANNER_VERSION,
            FPS,
        )
    except ImportError:
        from constants import (
            SCRIPTS,
            PLANNER_VERSION,
            FPS,
        )
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from edl_contract import normalise_edl, parse_time_range
from render_preview import build_plan, execute_plan
from edit_backends.kdenlive_adapter import Backend
from edit_backends.kdenlive_readback import audio_graph_differences
from edit_backends.otio_kdenlive import prepare_edl_audio
from edit_backends import handoff_pack



class DraftError(ValueError):
    def __init__(self, code, *, receipt_path=None):
        self.code = code
        self.receipt_path = str(receipt_path) if receipt_path else None
        super().__init__(code)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _ms(value):
    return float(Decimal(str(value)).quantize(Decimal('0.001'),rounding=ROUND_HALF_UP))


def _millisecond_times(value):
    if isinstance(value,list):
        return [_millisecond_times(item) for item in value]
    if isinstance(value,dict):
        return {key:_ms(item) if key.endswith('_sec') and type(item) in (int,float)
                else _millisecond_times(item) for key,item in value.items()}
    return value


def _sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b''):
            value.update(chunk)
    return value.hexdigest()


def _json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)+'\n')
    temporary.replace(path)


def _run(command):
    subprocess.run([str(x) for x in command], capture_output=True, check=True, timeout=1800)


def compile_roughcut_edl(*, plan, planner_inputs, sources_by_media, music_sources,
                        project_id, project_revision):
    """Return normalized EDL; reject a plan that differs from its complete inputs.

    sources_by_media and music_sources are explicit selected local paths. At this
    boundary original photos are accepted; generation prepares duration-bound
    photo videos before passing one identical EDL to both frozen consumers.
    """
    if plan != plan_roughcut(**copy.deepcopy(planner_inputs)):
        raise DraftError('roughcut_inputs_stale')
    shots = {s['id']:s for s in planner_inputs['shots']}
    source_versions = {str(key):_sha(path) for key,path in sources_by_media.items()}
    music_versions = {str(key):_sha(path) for key,path in music_sources.items()}
    provenance = dict(kind='media_first_planner',planner='roughcut_planner',planner_version=PLANNER_VERSION,
        preset_id=planner_inputs['preset']['id'],preset_name=planner_inputs['preset']['name'],
        input_digest=_digest(dict(inputs=planner_inputs,sources=source_versions,music=music_versions,
                                 project_id=project_id,project_revision=project_revision)))
    clips, by_shot = [], {}
    for item in plan['clips']:
        shot = shots[item['shot_id']]
        if item['kind']=='video' and not (shot['start_sec']-1e-6 <= item['source_start'] < item['source_end'] <= shot['end_sec']+1e-6):
            raise DraftError('shot_too_short')
        start,end = _ms(item['start']),_ms(item['end'])
        source_start = 0
        if item['kind']=='video':
            # Millisecond EDL times must stay inside the selected original span.
            lo=math.ceil(shot['start_sec']*1000-1e-7)
            hi=math.floor((shot['end_sec']-(end-start))*1000+1e-7)
            if hi<lo:
                raise DraftError('shot_too_short')
            source_start=max(lo,min(round(_ms(item['source_start'])*1000),hi))/1000
        clip = dict(slot=len(clips)+1,time_range=f"{start:.3f}-{end:.3f}",
            source_start_sec=source_start,source_file=str(Path(sources_by_media[item['media_id']]).resolve()),
            purpose=shot['scene'],visual_need=shot['scene'],caption='',
            edit_note='按粗剪方案排列。')
        if item['kind']=='photo':
            clip['audio_mute'] = True
        by_shot[item['shot_id']] = clip
        clips.append(clip)
    if abs(plan['clips'][-1]['end']-plan['metrics']['last_cut_sec']-1.6)>1e-6:
        raise DraftError('shot_too_short')
    beds, ducks = [], {}
    for occurrence in plan['occurrences']:
        if not occurrence['live']:
            continue
        reason = occurrence['reason_data']
        if occurrence['technique']=='jcut':
            by_shot[occurrence['shot_ids'][-1]]['audio_lead_sec'] = reason['lead_sec']
        elif occurrence['technique']=='bed':
            source = by_shot[reason['source_shot_id']]['source_file']
            beds.append(dict(source=source,source_start_sec=reason['source_start_sec'],
                timeline_start_sec=occurrence['at'],timeline_end_sec=occurrence['end'],volume=1,
                fade_in_sec=.03,fade_out_sec=.03))
            for sid in occurrence['shot_ids']:
                by_shot[sid]['audio_mute'] = True
        elif occurrence['technique']=='duck':
            for region in reason['regions']:
                ducks.setdefault(region['song_id'],[]).append(dict(start_sec=region['start'],end_sec=region['end'],gain=region['gain'],ramp_sec=region['ramp_sec']))
    # A muted picture's early sound must still come from that picture's
    # original source, not from the different shot chosen for the continuous bed.
    for clip in clips:
        if clip.get('audio_mute') and clip.get('audio_lead_sec'):
            lead = clip.pop('audio_lead_sec')
            start, _ = parse_time_range(clip['time_range'])
            beds.append(dict(source=clip['source_file'],source_start_sec=clip['source_start_sec']-lead,
                timeline_start_sec=start-lead,timeline_end_sec=start,volume=1,
                fade_in_sec=.03,fade_out_sec=.03))
    music = []
    for song in plan['songs']:
        regions = sorted(ducks.get(song['id'],[]),key=lambda r:r['start_sec'])
        merged = []
        for region in regions:
            if merged and region['start_sec']-region['ramp_sec'] <= merged[-1]['end_sec']+merged[-1]['ramp_sec']+1e-6:
                merged[-1]['end_sec'] = max(merged[-1]['end_sec'],region['end_sec'])
                merged[-1]['ramp_sec'] = min(merged[-1]['ramp_sec'],region['ramp_sec'])
            else:
                merged.append(copy.deepcopy(region))
        music.append(dict(source=str(Path(music_sources[song['track_id']]).resolve()),source_start_sec=song['offset'],
            timeline_start_sec=song['start'],timeline_end_sec=song['end'],volume=1,
            fade_in_sec=.03,fade_out_sec=min(1.6,(song['end']-song['start'])/2),duck_regions=merged))
    return normalise_edl(_millisecond_times(dict(project_id=project_id,project_revision=project_revision,source_script_used=False,
        provenance=provenance,clips=clips,audio_beds=beds,music=music,missing_materials=[])))


def readback_video(project_path):
    """Read the saved XML picture playlist, not cached render-plan metadata."""
    root = ET.parse(project_path).getroot()
    profile=root.find('profile')
    if profile is None or int(profile.get('frame_rate_num'))/int(profile.get('frame_rate_den'))!=FPS:
        raise DraftError('draft_failed')
    producers = {p.get('id'):p for p in root.findall('producer')}
    playlists = [p for p in root.findall('playlist') if p.findtext("property[@name='content_os:layer']")=='primary']
    if len(playlists)!=1:
        raise DraftError('draft_failed')
    at, rows = 0, []
    for node in playlists[0]:
        if node.tag=='blank':
            at += int(node.get('length'))
        elif node.tag=='entry':
            producer = producers[node.get('producer')]
            lo, hi = int(node.get('in')), int(node.get('out'))+1
            rows.append(dict(slot=int(producer.findtext("property[@name='kdenlive:clipname']").split('_',1)[0]),
                source=producer.findtext("property[@name='resource']"),
                start=at/FPS,end=(at+hi-lo)/FPS,source_start=lo/FPS,source_end=hi/FPS))
            at += hi-lo
    return rows


def _check_pictures(path, edl):
    rows = readback_video(path)
    if len(rows)!=len(edl['clips']):
        raise DraftError('draft_failed')
    for row, clip in zip(rows,edl['clips']):
        start,end = parse_time_range(clip['time_range'])
        start_frame,end_frame=round(start*FPS),round(end*FPS)
        source_frame=round(clip['source_start_sec']*FPS)
        expected=dict(start=start_frame,end=end_frame,source_start=source_frame,
                      source_end=source_frame+end_frame-start_frame)
        if row['slot']!=clip['slot'] or row['source']!=clip['source_file'] or any(
                abs(row[key]*FPS-frame)>1e-6 for key,frame in expected.items()):
            raise DraftError('draft_failed')
    return rows


def _verify_binding(receipt, arguments):
    if any(_sha(b['original_source'])!=b['original_sha256'] for b in receipt['shot_bindings']):
        raise DraftError('roughcut_inputs_stale')
    current=compile_roughcut_edl(**arguments)
    if current['provenance']['input_digest']!=receipt['input_digest']:
        raise DraftError('roughcut_inputs_stale')


def _artifact_result(*, root, directory, project_id, plan_revision, receipt, result, specs):
    artifacts,index=[],{}
    for path,kind,mime in specs:
        identity='draft-'+_digest(dict(attempt=directory.name,file=path.name,sha256=_sha(path)))[:32]
        artifacts.append(dict(id=identity,kind=kind,content_type=mime,revision=plan_revision,shot_id=None,
            url=f'/api/review/pieces/{urllib.parse.quote(project_id,safe="")}/roughcut/media/{identity}'))
        index[identity]=dict(relative_path=path.relative_to(root).as_posix(),
            allowed_root=directory.relative_to(root).as_posix(),content_type=mime)
    result['artifact_ids']=[a['id'] for a in artifacts]
    receipt.update(status='done',checks=result['checks'],
        artifacts=[{**a,**index[a['id']],'sha256':_sha(root/index[a['id']]['relative_path'])} for a in artifacts])
    receipt_path=directory/'receipt.json'
    _json(receipt_path,receipt)
    return dict(result=result,artifacts=artifacts,artifact_index=index,directory=str(directory),
                receipt_path=str(receipt_path),duration_sec=receipt['preview_duration_sec'])


def _record_failure(directory, receipt, exc, *, default_code):
    code=exc.code if isinstance(exc,DraftError) else default_code
    receipt_path=directory/'receipt.json'
    receipt.update(status='failed',error_code=code,artifacts=[],checks=[],
        partial_files=[p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file() and p!=receipt_path])
    _json(receipt_path,receipt)
    return DraftError(code,receipt_path=receipt_path)


def generate_preview(*, workspace, plan, planner_inputs, sources_by_media, music_sources,
                     project_id, project_revision, plan_revision,
                     media_root=None, width=640, height=360) -> dict:
    """Compile and render a workspace-local preview without an editing backend.

    Return artifacts/index in the same envelope as generate_draft, plus the
    probed duration_sec. The source EDL and audit receipt stay in directory;
    only the preview is indexed. The caller owns confirmation and publication.
    """
    root = Path(workspace).expanduser().resolve()
    media = local_media_root(media_root)
    if not root.is_dir() or not root.is_relative_to(media) or root.is_relative_to(repository_root()):
        raise DraftError('draft_failed')
    if type(project_revision) is not int or project_revision<1 or type(plan_revision) is not int or plan_revision<1:
        raise DraftError('draft_failed')
    if any(type(n) is not int or n<=0 or n%2 for n in (width,height)):
        raise DraftError('preview_failed')
    try:
        sources = {k:Path(v).expanduser().resolve(strict=True) for k,v in sources_by_media.items()}
        songs = {k:Path(v).expanduser().resolve(strict=True) for k,v in music_sources.items()}
        if any(not p.is_file() or not p.is_relative_to(media) for p in [*sources.values(),*songs.values()]):
            raise DraftError('draft_failed')
        edl = compile_roughcut_edl(plan=plan,planner_inputs=planner_inputs,sources_by_media=sources,
            music_sources=songs,project_id=project_id,project_revision=project_revision)
    except DraftError:
        raise
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise DraftError('draft_failed') from exc
    base = root/'draft-project/roughcut'
    # Resolve the complete destination before mkdir; a symlink cannot redirect
    # a worker into another workspace or the software checkout.
    if not base.resolve().is_relative_to(root):
        raise DraftError('draft_failed')
    directory = base/str(plan_revision)/uuid.uuid4().hex
    if not directory.resolve().is_relative_to(root):
        raise DraftError('draft_failed')
    directory.mkdir(parents=True,exist_ok=False)
    receipt_path = directory/'receipt.json'
    receipt = dict(schema_version='roughcut_preview_receipt_v1',status='running',
        project_id=project_id,project_revision=project_revision,plan_revision=plan_revision,
        input_digest=edl['provenance']['input_digest'],summary=copy.deepcopy(plan['metrics']),
        edl_time_precision_sec=.001,editor_frame_tolerance_sec=1/FPS,
        source_end_quantization_bound_sec=1.5/FPS,
        artifacts=[],checks=[],shot_bindings=[])
    _json(receipt_path,receipt)
    arguments=dict(plan=plan,planner_inputs=planner_inputs,sources_by_media=sources,
        music_sources=songs,project_id=project_id,project_revision=project_revision)
    try:
        for clip, item in zip(edl['clips'],plan['clips']):
            source=Path(clip['source_file'])
            original_hash=_sha(source)
            if item['kind']=='photo':
                photo_dir=directory/'photo-sources';photo_dir.mkdir(exist_ok=True)
                proxy=photo_dir/f"{clip['slot']}.mp4"
                duration=item['end']-item['start']
                image_source=source
                if source.suffix.lower() in ('.heic','.heif'):
                    from PIL import Image, ImageOps
                    from pillow_heif import register_heif_opener
                    register_heif_opener()
                    image_source=photo_dir/f"{clip['slot']}.png"
                    with Image.open(source) as image:
                        ImageOps.exif_transpose(image).convert('RGB').save(image_source)
                _run(['ffmpeg','-nostdin','-v','error','-n','-loop','1','-i',image_source,
                    '-t',f'{math.ceil(duration*FPS)/FPS:.6f}','-vf',
                    f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1',
                    '-r',str(FPS),'-c:v','libx264','-pix_fmt','yuv420p',proxy])
                clip.update(source_file=str(proxy),candidate_files=[str(proxy)])
            receipt['shot_bindings'].append(dict(shot_id=item['shot_id'],kind=item['kind'],
                original_source=str(source),original_sha256=original_hash,edl_source=clip['source_file'],
                source_start_sec=clip['source_start_sec'],time_range=clip['time_range']))
        edl=normalise_edl(edl)
        edl_path=directory/'06_edit_decision_list.json';_json(edl_path,edl)
        receipt['edl_digest']=_sha(edl_path)
        preview=directory/'preview.mp4'
        preview_plan=build_plan(edl,project=media,output=preview,width=width,height=height)
        _json(directory/'preview-plan.json',preview_plan)
        execute_plan(preview_plan)
        probe=subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(preview)],
            check=True,capture_output=True,text=True,timeout=30)
        facts=json.loads(probe.stdout)
        if abs(float(facts['format']['duration'])-plan['metrics']['duration_sec'])>1/FPS+.02 or not any(s['codec_type']=='video' for s in facts['streams']):
            raise DraftError('preview_failed')
        receipt['preview_duration_sec']=float(facts['format']['duration'])
        _verify_binding(receipt,arguments)
        checks=[dict(id=key,status='passed') for key in
                ('source_ranges','shot_identity','duration','photos','audio','music')]
        result=dict(project_revision=project_revision,edl_digest=receipt['edl_digest'],checks=checks)
        return _artifact_result(root=root,directory=directory,project_id=project_id,plan_revision=plan_revision,
            receipt=receipt,result=result,specs=[(preview,'preview','video/mp4')])
    except Exception as exc:
        raise _record_failure(directory,receipt,exc,default_code='preview_failed') from exc


def generate_draft(*, workspace, plan, planner_inputs, sources_by_media, music_sources,
                   project_id, project_revision, plan_revision, editor_choice,
                   media_root=None, width=640, height=360):
    """Generate a preview and the selected draft in one workspace-local attempt.

    The choice is the saved snapshot from the service, never a client override.
    The caller owns confirmation, revision checks and artifact publication.
    """
    method,editor = editor_choice.get('method'),editor_choice.get('editor')
    if method!='guide' and (method!='external' or editor!='otio_kdenlive'):
        raise DraftError('draft_backend_unsupported')
    arguments=dict(plan=plan,planner_inputs=planner_inputs,sources_by_media=sources_by_media,
        music_sources=music_sources,project_id=project_id,project_revision=project_revision)
    try:
        generated=generate_preview(workspace=workspace,plan_revision=plan_revision,media_root=media_root,
            width=width,height=height,**arguments)
    except DraftError as exc:
        if exc.receipt_path:
            receipt_path=Path(exc.receipt_path)
            receipt=json.loads(receipt_path.read_text())
            receipt.update(schema_version='roughcut_draft_receipt_v1',editor=editor,method=method)
            _json(receipt_path,receipt)
        raise
    root=Path(workspace).expanduser().resolve()
    media=local_media_root(media_root)
    directory=Path(generated['directory'])
    receipt_path=Path(generated['receipt_path'])
    receipt=json.loads(receipt_path.read_text())
    receipt.update(schema_version='roughcut_draft_receipt_v1',status='running',editor=editor,method=method,
                   artifacts=[],checks=[])
    _json(receipt_path,receipt)
    try:
        edl_path=directory/'06_edit_decision_list.json'
        edl=json.loads(edl_path.read_text())
        if method=='guide':
            storyboard=directory/'05_storyboard.md'
            storyboard.write_text('\n'.join(f"- 第 {clip['slot']} 镜：{clip['time_range']}" for clip in edl['clips'])+'\n')
            handoff_pack.generate(project_id=project_id,project_revision=project_revision,edl_path=edl_path,
                storyboard_path=storyboard,output_root=directory/'edit-handoff',materials_path=None,revision_basis_path=None)
            handoff_pack.validate(directory/'edit-handoff'/str(project_revision)/'manifest.json')
        else:
            Backend().generate_from_edl(edl_path=edl_path,output_dir=directory/'kdenlive',media_root=media,
                project_id=project_id,project_revision=project_revision)
            rows=_check_pictures(directory/'kdenlive/timeline.kdenlive',edl)
            # Compare saved audio entries, gain keyframes and mix routing with a
            # freshly compiled EDL plan, using the editor's explicit frame clock.
            _,_,audio_plan=prepare_edl_audio(edl,media)
            render_plan=json.loads((directory/'kdenlive/render-plan.json').read_text())
            actual,mismatches=audio_graph_differences(ET.parse(directory/'kdenlive/timeline.kdenlive').getroot(),
                directory/'kdenlive',audio_plan,render_plan.get('audio_sources'))
            audible_end=max((a['timeline_end_sec'] for a in actual),default=0)
            if mismatches or abs(audible_end-audio_plan['duration_sec'])>1/FPS+.002:
                raise DraftError('draft_failed')
            receipt['readback']=dict(pictures=rows,audio=dict(audio_segments=actual,
                audio_matches_plan=True,audio_mismatches=mismatches,duration=audible_end,
                nominal_duration_sec=audio_plan['duration_sec'],frame_tolerance_sec=1/FPS))
        _verify_binding(receipt,arguments)
        checks=[dict(id=key,status='manual' if method=='guide' and key in ('audio','music','readback') else 'passed')
            for key in ('source_ranges','shot_identity','duration','photos','audio','music','readback')]
        specs=[(directory/'preview.mp4','preview','video/mp4'),(edl_path,'draft','application/json')]
        if method=='guide':
            package=directory/'edit-handoff'/str(project_revision)
            specs += [(package/'manifest.json','guide','application/json'),
                      (package/'剪辑交接说明.md','guide','text/markdown; charset=utf-8')]
        else:
            specs += [(directory/'kdenlive/timeline.kdenlive','draft','application/xml')]
        result=dict(editor=editor,method=method,project_revision=project_revision,
                    edl_digest=receipt['edl_digest'],checks=checks)
        return _artifact_result(root=root,directory=directory,project_id=project_id,plan_revision=plan_revision,
            receipt=receipt,result=result,specs=specs)
    except Exception as exc:
        raise _record_failure(directory,receipt,exc,default_code='draft_failed') from exc
