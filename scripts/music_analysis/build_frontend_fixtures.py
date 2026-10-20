#!/usr/bin/env python3
"""Project approved mock inputs through the unchanged stage A music payload."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from music_library.cache import write_json
from studio.media_review import MediaReview
from studio.music_analysis import failure, validate_analysis
from music_analysis.approved_frontend_copy import approved_copy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--library-copy', type=Path, required=True)
    parser.add_argument('--analysis-input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    mock = ROOT / 'docs/tasks/R223-music-beat-map/mock'
    inputs = json.JSONDecoder().raw_decode((mock / 'beat-data.js').read_text().split('window.TRACKS=', 1)[1])[0]
    source = json.loads((args.library_copy / 'library/music/index.json').read_text())['tracks']
    media = Path(tempfile.mkdtemp(prefix='r223-frontend-fixtures-'))
    os.environ['LOCAL_MEDIA_ROOT'] = str(media)
    folder = media / 'library/music'
    tracks, analyses = [], {}
    for row in inputs:
        track = copy.deepcopy(next(t for t in source if t['file_sha256'] == row['id']))
        track.update(title=row['title'], artist=row['artist'], duration_seconds=row['dur'], imported_at=row['imported'])
        track['platform'] = row['platform']
        data = json.loads((args.analysis_input / (row['id'] + '.json')).read_text())
        data['duration_seconds'] = row['dur']
        data['beat'].update(beats=row['beats'], downbeats=row['downbeats'], beat_energy=row['energy'], sections=[{k:s[k] for k in ('start','end','kind')} for s in row['sections']])
        data['beat']['sections'][-1]['end'] = row['dur']
        validate_analysis(data)
        tracks.append(track)
        analyses[track['file_sha256']] = data
        target = folder / track['file_sha256']; target.mkdir(parents=True)
        (target / track['audio_file']).write_bytes(b'synthetic fixture placeholder')
        write_json(target / 'peaks.json', row['peaks'])
    extra = copy.deepcopy(tracks[1]); extra.update(original_url='fixture:new-summer',file_sha256=hashlib.sha256(b'r223-new-summer').hexdigest(),title='夏日漱石',artist='橘子海',platform='qishui',duration_seconds=252,imported_at='2026-10-21T01:12:00+08:00')
    directory=folder/extra['file_sha256'];directory.mkdir();(directory/extra['audio_file']).write_bytes(b'synthetic fixture placeholder');write_json(directory/'peaks.json',inputs[2]['peaks'])
    states=['music','music-beats-queued','music-beats-analyzing','music-beats-failed','music-beats-failed-unreadable','music-beats-failed-unknown','music-tags-failed','music-filter-empty']
    args.out.mkdir(parents=True, exist_ok=True)
    for state in states:
        for identity, data in analyses.items(): write_json(folder/identity/'analysis.json',data)
        present=tracks+([extra] if state=='music-beats-analyzing' else [])
        for track in present: write_json(folder/track['file_sha256']/'track.json',track)
        if extra not in present:
            (directory/'track.json').unlink(missing_ok=True)
        write_json(folder/'index.json',dict(schema_version=2,tracks=present))
        review=MediaReview(None)
        if state=='music-beats-queued':
            review.analysis_queue.active=(tracks[0]['file_sha256'],'all')
            review.analysis_queue.pending.extend((t['file_sha256'],'all') for t in tracks[1:])
        elif state=='music-beats-analyzing': review.analysis_queue.active=(extra['file_sha256'],'all')
        elif state.startswith('music-beats-failed') or state=='music-tags-failed':
            part='tags' if state=='music-tags-failed' else 'beat';target=tracks[2] if part=='tags' else tracks[0]
            data=copy.deepcopy(analyses[target['file_sha256']]);code='audio_unreadable' if state.endswith('unreadable') else 'beat_worker_exit_9' if state.endswith('unknown') else 'worker_error'
            data[part]=failure(code);write_json(folder/target['file_sha256']/'analysis.json',data)
        write_json(args.out/(state+'.json'),dict(ok=True,**review.music_payload()))
    write_json(args.out/'approved-copy.json',approved_copy())
    print(f'Projected {len(states)} API fixtures through stage A')

if __name__ == '__main__': main()
