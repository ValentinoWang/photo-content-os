import { failureMessage, safeText } from './direct-view.js';
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean=value=>esc(safeText(value));
const views=new WeakMap();
const proposalError='这条草稿已经处理过，刷新一下。';
function nowText(category){
  const proposals=category.proposals||[],latest=proposals.at(-1),through=Math.max(0,...proposals.map(p=>p.throughCount));
  if(proposals.some(p=>p.status==='pending'))return '建议写进规则';
  if(proposals.some(p=>p.status==='running'))return '正在起草规则';
  if(latest?.status==='failed')return '这次没起草成，再攒 3 次会重新起草。';
  if(latest?.status==='adopted'&&category.count===latest.throughCount)return '已写进规则';
  return 3-(category.count-through)===1?'再有 1 次会起草规则':'记着';
}
function sourcesFor(sources){const groups=new Map();for(const source of sources||[]){const key=source.projectId||source.projectTitle;if(!groups.has(key))groups.set(key,{title:source.projectTitle,shots:new Set()});groups.get(key).shots.add(source.shotId);}return [...groups.values()].map(g=>`${clean(g.title)} · ${[...g.shots].sort((a,b)=>Number(a)-Number(b)||String(a).localeCompare(String(b))).map(clean).join('、')}`).join('<br>');}

export function renderRevisionLog(container,{api,onBack}) {
  const state={active:true,timer:null};const previous=views.get(container);if(previous){previous.active=false;clearTimeout(previous.timer);}views.set(container,state);
  const anchor=container.ownerDocument.createElement('div');anchor.className='rv-log-page';container.replaceChildren(anchor);state.anchor=anchor;
  const active=()=>state.active&&container.isConnected&&container.firstElementChild===state.anchor&&views.get(container)===state;
  const back=()=>{state.active=false;clearTimeout(state.timer);onBack();};
  async function load(){
    try{const [log,samples]=await Promise.all([api('/api/direct/revision-log'),api('/api/direct/samples')]);if(!active())return;if(!Array.isArray(log.categories)||!Array.isArray(samples.samples))throw new Error('invalid projection');paint(log,samples.samples);
      if(log.categories.some(c=>c.proposals?.some(p=>p.status==='running')))state.timer=setTimeout(load,2000);
    }catch{if(active()){container.innerHTML=`<div class="rv-log-page"><button class="btn" data-back>回到作品</button><p role="alert" data-design-data>${failureMessage()}</p><button class="btn" data-retry>重试</button></div>`;state.anchor=container.firstElementChild;container.querySelector('[data-back]').onclick=back;container.querySelector('[data-retry]').onclick=load;}}
  }
  function paint(log,samples){const revision=Number.isInteger(log.rulesRevision)?log.rulesRevision:0;
    const categories=log.categories.filter(c=>c.count>0).sort((a,b)=>b.count-a.count);
    const proposal=(p,category)=>`<div class="rv-prop" data-design-id="RV-PROPOSAL"><small data-design-data>起草的规则修改 · 画面规则第 ${revision} 版 → 第 ${revision+1} 版</small><p class="add" data-design-data>${clean(p.text)}</p><p class="why" data-design-data>依据：这 ${p.throughCount} 次你都点了「${clean(category)}」类改法。</p><div class="actions"><button class="btn btn--pri btn--sm" data-proposal="${esc(p.proposalId)}" data-choice="adopt">采用</button><button class="btn btn--sm" data-proposal="${esc(p.proposalId)}" data-choice="reject">不用</button><span data-design-data>采用后，之后新写的镜按第 ${revision+1} 版；已经写好的镜不变。</span></div></div>`;
    container.innerHTML=`<div class="rv-log-page"><div class="stephead full" data-design-id="DV-HEAD"><div><p class="eyebrow">脚本直出</p><h2>画面问题记录</h2></div><div class="actions"><button class="btn" data-back>回到作品</button></div><p class="rv-log-lede">你在各作品里改过的画面问题和存下的样例。同一种问题到 3 次，会起草一条画面规则给你看，点「采用」才生效。</p></div><div class="full" data-design-id="RV-LOG">${categories.length?`<div class="rv-log-wrap"><table class="rv-log"><thead><tr><th>问题</th><th>几次</th><th>出在哪几镜</th><th>现在</th></tr></thead><tbody>${categories.map(c=>`<tr><td data-design-data>${clean(c.category)}</td><td class="n" data-design-data>${c.count}</td><td data-design-data>${sourcesFor(c.sources)}</td><td><span class="${c.proposals?.some(p=>p.status==='pending')?'hot':''}">${nowText(c)}</span>${(c.proposals||[]).filter(p=>p.status==='pending').map(p=>proposal(p,c.category)).join('')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="rv-empty">还没有改过画面。改过的问题会记在这里。</p>'}<p data-log-error role="alert" data-design-data hidden></p><div class="rv-sec" data-design-id="RV-SAMPLES"><h3>存下的样例 · <span data-design-data>${samples.length}</span> 镜</h3><p>写新镜时，Opus 会参考和这一镜最像的两个样例。</p>${samples.length?`<div class="rv-samples">${samples.map(s=>{const date=new Date(s.savedAt),title=Array.from(String(s.projectTitle||'').split(/[，,]/)[0]).slice(0,8).join(''),url=String(s.posterUrl||'');const valid=url.startsWith('/api/direct/samples?')&&!url.includes('://');return `<figure>${valid?`<img src="${esc(url)}" alt="">`:''}<figcaption data-design-data>${clean(title)} · 第 ${clean(s.shotId)} 镜<br>${Number.isFinite(date.getTime())?`${date.getMonth()+1}月${date.getDate()}日存`:''}</figcaption></figure>`;}).join('')}</div>`:'<p class="rv-empty">还没有存样例。在一镜上点「♡ 这镜好」就会存到这里。</p>'}</div></div></div>`;
    state.anchor=container.firstElementChild;container.querySelector('[data-back]').onclick=back;
    container.querySelectorAll('[data-proposal]').forEach(button=>button.onclick=async()=>{container.querySelectorAll('[data-proposal]').forEach(b=>b.disabled=true);try{const bootstrap=await api('/api/bootstrap');const response=await fetch(`/api/direct/rules/proposals/${encodeURIComponent(button.dataset.proposal)}/${button.dataset.choice}`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':bootstrap.csrfToken},body:'{}'});const payload=await response.json();if(!response.ok||!payload.ok){const error=new Error('proposal failed');error.code=payload.error?.code;throw error;}if(active())await load();}catch(e){if(active()){const error=container.querySelector('[data-log-error]');error.hidden=false;error.textContent=['proposal_not_found','proposal_not_ready'].includes(e.code)?proposalError:failureMessage(e.code);container.querySelectorAll('[data-proposal]').forEach(b=>b.disabled=false);}}});
  }
  load();
}
