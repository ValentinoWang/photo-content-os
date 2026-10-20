"""Regression-only snapshot: section_map from A2 commit 02a9606."""

def section_map(beats, downs, energy, duration, rules):
    import numpy as np
    boundaries = sorted(set([0.0, *downs, duration]))
    bars = []
    for start, end in zip(boundaries, boundaries[1:]):
        values = [e for t, e in zip(beats, energy) if start <= t < end]
        bars.append({'start': start, 'end': end, 'energy': float(np.mean(values)) if values else 0.0})
    low, high = np.quantile([b['energy'] for b in bars], [1/3, 2/3])
    runs = []
    for bar in bars:
        kind = 'quiet' if bar['energy'] <= low else 'peak' if bar['energy'] > high else 'build'
        if runs and runs[-1]['kind'] == kind:
            runs[-1]['end'] = bar['end']; runs[-1]['bars'] += 1
        else:
            runs.append(dict(start=bar['start'], end=bar['end'], kind=kind, bars=1))
    while len(runs) > 1:
        short = next((i for i, r in enumerate(runs) if r['bars'] < rules['min_bars']), None)
        if short is None:
            break
        i = short
        neighbor = i - 1 if i > 0 and (i == len(runs) - 1 or runs[i-1]['bars'] >= runs[i+1]['bars']) else i + 1
        left, right = sorted([i, neighbor])
        merged = dict(start=runs[left]['start'], end=runs[right]['end'], kind=runs[neighbor]['kind'], bars=runs[left]['bars'] + runs[right]['bars'])
        runs[left:right+1] = [merged]
        # Coalesce adjacent equal kinds after merging a short run.
        j = 1
        while j < len(runs):
            if runs[j-1]['kind'] == runs[j]['kind']:
                runs[j-1]['end'] = runs[j]['end']; runs[j-1]['bars'] += runs[j]['bars']; runs.pop(j)
            else:
                j += 1
    return [{k: v for k, v in run.items() if k != 'bars'} for run in runs]
