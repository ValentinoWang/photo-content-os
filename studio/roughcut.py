"""R226 application service: snapshots, pure plans, CAS, jobs and safe projections."""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import math
import re
import secrets
import threading
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator

from scripts.roughcut_planner import plan_roughcut, PlannerError
from scripts.roughcut_capabilities import capabilities_for_choice
from scripts.runtime_paths import local_media_root
from studio.media_review import digest as review_digest
from studio.project_store import ProjectStoreError
from studio.roughcut_jobs import RoughcutJobs
from studio.roughcut_store import (ROOT, RoughcutStore, RoughcutError, JsonReader, safe_path,
                                   digest, validate)
from studio.roughcut_transcription import LocalTranscriber

TECHNIQUES = ('jcut','bed','duck','pause','action')
BEAT_WAIT_TIMEOUT_SEC = 30 * 60
BEAT_POLL_MAX_SEC = 30
CHOICE_LOCK = threading.RLock()
AUDIO_TRANSCRIPT = Draft202012Validator(json.loads((ROOT/'schemas/audio-transcript.schema.json').read_text()))


@dataclass(frozen=True)
class MediaSlice:
    path: Path
    status: int
    content_type: str
    start: int
    length: int
    headers: dict


class RoughcutService:
    def __init__(self, app, *, beat_loader=None, transcriber=None, planner=None,
                 start_jobs=True, poll_interval=.5):
        self.app = app
        self.reader = JsonReader()
        self.store = RoughcutStore(app.store.state_dir, self.reader)
        self.io_stats = self.reader.stats
        self.beat_loader = beat_loader
        self.transcriber = transcriber or LocalTranscriber()
        self.planner = planner or plan_roughcut
        self.poll_interval = poll_interval
        self.jobs = RoughcutJobs(self._run_job, autostart=start_jobs)
        self.roots = {}
        self.asr_lock = threading.Lock()
        self.preview_renderer = None
        self.draft_generator = None
        self.music_resolver = None
        self.editor_opener = None
        self.editor_backend = None

    def close(self):
        self.jobs.close()
        if self.editor_backend is not None:
            self.editor_backend.close()

    def _project(self, identity):
        if not isinstance(identity, str) or not identity or '/' in identity or '\\' in identity or identity in ('.','..'):
            raise RoughcutError('project_not_found')
        try:
            return self.app.store.get_project(identity)
        except ProjectStoreError as exc:
            raise RoughcutError('project_not_found' if exc.code=='project_not_found' else 'roughcut_state_unreadable') from exc

    def _root(self, identity, project):
        marker = project.get('local_workspace', {}).get('path_digest')
        cached = self.roots.get(identity)
        try:
            path = cached[1] if cached and cached[0] == marker else self.app.store.local_workspace_path(identity)
            media = local_media_root()
            if not path.is_dir() or not path.resolve().is_relative_to(media):
                raise RoughcutError('shots_invalid')
            self.roots[identity] = (marker, path)
            return path
        except (ProjectStoreError, OSError, ValueError) as exc:
            if isinstance(exc, RoughcutError):
                raise
            raise RoughcutError('shots_invalid') from exc

    def _context(self, identity, *, transcripts=False):
        project = self._project(identity)
        root = self._root(identity, project)
        folder = root / 'ai-analysis/shots'
        document = self.reader.read(folder/'shots.json', root, 'shots_invalid', optional=True)
        manifest = self.reader.read(root/'ai-analysis/media-manifest.json', root, 'shots_invalid', optional=True)
        decisions = self.reader.read(folder/'decisions.json', root, 'shots_invalid', optional=True)
        document = document if document is not None else dict(shots=[],run_status='not_started',hook_candidates=[])
        manifest = manifest if manifest is not None else dict(items=[])
        decisions = decisions if decisions is not None else dict(version=0,shots={},confirmation=None)
        try:
            if not isinstance(document,dict) or not isinstance(document.get('shots'),list) or not isinstance(manifest,dict) or not isinstance(manifest.get('items'),list):
                raise RoughcutError('shots_invalid')
            if not isinstance(decisions,dict) or type(decisions.get('version')) is not int or not isinstance(decisions.get('shots'),dict):
                raise RoughcutError('shots_invalid')
            if any(not isinstance(v,dict) or v.get('status') not in ('selected','usable','unused') or not isinstance(v.get('decided_at'),str) for v in decisions['shots'].values()):
                raise RoughcutError('shots_invalid')
            items = {x.get('relative_path',x.get('path')): x for x in manifest['items'] if isinstance(x,dict)}
            if len(items)!=len(manifest['items']):
                raise RoughcutError('shots_invalid')
            rows, earliest = [], {}
            for raw in document['shots']:
                row = copy.deepcopy(raw)
                if not isinstance(row,dict) or not isinstance(row.get('id'),str) or row.get('kind') not in ('video','photo') or not isinstance(row.get('scene'),str):
                    raise RoughcutError('shots_invalid')
                relative = row['source_relative_path']
                if not isinstance(relative,str):
                    raise RoughcutError('shots_invalid')
                source = safe_path(root/relative, root, 'shots_invalid', absent=True)
                item = items.get(relative, {})
                timestamp = item.get('created_at')
                captured = datetime.fromisoformat(timestamp.replace('Z','+00:00')).timestamp() if timestamp else source.stat().st_mtime if source.exists() else 0
                row['_captured'] = captured
                earliest[row['scene']] = min(earliest.get(row['scene'],captured),captured)
                if row.get('status') != 'rejected':
                    override = decisions['shots'].get(row['id'],{}).get('status')
                    if override:
                        row['status'] = override
                rows.append(row)
            if len({r['id'] for r in rows}) != len(rows):
                raise RoughcutError('shots_invalid')
            rows.sort(key=lambda r:(earliest[r['scene']],r['scene'],Path(r['source_relative_path']).name,r.get('start_sec') or 0))
            selected = [r for r in rows if r.get('status')=='selected']
            conf = decisions.get('confirmation')
            if conf is not None and (not isinstance(conf,dict) or any(not isinstance(conf.get(k),str) for k in ('confirmed_at','selection_digest','evidence_digest'))):
                raise RoughcutError('shots_invalid')
            confirmed = bool(selected and conf and conf['selection_digest']==review_digest([r['id'] for r in selected]) and conf['evidence_digest']==review_digest(document) and document.get('run_status')=='complete')
            shots, by_media, sources, paths, transcripts_by_media, source_facts = [], {}, {}, {}, {}, []
            seen_transcript_media=set()
            for row in selected:
                relative = row['source_relative_path']
                item = items.get(relative)
                if not item:
                    raise RoughcutError('shots_invalid')
                mid = row.get('media_id') or item.get('media_id') or item.get('id')
                if not isinstance(mid,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',mid):
                    raise RoughcutError('shots_invalid')
                source = safe_path(root/relative, root, 'shots_invalid')
                stat = source.stat()
                source_facts.append(dict(id=row['id'],media_id=mid,source=relative,size=stat.st_size,mtime_ns=stat.st_mtime_ns,sha256=item.get('sha256')))
                if mid in sources and sources[mid] != source:
                    raise RoughcutError('shots_invalid')
                by_media[mid],sources[mid] = item,source
                transcript_ref = item.get('transcript_path') or f'ai-analysis/transcripts/{mid}.transcript.json'
                paths[mid] = safe_path(root/transcript_ref, root/'ai-analysis/transcripts', 'transcript_unreadable', absent=True)
                shot = {k:row[k] for k in ('id','kind','scene','start_sec','end_sec','metrics','has_audio','speaking') if k in row}
                shot['media_id'] = mid
                if 'has_audio' not in shot and type(item.get('has_audio')) is bool:
                    shot['has_audio'] = item['has_audio']
                shots.append(shot)
                if transcripts and row['kind']=='video' and row['scene']=='selfie-moments' and mid not in seen_transcript_media:
                    seen_transcript_media.add(mid)
                    transcript = self.reader.read(paths[mid],root,'transcript_unreadable',optional=True)
                    if transcript is not None:
                        if not AUDIO_TRANSCRIPT.is_valid(transcript) or transcript.get('media_id') != mid:
                            raise RoughcutError('transcript_unreadable')
                        previous_end=0
                        for segment in transcript['segments']:
                            if segment['start_sec']<previous_end or segment['end_sec']<segment['start_sec']:
                                raise RoughcutError('transcript_invalid')
                            previous_end=segment['end_sec']
                            last_word=segment['start_sec']
                            for word in segment['words']:
                                if not last_word<=word['start']<=word['end']<=segment['end_sec']:
                                    raise RoughcutError('transcript_invalid')
                                last_word=word['end']
                        if transcript['status']=='ok' and transcript['precision']=='word' and transcript['auto_cut_allowed'] and not self._word_ready(transcript):
                            raise RoughcutError('transcript_invalid')
                        transcripts_by_media[mid] = transcript
            selection_digest = digest([dict(id=s['id'],media_id=s['media_id'],kind=s['kind'],start=s.get('start_sec'),end=s.get('end_sec')) for s in shots])
            shots_digest = digest(dict(shots=shots,sources=source_facts))
            summary = dict(selected_shot_count=len(shots),selected_video_count=sum(s['kind']=='video' for s in shots),selected_photo_count=sum(s['kind']=='photo' for s in shots),inventory_video_count=sum(x.get('media_type',x.get('type'))=='video' for x in manifest['items']),inventory_photo_count=sum(x.get('media_type',x.get('type')) in ('image','photo') for x in manifest['items']),selection_confirmed=confirmed,selection_digest=selection_digest)
            return dict(root=root,project=project,shots=shots,rows=selected,summary=summary,shots_digest=shots_digest,
                        transcripts=transcripts_by_media,transcripts_digest=digest(transcripts_by_media),
                        items_by_media=by_media,sources_by_media=sources,transcript_paths=paths,
                        confirmation_digest=digest(conf))
        except (KeyError,TypeError,ValueError,OSError,OverflowError) as exc:
            if isinstance(exc,RoughcutError):
                raise
            raise RoughcutError('shots_invalid') from exc

    def _config(self):
        config = self.reader.read(ROOT/'scripts/editing_presets.json',ROOT,'builtin_presets_invalid')
        try:
            if not isinstance(config,dict) or config.get('schema_version')!='editing_presets_v1' or not isinstance(config['settings'],dict) or len(config['presets'])!=6:
                raise RoughcutError('builtin_presets_invalid')
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in config['settings'].values()):
                raise RoughcutError('settings_invalid')
            presets=[]
            for item in config['presets']:
                preset=dict(id=item['id'],revision=1,origin='builtin',base_preset_id=None,name=item['name'],category=item['category'],description=item['description'],recipe={k:item[k] for k in ('beats_per_cut','techniques','order')},overrides={},created_at=None)
                validate('preset',preset,presets=True,code='builtin_presets_invalid')
                presets.append(preset)
            if len({p['id'] for p in presets})!=6:
                raise RoughcutError('builtin_presets_invalid')
            return config['settings'],presets
        except (KeyError,TypeError,ValueError) as exc:
            if isinstance(exc,RoughcutError):
                raise
            raise RoughcutError('builtin_presets_invalid') from exc

    def presets(self):
        _,builtins=self._config()
        warning=None
        try:
            mine=self.store.mine()
            status='absent' if mine is None else 'readable'
            revision=1 if mine is None else mine['revision']
            custom=[] if mine is None else sorted(mine['presets'],key=lambda p:p['created_at'],reverse=True)
            if {p['id'] for p in custom} & {p['id'] for p in builtins}:
                raise RoughcutError('preset_store_unreadable')
        except RoughcutError as exc:
            if exc.code!='preset_store_unreadable':
                raise
            custom,status,revision=[], 'unreadable',None
            warning=dict(code='preset_store_unreadable',design_state='cut-presets-unreadable')
        presets=custom+builtins
        categories=[dict(id='all',label='全部',count=len(presets))]
        for id,label in [('travel','旅行'),('sports','运动'),('daily','日常'),('mine','我的')]:
            categories.append(dict(id=id,label=label,count=None if id=='mine' and status=='unreadable' else sum(p['category']==label for p in presets)))
        return dict(ok=True,schema_version='editing_presets_api_v1',revision=revision,mine_status=status,can_save=status!='unreadable',presets=presets,categories=categories,total=len(presets),warning=warning)

    def _preset(self, selection, library=None):
        library=library or self.presets()
        preset=next((p for p in library['presets'] if p['id']==selection['preset_id']),None)
        if preset is None:
            raise RoughcutError('preset_store_unreadable' if library['mine_status']=='unreadable' else 'preset_not_found')
        if preset['revision']!=selection['preset_revision']:
            raise RoughcutError('roughcut_inputs_stale')
        return preset

    def _availability(self):
        checks=self.app.doctor_checks
        if not isinstance(checks,list) or any(not isinstance(c,dict) or not isinstance(c.get('id'),str) or not isinstance(c.get('status'),str) for c in checks):
            raise RoughcutError('editor_diagnostics_unreadable')
        by_id={c['id']:c['status'] for c in checks}
        result={}
        for name,key in [('otio_kdenlive','kdenlive'),('openchatcut','edit_tool_openchatcut'),('guide','jianying')]:
            status=by_id.get(key)
            installed=True if status=='ready' else False if status in ('missing','not_installed','not_found') else None
            result[name]=dict(status='ready' if installed is True else 'absent' if installed is False else 'unknown',installed=installed,connected=None,checked_at=self.app.doctor_checked_at)
        chat=self.app.chatcut_mcp.state
        if not isinstance(chat,dict) or type(chat.get('available')) is not bool:
            raise RoughcutError('editor_diagnostics_unreadable')
        result['chatcut']=dict(status='ready' if chat['available'] else 'disconnected',installed=True if chat.get('visible') else None,connected=chat['available'],checked_at=self.app.doctor_checked_at)
        return result

    def capabilities(self, identity, *, project=None):
        project=project or self._project(identity)
        failure=None
        try:
            saved=self.app._video_editor_choice(identity)
            choice={k:saved[k] for k in ('editor','method','revision')}
        except (ProjectStoreError,KeyError,OSError,ValueError):
            failure=RoughcutError('editor_choice_unreadable').failure
            choice={'error':dict(code='editor_choice_unreadable',message='无法读取本机记录')}
        available=self._availability()
        options=[]
        for id,editor,method in [('kdenlive','otio_kdenlive','external'),('chatcut','chatcut','external'),('openchatcut','openchatcut','external'),('guide',choice.get('editor','otio_kdenlive'),'guide')]:
            availability=available['guide' if method=='guide' else editor]
            ready=True if availability['status']=='ready' else False if availability['status'] in ('absent','disconnected') else None
            option_choice=dict(editor=editor,method=method)
            options.append(dict(id=id,choice=option_choice,availability=availability,capability=capabilities_for_choice(option_choice,ready=ready)))
        selected,selected_id=None,None
        if 'error' not in choice:
            availability=available.get('guide' if choice['method']=='guide' else choice['editor'])
            ready=None if availability is None else True if availability['status']=='ready' else False if availability['status'] in ('absent','disconnected') else None
            selected=capabilities_for_choice(choice,ready=ready)
            if choice['method']!='self':
                selected_id='guide' if choice['method']=='guide' else next((o['id'] for o in options if o['choice']['editor']==choice['editor'] and o['choice']['method']=='external'),None)
        return dict(ok=True,project_revision=project['revision'],capability_version='roughcut_capabilities_v1',choice=choice,editors=options,selected=selected,selected_option_id=selected_id,failure=failure)

    @staticmethod
    def _recipe_digest(preset, selection):
        return digest(dict(preset=preset,technique_overrides=selection['technique_overrides'],
                           occurrence_overrides=selection['occurrence_overrides'],swap_positions=selection['swap_positions']))

    def _binding(self, context, selection, preset, settings, analysis):
        by_id={a['song_instance_id']:a for a in analysis}
        music=[]
        for song in selection['playlist']:
            beat=by_id.get(song['id'],{}).get('beat_map')
            music.append(dict(song_instance_id=song['id'],track_id=song['track_id'],registry_version=None if beat is None else beat['registry_version'],beat_map_digest=None if beat is None else digest(beat)))
        return dict(project_revision=context['project']['revision'],selection_digest=context['summary']['selection_digest'],shots_digest=context['shots_digest'],transcripts_digest=context['transcripts_digest'],preset_digest=self._recipe_digest(preset,selection),settings_digest=digest(settings),music=music,editor_choice_revision=None,edl_digest=None)

    def _empty(self, identity, context):
        settings,builtins=self._config()
        selection=dict(playlist=[],preset_id='trip',preset_revision=1,technique_overrides={},occurrence_overrides={},swap_positions={})
        return dict(schema_version='roughcut_store_v1',piece_id=identity,revision=1,status='no_music',selection=selection,input_binding=self._binding(context,selection,next(p for p in builtins if p['id']=='trip'),settings,[]),published=None,job_id=None,analysis=[],failure=None,preset_previews=[],stop_revisions={})

    def _current(self, identity, context):
        return self.store.read_state(identity) or self._empty(identity,context)

    def _analysis(self, playlist):
        loader=self.beat_loader
        if loader is None:
            try:
                loader=importlib.import_module('studio.music_analysis').load_beat_map
            except (ImportError,AttributeError) as exc:
                raise RoughcutError('beat_analysis_unavailable',dict(dependency='r223_beat_reader')) from exc
        if not callable(loader):
            raise RoughcutError('beat_analysis_unavailable',dict(dependency='r223_beat_reader'))
        result=[]
        for song in playlist:
            try:
                beat=loader(song['track_id'],media_root=local_media_root())
                try:
                    json.dumps(beat, allow_nan=False)
                except (ValueError, TypeError) as exc:
                    raise RoughcutError('beat_map_invalid') from exc
                validate('beat_map',beat,code='beat_map_invalid')
                if beat['track_id']!=song['track_id']:
                    raise RoughcutError('beat_map_invalid')
                result.append(dict(song_instance_id=song['id'],track_id=song['track_id'],status='done',beat_count=len(beat['beats']),beat_map=beat,failure=None))
            except Exception as exc:
                if isinstance(exc,RoughcutError):
                    raise
                code=getattr(exc,'code',None)
                if code in ('queued','analyzing'):
                    result.append(dict(song_instance_id=song['id'],track_id=song['track_id'],status=code,beat_count=None,beat_map=None,failure=None))
                    continue
                if code not in ('unknown_track','beat_failed','result_unreadable'):
                    raise RoughcutError('result_unreadable',dict(track_id=song['track_id'])) from exc
                details=dict(track_id=song['track_id'])
                failure_code=getattr(exc,'failure_code',None)
                if failure_code is not None:
                    details['upstream_failure_code']=failure_code if isinstance(failure_code,str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}',failure_code) else 'unknown'
                raise RoughcutError(code,details) from exc
        return result

    @staticmethod
    def _source_matches(binding, context):
        return (binding['project_revision']==context['project']['revision'] and
                binding['selection_digest']==context['summary']['selection_digest'] and
                binding['shots_digest']==context['shots_digest'] and
                binding['transcripts_digest']==context['transcripts_digest'] and
                context['summary']['selection_confirmed'])

    @staticmethod
    def _custom_empty():
        return dict(changed=False,disabled=[],enabled=[],skipped_occurrence_ids=[])

    def state(self, identity):
        with self.store.locked('piece',identity):
            saved=self.store.read_state(identity)
            context=self._context(identity,transcripts=bool(saved and saved['selection']['playlist']))
            record=saved or self._empty(identity,context)
            library=self.presets()
            caps=self.capabilities(identity,project=context['project'])
            published=record['published']
            plan=None if published is None else published['plan']
            failure=record['failure']
            status=record['status']
            stale=False
            if record['selection']['playlist'] and not self._source_matches(record['input_binding'],context):
                stale=True
                failure=RoughcutError('roughcut_inputs_stale').failure
                status='failed'
            if record['selection']['playlist']:
                settings,_=self._config()
                try:
                    selected_preset=self._preset(record['selection'],library)
                    configuration_changed=(digest(settings)!=record['input_binding']['settings_digest'] or
                                           self._recipe_digest(selected_preset,record['selection'])!=record['input_binding']['preset_digest'])
                except RoughcutError as exc:
                    failure=exc.failure
                    configuration_changed=True
                if configuration_changed:
                    stale=True
                    failure=failure or RoughcutError('roughcut_inputs_stale').failure
                    status='failed'
            if published and published['binding']==record['input_binding'] and not stale:
                try:self._require_plan_current(record,context)
                except RoughcutError as exc:
                    stale=True;status='failed';failure=exc.failure
            if plan is None and not context['summary']['selection_confirmed']:
                status='prerequisite'
            warnings=None if plan is None else plan['warnings']
            customization=self._custom_empty() if plan is None else plan['customization']
            speech=dict(eligible_video_count=sum(s['kind']=='video' and s['scene']=='selfie-moments' and s.get('speaking') is not False for s in context['shots']),missing_video_count=0,affected_techniques=[],mode='none',by_technique={t:dict(enabled=False,count=0,shot_ids=[],media_ids=[]) for t in ('pause','duck')})
            if warnings:
                speech.update(missing_video_count=warnings['missing_word_count'],by_technique=warnings['missing_word_by_technique'])
                speech['affected_techniques']=[t for t in ('pause','duck') if speech['by_technique'][t]['enabled'] and speech['by_technique'][t]['count']]
                if speech['missing_video_count']:
                    speech['mode']='all' if speech['missing_video_count']==speech['eligible_video_count'] else 'partial'
            notices=[]
            blockers=[]
            if plan is None:blockers.append('no_plan')
            if record['status'] in ('queued','arranging','stopping'):blockers.append('busy')
            if stale or failure or (published is not None and published['binding']!=record['input_binding']):blockers.append('stale')
            selected=caps['selected']
            if selected is None:
                blockers.append('editor_choice_unreadable')
                notices.append(dict(code='editor_choice_unreadable',design_state='cut-editor-unreadable',count=None,techniques=[],failure=caps['failure']))
            elif not selected['can_generate']:
                reason=selected['block_reason']
                blockers.append(reason)
                choice=caps['choice']
                state='cut-editor-openfilm' if choice['method']=='self' else 'cut-editor-unsupported'
                code='draft_backend_unsupported'
                if reason in ('editor_not_ready','editor_readiness_unknown'):
                    code='editor_not_ready'
                    state='cut-editor-chatcut' if choice['editor']=='chatcut' else 'cut-editor-kdenlive-missing' if choice['editor']=='otio_kdenlive' and reason=='editor_not_ready' else 'cut-editor'
                notices.append(dict(code=code,design_state=state,count=None if plan is None else plan['metrics']['shot_count'],techniques=[],failure=RoughcutError(code,dict(block_reason=reason,editor=choice['editor'])).failure))
            if record['failure'] and plan is not None and record['failure']['design_state']=='cut-rearrange-failed':
                notices.append(dict(code='rearrange_failed',design_state=failure['design_state'] or 'cut-ready',count=failure['details'].get('short_shot_count'),techniques=[],failure=failure))
            if library['mine_status']=='unreadable':
                notices.append(dict(code='preset_store_unreadable',design_state='cut-presets-unreadable',count=None,techniques=[],failure=None))
            if speech['missing_video_count']:
                notices.append(dict(code='missing_word_timing',design_state='cut-partial-none' if speech['mode']=='all' else 'cut-partial',count=speech['missing_video_count'],techniques=speech['affected_techniques'],failure=None))
            if warnings and warnings['bed_short_count']:
                notices.append(dict(code='bed_source_too_short',design_state='cut-bed-short',count=warnings['bed_short_count'],techniques=['bed'],failure=None))
            analysis=record['analysis']
            if status=='prerequisite':base=None
            elif status=='no_music':base='cut-no-music'
            elif status in ('queued','arranging'):
                base='cut-beat-queued' if any(a['status']=='queued' for a in analysis) else 'cut-beat-analyzing' if any(a['status']=='analyzing' for a in analysis) else 'cut-arranging'
            elif failure and failure['design_state'] and plan is None:base=failure['design_state']
            elif plan:base='cut-multi' if plan['metrics']['song_count']>1 else 'cut-custom' if customization['changed'] else 'cut-mine' if any(p['id']==plan['preset_id'] and p['origin']=='mine' for p in library['presets']) else 'cut-ready'
            else:base=None
            scene_counts={}
            for shot in context['shots']:
                group='travel' if shot['scene'] in ('travel','travel/raw-pending') else shot['scene']
                scene_counts[group]=scene_counts.get(group,0)+1
            dominant=max(scene_counts,key=scene_counts.get) if scene_counts else None
            job=None
            if record['job_id']:
                raw_job=self.store.read_job(record['job_id'])['public']
                job={k:raw_job[k] for k in ('job_id','kind','revision')}
                if raw_job['status'] in ('queued','running','stopping') and 'busy' not in blockers:
                    blockers.append('busy')
            draft=self._draft_view(record,context,caps,stale or 'stale' in blockers)
            playback=copy.deepcopy((published or {}).get('playback',dict(status='unavailable',preview_artifact_id=None,duration_sec=None,audio_verified=False,failure=None)))
            if published and (stale or published['binding']!=record['input_binding']):
                playback.update(status='unavailable',preview_artifact_id=None)
            result=dict(ok=True,schema_version='roughcut_api_v1',piece_id=identity,project_revision=context['project']['revision'],revision=record['revision'],status=status,source_summary=context['summary'],selection=record['selection'],input_binding=record['input_binding'],plan=plan,plan_revision=None if published is None else published['revision'],plan_input_binding=None if published is None else published['binding'],job=job,analysis=analysis,failure=failure,recommendation=dict(preset_id='race' if dominant=='sports-meet' else 'diary' if dominant=='selfie-moments' else 'trip',scene_counts=scene_counts,dominant_scene=dominant,dominant_count=0 if dominant is None else scene_counts[dominant],sports_count=scene_counts.get('sports-meet',0)),preset_previews=record['preset_previews'],warnings=warnings,customization=customization,display=dict(base_state=base,notices=notices,draft_allowed=False,draft_blockers=list(dict.fromkeys(blockers)),speech=speech),artifacts=[] if published is None else published['artifacts'],playback=dict(status='unavailable',preview_artifact_id=None,duration_sec=None,audio_verified=False,failure=None),source_audio=[] if published is None else published['source_audio'])
            result.update(draft=draft,playback=playback)
            result['display']['draft_allowed']=not blockers
            if record.get('draft_published'):
                result['artifacts']=list({a['id']:a for a in [*result['artifacts'],*record['draft_published']['artifacts']]}.values())
            validate('state_response',result,code='roughcut_state_unreadable')
            return result

    @staticmethod
    def _cas(record, value, context):
        if type(value.get('expectedRevision')) is not int or value['expectedRevision']<1:
            raise RoughcutError('revision_invalid')
        if value['expectedRevision']!=record['revision']:
            raise RoughcutError('revision_conflict')
        if 'projectRevision' in value and value['projectRevision']!=context['project']['revision']:
            raise RoughcutError('roughcut_inputs_stale')
        if 'selectionDigest' in value and value['selectionDigest']!=context['summary']['selection_digest']:
            raise RoughcutError('roughcut_inputs_stale')
        if not context['summary']['selection_confirmed']:
            raise RoughcutError('selection_not_confirmed')

    def command(self, identity, value):
        validate('command_request',value,code='roughcut_command_invalid')
        with self.store.locked('piece',identity):
            context=self._context(identity,transcripts=True)
            record=self._current(identity,context)
            replay=self._replay_command(record,context,value)
            if replay is not None:return replay
            self._cas(record,value,context)
            selection=copy.deepcopy(record['selection'])
            command=value['command'];kind=command['type']
            playlist=selection['playlist']
            published=record['published']
            plan=None if published is None else published['plan']
            if kind=='select_music':
                selection['playlist']=[dict(id='song-'+secrets.token_hex(12),track_id=t) for t in command['track_ids']]
                selection['swap_positions']={}
            elif kind=='apply_preset':
                selection.update(preset_id=command['preset_id'],preset_revision=command['preset_revision'],technique_overrides={},occurrence_overrides={})
            elif kind=='set_technique':
                selection['technique_overrides'][command['id']]=command['enabled']
            elif kind=='set_occurrence':
                candidates=[] if plan is None else plan['occurrences']+plan['warnings']['bed_short_occurrences']
                if not any(o['id']==command['id'] for o in candidates):
                    raise RoughcutError('occurrence_not_found')
                selection['occurrence_overrides'][command['id']]=command['enabled']
            elif kind=='reset_customization':
                selection.update(technique_overrides={},occurrence_overrides={})
            elif kind=='add_song':
                playlist.append(dict(id='song-'+secrets.token_hex(12),track_id=command['track_id']))
            elif kind in ('replace_song','remove_song'):
                song=next((p for p in playlist if p['id']==command['song_instance_id']),None)
                if song is None:raise RoughcutError('roughcut_command_invalid')
                if kind=='replace_song':
                    if song['track_id']==command['track_id']:raise RoughcutError('roughcut_command_invalid')
                    song['track_id']=command['track_id']
                else:
                    playlist.remove(song)
                    selection['swap_positions'].pop(song['id'],None)
            elif kind=='move_swap':
                swap=next((s for s in (plan or {}).get('swaps',[]) if s['id']==command['swap_id']),None)
                if swap is None or not any(c['before_shot_id']==command['before_shot_id'] for c in swap['alternatives']):
                    raise RoughcutError('swap_boundary_invalid')
                selection['swap_positions'][swap['song_id']]=command['before_shot_id']
            tracks=[p['track_id'] for p in selection['playlist']]
            if any('/' in track or '\\' in track or '\x00' in track or track in ('.','..') for track in tracks):
                raise RoughcutError('roughcut_command_invalid')
            if not 1<=len(tracks)<=3 or len(set(tracks))!=len(tracks):
                raise RoughcutError('music_count_invalid')
            settings,_=self._config()
            preset=self._preset(selection)
            analysis=self._analysis(selection['playlist'])
            binding=self._binding(context,selection,preset,settings,analysis)
            accepted=self._accept(record,context,'arrange',selection,binding,analysis,command_request=value)
        self.jobs.submit(accepted['job_id'])
        return dict(ok=True,revision=accepted['revision'],job_id=accepted['job_id'],status='queued',accepted_selection=selection,input_binding=binding)

    def _replay_command(self, record, context, value):
        if record['job_id'] is None or record['status'] not in ('queued','arranging'):
            return None
        job=self.store.read_job(record['job_id'])
        request=job.get('command_request')
        if (not request or job['public']['kind']!='arrange' or
            job['public']['status'] not in ('queued','running') or not self._active(record,job) or
            request['command']!=value['command'] or
            value['expectedRevision'] not in (request['expectedRevision'],record['revision'])):
            return None
        self._cas(record,{**value,'expectedRevision':record['revision']},context)
        settings,_=self._config()
        self._check_inputs(context,job,settings,self._preset(job['selection']))
        return dict(ok=True,revision=job['public']['revision'],job_id=job['public']['job_id'],status='queued',accepted_selection=job['selection'],input_binding=job['accepted_binding'])

    def _accept(self, record, context, kind, selection, binding, analysis, *, media_ids=None, shot_ids=None, command_request=None, extra=None):
        job_id='cut-'+secrets.token_hex(16)
        revision=record['revision']+1
        public=dict(ok=True,job_id=job_id,piece_id=record['piece_id'],revision=revision,kind=kind,status='queued',progress=dict(phase='transcribe' if kind=='transcribe' else 'draft' if kind=='draft' else 'beat',completed=0,total=None,unit='media' if kind=='transcribe' else 'artifacts' if kind=='draft' else 'beats',determinate=False),analysis=analysis,failure=None,result_revision=None,result=None)
        job=dict(public=public,binding=binding,selection=copy.deepcopy(selection),confirmation_digest=context['confirmation_digest'],media_ids=media_ids or [],shot_ids=shot_ids or [])
        if extra:job.update(copy.deepcopy(extra))
        if command_request is not None:
            job.update(command_request=copy.deepcopy(command_request),accepted_binding=copy.deepcopy(binding))
        next_record=copy.deepcopy(record)
        next_record.update(revision=revision,status='queued',selection=selection,input_binding=binding,job_id=job_id,analysis=analysis,failure=None)
        if kind=='draft':
            next_record.update(status='ready',input_binding=record['input_binding'],draft_failure=None)
        elif kind=='arrange':
            next_record['draft_failure']=None
        self.store.write_job(job)
        try:
            self.store.write_state(record['piece_id'],next_record)
        except RoughcutError:
            self.store.job_path(job_id).unlink(missing_ok=True)
            raise
        if record['job_id']:
            self.jobs.cancel(record['job_id'])
        return dict(job_id=job_id,revision=revision)

    def save_preset(self, value):
        validate('create_request',value,presets=True,code='preset_invalid')
        identity=value['piece_id']
        with self.store.locked('presets','global'):
            mine=self.store.mine()
            revision=1 if mine is None else mine['revision']
            if value['expectedRevision']!=revision:raise RoughcutError('revision_conflict')
            with self.store.locked('piece',identity):
                context=self._context(identity,transcripts=True)
                record=self._current(identity,context)
                published=record['published']
                if published is None or published['revision']!=value['roughcut_revision'] or not self._source_matches(published['binding'],context) or record['status']!='ready':
                    raise RoughcutError('roughcut_inputs_stale')
                preset=self._preset(record['selection'])
                base_id=preset['id'] if preset['origin']=='builtin' else preset['base_preset_id']
                if base_id!=value['base_preset_id'] or record['selection']['technique_overrides']!=value['overrides']:
                    raise RoughcutError('preset_invalid')
                changes=published['plan']['customization']
                if not (changes['disabled'] or changes['enabled']):raise RoughcutError('preset_invalid')
                recipe=copy.deepcopy(preset['recipe'])
                recipe['techniques']=[t['id'] for t in published['plan']['techniques'] if t['enabled']]
                _,builtins=self._config()
                base=next(p for p in builtins if p['id']==base_id)
                overrides={t:(t in recipe['techniques']) for t in TECHNIQUES if (t in recipe['techniques']) != (t in base['recipe']['techniques'])}
                names=dict(jcut='声音先进',bed='现场声连着',duck='说话时压低音乐',pause='停顿处切',action='动作做完再切')
                description='从「'+base['name']+'」改的：'+'，'.join(('打开了' if v else '关掉了')+'「'+names[t]+'」' for t,v in overrides.items())
                saved=dict(id='mine-'+secrets.token_hex(12),revision=1,origin='mine',base_preset_id=base_id,name='我的预设',category='我的',description=description,recipe=recipe,overrides=overrides,created_at=datetime.now(timezone.utc).isoformat())
            payload=dict(schema_version='editing_presets_store_v1',revision=revision+1,presets=[saved]+([] if mine is None else mine['presets']))
            self.store.write_mine(payload)
            return dict(ok=True,revision=payload['revision'],preset=saved)

    def transcribe(self, identity, value):
        validate('transcription_request',value,code='transcript_selection_invalid')
        with self.store.locked('piece',identity):
            context=self._context(identity,transcripts=True)
            record=self._current(identity,context)
            self._cas(record,value,context)
            published=record['published']
            allowed=set() if published is None else set(published['plan']['warnings']['missing_word_shot_ids'])
            if published is not None and not self._source_matches(published['binding'],context):
                raise RoughcutError('roughcut_inputs_stale')
            if not set(value['shot_ids'])<=allowed:raise RoughcutError('transcript_selection_invalid')
            by_shot={s['id']:s for s in context['shots']}
            if any(by_shot[s]['kind']!='video' or by_shot[s]['scene']!='selfie-moments' for s in value['shot_ids']):
                raise RoughcutError('transcript_selection_invalid')
            media_ids=list(dict.fromkeys(by_shot[s]['media_id'] for s in value['shot_ids']))
            accepted=self._accept(record,context,'transcribe',record['selection'],record['input_binding'],record['analysis'],media_ids=media_ids,shot_ids=value['shot_ids'])
        self.jobs.submit(accepted['job_id'])
        return dict(ok=True,**accepted,media_ids=media_ids,shot_ids=value['shot_ids'])

    def draft(self, identity, value):
        validate('draft_request',value,code='request_invalid')
        with self.store.locked('piece',identity):
            context=self._context(identity,transcripts=True)
            record=self._current(identity,context)
            self._cas(record,value,context)
            self._require_plan_current(record,context)
            if record['job_id'] and self.store.read_job(record['job_id'])['public']['status'] in ('queued','running','stopping'):
                raise RoughcutError('roughcut_job_action_invalid')
            choice=self._draft_choice(identity,value['editorChoiceRevision'])
            published=record['published']
            if value['edlDigest']!=published['binding']['edl_digest']:
                raise RoughcutError('roughcut_inputs_stale')
            if self.draft_generator is None:
                self._draft_module()
            binding={**published['binding'],'editor_choice_revision':choice['revision']}
            accepted=self._accept(record,context,'draft',record['selection'],binding,record['analysis'],extra=dict(choice=choice,plan_revision=published['revision']))
        self.jobs.submit(accepted['job_id'])
        return dict(ok=True,**accepted,editor=choice['editor'],method=choice['method'],input_binding=binding)

    @staticmethod
    def _draft_module():
        try:
            return importlib.import_module('studio.roughcut_drafts')
        except (ImportError,AttributeError) as exc:
            raise RoughcutError('runtime_unavailable') from exc

    def _draft_choice(self, identity, revision):
        caps=self.capabilities(identity)
        if caps['selected'] is None:raise RoughcutError('editor_choice_unreadable')
        choice=caps['choice']
        if choice['revision']!=revision:raise RoughcutError('revision_conflict')
        if not caps['selected']['can_generate']:
            reason=caps['selected']['block_reason']
            code='editor_not_ready' if reason in ('editor_not_ready','editor_readiness_unknown') else 'draft_backend_unsupported'
            raise RoughcutError(code,dict(editor=choice['editor'],block_reason=reason))
        return choice

    def _draft_view(self, record, context, caps, stale):
        result=dict(status='none',design_state=None,job_id=None,plan_revision=None,editor=None,method=None,editor_choice_revision=None,input_edl_digest=None,edl_digest=None,guide_artifact_id=None,project_artifact_id=None,artifact_ids=[],can_open=False,failure=None)
        job=None if not record['job_id'] else self.store.read_job(record['job_id'])
        if job and job['public']['kind']=='draft' and job['public']['status'] in ('queued','running','stopping'):
            result.update(status=job['public']['status'] if job['public']['status']!='stopping' else 'running',design_state='cut-drafting',job_id=job['public']['job_id'],plan_revision=job['plan_revision'],editor=job['choice']['editor'],method=job['choice']['method'],editor_choice_revision=job['choice']['revision'],input_edl_digest=job['binding']['edl_digest'])
            return result
        if record.get('draft_failure'):
            result.update(status='failed',failure=record['draft_failure'])
            return result
        draft=record.get('draft_published')
        if draft:
            old=stale or record['published'] is None or draft['plan_revision']!=record['published']['revision'] or draft['choice']!=caps['choice'] or draft['binding']['edl_digest']!=record['published']['binding']['edl_digest']
            result.update(status='stale' if old else 'ready',design_state='cut-draft-stale' if old else 'cut-drafted-guide' if draft['choice']['method']=='guide' else 'cut-drafted',job_id=draft['job_id'],plan_revision=draft['plan_revision'],editor=draft['choice']['editor'],method=draft['choice']['method'],editor_choice_revision=draft['choice']['revision'],input_edl_digest=draft['binding']['edl_digest'],edl_digest=draft['result']['edl_digest'],guide_artifact_id=draft['guide_artifact_id'],project_artifact_id=draft['project_artifact_id'],artifact_ids=draft['result']['artifact_ids'],can_open=not old and draft['project_artifact_id'] is not None and bool(caps['selected'] and caps['selected']['can_generate']))
        return result

    def _music_sources(self, playlist):
        sources={}
        for song in playlist:
            key=song['track_id']
            if self.music_resolver:
                path=self.music_resolver(key)
                if path is None:raise RoughcutError('unknown_track',dict(track_id=key))
                path=safe_path(path,local_media_root(),'result_unreadable')
            else:
                folder=local_media_root()/'library/music'/key
                track=self.reader.read(folder/'track.json',local_media_root(),'result_unreadable')
                if not isinstance(track,dict) or track.get('file_sha256')!=key or not isinstance(track.get('audio_file'),str):
                    raise RoughcutError('result_unreadable',dict(track_id=key))
                path=safe_path(folder/track['audio_file'],folder,'result_unreadable')
            sources[key]=path
        return sources

    @staticmethod
    def _music_facts(sources):
        return {key:dict(size=path.stat().st_size,mtime_ns=path.stat().st_mtime_ns,ctime_ns=path.stat().st_ctime_ns) for key,path in sources.items()}

    def _require_plan_current(self, record, context):
        published=record['published']
        if (published is None or not self._source_matches(published['binding'],context) or
            published['binding']!=record['input_binding']):
            raise RoughcutError('roughcut_inputs_stale')
        settings,_=self._config()
        preset=self._preset(record['selection'])
        if digest(settings)!=published['binding']['settings_digest'] or self._recipe_digest(preset,record['selection'])!=published['binding']['preset_digest']:
            raise RoughcutError('roughcut_inputs_stale')
        analysis=self._analysis(record['selection']['playlist'])
        current=self._binding(context,record['selection'],preset,settings,analysis)
        if current['music']!=published['binding']['music']:
            raise RoughcutError('roughcut_inputs_stale')
        if published.get('music_facts')!=self._music_facts(self._music_sources(record['selection']['playlist'])):
            raise RoughcutError('roughcut_inputs_stale')
        return published

    def _generator_args(self, context, plan, inputs, revision):
        return dict(workspace=context['root'],plan=plan,planner_inputs=inputs,sources_by_media=context['sources_by_media'],music_sources=self._music_sources(inputs['playlist']),project_id=context['project']['id'],project_revision=context['project']['revision'],plan_revision=revision,media_root=local_media_root())

    def _generated_artifacts(self, identity, context, revision, generated):
        directory=safe_path(Path(generated['directory'])/'06_edit_decision_list.json',context['root'],'draft_failed').parent
        if not directory.is_relative_to(context['root']/'draft-project/roughcut') and not directory.is_relative_to(context['root']/'ai-analysis/roughcut'):
            raise RoughcutError('draft_failed')
        artifacts=copy.deepcopy(generated['artifacts']);index=copy.deepcopy(generated['artifact_index'])
        if not isinstance(artifacts,list) or not artifacts or not isinstance(index,dict):raise RoughcutError('draft_failed')
        if set(index)!={a['id'] for a in artifacts}:raise RoughcutError('draft_failed')
        for asset in artifacts:
            item=index[asset['id']]
            path=safe_path(context['root']/item['relative_path'],directory,'draft_failed')
            if (context['root']/item['allowed_root']).resolve()!=directory or asset['revision']!=revision or asset['content_type']!=item['content_type']:
                raise RoughcutError('draft_failed')
            if asset['content_type']=='text/markdown; charset=utf-8':
                asset['content_type']=item['content_type']='text/plain; charset=utf-8'
            asset['url']=f'/api/review/pieces/{urllib.parse.quote(identity,safe="")}/roughcut/media/{asset["id"]}'
            validate('artifact',asset,code='draft_failed')
            stat=path.stat();item['stamp']=[stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns]
        return artifacts,index

    def _handoff_note(self, generated, plan, choice, context):
        workspace=context['root']
        directory=safe_path(Path(generated['directory'])/'06_edit_decision_list.json',workspace,'draft_failed').parent
        if not directory.is_relative_to(workspace/'draft-project/roughcut'):
            raise RoughcutError('draft_failed')
        modes=capabilities_for_choice(choice,ready=True)
        names=dict(jcut='声音先进',bed='现场声连着',duck='说话时压低音乐',pause='停顿处切',action='动作做完再切')
        instructions=dict(jcut='让下一镜的现场声提前进入。',bed='让这几个镜头共用连续的现场声。',duck='按说话区间压低配乐，停顿时恢复。',pause='在逐字时间确定的停顿处切换镜头。',action='动作做完后再切换镜头。')
        order={c['shot_id']:i+1 for i,c in enumerate(plan['clips'])}
        def clock(sec):return f'{int(sec)//60:02d}:{sec%60:06.3f}'
        lines=['剪辑交接说明','',f"镜头：{len(plan['clips'])} 个；总时长：{plan['metrics']['duration_sec']:.2f} 秒。",'以下按时间码列出各处手法；标为人工处理的部分请在剪辑软件里核对并完成。','']
        for i,clip in enumerate(plan['clips'],1):
            source=context['sources_by_media'][clip['media_id']].name
            span='照片按此时长显示' if clip['kind']=='photo' else f"原片 {clip['source_start']:.3f}–{clip['source_end']:.3f} 秒"
            lines.append(f"第 {i} 个镜头 · {source} · {clock(clip['start'])}–{clock(clip['end'])} · {span}")
        lines.append('')
        for i,song in enumerate(plan['songs'],1):
            lines.append(f"第 {i} 首 · {song['title']} · {clock(song['start'])}–{clock(song['end'])} · 原曲从 {song['offset']:.3f} 秒开始")
        lines.append('')
        for item in plan['occurrences']:
            if not item['live']:continue
            manual=modes['techniques'][item['technique']]['mode']=='manual'
            slots='、'.join(str(order[s]) for s in item['shot_ids'])
            lines.append(f"{clock(item['at'])} · 第 {slots} 个镜头 · {names[item['technique']]} · {'要你在剪辑软件里做' if manual else '已按排法放入时间线'}")
            lines.append(instructions[item['technique']])
            reason=item['reason_data']
            if item['technique']=='jcut':lines.append(f"提前 {reason['lead_sec']:.3f} 秒进入下一镜的现场声。")
            elif item['technique']=='bed':lines.append(f"使用第 {order[reason['source_shot_id']]} 个镜头的现场声，原片从 {reason['source_start_sec']:.3f} 秒起，覆盖 {clock(item['at'])}–{clock(item['end'])}。")
            elif item['technique']=='duck':
                for region in reason['regions']:
                    lines.append(f"{clock(region['start'])}–{clock(region['end'])}：配乐调至 {20*math.log10(region['gain']):.1f} dB，过渡 {region['ramp_sec']:.3f} 秒。")
        for swap in plan['swaps']:
            lines.append(f"{clock(swap['at'])} · 换歌 · {'要你在剪辑软件里做' if modes['swap']['mode']=='manual' else '已按排法放入时间线'}")
        note=directory/'剪辑手法交接说明.txt'
        with note.open('x',encoding='utf-8') as handle:handle.write('\n'.join(lines)+'\n')
        identity='guide-'+digest(dict(attempt=directory.name,note=note.name))[:32]
        generated['artifacts'].append(dict(id=identity,kind='guide',content_type='text/plain; charset=utf-8',revision=generated['artifacts'][0]['revision'],shot_id=None,url=f'/api/review/pieces/local/roughcut/media/{identity}'))
        generated['artifact_index'][identity]=dict(relative_path=note.relative_to(workspace).as_posix(),allowed_root=directory.relative_to(workspace).as_posix(),content_type='text/plain; charset=utf-8')
        return identity

    def _run_draft(self, job, event, context):
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            published=self._require_plan_current(record,context)
            choice=self._draft_choice(identity,job['choice']['revision'])
            if choice!=job['choice'] or published['revision']!=job['plan_revision']:
                raise RoughcutError('roughcut_inputs_stale')
            snapshot=copy.deepcopy(published)
        self._progress(job,'draft',0,None,'artifacts')
        args=self._generator_args(context,snapshot['plan'],snapshot['planner_inputs'],snapshot['revision'])
        generator=self.draft_generator or self._draft_module().generate_draft
        try:generated=generator(**args,editor_choice=choice)
        except Exception as exc:
            code=getattr(exc,'code',None)
            raise RoughcutError(code if code in ('roughcut_inputs_stale','runtime_unavailable') else 'draft_failed') from exc
        if self._cancelled(job,event):self._stopped(job);return
        self._generated_artifacts(identity,context,snapshot['revision'],generated)
        if choice['method']=='guide' and any(Path(generated['directory']).rglob('captions.srt')):
            raise RoughcutError('draft_failed',dict(dependency='roughcut_guide_exporter'))
        if generated['result']['edl_digest']!=hashlib.sha256((Path(generated['directory'])/'06_edit_decision_list.json').read_bytes()).hexdigest():
            raise RoughcutError('draft_failed')
        guide=self._handoff_note(generated,snapshot['plan'],choice,context)
        artifacts,index=self._generated_artifacts(identity,context,snapshot['revision'],generated)
        generated['result']['artifact_ids']=[a['id'] for a in artifacts]
        validate('draft_result',generated['result'],code='draft_failed')
        if any(generated['result'][k]!=choice[k] for k in ('editor','method')) or generated['result']['project_revision']!=context['project']['revision']:
            raise RoughcutError('draft_failed')
        project=next((a['id'] for a in artifacts if a['content_type']=='application/xml'),None)
        if choice['method']=='external' and project is None:raise RoughcutError('draft_failed')
        preview_asset=next((a for a in artifacts if a['kind']=='preview' and a['content_type']=='video/mp4'),None)
        duration=generated.get('duration_sec')
        if duration is None:
            receipt=self.reader.read(Path(generated['receipt_path']),context['root'],'draft_failed')
            duration=receipt.get('preview_duration_sec')
        if preview_asset is None or type(duration) not in (int,float) or not math.isfinite(duration) or abs(duration-snapshot['plan']['metrics']['duration_sec'])>1/30+.02:
            raise RoughcutError('draft_failed')
        fresh=self._context(identity,transcripts=True)
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if not self._active(record,job) or event.is_set():self._stopped(job);return
            published=self._require_plan_current(record,fresh)
            if self._draft_choice(identity,choice['revision'])!=choice or published['revision']!=snapshot['revision']:
                raise RoughcutError('roughcut_inputs_stale')
            current_args=self._generator_args(fresh,snapshot['plan'],snapshot['planner_inputs'],snapshot['revision'])
            edl=self._draft_module().compile_roughcut_edl(**{k:current_args[k] for k in ('plan','planner_inputs','sources_by_media','music_sources','project_id','project_revision')})
            if digest(edl)!=job['binding']['edl_digest']:raise RoughcutError('roughcut_inputs_stale')
            self._progress(job,'draft',len(artifacts),len(artifacts),'artifacts')
            previous=copy.deepcopy(record)
            old=record.get('draft_published')
            record['retired_artifact_ids']=sorted(set(record.get('retired_artifact_ids',[]))|set([] if not old else old['result']['artifact_ids']))
            record.update(status='ready',draft_failure=None,draft_published=dict(job_id=job['public']['job_id'],plan_revision=snapshot['revision'],choice=choice,binding=job['binding'],result=generated['result'],artifacts=artifacts,artifact_index=index,guide_artifact_id=guide,project_artifact_id=project))
            published['artifacts'].append(preview_asset)
            published['artifact_index'][preview_asset['id']]=index[preview_asset['id']]
            published['playback']=dict(status='ready',preview_artifact_id=preview_asset['id'],duration_sec=duration,audio_verified=False,failure=None)
            self.store.write_state(identity,record)
            job['public'].update(status='done',failure=None,result_revision=None,result=dict(kind='draft',draft=generated['result']))
            try:self.store.write_job(job)
            except RoughcutError:
                self.store.write_state(identity,previous)
                raise

    def open_draft(self, identity, value):
        validate('open_draft_request',value,code='request_invalid')
        with self.store.locked('piece',identity):
            context=self._context(identity,transcripts=True)
            record=self._current(identity,context);self._cas(record,value,context)
            self._require_plan_current(record,context)
            draft=record.get('draft_published')
            choice=self._draft_choice(identity,value['editorChoiceRevision'])
            if (not draft or choice!=draft['choice'] or choice['method']!='external' or choice['editor']!='otio_kdenlive' or
                draft['plan_revision']!=record['published']['revision'] or draft['result']['edl_digest']!=value['edlDigest'] or not draft['project_artifact_id']):
                raise RoughcutError('roughcut_inputs_stale')
            item=draft['artifact_index'][draft['project_artifact_id']]
            path=safe_path(context['root']/item['relative_path'],context['root']/item['allowed_root'],'roughcut_inputs_stale')
            self._check_artifact_stamp(path,item)
            try:
                if self.editor_opener:opened=self.editor_opener(project_dir=path.parent)
                else:
                    if self.editor_backend is None:self.editor_backend=self._draft_module().Backend()
                    opened=self.editor_backend.open_for_refine(project_dir=path.parent)
            except Exception as exc:raise RoughcutError('draft_failed') from exc
            if opened!={'editor_backend':'otio_kdenlive','opened':True,'local_only':True}:raise RoughcutError('draft_failed')
            return dict(ok=True,**opened,revision=record['revision'],plan_revision=draft['plan_revision'])

    @staticmethod
    def _check_artifact_stamp(path, item):
        stat=path.stat()
        if 'stamp' in item and item['stamp']!=[stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns]:
            raise RoughcutError('roughcut_inputs_stale')

    def job(self, job_id):
        raw=self.store.read_job(job_id)
        with self.store.locked('piece',raw['public']['piece_id']):
            return self.store.read_job(job_id)['public']

    def stop(self, job_id, value):
        validate('stop_request',value,code='roughcut_job_action_invalid')
        job=self.store.read_job(job_id)
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            job=self.store.read_job(job_id)
            record=self.store.read_state(identity)
            if record is None:raise RoughcutError('roughcut_state_unreadable')
            if job['public']['status'] in ('stopping','stopped') and 'stop_request_revision' in job:
                if value['expectedRevision'] not in (record['revision'],job['stop_request_revision']):
                    raise RoughcutError('revision_conflict')
                return dict(ok=True,job_id=job_id,status=job['stop_response_status'],revision=job['stop_result_revision'])
            if value['expectedRevision']!=record['revision']:raise RoughcutError('revision_conflict')
            if record['job_id']!=job_id or job['public']['status'] in ('done','failed','stopped'):
                raise RoughcutError('roughcut_job_action_invalid')
            with self.jobs.lock:
                status='stopping' if job_id in self.jobs.running else 'stopped'
            next_record=copy.deepcopy(record)
            next_record.update(revision=record['revision']+1,status=status)
            previous_job=copy.deepcopy(job)
            job.update(stop_request_revision=value['expectedRevision'],stop_result_revision=next_record['revision'],stop_response_status=status)
            job['public'].update(status=status,failure=None,result=None,result_revision=None)
            self.store.write_job(job)
            try:
                self.store.write_state(identity,next_record)
            except RoughcutError:
                self.store.write_job(previous_job)
                raise
            self.jobs.cancel(job_id)
            return dict(ok=True,job_id=job_id,status=status,revision=next_record['revision'])

    @staticmethod
    def _active(record, job):
        return bool(record and record['job_id']==job['public']['job_id'] and record['revision']==job['public']['revision'])

    def _cancelled(self, job, event):
        if event.is_set():return True
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            return not self._active(self.store.read_state(identity),job)

    def _stopped(self, job):
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            job=self.store.read_job(job['public']['job_id'])
            if job['public']['status']=='done':return
            job['public'].update(status='stopped',failure=None,result=None,result_revision=None)
            self.store.write_job(job)
            record=self.store.read_state(identity)
            if record and record['job_id']==job['public']['job_id']:
                record['status']='stopped'
                self.store.write_state(identity,record)

    def _progress(self, job, phase, completed, total, unit):
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if not self._active(record,job):return False
            job['public']['progress']=dict(phase=phase,completed=completed,total=total or None,unit=unit,determinate=bool(total))
            self.store.write_job(job)
            return True

    @staticmethod
    def _domain_error(exc, previous=False):
        if isinstance(exc,RoughcutError):
            return RoughcutError(exc.code,exc.failure['details'],previous=previous)
        details=copy.deepcopy(getattr(exc,'details',{}))
        if 'shot_id' in details:
            details.update(shot_ids=[details.pop('shot_id')],short_shot_count=1)
        return RoughcutError(getattr(exc,'code','request_invalid'),details,previous=previous)

    def _fail_job(self, job, error):
        identity=job['public']['piece_id']
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if not self._active(record,job):
                self._stopped(job)
                return
            error=self._domain_error(error,previous=record['published'] is not None)
            job['public'].update(status='failed',failure=error.failure,result=None,result_revision=None)
            self.store.write_job(job)
            if job['public']['kind']=='draft':
                record.update(status='ready',draft_failure=error.failure)
            else:
                record.update(status='failed',failure=error.failure)
            self.store.write_state(identity,record)

    def _check_inputs(self, context, job, settings, preset, *, ignore_transcripts=False):
        binding=job['binding']
        candidate=copy.deepcopy(binding)
        if ignore_transcripts:candidate['transcripts_digest']=context['transcripts_digest']
        if (not self._source_matches(candidate,context) or job['confirmation_digest']!=context['confirmation_digest'] or
            digest(settings)!=binding['settings_digest'] or self._recipe_digest(preset,job['selection'])!=binding['preset_digest']):
            raise RoughcutError('roughcut_inputs_stale')

    def _run_job(self, job_id, event):
        job=self.store.read_job(job_id)
        try:
            identity=job['public']['piece_id']
            with self.store.locked('piece',identity):
                # A stop may still roll back; only inspect its outcome under the same lock.
                job=self.store.read_job(job_id)
                if job['public']['status'] in ('done','failed','stopped'):return
                record=self.store.read_state(identity)
                if event.is_set() or not self._active(record,job):
                    self._stopped(job);return
                job['public']['status']='running'
                record['status']='ready' if job['public']['kind']=='draft' else 'arranging'
                self.store.write_job(job);self.store.write_state(identity,record)
            context=self._context(identity,transcripts=True)
            settings,_=self._config()
            preset=self._preset(job['selection'])
            self._check_inputs(context,job,settings,preset)
            if job['public']['kind']=='transcribe':
                self._run_transcription(job,event,context)
            elif job['public']['kind']=='draft':
                self._run_draft(job,event,context)
            else:
                self._run_arrangement(job,event,context,settings,preset)
        except Exception as exc:
            if self._cancelled(job,event):self._stopped(job)
            else:self._fail_job(job,exc)

    def _run_arrangement(self, job, event, context, settings, preset):
        identity=job['public']['piece_id']
        deadline=time.monotonic()+BEAT_WAIT_TIMEOUT_SEC
        delay=self.poll_interval
        while True:
            if self._cancelled(job,event):self._stopped(job);return
            analysis=self._analysis(job['selection']['playlist'])
            binding=self._binding(context,job['selection'],preset,settings,analysis)
            with self.store.locked('piece',identity):
                record=self.store.read_state(identity)
                if not self._active(record,job):self._stopped(job);return
                record.update(analysis=analysis,input_binding=binding)
                job['public']['analysis']=analysis
                job['binding']=binding
                self.store.write_job(job);self.store.write_state(identity,record)
            if all(a['status']=='done' for a in analysis):break
            self._progress(job,'beat',0,None,'beats')
            remaining=deadline-time.monotonic()
            if remaining<=0:
                pending=next(a for a in analysis if a['status']!='done')
                raise RoughcutError('beat_failed',dict(track_id=pending['track_id'],upstream_failure_code='analysis_timeout'))
            if event.wait(min(delay,remaining)):self._stopped(job);return
            delay=min(delay*2,BEAT_POLL_MAX_SEC)
            fresh=self._context(identity,transcripts=True)
            self._check_inputs(fresh,job,settings,preset)
        beat_maps={a['track_id']:a['beat_map'] for a in analysis}
        previews=[];plan=None
        library=self.presets()
        self._progress(job,'cuts',0,len(context['shots']),'shots')
        for item in library['presets']:
            if self._cancelled(job,event):self._stopped(job);return
            selected=item['id']==preset['id']
            recipe=dict(id=item['id'],name=item['name'],category=item['category'],description=item['description'],**item['recipe'])
            try:
                result=self.planner(shots=context['shots'],beat_maps=beat_maps,playlist=job['selection']['playlist'],preset=recipe,settings=settings,transcripts=context['transcripts'],technique_overrides=job['selection']['technique_overrides'] if selected else {},occurrence_overrides=job['selection']['occurrence_overrides'] if selected else {},swap_positions=job['selection']['swap_positions'])
                validate('plan',result,code='shots_invalid')
                if selected:
                    plan=result
                    self._progress(job,'cuts',len(context['shots']),len(context['shots']),'shots')
                preview=dict(preset_id=item['id'],preset_revision=item['revision'],input_digest=digest(dict(binding=binding,preset=item)),status='ready',duration_sec=result['metrics']['duration_sec'],preview_shot_ids=result['metrics']['preview_shot_ids'],cuts=result['cuts'],mapped_sections=result['mapped_sections'],failure=None)
            except (PlannerError,RoughcutError) as exc:
                if selected:raise
                preview=dict(preset_id=item['id'],preset_revision=item['revision'],input_digest=digest(dict(binding=binding,preset=item)),status='failed',duration_sec=None,preview_shot_ids=[],cuts=[],mapped_sections=[],failure=self._domain_error(exc).failure)
            previews.append(preview)
        if plan is None:raise RoughcutError('preset_not_found')
        self._progress(job,'techniques',len(plan['occurrences']),len(plan['occurrences']),'occurrences')
        fresh=self._context(identity,transcripts=True)
        fresh_settings,_=self._config()
        self._check_inputs(fresh,job,fresh_settings,self._preset(job['selection']))
        fresh_analysis=self._analysis(job['selection']['playlist'])
        if self._binding(fresh,job['selection'],preset,settings,fresh_analysis)!=binding:
            raise RoughcutError('roughcut_inputs_stale')
        inputs=dict(shots=context['shots'],beat_maps=beat_maps,playlist=job['selection']['playlist'],preset=dict(id=preset['id'],name=preset['name'],category=preset['category'],description=preset['description'],**preset['recipe']),settings=settings,transcripts=context['transcripts'],technique_overrides=job['selection']['technique_overrides'],occurrence_overrides=job['selection']['occurrence_overrides'],swap_positions=job['selection']['swap_positions'])
        args=self._generator_args(context,plan,inputs,job['public']['revision'])
        module=self._draft_module()
        edl=module.compile_roughcut_edl(**{k:args[k] for k in ('plan','planner_inputs','sources_by_media','music_sources','project_id','project_revision')})
        music_facts=self._music_facts(args['music_sources'])
        self._progress(job,'preview',0,None,'artifacts')
        renderer=self.preview_renderer or getattr(module,'generate_preview',None)
        preview_error=None;preview_artifacts=[];preview_index={};preview_asset=None;duration=None
        try:
            if not callable(renderer):raise RoughcutError('preview_failed',dict(dependency='roughcut_preview_renderer'))
            generated=renderer(**args)
            preview_artifacts,preview_index=self._generated_artifacts(identity,context,job['public']['revision'],generated)
            preview_asset=next((a for a in preview_artifacts if a['kind']=='preview' and a['content_type']=='video/mp4'),None)
            duration=generated.get('duration_sec')
            if preview_asset is None or type(duration) not in (int,float) or not math.isfinite(duration) or abs(duration-plan['metrics']['duration_sec'])>1/30+.02:
                raise RoughcutError('preview_failed')
        except Exception as exc:
            if getattr(exc,'code',None)=='roughcut_inputs_stale':raise RoughcutError('roughcut_inputs_stale') from exc
            preview_error=exc if isinstance(exc,RoughcutError) and exc.code=='preview_failed' else RoughcutError('preview_failed')
            preview_artifacts=[];preview_index={};preview_asset=None;duration=None
        fresh=self._context(identity,transcripts=True)
        fresh_settings,_=self._config()
        self._check_inputs(fresh,job,fresh_settings,self._preset(job['selection']))
        if self._binding(fresh,job['selection'],preset,fresh_settings,self._analysis(job['selection']['playlist']))!=binding or music_facts!=self._music_facts(self._music_sources(job['selection']['playlist'])):
            raise RoughcutError('roughcut_inputs_stale')
        binding={**binding,'edl_digest':digest(edl)}
        artifacts,index=self._artifacts(identity,job['public']['revision'],context,plan,binding)
        artifacts.extend(preview_artifacts);index.update(preview_index)
        source_audio=[dict(shot_id=c['shot_id'],has_audio=next(s.get('has_audio') for s in context['shots'] if s['id']==c['shot_id']),mode='unknown',evidence='unverified',position=round(c['start']/plan['metrics']['duration_sec'],6),end_position=round(c['end']/plan['metrics']['duration_sec'],6)) for c in plan['clips']]
        if preview_error is None:self._progress(job,'preview',len(artifacts),len(artifacts),'artifacts')
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if not self._active(record,job) or event.is_set():self._stopped(job);return
            previous=copy.deepcopy(record)
            retired=set(record.get('retired_artifact_ids',[]))
            if record['published']:
                retired.update(a['id'] for a in record['published']['artifacts'] if a['kind']!='thumbnail')
            record.update(status='ready',failure=None,preset_previews=previews,analysis=analysis,input_binding=binding,retired_artifact_ids=sorted(retired),published=dict(plan=plan,revision=job['public']['revision'],binding=binding,artifacts=artifacts,artifact_index=index,source_audio=source_audio,preset=preset,planner_inputs=inputs,music_facts=music_facts,playback=dict(status='unavailable' if preview_error else 'ready',preview_artifact_id=None if preview_asset is None else preview_asset['id'],duration_sec=duration,audio_verified=False,failure=None if preview_error is None else preview_error.failure)))
            self.store.write_state(identity,record)
            if preview_error:
                job['public'].update(status='failed',failure=preview_error.failure,result_revision=None,result=None)
            else:
                job['public'].update(status='done',failure=None,result_revision=job['public']['revision'],result=dict(kind='arrange',result_revision=job['public']['revision']))
            try:self.store.write_job(job)
            except RoughcutError:
                self.store.write_state(identity,previous)
                raise

    @staticmethod
    def _word_ready(document):
        if not document or document.get('status')!='ok' or document.get('precision')!='word' or document.get('auto_cut_allowed') is not True:
            return False
        segments=document.get('segments')
        return bool(segments and all(isinstance(s,dict) and s.get('precision')=='word' and s.get('words') and all(isinstance(w,dict) and type(w.get('start')) in (int,float) and type(w.get('end')) in (int,float) and math.isfinite(w['start']) and math.isfinite(w['end']) and s['start_sec']<=w['start']<=w['end']<=s['end_sec'] for w in s['words']) for s in segments))

    def _run_transcription(self, job, event, context):
        identity=job['public']['piece_id']
        def cancelled():
            if self._cancelled(job,event):return True
            fresh=self._context(identity,transcripts=False)
            return not (fresh['shots_digest']==context['shots_digest'] and fresh['project']['revision']==context['project']['revision'] and fresh['confirmation_digest']==context['confirmation_digest'])
        while not self.asr_lock.acquire(timeout=.1):
            if cancelled():self._stopped(job);return
        try:
            if cancelled():self._stopped(job);return
            self._progress(job,'transcribe',0,len(job['media_ids']),'media')
            self.transcriber.run(context,job['media_ids'],cancelled)
        finally:
            self.asr_lock.release()
        if cancelled():self._stopped(job);return
        fresh=self._context(identity,transcripts=True)
        ready=[s['id'] for s in fresh['shots'] if s['id'] in job['shot_ids'] and self._word_ready(fresh['transcripts'].get(s['media_id']))]
        missing=[s for s in job['shot_ids'] if s not in ready]
        follow=None
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if not self._active(record,job) or event.is_set():self._stopped(job);return
            self._progress(job,'transcribe',len(job['media_ids']),len(job['media_ids']),'media')
            settings,_=self._config();preset=self._preset(job['selection'])
            if fresh['transcripts_digest']!=context['transcripts_digest']:
                binding=self._binding(fresh,job['selection'],preset,settings,record['analysis'])
                follow=self._accept(record,fresh,'arrange',job['selection'],binding,record['analysis'])
            else:
                record['status']='ready' if record['published'] else 'stopped'
                self.store.write_state(identity,record)
            job['public'].update(status='done',failure=None,result_revision=None,result=dict(kind='transcribe',transcription=dict(media_ids=job['media_ids'],shot_ids=job['shot_ids'],word_ready_shot_ids=ready,missing_word_shot_ids=missing,rearrange_job_id=None if follow is None else follow['job_id'])))
            self.store.write_job(job)
        if follow:self.jobs.submit(follow['job_id'])

    def _artifacts(self, identity, revision, context, plan, binding):
        artifacts,index=[],{}
        for row in context['rows']:
            frames=row.get('frames',[])
            if not frames:continue
            relative=frames[len(frames)//2]
            try:path=safe_path(context['root']/relative,context['root']/'ai-analysis/shots/frames','roughcut_media_not_found')
            except RoughcutError:continue
            mime='image/png' if path.suffix.lower()=='.png' else 'image/jpeg' if path.suffix.lower() in ('.jpg','.jpeg') else None
            if mime is None:continue
            id='thumb-'+digest(dict(piece=identity,revision=revision,shot=row['id'],binding=binding))[:32]
            artifacts.append(dict(id=id,kind='thumbnail',url=f'/api/review/pieces/{urllib.parse.quote(identity,safe="")}/roughcut/media/{id}',content_type=mime,revision=revision,shot_id=row['id']))
            index[id]=dict(relative_path=path.relative_to(context['root']).as_posix(),allowed_root='ai-analysis/shots/frames',content_type=mime)
        return artifacts,index

    def media(self, identity, artifact_id, range_header=None):
        self._project(identity)
        with self.store.locked('piece',identity):
            record=self.store.read_state(identity)
            if record is None or record['published'] is None:
                raise RoughcutError('roughcut_media_not_found')
            published=record['published']
            item=published['artifact_index'].get(artifact_id)
            draft=record.get('draft_published')
            from_draft=False
            if item is None and draft:
                item=draft['artifact_index'].get(artifact_id)
                from_draft=item is not None
            if item is None:
                if artifact_id in record.get('retired_artifact_ids',[]):raise RoughcutError('roughcut_inputs_stale')
                raise RoughcutError('roughcut_media_not_found')
            context=self._context(identity,transcripts=True)
            self._require_plan_current(record,context)
            saved_choice=self.app._video_editor_choice(identity) if from_draft else None
            if from_draft and (draft['plan_revision']!=published['revision'] or {k:saved_choice[k] for k in ('editor','method','revision')}!=draft['choice']):
                raise RoughcutError('roughcut_inputs_stale')
            path=safe_path(context['root']/item['relative_path'],context['root']/item['allowed_root'],'roughcut_media_not_found')
            self._check_artifact_stamp(path,item)
            size=path.stat().st_size
            start,end=0,size-1
            headers={'Accept-Ranges':'bytes'}
            if item['content_type'].startswith('text/'):
                headers['Content-Disposition']='inline'
            if range_header is not None:
                match=re.fullmatch(r'bytes=(\d{0,20})-(\d{0,20})',range_header)
                valid=bool(match and any(match.groups()))
                if valid:
                    first,last=match.groups()
                    if first:
                        start=int(first);end=min(int(last),size-1) if last else size-1
                    else:
                        valid=int(last)>0;start=max(0,size-int(last))
                    valid=valid and 0<=start<=end<size
                if not valid:raise RoughcutError('range_not_satisfiable',dict(media_length=size))
                headers['Content-Range']=f'bytes {start}-{end}/{size}'
            return MediaSlice(path,206 if range_header is not None else 200,item['content_type'],start,max(0,end-start+1),headers)


def for_application(app):
    with CHOICE_LOCK:
        if not hasattr(app,'roughcut'):
            app.roughcut=RoughcutService(app)
        return app.roughcut


def dispatch(app, method, segments, value=None, range_header=None):
    service=for_application(app)
    if segments==['api','review','editing-presets']:
        return (201,service.save_preset(value)) if method=='POST' else (200,service.presets())
    if len(segments)==4 and segments[2]=='roughcut-jobs':
        return (202,service.stop(segments[3],value)) if method=='POST' else (200,service.job(segments[3]))
    identity=segments[3]
    if segments[4]=='editor-capabilities':return 200,service.capabilities(identity)
    if len(segments)==5:return 200,service.state(identity)
    action=segments[5]
    if action=='media':return service.media(identity,segments[6],range_header)
    if action=='commands':return 202,service.command(identity,value)
    if action=='transcriptions':return 202,service.transcribe(identity,value)
    if action=='drafts':
        if len(segments)==7:return 200,service.open_draft(identity,value)
        return 202,service.draft(identity,value)
    raise RoughcutError('request_invalid')
