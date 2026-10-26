import {bindClips} from './direct-storyboard.js';
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D = value => `<span data-design-data>${esc(value)}</span>`;
const button=(text,attrs='')=>`<button class="btn" ${attrs}>${text}</button>`;
const paletteKeys=[['background','背景'],['primary','主色'],['accent','强调色'],['neutral','中性']];
export const HINTS=['底色和主色','强调色','字的感觉','画面怎么动','参考什么','不要什么'];
export const draftBusy = draft => !!draft&&['designing','writing'].includes(draft.status);
export function canGenerate(rows,state,unavailable,busy){return rows.some(r=>r.dialogue.trim())&&!unavailable&&!busy&&(state.mode==='base'?!!state.base:state.draft?.status==='ready'&&state.accepted);}
export function canDraft(rows,state,unavailable,busy){return rows.some(r=>r.dialogue.trim())&&!!state.text.trim()&&!unavailable&&!busy&&!draftBusy(state.draft);}
export function stylePayload(state,projectId){return state.mode==='base'?{styleBase:state.base.kind==='library'?{kind:'library',id:state.base.id}:{kind:'job',projectId:state.base.projectId,jobId:state.base.jobId},style:state.adjust.trim()}:{styleBase:{kind:'draft',projectId,draftId:state.draft.draftId},style:''};}
export function styleTime(value){const d=new Date(value);return `${d.getMonth()+1} 月 ${d.getDate()} 日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;}
export function appendHint(text,hint){return `${text.trimEnd()}${text.trim()?'\n':''}${hint}：`;}
export function sameSampleShot(a,b){return ['dialogue','visual','subtitle','camera'].every(f=>(a?.[f]||'')===(b?.[f]||''));}
export function sourceText(source){if(!source)return '';return source.kind==='library'?`用风格库「${source.name}」的风格`:source.kind==='drafted'?'这次从头定的风格':source.kind==='adjusted'?`在「${source.title}」的风格上改过`:`沿用「${source.title}」的风格`;}
export function motionText(d){return d.motionSummary??d.motionRules??'';}
export function bannedText(d){return d.bannedShort??d.banned??[];}
export function swatches(d,names=true){return paletteKeys.map(([key,label])=>`<${names?'span class="dv-sw"':'i'}${names?'':` data-color="${esc(d?.palette?.[key]||'')}"`}>${names?`<i data-color="${esc(d?.palette?.[key]||'')}"></i>${label}</span>`:'</i>'}`).join('');}
export function applySwatches(root){root.querySelectorAll('[data-color]').forEach(el=>{if(/^#[0-9a-f]{6}$/i.test(el.dataset.color))el.style.setProperty('--swatch',el.dataset.color);});}
export function designLines(d){return `<p class="dv-design-line"><em>动作规矩</em><span class="${d.motionSummary==null?'dv-legacy-motion':''}" data-design-data>${esc(motionText(d))}</span></p><p class="dv-design-line"><em>不用</em><span class="dv-nots">${bannedText(d).map(t=>`<span data-design-data title="${esc(t)}">${esc(t)}</span>`).join('')}</span></p>`;}
function meta(d,title,actions=''){return `<div class="dv-sw-meta"><h4 data-design-data>${esc(title)}</h4><div class="dv-sw-pal">${swatches(d)}</div><dl><div><dt>字号</dt><dd data-design-data>${esc(d.typeScale?.join(' / '))}</dd></div><div><dt>动作规矩</dt><dd class="${d.motionSummary==null?'dv-legacy-motion':''}" data-design-data>${esc(motionText(d))}</dd></div><div><dt>不用</dt><dd><span class="dv-nots">${bannedText(d).map(t=>D(t)).join('')}</span></dd></div></dl>${actions}</div>`;}
export function howFirst(state){return state.mode==='base'?(!state.base?['先在下面选一个风格','选好就能生成']:state.adjust.trim()?['Opus 先按你写的改全片设计','约 1 分钟']:['全片设计沿用选中的风格','不用等']):state.accepted?['全片设计用刚定好的风格，第 01 镜直接用样张','不用等']:['先在下面定好风格、看过样张','点「先定风格」，约 2–3 分钟'];}
export function generationText(rows,state){
  if(!rows.some(r=>r.dialogue.trim()))return ['分镜脚本还空着：先在上面粘贴或导入',true];
  if(state.mode==='base'){
    if(!state.base)return ['风格还没选：在下面选一个现成的风格，或者从头定',true];
    const base=state.base,adjust=state.adjust.trim()?'，改：'+state.adjust.trim():'';
    return [base.kind==='library'?`风格：风格库「${base.name}」${adjust}`:`风格：沿用「${base.title}」${styleTime(base.createdAt)}${adjust}`,false];
  }
  return state.accepted?['风格：刚定好的风格（从头定）',false]:['风格还没定好：先点「先定风格」，满意了点「就用这个」',true];
}
export function renderStyle(container,{state,styles,library=[],rows,projectId,jobId,unavailable,busy,onChange,onDraft,onRevise,onRedo,mmss,elapsed,failureMessage}){
  const s=state,writing=draftBusy(s.draft)||busy,noLines=!rows.some(r=>r.dialogue.trim());let edit='',preview='';
  if(s.mode==='base'){
    const card=(x,lib=false)=>`<button class="dv-sw-card" data-style-card ${lib?`data-library="${esc(x.id)}"`:`data-project="${esc(x.projectId)}" data-job="${esc(x.jobId)}"`} aria-pressed="${lib?s.base?.kind==='library'&&s.base.id===x.id:s.base?.kind!=='library'&&s.base?.jobId===x.jobId&&s.base?.projectId===x.projectId}">${x.posterUrl?`<img src="${esc(x.posterUrl)}" alt="">`:'<span class="dv-sw-card-empty" aria-hidden="true"></span>'}<span><b data-design-data>${esc(lib?x.name:x.title)}</b>${lib?'':`<small data-design-data>${x.jobId===jobId?'这条 · ':''}${styleTime(x.createdAt)}</small>`}<span class="dv-style-sw">${swatches(x.design,false)}</span></span></button>`;
    edit=(styles.length?`<label class="dv-sw-label">这台电脑上做过的</label><div class="dv-sw-cards" data-design-id="DV-STYLE-CARDS">${styles.map(x=>card(x)).join('')}</div>`:'<p class="dv-sw-none">这台电脑上还没有做过的成片，先从风格库里挑一个。</p>')
      +`<label class="dv-sw-label">风格库<span>样张都是同一段台词</span></label><div class="dv-sw-cards" data-design-id="DV-STYLE-LIB">${library.map(x=>card(x,true)).join('')}</div><label class="dv-sw-label" for="dv-adjust">在这个风格上改哪里<span>（可不填）</span></label><textarea id="dv-adjust" rows="3" maxlength="4000" data-adjust placeholder="例：强调色换成暖黄，其余不动；数字再大一些">${esc(s.adjust)}</textarea>`;
    const x=s.base;
    if(x?.kind==='library')preview=`<div><div class="dv-poster"><video data-clip src="${esc(x.clipUrl)}" poster="${esc(x.posterUrl)}" muted loop playsinline preload="metadata" aria-hidden="true"></video></div><p class="dv-sw-cap">样张 · 同一段台词</p></div>${meta(x.design,`风格库 · ${x.name}`)}`;
    else if(x)preview=`<div>${x.posterUrl?`<div class="dv-poster"><img src="${esc(x.posterUrl)}" alt=""></div>`:'<div class="dv-sw-empty"></div>'}<p class="dv-sw-cap">首镜关键帧</p></div>${meta(x.design,`${x.jobId===jobId?'这条 · ':''}${styleTime(x.createdAt)}`)}`;
    else preview='<div class="dv-sw-empty"><b>还没选风格</b><span>在左边选一个</span></div><div class="dv-sw-meta"><p class="muted">选好以后这里放它的样张，和色板、字号、动作规矩、不用的套路。</p></div>';
  }else{
    edit=`<label class="dv-sw-label" for="dv-desc">风格说明<span>越具体越好</span></label><textarea id="dv-desc" rows="6" maxlength="4000" data-desc ${writing?'readonly':''} placeholder="例：浅米色底，深青做主色，结论只用橙色。标题要粗，数字特别大。每句只动一个东西，动完就停。不要渐变，不要一屏堆很多卡片。">${esc(s.text)}</textarea><div class="dv-sw-hints"><span>可以照这几项写：</span>${HINTS.map(h=>`<button class="pill" data-hint="${h}" ${writing?'disabled':''}>${h}</button>`).join('')}</div>`;
    if(s.draft?.status==='ready'&&!s.accepted||s.revising)edit+=`<label class="dv-sw-label" for="dv-revise">再改一句<span>（可不填）</span></label><textarea id="dv-revise" rows="3" maxlength="1000" data-revise ${writing?'readonly':''} placeholder="例：主色再深一点，标题再大一号">${esc(s.revise)}</textarea><div class="dv-sw-acts">${button('改','data-revise-go'+(!s.revise.trim()||writing||unavailable?' disabled':''))}</div>`;
    else if(!s.accepted)edit+=`<div class="dv-sw-acts">${button('先定风格','data-draft'+(!canDraft(rows,s,unavailable,busy)||s.draft?' disabled':''))}<p>${noLines?'先粘贴分镜脚本：样张就是第 01 镜。':'Opus 先定全片设计，再把第 01 镜写出来当样张，约 2–3 分钟。'}</p></div>`;
    if(!s.draft)preview='<div class="dv-sw-empty"><b>样张会出现在这里</b><span>先写出第 01 镜</span></div><div class="dv-sw-meta"><p class="muted">定好以后这里显示色板、字号、动作规矩和不用的套路。</p></div>';
    else if(writing)preview=`<div class="dv-poster"><div class="dv-veil dv-veil--writing"><b>${s.revising?'正在改样张':'正在定风格'}</b><span class="mono" data-draft-clock data-design-data>已用 ${mmss(elapsed(s.draft.startedAt))}</span></div></div><div class="dv-sw-meta"><p class="muted">${s.revising?D('按你的话改：'+s.revise):'先定全片设计，再把第 01 镜写出来当样张，约 2–3 分钟。'}</p></div>`;
    else if(s.draft.status==='failed')preview=`<div class="dv-sw-empty"><b>没定成</b></div><div class="dv-sw-meta"><p class="dv-sw-fail" data-design-data>没定成：${esc(s.draft.failureCode==='lint_failed_after_retry'?'样张写了两次都没过自查。':failureMessage(s.draft.failureCode))}</p><div class="dv-sw-acts">${button('重试','data-draft'+(unavailable?' disabled':''))}</div></div>`;
    else {const url=`/api/projects/${encodeURIComponent(projectId)}/direct/style-drafts/${encodeURIComponent(s.draft.draftId)}/poster.jpg?v=${encodeURIComponent(s.draft.sample.posterRevision)}`;preview=`<div><div class="dv-poster"><img src="${url}" alt=""></div><p class="dv-sw-cap">样张 · 第 01 镜</p></div>${meta(s.draft.design,s.accepted?'刚定好的风格':'样张出来了',`${s.accepted?'<span class="dv-sw-used">已选用</span>':''}<div class="dv-sw-acts">${s.accepted?button('重新定','data-redo'):button('就用这个','data-accept')} ${s.accepted?'':'<p>满意了点「就用这个」，才能生成。</p>'}</div>`)}`;}
  }
  container.innerHTML=`<section class="dv-style-wide" data-design-id="DV-STYLE"><header class="dv-sw-head"><div><h3>视频风格</h3><p>Opus 在这个风格上写每一镜。先定好风格，才能生成。</p></div><div class="seg" role="radiogroup" aria-label="视频风格怎么定">${[['base','选现成的风格'],['new','从头定风格']].map(([mode,label])=>`<button role="radio" data-mode="${mode}" aria-checked="${s.mode===mode}" aria-pressed="${s.mode===mode}" >${label}</button>`).join('')}</div></header><div class="dv-sw-body"><div class="dv-sw-edit" data-design-id="DV-STYLE-EDIT">${edit}</div><div class="dv-sw-preview" data-design-id="DV-STYLE-PREVIEW">${preview}</div></div></section>`;
  applySwatches(container);
  const click=(selector,fn)=>container.querySelectorAll(selector).forEach(el=>el.onclick=()=>fn(el));
  click('[data-mode]',el=>{s.mode=el.dataset.mode;onChange(true);});click('[data-style-card]',el=>{s.base=el.dataset.library?{...library.find(x=>x.id===el.dataset.library),kind:'library'}:styles.find(x=>x.projectId===el.dataset.project&&x.jobId===el.dataset.job);onChange(true);});
  for(const [selector,key] of [['[data-adjust]','adjust'],['[data-desc]','text'],['[data-revise]','revise']]){const el=container.querySelector(selector);if(el)el.oninput=()=>{s[key]=el.value;onChange(false);};}
  click('[data-hint]',el=>{s.text=appendHint(s.text,el.dataset.hint);const t=container.querySelector('[data-desc]');t.value=s.text;t.focus();t.setSelectionRange(t.value.length,t.value.length);onChange(false);});
  click('[data-draft]',onDraft);click('[data-revise-go]',onRevise);click('[data-accept]',()=>{s.accepted=true;onChange(true);});click('[data-redo]',onRedo);
  return bindClips(container);
}
