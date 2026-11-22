"""One named test per DESIGN section 6 formula, plus its observable boundaries."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from roughcut_planner import clip_at, preset_counts, preview_indices, timeline_position
from tests.test_r226_planner import assert_code, case, plan, small


def multi(n=2):
    return case(playlist=[{'id':chr(97+i),'track_id':f'song-{chr(97+i)}'} for i in range(n)])


def test_F01_total_is_last_cut_plus_fade():
    result = plan(small(3))
    assert result['metrics']['last_cut_sec'] == 3
    assert result['metrics']['duration_sec'] == 4.6
    assert result['clips'][-1]['cut_end'] == 3
    assert result['clips'][-1]['end'] == result['songs'][-1]['end'] == 4.6


def test_F02_preset_duration_uses_its_own_plan():
    slow = small(3)
    fast = copy.deepcopy(slow)
    fast['preset']['beats_per_cut'] = dict(quiet=1,build=1,peak=1)
    assert plan(slow)['metrics']['duration_sec'] == 4.6
    assert plan(fast)['metrics']['duration_sec'] == 3.1


def test_F03_average_excludes_tail_and_rounds_one_decimal():
    assert plan(small(3))['metrics']['average_cut_sec'] == 1.0
    value = small(3)
    value['beat_maps']['song-a']['beats'] = [i*.25 for i in range(1200)]
    value['beat_maps']['song-a']['downbeats'] = [i for i in range(300)]
    value['beat_maps']['song-a']['beat_energy'] = [.5]*1200
    value['preset']['beats_per_cut'] = dict(quiet=1,build=1,peak=1)
    assert plan(value)['metrics']['average_cut_sec'] == .3


def test_F04_preview_six_indices_round_half_up():
    assert preview_indices(27) == [0,5,10,16,21,26]
    assert preview_indices(2) == [0,0,0,1,1,1]
    assert preview_indices(1) == [0]*6
    result = plan()
    assert result['metrics']['preview_shot_ids'] == [result['clips'][i]['shot_id'] for i in [0,5,10,16,21,26]]


def test_F05_library_totals_and_categories_include_mine():
    presets = json.loads((ROOT/'scripts/editing_presets.json').read_text())['presets']
    assert preset_counts(presets) == {'total':6,'categories':{'旅行':2,'运动':2,'日常':2}}
    mine = [dict(presets[0],id=f'mine-{i}',category='我的') for i in range(2)]
    assert preset_counts(presets+mine) == {'total':8,'categories':{'旅行':2,'运动':2,'日常':2,'我的':2}}
    assert preset_counts([]) == {'total':0,'categories':{}}


def test_F06_used_techniques_require_enabled_live_occurrence():
    value = small(2,['travel','selfie-moments'],['jcut','pause'])
    assert plan(value)['metrics']['used_technique_count'] == 1
    assert plan(value,occurrence_overrides={'jcut:s0>s1':False})['metrics']['used_technique_count'] == 0


def test_F07_total_occurrences_sums_live_only_and_excludes_swaps():
    value = small(4,['travel','selfie-moments','travel','selfie-moments'],['jcut'])
    assert plan(value)['metrics']['occurrence_count'] == 2
    assert plan(value,occurrence_overrides={'jcut:s0>s1':False})['metrics']['occurrence_count'] == 1
    result = plan(multi())
    assert result['metrics']['occurrence_count'] == len([o for o in result['occurrences'] if o['live']])
    assert all(o['technique']!='swap' for o in result['occurrences'])


def test_F08_row_counts_distinguish_off_unused_and_enabled_zero():
    result = plan(small(3,techniques=['pause']),technique_overrides={'jcut':False})
    rows = {row['id']:row for row in result['techniques']}
    assert rows['jcut']['status'] == 'off' and rows['jcut']['count']==0
    assert rows['bed']['status'] == 'unused'
    assert rows['pause']['status'] == 'active' and rows['pause']['count']==0


def test_F09_occurrence_navigation_keeps_skipped_in_denominator():
    result = plan(small(4,['travel','selfie-moments','travel','selfie-moments'],['jcut']),
                  occurrence_overrides={'jcut:s0>s1':False})
    assert [(o['index'],o['total'],o['live']) for o in result['occurrences']] == [(1,2,False),(2,2,True)]


def test_F10_current_clip_and_selected_cardinality():
    result = plan(small(3))
    assert clip_at(result,0)['index'] == 1
    assert clip_at(result,1)['index'] == 2
    assert clip_at(result,4.6)['index'] == 3
    assert clip_at(result,999)['index'] == 3
    assert result['metrics']['shot_count'] == 3
    assert plan()['metrics']['shot_count'] == 27


def test_F11_recommendation_counts_normalize_travel_group():
    assert plan()['metrics']['scene_counts'] == {'travel':14,'sports-meet':7,'selfie-moments':6}
    value = case()
    value['shots'][0]['scene'] = 'other'
    assert plan(value)['metrics']['scene_counts']['travel'] == 13


@pytest.mark.parametrize('pause,duck', [(True,True),(True,False),(False,True),(False,False)])
def test_F12_missing_word_count_depends_on_enabled_speech_techniques_and_shots(pause,duck):
    value = case()
    del value['transcripts']['media-selfie-04'],value['transcripts']['media-selfie-05']
    value['technique_overrides'] = {'pause':pause,'duck':duck}
    result = plan(value)
    expected = {'selfie-04','selfie-05'} if pause or duck else set()
    assert result['warnings']['missing_word_count'] == len(expected)
    assert set(result['warnings']['missing_word_shot_ids']) == expected
    for technique,enabled in (('pause',pause),('duck',duck)):
        warning = result['warnings']['missing_word_by_technique'][technique]
        assert warning['enabled'] is enabled
        assert warning['count'] == (2 if enabled else 0)
        assert set(warning['shot_ids']) == (expected if enabled else set())
        assert len(warning['media_ids']) == warning['count']
    assert not [o for o in result['occurrences'] if o['technique'] in ('pause','duck')
                and set(o['shot_ids']) & {'selfie-04','selfie-05'}]
    value['transcripts'] = {}
    value['shots'][-1]['media_id'] = value['shots'][-2]['media_id']
    result = plan(value)
    assert result['warnings']['missing_word_count'] == (6 if pause or duck else 0)
    assert len(result['warnings']['missing_word_media_ids']) == (5 if pause or duck else 0)
    rows = {r['id']:r for r in result['techniques']}
    assert rows['pause']['count'] == rows['duck']['count'] == 0
    assert not [o for o in result['occurrences'] if o['technique'] in ('pause','duck')]


@pytest.mark.parametrize('precision,allowed,missing', [
    ('word', True, 0), ('word', False, 1), ('chunk', True, 1), ('chunk', False, 1),
])
def test_F12_word_readiness_uses_trusted_words_not_pause_or_segment_counts(precision, allowed, missing):
    from tests.test_r226_planner import word_document

    value = small(2, ['selfie-moments', 'travel'], ['pause', 'duck'])
    # One word has no internal pause, but is still valid word evidence for duck.
    doc = word_document([(1, 4)])
    doc.update(precision=precision, auto_cut_allowed=allowed)
    if precision == 'chunk':
        doc['segments'][0]['precision'] = 'chunk'
    value['transcripts'] = {'m0': doc}
    result = plan(value)
    assert result['warnings']['missing_word_count'] == missing
    for technique in ('pause', 'duck'):
        assert result['warnings']['missing_word_by_technique'][technique]['count'] == missing
    rows = {r['id']: r for r in result['techniques']}
    assert rows['pause']['count'] == 0
    assert rows['duck']['count'] == 1-missing


def test_F12_trusted_words_outside_clip_do_not_invent_duck_or_missing_evidence():
    from tests.test_r226_planner import word_document

    value = small(2, ['selfie-moments', 'travel'], ['duck'])
    value['transcripts'] = {'m0': word_document([(0, .5), (3, 4)])}
    result = plan(value)
    assert result['warnings']['missing_word_count'] == 0
    assert result['warnings']['missing_word_by_technique']['duck']['count'] == 0
    assert not result['occurrences']
    assert next(r for r in result['techniques'] if r['id'] == 'duck')['count'] == 0


@pytest.mark.parametrize('count',[1,2,3])
def test_F13_song_count_is_logical_playlist_length(count):
    assert plan(multi(count))['metrics']['song_count'] == count


def test_F14_song_ranges_are_contiguous_to_total():
    for count in (1,2,3):
        result = plan(multi(count))
        songs = result['songs']
        assert songs[0]['start'] == 0
        assert songs[-1]['end'] == result['metrics']['duration_sec']
        assert all(a['end']==b['start'] for a,b in zip(songs,songs[1:]))


def test_F15_swap_is_new_clip_start_on_previous_song_beat():
    value = multi(3)
    result = plan(value)
    for i,swap in enumerate(result['swaps']):
        clip = next(c for c in result['clips'] if c['shot_id']==swap['before_shot_id'])
        song = result['songs'][i]
        assert swap['at'] == clip['start'] == song['end']
        source = song['offset']+swap['at']-song['start']
        assert min(abs(source-b) for b in value['beat_maps'][song['track_id']]['beats']) < 1e-6


@pytest.mark.parametrize('a,b,delta,relation',[(120.49,120.5,1,'faster'),(125.1,120.9,-4,'slower'),(120.1,120.4,0,'same')])
def test_F16_bpm_delta_uses_independent_rounding(a,b,delta,relation):
    value = multi()
    value['beat_maps']['song-a']['bpm'] = a
    value['beat_maps']['song-b']['bpm'] = b
    swap = plan(value)['swaps'][0]
    assert (swap['bpm_delta'],swap['speed_relation']) == (delta,relation)


def test_F17_swap_choices_are_post_six_scene_boundaries():
    result = plan(multi())
    clips = result['clips']
    expected = {c['shot_id'] for i,c in enumerate(clips) if i>=6 and c['scene_group']!=clips[i-1]['scene_group']}
    swap = result['swaps'][0]
    assert {c['before_shot_id'] for c in swap['alternatives']} == expected-{swap['before_shot_id']}
    assert {c['before_shot_id'] for c in result['swap_candidates']} == expected


def test_F18_timeline_positions_share_total_denominator():
    result = plan(multi())
    total = result['metrics']['duration_sec']
    for item in result['cuts']+result['occurrences']:
        t = item.get('t',item.get('at'))
        assert item['position'] == pytest.approx(t/total)
    assert timeline_position(0,total) == 0
    assert timeline_position(total,total) == 1
    assert timeline_position(-1,total) == 0
    assert timeline_position(total+1,total) == 1


def test_F19_cut_density_follows_active_song_section_and_source_length():
    value = small(3)
    value['preset']['beats_per_cut'] = dict(quiet=8,build=4,peak=2)
    value['beat_maps']['song-a']['sections'] = [{'start':0,'end':1,'kind':'quiet'}, {'start':1,'end':300,'kind':'build'}]
    result = plan(value)
    assert [c['cut_end']-c['start'] for c in result['clips'][:2]] == [4,2]
    value['shots'][0]['end_sec'] = 2.2
    assert plan(value)['clips'][0]['cut_end'] == 1
    value['shots'][0]['end_sec'] = 1.1
    assert_code('shot_too_short',value)


def test_F20_later_song_enters_first_eligible_section_bar():
    value = multi()
    result = plan(value)
    assert result['songs'][1]['offset'] == 32.64
    assert result['songs'][1]['offset'] in value['beat_maps']['song-b']['downbeats']


def test_F21_default_swap_prefers_sports_then_actual_time_middle():
    result = plan(multi())
    assert next(c for c in result['clips'] if c['shot_id']==result['swaps'][0]['before_shot_id'])['scene_group']=='sports-meet'
    value = small(18,['travel']*6+['other-a']*3+['other-b']*6+['other-c']*3)
    value['playlist'].append({'id':'b','track_id':'song-b'})
    for beat in value['beat_maps'].values():
        beat['sections'] = [{'start':0,'end':12,'kind':'quiet'},{'start':12,'end':300,'kind':'build'}]
    value['preset']['beats_per_cut'] = dict(quiet=4,build=1,peak=1)
    assert plan(value)['swaps'][0]['before_shot_id'] == 's6'


def test_F22_action_peak_ends_quarter_second_before_cut():
    value = small(2,['sports-meet','travel'],['action'])
    value['shots'][0]['metrics']['motion_peak_time_sec'] = 3
    result = plan(value)
    assert result['clips'][0]['source_start'] == 2.25
    assert result['occurrences'][0]['at'] == 1
    value['shots'][0]['metrics']['motion_peak_time_sec'] = 1.1
    assert not plan(value)['occurrences']


def test_F23_audio_lead_candidates_only_on_target_video_boundary():
    value = small(5,['travel','sports-meet','selfie-moments','travel','selfie-moments'],['jcut'])
    value['shots'][2]['kind'] = 'photo'
    occurrences = plan(value)['occurrences']
    assert [o['id'] for o in occurrences] == ['jcut:s0>s1','jcut:s3>s4']
    assert all(o['reason_data']['lead_sec']==.5 for o in occurrences)


def test_F24_continuous_sports_bed_threshold_and_longest_source():
    value = small(4,['sports-meet']*3+['travel'],['bed'])
    value['shots'][1]['end_sec'] = 91
    result = plan(value)
    bed = result['occurrences'][0]
    assert bed['id'] == 'bed:s0'
    assert bed['reason_data']['source_shot_id'] == 's1'
    assert (bed['at'],bed['end']) == (0,3)
    assert result['warnings']['bed_short_count'] == 0
    for shot in value['shots'][:3]:
        shot['end_sec'] = 2
    result = plan(value)
    assert not result['occurrences']
    assert result['metrics']['occurrence_count'] == result['metrics']['used_technique_count'] == 0
    row = next(r for r in result['techniques'] if r['id']=='bed')
    assert row['count'] == row['total'] == 0
    assert result['warnings']['bed_short_count'] == 1
    assert result['warnings']['bed_short_occurrences'] == [{
        'id':'bed:s0','code':'bed_source_too_short','shot_ids':['s0','s1','s2'],
        'source_shot_id':'s0','at':0,'end':3,'required_sec':3,'available_sec':1,
    }]
    value['shots'][2]['scene'] = 'travel'
    result = plan(value)
    assert not result['occurrences'] and result['warnings']['bed_short_count'] == 0
