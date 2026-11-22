"""Pure deterministic media-first roughcut planning; no EDL or runtime IO."""
from bisect import bisect_right
from collections import Counter
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
import math
from urllib.parse import quote

TECHNIQUES = ('jcut', 'bed', 'duck', 'pause', 'action')
SECTION_KINDS = {'quiet', 'build', 'peak'}
EPS = 1e-6


class PlannerError(ValueError):
    """Stable machine failure with identity/number details, never source prose."""
    def __init__(self, code, details=None):
        self.code, self.details = code, details or {}
        super().__init__(code)


def _fail(code, **details):
    raise PlannerError(code, details)


def _number(value, code, field, minimum=0, positive=False):
    if (type(value) not in (int, float) or not math.isfinite(value) or
            value < minimum or (positive and value <= minimum)):
        _fail(code, field=field)
    return float(value)


def _q(value):
    return round(value, 6)


def _rounded(value, places=0):
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def _identity(value, code, field):
    if not isinstance(value, str) or not value.strip():
        _fail(code, field=field)
    return value


def _token(value):
    return quote(value, safe='')


def _scene(scene):
    return 'travel' if scene in ('travel', 'travel/raw-pending') else scene


def preview_indices(count):
    if type(count) is not int or count <= 0:
        _fail('shots_invalid', field='count')
    return [int(_rounded(i*(count-1)/5)) for i in range(6)]


def preset_counts(presets):
    if not isinstance(presets, list):
        _fail('preset_invalid', field='presets')
    seen, counts = set(), Counter()
    for preset in presets:
        if not isinstance(preset, dict):
            _fail('preset_invalid', field='preset')
        identity = _identity(preset.get('id'), 'preset_invalid', 'id')
        category = _identity(preset.get('category'), 'preset_invalid', 'category')
        if identity in seen:
            _fail('preset_invalid', field='duplicate_id')
        seen.add(identity)
        counts[category] += 1
    return {'total': len(presets), 'categories': dict(counts)}


def timeline_position(time, duration):
    time = _number(time, 'shots_invalid', 'time', minimum=-math.inf)
    duration = _number(duration, 'shots_invalid', 'duration', positive=True)
    return max(0.0, min(1.0, time/duration))


def clip_at(plan, time):
    time = _number(time, 'shots_invalid', 'time', minimum=-math.inf)
    clips = plan['clips']
    return deepcopy(next((c for c in clips if time < c['end']), clips[-1]))


def _validate_settings(settings):
    if not isinstance(settings, dict):
        _fail('settings_invalid', field='settings')
    for key in ('fade_out_sec', 'min_pause_sec', 'action_offset_sec', 'audio_lead_sec',
                'duck_ramp_sec', 'duck_silence_gap_sec', 'cut_fade_sec', 'song_entry_after_sec'):
        _number(settings.get(key), 'settings_invalid', key, positive=True)
    db = _number(settings.get('duck_db'), 'settings_invalid', 'duck_db', minimum=-math.inf)
    if db > 0:
        _fail('settings_invalid', field='duck_db')
    for key, minimum in (('swap_min_shot_index', 2), ('bed_min_clips', 3)):
        if type(settings.get(key)) is not int or settings[key] < minimum:
            _fail('settings_invalid', field=key)


def _validate_preset(preset):
    if not isinstance(preset, dict):
        _fail('preset_invalid', field='preset')
    for key in ('id', 'name', 'category', 'description'):
        _identity(preset.get(key), 'preset_invalid', key)
    density = preset.get('beats_per_cut')
    if not isinstance(density, dict) or set(density) != SECTION_KINDS or any(
            type(n) is not int or n <= 0 for n in density.values()):
        _fail('preset_invalid', field='beats_per_cut')
    tech = preset.get('techniques')
    if (not isinstance(tech, list) or any(t not in TECHNIQUES for t in tech) or
            len(set(tech)) != len(tech) or preset.get('order') not in ('story', 'sports', 'selfie')):
        _fail('preset_invalid', field='techniques_or_order')


def _validate_shots(shots, hook_ids):
    if not isinstance(shots, list) or not shots:
        _fail('shots_invalid', field='shots')
    seen = set()
    for s in shots:
        if not isinstance(s, dict):
            _fail('shots_invalid', field='shot')
        sid = _identity(s.get('id'), 'shots_invalid', 'id')
        _identity(s.get('scene'), 'shots_invalid', 'scene')
        if sid in seen or s.get('kind') not in ('video', 'photo'):
            _fail('shots_invalid', field='id_or_kind')
        seen.add(sid)
        if 'media_id' in s:
            _identity(s['media_id'], 'shots_invalid', 'media_id')
        for flag in ('has_audio', 'speaking'):
            if flag in s and type(s[flag]) is not bool:
                _fail('shots_invalid', field=flag)
        if s['kind'] == 'video':
            start = _number(s.get('start_sec'), 'shots_invalid', 'start_sec')
            end = _number(s.get('end_sec'), 'shots_invalid', 'end_sec')
            if end <= start:
                _fail('shots_invalid', field='source_range')
        metrics = s.get('metrics', {})
        if not isinstance(metrics, dict):
            _fail('shots_invalid', field='metrics')
        if metrics.get('motion_peak_time_sec') is not None:
            _number(metrics['motion_peak_time_sec'], 'shots_invalid', 'motion_peak_time_sec')
    if (not isinstance(hook_ids, (list, tuple)) or any(not isinstance(h,str) or h not in seen for h in hook_ids) or
            len(set(hook_ids)) != len(hook_ids)):
        _fail('shots_invalid', field='hook_ids')


def _validate_beat_map(beat, track_id):
    code = 'beat_map_invalid'
    if not isinstance(beat, dict) or beat.get('track_id') != track_id:
        _fail(code, field='track_id')
    _identity(beat.get('title'), code, 'title')
    duration = _number(beat.get('duration_seconds'), code, 'duration_seconds', positive=True)
    _number(beat.get('bpm'), code, 'bpm', positive=True)
    if type(beat.get('meter')) is not int or beat['meter'] <= 0 or type(beat.get('registry_version')) is not int or beat['registry_version'] < 1:
        _fail(code, field='meter_or_registry_version')
    for key in ('beats', 'downbeats'):
        times = beat.get(key)
        if not isinstance(times, list) or not times:
            _fail(code, field=key)
        previous = -1
        for value in times:
            value = _number(value, code, key)
            if value <= previous or value > duration:
                _fail(code, field=key)
            previous = value
    grid = set(beat['beats'])
    if any(t not in grid for t in beat['downbeats']):
        _fail(code, field='downbeats')
    energy = beat.get('beat_energy')
    if not isinstance(energy, list) or len(energy) != len(grid):
        _fail(code, field='beat_energy')
    for n in energy:
        if _number(n, code, 'beat_energy') > 1:
            _fail(code, field='beat_energy')
    sections = beat.get('sections')
    if not isinstance(sections, list) or not sections:
        _fail(code, field='sections')
    end = 0
    for section in sections:
        if not isinstance(section, dict) or section.get('kind') not in tuple(SECTION_KINDS):
            _fail(code, field='section_kind')
        start = _number(section.get('start'), code, 'section_start')
        next_end = _number(section.get('end'), code, 'section_end')
        if abs(start-end) > EPS or next_end <= start:
            _fail(code, field='section_contiguity')
        end = next_end
    if abs(end-duration) > EPS:
        _fail(code, field='section_coverage')


def _transcript_segments(document):
    """Validate the whole document before exposing its individual word ranges."""
    code = 'transcript_invalid'
    if (not isinstance(document, dict) or document.get('status') not in ('ok', 'empty', 'pending') or
            document.get('precision') not in ('word', 'sentence', 'chunk') or
            type(document.get('auto_cut_allowed')) is not bool or not isinstance(document.get('segments'), list)):
        _fail(code, field='document')
    result, previous, word_segments = [], 0, 0
    for segment in document['segments']:
        if not isinstance(segment, dict) or segment.get('precision') not in ('word', 'sentence', 'chunk'):
            _fail(code, field='segment')
        start = _number(segment.get('start_sec'), code, 'segment_start')
        end = _number(segment.get('end_sec'), code, 'segment_end')
        if start < previous-EPS or end < start:
            _fail(code, field='segment_range')
        previous = end
        words = segment.get('words')
        if not isinstance(words, list) or (segment['precision'] == 'word' and not words):
            _fail(code, field='words')
        last = start
        for word in words:
            if not isinstance(word, dict):
                _fail(code, field='word')
            a = _number(word.get('start'), code, 'word_start')
            b = _number(word.get('end'), code, 'word_end')
            if a < last-EPS or b <= a or b > end+EPS:
                _fail(code, field='word_range')
            last = b
        if words and segment['precision'] == 'word':
            result.extend((word['start'], word['end']) for word in words)
            word_segments += 1
    if (document['status'] == 'ok' and document['precision'] == 'word' and document['auto_cut_allowed'] and
            (not result or word_segments != len(document['segments']))):
        _fail(code, field='word_precision_without_complete_words')
    if (document['status'] != 'ok' or document['precision'] != 'word' or not document['auto_cut_allowed'] or
            word_segments != len(document['segments']) or not result):
        return None
    return result


def _ordered(shots, preset, hooks):
    by_id = {s['id']: s for s in shots}
    rest = [s for s in shots if s['id'] not in hooks]
    travel = [s for s in rest if s['scene'] == 'travel']
    selfie = [s for s in rest if s['scene'] == 'selfie-moments']
    sports = [s for s in rest if s['scene'] == 'sports-meet']
    half = (len(selfie)+1)//2
    if preset['order'] == 'sports':
        middle = sports+travel+selfie
    elif preset['order'] == 'selfie':
        middle = selfie[:half]+travel+sports+selfie[half:]
    else:
        middle = travel+selfie[:half]+sports+selfie[half:]
    tail = [s for s in rest if s['scene'] == 'travel/raw-pending']
    known = {'travel', 'travel/raw-pending', 'selfie-moments', 'sports-meet'}
    return [by_id[h] for h in hooks]+middle+tail+[s for s in rest if s['scene'] not in known]


def _entry(beat, settings):
    for section in beat['sections']:
        if section['kind'] in ('build', 'peak') and section['start'] >= settings['song_entry_after_sec']:
            for downbeat in beat['downbeats']:
                if section['start'] <= downbeat < section['end']:
                    return downbeat
    _fail('song_entry_unavailable', track_id=beat['track_id'])


def _pause(shot, speech, target, settings):
    choices = [(end+start)/2 for (_, end), (start, _) in zip(speech, speech[1:])
               if start-end+EPS >= settings['min_pause_sec'] and
               end >= shot['start_sec'] and start <= shot['end_sec']]
    return min(choices, key=lambda t: (round(abs(t-target), 6), t)) if choices else None


def _occurrence(tech, identity, clips, at, end=None, **reason):
    return dict(id=f'{tech}:{identity}', technique=tech, shot_ids=[c['shot_id'] for c in clips],
                at=_q(at), end=_q(at if end is None else end), reason_data=reason)


def _layout(order, playlist, maps, preset, settings, speech, enabled, overrides, boundaries):
    clips, pauses, songs = [], [], []
    song_index, time = -1, 0.0
    switches = {boundary: i+1 for i, boundary in enumerate(boundaries)}
    for i, shot in enumerate(order):
        if i == 0 or i in switches:
            if songs:
                songs[-1]['end'] = time
            song_index = 0 if i == 0 else switches[i]
            instance = playlist[song_index]
            beat = maps[instance['track_id']]
            offset = 0 if i == 0 else _entry(beat, settings)
            songs.append(dict(id=instance['id'],track_id=instance['track_id'],title=beat['title'],
                              start=time,offset=offset,bpm=beat['bpm']))
        song = songs[-1]
        source_time = song['offset']+time-song['start']
        section = next((s for s in beat['sections'] if s['start'] <= source_time < s['end']), None)
        if section is None:
            _fail('song_too_short', track_id=beat['track_id'])
        count = preset['beats_per_cut'][section['kind']]
        begin = bisect_right(beat['beats'], source_time+EPS)
        upcoming = beat['beats'][begin:begin+count]
        if not upcoming:
            _fail('song_too_short', track_id=beat['track_id'])
        available = math.inf if shot['kind'] == 'photo' else shot['end_sec']-shot['start_sec']
        fitting = [t for t in upcoming if t-source_time <= available+EPS]
        if not fitting:
            _fail('shot_too_short', shot_id=shot['id'])
        end = _q(song['start']+fitting[-1]-song['offset'])
        if end <= time:
            _fail('shot_too_short', shot_id=shot['id'])
        clip = dict(shot_id=shot['id'],media_id=shot.get('media_id',shot['id']),kind=shot['kind'],
                    scene=shot['scene'],scene_group=_scene(shot['scene']),index=i+1,start=time,cut_end=end,
                    end=end,source_start=shot.get('start_sec',0) if shot['kind']=='video' else None,
                    song_id=song['id'],section_kind=section['kind'],cut_kind='beat')
        segments = speech.get(clip['media_id'])
        if (enabled['pause'] and clip['scene_group']=='selfie-moments' and clip['kind']=='video' and
                shot.get('speaking') is not False and segments and i < len(order)-1):
            point = _pause(shot, segments, shot['start_sec']+end-time, settings)
            on_swap = i+1 in switches
            if point is not None and (not on_swap or abs(point-shot['start_sec']-(end-time)) <= EPS):
                occurrence = _occurrence('pause',_token(shot['id']),[clip],end,source_pause_sec=_q(point))
                if overrides.get(occurrence['id']) is not False:
                    clip['cut_end'] = clip['end'] = _q(time+point-shot['start_sec'])
                    clip['cut_kind'] = 'pause'
                occurrence['at'] = occurrence['end'] = clip['cut_end']
                pauses.append(occurrence)
        clips.append(clip)
        time = clip['cut_end']
    total = _q(time+settings['fade_out_sec'])
    clips[-1]['end'] = total
    songs[-1]['end'] = total
    for song in songs:
        if song['offset']+song['end']-song['start'] > maps[song['track_id']]['duration_seconds']+EPS:
            _fail('song_too_short', track_id=song['track_id'])
    return clips, pauses, songs, total


def _audio_feasibility(shots, *, handle_ok=True):
    if any(s.get('has_audio') is False for s in shots):
        return {'status':'unavailable','reason':'audio_stream_missing'}
    if not handle_ok:
        return {'status':'unavailable','reason':'audio_handle_invalid'}
    if any('has_audio' not in s for s in shots):
        return {'status':'unknown','reason':'audio_stream_unverified'}
    return {'status':'available','reason':None}


def _duck_regions(clip, words, songs, settings):
    speech = []
    for a,b in words:
        # Group before clipping: a short pause keeps music down even at a clip edge.
        if speech and a-speech[-1][1]+EPS < settings['duck_silence_gap_sec']:
            speech[-1] = (speech[-1][0], b)
        else:
            speech.append((a,b))
    spans = []
    for a,b in speech:
        lo = max(clip['source_start'],a)
        hi = min(clip['source_end'],b)
        if hi > lo:
            spans.append((clip['start']+lo-clip['source_start'],clip['start']+hi-clip['source_start']))
    regions = []
    for song in songs:
        merged = []
        for a,b in spans:
            a,b = max(a,song['start']),min(b,song['end'])
            if b <= a:
                continue
            if merged and a-merged[-1][1] <= 2*settings['duck_ramp_sec']+EPS:
                merged[-1] = (merged[-1][0], max(merged[-1][1],b))
            else:
                merged.append((a,b))
        for a,b in merged:
            regions.append(dict(song_id=song['id'],start=_q(a),end=_q(b),
                                gain=10**(settings['duck_db']/20),
                                ramp_sec=_q(max(0,min(settings['duck_ramp_sec'],a-song['start'],song['end']-b)))))
    return regions


def _decorate(clips, pauses, songs, order, speech, enabled, overrides, settings):
    occurrences = list(pauses)
    short_beds = []
    paused = {o['shot_ids'][0] for o in pauses if overrides.get(o['id']) is not False}
    for clip,shot in zip(clips,order):
        duration = _q(clip['end']-clip['start'])
        clip['duration'] = duration
        if clip['kind'] == 'photo':
            clip['source_end'] = None
            continue
        lo,hi = shot['start_sec'],shot['end_sec']
        cut_duration = clip['cut_end']-clip['start']
        peak = shot.get('metrics',{}).get('motion_peak_time_sec')
        action = None
        if enabled['action'] and clip['scene_group']=='sports-meet' and peak is not None and shot['id'] not in paused:
            wanted = _q(peak+settings['action_offset_sec']-cut_duration)
            if lo-EPS <= wanted <= hi-cut_duration+EPS:
                action = _occurrence('action',_token(shot['id']),[clip],clip['cut_end'],peak_sec=peak,source_in_sec=wanted)
                if overrides.get(action['id']) is not False:
                    clip['source_start'] = max(lo,wanted)
        if duration > hi-lo+EPS:
            _fail('shot_too_short', shot_id=shot['id'])
        # Retain motion/source intent while fitting the actual, extended final image.
        clip['source_start'] = _q(max(lo,min(clip['source_start'],hi-duration)))
        clip['source_end'] = _q(clip['source_start']+duration)
        if action and action['reason_data']['source_in_sec']+duration <= hi+EPS:
            occurrences.append(action)
    for i,clip in enumerate(clips):
        if enabled['jcut'] and i and clip['kind']=='video' and clip['scene_group'] in ('sports-meet','selfie-moments') and clip['scene_group']!=clips[i-1]['scene_group']:
            occurrence = _occurrence('jcut',f"{_token(clips[i-1]['shot_id'])}>{_token(clip['shot_id'])}",[clips[i-1],clip],clip['start'],
                                     lead_sec=settings['audio_lead_sec'])
            occurrence['audio_feasibility'] = _audio_feasibility([order[i]],handle_ok=clip['source_start'] >= settings['audio_lead_sec']-EPS)
            occurrences.append(occurrence)
        if enabled['duck'] and clip['kind']=='video' and clip['scene_group']=='selfie-moments' and order[i].get('speaking') is not False:
            segments = speech.get(clip['media_id'])
            if segments:
                regions = _duck_regions(clip,segments,songs,settings)
                if regions:
                    occurrence = _occurrence('duck',_token(clip['shot_id']),[clip],regions[0]['start'],regions[-1]['end'],regions=regions)
                    occurrence['audio_feasibility'] = _audio_feasibility([order[i]])
                    occurrences.append(occurrence)
    if enabled['bed']:
        run = []
        def flush():
            if len(run) < settings['bed_min_clips']:
                return
            identity = f"bed:{_token(run[0]['shot_id'])}"
            rows = {s['id']:s for s in order}
            source = max(run,key=lambda c: rows[c['shot_id']]['end_sec']-rows[c['shot_id']]['start_sec'])
            shot = rows[source['shot_id']]
            span = run[-1]['end']-run[0]['start']
            available = shot['end_sec']-shot['start_sec']
            if span > available+EPS:
                short_beds.append(dict(id=identity,code='bed_source_too_short',
                                       shot_ids=[c['shot_id'] for c in run],
                                       source_shot_id=shot['id'],at=run[0]['start'],end=run[-1]['end'],
                                       required_sec=_q(span),available_sec=_q(available)))
                return
            occurrence = _occurrence('bed',_token(run[0]['shot_id']),run,run[0]['start'],run[-1]['end'],
                                     source_shot_id=source['shot_id'],source_start_sec=shot['start_sec'])
            occurrence['audio_feasibility'] = _audio_feasibility([shot])
            occurrences.append(occurrence)
        for clip in clips:
            if clip['kind']=='video' and clip['scene_group']=='sports-meet':
                run.append(clip)
            else:
                flush()
                run = []
        flush()
    return occurrences, short_beds


def plan_roughcut(*, shots, beat_maps, playlist, preset, settings, transcripts=None,
                  technique_overrides=None, occurrence_overrides=None, swap_positions=None, hook_ids=()):
    """Compile supplied facts into a new plan, or raise without mutating any input."""
    _validate_settings(settings)
    _validate_preset(preset)
    _validate_shots(shots,hook_ids)
    if not isinstance(playlist,list) or not 1 <= len(playlist) <= 3:
        _fail('playlist_invalid',field='playlist')
    ids = set()
    if not isinstance(beat_maps,dict):
        _fail('beat_map_invalid',field='beat_maps')
    for entry in playlist:
        if not isinstance(entry,dict):
            _fail('playlist_invalid',field='entry')
        identity = _identity(entry.get('id'),'playlist_invalid','id')
        track = _identity(entry.get('track_id'),'playlist_invalid','track_id')
        if identity in ids:
            _fail('playlist_invalid',field='duplicate_instance')
        ids.add(identity)
        if track not in beat_maps:
            _fail('beat_map_missing',track_id=track)
        _validate_beat_map(beat_maps[track],track)
    technique_overrides = {} if technique_overrides is None else technique_overrides
    occurrence_overrides = {} if occurrence_overrides is None else occurrence_overrides
    for values,global_switch in ((technique_overrides,True),(occurrence_overrides,False)):
        if not isinstance(values,dict) or any(type(v) is not bool or not isinstance(k,str) or
                (k not in TECHNIQUES if global_switch else not any(k.startswith(t+':') for t in TECHNIQUES)) for k,v in values.items()):
            _fail('overrides_invalid',field='overrides')
    enabled = {t:technique_overrides.get(t,t in preset['techniques']) for t in TECHNIQUES}
    if transcripts is None:
        transcripts = {}
    if not isinstance(transcripts,dict):
        _fail('transcript_invalid',field='transcripts')
    speech = {}
    for media_id in {s.get('media_id',s['id']) for s in shots if s['kind']=='video'}:
        speech[media_id] = _transcript_segments(transcripts[media_id]) if media_id in transcripts else None
    order = _ordered(shots,preset,hook_ids)
    bounds = [i for i in range(settings['swap_min_shot_index']-1,len(order))
              if _scene(order[i]['scene'])!=_scene(order[i-1]['scene'])]
    positions = {} if swap_positions is None else swap_positions
    if not isinstance(positions,dict) or any(k not in {p['id'] for p in playlist[1:]} for k in positions):
        _fail('swap_boundary_invalid',field='swap_positions')
    by_shot = {s['id']:i for i,s in enumerate(order)}
    fixed = {}
    for k,v in positions.items():
        if not isinstance(v,str) or by_shot.get(v) not in bounds:
            _fail('swap_boundary_invalid',song_id=k)
        fixed[k] = by_shot[v]
    best, best_score, first_error = None,None,None
    for choice in combinations(bounds,len(playlist)-1):
        if any(choice[i]!=fixed[p['id']] for i,p in enumerate(playlist[1:]) if p['id'] in fixed):
            continue
        try:
            candidate = _layout(order,playlist,beat_maps,preset,settings,speech,enabled,occurrence_overrides,choice)
        except PlannerError as error:
            if first_error is None:
                first_error = error
            continue
        clips,_,_,total = candidate
        score = ()
        if choice:
            first = choice[0]
            score = (0 if _scene(order[first]['scene'])=='sports-meet' else 1,
                     _q(abs(clips[first]['start']-total/2)),clips[first]['start'])
            if len(choice)>1:
                score += (_q(abs(clips[choice[1]]['start']-(clips[first]['start']+total)/2)),clips[choice[1]]['start'])
        if best_score is None or score < best_score:
            best,best_score = (candidate,choice),score
    if best is None:
        if first_error:
            raise first_error
        _fail('swap_boundary_invalid',field='ordered_boundaries')
    (clips,pauses,songs,total),choice = best
    occurrences, short_beds = _decorate(clips,pauses,songs,order,speech,enabled,occurrence_overrides,settings)
    occurrences.sort(key=lambda o:(o['at'],TECHNIQUES.index(o['technique']),o['id']))
    totals = Counter(o['technique'] for o in occurrences)
    numbers = Counter()
    for o in occurrences:
        o['skipped'] = occurrence_overrides.get(o['id']) is False
        o['live'] = enabled[o['technique']] and not o['skipped']
        numbers[o['technique']] += 1
        o.update(index=numbers[o['technique']],total=totals[o['technique']],
                 position=timeline_position(o['at'],total),end_position=timeline_position(o['end'],total))
        o.setdefault('audio_feasibility',{'status':'not_applicable','reason':None})
    counts = Counter(o['technique'] for o in occurrences if o['live'])
    techniques = [dict(id=t,enabled=enabled[t],count=counts[t],total=totals[t],
                       status='active' if enabled[t] else 'off' if t in preset['techniques'] or t in technique_overrides else 'unused')
                  for t in TECHNIQUES]
    cuts = [dict(shot_id=c['shot_id'],t=c['cut_end'],kind=c['cut_kind'],position=timeline_position(c['cut_end'],total)) for c in clips]
    candidates = [dict(before_shot_id=order[i]['id'],previous_shot_id=order[i-1]['id'],
                       from_scene=_scene(order[i-1]['scene']),to_scene=_scene(order[i]['scene']),at=clips[i]['start']) for i in bounds]
    swaps = []
    for i,index in enumerate(choice):
        a,b = songs[i],songs[i+1]
        delta = int(_rounded(b['bpm'])-_rounded(a['bpm']))
        alternatives = [deepcopy(c) for c in candidates if c['before_shot_id']!=order[index]['id'] and
                        (i==0 or by_shot[c['before_shot_id']]>choice[i-1]) and
                        (i==len(choice)-1 or by_shot[c['before_shot_id']]<choice[i+1])]
        swaps.append(dict(id=f"swap:{_token(a['id'])}>{_token(b['id'])}",index=i+1,song_id=b['id'],before_shot_id=order[index]['id'],
                          at=clips[index]['start'],bpm_delta=delta,speed_relation='faster' if delta>0 else 'slower' if delta<0 else 'same',
                          alternatives=alternatives))
    for s in songs:
        s.update(position=timeline_position(s['start'],total),end_position=timeline_position(s['end'],total))
    mapped_sections,mapped_downbeats = [],[]
    for s in songs:
        beat = beat_maps[s['track_id']]
        for section in beat['sections']:
            start = max(s['start'],s['start']+section['start']-s['offset'])
            end = min(s['end'],s['start']+section['end']-s['offset'])
            if end>start:
                mapped_sections.append(dict(song_id=s['id'],kind=section['kind'],start=_q(start),end=_q(end)))
        for bar,t in enumerate(beat['downbeats'],1):
            at = _q(s['start']+t-s['offset'])
            if s['start'] <= at < s['end']:
                mapped_downbeats.append(dict(song_id=s['id'],bar=bar,t=at))
    missing = [s for s in shots if (enabled['pause'] or enabled['duck']) and s['scene']=='selfie-moments' and s['kind']=='video' and
               s.get('speaking') is not False and not speech.get(s.get('media_id',s['id']))]
    missing_by_technique = {
        t: dict(enabled=enabled[t],count=len(missing) if enabled[t] else 0,
                shot_ids=[s['id'] for s in missing] if enabled[t] else [],
                media_ids=sorted({s.get('media_id',s['id']) for s in missing}) if enabled[t] else [])
        for t in ('pause','duck')
    }
    found = {o['id'] for o in occurrences} | {b['id'] for b in short_beds}
    unlaid_beds = [b for b in short_beds if occurrence_overrides.get(b['id']) is not False]
    disabled = [t for t in preset['techniques'] if not enabled[t]]
    added = [t for t in TECHNIQUES if enabled[t] and t not in preset['techniques']]
    skipped = sorted(k for k,v in occurrence_overrides.items() if not v)
    return dict(schema_version='roughcut_plan_v1',preset_id=preset['id'],clips=clips,cuts=cuts,techniques=techniques,
                occurrences=occurrences,songs=songs,swaps=swaps,swap_candidates=candidates,
                mapped_sections=mapped_sections,mapped_downbeats=mapped_downbeats,
                metrics=dict(duration_sec=total,last_cut_sec=clips[-1]['cut_end'],fade_out_sec=settings['fade_out_sec'],
                             average_cut_sec=_rounded((total-settings['fade_out_sec'])/len(clips),1),shot_count=len(clips),
                             song_count=len(songs),used_technique_count=len(counts),occurrence_count=sum(counts.values()),
                             scene_counts=dict(Counter(_scene(s['scene']) for s in shots)),
                             preview_shot_ids=[clips[i]['shot_id'] for i in preview_indices(len(clips))]),
                warnings=dict(missing_word_shot_ids=[s['id'] for s in missing],
                              missing_word_media_ids=sorted({s.get('media_id',s['id']) for s in missing}),missing_word_count=len(missing),
                              missing_word_by_technique=missing_by_technique,
                              bed_short_count=len(unlaid_beds),bed_short_occurrences=unlaid_beds,
                              unmatched_override_ids=sorted(set(occurrence_overrides)-found),
                              audio_unverified_occurrence_ids=[o['id'] for o in occurrences if o['live'] and o['audio_feasibility']['status'] in ('unknown','unavailable')]),
                customization=dict(changed=bool(disabled or added or skipped),disabled=disabled,enabled=added,skipped_occurrence_ids=skipped),
                audio_settings=dict(cut_fade_sec=settings['cut_fade_sec'],duck_db=settings['duck_db']))
