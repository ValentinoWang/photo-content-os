import {mediaSummary, flowSteps, sec} from '/review-common.js';
export const seconds = n => {const t=Math.round(n||0);return Math.floor(t/60)+':'+String(t%60).padStart(2,'0');};
const labels={selected:'精选',usable:'可用',unused:'不用',rejected:'淘汰'};
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
export function createShotView(ctx) {
 const {api,notice,root,mark,refreshCatalog,D,esc,button}=ctx;
 let data,piece,focus=null,index=0,playing=false,muted=false,tab='usable',scene='all',expanded=new Set(),detail=false,poll,timer,photoStart=0;
 const selected=()=>data.shots.filter(s=>s.status==='selected');
 const current=()=>data.shots.find(s=>s.id===focus)||selected()[Math.min(index,selected().length-1)];
 const frame=s=>s.frames[Math.floor(s.frames.length/2)]||'';
 const thumb=s=>frame(s)?`<img src="${esc(frame(s))}" alt="" loading="lazy">`:'';
 const tags=s=>`${data.hook_candidates.some(h=>h.id===s.id)?'<span class="chip">开场候选</span>':''}${s.duplicate_of?'<span class="chip">重复备选</span>':''}${s.visual_flags?.has_occlusion?'<span class="chip">有遮挡</span>':''}`;
 function stop(){clearTimeout(poll);clearInterval(timer);$('#hero-v')?.pause();playing=false;}
 function flow() {
  const progress=data.progress?.status==='running';
  const currentLabel=progress?'正在挑':data.partial?'看图做了一半':data.shots.length?`${D(data.counts.selected)} 个精选 · ${data.confirmed?'已确认':'等你过目'}`:'还没开始';
  return flowSteps([['素材归档',mediaSummary(piece,D)],['挑镜头',currentLabel],['配乐卡点',data.confirmed?'下一阶段上线':'从音乐库选歌'],['出草稿','剪映或 ChatCut'],['人工精剪','在剪辑软件里改']].map(([title,note],i)=>({title,note,current:i===1,done:i===0&&piece.connected||i===1&&data.confirmed})), 'R208-STEPS');
 }
 function panel(s) {
  if(!s)return '';
  const list=selected(),i=list.findIndex(x=>x.id===s.id),m=s.metrics||{};
  return `<div><p class="eyebrow">${i>=0?`第 ${D(i+1)} / ${D(list.length)} 个精选`:`${labels[s.status]||''} · 不在精选里`}</p><h3 data-design-data>${esc(s.name)}</h3><p class="where" data-design-data>${esc(s.scene_name)} · ${s.kind==='photo'?'照片':sec(s.duration)+' 秒 · 原片第 '+sec(s.start_sec)+'–'+sec(s.end_sec)+' 秒'}</p><div class="verdict"><small>${s.status==='selected'?'为什么选它':'为什么没选它'}</small><p data-design-data>${esc(s.model_reason||(s.rejection_reasons||[]).join('、'))}</p></div><div class="tags">${tags(s)}</div>${s.status==='rejected'?'':`<div class="decide" data-design-id="R208-REV-decide"><small>不同意就改，改了以你为准</small><div class="seg">${['selected','usable','unused'].map(k=>`<button data-decision="${k}" aria-pressed="${s.status===k}">${labels[k]}</button>`).join('')}</div></div>`}<details class="more-d" ${detail?'open':''}><summary>打分细节</summary><div class="kv"><span>美感分</span><strong>${D(s.aesthetic?.score?.toFixed(2)??'—')}</strong></div><div class="kv"><span>主体清晰度</span><strong>${D(m.blur_variance==null?'—':Math.round(m.blur_variance))}<small>项目中间值 ${D(data.median==null?'—':Math.round(data.median))}</small></strong></div><div class="kv"><span>曝光</span><strong>${m.overexposed_fraction>.25||m.underexposed_fraction>.25?D(m.overexposed_fraction>m.underexposed_fraction?'偏亮':'偏暗'):'正常'}</strong></div><div class="kv"><span>抖动</span><strong>${m.shake_high_frequency==null?D(s.kind==='photo'?'不适用':'量不准'):m.shake_high_frequency>.008?'轻微抖动':'稳'}</strong></div>${m.motion_peak_time_sec!=null?`<div class="kv"><span>动作最猛</span><strong>原片第 ${D(sec(m.motion_peak_time_sec))} 秒<small><button class="link" data-seek="${Math.max(0,m.motion_peak_time_sec-(s.start_sec||0))}">跳到这一刻</button></small></strong></div>`:''}</details>${focus?'<div class="set-actions"><button class="link" data-back-reel>回到精选</button></div>':''}</div>`;
 }
 function board() {
  const list=selected(),scenes=[...new Set(list.map(s=>s.scene))];
  return scenes.map(k=>{const rows=list.filter(s=>s.scene===k);return `<div class="board-scene"><h3><span data-design-data>${esc(rows[0].scene_name)}</span><span data-design-data>${rows.length}</span></h3><div class="sb-row">${rows.map(s=>{const n=list.indexOf(s);return `<button class="sb" data-hero="${n}" aria-current="${!focus&&n===index}" data-design-data>${thumb(s)}<span class="n">${n+1}</span><span class="d">${s.kind==='photo'?'照片':sec(s.duration)+'″'}</span></button>`;}).join('')}</div></div>`;}).join('');
 }
 function alternatives() {
  const scenes=[...new Set(data.shots.map(s=>s.scene))];
  const matching=data.shots.filter(s=>s.status===tab&&(scene==='all'||s.scene===scene));
  return `<section class="alts" data-design-id="R208-REV-alts"><div class="alts-head"><h2 class="section-title">没进精选的<span>需要时点开，改成「精选」就会加进上面</span></h2><div class="tabs" role="group" aria-label="按结论看" data-design-id="R208-REV-tabs">${['usable','unused','rejected'].map(k=>`<button data-filter="${k}" aria-pressed="${tab===k}">${labels[k]}<i data-design-data>${data.counts[k]}</i></button>`).join('')}</div><div class="subfilters" data-design-id="R208-REV-subfilters"><button class="pill" data-scene="all" aria-pressed="${scene==='all'}">全部</button>${scenes.filter(k=>data.shots.some(s=>s.scene===k&&s.status===tab)).map(k=>`<button class="pill" data-scene="${esc(k)}" aria-pressed="${scene===k}">${D(data.shots.find(s=>s.scene===k).scene_name)}<i data-design-data>${data.shots.filter(s=>s.scene===k&&s.status===tab).length}</i></button>`).join('')}</div></div><div class="list" data-design-id="R208-REV-list">${scenes.map(k=>{const rows=matching.filter(s=>s.scene===k);if(!rows.length)return '';return `<section><div class="scene-head"><h2 data-design-data>${esc(rows[0].scene_name)}</h2><span>${D(rows.length)} 条${labels[tab]} · 共 ${D(data.shots.filter(s=>s.scene===k).length)} 条</span></div><div class="grid">${rows.slice(0,expanded.has(k)?rows.length:8).map(s=>`<button class="card" data-shot="${esc(s.id)}" aria-selected="${focus===s.id}"><span class="strip ${s.kind==='photo'?'one':''}" ${s.kind==='video'?`data-hover="${esc(s.id)}"`:''}>${s.frames.map(f=>`<img src="${esc(f)}" alt="" loading="lazy">`).join('')}<span class="len" data-design-data>${s.kind==='photo'?'照片':'▶ '+sec(s.duration)+' 秒'}</span></span><span class="card-body"><b data-design-data>${esc(s.name)}</b><span class="reason" data-design-data>${esc(s.model_reason||(s.rejection_reasons||[]).join('、'))}</span><span class="tags">${tags(s)}</span></span></button>`).join('')}</div>${rows.length>8&&!expanded.has(k)?`<button class="more" data-more="${esc(k)}">再看 ${D(rows.length-8)} 条</button>`:''}</section>`;}).join('')}</div></section>`;
 }
 function progress(t) {
  const list=selected(),total=list.reduce((a,s)=>a+s.duration,0),elapsed=focus?0:list.slice(0,index).reduce((a,s)=>a+s.duration,0)+t;
  const pos=$('#hero-pos');if(pos)pos.innerHTML=focus?`精选 ${D(list.length)} 个 · 共 ${D(seconds(total))}`:`第 ${D(index+1)} / ${D(list.length)} 个 · ${D(seconds(elapsed))} / ${D(seconds(total))}`;
  $$('#hero-prog button').forEach((b,i)=>{b.firstElementChild.style.width=(focus?0:i<index?100:i>index?0:Math.min(100,t/(list[i].duration||1)*100))+'%';});
 }
 function paintHero() {
  clearInterval(timer);const s=current();if(!s)return;const stage=$('#hero-stage');if(!stage)return;
  stage.innerHTML=(s.kind==='photo'?`<img src="${esc(s.preview)}" alt="">`:`<video id="hero-v" src="${esc(s.preview)}" poster="${esc(frame(s))}" playsinline ${focus?'loop':''}></video>`)+(!playing?'<button class="big-play" data-toggle aria-label="播放">▶</button>':'')+(focus?`<span class="stage-tag">${labels[s.status]}镜头，不在精选里</span>`:'');
  $('#shot-panel').innerHTML=panel(s);$('#hero-play').textContent=playing?'❚❚':'▶';$('#hero-play').setAttribute('aria-label',playing?'暂停':'播放');
  $$('#hero-board .sb').forEach(b=>b.setAttribute('aria-current',String(!focus&&Number(b.dataset.hero)===index)));
  const v=$('#hero-v');
  if(v){v.muted=muted;v.ontimeupdate=()=>progress(v.currentTime);v.onended=next;if(playing)v.play().catch(e=>{playing=false;notice(e.message,true);paintHero();});}
  else if(playing){photoStart=performance.now();timer=setInterval(()=>{const t=(performance.now()-photoStart)/1000;progress(t);if(t>=2.5){clearInterval(timer);if(!focus)next();}},50);}
  progress(0);bindHero();
 }
 function next(){if(focus)return;if(index<selected().length-1){index++;paintHero();}else{playing=false;paintHero();}}
 function bindHero() {
  $$('[data-toggle]').forEach(b=>b.onclick=()=>{playing=!playing;paintHero();});
  $$('.more-d').forEach(d=>d.ontoggle=()=>{detail=d.open;});
  $$('[data-decision]').forEach(b=>b.onclick=async()=>{
   const s=current(),before=structuredClone(data);const status=b.dataset.decision;
   if(status===s.status)return;
   // User choice responds immediately; the server remains the persistence authority.
   data.shots.find(r=>r.id===s.id).status=status;data.confirmed=false;focus=status==='selected'?null:s.id;
   data.counts=Object.fromEntries(Object.keys(labels).map(k=>[k,data.shots.filter(r=>r.status===k).length]));data.duration=selected().reduce((a,r)=>a+r.duration,0);index=Math.max(0,selected().findIndex(r=>r.id===s.id));playing=false;paint();
   try{data=await api(`/api/review/pieces/${piece.id}/decisions`,{method:'POST',body:{expectedVersion:before.version,shotId:s.id,status}});await refreshCatalog();paint();}catch(e){data=before;paint();notice(e.message,true);}
  });
  $('[data-back-reel]')?.addEventListener('click',()=>{focus=null;paintHero();});
  $$('[data-seek]').forEach(b=>b.onclick=()=>{const v=$('#hero-v');if(v){v.currentTime=Number(b.dataset.seek);playing=true;v.play().catch(e=>notice(e.message,true));}});
 }
 function paint() {
  const tabs=$('.ptabs')?.outerHTML||'';const running=data.progress?.status==='running';const empty=!data.shots.length;
  const name=running?'piece-running':empty?(piece.versions?'piece-empty':piece.videos?'piece-not-started':'piece-not-started-photos'):data.partial?'piece-partial':data.confirmed?'piece-confirmed':focus?'piece-review-alt':'piece-review';mark(name);root().classList.add('single');
  const interrupted=['failed','stopped'].includes(data.progress?.status)||['failed','stopped'].includes(data.run_status);
  const warning=interrupted?`<div class="attention full" role="alert" data-design-id="R208-REV-partial"><div><strong>挑镜头停在一半</strong><p>${data.progress?.reason?D(data.progress.reason)+' ':''}已做完的部分都留着，继续时不会重做。</p></div><div class="actions">${button('继续看图','data-job="resume"')}${button('重新挑选','data-job="restart"')}</div></div>`:'';
  if(empty&&!running){root().innerHTML=tabs+flow()+warning+`<div class="empty" data-design-id="R208-REV-empty"><h2>先挑镜头，再配乐卡点</h2>${piece.versions?`<p><span>这件作品已经出过 ${D(piece.versions)} 版（手工剪的），右上角能看。想让 AI 重新挑一遍、配乐卡点，从这里开始。</span></p>`:''}<p>${piece.videos?'AI 会把每段视频切成镜头，先在本机量清晰度、曝光和抖动，再让大模型看图，挑出这条视频要用的精选。原素材只读，不会被改动。':'AI 会先在本机量每张照片的清晰度和曝光，再让大模型看图，挑出这条视频要用的精选。原素材只读，不会被改动。'}</p><div class="facts">${piece.videos?`<span><b>${D(piece.videos)}</b>段视频</span>`:''}${piece.photos?`<span><b>${D(piece.photos)}</b>张照片</span>`:''}</div>${interrupted?'':`<div class="actions">${button('开始挑镜头','data-job="start"',true)}</div>`}</div>`;bind();return;}
  const head=(title,lede,actions)=>`<div class="stephead full" data-design-id="R208-REV-head"><div><p class="eyebrow">第 2 步 · 挑镜头</p><h2>${title}</h2><p>${lede}</p></div><div class="actions">${actions}</div></div>`;
  if(running){const p=data.progress, phases=[['local','切镜头、体检'],['model','大模型看图'],['hooks','挑开场候选']],at=phases.findIndex(x=>x[0]===p.phase);
   root().innerHTML=tabs+flow()+head('正在挑镜头','看图做完才知道哪些进精选。可以先去做别的，做完会在工作台提醒你。',button('停止','data-job="stop"'))+`<div class="review-progress full" data-design-id="R208-REV-progress"><div class="steps">${phases.map(([key,label],i)=>`<div class="step"><b>${label}</b><span data-design-data>${i===at?p.completed+' / '+p.total:''}</span><div class="bar"><i data-percent="${i<at?100:i===at&&p.total?p.completed/p.total*100:0}"></i></div></div>`).join('')}</div></div><section class="pending full" data-design-id="R208-REV-measured"><h3>已经切好的镜头 <span data-design-data>${data.shots.length}</span> 个 · 等看图</h3><div class="mini">${data.shots.slice(0,expanded.has('__measured')?data.shots.length:36).map(s=>`<figure>${thumb(s)}<figcaption>${s.kind==='photo'?D('照片'):D(sec(s.duration))+' 秒'}</figcaption></figure>`).join('')}</div>${data.shots.length>36&&!expanded.has('__measured')?`<button class="more" data-more="__measured">再看 ${D(data.shots.length-36)} 个</button>`:''}</section>`;bind();return;}
  const list=selected();index=Math.min(index,Math.max(0,list.length-1));
  const title=data.partial?`已经挑出 ${D(list.length)} 个镜头`:data.confirmed?`精选已确认：${D(list.length)} 个镜头`:`AI 给这条视频挑了 ${D(list.length)} 个镜头`;
  const lede=data.partial?'看图做完之前不能确认。已看完的部分可以先播一遍。':data.confirmed?'配乐卡点下一阶段上线，到时直接用这些镜头。之后再改精选，需要重新确认。':`串起来 ${D(seconds(data.duration))}。先从头看一遍，不合适的在右边改成「可用」或「不用」；最下面还有 ${D(data.counts.usable)} 个可用的备选。确认后，下一步配乐卡点会从<button class="link" data-go="music">音乐库</button>挑一首歌，按拍子把这些镜头排起来。`;
  root().innerHTML=tabs+flow()+warning+(!interrupted&&data.partial?`<div class="attention full" role="alert" data-design-id="R208-REV-partial"><div><strong>看图只做完 ${D(data.model_progress?.completed||0)} / ${D(data.model_progress?.total||0)} 页</strong><p>还有 ${D(data.shots.filter(s=>!s.status).length)} 个镜头（${D([...new Set(data.shots.filter(s=>!s.status).map(s=>s.scene_name))].join('、'))}那一组）没有结论，先不列出来。本地体检的结果都留着，继续时不会重做。</p></div>${button('继续看图','data-job="resume"')}</div>`:'')+head(title,lede,(interrupted?'':button('重新挑选','data-job="restart"'))+(!data.partial&&!data.confirmed?button('确认精选','data-confirm',true):''))+`<section class="hero full" data-design-id="R208-REV-hero"><div class="stage-wrap"><div class="stage" id="hero-stage"></div><div class="prog" id="hero-prog">${list.map((s,i)=>`<button data-hero="${i}" data-design-data data-duration="${s.duration}"><i></i></button>`).join('')}</div><div class="hero-ctl"><button class="btn-round" id="hero-play" data-toggle aria-label="播放">▶</button>${button('上一个','data-hstep="-1"')}${button('下一个','data-hstep="1"')}<button class="btn" id="hero-mute">${muted?'声音关':'声音开'}</button><span class="hero-pos" id="hero-pos"></span></div></div><aside class="shot-panel" id="shot-panel" data-design-id="R208-REV-shot"></aside></section><section class="board full" id="hero-board" data-design-id="R208-REV-board"><h2 class="section-title">精选顺序<span>按场景排，配乐卡点时会按节奏重排</span></h2>${board()}</section>${alternatives()}`;
  bind();paintHero();
 }
 function bind() {
  $$('[data-duration]').forEach(n=>n.style.flex=`${n.dataset.duration} 1 0`);
  $$('[data-percent]').forEach(n=>n.style.width=n.dataset.percent+'%');
  ctx.common();
  $$('[data-ptab]').forEach(b=>b.onclick=()=>{try{localStorage.setItem('studio-piece-tab:'+piece.id,b.dataset.ptab);}catch{}location.hash=new URLSearchParams({...ctx.route(),ptab:b.dataset.ptab});});
  $$('[data-filter]').forEach(b=>b.onclick=()=>{tab=b.dataset.filter;scene='all';paint();});
  $$('[data-scene]').forEach(b=>b.onclick=()=>{scene=b.dataset.scene;paint();});
  $$('[data-more]').forEach(b=>b.onclick=()=>{expanded.add(b.dataset.more);paint();});
  $$('[data-hero]').forEach(b=>b.onclick=()=>{focus=null;index=Number(b.dataset.hero);paintHero();});
  $$('[data-hstep]').forEach(b=>b.onclick=()=>{focus=null;index=Math.max(0,Math.min(selected().length-1,index+Number(b.dataset.hstep)));paintHero();});
  $('#hero-mute')?.addEventListener('click',()=>{muted=!muted;const v=$('#hero-v');if(v)v.muted=muted;$('#hero-mute').textContent=muted?'声音关':'声音开';});
  $$('[data-shot]').forEach(b=>b.onclick=()=>{focus=b.dataset.shot;playing=true;mark('piece-review-alt');paintHero();$('.hero').scrollIntoView({block:'start'});});
  $$('[data-hover]').forEach(el=>{el.onmouseenter=()=>{const s=data.shots.find(s=>s.id===el.dataset.hover);if(el.querySelector('video'))return;const v=document.createElement('video');v.src=s.preview;v.muted=true;v.loop=true;v.playsInline=true;el.append(v);v.play().catch(()=>v.remove());};el.onmouseleave=()=>el.querySelector('video')?.remove();});
  $('[data-confirm]')?.addEventListener('click',async()=>{try{data=await api(`/api/review/pieces/${piece.id}/decisions`,{method:'POST',body:{expectedVersion:data.version,confirm:true}});await refreshCatalog();paint();}catch(e){notice(e.message,true);}});
  $$('[data-job]').forEach(b=>b.onclick=async()=>{try{await api(`/api/review/pieces/${piece.id}/jobs`,{method:'POST',body:{action:b.dataset.job}});await reload();}catch(e){notice(e.message,true);}});
 }
 async function reload(){const identity=piece.id;const next=await api(`/api/review/pieces/${identity}/shots`);if(ctx.route().view!=='piece'||ctx.route().ptab!=='vlog'||ctx.route().piece!==identity||piece.id!==identity)return;data=next;paint();if(data.progress?.status==='running')poll=setTimeout(reload,1200);else await refreshCatalog();}
 return {stop,async render(p,tabs){if(piece?.id!==p.id){focus=null;index=0;expanded=new Set();}piece=p;root().innerHTML=tabs;if(!p.connected){mark('piece-empty');root().classList.add('single');root().innerHTML=tabs+`<div class="empty" data-design-id="R208-REV-empty"><h2>这件作品还没连上素材文件夹</h2><p>要挑镜头，先给它连上本机的素材文件夹。按脚本做视频不受影响。</p></div>`;return;}await reload();}};
}
