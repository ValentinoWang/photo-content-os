"""Synthetic domain inputs; no Studio, media analysis or editor execution."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from creative.roughcut_planner import PlannerError, plan_roughcut


def case(preset_id='trip', **changes):
    fixture = json.loads((ROOT / 'tests/fixtures/r226-editing-techniques/synthetic.json').read_text())
    config = json.loads((ROOT / 'scripts/editing_presets.json').read_text())
    value = {key: fixture[key] for key in ('shots', 'beat_maps', 'transcripts')}
    value.update(playlist=[{'id': 'a', 'track_id': 'song-a'}],
                 preset=next(p for p in config['presets'] if p['id'] == preset_id), settings=config['settings'])
    value.update(changes)
    return value


def small(count=4, scenes=None, techniques=()):
    value = case()
    value['shots'] = [dict(id=f's{i}', media_id=f'm{i}', kind='video', scene=(scenes or ['travel']*count)[i],
                           start_sec=1, end_sec=61, has_audio=True, metrics={}) for i in range(count)]
    value['hook_ids'] = [s['id'] for s in value['shots']]
    value['transcripts'] = {}
    value['preset'].update(beats_per_cut=dict(quiet=2, build=2, peak=2), techniques=list(techniques))
    return value


def plan(value=None, **changes):
    value = copy.deepcopy(value if value is not None else case())
    value.update(changes)
    return plan_roughcut(**value)


def assert_code(code, value):
    with pytest.raises(PlannerError) as error:
        plan(value)
    assert error.value.code == code
    assert isinstance(error.value.details, dict)


def test_plan_is_deterministic_pure_and_keeps_every_selected_shot(monkeypatch):
    value = case()
    before = copy.deepcopy(value)
    first = plan_roughcut(**value)
    assert value == before
    assert first == plan_roughcut(**value)
    assert sorted(c['shot_id'] for c in first['clips']) == sorted(s['id'] for s in value['shots'])
    monkeypatch.setattr('builtins.open', lambda *a, **k: pytest.fail('planner attempted IO'))
    assert first == plan_roughcut(**value)


@pytest.mark.parametrize('order', ['story', 'sports', 'selfie'])
def test_unknown_scenes_and_explicit_hooks_are_never_dropped(order):
    value = small(5, ['unknown-a','travel','selfie-moments','sports-meet','unknown-b'])
    value['preset']['order'] = order
    value['hook_ids'] = ['s3']
    result = plan(value)
    assert result['clips'][0]['shot_id'] == 's3'
    assert {c['shot_id'] for c in result['clips']} == {f's{i}' for i in range(5)}


@pytest.mark.parametrize('change', ['empty','duplicate','negative','nan','reverse','kind','audio_type','peak','hooks'])
def test_invalid_shots_are_rejected(change):
    value = small()
    if change == 'empty': value['shots'] = []
    if change == 'duplicate': value['shots'][1]['id'] = 's0'
    if change == 'negative': value['shots'][0]['start_sec'] = -1
    if change == 'nan': value['shots'][0]['end_sec'] = float('nan')
    if change == 'reverse': value['shots'][0]['end_sec'] = 0
    if change == 'kind': value['shots'][0]['kind'] = 'audio'
    if change == 'audio_type': value['shots'][0]['has_audio'] = 'yes'
    if change == 'peak': value['shots'][0]['metrics']['motion_peak_time_sec'] = float('inf')
    if change == 'hooks': value['hook_ids'] = ['not-selected']
    assert_code('shots_invalid', value)


@pytest.mark.parametrize('change', ['empty','duplicate','nan','downbeat','energy','gap','coverage','kind','identity','bool_bpm'])
def test_invalid_beat_map_is_not_filled_or_treated_as_empty_music(change):
    value = small()
    beat = value['beat_maps']['song-a']
    if change == 'empty': beat['beats'] = []
    if change == 'duplicate': beat['beats'][1] = beat['beats'][0]
    if change == 'nan': beat['beats'][1] = float('nan')
    if change == 'downbeat': beat['downbeats'][1] = .123
    if change == 'energy': beat['beat_energy'] = []
    if change == 'gap': beat['sections'][1]['start'] += .1
    if change == 'coverage': beat['sections'][-1]['end'] -= 1
    if change == 'kind': beat['sections'][0]['kind'] = 'intro'
    if change == 'identity': beat['track_id'] = 'different'
    if change == 'bool_bpm': beat['bpm'] = True
    assert_code('beat_map_invalid', value)


def test_missing_map_is_distinct_from_invalid_map():
    value = small()
    del value['beat_maps']['song-a']
    assert_code('beat_map_missing', value)


@pytest.mark.parametrize('change,code', [('no_playlist','playlist_invalid'),('four','playlist_invalid'),('duplicate','playlist_invalid'),
                                      ('bad_technique','overrides_invalid'),('bad_bool','overrides_invalid'),
                                      ('bad_density','preset_invalid'),('bad_constant','settings_invalid')])
def test_invalid_recipe_playlist_and_overrides(change, code):
    value = small()
    if change == 'no_playlist': value['playlist'] = []
    if change == 'four': value['playlist'] *= 4
    if change == 'duplicate': value['playlist'] *= 2
    if change == 'bad_technique': value['technique_overrides'] = {'invented':True}
    if change == 'bad_bool': value['technique_overrides'] = {'jcut':1}
    if change == 'bad_density': value['preset']['beats_per_cut']['quiet'] = 0
    if change == 'bad_constant': value['settings']['min_pause_sec'] = None
    assert_code(code, value)


def test_video_tail_uses_room_then_moves_in_point_and_never_freezes():
    value = small(1)
    value['shots'][0]['end_sec'] = 3.6
    result = plan(value)
    assert result['clips'][0]['source_start'] == 1
    assert result['clips'][0]['source_end'] == 3.6
    value['shots'][0]['end_sec'] = 3.5
    assert_code('shot_too_short', value)
    value['shots'][0]['kind'] = 'photo'
    assert plan(value)['clips'][0]['end'] == 2.6


def test_disabled_occurrences_do_not_cause_bed_side_effects():
    value = small(4, ['sports-meet']*3+['travel'], ['bed'])
    value['shots'][-1]['kind'] = 'photo'
    for shot in value['shots'][:3]: shot['end_sec'] = 2
    result = plan(value)
    assert result['warnings']['bed_short_count'] == 1
    assert not result['occurrences']
    for changes in ({'occurrence_overrides':{'bed:s0':False}}, {'technique_overrides':{'bed':False}}):
        result = plan(value, **changes)
        assert result['metrics']['occurrence_count'] == 0
        assert result['warnings']['bed_short_count'] == 0
        assert result['warnings']['unmatched_override_ids'] == []


def test_pause_uses_word_boundaries_and_single_override_restores_beat():
    value = small(2, ['selfie-moments','travel'], ['pause','action'])
    value['transcripts'] = {'m0':case()['transcripts']['media-selfie-00']}
    result = plan(value)
    pause = next(o for o in result['occurrences'] if o['technique']=='pause')
    # Target source time=2; eligible gap centres=1.65,2.75,3.75,5.25,6.5.
    assert pause['reason_data']['source_pause_sec'] == 1.65
    assert result['clips'][0]['cut_end'] == .65
    # An explicit pause override must restore the original beat and persist its ID.
    off = plan(value, occurrence_overrides={pause['id']:False})
    assert off['clips'][0]['cut_end'] == 1
    assert next(o for o in off['occurrences'] if o['id']==pause['id'])['skipped']


def word_document(spans, *, separate_segments=False):
    """Synthetic acoustic units; segment boundaries carry no sentence meaning."""
    words = [dict(start=a, end=b, text='合成') for a, b in spans]
    groups = [[w] for w in words] if separate_segments else [words]
    return dict(status='ok', precision='word', auto_cut_allowed=True,
                segments=[dict(start_sec=g[0]['start'], end_sec=g[-1]['end'],
                               precision='word', words=g) for g in groups])


@pytest.mark.parametrize('separate_segments', [False, True])
@pytest.mark.parametrize('gap,expected', [(.249, None), (.25, 2), (.251, 2.0005)])
def test_pause_reads_intra_segment_word_gaps_at_quarter_second_threshold(separate_segments, gap, expected):
    value = small(2, ['selfie-moments', 'travel'], ['pause'])
    value['transcripts'] = {'m0': word_document([(1, 1.875), (1.875+gap, 3)],
                                               separate_segments=separate_segments)}
    result = plan(value)
    pauses = [o for o in result['occurrences'] if o['technique'] == 'pause']
    assert len(pauses) == (expected is not None)
    if expected is not None:
        assert pauses[0]['id'] == 'pause:s0'
        assert pauses[0]['reason_data']['source_pause_sec'] == expected
        assert result['clips'][0]['cut_end'] == pytest.approx(expected-1)
        assert result['clips'][1]['start'] == result['clips'][0]['cut_end']


@pytest.mark.parametrize('separate_segments', [False, True])
def test_word_pause_ties_choose_earlier_and_require_entire_gap_inside_shot(separate_segments):
    value = small(2, ['selfie-moments', 'travel'], ['pause'])
    value['transcripts'] = {'m0': word_document([(1, 1.5), (1.8, 2.2), (2.5, 3)],
                                               separate_segments=separate_segments)}
    assert plan(value)['occurrences'][0]['reason_data']['source_pause_sec'] == 1.65
    # Both midpoints are inside this source range, but both complete gaps are not.
    value['shots'][0].update(start_sec=1.6, end_sec=2.4)
    result = plan(value)
    assert not result['occurrences']
    assert result['cuts'][0]['kind'] == 'beat'


@pytest.mark.parametrize('separate_segments', [False, True])
@pytest.mark.parametrize('gap,split', [(.3, False), (.999, False), (1.0, True), (1.001, True)])
def test_duck_holds_short_word_pauses_and_breaks_at_one_second(separate_segments, gap, split):
    value = small(2, ['selfie-moments', 'travel'], ['duck'])
    value['preset']['beats_per_cut'] = dict(quiet=10, build=10, peak=10)
    value['transcripts'] = {'m0': word_document([(1, 1.5), (1.5+gap, 3.5)],
                                               separate_segments=separate_segments)}
    result = plan(value)
    duck = next(o for o in result['occurrences'] if o['technique'] == 'duck')
    regions = duck['reason_data']['regions']
    assert [(r['start'], r['end']) for r in regions] == (
        [(0, .5), (.5+gap, 2.5)] if split else [(0, 2.5)])
    assert duck['id'] == 'duck:s0' and duck['total'] == 1
    assert all(r['gain'] == pytest.approx(10**(-12/20)) for r in regions)


def test_duck_groups_words_before_clipping_and_does_not_fill_long_silence():
    value = small(2, ['selfie-moments', 'travel'], ['duck'])
    value['transcripts'] = {'m0': word_document([(0, .5), (1.2, 1.4), (2.4, 3)])}
    value['shots'][0]['start_sec'] = .75
    regions = plan(value)['occurrences'][0]['reason_data']['regions']
    assert [(r['start'], r['end']) for r in regions] == [(0, .65)]
    value['transcripts'] = {'m0': word_document([(0, .5), (2, 3)])}
    assert not plan(value)['occurrences']


def test_duck_gap_uses_explicit_configuration_and_preserves_segment_partition_invariance():
    value = small(2, ['selfie-moments', 'travel'], ['pause', 'duck'])
    spans = [(1, 1.5), (1.8, 2.2), (3.4, 4)]
    value['transcripts'] = {'m0': word_document(spans)}
    first = plan(value)
    value['transcripts'] = {'m0': word_document(spans, separate_segments=True)}
    assert plan(value) == first
    value['technique_overrides'] = {'pause': False}
    value['preset']['beats_per_cut'] = dict(quiet=10, build=10, peak=10)
    assert len(plan(value)['occurrences'][0]['reason_data']['regions']) == 2
    value['settings']['duck_silence_gap_sec'] = 2
    assert len(plan(value)['occurrences'][0]['reason_data']['regions']) == 1


@pytest.mark.parametrize('invalid', [None, 0, -1, True, float('nan'), float('inf'), '1.0'])
def test_duck_gap_configuration_rejects_invalid_values(invalid):
    value = small()
    value['settings']['duck_silence_gap_sec'] = invalid
    assert_code('settings_invalid', value)


def test_duck_gap_configuration_is_frozen_and_required():
    value = small()
    assert value['settings']['duck_silence_gap_sec'] == 1.0
    del value['settings']['duck_silence_gap_sec']
    assert_code('settings_invalid', value)


def test_too_short_gaps_sentence_precision_and_explicit_silence_do_not_invent_pauses():
    value = small(2, ['selfie-moments','travel'], ['pause','duck'])
    transcript = copy.deepcopy(case()['transcripts']['media-selfie-00'])
    transcript.update(precision='sentence', auto_cut_allowed=False)
    value['transcripts'] = {'m0':transcript}
    result = plan(value)
    assert not result['occurrences']
    assert result['warnings']['missing_word_count'] == 1
    value['shots'][0]['speaking'] = False
    assert plan(value)['warnings']['missing_word_count'] == 0


@pytest.mark.parametrize('change', ['word_outside','word_reversed','segment_overlap','bad_precision','not_document'])
def test_unreadable_transcript_never_becomes_missing_words(change):
    value = small(2, ['selfie-moments','travel'], ['pause'])
    doc = copy.deepcopy(case()['transcripts']['media-selfie-00'])
    if change == 'word_outside': doc['segments'][0]['words'][0]['end'] = 3
    if change == 'word_reversed': doc['segments'][0]['words'][0]['end'] = 0
    if change == 'segment_overlap': doc['segments'][1]['start_sec'] = 1.2
    if change == 'bad_precision': doc['precision'] = 'unknown'
    value['transcripts'] = {'m0':[] if change=='not_document' else doc}
    assert_code('transcript_invalid', value)


def test_duck_uses_real_speech_gain_ramps_and_splits_at_songs():
    result = plan()
    ducks = [o for o in result['occurrences'] if o['technique']=='duck' and o['live']]
    assert ducks
    for occurrence in ducks:
        for region in occurrence['reason_data']['regions']:
            assert region['gain'] == pytest.approx(10**(-12/20))
            song = next(s for s in result['songs'] if s['id']==region['song_id'])
            assert song['start'] <= region['start']-region['ramp_sec']+1e-6
            assert region['end']+region['ramp_sec'] <= song['end']+1e-6
    assert result['audio_settings']['cut_fade_sec'] == .03


def test_audio_unknown_and_explicit_no_audio_are_not_claimed_executable():
    value = small(2, ['travel','selfie-moments'], ['jcut'])
    del value['shots'][1]['has_audio']
    occurrence = plan(value)['occurrences'][0]
    assert occurrence['audio_feasibility']['status'] == 'unknown'
    value['shots'][1]['has_audio'] = False
    assert plan(value)['occurrences'][0]['audio_feasibility']['status'] == 'unavailable'
    value['shots'][1]['has_audio'] = True
    value['shots'][1]['start_sec'] = 0
    assert plan(value)['occurrences'][0]['audio_feasibility']['reason'] == 'audio_handle_invalid'


def test_stable_ids_survive_retiming_and_unknown_overrides_are_reported():
    value = small(3, ['travel','selfie-moments','travel'], ['jcut'])
    a = plan(value)
    value['preset']['beats_per_cut'] = dict(quiet=4,build=4,peak=4)
    b = plan(value, occurrence_overrides={'pause:retired-shot':False})
    assert a['occurrences'][0]['id'] == b['occurrences'][0]['id']
    assert a['occurrences'][0]['at'] != b['occurrences'][0]['at']
    assert b['warnings']['unmatched_override_ids'] == ['pause:retired-shot']


def test_explicit_bad_swap_never_silently_moves():
    value = case(playlist=[{'id':'a','track_id':'song-a'},{'id':'b','track_id':'song-b'}])
    for position in ['travel-01', 'does-not-exist']:
        assert_code('swap_boundary_invalid', {**value,'swap_positions':{'b':position}})
    assert_code('swap_boundary_invalid', {**value,'swap_positions':{'unknown':'selfie-00'}})


def test_later_song_without_entry_fails_and_song_exhaustion_is_distinct():
    value = case(playlist=[{'id':'a','track_id':'song-a'},{'id':'b','track_id':'song-b'}])
    value['beat_maps']['song-b']['sections'] = [{'start':0,'end':300,'kind':'quiet'}]
    assert_code('song_entry_unavailable', value)
    value = small(5)
    beat = value['beat_maps']['song-a']
    beat.update(duration_seconds=2, beats=[0,.5,1,1.5],downbeats=[0],beat_energy=[.5]*4,
                sections=[{'start':0,'end':2,'kind':'quiet'}])
    assert_code('song_too_short', value)


def test_same_song_instances_have_distinct_swap_and_song_identity():
    result = plan(case(playlist=[{'id':'a','track_id':'song-a'},{'id':'b','track_id':'song-a'}]))
    assert [s['id'] for s in result['songs']] == ['a','b']
    assert result['swaps'][0]['song_id'] == 'b'


def test_input_failure_preserves_previous_plan_and_input():
    value = case()
    previous = plan(value)
    frozen = copy.deepcopy(previous)
    value['shots'][-1]['end_sec'] = value['shots'][-1]['start_sec']+.1
    assert_code('shot_too_short', value)
    assert previous == frozen


def test_tail_moves_source_back_and_does_not_claim_invalid_action():
    value = small(2,['travel','sports-meet'],['action'])
    value['shots'][1].update(start_sec=1,end_sec=4,metrics={'motion_peak_time_sec':3})
    result = plan(value)
    last = result['clips'][-1]
    assert last['source_start'] == 1.4
    assert last['source_end'] == 4
    assert last['end'] == 3.6
    assert not [o for o in result['occurrences'] if o['technique']=='action']


def test_pause_minimum_and_equal_distance_tie_choose_earlier_gap():
    value = small(2,['selfie-moments','travel'],['pause'])
    doc = copy.deepcopy(case()['transcripts']['media-selfie-00'])
    doc['segments'] = [dict(start_sec=a,end_sec=b,precision='word',words=[dict(start=a,end=b,text='合成')])
                       for a,b in [(1,1.5),(1.8,2.2),(2.5,3)]]
    value['transcripts'] = {'m0':doc}
    # Gap centres 1.65 and 2.35 are equally distant from the source beat target 2.
    assert plan(value)['occurrences'][0]['reason_data']['source_pause_sec'] == 1.65
    doc['segments'] = [dict(start_sec=a,end_sec=b,precision='word',words=[dict(start=a,end=b,text='合成')])
                       for a,b in [(1,1.9),(2.1,3)]]
    assert not plan(value)['occurrences']


def test_multi_song_on_swap_disables_off_beat_pause_and_replans_later_clips():
    value = case(playlist=[{'id':'a','track_id':'song-a'},{'id':'b','track_id':'song-b'}],
                 swap_positions={'b':'sport-00'})
    result = plan(value)
    assert not [o for o in result['occurrences'] if o['id']=='pause:selfie-02']
    assert next(c for c in result['clips'] if c['shot_id']=='selfie-02')['cut_kind'] == 'beat'
    assert result['swaps'][0]['before_shot_id'] == 'sport-00'
    assert result['swaps'][0]['at'] in value['beat_maps']['song-a']['beats']


def test_change_song_remove_song_and_move_boundary_all_recompute():
    value = case(playlist=[{'id':'a','track_id':'song-a'},{'id':'b','track_id':'song-b'}])
    two = plan(value)
    option = two['swaps'][0]['alternatives'][0]['before_shot_id']
    moved = plan(value,swap_positions={'b':option})
    assert moved['swaps'][0]['before_shot_id'] == option
    assert moved['swaps'][0]['at'] != two['swaps'][0]['at']
    replacement = copy.deepcopy(value)
    replacement['playlist'][1]['track_id'] = 'song-c'
    assert plan(replacement)['songs'][1]['track_id'] == 'song-c'
    one = plan(value,playlist=value['playlist'][:1])
    assert len(one['songs'])==1 and not one['swaps']
    assert one['songs'][0]['end']==one['metrics']['duration_sec']


def test_long_film_can_switch_before_first_song_runs_out():
    value = small(18,['travel']*6+['other']*6+['last']*6)
    value['playlist'].append({'id':'b','track_id':'song-b'})
    beat = value['beat_maps']['song-a']
    beat.update(duration_seconds=10,beats=[i*.5 for i in range(20)],downbeats=[0,2,4,6,8],
                beat_energy=[.5]*20,sections=[{'start':0,'end':10,'kind':'quiet'}])
    result = plan(value)
    assert result['swaps'][0]['at'] == 6
    assert result['metrics']['duration_sec'] > 10


@pytest.mark.parametrize('change,code',[
    ('unhashable_hook','shots_invalid'),('unhashable_kind','beat_map_invalid'),
    ('unhashable_order','preset_invalid'),('unhashable_status','transcript_invalid'),
    ('empty_word_success','transcript_invalid')])
def test_malformed_values_always_have_contract_errors(change,code):
    value = small(2,['selfie-moments','travel'],['pause'])
    if change=='unhashable_hook': value['hook_ids'] = [[]]
    if change=='unhashable_kind': value['beat_maps']['song-a']['sections'][0]['kind'] = []
    if change=='unhashable_order': value['preset']['order'] = []
    if change in ('unhashable_status','empty_word_success'):
        doc = copy.deepcopy(case()['transcripts']['media-selfie-00'])
        if change=='unhashable_status': doc['status'] = []
        else: doc['segments'] = []
        value['transcripts'] = {'m0':doc}
    assert_code(code,value)


def test_stable_occurrence_ids_do_not_collide_on_reserved_characters():
    a = small(2,['travel','selfie-moments'],['jcut'])
    b = copy.deepcopy(a)
    a['shots'][0]['id'],a['shots'][1]['id'] = 'a>b','c'
    b['shots'][0]['id'],b['shots'][1]['id'] = 'a','b>c'
    a['hook_ids'] = [s['id'] for s in a['shots']]
    b['hook_ids'] = [s['id'] for s in b['shots']]
    assert plan(a)['occurrences'][0]['id'] != plan(b)['occurrences'][0]['id']


def test_every_cut_uses_current_song_grid_after_three_song_retiming():
    value = case(playlist=[{'id':'a','track_id':'song-a'}, {'id':'b','track_id':'song-b'}, {'id':'c','track_id':'song-c'}])
    result = plan(value)
    by_song = {s['id']:s for s in result['songs']}
    for clip in result['clips']:
        song = by_song[clip['song_id']]
        if clip['cut_kind']=='beat':
            source_time = song['offset']+clip['cut_end']-song['start']
            assert min(abs(t-source_time) for t in value['beat_maps'][song['track_id']]['beats']) < 1e-6
    assert all(s['end']>s['start'] for s in result['songs'])
    assert {r['song_id'] for o in result['occurrences'] if o['technique']=='duck'
            for r in o['reason_data']['regions']} >= {'a','b'}


def test_original_locators_and_unrelated_metadata_are_not_projected():
    value = small()
    for shot in value['shots']:
        shot.update(source_relative_path='synthetic-private-locator',model_reason='synthetic-private-prose')
    result = json.dumps(plan(value))
    assert 'synthetic-private-locator' not in result
    assert 'synthetic-private-prose' not in result


def test_source_motion_candidate_too_close_to_tail_is_not_clamped_into_a_false_occurrence():
    value = small(2,['sports-meet','travel'],['action'])
    value['shots'][0].update(start_sec=0,end_sec=4,metrics={'motion_peak_time_sec':3.9})
    assert not plan(value)['occurrences']


def test_no_legal_post_six_boundary_does_not_discard_second_song():
    value = small(10)
    value['playlist'].append({'id':'b','track_id':'song-b'})
    assert_code('swap_boundary_invalid',value)


@pytest.mark.parametrize('identity,name,category,density,techniques,order',[
    ('trip','轻快旅行','旅行',[8,4,2],['jcut','bed','duck','pause','action'],'story'),
    ('race','赛场热血','运动',[4,2,1],['jcut','bed','duck','action'],'sports'),
    ('calm','松弛日常','日常',[8,8,4],['bed','duck','pause'],'story'),
    ('walk','城市漫步','旅行',[8,4,4],['jcut','bed','duck'],'story'),
    ('beat','卡点快剪','运动',[2,2,1],['jcut','action'],'sports'),
    ('diary','自拍日记','日常',[8,4,4],['bed','duck','pause'],'selfie'),
])
def test_builtin_recipe_matches_approved_design(identity,name,category,density,techniques,order):
    preset = case(identity)['preset']
    assert (preset['name'],preset['category'],preset['order']) == (name,category,order)
    assert [preset['beats_per_cut'][kind] for kind in ('quiet','build','peak')] == density
    assert preset['techniques'] == techniques


@pytest.mark.parametrize('both_short,short_count,live_count', [(False,1,1),(True,2,0)])
def test_short_beds_are_separate_from_valid_occurrence_statistics(both_short,short_count,live_count):
    value = small(8,['sports-meet']*3+['travel']+['sports-meet']*3+['travel'],['bed'])
    for shot in value['shots'][:3]:
        shot['end_sec'] = 2
    if both_short:
        for shot in value['shots'][4:7]:
            shot['end_sec'] = 2
    before = copy.deepcopy(value)
    result = plan_roughcut(**value)
    assert value == before
    assert len(result['clips']) == 8
    assert result['warnings']['bed_short_count'] == short_count
    assert len(result['warnings']['bed_short_occurrences']) == short_count
    assert {o['id'] for o in result['warnings']['bed_short_occurrences']} == (
        {'bed:s0','bed:s4'} if both_short else {'bed:s0'})
    assert len(result['occurrences']) == result['metrics']['occurrence_count'] == live_count
    row = next(r for r in result['techniques'] if r['id']=='bed')
    assert row['total'] == row['count'] == live_count
    if live_count:
        assert [(o['id'],o['index'],o['total']) for o in result['occurrences']] == [('bed:s4',1,1)]


def test_short_bed_warning_clears_after_source_or_switch_change():
    value = small(4,['sports-meet']*3+['travel'],['bed'])
    for shot in value['shots'][:3]:
        shot['end_sec'] = 2
    before = plan(value)
    assert before['warnings']['bed_short_count'] == 1
    value['shots'][1]['end_sec'] = 10
    after = plan(value)
    assert after['warnings']['bed_short_count'] == 0
    assert after['warnings']['bed_short_occurrences'] == []
    assert [o['id'] for o in after['occurrences']] == ['bed:s0']
    assert after['cuts'] == before['cuts']
    skipped = plan(value,occurrence_overrides={'bed:s0':False})
    assert skipped['warnings']['bed_short_count'] == 0
    assert not skipped['occurrences'][0]['live'] and skipped['occurrences'][0]['total'] == 1


@pytest.mark.parametrize('techniques', [('pause',),('duck',),('pause','duck')])
@pytest.mark.parametrize('precision', ['absent','sentence','chunk'])
def test_missing_word_video_count_excludes_photos_and_does_not_invent_speech(techniques,precision):
    value = small(4,['selfie-moments']*3+['travel'],techniques)
    value['shots'][2]['kind'] = 'photo'
    if precision != 'absent':
        doc = copy.deepcopy(case()['transcripts']['media-selfie-00'])
        doc.update(precision=precision,auto_cut_allowed=False)
        value['transcripts'] = {'m0':doc,'m1':copy.deepcopy(doc)}
    result = plan(value)
    assert not result['occurrences']
    assert result['warnings']['missing_word_count'] == 2
    assert result['warnings']['missing_word_shot_ids'] == ['s0','s1']
    for technique in ('pause','duck'):
        details = result['warnings']['missing_word_by_technique'][technique]
        enabled = technique in techniques
        assert details == {'enabled':enabled,'count':2 if enabled else 0,
                           'shot_ids':['s0','s1'] if enabled else [],
                           'media_ids':['m0','m1'] if enabled else []}
    assert all(c['cut_kind']=='beat' for c in result['clips'])
