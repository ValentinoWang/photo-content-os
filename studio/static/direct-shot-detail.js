import { failureMessage, safeText, shotSeconds, writtenSeconds, mmss, jobUrl, posterUrl, canRewrite } from './direct-view.js';

const views=new WeakMap();
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D=value=>`<span data-design-data>${esc(value)}</span>`;

export function renderShotDetail(container,{job,shot,projectId,api,onRewrite}) {
  let state=views.get(container);
  if(!state || state.jobId!==job.jobId){state={jobId:job.jobId,key:null,drafts:new Map(),codes:new Map(),busy:false};views.set(container,state);}
  const unavailable=job.failureCode==='claude_cli_unavailable';
  const key=JSON.stringify([shot.shotId,shot.status,shot.posterRevision,shot.checks,shot.attempts,unavailable]);
  if(state.key===key)return;
  const previous=container.querySelector('#dv-ask'),focus=previous && previous===container.ownerDocument.activeElement;
  const selection=focus?[previous.selectionStart,previous.selectionEnd]:null;
  if(previous && state.shotId)state.drafts.set(state.shotId,previous.value);
  const open=state.shotId===shot.shotId && !!container.querySelector('details')?.open;
  state.shotId=shot.shotId;state.key=key;
  const pending=['writing','rendering'].includes(shot.status),failed=shot.status==='failed',hasPoster=shot.posterRevision>0;
  const errors=shot.checks?.errors||[],warnings=shot.checks?.warnings||[];
  const rules=[['animation_cut_short','动画在这一镜时长内做完'],['header_missing','页眉标好了'],['subtitle_band','字幕带里没放字'],['external_resource','不读网络和外部文件'],['forbidden_runtime','不用定时器和随机数']];
  const checked=shot.codeChars>0 && !pending;
  const checks=errors.map(e=>`<li class="fail" data-design-data>${esc(safeText(e.message)||failureMessage(e.code))}</li>`).join('')+warnings.map(w=>`<li class="warn" data-design-data>${esc(safeText(w.message)||failureMessage(w.code))}</li>`).join('')+(checked?rules.filter(([code])=>!(failed&&code==='animation_cut_short')&&!errors.some(e=>e.code===code)).map(([,label])=>`<li>${label}</li>`).join(''):'');
  container.innerHTML=`<section class="dv-detail" data-design-id="DV-DETAIL"><div class="dv-pv"><div class="dv-stage">${hasPoster?`<img src="${posterUrl(projectId,job,shot)}" alt="">`:'<div class="dv-veil dv-veil--fail"><b>这一镜还没有画面</b></div>'}</div>${hasPoster?`<p class="dv-pvnote" data-design-id="DV-PVNOTE" data-design-data>关键帧 · 这一镜 ${shotSeconds(shot).toFixed(1)} 秒处的 80%</p>`:''}</div><div class="dv-info"><header><h3 data-design-data>第 ${esc(shot.shotId)} 镜</h3><span data-design-data>${pending?'正在重写':failed?'没写成':shot.writtenAt?`写好于 ${mmss(writtenSeconds(job,shot))}`:''}</span></header><p class="dv-say" data-design-data>${esc(safeText(shot.dialogue))}</p><div class="dv-kv" data-design-id="DV-FACTS"><div><small>时长</small><b data-design-data>${shot.measuredSeconds!=null?'配音实测':'按字数估'} ${shotSeconds(shot).toFixed(1)} 秒</b></div><div><small>写了几次</small><b data-design-data>${Number.isFinite(shot.attempts)?shot.attempts:0} 次</b></div><div><small>主动作</small><b data-design-data>${esc(safeText(shot.mainAction))}</b></div><div><small>代码</small><b data-design-data>${Number.isFinite(shot.codeChars)?shot.codeChars.toLocaleString():0} 字</b></div></div><ul class="dv-checks" data-design-id="DV-CHECKS">${checks}</ul><div class="dv-ask" data-design-id="DV-REWRITE"><label for="dv-ask">写一句修改意见，让 Opus 只重写这一镜</label><div class="row"><input id="dv-ask" type="text" maxlength="200" placeholder="例：数字再大一点，底色不动" ${pending||unavailable?'disabled':''}><button class="btn" data-rewrite disabled>让 Opus 重写这一镜</button></div><small>只重写、只重渲这一镜；其他镜的画面和写好的时间都不变。</small><p data-detail-error role="alert" data-design-data></p></div><details class="dv-code" data-design-id="DV-CODE"><summary>看代码<span data-design-data>${Number.isFinite(shot.codeChars)?shot.codeChars.toLocaleString():0} 字 · 上限 100,000</span></summary><pre data-design-data></pre></details></div></section>`;
  const input=container.querySelector('#dv-ask'),button=container.querySelector('[data-rewrite]'),details=container.querySelector('details'),error=container.querySelector('[data-detail-error]');
  input.value=state.drafts.get(shot.shotId)??shot.lastInstruction??'';
  const valid=()=>{const length=Array.from(input.value.trim()).length;button.disabled=pending||unavailable||state.busy||!canRewrite(shot,input.value);button.textContent=['failed','interrupted'].includes(shot.status)&&length===0?'重试这一镜':'让 Opus 重写这一镜';};
  input.oninput=()=>{state.drafts.set(shot.shotId,input.value);valid();};valid();
  if(focus&&!input.disabled){input.focus({preventScroll:true});if(selection)input.setSelectionRange(...selection);}
  button.onclick=async()=>{
    valid();if(button.disabled)return;state.busy=true;button.disabled=true;input.disabled=true;
    try {
      const bootstrap=await api('/api/bootstrap');
      const response=await fetch(`${jobUrl(projectId,job.jobId)}/shots/${encodeURIComponent(shot.shotId)}/rewrite`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Content-OS-CSRF':bootstrap.csrfToken},body:JSON.stringify({instruction:input.value.trim()})});
      const payload=await response.json();
      if(!response.ok||!payload.ok){error.textContent=failureMessage(payload.error?.code);if(payload.error?.code==='claude_cli_unavailable'){job.failureCode=payload.error.code;onRewrite(shot.shotId);}return;}
      onRewrite(shot.shotId);
    }catch{error.textContent=failureMessage();}
    finally{state.busy=false;if(input.isConnected){input.disabled=pending||unavailable;valid();}}
  };
  const cacheKey=`${shot.shotId}:${shot.posterRevision}:${shot.codeChars}:${shot.attempts}`;
  let loading=false;
  details.ontoggle=async()=>{
    if(!details.open||loading)return;
    const pre=details.querySelector('pre');if(state.codes.has(cacheKey)){pre.textContent=state.codes.get(cacheKey);return;}
    loading=true;
    try{const response=await fetch(`${jobUrl(projectId,job.jobId)}/shots/${encodeURIComponent(shot.shotId)}/code`,{credentials:'same-origin',headers:{Accept:'text/plain'}});if(!response.ok)throw new Error('code unavailable');const code=await response.text();state.codes.set(cacheKey,code);pre.textContent=code;}
    catch{pre.textContent=failureMessage();}
    finally{loading=false;}
  };
  details.open=open;
}
