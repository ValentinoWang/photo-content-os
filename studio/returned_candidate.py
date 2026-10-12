"""Project an uploaded export from measurements and, optionally, a saved project."""
import copy
from datetime import datetime, timezone
from fractions import Fraction
import re
import subprocess
from pathlib import Path

from edit_backends.interface import BackendError
from edit_backends.kdenlive_render import probe_media, srt_timestamp
from media_common import file_sha256
from openclaw_product_contract import video_digest
from video_candidate import preview_video, waveform_peaks


def openfilm_plan(backend, directory, output, suggestions):
    import json
    readback = backend.read_back(project_dir=directory)
    root = directory/'openfilm-project'
    config = json.loads((root/'adapter-project.json').read_text())
    for item in config['inputs']:
        if file_sha256(Path(item['path']))!=item['sha256']:
            raise BackendError('openfilm_original_input_changed')
    for item in config['working_media']:
        if file_sha256(root/item['path'])!=item['sha256']:
            raise BackendError('openfilm_working_media_changed')
    state = backend._state(root)
    if state['rev'] != readback['engine_revision']:
        raise BackendError('openfilm_project_changed_during_readback')
    rows = readback['time_map']
    cuts, cursor = [], 0.
    for row in [*rows, {'source_start': config['source_duration'], 'source_end': config['source_duration']}]:
        if row['source_start'] > cursor+1e-6:
            contributors = [s for s in suggestions if s.get('automatic') and s['type'] in ('silence','repetition') and s['start'] <= cursor+1e-6 and s['end'] >= row['source_start']-1e-6]
            if not contributors:
                raise BackendError('openfilm_cut_reason_unverified')
            cuts.append({'kind':'retake' if any(s['type']=='repetition' for s in contributors) else 'silence', 'startSeconds':cursor,'endSeconds':row['source_start']})
        cursor = row['source_end']
    clips = [c for t in state['doc']['tracks'] if not t.get('hidden') for c in t['clips']]
    assets = {a['path']: a for a in config['animation_assets']}
    placements = []
    for c in clips:
        if c['src'] in assets:
            box=c.get('box',{})
            if any(k not in box for k in ('x','y','w','h')) or c.get('speed',1)!=1:
                raise BackendError('openfilm_animation_geometry_unverified')
            placements.append({'animation_id':assets[c['src']]['animation_id'],'start':c.get('at',0),'end':c.get('at',0)+c['time'][1]-c['time'][0], 'geometry':dict(zip(('x','y','width','height'),(box[k] for k in ('x','y','w','h'))))})
    sub=state['subtitles'];style=sub['style']
    if not style['on'] or not sub['cues']:
        raise BackendError('openfilm_subtitle_trace_missing')
    subtitles=output/'readback.srt';subtitles.write_text(state['subtitleSrt'],encoding='utf-8')
    duration=max(c.get('at',0)+(c['time'][1]-c['time'][0])/c.get('speed',1) for c in clips)
    fps=30.
    return {'time_map':rows,'duration':duration,'fps':fps,'frames':round(duration*fps),'executed_cuts':cuts,
            'animation_placements':placements,'subtitles':str(subtitles),'subtitle_burned_in':True,
            'subtitle_bottom_ratio':style['pos']['y']}


def openchatcut_plan(backend,directory,output,suggestions):
    import json
    readback=backend.read_back(project_dir=directory)
    binding=json.loads((directory/'openchatcut-project.json').read_text())
    data=readback['native_snapshot'];state=data['state']
    for item in binding['inputs']:
        if file_sha256(Path(item['path']))!=item['sha256']:
            raise BackendError('openchatcut_original_input_changed')
    source_info=probe_media(Path(binding['source']))
    video=next(s for s in source_info['streams'] if s['codec_type']=='video')
    source_duration=float(video.get('duration') or source_info['format']['duration'])
    cuts=[];cursor=0.
    for row in [*readback['time_map'],{'source_start':source_duration,'source_end':source_duration}]:
        if row['source_start']>cursor+1e-6:
            contributors=[s for s in suggestions if s['automatic'] and s['type'] in ('silence','repetition') and s['start']<=cursor+1e-6 and s['end']>=row['source_start']-1e-6]
            if not contributors:raise BackendError('openchatcut_cut_reason_unverified')
            cuts.append({'kind':'retake' if any(s['type']=='repetition' for s in contributors) else 'silence','startSeconds':cursor,'endSeconds':row['source_start']})
        cursor=row['source_end']
    paths={a['id']:a['path'] for a in data['media']}
    allowed={a['path']:a['animation_id'] for a in binding['animations']}
    placements=backend._placements(data,binding['source_asset_id'])
    for placement in placements:
        path=paths.get(placement['editor_asset_id'])
        # Converted alpha assets retain the binding's conversion source.
        path=next((c['source'] for c in binding.get('conversions',[]) if c['output']==path),path)
        if path not in allowed:raise BackendError('openchatcut_animation_identity_unverified')
        placement['animation_id']=allowed[path]
    if not data['captions']:raise BackendError('openchatcut_subtitle_trace_missing')
    ratios=[]
    for track in data.get('captionTracks',[]):
        layout=track.get('layout',{})
        if layout.get('anchor','bottom-center')!='bottom-center' or layout.get('rotation',0)!=0 or layout.get('scale',1)!=1 or layout.get('opacity',1)!=1 or any(e.get('layout') or e.get('styleOverride') for e in track.get('sourceEntries',[])):
            raise BackendError('openchatcut_subtitle_position_unverified')
        style=track.get('nativePlacement',{});bottom=style.get('bottom')
        if isinstance(bottom,str) and bottom.endswith('%'):ratio=1-float(bottom[:-1])/100
        elif isinstance(bottom,(int,float)):ratio=1-bottom/state['height']
        else:raise BackendError('openchatcut_subtitle_position_unverified')
        ratios.append(ratio-layout.get('offsetYRatio',0))
    if not ratios:raise BackendError('openchatcut_subtitle_position_unverified')
    subs=output/'readback.srt';subs.write_text('\n\n'.join(f"{i}\n{srt_timestamp(w['start']/1000)} --> {srt_timestamp(w['end']/1000)}\n{w['text']}" for i,w in enumerate(data['captions'],1))+'\n')
    fps=float(state['fps']);duration=max((i['startFrame']+i['durationInFrames'])/fps for i in state['items'])
    return {'time_map':readback['time_map'],'fps':fps,'duration':duration,'frames':round(duration*fps),'executed_cuts':cuts,
            'animation_placements':placements,'subtitles':str(subs),'subtitle_burned_in':True,'subtitle_bottom_ratio':min(ratios),
            'project_id':binding['project_id'],'project_revision':binding['project_revision']}


def project_returned(ctx, video, output, inspected, checks, plan=None):
    stream=next(s for s in probe_media(video)['streams'] if s['codec_type']=='video')
    duration=float(stream['duration']);fps=float(Fraction(stream['avg_frame_rate']))
    source_info=probe_media(ctx['source'])
    source_stream=next(s for s in source_info['streams'] if s['codec_type']=='video')
    source_duration=float(source_stream.get('duration') or source_info['format']['duration'])
    c={'publicCandidateId':'candidate_'+file_sha256(video)[:32], 'identity':copy.deepcopy(ctx['identity']),
       'status':'candidate' if inspected['status']=='passed' else 'check_failed','description':'',
       'provenance':'native_readback' if plan else 'manual_export','durationSeconds':duration,'sourceDurationSeconds':source_duration,
       'frameCount':checks['actualFrames'],'fps':fps,'checks':checks,
       'returnedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
    if plan:
        c.update(cuts=plan['executed_cuts'],cutCount=len(plan['executed_cuts']),
                 removedSeconds=sum(x['endSeconds']-x['startSeconds'] for x in plan['executed_cuts']))
        text=Path(plan['subtitles']).read_text(encoding='utf-8')
        if len(text.encode())>200000 or '\x00' in text or re.search(r'(?:^|[\s\"\'=(:：])/(?:[\w.-]+/)+',text):
            raise BackendError('native_subtitle_privacy_rejected')
        c.update(subtitles=text,subtitleBurnedIn=plan['subtitle_burned_in'],subtitleBottomRatio=plan['subtitle_bottom_ratio'])
        animations=[]
        for p in plan['animation_placements']:
            original=next((a for a in ctx['descriptor']['animations'] if a['animationId']==p['animation_id']),None)
            if original is None:
                raise BackendError('native_animation_identity_unverified')
            a=copy.deepcopy(original);a.update(suggestedStartSeconds=p['start'],durationSeconds=p['end']-p['start'],timeBasis='edited');animations.append(a)
        c['animations']=animations
        black=subprocess.run(['ffmpeg','-nostdin','-v','info','-i',str(video),'-vf','blackframe=amount=98:threshold=32','-an','-f','null','-'],capture_output=True,text=True,check=True,timeout=1800)
        checks.update(subtitles='pass' if next((r['status'] for r in inspected['checks'] if r['check']=='subtitles'),None)=='passed' and plan['subtitle_burned_in'] and .8<=plan['subtitle_bottom_ratio']<=1 else 'fail',blackFrames='fail' if re.search(r'\bpblack:',black.stderr) else 'pass')
        if any(checks.get(k)!='pass' for k in ('playable','avSync','frameCount','sourceUnchanged','subtitles','blackFrames')):
            c['status']='check_failed'
    preview=output/'preview.mp4';c['preview']=preview_video(video,preview)
    c['waveformPeaks']=waveform_peaks(ctx['source'])
    c['candidateDigest']=video_digest(c)
    return {'candidate':c,'preview_ref':str(preview.resolve().relative_to(ctx['workspace'])),
            'progress':{'shotProgress':[],'waveformPeaks':c['waveformPeaks'],'waveformSource':'source'}}
