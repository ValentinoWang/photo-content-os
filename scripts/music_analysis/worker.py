#!/usr/bin/env python3
"""One offline request on stdin, one JSON result on stdout; diagnostics go to stderr."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / '.tools/music-analysis'


def deny_network(*args, **kwargs):
    raise RuntimeError('network disabled during analysis')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified(path, sha):
    if not path.is_file() or digest(path) != sha:
        raise ValueError('missing or damaged model: ' + path.name)
    return path


def versions(*packages):
    return {p: importlib.metadata.version(p) for p in packages}


def section_bars(beats, downs, energy, duration, rules):
    import numpy as np
    window = rules['smooth_bars']
    if type(window) is not int or window <= 0:
        raise ValueError('smooth_bars must be a positive integer')
    starts = list(downs)
    if not starts:
        starts = [0.0]
    elif starts[0] > 0:
        if any(0 <= beat < starts[0] for beat in beats):
            starts.insert(0, 0.0)
        else:
            starts[0] = 0.0
    bars = []
    for start, end in zip(starts, [*starts[1:], duration]):
        values = [value for beat, value in zip(beats, energy) if start <= beat < end]
        bars.append(dict(start=start, end=end, energy=float(np.mean(values)) if values else 0.0))
    # For an even window, the extra neighbor is before the current bar.
    left = window // 2
    right = window - left - 1
    for i, bar in enumerate(bars):
        bar['smoothed_energy'] = float(np.mean([b['energy'] for b in bars[max(0, i-left):min(len(bars), i+right+1)]]))
    return bars


def merge_short_sections(runs, minimum):
    if type(minimum) is not int or minimum <= 0:
        raise ValueError('min_bars must be a positive integer')
    while len(runs) > 1:
        short = [i for i, run in enumerate(runs) if run['bars'] < minimum]
        if not short:
            break
        i = min(short, key=lambda index: (runs[index]['bars'], index))
        mean = runs[i]['energy_sum'] / runs[i]['bars']
        neighbors = [j for j in (i-1, i+1) if 0 <= j < len(runs)]
        neighbor = min(neighbors, key=lambda j: (abs(mean - runs[j]['energy_sum'] / runs[j]['bars']), -runs[j]['bars'], j))
        left, right = sorted((i, neighbor))
        merged = dict(start=runs[left]['start'], end=runs[right]['end'], kind=runs[neighbor]['kind'],
                      bars=runs[left]['bars']+runs[right]['bars'], energy_sum=runs[left]['energy_sum']+runs[right]['energy_sum'])
        runs[left:right+1] = [merged]
        j = 1
        while j < len(runs):
            if runs[j-1]['kind'] == runs[j]['kind']:
                runs[j-1]['end'] = runs[j]['end']
                runs[j-1]['bars'] += runs[j]['bars']
                runs[j-1]['energy_sum'] += runs[j]['energy_sum']
                runs.pop(j)
            else:
                j += 1
    return runs


def section_map(beats, downs, energy, duration, rules):
    import numpy as np
    bars = section_bars(beats, downs, energy, duration, rules)
    low, high = np.quantile([bar['smoothed_energy'] for bar in bars], [1/3, 2/3])
    runs = []
    for bar in bars:
        value = bar['smoothed_energy']
        kind = 'build' if high-low < 1e-9 else 'quiet' if value <= low else 'peak' if value >= high else 'build'
        if runs and runs[-1]['kind'] == kind:
            runs[-1]['end'] = bar['end']
            runs[-1]['bars'] += 1
            runs[-1]['energy_sum'] += value
        else:
            runs.append(dict(start=bar['start'], end=bar['end'], kind=kind, bars=1, energy_sum=value))
    runs = merge_short_sections(runs, rules['min_bars'])
    return [{key: run[key] for key in ('start', 'end', 'kind')} for run in runs]


def analyze_beat(audio, sr, duration, reg, lock):
    import numpy as np
    import librosa
    import torch
    from beat_this.inference import Audio2Beats
    spec = lock['beat_checkpoint']
    path = verified(ENV / 'models' / spec['file'], spec['sha256'])
    torch.set_num_threads(2)
    beats, downs = Audio2Beats(checkpoint_path=str(path), device='cpu', dbn=False)(audio, sr)
    beats = [float(t) for t in beats if 0 <= t < duration]
    downs = [float(t) for t in downs if float(t) in set(beats)]
    if len(beats) < 2:
        raise ValueError('insufficient beats')
    energy = []
    for start, end in zip(beats, [*beats[1:], duration]):
        frame = audio[int(start*sr):max(int(start*sr)+1, int(end*sr))]
        energy.append(float(librosa.feature.rms(y=frame, frame_length=len(frame), hop_length=len(frame), center=False)[0, 0]))
    low, high = np.quantile(energy, [.05, .95])
    normalized = np.clip((np.asarray(energy) - low) / max(float(high-low), 1e-12), 0, 1).tolist()
    return dict(status='done', beats=beats, downbeats=downs, beat_energy=normalized,
                sections=section_map(beats, downs, normalized, duration, reg['sections']['rules']),
                package_versions=versions('beat-this', 'librosa', 'torch', 'torchaudio'), models=[spec['id']], registry_version=reg['registry_version'])


def analyze_tags(audio, sr, reg, lock):
    import numpy as np
    import soxr
    from essentia.standard import TensorflowPredictEffnetDiscogs, TensorflowPredict2D
    specs = reg['analyzers']['tags']['models']
    paths = {m['id']: verified(ENV / 'models' / (m['id']+'.pb'), m['sha256']) for m in specs}
    embedding = next(m for m in specs if m['role'] == 'embedding')
    signal = soxr.resample(audio, sr, 16000).astype(np.float32) if sr != 16000 else audio.astype(np.float32)
    vectors = TensorflowPredictEffnetDiscogs(graphFilename=str(paths[embedding['id']]), output='PartitionedCall:1', lastPatchMode='repeat')(signal)
    scores = {}
    for head, model_id in lock['heads'].items():
        meta_spec = lock['metadata'][model_id]
        path = verified(ENV / 'models' / meta_spec['file'], meta_spec['sha256'])
        meta = json.loads(path.read_text())
        output = next(o['name'] for o in meta['schema']['outputs'] if o.get('output_purpose') == 'predictions')
        prediction = TensorflowPredict2D(graphFilename=str(paths[model_id]), input=meta['schema']['inputs'][0]['name'], output=output)(vectors)
        values = np.mean(prediction, axis=0)
        if len(values) != len(meta['classes']) or not np.isfinite(values).all():
            raise ValueError('classifier output shape or value invalid')
        scores[head] = sorted([[label, float(score)] for label, score in zip(meta['classes'], values)], key=lambda p: -p[1])
    return dict(status='done', scores=scores, package_versions=versions('essentia-tensorflow'), models=[m['id'] for m in specs], registry_version=reg['registry_version'])


def failed(code):
    return dict(status='failed', failure=dict(code=code, retryable=code != 'audio_unreadable'))


def process(request):
    import numpy as np
    reg = json.loads((ROOT / 'music-analysis.registry.json').read_text())
    lock = json.loads((ROOT / 'third_party/edit-tools.lock.json').read_text())['music_analysis']
    parts = ('beat', 'tags') if request['part'] == 'all' else (request['part'],)
    try:
        # Decode once with the same offline FFmpeg used by the importer, including AAC/MP3.
        import subprocess
        result = subprocess.run(['ffmpeg', '-v', 'error', '-i', request['audio'], '-ac', '1', '-ar', '22050', '-f', 'f32le', '-'], check=True, capture_output=True, timeout=60)
        audio = np.frombuffer(result.stdout, dtype='<f4')
        if not len(audio) or not np.isfinite(audio).all():
            raise ValueError('unreadable audio')
    except (OSError, ValueError, subprocess.SubprocessError):
        return {part: failed('audio_unreadable') for part in parts}
    output = {}
    for part in parts:
        try:
            fn = analyze_beat if part == 'beat' else analyze_tags
            output[part] = fn(audio, 22050, request['duration_seconds'], reg, lock) if part == 'beat' else fn(audio, 22050, reg, lock)
        except Exception as exc:
            print(f'{part}: {type(exc).__name__}: {exc}', file=sys.stderr)
            output[part] = failed('worker_error')
    return output


if __name__ == '__main__':
    socket.socket.connect = deny_network
    socket.create_connection = deny_network
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['TF_NUM_INTRAOP_THREADS'] = '2'
    os.environ['TF_NUM_INTEROP_THREADS'] = '2'
    print(json.dumps(process(json.load(sys.stdin)), allow_nan=False))
