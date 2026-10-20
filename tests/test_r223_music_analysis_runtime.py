"""Opt-in real model tests; generated audio only, no library or network fixtures."""
import json
import math
import os
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import wave

import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from studio.music_analysis import beat_metrics, validate_analysis

pytestmark=pytest.mark.skipif(os.environ.get('R223_RUNTIME_TESTS')!='1',reason='opt-in offline model runtime; R223_RUNTIME_TESTS=1')


def clicks(path, offset=0, seconds=32, tone=0):
    sr=22050;values=[]
    for j in range(sr*seconds):
        t=j/sr+offset;phase=t%.5;bar=int(t*2)%4
        value=(.7 if bar==0 else .4)*math.sin(2*math.pi*(160 if bar==0 else 800)*phase)*math.exp(-phase*65)
        if tone:value+=.03*math.sin(2*math.pi*tone*t)
        values.append(int(max(-1,min(1,value))*32767))
    with wave.open(str(path),'wb') as out:
        out.setparams((1,2,sr,0,'NONE','not compressed'));out.writeframes(struct.pack('<'+'h'*len(values),*values))


def worker(path,part='all',duration=32):
    request=dict(audio=str(path),part=part,duration_seconds=duration)
    result=subprocess.run([str(ROOT/'.tools/music-analysis/bin/python'),str(ROOT/'scripts/music_analysis/worker.py')],input=json.dumps(request),text=True,capture_output=True,timeout=180,check=True)
    return json.loads(result.stdout)


def test_click_bpm_shift_and_full_scores(tmp_path):
    original=tmp_path/'click.wav';shifted=tmp_path/'shifted.wav'
    clicks(original);clicks(shifted,offset=.5,seconds=31)
    # Exact crop: remove 0.5s of the original PCM, preserve all remaining samples.
    with wave.open(str(original),'rb') as audio:
        params=audio.getparams();audio.setpos(11025);pcm=audio.readframes(audio.getnframes()-11025)
    with wave.open(str(shifted),'wb') as audio:audio.setparams(params);audio.writeframes(pcm)
    a=worker(original);b=worker(shifted,part='beat',duration=31.5)
    assert a['beat']['status']=='done',a['beat'];assert a['tags']['status']=='done',a['tags'];assert b['beat']['status']=='done',b
    beats=a['beat']['beats'];new=b['beat']['beats']
    assert abs(beat_metrics(a['beat'])['bpm']-120)<=1
    # Exclude first/last 4s; nearest beat must shift by -0.5s within 40ms.
    errors=[min(abs((t-.5)-u) for u in new) for t in beats if 4<t<27]
    assert errors and max(errors)<=.04,max(errors)
    assert set(a['beat']['downbeats'])<=set(beats)
    assert len(a['beat']['beat_energy'])==len(beats)
    assert all(x<32 for x in beats) # no empty RMS frame at the exact end
    assert {k:len(v) for k,v in a['tags']['scores'].items()}=={'genre':400,'moodtheme':56,'instrument':40,'voice':2}
    validate_analysis(dict(schema_version=1,file_sha256='a'*64,duration_seconds=32,registry_version=1,**a))
    evidence=os.environ.get('R223_EVIDENCE')
    if evidence:
        Path(evidence).mkdir(parents=True,exist_ok=True)
        (Path(evidence)/'click-quality.json').write_text(json.dumps(dict(bpm=beat_metrics(a['beat'])['bpm'],bpm_error=abs(beat_metrics(a['beat'])['bpm']-120),shift_max_error_seconds=max(errors),shift_tolerance_seconds=.04,boundary_excluded_seconds=4,beats=len(beats),downbeats=len(a['beat']['downbeats']),score_counts={k:len(v) for k,v in a['tags']['scores'].items()}),indent=2)+'\n')
