"""Section boundaries and short-run merging, using deterministic synthetic audio."""
import copy
import json
from pathlib import Path
import sys
import wave

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from music_analysis.worker import merge_short_sections, section_bars, section_map
from validate_music_analysis_registry import validate

RULES = {
    'levels': '按平滑后的小节能量在本曲内三等分',
    'smooth_bars': 4,
    'min_bars': 4,
    'merge': '先并最短的段，并入能量更接近的相邻段',
}


def assert_coverage(sections, downbeats, duration):
    assert sections and sections[0]['start'] == 0 and sections[-1]['end'] == duration
    assert all(s['kind'] in {'quiet', 'build', 'peak'} for s in sections)
    assert all(s['start'] < s['end'] for s in sections)
    assert all(a['end'] == b['start'] for a, b in zip(sections, sections[1:]))
    assert all(s['start'] == 0 or s['start'] in downbeats for s in sections)
    assert all(s['end'] == duration or s['end'] in downbeats for s in sections)


def test_synthetic_audio_preserves_four_energy_regions(tmp_path):
    sr = 8000
    bars = [.1] * 16 + [.9] * 16 + [.5] * 16 + [.9] * 16
    bar_seconds = 2
    samples = np.concatenate([amplitude * np.sin(2 * np.pi * 440 * np.arange(sr * bar_seconds) / sr)
                              for amplitude in bars])
    path = tmp_path / 'quiet-peak-build-peak.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, sr, 0, 'NONE', 'not compressed'))
        audio.writeframes((samples * 32767).astype('<i2').tobytes())
    with wave.open(str(path), 'rb') as audio:
        decoded = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').astype(float) / 32768
    rms = np.sqrt(np.mean(decoded.reshape(-1, sr // 2) ** 2, axis=1))
    low, high = np.quantile(rms, [.05, .95])
    energy = np.clip((rms - low) / (high - low), 0, 1).tolist()
    duration = len(bars) * bar_seconds
    beats = np.arange(0, duration, .5).tolist()
    downbeats = np.arange(0, duration, bar_seconds).tolist()
    sections = section_map(beats, downbeats, energy, duration, RULES)
    assert_coverage(sections, downbeats, duration)
    assert [s['kind'] for s in sections] == ['quiet', 'peak', 'build', 'peak']
    assert len(sections) == 4
    assert all(abs(section['start'] - target) <= bar_seconds
               for section, target in zip(sections[1:], [32, 64, 96]))


def test_alternating_bars_do_not_snowball_into_a_dominant_section():
    energy = [.2, .8] * 32
    beats = [float(i) for i in range(len(energy))]
    downbeats = list(beats)
    sections = section_map(beats, downbeats, energy, float(len(energy)), RULES)
    assert_coverage(sections, downbeats, len(energy))
    assert max(s['end'] - s['start'] for s in sections) <= .6 * len(energy)


@pytest.mark.parametrize('key', ['smooth_bars', 'min_bars'])
@pytest.mark.parametrize('value', [0, -1, 1.5, 4.0, True, '4', None])
def test_registry_rejects_invalid_bar_counts(key, value):
    registry = json.loads((ROOT / 'music-analysis.registry.json').read_text())
    registry['sections']['rules'][key] = value
    assert validate(registry)


def test_registry_requires_both_bar_counts_and_accepts_positive_integers():
    registry = json.loads((ROOT / 'music-analysis.registry.json').read_text())
    assert registry['sections']['rules'] == RULES
    assert validate(registry) == []
    for key in ('smooth_bars', 'min_bars'):
        missing = copy.deepcopy(registry)
        del missing['sections']['rules'][key]
        assert validate(missing)


def test_intro_bar_exists_only_when_there_are_beats_before_first_downbeat():
    rules = dict(RULES, smooth_bars=1)
    bars = section_bars([.5, 1, 2, 3], [1, 3], [.2, .4, .6, .8], 4, rules)
    assert [(b['start'], b['end']) for b in bars] == [(0, 1), (1, 3), (3, 4)]
    assert [b['energy'] for b in bars] == pytest.approx([.2, .5, .8])
    bars = section_bars([1, 2, 3], [1, 3], [.4, .6, .8], 4, rules)
    assert [(b['start'], b['end']) for b in bars] == [(0, 3), (3, 4)]
    assert [b['energy'] for b in bars] == pytest.approx([.5, .8])


def test_smoothing_uses_registry_window_and_clips_at_both_ends():
    args = ([0, 1, 2, 3, 4], [0, 1, 2, 3, 4], [0, .2, .4, .6, .8], 5)
    bars = section_bars(*args, RULES)
    assert [b['smoothed_energy'] for b in bars] == pytest.approx([.1, .2, .3, .5, .6])
    bars = section_bars(*args, dict(RULES, smooth_bars=1))
    assert [b['smoothed_energy'] for b in bars] == pytest.approx(args[2])


def make_runs(specs):
    start = 0
    runs = []
    for kind, count, mean in specs:
        runs.append(dict(start=start, end=start+count, kind=kind, bars=count, energy_sum=count*mean))
        start += count
    return runs


def test_merge_shortest_first_chooses_closest_energy_and_coalesces():
    runs = make_runs([('quiet', 4, .1), ('build', 3, .4), ('peak', 1, .7), ('build', 4, .5)])
    result = merge_short_sections(runs, 4)
    assert [(r['kind'], r['bars']) for r in result] == [('quiet', 4), ('build', 8)]
    assert result[1]['energy_sum'] == pytest.approx(3*.4+.7+4*.5)


def test_merge_energy_tie_prefers_longer_neighbor_and_inherits_its_type():
    result = merge_short_sections(make_runs([('quiet', 4, .25), ('build', 1, .5), ('peak', 5, .75)]), 4)
    assert [(r['kind'], r['bars']) for r in result] == [('quiet', 4), ('peak', 6)]


def test_equal_shortest_runs_are_processed_from_left_and_minimum_is_configurable():
    specs = [('quiet', 4, 0), ('build', 1, .25), ('peak', 1, .75), ('quiet', 4, 1)]
    assert [(r['kind'], r['bars']) for r in merge_short_sections(make_runs(specs), 1)] == [(k, n) for k, n, _ in specs]
    assert [(r['kind'], r['bars']) for r in merge_short_sections(make_runs(specs), 4)] == [('quiet', 10)]
