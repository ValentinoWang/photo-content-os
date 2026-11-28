#!/usr/bin/env python3
"""Measure saved editor output and the registered preview; keep failures visible."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_ROOT_DIR = str(_Path(__file__).resolve().parents[1])
if _SCRIPTS_ROOT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_ROOT_DIR)
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from scipy.signal import butter, sosfiltfilt

from edit_backends.editors.kdenlive_render import melt_executable
from creative.render_preview import _audio_filters

if __package__ and "." in __package__:
    from ..constants import (
        RATE,
    )
else:
    import sys as _sys
    from pathlib import Path as _Path
    _sdir = str(_Path(__file__).resolve().parents[1])
    if _sdir not in _sys.path:
        _sys.path.insert(0, _sdir)
    from constants import (
        RATE,
    )


def pcm(path):
    data = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
                                    '-ac', '1', '-ar', str(RATE), '-f', 'f64le', '-'])
    return np.frombuffer(data, dtype='<f8')


def db(value):
    return float(20 * np.log10(max(float(value), 1e-12)))


def rms(samples):
    return float(np.sqrt(np.mean(samples**2)))


def window_differences(first, second):
    assert len(first) == len(second) == 22 * RATE
    return [abs(db(rms(first[a:a+4800]))-db(rms(second[a:a+4800])))
            for a in range(0, len(first), 4800)]


def pop_energy(samples, cuts):
    filtered = sosfiltfilt(butter(4, 4000, 'highpass', fs=RATE, output='sos'), samples)
    half, reach, hop = round(.005*RATE), round(.1*RATE), round(.001*RATE)
    padded = np.pad(filtered, (half, half))
    results = {}
    for cut in cuts:
        position = round(cut*RATE)
        energy = float(np.mean(padded[position:position+2*half]**2))
        neighbors = [float(np.mean(filtered[c-half:c+half]**2))
                     for c in range(max(half, position-reach), min(len(samples)-half, position+reach)+1, hop)]
        median = float(np.median(neighbors))
        excess = float(10*np.log10(max(energy, 1e-24)/max(median, 1e-24)))
        results[str(cut)] = {'window_energy': energy, 'context_median_energy': median, 'excess_db': excess}
    return results


def preview_pcm(plan, path):
    sources = list(dict.fromkeys(s['source'] for s in plan['segments']))
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-filter_complex_threads', '1']
    for source in sources:
        command.extend(['-i', source])
    graph = ';'.join(_audio_filters(plan, dict(zip(sources, range(len(sources))))))
    subprocess.run([*command, '-filter_complex', graph, '-map', '[outa]', '-ac', '2', '-ar', str(RATE),
                    '-c:a', 'pcm_s24le', str(path)], check=True)


def prop(node, name):
    return node.findtext(f"property[@name='{name}']")


def set_prop(node, name, value):
    element = node.find(f"property[@name='{name}']")
    if element is None:
        element = ET.SubElement(node, 'property', {'name': name})
    element.text = str(value)


def melt_probe(root, source, path, *, neutral=False):
    selected = copy.deepcopy(root)
    for node in selected:
        resource = prop(node, 'resource')
        if not resource:
            continue
        resolved = Path(resource)
        if not resolved.is_absolute():
            resolved = Path(root.attrib['root']) / resolved
        set_prop(node, 'resource', resolved)
        set_prop(node, 'set.test_image', 1)
        if str(resolved.resolve()) != source:
            set_prop(node, 'set.test_audio', 1)
        elif neutral:
            for effect in node.findall('filter'):
                if prop(effect, 'mlt_service') == 'volume':
                    set_prop(effect, 'level', db(.14))
    project = path.with_suffix('.mlt')
    ET.ElementTree(selected).write(project, encoding='utf-8', xml_declaration=True)
    with path.with_suffix('.log').open('wb') as log:
        subprocess.run([melt_executable(), str(project), '-consumer', 'avformat:' + str(path),
                        'f=wav', 'vn=1', 'acodec=pcm_s16le', 'ar=48000', 'channels=2',
                        'real_time=-1', 'threads=2', 'out=659'], stdout=log, stderr=log,
                       check=True, env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen'})
    return pcm(path)


def preview_probe(plan, source, path, *, neutral=False):
    selected = copy.deepcopy(plan)
    selected['segments'] = [s for s in selected['segments'] if s['source'] == source]
    if neutral:
        for segment in selected['segments']:
            segment['gain_envelope']['factors'] = [f for f in segment['gain_envelope']['factors']
                                                     if f['kind'] != 'duck']
    graph = ';'.join(_audio_filters(selected, {source: 0}))
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', source,
                    '-filter_complex', graph, '-map', '[outa]', '-ac', '1', '-ar', str(RATE),
                    '-c:a', 'pcm_s16le', str(path)], check=True)
    return pcm(path)


def measure(directory):
    target = directory / 'measurements'
    target.mkdir(exist_ok=True)
    saved_path = directory / 'kdenlive/timeline.kdenlive'
    root = ET.parse(saved_path).getroot()
    render_plan = json.loads((directory / 'kdenlive/render-plan.json').read_text())
    plan = render_plan['audio_plan']
    prepared_sources = render_plan.get('audio_sources', {})
    k = pcm(directory / 'kdenlive-saved.wav')
    p = pcm(directory / 'preview.mp4')
    assert len(k) == len(p) == 22 * RATE
    reference = directory / 'preview-pcm.wav'
    if not reference.exists():
        preview_pcm(plan, reference)
    uncompressed = pcm(reference)
    encoding = {}
    for filename in ('mixed.mp4', 'preview.mp4'):
        values = window_differences(uncompressed, pcm(directory / filename))
        encoding[filename] = {'max_100ms_rms_error_db': max(values),
                              'median_100ms_rms_error_db': float(np.median(values)),
                              'all_errors_db': values}
    saved_difference = window_differences(pcm(directory / 'kdenlive-before.wav'), k)
    paths = {s['id']: s['source'] for s in plan['segments']}
    sources = {'speech': paths['clip:5'], 'bed': paths['bed:0'],
               'music0': paths['music:0'], 'music1': paths['music:1'], 'airport': paths['clip:1']}
    ks, ps = {}, {}
    for name, source in sources.items():
        print('isolate', name, flush=True)
        ks[name] = melt_probe(root, prepared_sources.get(source, source), target / ('k-' + name + '.wav'))
        ps[name] = preview_probe(plan, source, target / ('p-' + name + '.wav'))
    kn = melt_probe(root, prepared_sources.get(sources['music1'], sources['music1']), target / 'k-music1-neutral.wav', neutral=True)
    pn = preview_probe(plan, sources['music1'], target / 'p-music1-neutral.wav', neutral=True)
    windows = np.arange(220) * .1
    differences = [abs(db(rms(k[round(t*RATE):round((t+.1)*RATE)])) -
                       db(rms(p[round(t*RATE):round((t+.1)*RATE)]))) for t in windows]
    result = {'files': {'kdenlive': 'kdenlive-saved.wav', 'preview': 'preview.mp4',
                       'saved_project': 'kdenlive/timeline.kdenlive'},
              'duration_sec': {'kdenlive': len(k)/RATE, 'preview': len(p)/RATE},
              'gui_save_100ms': {'max_db': max(saved_difference), 'median_db': float(np.median(saved_difference)),
                                  'all_differences_db': saved_difference},
              'aac_error_vs_preview_pcm': encoding,
              'loudness_100ms': {'definition': 'mono unweighted RMS dBFS; identical film time, 220 windows',
                                  'max_absolute_difference_db': max(differences),
                                  'median_absolute_difference_db': float(np.median(differences)),
                                  'all_absolute_differences_db': differences},
              'isolation': 'Only source audio is disabled in copies of the saved graph; original mix transitions and gains are retained. FFmpeg component plans retain original envelopes. These copies attribute components; full-output figures use the files above.'}
    for name, mix, stems, neutral in [('kdenlive', k, ks, kn), ('preview', p, ps, pn)]:
        # Fit the actual full output, rather than treating solo renders as the
        # mix: MLT's default mix transition changes attenuation with occupancy.
        names = list(stems)
        references = dict(stems, music1=neutral)
        fits = []
        for t in windows:
            a, b = round(t*RATE), round((t+.1)*RATE)
            matrix = np.stack([references[n][a:b] for n in names], axis=1)
            actual = mix[a:b]
            gains = np.linalg.lstsq(matrix, actual, rcond=1e-5)[0]
            residual = rms(actual-matrix@gains)/max(rms(actual), 1e-12)
            fits.append({'time': round(float(t), 3), 'gains': dict(zip(names, map(float, gains))),
                         'residual_ratio': residual})
        before_gain = float(np.median([f['gains']['music1'] for f in fits if 11.7 <= f['time'] <= 13.2]))
        during_gain = float(np.median([f['gains']['music1'] for f in fits if 14.3 <= f['time'] <= 17.7]))
        bed_fitted = {}
        for cut in (8, 11):
            before_gain_bed = float(np.median([f['gains']['bed'] for f in fits if cut-.4 <= f['time'] < cut]))
            after_gain_bed = float(np.median([f['gains']['bed'] for f in fits if cut <= f['time'] < cut+.4]))
            bed_fitted[str(cut)] = {'before_source_gain': before_gain_bed, 'after_source_gain': after_gain_bed,
                                    'change_db': db(after_gain_bed/before_gain_bed)}
        speech = stems['speech']
        steady = rms(speech[round(13.7*RATE):round(13.8*RATE)])
        onset = next((t for t in np.arange(13.45, 13.65, .001)
                      if rms(speech[round(t*RATE):round((t+.005)*RATE)]) > steady*.1), None)
        ranges = [(14.3, 14.5), (15.0, 15.2), (17.0, 17.2)]
        duck = [db(rms(stems['music1'][round(a*RATE):round(b*RATE)]) /
                   max(rms(neutral[round(a*RATE):round(b*RATE)]), 1e-12)) for a, b in ranges]
        pre = db(rms(stems['music1'][round(12*RATE):round(12.2*RATE)]) /
                 max(rms(neutral[round(12*RATE):round(12.2*RATE)]), 1e-12))
        crossing = [db(rms(mix[round(t*RATE):round((t+.02)*RATE)])) for t in np.arange(8, 8.5, .02)]
        bed_changes = {}
        for cut in (8, 11):
            # Compare adjacent source-continuous windows; natural source dynamics remain visible.
            before = rms(stems['bed'][round((cut-.02)*RATE):round(cut*RATE)])
            after = rms(stems['bed'][round(cut*RATE):round((cut+.02)*RATE)])
            bed_changes[str(cut)] = {'before_dbfs': db(before), 'after_dbfs': db(after),
                                     'natural_window_change_db': db(after/max(before, 1e-12))}
        cuts = sorted({0, 4, 8, 11, 14, 18, 22} |
                      {s[key] for s in plan['segments'] for key in ('timeline_start_sec', 'timeline_end_sec')})
        pad = np.pad(mix, (1, 1))
        jumps = {str(t): float(abs(pad[round(t*RATE)+1]-pad[round(t*RATE)])) for t in cuts}
        pops = pop_energy(mix, cuts)
        result[name] = {'speech_onset_sec': float(onset) if onset is not None else None,
                        'speech_lead_sec': float(14-onset) if onset is not None else None,
                        'duck_attribution_db': duck, 'duck_before_db': pre,
                        'duck_relative_to_before_db': [d-pre for d in duck],
                        'crossfade_full_mix_min_20ms_dbfs': min(crossing),
                        'bed_picture_cut_windows': bed_changes,
                        'cut_adjacent_sample_jumps_fs_diagnostic_only': jumps,
                        'pop_4khz_10ms': pops,
                        'pop_threshold_satisfied': all(v['excess_db'] <= 6 for v in pops.values()),
                        'full_mix_rms_dbfs': db(rms(mix)), 'peak_fs': float(np.max(abs(mix)))}
        result[name]['component_sum_max_residual_fs'] = float(np.max(abs(mix-sum(stems.values()))))
        result[name]['actual_full_mix_attribution'] = {
            'method': '100ms least squares against source-isolated references; music1 reference has no duck; median coefficients before/during; bed compares 400ms either side against the same continuous source',
            'music_before_gain': before_gain, 'music_during_gain': during_gain,
            'duck_relative_to_before_db': db(during_gain/before_gain),
            'bed_cut_gain_changes': bed_fitted,
            'median_residual_rms_ratio': float(np.median([f['residual_ratio'] for f in fits])),
            'windows': fits}
        detected = None
        for t in np.arange(13.45, 13.65, .001):
            a, b = round(t*RATE), round((t+.005)*RATE)
            matrix = np.stack([stems[n][a:b] for n in names], axis=1)
            gains = np.linalg.lstsq(matrix, mix[a:b], rcond=1e-5)[0]
            speech_index = names.index('speech')
            if gains[speech_index] > .01 and rms(matrix[:, speech_index]*gains[speech_index]) > .002:
                detected = float(t)
                break
        result[name]['full_mix_speech_onset_sec'] = detected
        result[name]['full_mix_speech_lead_sec'] = 14-detected if detected is not None else None
        result[name]['speech_detection_method'] = '5ms sliding source-attribution windows, 1ms hop; fitted speech RMS >0.002 FS and positive coefficient'
        music_levels = []
        for t in np.arange(8, 8.5, .02):
            a, b = round(t*RATE), round((t+.02)*RATE)
            matrix = np.stack([stems[n][a:b] for n in names], axis=1)
            gains = np.linalg.lstsq(matrix, mix[a:b], rcond=1e-5)[0]
            music_indices = [names.index('music0'), names.index('music1')]
            attributed = sum(matrix[:, i]*gains[i] for i in music_indices)
            music_levels.append(db(rms(attributed)))
        result[name]['crossfade_music_min_20ms_dbfs'] = min(music_levels)
    (directory / 'measurements.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'loudness_max_difference_db': max(differences),
                      'loudness_median_difference_db': float(np.median(differences)),
                      'pop_threshold_satisfied': {name: result[name]['pop_threshold_satisfied']
                                                   for name in ('kdenlive', 'preview')}}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    measure(parser.parse_args().directory.expanduser().resolve())
