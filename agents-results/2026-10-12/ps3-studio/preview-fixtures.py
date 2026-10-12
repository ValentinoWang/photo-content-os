import sys,json,hashlib,subprocess
from pathlib import Path
sys.path[:0]=['/Users/vsiyo/Desktop/创业项目/photo-content-os/scripts']
from edit_backends.kdenlive_render import plan_ranges,probe_media
root=Path(__file__).parent/'capture-temp';c=json.loads((root/'capture.json').read_text());media=root/'media';run=media/'runs'/hashlib.sha256(c['identity']['jobId'].encode()).hexdigest()[:32]
raw=json.loads((run/'native-suggest.json').read_text());ranges,_=plan_ranges(raw,252)
expr='+'.join(f'gte(t,{r["source_start"]})*lt(t,{r["source_end"]})' for r in ranges)
output=run/'ui-fixture-preview.mp4'
subprocess.run(['ffmpeg','-v','error','-y','-i',str(media/'talk.mp4'),'-vf',f"select='{expr}',setpts=N/FRAME_RATE/TB",'-af',f"aselect='{expr}',asetpts=N/SR/TB",'-t','165','-r','30','-c:v','libx264','-threads','1','-crf','28','-pix_fmt','yuv420p','-c:a','aac','-b:a','32k','-movflags','+faststart',str(output)],check=True)
info=probe_media(output);v=next(s for s in info['streams'] if s['codec_type']=='video');assert abs(float(v['duration'])-165)<.034 and int(v['nb_frames'])==4950
ids=['ui-fixture-chatcut','ui-fixture-kdenlive'];history={'scope':'isolated UI fixtures, not editor execution evidence','candidates':[{'identity':c['identity'],'publicCandidateId':i,'status':'candidate','editingMethod':'open_source','editor':{'toolId':'chatcut' if n==0 else 'otio_kdenlive','displayName':'UI fixture'}} for n,i in enumerate(ids)],'previews':{i:str(output.relative_to(media)) for i in ids}}
(run/'studio-candidates.json').write_text(json.dumps(history))
print('synthetic preview 165 seconds / 4950 frames',output.stat().st_size)
