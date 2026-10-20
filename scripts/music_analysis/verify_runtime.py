#!/usr/bin/env python3
"""Exercise real Studio HTTP import, offline queue, partial retry and audio failure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import urllib.request
import wave
import math

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    args=parser.parse_args()
    evidence=args.evidence_dir;evidence.mkdir(parents=True,exist_ok=True)
    assets=Path.home()/'.photo-content-os/evidence/R223-music-beat-map'
    assets.mkdir(parents=True,exist_ok=True)
    media=Path(tempfile.mkdtemp(prefix='integration-',dir=assets))
    source=media/'input';source.mkdir()
    for i in range(3):
        sr=22050;values=[]
        for j in range(sr*24):
            t=j/sr;phase=t%.5;accent=int(t*2)%4==0
            x=(.7 if accent else .4)*math.sin(2*math.pi*(160 if accent else 800)*phase)*math.exp(-phase*65)+.03*math.sin(2*math.pi*(220+i*55)*t)
            values.append(int(x*32767))
        with wave.open(str(source/f'synthetic-{i+1}.wav'),'wb') as out:
            out.setparams((1,2,sr,0,'NONE','not compressed'));out.writeframes(struct.pack('<'+'h'*len(values),*values))
    os.environ['LOCAL_MEDIA_ROOT']=str(media)
    os.environ['ASSET_INDEX_PATH']=str(media/'assets.sqlite')
    from studio.server import serve
    server=serve(state_dir=media/'state',port=0)
    port=server.server_address[1];assert port!=8765
    base=f'http://127.0.0.1:{port}'
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def api(path,value=None):
        headers={'Content-Type':'application/json'}
        if value is not None:headers.update({'X-Content-OS-CSRF':csrf,'Origin':base})
        request=urllib.request.Request(base+path,data=json.dumps(value).encode() if value is not None else None,headers=headers)
        return json.load(urllib.request.urlopen(request,timeout=20))
    def wait(predicate,seconds=180):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            value=api('/api/review/music')
            states.append({row['title']:{p:row[p]['status'] for p in ('beat','tags')} for row in value['tracks']})
            if predicate(value):return value
            time.sleep(.2)
        raise AssertionError('analysis queue did not complete')
    states=[]
    try:
        csrf=api('/api/bootstrap')['csrfToken']
        job=api('/api/review/music/import',{'folder':str(source)})['job']
        print('HTTP folder import started',flush=True)
        result=wait(lambda value:len(value['tracks'])==3 and all(row[p]['status']=='done' for row in value['tracks'] for p in ('beat','tags')))
        assert 'scores' not in json.dumps(result)
        assert result['taxonomy']['display'] and result['registry_version']==1
        for row in result['tracks']:
            assert row['beat']['bpm']==120
        print('Three real analyses complete',flush=True)
        target=result['tracks'][0];identifier=target['file_sha256'];folder=media/'library/music'/identifier
        analysis=json.loads((folder/'analysis.json').read_text())
        beat_before=analysis['beat']
        audio=folder/next(p.name for p in folder.glob('audio.*'));original=audio.read_bytes()
        audio.write_bytes(b'corrupted synthetic audio')
        api(f'/api/review/music/{identifier}/reanalyze',{'part':'tags'})
        failed=wait(lambda value:next(r for r in value['tracks'] if r['file_sha256']==identifier)['tags']['status']=='failed')
        bad=next(r for r in failed['tracks'] if r['file_sha256']==identifier)
        assert bad['tags']['failure']==dict(code='audio_unreadable',retryable=False)
        assert bad['beat']['status']=='done'
        audio.write_bytes(original)
        api(f'/api/review/music/{identifier}/reanalyze',{'part':'tags'})
        api(f'/api/review/music/{identifier}/reanalyze',{'part':'tags'})
        fixed=wait(lambda value:next(r for r in value['tracks'] if r['file_sha256']==identifier)['tags']['status']=='done')
        final=json.loads((folder/'analysis.json').read_text())
        assert final['beat']==beat_before
        print('Unreadable failure and tags-only retry verified',flush=True)
        # Restart against the same temporary library, with one result removed.
        server.shutdown();server.server_close();thread.join(5)
        (folder/'analysis.json').unlink()
        server=serve(state_dir=media/'state',port=0);base=f'http://127.0.0.1:{server.server_address[1]}'
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        restored=wait(lambda value:all(r[p]['status']=='done' for r in value['tracks'] for p in ('beat','tags')))
        print('Startup backfill verified',flush=True)
        counts={}
        for track in restored['tracks']:
            raw=json.loads((media/'library/music'/track['file_sha256']/'analysis.json').read_text())
            counts[track['title']]={head:len(v) for head,v in raw['tags']['scores'].items()}
        summary=dict(status='passed',port=port,tracks=3,import_method='HTTP folder import',queue_states=states,score_counts=counts,failure='audio_unreadable',retry='tags only; beat unchanged',startup_backfill=True,model_network='worker socket connections denied',media_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()})
        (evidence/'runtime.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        (evidence/'api-final.json').write_text(json.dumps(restored,ensure_ascii=False,indent=2)+'\n')
        # Local-only location for subsequent screenshot checks; never stored in Git evidence.
        Path('/tmp/r223-media-location').write_text(str(media))
        print(json.dumps({k:v for k,v in summary.items() if k not in ('queue_states','media_hashes')}),flush=True)
    finally:
        server.shutdown();server.server_close();thread.join(5)
    return 0


if __name__=='__main__':raise SystemExit(main())
