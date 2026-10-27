import { renderShotDetail } from './direct-shot-detail.js';
import {normalizeRows,handoffRows,rowSummary,storyboard,renderStoryboard} from './direct-storyboard.js';
import {canGenerate,canDraft,stylePayload,sourceText,swatches,applySwatches,designLines,howFirst,generationText,renderStyle,draftBusy,styleTime} from './direct-style.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D = value => `<span data-design-data>${esc(value)}</span>`;
const btn = (text, attrs='', primary=false) => (attrs==='data-voice'?'<button class="btn rv-go-log" data-revision-log>画面问题记录</button>':'')+`<button class="btn${primary?' btn--pri':''}" ${attrs}>${text}</button>`;
export const FAILURE_COPY = Object.freeze({
  claude_cli_unavailable:'本机的 Claude 调不通，现在用不了 Opus',
  model_timeout:'Opus 这一镜写了太久没写完，可以重试',
  code_invalid:'Opus 写出来的不是一段完整的动画代码，可以重试',
  lint_failed_after_retry:'写了两次都没过自查（下面写卡在哪条）',
  render_failed:'这一镜没渲染出来，可以只重试这一镜',
  narration_invalid:'配音文件读不出来，换一个 WAV 再传',
});
export function failureMessage(code) { return FAILURE_COPY[code] || '读不到这一镜的状态，点重试'; }
export function safeText(value) {
  return String(value ?? '').replace(/(?:[A-Za-z]:[\\/][^\s<>]+|\/(?:[^\s/<>]+\/)+[^\s<>]*)/g,'［本机路径］').replace(/\b[a-z]+(?:_[a-z0-9]+)+\b/g,'［状态未登记］');
}
export function splitScript(script) { return String(script).split(/\r?\n/).map(s=>s.trim()).filter(Boolean); }
export function shotSeconds(shot) {
  if (Number.isFinite(shot.measuredSeconds) && shot.measuredSeconds >= 0) return shot.measuredSeconds;
  return Math.round(Array.from(shot.dialogue || '').length / 5.1 * 10) / 10;
}
export function mmss(value) { const n=Number.isFinite(value)?Math.max(0,Math.round(value)):0;return `${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`; }
export function elapsed(createdAt, now=Date.now()) { const start=Date.parse(createdAt);return Number.isFinite(start)?Math.max(0,(now-start)/1000):0; }
export function writingSeconds(shot,now=Date.now()) { return Number.isFinite(Date.parse(shot.writingStartedAt))?elapsed(shot.writingStartedAt,now):null; }
export function canRewrite(shot,instruction) { const text=String(instruction??'');return Array.from(text).length<=200 && (['failed','interrupted'].includes(shot.status)||text.trim().length>0); }
export function writtenSeconds(shot) {
  const start=Date.parse(shot.writingStartedAt),end=Date.parse(shot.writtenAt);
  return Number.isFinite(start)&&Number.isFinite(end)&&end>=start?(end-start)/1000:null;
}
export function writtenLabel(shot) { const seconds=writtenSeconds(shot);return seconds===null?'写好':`写好 · 用时 ${mmss(seconds)}`; }
export function totalSeconds(shots) { return shots.reduce((sum,s)=>sum+shotSeconds(s),0); }
export function writtenCount(shots) { return shots.filter(s=>['written','rendering','rendered'].includes(s.status)).length; }
export function shouldPoll(job) {
  return !!job && !(['ready','done','failed'].includes(job.status) && !job.shots.some(s=>['writing','rendering'].includes(s.status)) && job.output.status!=='composing');
}
export function defaultShot(shots) { return (shots.find(s=>s.status==='failed') || shots.find(s=>s.status==='writing' && (s.lastInstruction || s.attempts>1)) || shots[0])?.shotId; }
export function shotStart(shots,index) { return totalSeconds(shots.slice(0,index)); }
export function jobUrl(projectId,jobId) { return `/api/projects/${encodeURIComponent(projectId)}/direct/jobs${jobId?'/'+encodeURIComponent(jobId):''}`; }
export function posterUrl(projectId,job,shot) { return `${jobUrl(projectId,job.jobId)}/shots/${encodeURIComponent(shot.shotId)}/poster.jpg?v=${encodeURIComponent(shot.posterRevision)}`; }

export function canRescript(job,readError=false){return !!job&&!readError&&!shouldPoll(job)&&job.failureCode!=='claude_cli_unavailable'&&!job.shots.some(s=>s.look?.status==='running'||s.versions?.find(v=>v.version===s.currentVersion)?.verify?.status==='running');}

export function createDirectView(ctx) {
  let project, job=null, selected, userSelected=false, timer, generation=0, tabs='', readError=false, unavailable=false, pendingVoice=null, actionError='', busy=false, outputKey='',currentHandoff=null;
  const forms=new Map();let form,editor,draftTimer,disposeStyle=()=>{};
  function newForm(){return {rows:[],editing:false,handoff:null,measured:false,styles:null,library:[],mode:'base',base:null,adjust:'',text:'',revise:'',draft:null,accepted:false,revising:false};}
  const active = token => token===generation && ctx.active(project?.id);
  const root=ctx.root;
  const find=s=>root().querySelector(s);
  function stop(){generation++;clearTimeout(timer);clearTimeout(draftTimer);timer=null;disposeStyle();disposeStyle=()=>{};editor?.dispose();editor=null;root().querySelectorAll('video').forEach(v=>v.pause());}
  // The Studio JSON helper stringifies files and discards error codes. Keep binary and
  // text requests here, using the same bootstrap token and same-origin credentials.
  async function request(path,options={}) {
    const headers={...options.headers};
    if(options.method==='POST') headers['X-Content-OS-CSRF']=(await ctx.api('/api/bootstrap')).csrfToken;
    const response=await fetch(path,{credentials:'same-origin',...options,headers});
    const payload=await response.json();
    if(!response.ok || !payload.ok) {const e=new Error('direct request failed');e.code=payload.error?.code;throw e;}
    return payload;
  }
  function attention(title,text,actions,id='DV-SHOTFAIL',bad=false) {
    return `<div class="attention${bad?' attention--cut':''}" role="alert" data-design-id="${id}"><div><strong>${title}</strong>${text?`<p>${text}</p>`:''}</div><div class="actions">${actions}</div></div>`;
  }
  function model(){document.querySelector('#top-actions').innerHTML=`<span class="dv-model" data-design-id="DV-MODEL"><i class="dot ${unavailable?'dot--warn':'dot--ok'}"></i>Opus 5.5 · 本机 Claude${unavailable?' · 调不通':''}</span>`;}
  function stateName(){
    if(readError)return 'read-error';
    if(form.editing)return currentHandoff&&job?.handoffNewer&&!form.handoff?'rescript-newer':'rescript';
    if(!job&&form.handoff)return 'first-handoff';
    if(!job)return unavailable?'unavailable':rowSummary(form.rows).count?'filled':'empty';
    if(job.output.status==='ready' && job.status==='done')return job.output.kind==='silent'?'done-silent':'done';
    if(job.output.status==='composing')return job.output.kind==='silent'?'composing-silent':'composing';
    if(job.shots.some(s=>s.status==='failed') || job.status==='failed')return 'failed-shot';
    if(job.design.status!=='done')return 'designing';
    if(job.shots.some(s=>s.status==='writing' && s.lastInstruction))return 'rewriting';
    return shouldPoll(job)?'writing':'ready';
  }
  function flow(){
    const editing=form.editing||!job,shots=readError?[]:editing?form.rows:job.shots,n=shots.filter(s=>s.dialogue?.trim()).length,count=writtenCount(shots),st=stateName();
    const duration=editing?rowSummary(shots,form.measured).seconds:totalSeconds(shots);
    const steps=[['分镜脚本',readError?'读不到':n?`${n} 镜 · ${editing&&form.measured?'':'约 '}${mmss(duration)}`:'还没粘贴'],['Opus 写每一镜',form.editing?'生成后从头写':!job||readError?'等分镜脚本':st==='designing'?'正在定全片设计':count===n?`${n} 镜都写好了`:`${count} / ${n} 镜写好`],['成片',form.editing?'生成后重新合成':st.startsWith('composing')?'正在合成':st.startsWith('done')?`${job.output.kind==='narrated'?'带配音':'无声预览'} · ${mmss(job.output.durationSeconds)}`:'还没合成']];
    const cur=editing||readError?0:(st.startsWith('composing')||st.startsWith('done'))?2:1,entry=!editing&&canRescript(job,readError);
    return `<nav class="flow full" aria-label="这件作品的步骤" data-design-id="DV-STEPS">${steps.map(([title,note],i)=>{const done=!editing&&(i<cur||st.startsWith('done')),tag=i===0&&entry?'button':'div';return `<${tag} class="fstep ${done?'done':''} ${i===cur&&!st.startsWith('done')?'cur':''} ${i===0&&entry?'dv-fstep-btn':''}" ${i===0&&entry?'data-rescript aria-label="改分镜脚本"':''} ${i===cur?'aria-current="step"':''}><b>${done?'✓':i+1}</b><span><strong>${title}</strong><small data-design-data>${esc(note)}</small></span>${i===0&&!editing&&!readError?(entry?'<em class="dv-step-edit" data-design-id="DV-RESCRIPT-ENTRY">改分镜脚本</em>':`<em class="dv-step-lock" data-design-id="DV-RESCRIPT-LOCKED">${job.output.status==='composing'?'合成完才能改':'写完才能改'}</em>`):''}</${tag}>`;}).join('')}</nav>`;
  }
  function head(title,lede='',actions=''){return `<div class="stephead full" data-design-id="DV-HEAD"><div><p class="eyebrow">脚本直出</p><h2>${title}</h2>${lede?`<p>${lede}</p>`:''}</div><div class="actions">${actions}</div></div>`;}
  async function loadStyles(token){
    const result=await ctx.api('/api/direct/styles');if(!active(token))return;
    if(!Array.isArray(result.styles)||!Array.isArray(result.library))throw new Error('invalid styles');form.styles=result.styles;form.library=result.library;
    if(form.base?.kind==='library'){const match=result.library.find(x=>x.id===form.base.id);form.base=match?{...match,kind:'library'}:null;}
    else if(form.base)form.base=result.styles.find(x=>x.projectId===form.base.projectId&&x.jobId===form.base.jobId)||(form.editing&&form.base.projectId===project.id&&form.base.jobId===job?.jobId?form.base:null);
    else form.base=result.styles[0]||null;
  }
  function updateForm(){
    const summary=rowSummary(form.rows,form.measured),[text,need]=generationText(form.rows,form);
    find('[data-generate]').disabled=!canGenerate(form.rows,form,unavailable,busy);
    find('[data-gen-text]').textContent=text;find('[data-gen-text]').classList.toggle('need',need);
    find('[data-flow]').innerHTML=flow();
    find('[data-head]').innerHTML=form.editing?head('改分镜脚本，重新生成','点「生成」后 Opus 从头写每一镜，配音要重新上传。现在这条留在本机，页面只显示新的那条。',btn('回到现在这条','data-rescript-back')):summary.count?head(D(`分镜脚本共 ${summary.count} 镜，可以生成了`),form.handoff?(form.handoff.narration?'中台交过来的分镜和配音都已带上。检查一下，改完就能生成。':''):'检查一下分镜：一格是一镜。时长先按字数估，上传配音后按实测。'):head('把分镜脚本直接做成视频','粘贴分镜脚本，Opus 给每一镜写一段动画代码，在这台电脑上逐帧渲染成画面，再合成一条竖屏成片。不用素材，也不用剪辑软件。');
    find('[data-rescript-back]')?.addEventListener('click',()=>{editor?.dispose();editor=null;form.editing=false;pendingVoice=null;actionError='';paint();schedule(generation);});
    const first=howFirst(form);find('[data-how-first]').innerHTML=`${first[0]}<small>${first[1]}</small>`;
    const draftButton=find('[data-draft]');if(draftButton)draftButton.disabled=!canDraft(form.rows,form,unavailable,busy)||(!!form.draft&&form.draft.status!=='failed');
    const revise=find('[data-revise-go]');if(revise)revise.disabled=!form.revise.trim()||draftBusy(form.draft)||busy||unavailable;
    document.querySelector('.main').dataset.designState=stateName();
  }
  function paintStyle(){
    disposeStyle();disposeStyle=renderStyle(find('[data-style-slot]'),{state:form,styles:form.styles||[],library:form.library,rows:form.rows,projectId:project.id,jobId:form.editing?job.jobId:null,unavailable,busy,mmss,elapsed,failureMessage,
      onChange:redraw=>{if(redraw)paintStyle();updateForm();},onDraft:()=>writeDraft(false),onRevise:()=>writeDraft(true),onRedo:()=>{clearTimeout(draftTimer);form.draft=null;form.accepted=false;form.revising=false;form.revise='';paintStyle();updateForm();}});
  }
  function takeHandoff(){
    if(!currentHandoff)return;
    form.handoff=structuredClone(currentHandoff);form.rows=handoffRows(form.handoff);form.measured=true;pendingVoice=null;startForm();
  }
  function handoffTime(h){return Number.isFinite(Date.parse(h.handedAt))?' · '+styleTime(h.handedAt):'';}
  function handoffSource(){
    if(form.handoff){const h=form.handoff;return `<p class="dv-sb-src" data-design-id="DV-SB-SOURCE">${D(`从中台交过来：「${h.title}」${h.revision==null?'':`第 ${h.revision} 版`}${handoffTime(h)}${h.narration?` · 带配音（${h.narration.voice} · ${mmss(h.narration.durationSeconds)}）`:''}。`)}<span>在这里改只存在本机，不会改中台的分镜。</span></p>`;}
    return form.editing&&currentHandoff&&job.handoffNewer?`<p class="dv-sb-src" data-design-id="DV-SB-SOURCE">${D(currentHandoff.revision==null?'中台又交过来新的分镜。':`中台又交过来新的分镜：第 ${currentHandoff.revision} 版${handoffTime(currentHandoff)}。`)}<button class="link" data-take-handoff>换成中台这版</button></p>`:'';
  }
  function voiceCard(){
    const n=form.handoff?.narration;
    return `<h4>${n?'配音（从中台带过来）':'配音（可以之后再加）'}</h4><p>${n?D(`${n.voice} · ${mmss(n.durationSeconds)}`)+'。生成时按这条配音实测每一镜的时长，动画比配音长的镜会自动改短。':'没有配音先出无声预览。上传配音以后，按配音实测每一镜的时长，动画比配音长的镜会自动改短。'}</p><div class="row">${btn(n?'换一个配音…':'上传配音…','data-voice')}<span class="dv-voice-name" data-design-data>${esc(pendingVoice?.name||'')}</span></div>`;
  }
  function startForm(){
    editor?.dispose();find('[data-body]').innerHTML=`<div class="dv-start" data-design-id="DV-START"><div data-script-slot class="dv-body"></div><div data-style-slot class="dv-body"></div><aside class="dv-opts"><div class="dv-opt" data-design-id="DV-HOW"><h4>点「生成」以后</h4><ol class="dv-how"><li><b>1</b><span data-how-first></span></li><li><b>2</b><span>每一镜写一段动画代码，三镜同时写；写完自查，不过关的自动重写一次<small>每镜约 1–3 分钟</small></span></li><li><b>3</b><span>写好一镜就在本机逐帧渲染一镜，页面上马上能看<small>可以离开这一页，不会中断</small></span></li></ol></div><div class="dv-opt" data-design-id="DV-VOICE">${voiceCard()}</div></aside><div class="dv-genbar" data-design-id="DV-GENBAR"><p data-gen-text data-design-data></p><div class="actions">${btn('生成','data-generate disabled',true)}</div></div></div>`;
    editor=renderStoryboard(find('[data-script-slot]'),{rows:form.rows,source:handoffSource(),onTakeHandoff:takeHandoff,measured:form.measured,hasNarration:!!form.handoff?.narration,onChange:(rows,measured)=>{form.rows=rows;form.measured=measured;updateForm();},onImport:()=>pickFile('application/json,.json',async file=>{const value=JSON.parse(await file.text());if(!Array.isArray(value.shots)||value.shots.some(s=>typeof s.dialogue!=='string'||['visual','subtitle','camera','audio'].some(f=>s[f]!=null&&typeof s[f]!=='string')))throw new Error('invalid storyboard');form.rows=normalizeRows(value.shots);form.handoff=null;form.measured=false;startForm();})});
    paintStyle();updateForm();find('[data-generate]').onclick=generate;bindVoice();
  }
  function draftUrl(){return `/api/projects/${encodeURIComponent(project.id)}/direct/style-drafts`;}
  async function writeDraft(revise){
    if(revise?(!form.revise.trim()||draftBusy(form.draft)||unavailable||busy):!canDraft(form.rows,form,unavailable,busy))return;
    const token=generation,previous=form.draft;form.accepted=false;form.revising=revise;form.draft={...previous,status:'designing',startedAt:new Date().toISOString()};paintStyle();updateForm();
    try{const result=await request(draftUrl()+(revise?'/'+encodeURIComponent(previous.draftId)+'/revise':''),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(revise?{instruction:form.revise.trim()}:{text:form.text.trim(),shot:storyboard(form.rows).shots[0]})});if(!active(token))return;form.draft=result.draft;if(!draftBusy(form.draft))form.revising=false;paintStyle();updateForm();scheduleDraft(token);}
    catch(e){if(active(token)){form.draft={...form.draft,status:'failed',failureCode:e.code};form.revising=false;unavailable=e.code==='claude_cli_unavailable';model();paintMessage();paintStyle();updateForm();}}
  }
  function scheduleDraft(token){clearTimeout(draftTimer);if(active(token)&&draftBusy(form.draft))draftTimer=setTimeout(()=>pollDraft(token),2000);}
  async function pollDraft(token){
    try{const result=await ctx.api(draftUrl()+'/'+encodeURIComponent(form.draft.draftId));if(!active(token))return;const old=JSON.stringify(form.draft);form.draft=result.draft;if(!form.draft||!['designing','writing','ready','failed'].includes(form.draft.status))throw new Error('invalid draft');if(old!==JSON.stringify(form.draft)){if(!draftBusy(form.draft))form.revising=false;paintStyle();updateForm();}else if(find('[data-draft-clock]'))find('[data-draft-clock]').textContent='已用 '+mmss(elapsed(form.draft.startedAt));scheduleDraft(token);}
    catch{if(active(token)){form.draft={...form.draft,status:'failed',failureCode:null};paintStyle();updateForm();}}
  }
  async function rescript(){
    if(!canRescript(job,readError))return;
    const token=generation;try{const result=await ctx.api(jobUrl(project.id,job.jobId));if(!active(token))return;job=result.job;const hand=await ctx.api(`/api/projects/${encodeURIComponent(project.id)}/direct/handoff`);if(!active(token))return;currentHandoff=hand.handoff;}catch{if(active(token)){actionError=failureMessage();paintMessage();}return;}
    form.handoff=null;form.measured=false;form.editing=true;form.rows=normalizeRows(job.shots).map((r,i)=>({...r,image:job.shots[i].posterRevision?{poster:posterUrl(project.id,job,job.shots[i]),clip:`${jobUrl(project.id,job.jobId)}/shots/${encodeURIComponent(r.shotId)}/clip.mp4?v=${encodeURIComponent(job.shots[i].posterRevision)}`} :null}));
    form.base={projectId:project.id,jobId:job.jobId,title:project.title,createdAt:job.createdAt,design:job.design,posterUrl:job.shots.find(s=>s.posterRevision)?posterUrl(project.id,job,job.shots.find(s=>s.posterRevision)):null};form.mode='base';form.adjust='';pendingVoice=null;clearTimeout(timer);paint();window.scrollTo(0,0);editor.focus();
    if(!form.styles){try{await loadStyles(generation);if(ctx.active(project.id)&&form.editing){paintStyle();updateForm();}}catch{actionError=failureMessage();paintMessage();}}
  }
  function design(){
    const d=job.design;
    if(d.status!=='done')return `<div class="dv-design dv-design--pending" data-design-id="DV-DESIGN"><b>全片设计</b>${d.source?.kind==='adjusted'?D(`在「${d.source.title}」的风格上改：${d.source.instruction}。改好以后七镜都照它写。`):'<span>Opus 正在定：底色、主色、强调色、字号和动作规矩。定好以后七镜都照它写。</span>'}</div>`;
    return `<div class="dv-design" data-design-id="DV-DESIGN"><b>全片设计</b><span class="dv-design-src" data-design-data>${esc(sourceText(d.source))}</span>${swatches(d)}${D(`字号 ${(d.typeScale||[]).join(' / ')}`)}${designLines(d)}</div>`;
  }
  function card(s){
    const writing=s.status==='writing',failed=s.status==='failed',interrupted=s.status==='interrupted',rewriting=writing&&!!s.lastInstruction,auto=writing&&!rewriting&&s.attempts>1;
    const good=['written','rendering','rendered'].includes(s.status);
    const label=good?writtenLabel(s):rewriting?'按你的意见重写':auto?'自查没过，正在重写':writing?'正在写':failed?(s.failureCode==='lint_failed_after_retry'?'写了两次都没过':failureMessage(s.failureCode)):interrupted?'中断了':s.status==='queued'?'等着写':failureMessage(s.failureCode);
    let poster=s.posterRevision?`<img src="${posterUrl(project.id,job,s)}" alt="">`:'';
    if(!poster||writing)poster+=`<div class="dv-veil ${failed?'dv-veil--fail':writing?'dv-veil--writing'+(s.posterRevision?' dv-veil--dim':''):'dv-veil--queued'}"><b>${failed?'没写成':rewriting?'按你的意见重写':auto?'自查没过，正在重写':writing?'Opus 正在写':interrupted?'中断了':'等着写'}</b>${writing&&writingSeconds(s)!=null?`<span class="mono" data-design-data>已写 ${mmss(writingSeconds(s))}</span>`:''}</div>`;
    return `<article tabindex="0" class="dv-card ${failed?'is-bad':''}" data-shot="${esc(s.shotId)}" aria-current="${selected===s.shotId}" data-design-id="DV-SHOT"><div class="dv-poster">${poster}</div><div class="dv-card-b"><header><b data-design-data>${esc(s.shotId)}</b><span data-design-data>${shotSeconds(s).toFixed(1)} 秒</span></header><p data-design-data>${esc(safeText(s.dialogue))}</p><div class="dv-tags">${interrupted?`<button class="st st--off" data-retry-shot="${esc(s.shotId)}">中断了 · 重试</button>`:`<span class="st ${failed?'st--bad':auto?'st--wait':writing?'st--run':good?'':'st--off'}" data-design-data>${esc(label)}</span>`}${good&&s.checks.warnings.length?'<span class="st st--wait">有提醒</span>':''}</div></div></article>`;
  }
  function refreshDetail(){
    const shot=job.shots.find(s=>s.shotId===selected);
    const container=find('[data-detail]');
    if((stateName().startsWith('composing')||stateName().startsWith('done'))&&!userSelected){container.hidden=true;return;}
    if(!shot || ['queued','writing'].includes(shot.status)&&!shot.lastInstruction&&shot.attempts<=1){container.hidden=true;return;}
    container.hidden=false;
    renderShotDetail(container,{job,shot,projectId:project.id,api:ctx.api,onRewrite:()=>{if(ctx.active(project.id))refresh(generation);}});
  }
  function output(){
    const o=job.output,checks=o.checks||{},duration=o.durationSeconds||totalSeconds(job.shots),silent=o.kind==='silent';
    const check=(label,pass,note)=>`<li class="${pass===true?'':pass===false?'fail':'warn'}">${label}<span data-design-data>${esc(note)}</span></li>`;
    return `<section class="dv-out" data-design-id="DV-OUTPUT"><div class="dv-player"><div class="dv-stage"><video src="${jobUrl(project.id,job.jobId)}/output.mp4?v=${encodeURIComponent(o.revision)}" playsinline preload="metadata" poster="${posterUrl(project.id,job,job.shots[0])}"></video><button class="dv-bigplay" data-play aria-label="播放成片">▶</button></div><div class="dv-scrub" data-design-id="DV-SCRUB"><input type="range" min="0" max="${duration}" step="0.01" value="0" data-scrub aria-label="拖到成片哪里"><span data-readout data-design-data>0:00 / ${mmss(duration)}</span></div></div><div class="dv-outinfo"><h3 data-design-data>${esc(safeText(project.title))}</h3><p data-design-data>竖屏 1080×1920 · ${job.shots.length} 镜 · ${o.kind==='narrated'?'带配音':'无声预览'} ${mmss(duration)}</p><ul class="dv-outchecks" data-design-id="DV-OUTCHECKS">${check('能从头放到尾',checks.playable==='pass'?true:checks.playable==='fail'?false:null,o.frames==null?failureMessage():`${o.frames.toLocaleString()} 帧`)}${silent?'<li class="none">无声预览，不检查声音</li>':check('声音和画面对得上',Number.isFinite(checks.avOffsetSeconds)?Math.abs(checks.avOffsetSeconds)<=.1:null,Number.isFinite(checks.avOffsetSeconds)?`差 ${Math.abs(checks.avOffsetSeconds).toFixed(2)} 秒`:failureMessage())}${check(silent?'帧数和各镜时长一致':'帧数和配音时长一致',Number.isFinite(o.frames)&&Number.isFinite(silent?totalSeconds(job.shots):job.narration.durationSeconds)?Math.abs(o.frames/30-(silent?totalSeconds(job.shots):job.narration.durationSeconds))<=1/30:null,mmss(silent?totalSeconds(job.shots):job.narration.durationSeconds))}${check('没有黑帧',checks.blackFrames==='pass'?true:checks.blackFrames==='fail'?false:null,checks.blackFrames==='pass'?'0 处':failureMessage())}</ul><div class="dv-strip" data-design-id="DV-STRIP">${job.shots.map((s,i)=>`<button data-jump="${i}" data-design-data aria-label="第 ${esc(s.shotId)} 镜"><img src="${posterUrl(project.id,job,s)}" alt=""><b>${esc(s.shotId)}</b></button>`).join('')}</div></div></section>`;
  }
  function bindOutput(){
    const video=find('video'),scrub=find('[data-scrub]'),play=find('[data-play]');if(!video)return;
    play.onclick=()=>{if(video.paused)video.play().catch(()=>{actionError=failureMessage();paintMessage();});else video.pause();};
    video.onclick=()=>play.click();video.onplay=()=>{play.hidden=true;};video.onpause=video.onended=()=>{play.hidden=false;};
    video.ontimeupdate=()=>{if(!video.isConnected)return;scrub.value=video.currentTime;find('[data-readout]').textContent=`${mmss(video.currentTime)} / ${mmss(Number(scrub.max))}`;root().querySelectorAll('[data-jump]').forEach(b=>{const i=Number(b.dataset.jump),t=video.currentTime;b.setAttribute('aria-current',String(t>=shotStart(job.shots,i)&&t<shotStart(job.shots,i+1)));});};
    scrub.oninput=()=>{video.currentTime=Number(scrub.value);};
    root().querySelectorAll('[data-jump]').forEach(b=>b.onclick=()=>{video.currentTime=shotStart(job.shots,Number(b.dataset.jump));video.ontimeupdate();});
  }
  function paintMessage(){
    const slot=find('[data-message]');
    slot.innerHTML=readError?attention('读不到这件作品的直出任务','Studio 读这件作品的直出记录时出错。没有显示成「还没生成」，免得你重复生成一遍。点重试再读一次。',btn('重试','data-retry',true),'DV-READERROR'):unavailable?attention(FAILURE_COPY.claude_cli_unavailable,'Studio 在后台调用这台电脑上的 Claude 没有回应，多半是登录过期。在终端里运行一次 claude 确认能用，再回来点重试。',btn('去设置看看','data-settings')+btn('重试','data-retry',true),'DV-UNAVAILABLE'):actionError?attention(esc(actionError),'',btn('重试','data-retry')):'';
    find('[data-retry]')?.addEventListener('click',()=>{unavailable=false;actionError='';refresh(generation,true);});
    find('[data-settings]')?.addEventListener('click',()=>ctx.go({view:'settings',tab:'models'}));
  }
  function paint(){
    if(!ctx.active(project.id))return;
    unavailable=unavailable||job?.failureCode==='claude_cli_unavailable';model();paintMessage();
    if(readError){find('[data-body]').hidden=true;find('[data-head]').innerHTML='';find('[data-flow]').innerHTML=flow();document.querySelector('.main').dataset.designState='read-error';return;}
    find('[data-body]').hidden=false;
    document.querySelector('.main').dataset.designState=stateName();
    if(form.editing||!job){
      startForm();
      scheduleDraft(generation);return;
    }
    disposeStyle();disposeStyle=()=>{};
    if(!find('[data-film]')) {find('[data-body]').innerHTML='<div data-job-alert class="dv-body"></div><div data-design class="dv-body"></div><div data-progress class="dv-body"></div><div data-output class="dv-body"></div><div data-film class="dv-body"></div><div data-detail class="dv-body"></div>';outputKey='';}
    find('[data-flow]').innerHTML=flow();
    find('[data-rescript]')?.addEventListener('click',rescript);
    const st=stateName(),count=writtenCount(job.shots),n=job.shots.length,writing=job.shots.filter(s=>s.status==='writing'),failed=job.shots.find(s=>s.status==='failed');
    let title='',lede='',actions='';
    if(st==='designing'){title=job.design.source?.kind==='adjusted'?'Opus 正在按你的话改全片设计':'Opus 正在定全片设计';lede='定好以后七镜三镜一组同时写。可以离开这一页，回来接着看进度。';}
    else if(st==='writing'){title=D(`Opus 写好了 ${count} 镜${writing.length?'，正在写第 '+writing.map(s=>s.shotId).join('、')+' 镜':''}`);lede=D('写好一镜就渲染一镜。'+job.shots.filter(s=>s.status==='writing'&&!s.lastInstruction&&s.attempts>1).map(s=>`第 ${s.shotId} 镜自查没过，正在自动重写一次。`).join(''));}
    else if(st==='failed-shot'){title=D(failed?`${count} 镜写好了，第 ${failed.shotId} 镜没写成`:failureMessage(job.failureCode));}
    else if(st==='rewriting'){title=D(`正在按你的意见重写第 ${writing.find(s=>s.lastInstruction)?.shotId} 镜`);lede=D(`只重写、只重渲这一镜；其他 ${n-1} 镜不动。`);}
    else if(st.startsWith('composing')){title=st==='composing-silent'?'正在合成无声预览':'正在合成成片';lede=st==='composing-silent'?'七镜画面逐帧拼起来，再检查一遍。':'七镜画面按配音逐帧拼起来，再检查一遍。';}
    else if(st==='done-silent'){title='无声预览出来了';lede=D(`${job.output.composedAt?`从点「生成」到出片用了 ${mmss(elapsed(job.createdAt,Date.parse(job.output.composedAt)))}。`:""}上传配音以后按配音重排时长，再合成带声成片。`);actions=btn('上传配音…','data-voice')+btn('重新合成','data-compose');}
    else if(st==='done'){title='成片出来了';lede=D(`${job.output.composedAt?`从点「生成」到出片用了 ${mmss(elapsed(job.createdAt,Date.parse(job.output.composedAt)))}。`:""}看一遍，有哪一镜不满意，点那一镜写意见重写，重写后重新合成。`);actions=btn('重新合成','data-compose');}
    else {title=D(`${n} 镜都写好了`);lede=D(`用时 ${mmss(elapsed(job.createdAt))} · ${job.shots.reduce((sum,s)=>sum+s.checks.warnings.length,0)} 条提醒，看过觉得没问题就可以合成。`);actions=btn('上传配音…','data-voice')+btn(job.narration.status==='ready'?'合成成片':'先合成无声预览','data-compose',true);}
    const body=find('[data-body]'),designSlot=find('[data-design]');
    if(st.startsWith('done'))body.insertBefore(find('[data-output]'),designSlot);
    if(st.startsWith('composing'))body.insertBefore(find('[data-progress]'),designSlot);
    find('[data-head]').innerHTML=head(title,lede,actions);
    find('[data-job-alert]').innerHTML=failed?attention(D(failed.failureCode==='lint_failed_after_retry'?`第 ${failed.shotId} 镜写了两次，都没过自查`:`第 ${failed.shotId} 镜没写成`),D(failed.checks.errors.map(e=>safeText(e.message)).filter(Boolean).join('；')||failureMessage(failed.failureCode)),btn('写意见重写','data-focus',true),'DV-SHOTFAIL',true):'';
    find('[data-focus]')?.addEventListener('click',()=>{selected=failed.shotId;userSelected=true;paint();find('#dv-ask')?.focus();});
    find('[data-design]').innerHTML=design();applySwatches(root());
    find('[data-progress]').innerHTML=['writing','designing'].includes(st)?`<div class="dv-progress" data-design-id="DV-PROGRESS"><span data-design-data>${count} / ${n} 镜写好</span><div class="meter"><i data-progress-bar></i></div><span class="mono" data-design-data>已用 ${mmss(elapsed(job.createdAt))} · 三镜同时写</span></div>`:st.startsWith('composing')?`<div class="dv-compose" data-design-id="DV-COMPOSE"><div><b>合成中</b><p data-design-data>${n} 镜 · ${st==='composing-silent'?'无声预览 · 约 '+mmss(totalSeconds(job.shots)):'配音 '+mmss(job.narration.durationSeconds)}</p></div></div>`:'';
    find('[data-progress-bar]')?.style.setProperty('width',`${n?count/n*100:0}%`);
    if(!userSelected)selected=defaultShot(job.shots);
    find('[data-film]').innerHTML=`<div class="dv-film" data-design-id="DV-FILM">${job.shots.map(card).join('')}</div>`;
    root().querySelectorAll('[data-shot]').forEach(b=>b.onclick=()=>{selected=b.dataset.shot;userSelected=true;root().querySelectorAll('[data-shot]').forEach(c=>c.setAttribute('aria-current',String(c===b)));refreshDetail();});
    root().querySelectorAll('[data-shot]').forEach(b=>b.onkeydown=e=>{if(e.target===b&&['Enter',' '].includes(e.key)){e.preventDefault();b.click();}});
    root().querySelectorAll('[data-retry-shot]').forEach(b=>b.onclick=e=>{e.stopPropagation();mutate(`/shots/${encodeURIComponent(b.dataset.retryShot)}/rewrite`,{});});
    refreshDetail();
    const key=st.startsWith('done')?`${job.jobId}:${job.output.revision}`:'';
    if(key!==outputKey){find('[data-output]').innerHTML=key?output():'';outputKey=key;bindOutput();}
    find('[data-compose]')?.addEventListener('click',()=>mutate('/compose',{}));bindVoice();
  }
  async function pickFile(accept,handler){
    const token=generation,input=document.createElement('input');input.type='file';input.accept=accept;
    input.onchange=async()=>{if(!input.files[0]||!active(token))return;try{await handler(input.files[0]);}catch{if(active(token)){actionError=failureMessage(accept.includes('wav')?'narration_invalid':null);paintMessage();}}};input.click();
  }
  function bindVoice(){find('[data-revision-log]')?.addEventListener('click',async()=>{stop();const token=generation,saved=document.createDocumentFragment();while(root().firstChild)saved.append(root().firstChild);const {renderRevisionLog}=await import('./direct-revision-log.js');if(!active(token))return;renderRevisionLog(root(),{api:ctx.api,onBack:()=>{if(!active(token))return;root().replaceChildren(saved);refresh(generation);}});});find('[data-voice]')?.addEventListener('click',()=>pickFile('.wav,audio/wav',async file=>{if(job&&!form.editing)await mutate('/narration',file,true);else {pendingVoice=file;find('.dv-voice-name').textContent=safeText(file.name);}}));}
  async function generate(){
    if(!canGenerate(form.rows,form,unavailable,busy))return;
    const token=generation;busy=true;updateForm();
    try{const result=await request(jobUrl(project.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({storyboard:storyboard(form.rows),...stylePayload(form,project.id),...(form.handoff?{handoff:{jobId:form.handoff.jobId,revision:form.handoff.revision}}:{})})});if(!active(token))return;job=result.job;form.editing=false;clearTimeout(draftTimer);editor?.dispose();editor=null;selected=undefined;userSelected=false;paint();if(pendingVoice){const file=pendingVoice;pendingVoice=null;await mutate('/narration',file,true);}schedule(token);}
    catch(e){if(active(token)){unavailable=e.code==='claude_cli_unavailable';actionError=unavailable?'':failureMessage(e.code);paint();}}
    finally{busy=false;if(active(token)&&(form.editing||!job))updateForm();}
  }
  async function mutate(suffix,body,binary=false){
    const token=generation,button=find(suffix==='/compose'?'[data-compose]':'[data-voice]');if(button)button.disabled=true;
    try{const result=await request(jobUrl(project.id,job.jobId)+suffix,{method:'POST',headers:{'Content-Type':binary?'audio/wav':'application/json'},body:binary?body:JSON.stringify(body)});if(!active(token))return;job=result.job;actionError='';paint();schedule(token);}
    catch(e){if(active(token)){actionError=failureMessage(e.code);paintMessage();}}
    finally{if(button?.isConnected)button.disabled=false;}
  }
  function schedule(token){clearTimeout(timer);if(active(token)&&!form.editing&&(shouldPoll(job)||job&&!canRescript(job,readError)&&job.failureCode!=='claude_cli_unavailable'))timer=setTimeout(()=>refresh(token),2000);}
  async function refresh(token,latest=false){
    try{const result=await ctx.api(jobUrl(project.id,latest||!job?'latest':job.jobId));if(!active(token))return;if(!Object.hasOwn(result,'job') || result.job!==null&&(!Array.isArray(result.job.shots)||!result.job.output||!result.job.design))throw new Error('invalid projection');const changed=job?.jobId!==result.job?.jobId;job=result.job;if(latest){const hand=await ctx.api(`/api/projects/${encodeURIComponent(project.id)}/direct/handoff`);if(!active(token))return;currentHandoff=hand.handoff;if(!job&&!form.rows.length&&currentHandoff){form.handoff=structuredClone(currentHandoff);form.rows=handoffRows(form.handoff);form.measured=true;}}if(changed){selected=undefined;userSelected=false;}readError=false;actionError='';if(!job&&form.styles===null)await loadStyles(token);if(!active(token))return;paint();schedule(token);}
    catch{if(active(token)){readError=true;paint();}}
  }
  return {stop,async render(piece,tabMarkup){
    stop();const changed=project?.id!==piece.id;project=piece;if(changed){currentHandoff=null;job=null;selected=undefined;userSelected=false;form=forms.get(piece.id)||newForm();forms.set(piece.id,form);pendingVoice=null;unavailable=false;}readError=false;actionError='';tabs=tabMarkup;
    ctx.mark('direct');root().classList.add('single','dv-direct');document.querySelector('.topbar').dataset.designId='DV-TOPBAR';document.querySelector('#crumb').parentElement.removeAttribute('data-design-id');
    root().innerHTML=tabs.replace('R208-PIECE-tabs','DV-TABS').replace(' aria-label="做法"','')+'<div data-flow class="dv-body"></div><div data-head class="dv-body"></div><div data-message class="dv-body"></div><div data-body class="dv-body"></div>';
    document.querySelector('#crumb').childNodes.forEach(n=>{if(n.nodeType===3&&n.textContent==='›')n.textContent='·';});
    model();await refresh(generation,true);
  }};
}
