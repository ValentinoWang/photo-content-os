import { failureMessage, safeText, shotSeconds, mmss, writingSeconds, jobUrl, posterUrl, shouldPoll } from './direct-view.js';

const views=new WeakMap();
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean=value=>esc(safeText(value));
const D=value=>`<span data-design-data>${clean(value)}</span>`;
const failures={instruction_too_long:'要改的超过 200 字了，删短一点再重写。',version_not_found:'这一版找不到了，刷新一下再选。',sample_not_found:'这个样例已经不在了，刷新一下。',proposal_not_found:'这条草稿已经处理过，刷新一下。',proposal_not_ready:'这条草稿已经处理过，刷新一下。',look_failed:'Opus 这次没看成画面：读不到渲染出的图。你照样可以自己点。',verify_failed:'Opus 这次没核对成，两版照样可以比。'};
const message=code=>failures[code]||failureMessage(code);
const ACTS=[['main','做主角'],['dim','缩小变灰'],['del','删掉'],['short','字改短']];
const WHOLE=[['space','太空或挤在上面','主画面放在页眉和字幕之间居中，下面空白不超过三成。'],['color','颜色乱','只用一个强调色，只标结论；其余用主色和灰。'],['sync','跟口播对不上','口播说到哪一部分，画面才出现哪一部分。']];
const actText=(action,name)=>({main:`${name}做成这一镜唯一的主角：数字 150px 以上，柱子至少占画面高度的四分之一。`,dim:`${name}缩小一档、改成灰色，不和主角抢。`,del:`删掉${name}。`,short:`${name}只留关键词，不超过 8 个字。`})[action];
const rules=[['animation_cut_short','动画在这一镜时长内做完'],['header_missing','页眉标好了'],['subtitle_band','字幕带里没放字'],['external_resource','不读网络和外部文件'],['forbidden_runtime','不用定时器和随机数']];
const linesFor=draft=>[...draft.items.map(({key,...line})=>line),...(draft.extra.trim()?[{text:draft.extra.trim(),own:true}]:[])];
const decisionKey=(projectId,job,shot)=>`direct-version:${projectId}:${job.jobId}:${shot.shotId}:${shot.currentVersion}`;
function accepted(key){try{return localStorage.getItem(key)==='yes';}catch{return false;}}

function positionMarkers(stage){
  const frame=stage.getBoundingClientRect(),gap=2,placed=[];
  if(!frame.width||!frame.height)return;
  const size=frame.width<=300.1?16:20;
  stage.style.setProperty('--rv-marker-size',`${size}px`);
  stage.style.setProperty('--rv-marker-font',`${size*11.5/20}px`);
  const area=(a,b)=>Math.max(0,Math.min(a.left+a.width,b.left+b.width)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.top+a.height,b.top+b.height)-Math.max(a.top,b.top));
  const hosts=[...stage.querySelectorAll('.rv-hs')],blocks=hosts.map(host=>host.getBoundingClientRect());
  for(const host of hosts){
    const box=host.getBoundingClientRect();
    const markers=[...host.children].filter(e=>e.matches('.rv-num,.rv-pin')).sort((a,b)=>Number(b.matches('.rv-num'))-Number(a.matches('.rv-num')));
    for(const marker of markers){
      const number=marker.matches('.rv-num'),width=marker.offsetWidth,height=marker.offsetHeight;
      const left={left:box.left-gap-width,top:box.top,width,height,side:'left'},right={left:box.right+gap,top:box.top,width,height,side:'right'};
      const top={left:number?box.left:box.right-width,top:box.top-gap-height,width,height,side:'top'};
      const bottom={left:number?box.left:box.right-width,top:box.bottom+gap,width,height,side:'bottom'};
      const candidates=number?[left,top,bottom,right]:[right,top,bottom,left];
      const inside=p=>p.left>=frame.left&&p.top>=frame.top&&p.left+p.width<=frame.right&&p.top+p.height<=frame.bottom;
      const available=candidates.filter(p=>inside(p)&&!area(p,box)&&placed.every(other=>!area(p,other)));
      const scored=available.map(p=>({...p,overlap:blocks.reduce((sum,b)=>sum+area(p,b),0)}));
      // Keep candidate order for clear positions and ties; only unavoidable block overlap is minimized.
      const best=scored.find(p=>p.overlap<.01)||scored.reduce((best,p)=>!best||p.overlap<best.overlap?p:best,null);
      const corner={left:number?box.left+host.clientLeft-9*size/20:box.right-host.clientLeft+9*size/20-width,top:box.top+host.clientTop-9*size/20,width,height,side:'corner'};
      const position=best||corner;
      marker.style.setProperty('left',`${position.left-box.left-host.clientLeft}px`);
      marker.style.setProperty('top',`${position.top-box.top-host.clientTop}px`);
      marker.style.setProperty('right','auto');marker.dataset.placement=position.side;
      marker.dataset.placementMode=best?(best.overlap<.01?'clear':'minimum-overlap'):'corner';placed.push(position);
    }
  }
}

export function renderShotDetail(container,{job,shot,projectId,api,onRewrite}) {
  let state=views.get(container);
  if(!state||state.jobId!==job.jobId){clearTimeout(state?.timer);state?.markerObserver?.disconnect();state={jobId:job.jobId,key:null,drafts:new Map(),codes:new Map()};views.set(container,state);}
  const previous=container.querySelector('[data-extra]'),focus=previous===container.ownerDocument.activeElement;
  const selection=focus?[previous.selectionStart,previous.selectionEnd,previous.selectionDirection]:null;
  const old=state.drafts.get(state.shotId);
  if(old){if(previous)old.extra=previous.value;for(const details of container.querySelectorAll('details'))old.open[details.dataset.designId]=details.open;}
  let draft=state.drafts.get(shot.shotId);
  if(!draft){draft={pick:'',items:[],extra:'',open:{},busy:false,error:'',sentCount:null,acceptedVersion:null};state.drafts.set(shot.shotId,draft);}
  const versions=shot.versions||[],current=versions.find(v=>v.version===shot.currentVersion),latest=versions.reduce((a,b)=>b.version>a.version?b:a,{version:0});
  const pending=['writing','rendering'].includes(shot.status),locked=pending||job.output?.status==='composing'||job.failureCode==='claude_cli_unavailable'||draft.busy;
  // R276 stops job polling once rendering ends; look/verify may still be running.
  clearTimeout(state.timer);
  if(!shouldPoll(job)&&(shot.look?.status==='running'||current?.verify?.status==='running'))state.timer=setTimeout(()=>{if(container.isConnected&&views.get(container)===state)onRewrite(shot.shotId);},2000);
  const key=JSON.stringify([shot.shotId,shot.status,shot.posterRevision,shot.checks,shot.attempts,shot.currentVersion,versions.map(v=>[v.version,v.posterRevision,v.verify?.status]),shot.boxes,shot.look?.status,shot.look?.findings,shot.sample,locked,draft.acceptedVersion]);
  if(state.key===key){const clock=container.querySelector('[data-busy-clock]');if(clock)clock.textContent=busyText();return;}
  const sameShot=state.shotId===shot.shotId;
  state.shotId=shot.shotId;state.key=key;
  const base=`${jobUrl(projectId,job.jobId)}/shots/${encodeURIComponent(shot.shotId)}`;
  const boxes=shot.boxes||[],findings=shot.look?.status==='done'?shot.look.findings||[]:[];
  if(draft.pick&&!boxes.some(b=>b.id===draft.pick))draft.pick='';
  const compare=!pending&&shot.currentVersion===latest.version&&current?.request?.lines?.length>0&&current.baseVersion!=null&&draft.acceptedVersion!==shot.currentVersion&&!accepted(decisionKey(projectId,job,shot));
  const reverted=!pending&&shot.currentVersion<latest.version&&latest.baseVersion===shot.currentVersion;
  const disabled=locked?'disabled':'';
  function busyText(){const seconds=writingSeconds(shot);return `${draft.sentCount?`正在按 ${draft.sentCount} 处改法重写`:'正在重写这一镜'}${seconds==null?'':` · ${mmss(seconds)}`}`;}
  function stage({version=null,interactive=true,numbers=true,look=true}={}){
    const src=version==null?posterUrl(projectId,job,shot):`${base}/poster.jpg?version=${encodeURIComponent(version)}`;
    const markerLines=compare?current.request.lines:linesFor(draft);
    return `<div class="rv-stage">${shot.posterRevision>0?`<img src="${src}" alt="">`:'<div class="rv-no-poster" data-design-data>这一镜还没有画面</div>'}${boxes.map(b=>{
      const index=numbers?markerLines.findIndex(l=>l.boxId===b.id):-1,pin=look&&findings.some(f=>f.boxId===b.id)&&index<0;
      const inside=`${pin?'<i class="rv-pin" aria-hidden="true">!</i>':''}${index>=0?`<b class="rv-num${compare?' ok':''}" data-design-data>${index+1}</b>`:''}`;
      return interactive?`<button class="rv-hs${draft.pick===b.id?' on':''}" data-box="${esc(b.id)}" data-design-data aria-label="${clean(b.name)}" aria-pressed="${draft.pick===b.id}" ${disabled}>${inside}</button>`:(`<span class="rv-hs ro" data-box="${esc(b.id)}">${inside}</span>`);
    }).join('')}${pending?`<div class="rv-busy" data-design-id="RV-BUSY"><b data-busy-clock data-design-data>${busyText()}</b></div>`:''}</div>`;
  }
  function inspector(){
    if(shot.look?.status==='running')return '<section class="rv-insp empty" data-design-id="RV-INSPECT"><h4>Opus 正在看这一镜的画面</h4></section>';
    const box=boxes.find(b=>b.id===draft.pick);
    if(box){const fs=findings.filter(f=>f.boxId===box.id),selected=draft.items.find(l=>l.boxId===box.id);
      return `<section class="rv-insp" data-design-id="RV-INSPECT"><header><small>选中</small><h4 data-design-data>${clean(box.name)}</h4><button class="rv-x" data-unpick aria-label="不选了" ${disabled}>×</button></header>${fs.map(f=>`<p class="rv-note" data-design-data><b>Opus 看出 · ${clean(f.kind)}</b>${clean(f.text)}</p>`).join('')}<div class="rv-acts" role="group" aria-label="这一块怎么改">${ACTS.map(([action,label])=>`<button class="rv-act" data-act="${action}" aria-pressed="${selected?.action===action}" ${disabled}>${label}${fs.some(f=>f.suggest===action)?'<em>建议</em>':''}</button>`).join('')}</div></section>`;
    }
    const count=findings.filter(f=>boxes.some(b=>b.id===f.boxId)).length;
    const lead=!boxes.length?`<button class="btn btn--sm" data-look ${disabled}>让 Opus 看一遍</button>`:pending?'':shot.look?.status==='failed'?`<p class="rv-warnline">${message('look_failed')}<button class="rv-link" data-look>重试</button></p>`:count?`<p>画面上 <i class="rv-pin inline" aria-hidden="true">!</i> ${D(`是 Opus 自己看出的 ${count} 处问题，点开看它怎么说。`)}</p>`:shot.look?.status==='done'?'<p>Opus 看了这一镜，没看出要改的地方。</p>':'';
    return `<section class="rv-insp empty" data-design-id="RV-INSPECT"><h4>${!boxes.length?'这一镜还没有可以点的块':pending?'正在重写，先别点':'在左边画面上点要改的地方'}</h4>${lead}</section>`;
  }
  function changeList(){return `<section class="rv-list" data-design-id="RV-BRIEF"><header><h4>要改的</h4><span data-item-count data-design-data></span></header><div data-items></div><div class="rv-whole" data-design-id="RV-WHOLE"><small>整镜</small>${WHOLE.map(([issue,label])=>`<button class="rv-chip" data-whole="${issue}" aria-pressed="${draft.items.some(l=>l.issue===issue)}" ${disabled}>${label}</button>`).join('')}</div><input id="dv-ask" type="text" data-extra placeholder="再补一句（可不填），例：底色不动" ${disabled}><footer><span class="rv-count" aria-live="polite" data-design-data></span><button class="btn btn--pri rv-go" data-revise data-design-data></button></footer><small class="rv-foot" data-design-data>只重写这一镜，其他${job.shots.length-1===6?'六':Math.max(0,job.shots.length-1)}镜不动。</small></section>`;}
  function changed(){const verify=current.verify;return `<section class="rv-list done" data-design-id="RV-CHANGED"><header><h4>这次改的</h4><span>${verify?.status==='done'?'Opus 对着新画面核过':verify?.status==='running'?'正在核对':''}</span></header>${verify?.status==='failed'?`<p class="rv-warnline">${message('verify_failed')}</p>`:''}<ol>${current.request.lines.map((line,i)=>{const item=verify?.items?.find(v=>v.index===i);return `<li><b class="rv-num ok" data-design-data>${i+1}</b><p data-design-data>${clean(line.text)}${verify?.status==='done'&&item?.result==='missed'?`<span class="rv-reason">${clean(item.reason)}</span>`:''}</p>${verify?.status==='running'?'<em>正在核对</em>':verify?.status==='done'&&item?`<em class="${item.result==='done'?'ok':'w'}">${item.result==='done'?'做到了':'没做到'}</em>`:''}</li>`;}).join('')}</ol></section>`;}
  function more(){const errors=shot.checks?.errors||[],warnings=shot.checks?.warnings||[],count=errors.length+warnings.length;
    return `<div class="rv-more" ${locked?'inert':''}><details data-design-id="DV-SAY"><summary>口播${D(safeText(shot.dialogue).slice(0,22)+'…')}</summary><p data-design-data>${clean(shot.dialogue)}</p></details><details data-design-id="DV-CHECKS"><summary>规则检查<span class="${count?'w':''}" data-design-data>${count?`${count} 项要看`:'都过了'}</span></summary><ul>${[...errors,...warnings].map(e=>`<li class="w" data-design-data>${clean(e.message||message(e.code))}</li>`).join('')}${shot.codeChars>0?rules.filter(([code])=>!errors.some(e=>e.code===code)).map(([,label])=>`<li>${label}</li>`).join(''):''}</ul></details><details data-design-id="DV-CODE"><summary>代码${D(`${Number.isFinite(shot.codeChars)?shot.codeChars.toLocaleString():0} 字 · 上限 100,000`)}</summary><pre data-design-data></pre></details></div>`;
  }
  const ver=pending?`第 ${shot.currentVersion||1} 版 · 正在写第 ${latest.version+1} 版`:versions.length>1?`${reverted?'用第':'第'} ${shot.currentVersion} 版 · 共 ${versions.length} 版`:`第 ${shot.currentVersion||1} 版`;
  const head=`<header class="rv-head"><div><h3 data-design-data>第 ${clean(shot.shotId)} 镜</h3>${D(`${shot.measuredSeconds!=null?'配音实测':'按字数估'} ${shotSeconds(shot).toFixed(1)} 秒 · ${ver}`)}</div><button class="rv-rate" data-sample data-design-id="RV-RATE" aria-pressed="${!!shot.sample}" ${disabled}>${shot.sample?'♥ 已存为样例':'♡ 这镜好'}</button></header>`;
  container.innerHTML=`<section class="rv-detail${compare?' cmp':''}" data-design-id="DV-DETAIL">${compare?head:''}<div class="dv-pv" ${compare?'data-design-id="RV-COMPARE"':''}>${compare?`<div class="rv-pair"><figure><figcaption data-design-data>第 ${current.baseVersion} 版</figcaption>${stage({version:current.baseVersion,interactive:false,numbers:false,look:false})}</figure><figure class="new"><figcaption data-design-data>第 ${current.version} 版 · 按你的 ${current.request.lines.length} 处改法</figcaption>${stage({interactive:false,look:false})}</figure></div><div class="rv-decide"><button class="btn" data-previous ${disabled}>退回第 ${current.baseVersion} 版</button><button class="btn btn--pri" data-keep ${disabled}>用第 ${current.version} 版</button></div>`:`${stage()}<p class="dv-pvnote" data-design-id="DV-PVNOTE" data-design-data>关键帧 · 这一镜 ${shotSeconds(shot).toFixed(1)} 秒处的 80%</p>`}</div><div class="rv-side">${compare?'':head}${reverted?`<p class="rv-back" data-design-id="RV-CHANGED" data-design-data>已退回第 ${shot.currentVersion} 版。第 ${latest.version} 版留着，你点的问题已经记下。</p>`:''}${compare?changed():inspector()+findings.filter(f=>f.boxId==null).map(f=>`<p class="rv-note" data-design-data><b>Opus 看出 · ${clean(f.kind)}</b>${clean(f.text)}</p>`).join('')+changeList()}<p data-detail-error role="alert" data-design-data ${draft.error?'':'hidden'}>${esc(draft.error)}</p>${more()}</div></section>`;
  for(const el of container.querySelectorAll('[data-box]')){const box=boxes.find(b=>b.id===el.dataset.box);for(const [prop,value,total] of [['left',box.x,1080],['top',box.y,1920],['width',box.w,1080],['height',box.h,1920]])el.style.setProperty(prop,`${value/total*100}%`);}
  state.markerObserver?.disconnect();
  const stages=[...container.querySelectorAll('.rv-stage')];
  state.markerObserver=new ResizeObserver(()=>{if(!container.isConnected){state.markerObserver.disconnect();return;}for(const stage of stages)positionMarkers(stage);});
  for(const stage of stages){positionMarkers(stage);state.markerObserver.observe(stage);}
  const redraw=()=>{state.key=null;renderShotDetail(container,{job,shot,projectId,api,onRewrite});};
  const input=container.querySelector('[data-extra]');
  function updateBrief(){if(!input)return;const lines=linesFor(draft),count=lines.reduce((n,l)=>n+Array.from(l.text).length,0),retry=!lines.length&&['failed','interrupted'].includes(shot.status);
    container.querySelector('[data-item-count]').textContent=draft.items.length?`${draft.items.length} 处`:'';
    container.querySelector('[data-items]').innerHTML=draft.items.length?`<ol>${draft.items.map((l,i)=>`<li><b class="rv-num" data-design-data>${i+1}</b><p data-design-data>${clean(l.text)}</p>${pending?'':`<button class="rv-x" data-drop="${i}" aria-label="去掉这一条" ${disabled}>×</button>`}</li>`).join('')}</ol>`:'<p class="rv-empty">还没有。点画面上的一块，或者选下面整镜的问题。</p>';
    container.querySelectorAll('[data-drop]').forEach(b=>b.onclick=()=>{draft.items.splice(Number(b.dataset.drop),1);redraw();});
    const counter=container.querySelector('.rv-count');counter.classList.toggle('over',count>200);counter.textContent=lines.length?`${count} / 200 字${count>200?' · 超了，去掉一两条':''}`:'';
    const go=container.querySelector('[data-revise]');go.disabled=locked||count>200||(!lines.length&&!retry);go.textContent=pending?`正在重写${writingSeconds(shot)==null?'':` · ${mmss(writingSeconds(shot))}`}`:retry?'重试这一镜':'重写这一镜';
  }
  if(input){input.value=draft.extra;input.oninput=()=>{draft.extra=input.value;updateBrief();};updateBrief();if(sameShot&&focus&&!input.disabled){input.focus({preventScroll:true});input.setSelectionRange(...selection);}}
  container.querySelectorAll('button[data-box]').forEach(b=>b.onclick=()=>{draft.pick=draft.pick===b.dataset.box?'':b.dataset.box;redraw();});
  container.querySelector('[data-unpick]')?.addEventListener('click',()=>{draft.pick='';redraw();});
  container.querySelectorAll('[data-act]').forEach(b=>b.onclick=()=>{const box=boxes.find(v=>v.id===draft.pick),index=draft.items.findIndex(l=>l.boxId===box.id),action=b.dataset.act;if(index>=0&&draft.items[index].action===action)draft.items.splice(index,1);else {const line={key:box.id,text:actText(action,box.name),boxId:box.id,action};if(index<0)draft.items.push(line);else draft.items[index]=line;}redraw();});
  container.querySelectorAll('[data-whole]').forEach(b=>b.onclick=()=>{const issue=b.dataset.whole,index=draft.items.findIndex(l=>l.issue===issue);if(index>=0)draft.items.splice(index,1);else draft.items.push({key:`whole:${issue}`,text:WHOLE.find(w=>w[0]===issue)[2],issue});redraw();});
  async function mutate(suffix,body={},method='POST'){
    if(locked)return;draft.busy=true;draft.error='';redraw();
    try{const bootstrap=await api('/api/bootstrap');const response=await fetch(`${base}/${suffix}`,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':bootstrap.csrfToken},...(method==='DELETE'?{}:{body:JSON.stringify(body)})});const payload=await response.json();if(!response.ok||!payload.ok){draft.error=message(payload.error?.code);return;}
      if(suffix==='revise'){draft.sentCount=body.lines.length;draft.pick='';}
      if(suffix==='rewrite')draft.sentCount=null;
      if(payload.job){job=payload.job;shot=job.shots.find(s=>s.shotId===shot.shotId)||shot;}
      if(container.isConnected)onRewrite(shot.shotId);
    }catch{draft.error=message();}finally{draft.busy=false;if(container.isConnected&&state.shotId===shot.shotId){state.key=null;renderShotDetail(container,{job,shot,projectId,api,onRewrite});}}
  }
  container.querySelector('[data-revise]')?.addEventListener('click',()=>{const lines=linesFor(draft);if(!container.querySelector('[data-revise]').disabled)mutate(lines.length?'revise':'rewrite',lines.length?{lines}:{instruction:''});});
  container.querySelector('[data-look]')?.addEventListener('click',()=>mutate('look'));
  container.querySelector('[data-sample]')?.addEventListener('click',()=>mutate('sample',{},shot.sample?'DELETE':'PUT'));
  container.querySelector('[data-previous]')?.addEventListener('click',()=>mutate('current',{version:current.baseVersion}));
  container.querySelector('[data-keep]')?.addEventListener('click',()=>{draft.acceptedVersion=shot.currentVersion;draft.items=[];draft.extra='';const field=container.querySelector('[data-extra]');if(field)field.value='';try{localStorage.setItem(decisionKey(projectId,job,shot),'yes');}catch{}redraw();});
  for(const details of container.querySelectorAll('details'))details.open=!!draft.open[details.dataset.designId];
  const details=container.querySelector('[data-design-id="DV-CODE"]');let loading=false;
  const cacheKey=`${shot.shotId}:${shot.currentVersion}:${shot.posterRevision}:${shot.codeChars}:${shot.attempts}`;
  details.ontoggle=async()=>{
    if(!details.open||loading)return;
    const pre=details.querySelector('pre');if(state.codes.has(cacheKey)){pre.textContent=state.codes.get(cacheKey);return;}
    loading=true;try{const response=await fetch(`${base}/code`,{credentials:'same-origin',headers:{Accept:'text/plain'}});if(!response.ok)throw new Error('code unavailable');const code=await response.text();state.codes.set(cacheKey,code);if(details.isConnected)pre.textContent=code;}catch{pre.textContent=message();}finally{loading=false;}
  };
  if(details.open)details.ontoggle();
  if(locked)container.querySelectorAll('.rv-side button,.rv-side input').forEach(el=>el.disabled=true);
}
