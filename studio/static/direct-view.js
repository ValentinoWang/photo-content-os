import { renderShotDetail } from './direct-shot-detail.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D = value => `<span data-design-data>${esc(value)}</span>`;
const btn = (text, attrs='', primary=false) => `<button class="btn${primary?' btn--pri':''}" ${attrs}>${text}</button>`;
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
export function writtenSeconds(job,shot) { return elapsed(job.createdAt,Date.parse(shot.writtenAt)); }
export function totalSeconds(shots) { return shots.reduce((sum,s)=>sum+shotSeconds(s),0); }
export function writtenCount(shots) { return shots.filter(s=>['written','rendering','rendered'].includes(s.status)).length; }
export function shouldPoll(job) {
  return !!job && !(['ready','done','failed'].includes(job.status) && !job.shots.some(s=>['writing','rendering'].includes(s.status)) && job.output.status!=='composing');
}
export function defaultShot(shots) { return (shots.find(s=>s.status==='failed') || shots.find(s=>s.status==='writing' && (s.lastInstruction || s.attempts>1)) || shots[0])?.shotId; }
export function shotStart(shots,index) { return totalSeconds(shots.slice(0,index)); }
export function jobUrl(projectId,jobId) { return `/api/projects/${encodeURIComponent(projectId)}/direct/jobs${jobId?'/'+encodeURIComponent(jobId):''}`; }
export function posterUrl(projectId,job,shot) { return `${jobUrl(projectId,job.jobId)}/shots/${encodeURIComponent(shot.shotId)}/poster.jpg?v=${encodeURIComponent(shot.posterRevision)}`; }

export function createDirectView(ctx) {
  let project, job=null, selected, userSelected=false, timer, generation=0, tabs='', readError=false, unavailable=false, formScript='', formStyle='', pendingVoice=null, actionError='', busy=false, outputKey='';
  const active = token => token===generation && ctx.active(project?.id);
  const root=ctx.root;
  const find=s=>root().querySelector(s);
  function stop(){generation++;clearTimeout(timer);timer=null;root().querySelector('video')?.pause();}
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
    if(!job)return unavailable?'unavailable':splitScript(formScript).length?'filled':'empty';
    if(job.output.status==='ready' && job.status==='done')return job.output.kind==='silent'?'done-silent':'done';
    if(job.output.status==='composing')return job.output.kind==='silent'?'composing-silent':'composing';
    if(job.shots.some(s=>s.status==='failed') || job.status==='failed')return 'failed-shot';
    if(job.design.status!=='done')return 'designing';
    if(job.shots.some(s=>s.status==='writing' && s.lastInstruction))return 'rewriting';
    return shouldPoll(job)?'writing':'ready';
  }
  function flow(){
    const shots=readError?[]:job?.shots||splitScript(formScript).map(dialogue=>({dialogue})), n=shots.length, count=writtenCount(shots), st=stateName();
    const steps=[['口播稿',readError?'读不到':n?`${n} 镜 · 约 ${mmss(totalSeconds(shots))}`:'还没粘贴'],['Opus 写每一镜',!job||readError?'等口播稿':st==='designing'?'正在定全片设计':count===n?`${n} 镜都写好了`:`${count} / ${n} 镜写好`],['成片',st.startsWith('composing')?'正在合成':st.startsWith('done')?`${job.output.kind==='narrated'?'带配音':'无声预览'} · ${mmss(job.output.durationSeconds)}`:'还没合成']];
    const cur=!job||readError?0:(st.startsWith('composing')||st.startsWith('done'))?2:1;
    return `<nav class="flow full" aria-label="这件作品的步骤" data-design-id="DV-STEPS">${steps.map(([title,note],i)=>`<div class="fstep ${i<cur || st.startsWith('done')?'done':''} ${i===cur && !st.startsWith('done')?'cur':''}" ${i===cur?'aria-current="step"':''}><b>${i<cur || st.startsWith('done')?'✓':i+1}</b><span><strong>${title}</strong><small data-design-data>${esc(note)}</small></span></div>`).join('')}</nav>`;
  }
  function head(title,lede='',actions=''){return `<div class="stephead full" data-design-id="DV-HEAD"><div><p class="eyebrow">脚本直出</p><h2>${title}</h2>${lede?`<p>${lede}</p>`:''}</div><div class="actions">${actions}</div></div>`;}
  function startForm(){
    return `<div class="dv-start" data-design-id="DV-START"><section class="dv-form"><header><h3>口播稿</h3><span>一行是一镜</span></header><textarea aria-label="口播稿" placeholder="把口播稿粘贴进来，一行是一镜。例如：&#10;清华 AI 体育博主，断更一年。会写代码，会练体能，就是发不出一条视频。&#10;第一句：发出去，会被人看低。">${esc(formScript)}</textarea><div data-lines></div><footer><p data-total></p><div class="actions">${btn('导入分镜文件','data-import')}${btn('生成','data-generate disabled',true)}</div></footer></section><aside class="dv-opts"><div class="dv-opt" data-design-id="DV-HOW"><h4>点「生成」以后</h4><ol class="dv-how"><li><b>1</b><span>Opus 先定全片设计：底色、主色、强调色、字号和动作规矩<small>约 1 分钟</small></span></li><li><b>2</b><span>每一镜写一段动画代码，三镜同时写；写完自查，不过关的自动重写一次<small>每镜约 1–3 分钟</small></span></li><li><b>3</b><span>写好一镜就在本机逐帧渲染一镜，页面上马上能看<small>可以离开这一页，不会中断</small></span></li></ol></div><div class="dv-opt" data-design-id="DV-STYLE"><h4>风格说明（可不填）</h4><p>想模仿哪种画面，写一句给 Opus。</p><div class="row"><input type="text" data-style placeholder="例：浅米色底，一个深青主色，结论只用橙色" value="${esc(formStyle)}"></div></div><div class="dv-opt" data-design-id="DV-VOICE"><h4>配音（可以之后再加）</h4><p>没有配音先出无声预览。上传配音以后，按配音实测每一镜的时长，动画比配音长的镜会自动改短。</p><div class="row">${btn('上传配音…','data-voice',false)}<span class="dv-voice-name" data-design-data>${esc(pendingVoice?.name||'')}</span></div></div></aside></div>`;
  }
  function updateForm(){
    const shots=splitScript(formScript).map(dialogue=>({dialogue}));
    find('[data-lines]').innerHTML=shots.length?`<ul class="dv-lines" data-design-id="DV-LINES">${shots.map((s,i)=>`<li><b data-design-data>${String(i+1).padStart(2,'0')}</b><span data-design-data>${esc(s.dialogue)}</span><i data-design-data>${shotSeconds(s).toFixed(1)} 秒</i></li>`).join('')}</ul>`:'';
    find('[data-total]').innerHTML=shots.length?`<span data-design-data>${shots.length} 镜 · 按字数估约 ${mmss(totalSeconds(shots))} · 每秒按 5.1 字算</span>`:'还没有口播稿。也可以导入上游中台导出的分镜文件。';
    find('[data-generate]').disabled=!shots.length||unavailable||busy;
    find('[data-flow]').innerHTML=flow();
    find('[data-head]').innerHTML=unavailable?head('把口播稿直接做成视频','粘贴口播稿，Opus 给每一镜写一段动画代码，在这台电脑上逐帧渲染成画面，再合成一条竖屏成片。'):shots.length?head(D(`${shots.length} 镜口播稿，可以生成了`),'检查一下分镜：一行是一镜。时长先按字数估，上传配音后按实测。'):head('把口播稿直接做成视频','粘贴口播稿，Opus 给每一镜写一段动画代码，在这台电脑上逐帧渲染成画面，再合成一条竖屏成片。不用素材，也不用剪辑软件。');
    document.querySelector('.main').dataset.designState=stateName();
  }
  function design(){
    const d=job.design;
    if(d.status!=='done')return `<div class="dv-design dv-design--pending" data-design-id="DV-DESIGN"><b>全片设计</b><span>Opus 正在定：底色、主色、强调色、字号和动作规矩。定好以后七镜都照它写。</span></div>`;
    return `<div class="dv-design" data-design-id="DV-DESIGN"><b>全片设计</b>${[['background','背景'],['primary','主色'],['accent','强调色'],['neutral','中性']].map(([k,n])=>`<span class="dv-sw"><i data-color="${esc(/^#[0-9a-f]{6}$/i.test(d.palette?.[k])?d.palette[k]:'')}"></i>${n}</span>`).join('')}${D(`字号 ${(d.typeScale||[]).join(' / ')}`)}${D(safeText(d.motionRules))}<span class="dv-ban">${(d.banned||[]).map(b=>D(safeText(b))).join('')}</span></div>`;
  }
  function card(s){
    const writing=s.status==='writing',failed=s.status==='failed',interrupted=s.status==='interrupted',rewriting=writing&&!!s.lastInstruction,auto=writing&&!rewriting&&s.attempts>1;
    const good=['written','rendering','rendered'].includes(s.status);
    const label=good?`写好 · ${mmss(writtenSeconds(job,s))}`:rewriting?'按你的意见重写':auto?'自查没过，正在重写':writing?'正在写':failed?(s.failureCode==='lint_failed_after_retry'?'写了两次都没过':failureMessage(s.failureCode)):interrupted?'中断了':s.status==='queued'?'等着写':failureMessage(s.failureCode);
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
    video.ontimeupdate=()=>{scrub.value=video.currentTime;find('[data-readout]').textContent=`${mmss(video.currentTime)} / ${mmss(Number(scrub.max))}`;root().querySelectorAll('[data-jump]').forEach(b=>{const i=Number(b.dataset.jump),t=video.currentTime;b.setAttribute('aria-current',String(t>=shotStart(job.shots,i)&&t<shotStart(job.shots,i+1)));});};
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
    if(!job){
      find('[data-body]').innerHTML=startForm();updateForm();
      find('textarea').oninput=e=>{formScript=e.target.value;updateForm();};find('[data-style]').oninput=e=>{formStyle=e.target.value;};
      find('[data-import]').onclick=()=>pickFile('application/json,.json',async file=>{const value=JSON.parse(await file.text());if(!Array.isArray(value.shots)||value.shots.some(s=>typeof s.dialogue!=='string'))throw new Error('invalid storyboard');formScript=value.shots.map(s=>s.dialogue).join('\n');find('textarea').value=formScript;updateForm();});
      find('[data-generate]').onclick=generate;bindVoice();return;
    }
    if(!find('[data-film]')) {find('[data-body]').innerHTML='<div data-job-alert class="dv-body"></div><div data-design class="dv-body"></div><div data-progress class="dv-body"></div><div data-output class="dv-body"></div><div data-film class="dv-body"></div><div data-detail class="dv-body"></div>';outputKey='';}
    find('[data-flow]').innerHTML=flow();
    const st=stateName(),count=writtenCount(job.shots),n=job.shots.length,writing=job.shots.filter(s=>s.status==='writing'),failed=job.shots.find(s=>s.status==='failed');
    let title='',lede='',actions='';
    if(st==='designing'){title='Opus 正在定全片设计';lede='定好以后七镜三镜一组同时写。可以离开这一页，回来接着看进度。';}
    else if(st==='writing'){title=D(`Opus 写好了 ${count} 镜${writing.length?'，正在写第 '+writing.map(s=>s.shotId).join('、')+' 镜':''}`);lede=D('写好一镜就渲染一镜。'+job.shots.filter(s=>s.status==='writing'&&!s.lastInstruction&&s.attempts>1).map(s=>`第 ${s.shotId} 镜自查没过，正在自动重写一次。`).join(''));}
    else if(st==='failed-shot'){title=D(failed?`${count} 镜写好了，第 ${failed.shotId} 镜没写成`:failureMessage(job.failureCode));}
    else if(st==='rewriting'){title=D(`正在按你的意见重写第 ${writing.find(s=>s.lastInstruction)?.shotId} 镜`);lede=D(`只重写、只重渲这一镜；其他 ${n-1} 镜不动。`);}
    else if(st.startsWith('composing')){title=st==='composing-silent'?'正在合成无声预览':'正在合成成片';lede=st==='composing-silent'?'七镜画面逐帧拼起来，再检查一遍。':'七镜画面按配音逐帧拼起来，再检查一遍。';}
    else if(st==='done-silent'){title='无声预览出来了';lede=D(`从点「生成」到出片用了 ${mmss(elapsed(job.createdAt,Date.parse(job.updatedAt)))}。上传配音以后按配音重排时长，再合成带声成片。`);actions=btn('上传配音…','data-voice')+btn('重新合成','data-compose');}
    else if(st==='done'){title='成片出来了';lede=D(`从点「生成」到出片用了 ${mmss(elapsed(job.createdAt,Date.parse(job.updatedAt)))}。看一遍，有哪一镜不满意，点那一镜写意见重写，重写后重新合成。`);actions=btn('重新合成','data-compose');}
    else {title=D(`${n} 镜都写好了`);lede=D(`用时 ${mmss(elapsed(job.createdAt))} · ${job.shots.reduce((sum,s)=>sum+s.checks.warnings.length,0)} 条提醒，看过觉得没问题就可以合成。`);actions=btn('上传配音…','data-voice')+btn(job.narration.status==='ready'?'合成成片':'先合成无声预览','data-compose',true);}
    const body=find('[data-body]'),designSlot=find('[data-design]');
    if(st.startsWith('done'))body.insertBefore(find('[data-output]'),designSlot);
    if(st.startsWith('composing'))body.insertBefore(find('[data-progress]'),designSlot);
    find('[data-head]').innerHTML=head(title,lede,actions);
    find('[data-job-alert]').innerHTML=failed?attention(D(failed.failureCode==='lint_failed_after_retry'?`第 ${failed.shotId} 镜写了两次，都没过自查`:`第 ${failed.shotId} 镜没写成`),D(failed.checks.errors.map(e=>safeText(e.message)).filter(Boolean).join('；')||failureMessage(failed.failureCode)),btn('写意见重写','data-focus',true),'DV-SHOTFAIL',true):'';
    find('[data-focus]')?.addEventListener('click',()=>{selected=failed.shotId;userSelected=true;paint();find('#dv-ask')?.focus();});
    find('[data-design]').innerHTML=design();root().querySelectorAll('[data-color]').forEach(e=>e.style.setProperty('--swatch',e.dataset.color));
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
  function bindVoice(){find('[data-voice]')?.addEventListener('click',()=>pickFile('.wav,audio/wav',async file=>{if(job)await mutate('/narration',file,true);else {pendingVoice=file;find('.dv-voice-name').textContent=safeText(file.name);}}));}
  async function generate(){
    const token=generation;busy=true;updateForm();
    try{const result=await request(jobUrl(project.id),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({script:splitScript(formScript).join('\n'),style:formStyle})});if(!active(token))return;job=result.job;selected=undefined;userSelected=false;paint();if(pendingVoice){const file=pendingVoice;pendingVoice=null;await mutate('/narration',file,true);}schedule(token);}
    catch(e){if(active(token)){unavailable=e.code==='claude_cli_unavailable';actionError=unavailable?'':failureMessage(e.code);paint();}}
    finally{busy=false;if(active(token)&&!job)updateForm();}
  }
  async function mutate(suffix,body,binary=false){
    const token=generation,button=find(suffix==='/compose'?'[data-compose]':'[data-voice]');if(button)button.disabled=true;
    try{const result=await request(jobUrl(project.id,job.jobId)+suffix,{method:'POST',headers:{'Content-Type':binary?'audio/wav':'application/json'},body:binary?body:JSON.stringify(body)});if(!active(token))return;job=result.job;actionError='';paint();schedule(token);}
    catch(e){if(active(token)){actionError=failureMessage(e.code);paintMessage();}}
    finally{if(button?.isConnected)button.disabled=false;}
  }
  function schedule(token){clearTimeout(timer);if(active(token)&&shouldPoll(job))timer=setTimeout(()=>refresh(token),2000);}
  async function refresh(token,latest=false){
    try{const result=await ctx.api(jobUrl(project.id,latest||!job?'latest':job.jobId));if(!active(token))return;if(!Object.hasOwn(result,'job') || result.job!==null&&(!Array.isArray(result.job.shots)||!result.job.output||!result.job.design))throw new Error('invalid projection');const changed=job?.jobId!==result.job?.jobId;job=result.job;if(changed){selected=undefined;userSelected=false;}readError=false;actionError='';paint();schedule(token);}
    catch{if(active(token)){readError=true;paint();}}
  }
  return {stop,async render(piece,tabMarkup){
    stop();const changed=project?.id!==piece.id;project=piece;if(changed){job=null;selected=undefined;userSelected=false;formScript='';formStyle='';pendingVoice=null;unavailable=false;}readError=false;actionError='';tabs=tabMarkup;
    ctx.mark('direct');root().classList.add('single','dv-direct');document.querySelector('.topbar').dataset.designId='DV-TOPBAR';document.querySelector('#crumb').parentElement.removeAttribute('data-design-id');
    root().innerHTML=tabs.replace('R208-PIECE-tabs','DV-TABS').replace(' aria-label="做法"','')+'<div data-flow class="dv-body"></div><div data-head class="dv-body"></div><div data-message class="dv-body"></div><div data-body class="dv-body"></div>';
    document.querySelector('#crumb').childNodes.forEach(n=>{if(n.nodeType===3&&n.textContent==='›')n.textContent='·';});
    model();await refresh(generation,true);
  }};
}
