import {mountBeatMap, waveHeights, beatMetrics, sectionAt, barAt, formatBeatTime as mmss} from '/beat-map.js';
export {waveHeights};
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const source={qishui:'汽水音乐',netease:'网易云音乐',netease_client:'网易云音乐',local:'本机文件'};
export function createMusicView(ctx) {
 const {api,notice,root,top,mark,D,esc,button,active}=ctx;
 let tracks=[],taxonomy={sections:[],tag_categories:[],display:{filter_order:[],panel_order:[],row:[]}},selectedId,filter='all',job=null,paste='',poll,opened=false,frame,map,epoch=0;
 const selectedTags=new Set(),optimistic=new Map(),player=()=>$('#music-player');
 const current=()=>tracks.find(t=>t.file_sha256===selectedId)||tracks.find(t=>t.platform==='netease')||tracks[0];
 const fmt=(iso,time=false)=>new Date(iso).toLocaleString('zh-CN',{year:'numeric',month:'numeric',day:'numeric',...(time?{hour:'2-digit',minute:'2-digit',hour12:false}:{})});
 const categories=()=>Object.fromEntries(taxonomy.tag_categories.map(c=>[c.id,c]));
 const names=()=>Object.fromEntries(taxonomy.tag_categories.flatMap(c=>c.tags.map(t=>[t.id,t.name])));
 const kindName=kind=>taxonomy.sections.find(s=>s.id===kind)?.name||'';
 const tagIds=(m,g)=>m.tags?.status==='done'?m.tags[g]||[]:[];
 const srcOK=m=>filter==='all'||(m.platform==='netease_client'?'netease':m.platform)===filter;
 const groupOK=(m,g)=>{const ids=[...selectedTags].filter(id=>id.split('.')[0]===g);return !ids.length||ids.some(id=>tagIds(m,g).includes(id));};
 const visible=m=>srcOK(m)&&taxonomy.display.filter_order.every(g=>groupOK(m,g));
 const ahead=m=>tracks.slice(0,tracks.indexOf(m)).filter(t=>['queued','analyzing'].includes(t.beat?.status)).length;
 const busy=()=>tracks.some(m=>['beat','tags'].some(part=>['queued','analyzing'].includes(m[part]?.status)));
 function stopPolling(){epoch++;clearTimeout(poll);cancelAnimationFrame(frame);map?.destroy();map=null;}
 function receive(payload){tracks=payload.tracks;taxonomy=payload.taxonomy||taxonomy;for(const [id,parts] of optimistic){const track=tracks.find(t=>t.file_sha256===id);if(track)Object.assign(track,parts);}}
 function schedule(){clearTimeout(poll);if(active()&&(busy()||job?.state==='importing'))poll=setTimeout(()=>refresh().catch(e=>{notice(e.message,true);schedule();}),1000);}
 async function refresh(){const token=epoch,oldJob=JSON.stringify(job);if(job?.state==='importing'){const value=await api(`/api/review/imports/${job.id}`);if(token!==epoch||!active())return;job=value.job;}
  const payload=await api('/api/review/music');if(token!==epoch||!active())return;const old=JSON.stringify([tracks,taxonomy]);receive(payload);if(old!==JSON.stringify([tracks,taxonomy])||oldJob!==JSON.stringify(job))paint();schedule();}
 function speedMeta(m){return m.beat?.status==='done'?`<span data-design-data>${beatMetrics(m.beat).bpm}</span> BPM`:{queued:'排队中',analyzing:'分析中',failed:'没分析出来'}[m.beat?.status]||'';}
 function speedCell(m){return m.beat?.status==='done'?`<span class="bm-speed"><b data-design-data>${beatMetrics(m.beat).bpm}</b> BPM</span>`:`<span class="bm-state ${m.beat?.status==='failed'?'bm-state--warn':''}">${m.beat?.status==='analyzing'?'<i class="bm-spin" aria-hidden="true"></i>':''}${speedMeta(m)}</span>`;}
 function rowTags(m){if(m.tags?.status==='failed')return '<small class="tg-fail">标签没标出来</small>';if(['queued','analyzing'].includes(m.tags?.status)&&['done','failed'].includes(m.beat?.status))return '<small class="bm-state">分析中</small>';if(m.tags?.status!=='done')return '';
  const ids=taxonomy.display.row.map(r=>tagIds(m,r.category)[0]||(r.fallback?tagIds(m,r.fallback)[0]:null)).filter(Boolean),labels=names();
  return `<span class="tags" data-design-id="R223-TAG-row">${ids.map(id=>`<i class="tag">${esc(labels[id])}</i>`).join('')}</span>`;}
 function tagFilters(){const cats=categories(),labels=names();const groups=taxonomy.display.filter_order.map(g=>{
  const base=tracks.filter(m=>srcOK(m)&&taxonomy.display.filter_order.every(other=>other===g||groupOK(m,other)));
  const ordered=cats[g].tags.filter(t=>t.status==='active').map(t=>t.id);
  const keys=ordered.map(id=>({id,n:base.filter(m=>tagIds(m,g).includes(id)).length})).filter(({id,n})=>n||selectedTags.has(id)).sort((a,b)=>b.n-a.n);
  return keys.length?`<span class="tf-label">${esc(cats[g].name)}</span>${keys.map(({id,n})=>`<button class="pill" data-tag="${esc(id)}" aria-pressed="${selectedTags.has(id)}">${esc(labels[id])}<i data-design-data>${n}</i></button>`).join('')}`:'';
 }).join('');return groups?`<div class="tagfilters full" data-design-id="R223-TAG-filters">${groups}</div>`:'';}
 function failureBlock(part,value){const code=value.failure?.code,unreadable=code==='audio_unreadable',known=code==='worker_error'||code==='timeout';
  const text=unreadable?'这首的音频文件读不出来，再分析也一样。换一个文件，用右上角「从文件夹导入」重新导入。':known?'分析到一半出错了，可以再试一次。':'没认出是什么原因，可以再试一次。';
  return `<div class="attention bm-attn" role="alert" data-design-id="R223-${part==='beat'?'BEAT':'TAG'}-failed"><div><strong>${part==='beat'?'节拍没分析出来':'标签没标出来'}</strong><p>${text}${!known&&!unreadable?` <code data-design-data>${esc(code)}</code>`:''}</p></div>${unreadable?'':`<button class="btn" data-retry-part="${part}">${part==='beat'?'重新分析':'重新标注'}</button>`}</div>`;}
 function aiBlock(m){const title=esc(taxonomy.display.panel_title);if(m.tags?.status==='failed')return `<div class="tg"><div class="tg-head">${title}</div>${failureBlock('tags',m.tags)}</div>`;if(['queued','analyzing'].includes(m.tags?.status)&&['done','failed'].includes(m.beat?.status))return `<div class="tg" data-design-id="R223-TAG-panel"><div class="tg-head">${title}</div><span class="bm-state">分析中</span></div>`;if(m.tags?.status!=='done')return '';
  const cats=categories(),labels=names();return `<div class="tg" data-design-id="R223-TAG-panel"><div class="tg-head">${title}</div>${taxonomy.display.panel_order.map(g=>`<div class="tg-row" data-category="${g}"><span>${esc(cats[g].name)}</span><div>${g==='voice'&&m.tags.voice_uncertain?`<em>${esc(cats[g].uncertain_text)}</em>`:tagIds(m,g).length?tagIds(m,g).map(id=>`<i class="tag">${esc(labels[id])}</i>`).join('')+(g==='genre'&&m.tags.style?`<small data-design-data>${esc(m.tags.style)}</small>`:''):`<em>${esc(cats[g].empty_text||'')}</em>`}</div></div>`).join('')}</div>`;}
 function rail(m){const done=m.beat?.status==='done';return `<button class="rail-close" data-close-rail aria-label="关闭">×</button><div class="wave"><div class="bm-host"></div></div><div class="rail-body"><h3 data-design-data>${esc(m.title)}</h3><p class="where" data-design-data>${esc(m.artist)}</p>${aiBlock(m)}<div class="kv"><span>来源</span><strong>${source[m.platform]||D(m.platform)}${m.original_url?`<small><a class="link" href="${esc(m.original_url)}" target="_blank" rel="noopener noreferrer">打开原页面</a></small>`:''}</strong></div><div class="kv"><span>时长</span><strong data-design-data>${mmss(m.duration_seconds)}</strong></div>${done?`<div class="kv" data-design-id="R223-BEAT-speed"><span>速度</span><strong><span data-design-data>${beatMetrics(m.beat).bpm}</span> BPM<small>每小节 <span data-design-data>${beatMetrics(m.beat).meter}</span> 拍</small></strong></div>`:''}<div class="kv"><span>导入时间</span><strong data-design-data>${fmt(m.imported_at,true)}</strong></div></div>`;}
 function analysisState(m){const s=m.beat?.status;if(s==='queued')return 'music-beats-queued';if(s==='analyzing')return 'music-beats-analyzing';if(s==='failed')return m.beat.failure?.code==='audio_unreadable'?'music-beats-failed-unreadable':['worker_error','timeout'].includes(m.beat.failure?.code)?'music-beats-failed':'music-beats-failed-unknown';return m.tags?.status==='failed'?'music-tags-failed':'music';}
 function result() {
  if(job?.state==='duplicate')return `<div class="note full" role="status" data-design-id="R208-MUSIC-result">《${D(job.title)}》已经在库里了，没有重新下载。</div>`;
  if(job?.state==='member')return `<div class="attention full" role="alert" data-design-id="R208-MUSIC-result"><div><strong>《${D(job.title)}》要网易云会员才能下载</strong><p>你的网易云账号不是会员，库里没有多出任何东西。可以去汽水音乐找同名歌。</p></div>${button('去汽水音乐找同名歌','data-search-elsewhere')}</div>`;
  if(job?.state==='error'){
   const douyin=job.reason?.startsWith('没从抖音取到这首的音乐。');
   return `<div class="attention full" role="alert" data-design-id="R208-MUSIC-result"><div>${douyin?'<strong>没从抖音取到这首的音乐</strong><p>可以在剪映里直接用原声，或者找这首歌在汽水音乐、网易云音乐的分享链接。</p>':`<p data-design-data>${esc(job.reason)}</p>`}</div></div>`;
  }
  return '';
 }
 function paint(){if(!active())return;const importing=job?.state==='importing',shown=tracks.filter(visible);
  if(shown.length&&!shown.includes(current())){select(shown[0],false);}
  const m=current(),state=importing?'music-importing':job?.state==='duplicate'?'music-dup':job?.state==='member'?'music-vip':job?.state==='error'&&job.reason?.startsWith('没从抖音')?'music-douyin':!tracks.length?'music-empty':!shown.length?'music-filter-empty':analysisState(m);
  map?.destroy();map=null;mark(state);top('音乐库','配乐卡点从这里选歌',button('从文件夹导入','data-from-folder'));
  const form=`<form class="import" data-design-id="R208-MUSIC-import" id="music-import"><label for="paste">粘贴分享链接导入</label><div class="import-row"><input id="paste" value="${esc(paste)}" placeholder="粘贴汽水音乐或网易云音乐的分享文字" ${importing?'disabled':''}>${button(importing?'导入中':'导入',importing?'disabled':'',true)}</div><small>每首只下载一次，之后都用本机这份。</small></form>`;
  if(!tracks.length){root().classList.add('single');root().innerHTML=form+result()+`<div class="empty" data-design-id="R208-MUSIC-empty"><h2>音乐库还是空的</h2><p>在上面粘贴一首歌在汽水音乐或网易云音乐的分享文字；手里已有的歌，用右上角「从文件夹导入」。配乐卡点时只从这里选歌。</p></div>`;bind();return;}
  if(!shown.length)root().classList.add('single');
  root().innerHTML=form+result()+`<div class="subfilters full" data-design-id="R208-MUSIC-filters">${[['all','全部'],['qishui','汽水音乐'],['netease','网易云音乐'],['local','本机文件']].map(([k,l])=>{const n=k==='all'?tracks.length:tracks.filter(t=>(t.platform==='netease_client'?'netease':t.platform)===k).length;return n||k==='all'?`<button class="pill" data-src="${k}" aria-pressed="${filter===k}">${l}<i data-design-data>${n}</i></button>`:'';}).join('')}</div>${tagFilters()}<div class="music-tracks" data-design-id="R208-MUSIC-list"><div class="trow head"><span></span><span>歌名</span><span>来源</span><span>时长</span><span>速度</span><span>导入时间</span></div>${importing?'<div class="trow" data-design-id="R208-MUSIC-importing"><span>—</span><span class="t"><b>正在导入</b></span></div>':''}${shown.length?shown.map(m=>`<button class="trow" data-track="${m.file_sha256}" aria-selected="${current()?.file_sha256===m.file_sha256}"><span class="play" data-play="${m.file_sha256}" aria-label="播放">${player().dataset.id===m.file_sha256&&!player().paused?'❚❚':'▶'}</span><span class="t"><b data-design-data>${esc(m.title)}</b><small data-design-data>${esc(m.artist)}</small><small class="meta">${source[m.platform]} · ${speedMeta(m)}</small>${rowTags(m)}</span><span>${source[m.platform]}</span><span data-design-data>${mmss(m.duration_seconds)}</span><span>${speedCell(m)}</span><span data-design-data>${fmt(m.imported_at)}</span></button>`).join(''):'<div class="tg-none" data-design-id="R223-TAG-noresult">这样筛选没有歌。<button class="btn" data-clear>清除标签筛选</button></div>'}</div>${shown.length?`<aside class="review-rail ${opened?'open':''}" id="rail" data-design-id="R208-MUSIC-rail">${rail(m)}</aside>`:''}`;
  if(shown.length){const host=$('.bm-host'),done=m.beat?.status==='done';map=mountBeatMap(host,{duration:m.duration_seconds,songs:[{id:m.file_sha256,title:m.title,start:0,end:m.duration_seconds,offset:0,beatMap:{duration_seconds:m.duration_seconds,...m.beat},peaks:m.peaks}],lane:done,taxonomy,onSeek:seek});
   const details=document.createElement('div');details.className='bm-details';
   details.innerHTML=(done?`<div class="bm-legend" data-design-id="R223-BEAT-legend">${taxonomy.sections.map(s=>`<span><i class="sw sw--${s.id}"></i>${esc(s.name)}</span>`).join('')}</div>`:m.beat?.status==='queued'?`<div class="bm-status" data-design-id="R223-BEAT-status"><span>排队等分析，前面还有 <span data-design-data>${ahead(m)}</span> 首。</span></div>`:m.beat?.status==='analyzing'?'<div class="bm-status" data-design-id="R223-BEAT-status"><span>正在分析节拍和标签</span><span class="lbar"><i></i></span></div>':failureBlock('beat',m.beat))+`<div class="bm-transport" data-design-id="R223-BEAT-transport"><button data-toggle-music aria-label="播放">▶</button><span id="ptime" data-design-data></span>${done?'<span class="bm-where"><span class="bm-bar"></span><span class="bm-kind"></span></span>':''}</div>`;
   host.insertBefore(details,host.querySelector('.bm-lane'));paintProgress();}
  bind();
 }
 function paintProgress(){const m=current();if(!m||!active())return;const p=player(),t=p.dataset.id===m.file_sha256?p.currentTime:0;map?.setTime(t);if($('#ptime'))$('#ptime').textContent=`${mmss(t)} / ${mmss(m.duration_seconds)}`;
  if($('.bm-bar')){const n=barAt(m.beat,t);$('.bm-bar').innerHTML=n?`第 <span data-design-data>${n}</span> 小节`:'';const section=sectionAt(m.beat,t);$('.bm-kind').textContent=kindName(section?.kind);$('.bm-kind').className='bm-kind bm-kind--'+section?.kind;}
  const playing=p.dataset.id===m.file_sha256&&!p.paused;const toggle=$('[data-toggle-music]');if(toggle){toggle.textContent=playing?'❚❚':'▶';toggle.setAttribute('aria-label',playing?'暂停':'播放');}
  $$('[data-play]').forEach(b=>b.textContent=p.dataset.id===b.dataset.play&&!p.paused?'❚❚':'▶');
 }
 function tick(){paintProgress();if(active()&&!player().paused)frame=requestAnimationFrame(tick);}
 function select(m,open=true){const p=player();if(current()?.file_sha256!==m.file_sha256){p.pause();if(p.dataset.id===m.file_sha256)p.currentTime=0;}selectedId=m.file_sha256;if(open)opened=true;}
 function readyAudio(m){const p=player();if(p.dataset.id!==m.file_sha256){p.src=m.audio;p.dataset.id=m.file_sha256;}return p;}
 function seek(t){const id=current().file_sha256,p=readyAudio(current());const apply=()=>{if(p.dataset.id!==id)return;p.currentTime=t;paintProgress();};if(Number.isFinite(p.duration))apply();else{p.addEventListener('loadedmetadata',apply,{once:true});p.load();}}
 function play(m){const p=readyAudio(m);if(p.paused)p.play().catch(e=>notice(e.message,true));else p.pause();}
 function finishOptimistic(id,part){const parts=optimistic.get(id);if(!parts)return;delete parts[part];if(!Object.keys(parts).length)optimistic.delete(id);}
 async function retry(part){const m=current(),id=m.file_sha256,old=structuredClone(m[part]);optimistic.set(id,{...(optimistic.get(id)||{}),[part]:{status:'analyzing'}});m[part]={status:'analyzing'};paint();
  try{await api(`/api/review/music/${id}/reanalyze`,{method:'POST',body:{part}});finishOptimistic(id,part);await refresh();}catch(e){finishOptimistic(id,part);const track=tracks.find(t=>t.file_sha256===id);if(track)track[part]=old;if(active())paint();notice(e.message,true);schedule();}}
 async function importMusic(value){try{job=(await api('/api/review/music/import',{method:'POST',body:value})).job;paint();await refresh();}catch(e){notice(e.message,true);}}
 function bind(){
  $('#paste').oninput=e=>{paste=e.target.value;};$('#music-import').onsubmit=e=>{e.preventDefault();if(job?.state!=='importing')importMusic({text:paste});};
  $$('[data-src]').forEach(b=>b.onclick=()=>{filter=b.dataset.src;paint();});$$('[data-tag]').forEach(b=>b.onclick=()=>{const id=b.dataset.tag;selectedTags.has(id)?selectedTags.delete(id):selectedTags.add(id);paint();});$('[data-clear]')?.addEventListener('click',()=>{selectedTags.clear();paint();});
  $$('[data-track]').forEach(b=>b.onclick=e=>{select(tracks.find(m=>m.file_sha256===b.dataset.track));if(e.target.closest('[data-play]'))play(current());paint();});
  $('[data-toggle-music]')?.addEventListener('click',()=>play(current()));$('[data-close-rail]')?.addEventListener('click',()=>{opened=false;$('#rail').classList.remove('open');});
  $$('[data-retry-part]').forEach(b=>b.onclick=()=>retry(b.dataset.retryPart));$('[data-search-elsewhere]')?.addEventListener('click',()=>importMusic({text:paste,searchElsewhere:true}));$('[data-from-folder]')?.addEventListener('click',()=>$('#folder-dialog').showModal());
  $('#folder-form').onsubmit=e=>{e.preventDefault();const folder=new FormData(e.target).get('folder');$('#folder-dialog').close();importMusic({folder});};
  const p=player();p.ontimeupdate=paintProgress;p.onplay=()=>{cancelAnimationFrame(frame);tick();};p.onpause=()=>{cancelAnimationFrame(frame);paintProgress();};p.onended=()=>{cancelAnimationFrame(frame);paintProgress();};
 }
 return {stopPolling,async render(){const token=++epoch;const payload=await api('/api/review/music');if(token!==epoch||!active())return;receive(payload);paint();schedule();}};
}
