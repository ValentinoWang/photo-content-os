import os,sys,json,subprocess,hashlib,shutil
from pathlib import Path
sys.path[:0]=['/Users/vsiyo/Desktop/创业项目/photo-content-os','/Users/vsiyo/Desktop/创业项目/photo-content-os/scripts']
from edit_backends.registry import get_backend
root=Path(__file__).parent/'export-temp';root.mkdir(exist_ok=True)
source=root/'source.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x25516b:s=288x512:r=30:d=4','-f','lavfi','-i','sine=frequency=660:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
suggestions=root/'suggest.json';suggestions.write_text(json.dumps({'duration':4,'precision':'word','suggestions':[]}))
subs=root/'source.srt';subs.write_text('1\n00:00:00,000 --> 00:00:04,000\n采纳与撤回验证\n')
b=get_backend('openfilm')
try:
 b.prepare_for_studio(output_dir=root/'project',source=source,suggestions_path=suggestions,subtitles=subs,project_id='ps3-export',project_revision=1)
 # Disk edit from the authoritative native API was already covered separately;
 # this export must honor the readback, not rebuild from the suggestion file.
 state=b.read_back(project_dir=root/'project')
 kw=state['render_kwargs']
 for key in ('source','suggestions_path','subtitles'):
  if kw[key]:kw[key]=Path(kw[key])
 result=b.render(output_dir=root/'result',**kw)
 assert result['status']=='candidate',result
 assert result['frames']==120,result
 out=Path('/Users/vsiyo/Desktop/创业项目/photo-content-os/agents-results/2026-10-12/ps3-studio/native-export.json')
 out.write_text(json.dumps({k:result[k] for k in ['status','editor_backend','frames','duration','project_id','project_revision']},indent=2))
 print(out.read_text())
finally:
 closed=b.close();assert closed['remaining_pids']==[],closed
 shutil.rmtree(root)
