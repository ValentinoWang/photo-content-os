const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const D = value => `<span data-design-data>${esc(value)}</span>`;
const mmss = value => {const n=Math.max(0,Math.round(value));return `${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;};
const fields=['dialogue','visual','subtitle','camera','audio'];
export const blankRow = dialogue => ({dialogue,visual:'',subtitle:'',camera:'',audio:'',image:null});
export function normalizeRows(shots){return shots.map(s=>({...blankRow(''),...s,...Object.fromEntries(fields.map(f=>[f,String(s[f]??'').trim()]))}));}
export function handoffRows(handoff){
  return handoff.shots.map(s=>{
    const image=s.image;
    const label=image?.source==='code_render'?'代码渲染':image?.source==='source_keyframe'?'参考关键帧':image?.source==='generated_illustration'?'AI 示意 · 非实拍':image?.source==='source_frame'?`原片截帧${Number.isFinite(image.sourceTimeSeconds)?' '+mmss(image.sourceTimeSeconds):''}`:'';
    return {...blankRow(''),...s,image:image?{poster:image.url,tag:label+(image.rightsStatus==='pending'?' · 待确认':''),pending:image.rightsStatus==='pending'}:null};
  });
}
export function rowTimes(rows,measured=false){let time=0;return rows.map(r=>{if(!r.dialogue.trim())return null;const start=measured?r.startSeconds:time;time=measured?r.endSeconds:time+Array.from(r.dialogue.trim()).length/5.1;return [start,time];});}
export function rowSummary(rows,measured=false){const times=rowTimes(rows,measured).filter(Boolean);return {count:times.length,seconds:times.at(-1)?.[1]||0,measured};}
export function storyboard(rows){return {shots:rows.filter(r=>r.dialogue.trim()).map((r,i)=>({shotId:String(i+1).padStart(2,'0'),...Object.fromEntries(fields.filter(f=>r[f]?.trim()).map(f=>[f,r[f].trim()]))}))};}
export function splitRow(rows,i,start,end){const r=rows[i];return rows.toSpliced(i,1,{...r,dialogue:r.dialogue.slice(0,start).trimEnd()},blankRow(r.dialogue.slice(end).trimStart()));}
export function mergeRow(rows,i){const a=rows[i-1],b=rows[i],r={...a,dialogue:a.dialogue+b.dialogue};for(const f of fields.slice(1))r[f]=[a[f],b[f]].filter(x=>x?.trim()).join('；');return rows.toSpliced(i-1,2,r);}
export function pasteRows(rows,i,start,end,text){const r=rows[i]||blankRow(''),lines=(r.dialogue.slice(0,start)+text+r.dialogue.slice(end)).split(/\r?\n/).map(x=>x.trim()).filter(Boolean);return rows.toSpliced(i,1,...lines.map((d,j)=>j?blankRow(d):{...r,dialogue:d}));}

export function bindClips(root){
  const motion=matchMedia('(prefers-reduced-motion: reduce)'),seen=new Set(),videos=[...root.querySelectorAll('video[data-clip]')];
  const sync=v=>{v.controls=motion.matches&&!!v.closest('.sb-zoom');if(seen.has(v)&&!motion.matches)v.play().catch(()=>{});else v.pause();};
  const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting)seen.add(e.target);else seen.delete(e.target);sync(e.target);}));
  for(const v of videos){v.muted=true;v.addEventListener('error',()=>{observer.unobserve(v);seen.delete(v);v.pause();if(v.poster){const img=new Image();img.src=v.poster;img.alt='';v.replaceWith(img);}else v.remove();},{once:true});sync(v);observer.observe(v);}
  const change=()=>videos.forEach(sync);motion.addEventListener('change',change);
  return ()=>{observer.disconnect();motion.removeEventListener('change',change);videos.forEach(v=>v.pause());};
}
const media = image => image.clip?`<video data-clip src="${esc(image.clip)}" poster="${esc(image.poster)}" muted loop playsinline preload="metadata" aria-hidden="true"></video>`:`<img src="${esc(image.poster)}" alt="">`;
export function renderStoryboard(container,{rows,onChange,onImport,source='',onTakeHandoff,measured=false,hasNarration=true}){
  let current=rows,disposeClips=()=>{},zoom=null,zoomOrigin=null,disposeZoom=()=>{};
  const events=new AbortController();
  function closeZoom(focus=true){if(!zoom)return;disposeZoom();zoom.remove();zoom=null;if(focus&&zoomOrigin?.isConnected)zoomOrigin.focus({preventScroll:true});}
  function openZoom(button){
    closeZoom(false);zoomOrigin=button;const i=Number(button.dataset.pic),r=current[i],time=rowTimes(current,measured)[i],n=String(i+1).padStart(2,'0');
    zoom=document.createElement('div');zoom.className='sb-zoom';zoom.dataset.designId='DV-SB-ZOOM';zoom.setAttribute('role','dialog');zoom.setAttribute('aria-label',`第 ${n} 镜画面`);zoom.dataset.designData='';
    zoom.innerHTML=`<header><b data-design-data>第 ${n} 镜</b>${D(time?time.map(mmss).join('–'):'—')}<button class="link" data-zoom-close>关闭</button></header>${media(button.querySelector('video')?r.image:{...r.image,clip:null}).replace(' aria-hidden="true"','')}`;
    container.append(zoom);const rect=button.getBoundingClientRect();zoom.style.left=Math.max(8,Math.min(innerWidth-296,rect.right+8))+'px';zoom.style.top=Math.max(8,Math.min(innerHeight-540,rect.top-8))+'px';
    disposeZoom=bindClips(zoom);zoom.querySelector('button').onclick=()=>closeZoom();zoom.querySelector('button').focus({preventScroll:true});
  }
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeZoom();},{signal:events.signal});
  document.addEventListener('click',e=>{if(zoom&&!zoom.contains(e.target)&&!e.target.closest('button[data-pic]'))closeZoom();},{signal:events.signal});
  document.addEventListener('scroll',()=>closeZoom(),{capture:true,signal:events.signal});
  function focus(i,pos){const t=container.querySelector(`[data-row="${i}"][data-f="dialogue"]`);if(t){t.focus({preventScroll:true});t.setSelectionRange(pos,pos);}}
  function changed(next,i,pos){measured=false;current=next;closeZoom(false);draw();onChange(current,measured);if(i!==undefined)focus(i,pos);}
  function totals(){const summary=rowSummary(current,measured);container.querySelector('[data-sb-total]').innerHTML=summary.count?D(`${summary.count} 镜 · ${measured?'':'约 '}${mmss(summary.seconds)}`):'';const times=rowTimes(current,measured);container.querySelectorAll('[data-sb-time]').forEach(e=>e.textContent=times[e.dataset.sbTime]?.map(mmss).join('–')||'—');const note=container.querySelector('[data-sb-note]');if(note)note.textContent=`台词里按回车拆成两镜，台词开头按退格并到上一镜${measured?(hasNarration?' · 时长按中台的配音':''):' · 时长按台词每秒 5.1 字估'}`;}
  function draw(){
    disposeClips();const n=i=>String(i+1).padStart(2,'0');
    const cell=(r,i,f,name)=>`<textarea rows="1" maxlength="2000" data-row="${i}" data-f="${f}" aria-label="第 ${n(i)} 镜${name}" placeholder="${f==='visual'?'写这一镜画什么（可不填）':'—'}"${r[f]?' data-design-data':''}>${esc(r[f])}</textarea>`;
    const pic=(r,i)=>r.image?.poster||r.image?.clip?`<button type="button" class="sb-pic" data-design-id="DV-SB-PIC" data-pic="${i}" aria-label="放大第 ${n(i)} 镜画面">${media(r.image)}</button>`:'<div class="sb-pic sb-none" data-design-id="DV-SB-PIC">还没有画面</div>';
    const table=`<div class="dv-sb-wrap"><table class="dv-sb" data-design-id="DV-SB-TABLE"><colgroup><col class="c-t"><col class="c-v"><col class="c-d"><col class="c-sub"><col class="c-cam"><col class="c-aud"></colgroup><thead><tr><th>镜头</th><th>画面</th><th>台词</th><th>字幕 / 花字</th><th>景别 · 运镜</th><th>音乐 / 音效<small>暂不进成片</small></th></tr></thead><tbody>${current.map((r,i)=>`<tr data-design-id="DV-SB-ROW"><td class="sb-t"><b data-design-data>${n(i)}</b><span data-sb-time="${i}" data-design-data></span></td><td><div class="sb-v">${pic(r,i)}<div class="sb-vt">${r.image?.tag?`<em class="sb-tag${r.image.pending?' sb-warn':''}" data-design-data>${esc(r.image.tag)}</em>`:''}${cell(r,i,'visual','画面')}</div></div></td><td>${cell(r,i,'dialogue','台词')}</td><td>${cell(r,i,'subtitle','字幕 / 花字')}</td><td>${cell(r,i,'camera','景别 · 运镜')}</td><td>${cell(r,i,'audio','音乐 / 音效')}</td></tr>`).join('')}</tbody></table></div>`;
    container.innerHTML=`<section class="dv-form" data-design-id="DV-SCRIPT"><header><div><h3>分镜脚本</h3><span class="dv-script-sub" data-max-lines="1">每镜写台词，就是配音要念的话；画面、字幕、景别 · 运镜不写，由 Opus 定。</span></div><span data-sb-total></span></header>${source}${current.length?table:'<div class="dv-sb-empty"><textarea aria-label="台词" data-empty placeholder="把台词粘贴进来，每一行会变成一镜。例如：&#10;清华 AI 体育博主，断更一年。会写代码，会练体能，就是发不出一条视频。&#10;第一句：发出去，会被人看低。"></textarea></div>'}<footer><p aria-live="polite">${current.length?'<span data-sb-note data-design-data></span>':'还没有分镜脚本。可以粘贴台词、导入分镜文件，或从中台交过来。'}</p><div class="actions"><button class="btn" data-import>导入分镜文件</button></div></footer></section>`;
    totals();container.querySelector('[data-import]').onclick=onImport;container.querySelector('[data-take-handoff]')?.addEventListener('click',onTakeHandoff);
    const grow=t=>{t.style.height='auto';t.style.height=t.scrollHeight+2+'px';};
    container.querySelectorAll('textarea[data-f]').forEach(t=>{
      grow(t);t.oninput=()=>{if(t.dataset.f==='dialogue')measured=false;current[Number(t.dataset.row)][t.dataset.f]=t.value;grow(t);totals();onChange(current,measured);};
      if(t.dataset.f!=='dialogue')return;
      t.onkeydown=e=>{const i=Number(t.dataset.row);if(e.isComposing||e.keyCode===229)return;if(e.key==='Enter'){e.preventDefault();changed(splitRow(current,i,t.selectionStart,t.selectionEnd),i+1,0);}else if(e.key==='Backspace'&&i>0&&t.selectionStart===0&&t.selectionEnd===0){e.preventDefault();const pos=current[i-1].dialogue.length;changed(mergeRow(current,i),i-1,pos);}};
      t.onpaste=e=>{const text=e.clipboardData.getData('text/plain');if(!/[\r\n]/.test(text))return;e.preventDefault();const i=Number(t.dataset.row),next=pasteRows(current,i,t.selectionStart,t.selectionEnd,text),target=i+next.length-current.length;changed(next,Math.max(i,target),next[Math.max(i,target)]?.dialogue.length||0);};
    });
    const empty=container.querySelector('[data-empty]');if(empty){empty.oninput=e=>{if(e.isComposing)return;const next=normalizeRows(empty.value.split(/\r?\n/).filter(x=>x.trim()).map(dialogue=>({dialogue})));if(next.length)changed(next,next.length-1,next.at(-1).dialogue.length);};empty.oncompositionend=()=>empty.oninput({});}
    container.querySelectorAll('button[data-pic]').forEach(b=>b.onclick=()=>openZoom(b));disposeClips=bindClips(container);
  }
  draw();return {focus:()=>focus(0,0),dispose(){closeZoom(false);disposeClips();events.abort();}};
}
