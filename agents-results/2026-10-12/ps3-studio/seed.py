import sys,json,hashlib,re,subprocess
from pathlib import Path
sys.path[:0]=['/Users/vsiyo/Desktop/创业项目/photo-content-os','/Users/vsiyo/Desktop/创业项目/photo-content-os/scripts']
from studio.project_store import ProjectStore
root=Path(__file__).parent/'capture-temp';media=root/'media';media.mkdir(parents=True,exist_ok=True)
design=Path('/Users/vsiyo/Desktop/创业项目/自媒体创作Agent/docs/development/personal-deconstruction/studio-handoff.html')
fixture=json.loads(re.search(r'<script[^>]*id="suggestion-fixture"[^>]*>(.*?)</script>',design.read_text(),re.S)[1])
source=media/'talk.mp4'
if not source.exists():
 command=['ffmpeg','-v','error']
 for color,duration in [('0x25516b',21),('0x38523d',41),('0x634739',46),('0x4a456a',52),('0x275f64',71),('0x63494e',21)]:command+=['-f','lavfi','-i',f'color=c={color}:s=288x512:r=30:d={duration}']
 command+=['-f','lavfi','-i','sine=frequency=440:duration=252','-filter_complex','[0:v][1:v][2:v][3:v][4:v][5:v]concat=n=6:v=1:a=0[v]','-map','[v]','-map','6:a','-c:v','libx264','-crf','28','-pix_fmt','yuv420p','-c:a','aac','-b:a','32k','-shortest',str(source)]
 subprocess.run(command,check=True)
store=ProjectStore(root/'state');p=store.create_project(title='AI 不会“生成”视频，它在写代码',local_workspace=str(media))
identity={'photoProjectId':p['id'],'photoProjectRevision':p['revision'],'jobId':'ps3-capture-fixture'}
run=media/'runs'/hashlib.sha256(identity['jobId'].encode()).hexdigest()[:32];run.mkdir(parents=True,exist_ok=True)
starts=[0,21,62,108,160,231,252]
shots=[{'shot':{'shotId':f'{i+1:02}','startSeconds':starts[i],'endSeconds':starts[i+1]},'subtitle':f'合成镜头 {i+1}'} for i in range(6)]
animations=[];clips=[]
for sid,start,duration,title in [('02',31,8,'五步流程图'),('04',148,12,'自绘 vs 真实'),('05',172,10,'编号字卡')]:
 movie=media/f'animation-{sid}.webm'
 if not movie.exists():subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=black@0.0:s=144x512:r=30:d={duration},format=rgba,drawbox=x=10:y=200:w=124:h=80:color=0x4fb3bd@0.9:t=fill,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(between(X,10,133)*between(Y,200,279),230,0)'','-c:v','libvpx-vp9','-pix_fmt','yuva420p','-auto-alt-ref','0','-an',str(movie)],check=True)
 animations.append({'shotId':sid,'animationId':sid,'suggestedStartSeconds':start,'durationSeconds':duration,'requirement':title,'selectedLayout':'split_screen','timeBasis':'source'})
 clips.append({'id':sid,'status':'completed','file':str(movie),'fps':30})
descriptor={'scope':'video_handoff_v1','identity':identity,'shots':shots,'animations':animations,'narration':None}
(media/'video.json').write_text(json.dumps(descriptor,ensure_ascii=False))
subs=media/'talk.srt';subs.write_text('\n\n'.join(f'{i+1}\n00:{starts[i]//60:02}:{starts[i]%60:02},000 --> 00:{starts[i+1]//60:02}:{starts[i+1]%60:02},000\n合成镜头 {i+1}' for i in range(6))+'\n')
fixture['precision']='word';fixture['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
for s in fixture['suggestions']:s['evidence_text']=s.get('text','');s['animation_id']=s.get('animationId') or (str(s.get('animation_id')) if s.get('animation_id') else None)
# The design fixture names animation IDs in its animation_id field.
(run/'native-suggest.json').write_text(json.dumps(fixture,ensure_ascii=False))
(run/'native-teaching_clips.json').write_text(json.dumps({'status':'completed','clips':clips,'shots':[{'id':c['id'],'status':'completed','progress_frames':round(next(a['durationSeconds'] for a in animations if a['shotId']==c['id'])*30),'total_frames':round(next(a['durationSeconds'] for a in animations if a['shotId']==c['id'])*30)} for c in clips]}))
binding={'identity':{'project_id':p['id'],'project_revision':p['revision'],'job_id':identity['jobId']},'creative_store':str(store.path),'project_root':str(media),'steps':[],'source_refs':['talk.mp4','talk.srt'],'candidate_ref':'candidate.json'}
(root/'binding.json').write_text(json.dumps(binding))
(root/'capture.json').write_text(json.dumps({'projectId':p['id'],'identity':identity,'source':str(source),'root':str(root)}))
print('Fixture ready:',p['id'])
