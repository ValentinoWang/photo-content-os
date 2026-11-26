"""Identity-bound local editing sessions. Cloud projections contain no locators."""
from __future__ import annotations
import copy
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid
from edit_backends.registry import BACKENDS, get_backend
from edit_backends.kdenlive_render import probe_media, sha256_file
from media_project_selection import RefineRun, SelectionError, delivered_context
from studio.direct_handoff_contract import read_delivered_handoff, read_handoff
from studio.project_store import ProjectStoreError


def candidate_failed(candidate):
    checks = candidate.get('checks', {})
    return candidate.get('status') in ('failed', 'check_failed') or (isinstance(checks, dict) and any(v in ('fail', 'failed') for v in checks.values() if isinstance(v, str))) or (isinstance(checks, list) and any(c.get('status') in ('fail', 'failed') for c in checks))


def review_projection(result):
    groups={row['check']:row for row in result['checks']}
    def status(names):
        rows=[groups[n]['status'] for n in names if n in groups]
        return 'fail' if 'failed' in rows else 'pass' if len(rows)==len(names) and all(v=='passed' for v in rows) else 'unknown'
    av=groups.get('av_duration',{}).get('details',{}).get('stream_seconds',[])
    frame=groups.get('frames',{}).get('details',{})
    return {'playable':status(['decode','tracks']),'avSync':status(['av_duration']),'frameCount':status(['frames']),
            'sourceUnchanged':status(['original_integrity']),'avOffsetSeconds':abs(av[0]-av[1]) if len(av)==2 else None,
            'avOffsetLimitSeconds':.1,'actualFrames':frame.get('frames'),'expectedFrames':round(frame['duration']*frame['fps']) if frame.get('fps') and frame.get('duration') else None}


def _replace_ops(before, after):
    return ([{'op': 'remove', 'clip': c['id']} for t in before['tracks'] for c in t['clips']]
            + [{'op': 'insert', 'clip': c, **({'newTrack': ti} if ci == 0 else {'track': ti})} for ti, t in enumerate(after['tracks']) for ci, c in enumerate(t['clips'])])


class VideoWorkflow:
    def __init__(self, app):
        self.app = app
        self.sessions = {}
        self.probes = None
        self.lock = threading.RLock()
        self.origin = None

    def editors(self, refresh=False):
        with self.lock:
            if self.probes is None or refresh:
                rows = []
                for bid in BACKENDS:
                    backend = get_backend(bid)
                    try:
                        rows.append({**backend.describe(), 'probe': backend.probe()})
                    finally:
                        backend.close()
                self.probes = rows
            return copy.deepcopy(self.probes)

    def context(self, project_id, *, identity=None, delivered_only=False):
        if delivered_only:
            try:
                handoff = delivered_context(self.app.store, project_id, identity)
            except SelectionError as exc:
                raise ProjectStoreError('revision_conflict', '作品交接已变化，请重新打开作品') from exc
        else:
            handoff = (read_delivered_handoff(self.app.store, project_id, device_id=None)
                       or read_handoff(self.app.store, project_id))
        if handoff is None:
            raise ProjectStoreError('video_binding_invalid', '作品交接已变化，请重新打开作品')
        data = self.app._video_handoff_projection(project_id, context=handoff)
        root, workspace, binding, descriptor = (handoff[k] for k in ('root', 'workspace', 'binding', 'descriptor'))
        identity = descriptor['identity']
        key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        run = workspace / 'runs' / hashlib.sha256(identity['jobId'].encode()).hexdigest()[:32]
        run.mkdir(parents=True, exist_ok=True)
        def local(ref):
            p = (root / ref).resolve()
            if not p.is_relative_to(root) or not p.is_file():
                raise ProjectStoreError('video_input_invalid', '交接素材不可用，请重新交接')
            return p
        refs = binding.get('source_refs', [])
        source = next((local(r) for r in refs if Path(r).suffix.lower() in {'.mp4', '.mov', '.mkv'}), None)
        subs = next((local(r) for r in refs if Path(r).suffix.lower() == '.srt'), None)
        # Bound render arguments can name files not listed as upload originals.
        for step in binding.get('steps', []):
            if step['action'] in ('editor', 'kdenlive'):
                for arg, current in [('source', source), ('subtitles', subs)]:
                    item = step['kwargs'].get(arg, {})
                    if current is None and isinstance(item, dict) and item.get('local_ref'):
                        if arg == 'source': source = local(item['local_ref'])
                        else: subs = local(item['local_ref'])
        suggestions = run / 'native-suggest.json'
        if not suggestions.is_file(): suggestions = root / 'ai-analysis/edit_suggestions.json'
        return {**handoff, 'data': data, 'run': run, 'identity': identity, 'key': key, 'source': source,
                'subtitles': subs, 'suggestions_path': suggestions}

    def _preview_edl(self, ctx):
        from studio.edl_bridge import AUTHORITY_FILE, EDLBridgeError, read_edl_bridge
        if ctx.get('data', {}).get('line') == 'direct':
            return None
        source = ctx['root'] / AUTHORITY_FILE
        if not source.exists() and not source.is_symlink():
            return None
        try:
            edl = read_edl_bridge(ctx['root'])['content']
        except EDLBridgeError as exc:
            raise ProjectStoreError('video_input_invalid', '剪辑方案无法读取，请检查后重新生成预览') from exc
        identity = ctx['identity']
        revision = edl.get('project_revision')
        if (edl.get('project_id') != identity['photoProjectId']
                or type(revision) is not type(identity['photoProjectRevision'])
                or revision != identity['photoProjectRevision']):
            raise ProjectStoreError('video_binding_invalid', '剪辑方案版本与当前作品不一致，请重新交接')
        return edl

    def _preview_edl_digest(self, ctx):
        from openclaw_product_contract import video_digest
        edl = self._preview_edl(ctx)
        return video_digest(edl) if edl is not None else None

    def candidate_records(self, ctx):
        records = copy.deepcopy(self.app._video_json(ctx['run'], 'studio-candidates.json'))
        entries = records.setdefault('candidates', [])
        previews = records.setdefault('previews', {})
        edls = records.setdefault('preview_edls', {})
        payload = self.app._video_json(ctx['run'], 'studio-candidate.json')
        if not payload and 'run_record' not in ctx:
            payload = self.app._video_json(ctx['root'], ctx.get('binding', {}).get('candidate_ref', 'candidate.json'))
        payload = payload or self.app._video_json(ctx['run'], 'handoff_manifest.json')
        candidate = payload.get('candidate', {})
        cid = candidate.get('publicCandidateId')
        if candidate.get('identity') == ctx['identity'] and cid:
            if not any(c.get('publicCandidateId') == cid for c in entries):
                entries.append(candidate)
            if payload.get('preview_ref'):
                previews.setdefault(cid, payload['preview_ref'])
            if payload.get('preview_edl_digest'):
                edls.setdefault(cid, payload['preview_edl_digest'])
        return records

    def public_candidates(self, project_id, ctx, *, direct=False):
        records = self.candidate_records(ctx)
        rows = []
        edl_digest = self._preview_edl_digest(ctx)
        for candidate in records['candidates']:
            if candidate.get('identity') != ctx['identity']:
                continue
            cid = candidate.get('publicCandidateId')
            ref = records['previews'].get(cid)
            path = (ctx['workspace'] / ref).resolve() if ref else None
            available = records['preview_edls'].get(cid) == edl_digest and path is not None and path.is_relative_to(ctx['workspace']) and path.is_file() and path.stat().st_size <= 20*1024**2
            rows.append({**{k: candidate[k] for k in ('status', 'durationSeconds', 'frameCount', 'cutCount', 'editingMethod', 'provenance') if k in candidate},
                         'editorName': '本机逐帧渲染' if direct else candidate.get('editor', {}).get('displayName'),
                         'previewUrl': f'/api/projects/{project_id}/video-preview/{cid}' if available else None})
        return rows

    def projection(self, project_id, data, *, ctx=None):
        if ctx is None:
            ctx = self.context(project_id)
        if data.get('line') == 'direct':
            data.update(identity=ctx['identity'], projectRevision=self.app.store.get_project(project_id)['revision'],
                        studioUrl=self.origin.rstrip('/')+'/' if self.origin else None,
                        editorName='本机逐帧渲染', candidates=self.public_candidates(project_id, ctx, direct=True))
            return data
        rows = self.editors()
        for row in rows:
            if row['id'] == 'chatcut':
                cc = data['tools']['chatcut']
                row['probe'].update(installed=cc['installed'], version=cc['version'], runnable=cc['handshake'],
                                    status='online' if cc['handshake'] else 'unavailable', login=cc['login'])
        data['editors'] = rows
        method = {'external':'open_source','guide':'jianying_guidance','self':'software_workflow'}[data['choice'].get('method','external')]
        chosen = 'openfilm' if method=='software_workflow' else data['choice']['editor']
        selected = next(r for r in rows if r['id']==chosen)
        data['selectedEditing']={'method':method,'editor':{'toolId':'jianying' if method=='jianying_guidance' else chosen,'displayName':'剪映' if method=='jianying_guidance' else selected['display_name']}}
        names=[r['display_name'] for r in rows if r['id']!=('jianying' if method=='jianying_guidance' else chosen) and r['probe']['runnable']]
        data['availableEditors']={'otherCount':len(names),'displayName':names}
        data['studioUrl']=self.origin.rstrip('/')+'/' if self.origin else None
        data['identity'] = ctx['identity']
        data['projectRevision'] = self.app.store.get_project(project_id)['revision']
        session = self._session(ctx)
        local_check=self.app._video_json(ctx['run'],'studio-check.json')
        if local_check.get('identity')==ctx['identity']:
            data.update(local_check.get('public',{}))
        data.update(copy.deepcopy(session.get('public', {})))
        choice = data['choice']
        if choice.get('method') == 'self' and not data.get('host'):
            data['state'] = 'self'
        elif choice.get('method') == 'guide' and data['state'] not in ('check-failed', 'returned', 'checking'):
            data['state'] = 'guide'
        elif not session.get('public') and data['state'] not in ('returned', 'check-failed'):
            selected = next(r for r in rows if r['id'] == choice['editor'])
            data['state'] = 'connected' if selected['probe']['runnable'] else 'offline' if not any(r['probe']['runnable'] for r in rows) else 'connected-unavailable'
        if choice.get('method','external')=='external' and data['state'].startswith('self'):
            selected=next(r for r in rows if r['id']==choice['editor'])
            data['state']='connected' if selected['probe']['runnable'] else 'connected-unavailable'
        if candidate_failed(data.get('candidate', {})) and not data['state'].startswith('self'):
            data['state'] = 'check-failed'
        data['candidates'] = self.public_candidates(project_id, ctx)
        if ctx['suggestions_path'].is_file() and data.get('sourceDuration'):
            from edit_backends.kdenlive_render import plan_ranges, remap_span
            raw=self.app._video_json(ctx['suggestions_path'].parent,ctx['suggestions_path'].name)
            ranges,_=plan_ranges({**raw,'suggestions':[{'type':s['type'],'start':s['start'],'end':s['end'],'auto_cut_allowed':s['automatic']} for s in data['suggestions']]},data['sourceDuration'])
            for suggestion in data['suggestions']:
                if suggestion['type']=='animation':
                    spans=remap_span(suggestion['start'],suggestion['end'],ranges)
                    suggestion['editedStart']=spans[0][0] if spans else None
        data['subtitleAvailable'] = ctx['subtitles'] is not None
        if ctx['source']:
            data['sourceName'] = ctx['source'].name
            if not session.get('sourceInfo'):
                session['sourceInfo'] = probe_media(ctx['source'])
            info = session['sourceInfo']
            v = next(s for s in info['streams'] if s['codec_type']=='video')
            from fractions import Fraction
            data.update(dimensions=[v['width'],v['height']], sourceFps=float(Fraction(v['avg_frame_rate'])))
        if ctx['subtitles']:
            from review_output_video import read_srt_cues
            data['subtitleCues'] = [{'start':a,'end':b,'text':text} for a,b,text in read_srt_cues(ctx['subtitles'])]
        return data

    def _session(self, ctx):
        if ctx['key'] not in self.sessions:
            self.sessions[ctx['key']] = {'public': {}, 'backend': None, 'undo': [], 'redo': [], 'accepted': set()}
        return self.sessions[ctx['key']]

    def assert_identity(self, ctx, body):
        if json.dumps(body.get('identity'),sort_keys=True)!=json.dumps(ctx['identity'],sort_keys=True) or type(body.get('expectedRevision')) is not int or body['expectedRevision']!=self.app.store.get_project(ctx['identity']['photoProjectId'])['revision']:
            raise ProjectStoreError('revision_conflict', '作品交接已变化，请重新打开作品')

    def command(self, project_id, body):
        op = body.get('op')
        ctx = self.context(project_id, identity=body.get('identity'), delivered_only=op == 'refine')
        self.assert_identity(ctx, body)
        with self.lock:
            session = self._session(ctx)
            if op == 'probe':
                self.editors(refresh=True)
            elif op == 'self-open':
                self.start_self(ctx, session)
            elif op in ('accept', 'retract', 'undo', 'redo', 'split', 'save', 'reload'):
                self.edit(ctx, session, body)
            elif op in ('render', 'export'):
                self.render(ctx, session, body, own=op == 'export')
            elif op == 'refine':
                run = RefineRun(ctx)
                opened = run.read()
                if opened is not None:
                    session['public'].update(state='refine-open', refineUrl=None)
                else:
                    if (ctx['data']['choice'].get('editor') == 'concat' or session.get('backend') is None
                            or not session.get('project_dir')):
                        raise ProjectStoreError('video_refine_missing', '先导出第一版，再打开剪辑软件')
                    result = session['backend'].open_for_refine(project_dir=session['project_dir'])
                    session['public'].update(state='refine-open', refineUrl=result.get('url'))
            elif op == 'close':
                if session.get('backend'): session['backend'].close()
                session.pop('engine',None)
                for key in ('host','filmUrl','audioUrl'): session['public'].pop(key,None)
                session['public']['state'] = 'connected'
            else:
                raise ProjectStoreError('video_action_invalid', '剪辑操作无效')
            return self.projection(project_id, self.app._video_handoff_projection(project_id, context=ctx), ctx=ctx)

    def _overlays(self, ctx):
        teaching = self.app._video_json(ctx['run'], 'native-teaching_clips.json')
        if not teaching: return []
        from video_derivatives import teaching_overlays
        return teaching_overlays(teaching, ctx['descriptor'], ctx['source'])

    def _kwargs(self, ctx):
        if ctx['source'] is None or not ctx['suggestions_path'].is_file():
            raise ProjectStoreError('video_input_missing', '原片或剪辑建议尚未交接，请重新交接作品')
        animations = self._overlays(ctx)
        return {'source': ctx['source'], 'suggestions_path': ctx['suggestions_path'], 'subtitles': ctx['subtitles'],
                'animations': animations, 'project_id': ctx['identity']['photoProjectId'],
                'project_revision': ctx['identity']['photoProjectRevision'], 'timeout_seconds': 300}

    def _host_assets(self, host, project_id):
        static=Path(__file__).with_name('static')
        names=('styles.css','workflow.css','handoff.js','studio-host.js','video-actions.js')
        digest=hashlib.sha256(b''.join((static/name).read_bytes() for name in names)).hexdigest()[:16]
        self._host_asset_path='assets/'+digest
        assets=host/self._host_asset_path
        assets.mkdir(parents=True,exist_ok=True)
        for name in names:
            content=(static/name).read_text()
            if name=='styles.css': content=''.join(line for line in content.splitlines(keepends=True) if not line.lstrip().startswith('@import'))
            (assets/name).write_text(content,encoding='utf-8')
        from edit_backends.openfilm_adapter import Backend
        package=Backend()._package()
        shutil.copy2(package/'studio/server/film-subtitle.mjs',assets/'film-subtitle.js')
        # Public static configuration carries no CSRF or editor capability key.
        (assets/'session.json').write_text(json.dumps({'photoOrigin':self.origin,'projectId':project_id}),encoding='utf-8')
        shell=(static/'index.html').read_text()
        sidebar=shell[shell.index('<aside class="side"'):shell.index('</aside>')+8]
        prefix='/'+self._host_asset_path
        (host/'index.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="'+prefix+'/styles.css"><link rel="stylesheet" href="'+prefix+'/workflow.css"><title>Photo Studio</title></head><body><div class="app">'+sidebar+'<main class="main"><section id="host"></section></main></div><script type="module" src="'+prefix+'/studio-host.js"></script></body></html>')

    def start_self(self, ctx, session):
        for other in self.sessions.values():
            if other is not session and other.get('backend'):
                other['backend'].close()
                other.pop('engine',None)
                for key in ('host','filmUrl','audioUrl'): other['public'].pop(key,None)
        if session.get('backend') and session.get('project_dir') and (session['project_dir']/'host').is_dir():
            backend=session['backend']
            previous_thumbnails=list(session['public'].get('thumbnails',[]))
            backend.close()
            self._host_assets(session['project_dir']/'host',ctx['identity']['photoProjectId'])
            opened=backend.open_for_studio(project_dir=session['project_dir'],host_dir=session['project_dir']/'host')
            session['engine']=opened
            session['public'].update(state='self-applied' if session['accepted'] else 'self',thumbnails=[{'url':opened['origin']+'/'+self._host_asset_path+'/'+Path(t['url']).name} for t in session['public'].get('thumbnails',[])],host=opened['url'],filmUrl=opened['filmUrl'],audioUrl=opened['filmUrl'].rsplit('/',1)[0]+'/assets/source.mp4',engineRevision=opened['rev'],film=opened['doc'])
            from urllib.parse import urlparse
            for thumbnail in previous_thumbnails:
                old=(session['project_dir']/'host'/urlparse(thumbnail['url']).path.lstrip('/')).resolve()
                destination=session['project_dir']/'host'/self._host_asset_path/old.name
                if old.is_file() and old!=destination: shutil.copy2(old,destination)
            session['public']['hostModule']=opened['origin']+'/'+self._host_asset_path+'/handoff.js'
            return
        if session.get('backend'): session['backend'].close()
        backend = get_backend('openfilm')
        work = ctx['run'] / ('studio-' + uuid.uuid4().hex)
        host = work / 'host'
        try:
            args = self._kwargs(ctx)
            # No suggestion is accepted until the person chooses it.
            blank = ctx['run'] / ('suggestions-' + uuid.uuid4().hex + '.json')
            raw = json.loads(ctx['suggestions_path'].read_text())
            blank.write_text(json.dumps({**raw, 'suggestions': []}), encoding='utf-8')
            args['suggestions_path'] = blank
            project_dir = backend.prepare_for_studio(output_dir=work, **args)
            host.mkdir()
            self._host_assets(host,ctx['identity']['photoProjectId'])
            # A genuine first frame prevents upstream's lazy poster warmer from
            # opening a second browser while the person's browser is previewing.
            cache = project_dir / 'openfilm-project/.film/cache'
            cache.mkdir(parents=True)
            subprocess.run(['ffmpeg','-v','error','-i',str(ctx['source']),'-frames:v','1','-vf','scale=288:-1',str(cache/'film-poster.jpg')], check=True, capture_output=True, timeout=30)
            thumbnail_names=[]
            for index,shot in enumerate(ctx['data']['shots'][:12]):
                moment=shot['start']
                if type(moment) not in (int,float) or not 0<=moment<(ctx['data']['sourceDuration'] or 0): continue
                name=f'thumb-{index}.jpg'
                subprocess.run(['ffmpeg','-v','error','-ss',str(moment),'-i',str(ctx['source']),'-frames:v','1','-vf','scale=144:-1',str(host/self._host_asset_path/name)],capture_output=True,check=True,timeout=30)
                thumbnail_names.append(name)
            opened = backend.open_for_studio(project_dir=project_dir, host_dir=host)
            data = self.projection(ctx['identity']['photoProjectId'], ctx['data'])

            full = copy.deepcopy(opened['value'])
            library = {}
            for index, animation in enumerate(args['animations']):
                native_clips = [c for t in full['tracks'] for c in t['clips'] if c['src']==f'assets/overlay-{index}.webm']
                library[animation.get('animation_id')] = native_clips
            source_only = {**full, 'tracks':[{'clips':[c for t in full['tracks'] for c in t['clips'] if c['src']=='assets/source.mp4']}]}
            if library:
                snapshot = backend.studio_edit(base=opened['rev'], ops=_replace_ops(full,source_only))
                opened.update(snapshot)
            session.update(backend=backend, project_dir=project_dir, engine=opened, undo=[], redo=[], accepted=set(), animation_library=library)
            session['public'].update(state='self', host=opened['url'], filmUrl=opened['filmUrl'], audioUrl=opened['filmUrl'].rsplit('/',1)[0]+'/assets/source.mp4',
                                     engineRevision=opened['rev'], film=opened['doc'], accepted=[], availableAnimationIds=list(library), hostModule=opened['origin']+'/'+self._host_asset_path+'/handoff.js', thumbnails=[{'url':opened['origin']+'/'+self._host_asset_path+'/'+name} for name in thumbnail_names])

        except Exception as exc:
            backend.close()
            session['public'].update(state='self-preview-failed', failureCode=type(exc).__name__)
            raise ProjectStoreError('video_preview_failed', '预览没能打开，请重试预览') from exc

    def edit(self, ctx, session, body):
        backend = session.get('backend')
        if backend is None:
            raise ProjectStoreError('video_session_missing', '先打开内置剪辑器')
        state = backend._state(session['project_dir'] / 'openfilm-project')
        if body['op'] != 'reload' and body.get('engineRevision') != state['rev']:
            session['public']['state'] = 'self-conflict'
            raise ProjectStoreError('revision_conflict', '工程已有新修改。先读取新版本，再决定保留哪一份。')
        op = body['op']
        if op=='reload' and state['rev']!=session['public'].get('engineRevision'):
            session['undo'].clear();session['redo'].clear()
            actual=[c['time'] for t in state['doc']['tracks'] for c in t['clips'] if c['src']=='assets/source.mp4']
            session['accepted']={sid for sid in session['accepted'] if not any(s['id']==sid and s['type'] in ('silence','repetition') and any(max(a,s['start'])<min(b,s['end']) for a,b in actual) for s in ctx['data']['suggestions'])}
        accepted = set(session['accepted'])
        target = copy.deepcopy(state['value'])
        if op in ('accept', 'retract'):
            item = next((s for s in ctx['data']['suggestions'] if s['id'] == body.get('suggestionId')), None)
            animation = item is not None and item['type']=='animation'
            if not item or (animation and item['animationId'] not in session.get('animation_library', {})) or (not animation and (not item['automatic'] or item['type'] not in ('silence', 'repetition'))):
                raise ProjectStoreError('video_suggestion_review_only', '这条建议只供复核')
            a, b = round(item['start'] * 30) / 30, round(item['end'] * 30) / 30
            clips = [c for t in target['tracks'] for c in t['clips'] if c['src'] == 'assets/source.mp4']
            ranges = [list(c['time']) for c in clips]
            if op == 'accept' and not animation:
                ranges = [p for x, y in ranges for p in ([x, min(a, y)], [max(b, x), y]) if p[1] > p[0]]
                accepted.add(item['id'])
            elif op == 'retract' and not animation:
                if item['id'] not in accepted:
                    raise ProjectStoreError('video_suggestion_not_applied', '这条建议尚未采纳')
                ranges.append([a, b]); ranges.sort()
                merged = []
                for x, y in ranges:
                    if merged and x <= merged[-1][1]: merged[-1][1] = max(y, merged[-1][1])
                    else: merged.append([x, y])
                ranges = merged
                accepted.remove(item['id'])
                # Restoring A must retain the cut of every other accepted B.
                for other in ctx['data']['suggestions']:
                    if other['id'] in accepted and other['type'] in ('silence','repetition'):
                        left,right=round(other['start']*30)/30,round(other['end']*30)/30
                        ranges=[p for x,y in ranges for p in ([x,min(left,y)],[max(right,x),y]) if p[1]>p[0]]
            else:
                if op=='accept': accepted.add(item['id'])
                elif item['id'] in accepted: accepted.remove(item['id'])
                else: raise ProjectStoreError('video_suggestion_not_applied','这条建议尚未采纳')
            if not ranges:
                raise ProjectStoreError('video_all_source_removed', '不能剪掉全部原片')
            new_rows, at = [], 0
            new_clips = []
            for i, (x, y) in enumerate(sorted(ranges)):
                new_rows.append({'source_start':x,'source_end':y,'output_start':at})
                new_clips.append({**clips[0],'id':f'studio-talk-{i}','time':[x,y],'at':at})
                at += y-x
            from edit_backends.kdenlive_render import remap_span
            tracks = [{'clips':new_clips}]
            overlays = []
            # Generate only the person's accepted overlays, using their original
            # approved asset ranges and the actual retained source intervals.
            for suggestion in ctx['data']['suggestions']:
                if suggestion['id'] not in accepted or suggestion['type']!='animation': continue
                for c in session['animation_library'][suggestion['animationId']]:
                    anchor=c.get('at',0)
                    for i,(start,end,offset) in enumerate(remap_span(anchor,anchor+c['time'][1]-c['time'][0],new_rows)):
                        overlays.append({**c,'id':f"studio-anim-{suggestion['id']}-{i}",'at':start,'time':[c['time'][0]+offset,c['time'][0]+offset+end-start]})
            # openfilm track 0 is the front layer; the talk must stay behind overlays.
            if overlays: tracks.insert(0,{'clips':overlays})
            target['tracks'] = tracks
        elif op in ('undo', 'redo'):
            stack = session[op]
            if not stack: raise ProjectStoreError('video_history_empty', '没有可撤销的修改')
            entry = stack[-1]
            target, accepted = entry['value'], entry['accepted']
        elif op == 'split':
            t = body.get('time')
            if type(t) not in (int, float): raise ProjectStoreError('video_time_invalid', '播放头位置无效')
            t=round(t*30)/30
            c = next((c for track in target['tracks'] for c in track['clips'] if c['src'] == 'assets/source.mp4' and c.get('at', 0) < t < c.get('at', 0) + c['time'][1] - c['time'][0]), None)
            if not c: raise ProjectStoreError('video_time_invalid', '播放头没有可分割的片段')
            cut = c['time'][0] + round((t-c.get('at', 0))*30)/30
            ops = [{'op': 'split', 'clip': c['id'], 'at': t, 'time': [c['time'][0], cut], 'restTime': [cut, c['time'][1]]}]
        if op not in ('save','reload'):
            previous={'value':copy.deepcopy(state['value']),'accepted':set(session['accepted'])}
            try:
                state=backend.studio_edit(base=state['rev'],ops=ops if op=='split' else _replace_ops(state['value'],target))
            except ValueError as exc:
                if 'revision_conflict' in str(exc):
                    session['public']['state']='self-conflict'
                    raise ProjectStoreError('revision_conflict','工程已有新修改。先读取新版本，再决定保留哪一份。') from exc
                raise ProjectStoreError('video_edit_failed','修改没能保存，请读取最新版本后重试') from exc
            if op in ('undo','redo'):
                session[op].pop()
                session['redo' if op=='undo' else 'undo'].append(previous)
            else:
                session['undo'].append(previous)
                session['redo'].clear()
            session['accepted']=accepted
        readback = backend.read_back(project_dir=session['project_dir'])
        session['public'].update(state='self-applied' if accepted else 'self', engineRevision=readback['engine_revision'],
                                 film=state['doc'], accepted=sorted(accepted), undoCount=len(session['undo']), redoCount=len(session['redo']))

    def render(self, ctx, session, body, own=False):
        choice = self.app.video_editor_choice(ctx['identity']['photoProjectId'])
        if not own and choice.get('method','external')!='external':
            raise ProjectStoreError('video_action_invalid','请在当前剪辑方式中导出成片')
        bid = 'openfilm' if own else choice['editor']
        if own and session.get('backend') is None:
            raise ProjectStoreError('video_session_missing', '先打开内置剪辑器')
        preview_edl = self._preview_edl(ctx)
        if not own and session.get('backend'): session['backend'].close()
        backend = session['backend'] if own else get_backend(bid)
        args = self._kwargs(ctx)
        if own:
            state = backend.read_back(project_dir=session['project_dir'])
            if body.get('engineRevision') != state['engine_revision']:
                raise ProjectStoreError('revision_conflict', '工程已有新修改。先读取新版本，再决定保留哪一份。')
            args = state['render_kwargs']
            for key in ('source', 'suggestions_path', 'subtitles'):
                if args.get(key): args[key] = Path(args[key])
        output = ctx['run'] / ('export-' + uuid.uuid4().hex)
        original = {ctx['source']: sha256_file(ctx['source'])}
        session['public']['state'] = 'rendering'
        try:
            # A Studio host starts no browser and owns no Chromium slot. Close it
            # before exporting so the adapter uses its queued one-shot path.
            if own: backend.close()
            native = backend.render(output_dir=output, **args)
            native['editingMethod']='software_workflow' if own else 'open_source'
            (ctx['run'] / 'native-editor.json').write_text(json.dumps(native, default=str), encoding='utf-8')
            if native.get('status') != 'candidate':
                raise ValueError('selected_editor_export_failed')
            session.update(backend=backend, project_dir=output if not own else session['project_dir'])
            if bid == 'chatcut':
                session['public'].update(state='refine', editorName='ChatCut')
                return
            from video_candidate import project_candidate
            descriptor=copy.deepcopy(ctx['descriptor'])
            if own:
                plan=json.loads(Path(native['manifest']).read_text())
                actual={a['animation_id'] for a in plan.get('animation_placements',[])}
                descriptor['animations']=[a for a in descriptor['animations'] if a['animationId'] in actual]
            payload = project_candidate(native=native, descriptor=descriptor, source=ctx['source'],
                                        original_hashes=original, output_dir=output / 'studio-check', workspace=ctx['workspace'],
                                        **({'edl': preview_edl, 'project': ctx['root']} if preview_edl is not None else {}))
            self._record_candidate(ctx, session, payload, editing_method='software_workflow' if own else 'open_source', editor_id=bid, verified=True)
            if not own and not candidate_failed(payload['candidate']): session['public']['state'] = 'refine'
        except Exception as exc:
            session['public'].update(state='self-export-failed' if own else 'failed', failureCode=type(exc).__name__)
            (ctx['run'] / 'studio-failure.json').write_text(json.dumps({'identity':ctx['identity'], 'editor_backend':bid, 'status':'failed', 'reason':str(exc)}))
            history=self.app._video_json(ctx['run'],'studio-candidates.json')
            method='software_workflow' if own else 'open_source'
            rows=[c for c in history.get('candidates',[]) if c.get('identity')==ctx['identity'] and (c.get('editingMethod'),c.get('editor',{}).get('toolId'))!=(method,bid)]
            rows.append({'identity':ctx['identity'],'status':'failed','editingMethod':method,'editor':{'toolId':bid,'displayName':next(r['display_name'] for r in self.editors() if r['id']==bid)}})
            (ctx['run']/'studio-candidates.json').write_text(json.dumps({**history,'candidates':rows[-12:]},default=str),encoding='utf-8')
        finally:
            if own:
                exported_state=session['public']['state']
                self.start_self(ctx,session)
                session['public']['state']=exported_state
            elif session.get('backend') is not backend: backend.close()

    def _record_candidate(self, ctx, session, payload, *, editing_method, editor_id, verified=False, refine=None, video=None):
        candidate = payload['candidate']
        for cut in candidate.get('cuts',[]):
            if cut['kind'] in ('silence','retake'): continue
            facts=[s for s in ctx['data']['suggestions'] if s['automatic'] and s['type'] in ('silence','repetition') and s['start']<=cut['startSeconds']+1e-6 and s['end']>=cut['endSeconds']-1e-6]
            if not facts:
                if cut['kind']=='manual': continue
                raise ValueError('native_cut_reason_unverified')
            cut['kind']='retake' if any(s['type']=='repetition' for s in facts) else 'silence'
        (ctx['run']/'studio-check.json').unlink(missing_ok=True)
        name='剪映' if editor_id=='jianying' else next(r['display_name'] for r in self.editors() if r['id']==editor_id)
        from datetime import datetime, timedelta, timezone
        from openclaw_product_contract import video_digest
        now=datetime.now(timezone.utc)
        candidate['editingMethod']=editing_method
        candidate['editor']={'toolId':editor_id,'displayName':name,'status':'online' if verified else 'unknown','reasonCode':'export_completed' if verified else 'returned_export','checkedAt':now.isoformat(),'expiresAt':(now+timedelta(minutes=5)).isoformat(),'installed':verified,'version':None,'evidenceKind':'command_probe' if verified else 'none'}
        candidate.pop('candidateDigest',None)
        candidate['candidateDigest']=video_digest(candidate)
        payload['progress'].update(selectedEditing={'method':candidate['editingMethod'],'editor':{'toolId':candidate['editor']['toolId'],'displayName':name}})
        if refine is not None and not candidate_failed(candidate):
            def check_current():
                current = delivered_context(self.app.store, ctx['identity']['photoProjectId'], ctx['identity'])
                if current['run_record'] != ctx['run_record']:
                    raise SelectionError('video_identity_stale')
            payload = refine.pin_candidate(payload, video, check_current)
            candidate = payload['candidate']
        history=self.app._video_json(ctx['run'],'studio-candidates.json')
        entries=[c for c in history.get('candidates',[]) if c.get('identity')==ctx['identity'] and (c.get('editingMethod'),c.get('editor',{}).get('toolId'))!=(editing_method,editor_id)]
        entries.append(copy.deepcopy(candidate))
        previews=history.get('previews',{})
        if payload.get('preview_ref'): previews[candidate['publicCandidateId']]=payload['preview_ref']
        edls=history.get('preview_edls',{})
        if payload.get('preview_edl_digest'): edls[candidate['publicCandidateId']]=payload['preview_edl_digest']
        (ctx['run']/'studio-candidates.json').write_text(json.dumps({'candidates':entries[-12:],'previews':previews,'preview_edls':edls},default=str),encoding='utf-8')
        (ctx['run']/'studio-candidate.json').write_text(json.dumps(payload,default=str),encoding='utf-8')
        session['public'].update(editorName=name,
                                 candidate={k:v for k,v in candidate.items() if k in ('status','durationSeconds','frameCount','cutCount','removedSeconds','returnedAt','checks','provenance')},
                                 state='check-failed' if candidate_failed(candidate) else 'returned', uploaded=False)

    def receive(self, project_id, stream, length, body):
        if not 0 < length <= 4*1024**3:
            raise ProjectStoreError('body_too_large', '成片大小无效')
        ctx = self.context(project_id, identity=body.get('identity'), delivered_only=True)
        self.assert_identity(ctx, body)
        choice=copy.deepcopy(self.app.video_editor_choice(project_id))
        refine = RefineRun(ctx)
        opened = refine.read()
        if opened is not None:
            choice.update(editor='concat', method='external')
        elif choice.get('editor') == 'concat' and choice.get('method') == 'external':
            raise ProjectStoreError('video_refine_missing', '先导出第一版，再打开剪辑软件')
        original = {ctx['source']: sha256_file(ctx['source'])} if ctx['source'] else {}
        if not original: raise ProjectStoreError('video_input_missing', '原片尚未交接')
        output = ctx['run'] / ('returned-' + uuid.uuid4().hex)
        output.mkdir()
        video = output / 'returned.mp4'
        received = False
        try:
            with video.open('wb') as target:
                left = length
                while left:
                    chunk = stream.read(min(left, 1024*1024))
                    if not chunk: raise ProjectStoreError('body_invalid', '成片上传未完成')
                    target.write(chunk); left -= len(chunk)
            received = True
            from review_output_video import check_output_video
            inspected=check_output_video(video,original_hashes=original)
            if inspected['status']!='passed':
                return self._return_failed(ctx, inspected)
            if opened is not None and opened['opened']['source_sha256'] != 'sha256:' + original[ctx['source']]:
                return self._return_failed(ctx, inspected, '原片已变化，请重新交接作品。')
            session=self._session(ctx)
            bid='jianying' if choice.get('method')=='guide' else 'openfilm' if choice.get('method')=='self' else choice['editor']
            from studio.returned_candidate import openfilm_plan, openchatcut_plan, concat_plan, project_returned
            backend=session.get('backend')
            directory=session.get('project_dir')
            if opened is not None:
                directory = refine.project_directory(opened)
                backend = get_backend('concat')
            plan=None
            can_read=bid!='jianying' and next(r for r in self.editors() if r['id']==bid)['capabilities']['read_back']
            project_name={'otio_kdenlive':'timeline.kdenlive','openfilm':'openfilm-project/adapter-project.json','openchatcut':'openchatcut-project.json','concat':'concat-project/concat.json'}.get(bid)
            if can_read and directory and project_name and (directory/project_name).is_file():
                if not backend or backend.describe()['id']!=bid:
                    raise ProjectStoreError('video_session_missing','所选软件工程不属于当前会话，请重新打开精修')
                try:
                    plan=openfilm_plan(backend,directory,output,ctx['data']['suggestions']) if bid=='openfilm' else openchatcut_plan(backend,directory,output,ctx['data']['suggestions']) if bid=='openchatcut' else concat_plan(backend,directory,output,ctx['data']['suggestions'],self._overlays(ctx)) if bid=='concat' else backend.read_back(project_dir=directory)
                    if bid in ('otio_kdenlive','openchatcut','concat') and (plan['project_id'],plan['project_revision'])!=(ctx['identity']['photoProjectId'],ctx['identity']['photoProjectRevision']):
                        raise ValueError('kdenlive_project_identity_mismatch')
                    if not 0<=plan['subtitle_bottom_ratio']<=1:
                        raise ValueError('native_subtitle_position_unverified')
                    inspected=check_output_video(video,original_hashes=original,subtitles=Path(plan['subtitles']),expected_duration=plan['duration'],expected_frames=plan['frames'],expected_fps=plan['fps'])
                except (OSError,ValueError,KeyError) as exc:
                    notice='请先关闭 Concat 里的这个工程再回传。' if str(exc)=='concat_project_in_use' else '保存的工程没有提供完整、可核对的剪辑记录；请检查工程后重新导出。'
                    return self._return_failed(ctx, inspected, notice)
                finally:
                    if opened is not None:
                        backend.close()
            if opened is not None and (plan is None or inspected['status'] != 'passed'):
                return self._return_failed(ctx, inspected)
            checks=review_projection(inspected)
            if plan: checks['expectedFrames']=plan['frames']
            payload=project_returned(ctx,video,output,inspected,checks,plan,exact_480=opened is not None)
            method={'external':'open_source','guide':'jianying_guidance','self':'software_workflow'}[choice.get('method','external')]
            try:
                with self.lock:
                    self._record_candidate(ctx,session,payload,editing_method=method,editor_id=bid,
                                           refine=refine if opened is not None else None, video=video)
            except SelectionError as exc:
                if exc.code == 'video_refine_candidate_changed':
                    return self._return_failed(ctx, inspected, '这个任务已有一份已检查的成片。')
                raise ProjectStoreError('revision_conflict', '作品交接已变化，请重新打开作品') from exc
            return self.projection(project_id,ctx['data'],ctx=ctx)
        except Exception:
            if not received:
                shutil.rmtree(output, ignore_errors=True)
            raise

    def _return_failed(self, ctx, inspected, notice=None):
        candidate = {'status': 'check_failed', 'checks': review_projection(inspected)}
        if notice:
            candidate['reviewNotice'] = notice
        public = {'state': 'check-failed', 'candidate': candidate, 'uploaded': False}
        self._session(ctx)['public'].update(public)
        (ctx['run']/'studio-check.json').write_text(json.dumps({'identity':ctx['identity'],'public':public}),encoding='utf-8')
        return self.projection(ctx['identity']['photoProjectId'], ctx['data'], ctx=ctx)

    def subtitles(self, project_id):
        ctx=self.context(project_id)
        if not ctx['subtitles']:
            raise ProjectStoreError('video_subtitles_missing','字幕尚未生成')
        if ctx['data']['choice'].get('method')!='guide': return ctx['subtitles'].read_bytes()
        from edit_backends.kdenlive_render import plan_ranges, remap_subtitles
        raw=self.app._video_json(ctx['suggestions_path'].parent,ctx['suggestions_path'].name)
        duration=ctx['data']['sourceDuration']
        ranges,_=plan_ranges({**raw,'suggestions':[{'type':s['type'],'start':s['start'],'end':s['end'],'auto_cut_allowed':s['automatic']} for s in ctx['data']['suggestions']]},duration)
        target=ctx['run']/'guide-subtitles.srt'
        remap_subtitles(ctx['subtitles'],target,ranges,duration)
        return target.read_bytes()

    def preview(self, project_id, candidate_id):
        ctx=self.context(project_id)
        records=self.candidate_records(ctx)
        if not any(c.get('publicCandidateId')==candidate_id and c.get('identity')==ctx['identity'] for c in records.get('candidates',[])):
            raise ProjectStoreError('video_preview_missing','候选预览不可用')
        if records['preview_edls'].get(candidate_id) != self._preview_edl_digest(ctx):
            raise ProjectStoreError('video_preview_missing','剪辑方案已变化，请重新生成预览')
        ref=records.get('previews',{}).get(candidate_id,'')
        path=(ctx['workspace']/ref).resolve()
        if not ref or not path.is_relative_to(ctx['workspace']) or not path.is_file() or path.stat().st_size>20*1024**2:
            raise ProjectStoreError('video_preview_missing','候选预览不可用')
        if 'run_record' in ctx:
            run = RefineRun(ctx)
            try:
                state = run.read()
                if state and state.get('candidate', {}).get('preview_ref') == ref:
                    run.candidate_receipt(state)
            except SelectionError as exc:
                raise ProjectStoreError('video_preview_missing', '候选预览不可用') from exc
        return path

    def allowed_origin(self, origin):
        return bool(origin and any(s.get('engine', {}).get('origin') == origin for s in self.sessions.values()))

    def close(self):
        for session in self.sessions.values():
            if session.get('backend'): session['backend'].close()
            session.pop('engine',None)
