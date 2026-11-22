import json
import math
import struct
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts/video_render'))
from scripts.direct_video import promo_plan
from studio.music_analysis import BeatMapUnavailable
import compose


def tone(path, duration, amplitude=0):
    with wave.open(str(path), 'wb') as w:
        w.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        w.writeframes(b''.join(struct.pack('<h', int(amplitude * math.sin(2 * math.pi * 440 * i / 48000))) for i in range(int(duration * 48000))))


@pytest.fixture
def inputs(tmp_path):
    track = 'a' * 64
    folder = tmp_path / 'library/music' / track
    folder.mkdir(parents=True)
    tone(folder / 'music.wav', 12)
    (folder / 'track.json').write_text(json.dumps({'audio_file': 'music.wav'}))
    beats = [round(i * .503, 3) for i in range(24)]
    beat_map = {'bpm': 119, 'meter': 4, 'beats': beats, 'downbeats': beats[::4], 'sections': [], 'duration_seconds': 12.0}
    spec = {'track_id': track, 'fps': 30, 'width': 1920, 'height': 1080, 'start_bar': 1,
            'shots': [{'id': str(i), 'html': f'{i}.html', 'bars': 1} for i in range(4)]}
    return tmp_path, beat_map, spec


def test_boundaries_and_wav(inputs):
    root, beats, spec = inputs
    render, composition, plan = promo_plan.create_plan(spec, root, root / 'out', beat_map=beats)
    assert [s['start_frame'] for s in render['shots']] == [round(t * 30) for t in beats['downbeats'][:4]]
    assert sum(s['frames'] for s in render['shots']) == round(beats['downbeats'][4] * 30)
    assert all(abs(s['start_frame'] / 30 - beats['downbeats'][i]) <= 1 / 30 for i, s in enumerate(render['shots']))
    assert plan['shots'][0]['start_bar'] == 1
    assert compose.audio_inputs(composition)
    with wave.open(composition['narration_wav']) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (48000, 2, 2)
        assert w.getnframes() == round(sum(s['frames'] for s in render['shots']) * 48000 / 30)


def test_sound_effect_lands_on_shot_offset(inputs):
    root, beats, spec = inputs
    effect = root / 'effect.wav'
    tone(effect, .2, 15000)
    spec['sfx'] = [{'shot': '1', 'file': str(effect), 'offset_frames': 3, 'gain_db': 0}]
    render, composition, _ = promo_plan.create_plan(spec, root, root / 'out', beat_map=beats)
    start = (render['shots'][1]['start_frame'] + 3) * 48000 // 30
    with wave.open(composition['narration_wav']) as w:
        w.setpos(start - 1600)
        before = w.readframes(1600)
        after = w.readframes(1600)
    assert max(before) == 0
    assert any(after)


def test_short_track(inputs):
    root, beats, spec = inputs
    spec['shots'][0]['bars'] = 100
    with pytest.raises(promo_plan.PlanError, match='downbeat') as exc:
        promo_plan.create_plan(spec, root, root / 'out', beat_map=beats)
    assert exc.value.code == 'track_too_short'


def test_beat_error_code_is_preserved(inputs, monkeypatch, capsys):
    root, _, spec = inputs
    spec_path = root / 'spec.json'
    spec_path.write_text(json.dumps(spec))
    def unavailable(*args, **kwargs):
        raise BeatMapUnavailable('analyzing', spec['track_id'])
    monkeypatch.setattr(promo_plan, 'load_beat_map', unavailable)
    assert promo_plan.main(['--spec', str(spec_path), '--media-root', str(root), '--out', str(root / 'out')]) != 0
    assert json.loads(capsys.readouterr().err)['code'] == 'analyzing'


def test_auto_bars_cover_declared_animation(inputs):
    root, beats, spec = inputs
    (root / 'long.html').write_text('<script>const D = 4.1;</script>')
    (root / 'short.html').write_text('<script>const D = 1.5;</script>')
    spec['shots'] = [{'id': 'a', 'html': 'long.html', 'bars': 'auto'}, {'id': 'b', 'html': 'short.html', 'bars': 'auto'}]
    render, _, plan = promo_plan.create_plan(spec, root, root / 'out', beat_map=beats, spec_dir=root)
    # one bar is 4 * 0.503 = 2.012s: D=4.1 needs 3 bars, D=1.5 needs 1
    assert [s['end_bar'] - s['start_bar'] for s in plan['shots']] == [3, 1]
    assert render['shots'][0]['frames'] / 30 >= 4.1


def test_auto_bars_need_declared_duration(inputs):
    root, beats, spec = inputs
    (root / 'plain.html').write_text('<p>no D</p>')
    spec['shots'] = [{'id': 'a', 'html': 'plain.html', 'bars': 'auto'}]
    with pytest.raises(promo_plan.PlanError) as exc:
        promo_plan.create_plan(spec, root, root / 'out', beat_map=beats, spec_dir=root)
    assert exc.value.code == 'animation_duration_missing'


def test_premix_peak_stays_one_db_below_full_scale(inputs):
    root, beats, spec = inputs
    track = root / 'library/music' / spec['track_id'] / 'music.wav'
    # Stereo at full scale: a mono source is upmixed 3 dB down and would never reach the limiter.
    with wave.open(str(track), 'wb') as w:
        w.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
        w.writeframes(b''.join(struct.pack('<hh', s, s) for s in (int(32767 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(12 * 48000))))
    _, composition, _ = promo_plan.create_plan(spec, root, root / 'out', beat_map=beats)
    with wave.open(composition['narration_wav']) as w:
        data = w.readframes(w.getnframes())
    peak = max(abs(v) for (v,) in struct.iter_unpack('<h', data))
    assert peak <= round(32767 * 10 ** (-1 / 20)) + 64
